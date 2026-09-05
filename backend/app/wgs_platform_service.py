from __future__ import annotations

from datetime import datetime, timedelta, timezone
import csv
import json
from pathlib import Path, PurePosixPath
import re
import secrets

from app.airflow_idempotency import ensure_dag_run

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.input_scanner import ensure_allowed_path
from app.models import (
    AnalysisRun, ObsTransferLease, RunAction, RunAttempt,
    RunValidationIssue, Sample, WgsInputSnapshot,
)
from app.wgs_orchestration_service import (
    SnapshotChangedError, build_fastq_snapshot, verify_fastq_snapshot,
)
from app.wgs_release_catalog import load_wgs_release_catalog
from app.wgs_run_projection import (
    load_wgs_runtime_binding,
    resolve_bound_wgs_batch_root,
)


EXECUTION_MODES = {"cce"}
WGS_CCE_DAG_ID = "bio_wgs"


class WgsPreparedArtifactPending(ValueError):
    """A successful remote prepare marker is visible before its NFS artifact."""


def create_wgs_platform_run(*, session: Session, settings, project_name: str, execution_mode: str, batch_no: str, fq_path: str, submitted_by: str, commit: bool = True, validate_input: bool = True, platform: str | None = None, sequencing_batch: str | None = None, analysis_batch: str | None = None, fastq_root: str | None = None, use_reference: str = "all") -> dict:
    if execution_mode not in EXECUTION_MODES:
        raise ValueError("execution_mode must be cce for the cloud orchestration release.")
    batch_no = batch_no.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", batch_no):
        raise ValueError("batch_no contains unsupported characters.")
    if validate_input:
        source = ensure_allowed_path(fq_path, list(getattr(settings, "wgs_config_roots", []) or []))
        if not source.is_dir():
            raise ValueError("fq_path must be a controlled FASTQ link directory.")
        canonical_source = str(source)
    else:
        source = PurePosixPath(fq_path)
        if not source.is_absolute() or ".." in source.parts:
            raise ValueError("catalog FASTQ root must be an absolute normalized path")
        canonical_source = str(source)
    release = load_wgs_release_catalog(
        Path(settings.wgs_release_catalog_path)
    ).release
    existing_snapshot = session.scalar(select(WgsInputSnapshot).where(WgsInputSnapshot.batch_no == batch_no, WgsInputSnapshot.fq_path == canonical_source))
    if existing_snapshot is not None:
        existing = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == existing_snapshot.analysis_id))
        if existing is not None:
            return run_payload(session, existing)
    analysis_id = f"WGS_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{secrets.token_hex(3).upper()}"
    workdir = Path(getattr(settings, "host_results_root", settings.container_shared_root)) / "runs" / analysis_id
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = config_dir / "input-manifest.json"
    run = AnalysisRun(
        analysis_id=analysis_id,
        pipeline_name="wgs",
        dag_id=WGS_CCE_DAG_ID,
        mode="new",
        execution_mode=execution_mode,
        attempt=1,
        status="snapshotting",
        sample_sheet_path=str(config_dir / "sampleinfo.tsv"),
        workdir=str(workdir),
        params_json={
            "project_name": project_name,
            "execution_mode": execution_mode,
            "batch_no": batch_no,
            "fq_path": canonical_source,
            "input_manifest_path": str(manifest_path),
            "pipeline_release_id": release.release_id,
            "wgs_version": release.version,
            "wgs_source_commit": release.source_commit,
            "rule_event_schema_version": release.rule_event_schema_version,
            "platform": platform,
            "sequencing_batch": sequencing_batch,
            "analysis_batch": analysis_batch,
            "fastq_root": fastq_root or canonical_source,
            "use_reference": use_reference,
        },
        submitted_by=submitted_by,
    )
    session.add(run)
    snapshot_row = WgsInputSnapshot(analysis_id=analysis_id, attempt=1, batch_no=batch_no, fq_path=canonical_source, manifest_path=str(manifest_path), status="pending")
    session.add(snapshot_row)
    session.add(RunAttempt(analysis_id=analysis_id, attempt=1, execution_mode=execution_mode, status="created"))
    session.flush()
    if validate_input:
        _revalidate_input(session=session, settings=settings, run=run, snapshot_row=snapshot_row, allow_rebuild=True)
    else:
        snapshot_row.status = "deferred_to_wgs_prepare"
        run.status = "created"
        run.current_stage = "validate_request"
    if commit:
        session.commit()
    else:
        session.flush()
    return run_payload(session, run)


