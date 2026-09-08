from __future__ import annotations

from sqlalchemy import case

from app.models import TransferFileState
from app.models import TransferJob


SUCCESS_STATES = {"success", "succeeded", "complete", "completed"}


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
