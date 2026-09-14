from __future__ import annotations

from sqlalchemy import case, select

from app.models import TransferFileState
from app.models import TransferJob


SUCCESS_STATES = {"success", "succeeded", "complete", "completed"}
ACTIVE_TRANSFER_STATUSES = {
    "accepted", "submitted", "queued", "running", "started", "retrying",
    "publishing", "downloading",
}
TRANSFER_STAGES = {"step1_upload": "upload", "step5_download": "download"}


def active_transfer_snapshot(*, session, run, stage: str) -> dict | None:
    query = select(TransferJob).where(
        TransferJob.analysis_id == run.analysis_id,
        TransferJob.attempt == run.attempt,
        TransferJob.status.in_(ACTIVE_TRANSFER_STATUSES),
    )
    if stage in TRANSFER_STAGES:
        query = query.where(TransferJob.direction == TRANSFER_STAGES[stage])
    row = session.scalar(query.order_by(TransferJob.updated_at.desc(), TransferJob.id.desc()).limit(1))
    return serialize_transfer_job(row)


def transfer_stage_progress(snapshot: dict | None) -> dict:
    """One presentation mapping for Tracker and Run detail; no second formula."""
    snapshot = snapshot or {}
    return {
        "progress_available": bool(snapshot.get("progress_detail_available")),
        "percent": snapshot.get("progress_percent"),
        "progress_percent": snapshot.get("progress_percent"),
        "completed_units": snapshot.get("bytes_transferred"),
        "total_units": snapshot.get("bytes_total"),
        "unit": "bytes",
        "current_item": snapshot.get("current_file"),
        "speed_bps": snapshot.get("speed_bps"),
        "eta_seconds": snapshot.get("eta_seconds"),
        "stage_updated_at": snapshot.get("heartbeat_at"),
        "progress_source": "transfer-job-snapshot",
    }


def transfer_file_order_by():
    """Keep active file evidence ahead of queued and completed rows."""

    status = case(
        (TransferFileState.status.in_(("running", "started")), 0),
        (
            TransferFileState.status.in_(
                ("accepted", "planned", "submitted", "queued", "pending")
            ),
            1,
        ),
        (TransferFileState.status.in_(("failed", "error")), 2),
        (TransferFileState.status.in_(tuple(SUCCESS_STATES)), 3),
        else_=4,
    )
    return status, TransferFileState.updated_at.desc(), TransferFileState.id


def transfer_progress_percent(row: TransferJob) -> float | None:
    if not row.progress_detail_available:
        return None
    if str(row.status or "").lower() in SUCCESS_STATES:
        return 100.0
    total = max(0, int(row.bytes_total or 0))
    done = max(0, int(row.bytes_transferred or 0))
    if total <= 0:
        return 0.0
    return round(min(100.0, done * 100.0 / total), 1)


def serialize_transfer_job(row: TransferJob | None) -> dict | None:
    if row is None:
        return None
    detailed = bool(row.progress_detail_available)
    return {
        "id": row.id,
        "transfer_id": row.transfer_id,
        "attempt": row.attempt,
        "transfer_type": row.transfer_type,
        "direction": row.direction,
        "source": "Input FASTQ manifest" if row.direction == "upload" else "Published result manifest",
        "destination": "Private OBS staging" if row.direction == "upload" else "Run-local result staging",
        "status": row.status,
        "progress_basis": "frozen_plan" if row.manifest_path else "legacy_estimate",
        "transfer_engine": "obsutil" if row.checkpoint_ref == "obsutil-checkpoint" else None,
        "progress_detail_available": detailed,
        "bytes_total": row.bytes_total if detailed else None,
        "bytes_transferred": row.bytes_transferred if detailed else None,
        "files_total": row.files_total if detailed else None,
        "files_completed": row.files_completed if detailed else None,
        "current_file": row.current_file if detailed else None,
        "progress_percent": transfer_progress_percent(row),
        "speed_bps": row.speed_bps if detailed else None,
        "eta_seconds": row.eta_seconds if detailed else None,
        "estimated_finish_at": (
            row.estimated_finish_at.isoformat()
            if detailed and row.estimated_finish_at
            else None
        ),
        "checkpoint_ref": "recorded" if row.checkpoint_ref else None,
        "heartbeat_at": row.heartbeat_at.isoformat() if row.heartbeat_at else None,
        "verification_status": row.verification_status,
        "message": row.message,
        "error_message": row.error_message,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.ended_at.isoformat() if row.ended_at else None,
        "ended_at": row.ended_at.isoformat() if row.ended_at else None,
    }