def revalidate_wgs_run(*, session: Session, settings, analysis_id: str) -> dict | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs"))
    if run is None:
        return None
    snapshot_row = session.scalar(select(WgsInputSnapshot).where(WgsInputSnapshot.analysis_id == analysis_id, WgsInputSnapshot.attempt == run.attempt))
    if snapshot_row is None:
        raise ValueError("WGS input snapshot is missing.")
    _revalidate_input(
        session=session,
        settings=settings,
        run=run,
        snapshot_row=snapshot_row,
        allow_rebuild=not Path(snapshot_row.manifest_path).is_file(),
    )
    session.commit()
    return run_payload(session, run)


def submit_wgs_run(*, session: Session, airflow_client, analysis_id: str) -> dict | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs"))
    if run is None:
        return None
    if run.status == "submitted" and run.dag_run_id:
        return run_payload(session, run)
    if run.status not in {"created", "failed", "cancelled"}:
        raise ValueError(f"Run status {run.status} cannot be submitted.")
    conf = {"analysis_id": run.analysis_id, "pipeline": "wgs", "execution_mode": run.execution_mode, "attempt": run.attempt, "workdir": run.workdir, "params": run.params_json}
    dag_run_id = f"{run.analysis_id}-a{run.attempt}"
    ensure_dag_run(
        airflow_client=airflow_client,
        dag_id=run.dag_id,
        dag_run_id=dag_run_id,
        conf=conf,
    )
    run.dag_run_id = dag_run_id
    run.status = "submitted"
    run.submitted_at = datetime.now(timezone.utc)
    run.current_stage = "queued"
    for sample in session.scalars(select(Sample).where(Sample.analysis_id == analysis_id)).all():
        sample.status = "running"
    session.commit()
    return run_payload(session, run)


def action_wgs_run(*, session: Session, airflow_client, analysis_id: str, action: str, requested_by: str) -> dict | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs"))
    if run is None:
        return None
    if action == "cancel":
        run.status = "cancel_requested"
        run.current_stage = "cancel_requested"
        session.add(RunAction(analysis_id=analysis_id, action=action, requested_by=requested_by, result_status="accepted", payload_json={}))
        session.commit()
        return run_payload(session, run)
    if action not in {"resume", "rerun_failed"}:
        raise ValueError("Unsupported WGS action.")
    if run.status not in {"failed", "cancelled", "unknown_interrupted"}:
        raise ValueError(f"Run status {run.status} cannot be resumed.")
    run.attempt += 1
    run.mode = action
    run.status = "created"
    run.started_at = None
    run.ended_at = None
    run.pipeline_finished_at = None
    run.progress_percent = 0
    run.progress_updated_at = None
    run.error_summary = None
    session.add(RunAttempt(analysis_id=analysis_id, attempt=run.attempt, execution_mode=run.execution_mode, status="created"))
    session.add(RunAction(analysis_id=analysis_id, action=action, requested_by=requested_by, result_status="accepted", payload_json={"attempt": run.attempt}))
    session.commit()
    return submit_wgs_run(session=session, airflow_client=airflow_client, analysis_id=analysis_id)


def acquire_obs_transfer_slot(*, session: Session, analysis_id: str, attempt: int, transfer_id: str, lease_minutes: int = 30) -> str | None:
    now = datetime.now(timezone.utc)
    slot = session.scalar(select(ObsTransferLease).where(ObsTransferLease.slot_name == "wgs-obs-transfer-01").with_for_update(skip_locked=True))
    if slot is None:
        return None
    expires = slot.lease_expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if slot.analysis_id is not None and (expires is None or expires > now):
        if slot.analysis_id != analysis_id or slot.attempt != attempt:
            return None
        slot.transfer_id = transfer_id
        slot.lease_expires_at = now + timedelta(minutes=lease_minutes)
        session.commit()
        return slot.slot_name
    slot.analysis_id, slot.attempt, slot.transfer_id = analysis_id, attempt, transfer_id
    slot.leased_at, slot.lease_expires_at = now, now + timedelta(minutes=lease_minutes)
    session.commit()
    return slot.slot_name


