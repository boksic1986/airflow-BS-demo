from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import secrets

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


EXECUTION_MODES = {"cce"}
WGS_CCE_DAG_ID = "bio_wgs"


def create_wgs_platform_run(*, session: Session, settings, project_name: str, execution_mode: str, batch_no: str, fq_path: str, submitted_by: str) -> dict:
    if execution_mode not in EXECUTION_MODES:
        raise ValueError("execution_mode must be cce for the cloud orchestration release.")
    batch_no = batch_no.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", batch_no):
        raise ValueError("batch_no contains unsupported characters.")
    source = ensure_allowed_path(fq_path, list(getattr(settings, "wgs_config_roots", []) or []))
    if not source.is_dir():
        raise ValueError("fq_path must be a controlled FASTQ link directory.")
    release = load_wgs_release_catalog(
        Path(settings.wgs_release_catalog_path)
    ).release
    canonical_source = str(source)
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
        },
        submitted_by=submitted_by,
    )
    session.add(run)
    snapshot_row = WgsInputSnapshot(analysis_id=analysis_id, attempt=1, batch_no=batch_no, fq_path=canonical_source, manifest_path=str(manifest_path), status="pending")
    session.add(snapshot_row)
    session.add(RunAttempt(analysis_id=analysis_id, attempt=1, execution_mode=execution_mode, status="created"))
    session.flush()
    _revalidate_input(session=session, settings=settings, run=run, snapshot_row=snapshot_row, allow_rebuild=True)
    session.commit()
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
    if run.status not in {"created", "failed", "cancelled"}:
        raise ValueError(f"Run status {run.status} cannot be submitted.")
    conf = {"analysis_id": run.analysis_id, "pipeline": "wgs", "execution_mode": run.execution_mode, "attempt": run.attempt, "workdir": run.workdir, "params": run.params_json}
    dag_run_id = f"manual__{run.analysis_id}__a{run.attempt}"
    airflow_client.trigger_dag_run(run.dag_id, dag_run_id=dag_run_id, conf=conf)
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
    *, session: Session, analysis_id: str, attempt: int, transfer_id: str | None = None
) -> bool:
    slot = session.scalar(
        select(ObsTransferLease)
        .where(ObsTransferLease.slot_name == "wgs-obs-transfer-01")
        .with_for_update()
    )
    if slot is None or slot.analysis_id is None:
        return False
    if slot.analysis_id != analysis_id or slot.attempt != attempt:
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
    sample_rows = {row.sample_id: row for row in session.scalars(select(Sample).where(Sample.analysis_id == run.analysis_id)).all()}
    pairs: dict[str, dict[str, str]] = {}
    for item in snapshot["files"]:
        pairs.setdefault(str(item["sample_id"]), {})[str(item["read"])] = str(item["resolved_path"])
    for sample_id, reads in pairs.items():
        row = sample_rows.get(sample_id)
        if row is None:
            session.add(Sample(analysis_id=run.analysis_id, sample_id=sample_id, family_id=None, fq1=reads["R1"], fq2=reads["R2"], status="pending", qc_status="unknown", metadata_json={"provider": "wgs_prepare_pending"}))
    run.status = "created"
    run.current_stage = "validate_request"
