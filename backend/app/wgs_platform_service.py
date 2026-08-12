from __future__ import annotations

from datetime import datetime, timedelta, timezone
import csv
import hashlib
from pathlib import Path
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.input_scanner import ensure_allowed_path
from app.models import AnalysisRun, MasterSlot, RunAction, RunAttempt, Sample, WgsIntakeBatch
from app.wgs_release_catalog import load_snapshot_catalog


EXECUTION_MODES = {"cce", "sge", "local"}
WGS_CCE_DAG_ID = "bio_wgs_cce"
WGS_ONPREM_DAG_ID = "bio_wgs_onprem"


def create_wgs_platform_run(*, session: Session, settings, project_name: str, execution_mode: str, source_path: str, submitted_by: str) -> dict:
    if execution_mode not in EXECUTION_MODES:
        raise ValueError("execution_mode must be cce, sge, or local.")
    source = ensure_allowed_path(source_path, list(getattr(settings, "wgs_config_roots", []) or []))
    if not source.is_dir():
        raise ValueError("WGS source_path must be a controlled batch directory.")
    ready = source / "READY"
    sample_manifest = _first_existing(source, ("sampleinfo.tsv", "samples.tsv", "sample_info.tsv"))
    md5_manifest = source / "FASTQ.MD5SUMS"
    if not ready.is_file() or sample_manifest is None or not md5_manifest.is_file():
        raise ValueError("WGS batch requires sample manifest, FASTQ.MD5SUMS, and READY.")
    samples = _read_samples(sample_manifest)
    if not samples:
        raise ValueError("WGS sample manifest contains no samples.")
    manifest_sha256 = hashlib.sha256(sample_manifest.read_bytes() + b"\0" + md5_manifest.read_bytes()).hexdigest()
    snapshot = load_snapshot_catalog(
        Path(settings.wgs_release_catalog_path)
    ).default_development()
    canonical_source = str(source.resolve())
    intake = session.scalar(select(WgsIntakeBatch).where(WgsIntakeBatch.source_path == canonical_source))
    if intake is not None:
        if intake.manifest_sha256 != manifest_sha256 or intake.ready_mtime_ns != ready.stat().st_mtime_ns:
            raise ValueError("WGS batch changed after READY; remove READY, correct the batch, and publish a new controlled batch.")
        existing = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == intake.analysis_id))
        if existing is not None:
            return run_payload(session, existing)
    analysis_id = f"WGS_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{secrets.token_hex(3).upper()}"
    workdir = Path(getattr(settings, "host_results_root", settings.container_shared_root)) / "runs" / analysis_id
    (workdir / "config").mkdir(parents=True, exist_ok=False)
    run = AnalysisRun(
        analysis_id=analysis_id,
        pipeline_name="wgs",
        dag_id=WGS_CCE_DAG_ID if execution_mode == "cce" else WGS_ONPREM_DAG_ID,
        mode="new",
        execution_mode=execution_mode,
        attempt=1,
        status="created",
        sample_sheet_path=str(sample_manifest),
        workdir=str(workdir),
        params_json={
            "project_name": project_name,
            "execution_mode": execution_mode,
            "source_path": str(source),
            "source_manifest_path": str(sample_manifest),
            "fastq_md5_manifest": str(md5_manifest),
            "manifest_sha256": manifest_sha256,
            "pipeline_snapshot_id": snapshot.snapshot_id,
            "source_commit": snapshot.source_commit,
            "snapshot_manifest_sha256": snapshot.snapshot_manifest_sha256,
            "rule_event_schema_version": snapshot.rule_event_schema_version,
        },
        submitted_by=submitted_by,
    )
    session.add(run)
    session.add(WgsIntakeBatch(source_path=canonical_source, manifest_sha256=manifest_sha256, analysis_id=analysis_id, ready_mtime_ns=ready.stat().st_mtime_ns))
    session.add(RunAttempt(analysis_id=analysis_id, attempt=1, execution_mode=execution_mode, status="created"))
    for item in samples:
        session.add(Sample(analysis_id=analysis_id, sample_id=item["sample_id"], family_id=item.get("family_id"), status="pending", qc_status="unknown", metadata_json={"source": "controlled_manifest"}))
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


def acquire_master_slot(*, session: Session, analysis_id: str, attempt: int, lease_minutes: int = 30) -> str | None:
    now = datetime.now(timezone.utc)
    slots = session.scalars(select(MasterSlot).order_by(MasterSlot.slot_name).with_for_update(skip_locked=True)).all()
    for slot in slots:
        expires = slot.lease_expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if slot.analysis_id is None or (expires is not None and expires <= now):
            slot.analysis_id = analysis_id
            slot.attempt = attempt
            slot.leased_at = now
            slot.lease_expires_at = now + timedelta(minutes=lease_minutes)
            session.commit()
            return slot.slot_name
    return None


def release_master_slot(*, session: Session, slot_name: str, analysis_id: str, attempt: int) -> bool:
    slot = session.scalar(select(MasterSlot).where(MasterSlot.slot_name == slot_name).with_for_update())
    if slot is None or slot.analysis_id != analysis_id or slot.attempt != attempt:
        return False
    slot.analysis_id = None
    slot.attempt = None
    slot.leased_at = None
    slot.lease_expires_at = None
    session.commit()
    return True


def run_payload(session: Session, run: AnalysisRun) -> dict:
    count = len(session.scalars(select(Sample).where(Sample.analysis_id == run.analysis_id)).all())
    return {"analysis_id": run.analysis_id, "pipeline": "wgs", "dag_id": run.dag_id, "dag_run_id": run.dag_run_id, "execution_mode": run.execution_mode, "attempt": run.attempt, "status": run.status, "sample_count": count, "workdir": run.workdir, "params": run.params_json, "submitted_by": run.submitted_by}


def _first_existing(root: Path, names: tuple[str, ...]) -> Path | None:
    return next((root / name for name in names if (root / name).is_file()), None)


def _read_samples(path: Path) -> list[dict[str, str | None]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = []
        for row in reader:
            sample_id = str(row.get("sample_id") or row.get("样本编号") or "").strip()
            if sample_id:
                family_id = str(row.get("family_id") or row.get("家系编号") or "").strip() or None
                rows.append({"sample_id": sample_id, "family_id": family_id})
        return rows