def release_obs_transfer_slot(
    *,
    session: Session,
    analysis_id: str,
    attempt: int,
    transfer_id: str | None = None,
    ignore_foreign_owner: bool = False,
) -> bool:
    slot = session.scalar(
        select(ObsTransferLease)
        .where(ObsTransferLease.slot_name == "wgs-obs-transfer-01")
        .with_for_update()
    )
    if slot is None or slot.analysis_id is None:
        return False
    if slot.analysis_id != analysis_id or slot.attempt != attempt:
        if ignore_foreign_owner:
            return False
        raise ValueError("OBS transfer lease belongs to another WGS attempt")
    if transfer_id is not None and slot.transfer_id != transfer_id:
        raise ValueError("OBS transfer lease identifies another transfer")
    slot.analysis_id = None
    slot.attempt = None
    slot.transfer_id = None
    slot.leased_at = None
    slot.lease_expires_at = None
    session.commit()
    return True


def run_payload(session: Session, run: AnalysisRun) -> dict:
    count = len(session.scalars(select(Sample).where(Sample.analysis_id == run.analysis_id)).all())
    return {"analysis_id": run.analysis_id, "pipeline": "wgs", "dag_id": run.dag_id, "dag_run_id": run.dag_run_id, "execution_mode": run.execution_mode, "attempt": run.attempt, "status": run.status, "sample_count": count, "workdir": run.workdir, "params": run.params_json, "submitted_by": run.submitted_by}


def sync_prepared_samples(*, session: Session, settings, run: AnalysisRun) -> int:
    """Import only the final WGS analysis selection from the frozen batch."""
    value = load_wgs_runtime_binding(
        request_root=settings.wgs_runtime_request_root,
        analysis_id=run.analysis_id,
        attempt=run.attempt,
    )
    batch_root = resolve_bound_wgs_batch_root(
        binding=value,
        node_analysis_root=settings.wgs_results_host_root,
        local_analysis_root=settings.host_results_root,
    )
    sampleinfo = batch_root / "sampleinfo.tsv"
    if not sampleinfo.is_file() or sampleinfo.is_symlink():
        raise WgsPreparedArtifactPending(
            "WGS prepare final sampleinfo.tsv is not visible yet"
        )
    rows = list(csv.DictReader(sampleinfo.open(encoding="utf-8-sig", newline=""), delimiter="\t"))
    if not rows:
        raise ValueError("WGS prepare selected no analysis samples")
    existing = {item.sample_id: item for item in session.scalars(select(Sample).where(Sample.analysis_id == run.analysis_id)).all()}
    selected: set[str] = set()
    for source in rows:
        sample_id = str(source.get("样本编号") or "").strip()
        if not sample_id:
            raise ValueError("WGS final sampleinfo contains an empty sample ID")
        selected.add(sample_id)
        metadata = {
            "data_id": str(source.get("数据编号") or "").strip() or None,
            "family_relation": str(source.get("家系关系") or "").strip() or None,
            "sample_type": str(source.get("样本类型") or "").strip() or None,
            "sex": str(source.get("性别") or "").strip() or None,
            "sequencing_batch": str(source.get("上机批次") or "").strip() or None,
            "provider": "wgs_final_selection",
        }
        row = existing.get(sample_id)
        if row is None:
            row = Sample(analysis_id=run.analysis_id, sample_id=sample_id, family_id=str(source.get("家系编号") or "").strip() or None, sample_type=metadata["sample_type"], sex=metadata["sex"], status="running", qc_status="unknown", metadata_json=metadata)
            session.add(row)
        else:
            row.family_id = str(source.get("家系编号") or "").strip() or None
            row.sample_type = metadata["sample_type"]
            row.sex = metadata["sex"]
            row.status = "running"
            row.metadata_json = metadata
    for sample_id, row in existing.items():
        if sample_id not in selected:
            session.delete(row)
    session.flush()
    return len(selected)


def sync_sampleinfo_preview(*, session: Session, settings, run: AnalysisRun) -> int:
    """Import the safe sample/family projection produced before analysis prepare."""
    params = dict(run.params_json or {})
    sampleinfo = (
        Path(settings.host_results_root).resolve()
        / "sampleinfo"
        / f"{params['batch_no']}.sampleinfo.txt"
    )
    if not sampleinfo.is_file() or sampleinfo.is_symlink():
        raise WgsPreparedArtifactPending(
            "WGS sampleinfo table is not visible yet"
        )
    rows = list(csv.DictReader(sampleinfo.open(encoding="utf-8-sig", newline=""), delimiter="\t"))
    if not rows:
        raise ValueError("WGS sampleinfo preparation selected no samples")
    existing = {
        item.sample_id: item
        for item in session.scalars(
            select(Sample).where(Sample.analysis_id == run.analysis_id)
        ).all()
    }
    selected: set[str] = set()
    for source in rows:
        sample_id = str(source.get("样本编号") or "").strip()
        if not sample_id:
            raise ValueError("WGS sampleinfo contains an empty sample ID")
        selected.add(sample_id)
        metadata = {
            "data_id": str(source.get("数据编号") or "").strip() or None,
            "family_relation": str(source.get("家系关系") or "").strip() or None,
            "sample_type": str(source.get("样本类型") or "").strip() or None,
            "sex": str(source.get("性别") or "").strip() or None,
            "sequencing_batch": str(source.get("上机批次") or "").strip() or None,
            "provider": "wgs_sampleinfo_preview",
        }
        row = existing.get(sample_id)
        if row is None:
            session.add(
                Sample(
                    analysis_id=run.analysis_id,
                    sample_id=sample_id,
                    family_id=str(source.get("家系编号") or "").strip() or None,
                    sample_type=metadata["sample_type"],
                    sex=metadata["sex"],
                    status="pending",
                    qc_status="unknown",
                    metadata_json=metadata,
                )
            )
        else:
            row.family_id = str(source.get("家系编号") or "").strip() or None
            row.sample_type = metadata["sample_type"]
            row.sex = metadata["sex"]
            row.status = "pending"
            row.metadata_json = metadata
    for sample_id, row in existing.items():
        if sample_id not in selected:
            session.delete(row)
    session.flush()
    return len(selected)


def _revalidate_input(*, session: Session, settings, run: AnalysisRun, snapshot_row: WgsInputSnapshot, allow_rebuild: bool) -> None:
    for issue in session.scalars(select(RunValidationIssue).where(RunValidationIssue.analysis_id == run.analysis_id, RunValidationIssue.status == "open")).all():
        issue.status = "resolved"
        issue.resolved_at = datetime.now(timezone.utc)
    try:
        if allow_rebuild:
            snapshot = build_fastq_snapshot(
                fq_path=snapshot_row.fq_path,
                allowed_link_roots=list(getattr(settings, "wgs_config_roots", []) or []),
                allowed_fastq_roots=list(getattr(settings, "wgs_fastq_roots", []) or []),
                manifest_path=Path(snapshot_row.manifest_path),
            )
        else:
            snapshot = verify_fastq_snapshot(Path(snapshot_row.manifest_path))
    except (OSError, ValueError, SnapshotChangedError) as error:
        snapshot_row.status = "needs_review"
        run.status = "needs_review"
        run.current_stage = "validate_samples_and_families"
        session.add(RunValidationIssue(analysis_id=run.analysis_id, attempt=run.attempt, code="WGS_INPUT_INVALID", severity="error", scope_type="batch", file_path=snapshot_row.fq_path, message=str(error), status="open"))
        return
    snapshot_row.file_count = int(snapshot["file_count"])
    snapshot_row.total_bytes = int(snapshot["total_bytes"])
    snapshot_row.manifest_sha256 = str(snapshot["manifest_sha256"])
    snapshot_row.status = "verified"
    snapshot_row.verified_at = datetime.now(timezone.utc)
    run.params_json = {**run.params_json, "input_manifest_sha256": snapshot_row.manifest_sha256, "input_file_count": snapshot_row.file_count, "input_total_bytes": snapshot_row.total_bytes}
    run.status = "created"
    run.current_stage = "validate_request"
