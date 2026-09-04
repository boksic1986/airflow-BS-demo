from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import secrets

from sqlalchemy import func, select

from app.models import AnalysisRun, WgsStageExecution
from app.wgs_stage_catalog import WgsStageContract


ACTIVE = {"accepted", "running"}
TERMINAL = {"success", "failed", "canceled"}
TRANSITIONS = {
    "accepted": {"running", "success", "failed", "canceled"},
    "running": {"running", "success", "failed", "canceled"},
    "success": set(),
    "failed": set(),
    "canceled": set(),
}


def register_stage_execution(*, session, run: AnalysisRun, contract: WgsStageContract, stage_code: str, request_payload: dict, now: datetime | None = None, force_new_generation: bool = False) -> WgsStageExecution:
    if int((run.params_json or {}).get("orchestration_contract_version") or 1) != 2:
        raise ValueError("WGS stage execution registration requires contract version 2")
    definition = contract.stages.get(stage_code)
    if definition is None:
        raise ValueError(f"stage is not defined by contract v2: {stage_code}")
    now = now or datetime.now(timezone.utc)
    request_hash = _sha256(request_payload)
    latest = session.scalar(
        select(WgsStageExecution)
        .where(WgsStageExecution.analysis_id == run.analysis_id, WgsStageExecution.attempt == run.attempt, WgsStageExecution.stage_code == stage_code)
        .order_by(WgsStageExecution.generation.desc())
        .limit(1)
    )
    if latest is not None and not force_new_generation and latest.request_hash == request_hash:
        return latest
    if latest is not None and latest.status in ACTIVE:
        raise ValueError(f"stage {stage_code} already has an active generation")
    predecessor_code = _predecessor_code(run, definition)
    predecessor = _successful_predecessor(session, run, predecessor_code)
    generation = int(latest.generation + 1) if latest is not None else 1
    row = WgsStageExecution(
        execution_id=f"wse_{secrets.token_hex(12)}",
        analysis_id=run.analysis_id,
        attempt=run.attempt,
        stage_code=stage_code,
        generation=generation,
        status="accepted",
        request_hash=request_hash,
        release_id=str((run.params_json or {}).get("pipeline_release_id") or "unknown"),
        predecessor_execution_id=predecessor.execution_id if predecessor else None,
        predecessor_generation=predecessor.generation if predecessor else None,
        predecessor_receipt_hash=predecessor.receipt_hash if predecessor else None,
        heartbeat_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    return row


def transition_stage_execution(*, session, execution_id: str, generation: int, status: str, observed_at: datetime | None = None, receipt_hash: str | None = None, evidence_type: str | None = None, evidence_key: str | None = None, terminal_payload: dict | None = None, message: str | None = None) -> bool:
    normalized = str(status).lower()
    if normalized not in TRANSITIONS:
        raise ValueError(f"unsupported stage execution status: {status}")
    row = session.scalar(select(WgsStageExecution).where(WgsStageExecution.execution_id == execution_id))
    if row is None:
        raise ValueError("unknown stage execution")
    latest_generation = session.scalar(
        select(func.max(WgsStageExecution.generation)).where(
            WgsStageExecution.analysis_id == row.analysis_id,
            WgsStageExecution.attempt == row.attempt,
            WgsStageExecution.stage_code == row.stage_code,
        )
    )
    if row.generation != generation or row.generation != latest_generation:
        return False
    if normalized == row.status:
        return True
    if normalized not in TRANSITIONS.get(row.status, set()):
        return False
    if normalized == "success" and (not receipt_hash or len(receipt_hash) != 64):
        raise ValueError("successful stage execution requires a receipt hash")
    observed_at = observed_at or datetime.now(timezone.utc)
    row.status = normalized
    row.heartbeat_at = observed_at
    row.updated_at = observed_at
    row.message = message
    if normalized == "running" and row.started_at is None:
        row.started_at = observed_at
    if normalized in TERMINAL:
        row.ended_at = observed_at
        row.receipt_hash = receipt_hash
        row.evidence_type = evidence_type
        row.evidence_key = evidence_key
        row.terminal_payload_json = dict(terminal_payload or {})
    return True


def transition_latest_stage_execution(*, session, analysis_id: str, attempt: int, stage_code: str, status: str, observed_at: datetime, receipt_hash: str | None = None, evidence_type: str | None = None, evidence_key: str | None = None, terminal_payload: dict | None = None, message: str | None = None) -> bool:
    row = session.scalar(
        select(WgsStageExecution)
        .where(
            WgsStageExecution.analysis_id == analysis_id,
            WgsStageExecution.attempt == attempt,
            WgsStageExecution.stage_code == stage_code,
        )
        .order_by(WgsStageExecution.generation.desc())
        .limit(1)
    )
    if row is None:
        return False
    normalized = {"complete": "success", "completed": "success", "succeeded": "success", "cancelled": "canceled", "terminated": "canceled"}.get(str(status).lower(), str(status).lower())
    return transition_stage_execution(
        session=session,
        execution_id=row.execution_id,
        generation=row.generation,
        status=normalized,
        observed_at=observed_at,
        receipt_hash=receipt_hash,
        evidence_type=evidence_type,
        evidence_key=evidence_key,
        terminal_payload=terminal_payload,
        message=message,
    )


def validate_current_stage_execution(*, session, analysis_id: str, attempt: int, stage_code: str, execution_id: str, generation: int, request_hash: str) -> WgsStageExecution | None:
    row = session.scalar(
        select(WgsStageExecution).where(WgsStageExecution.execution_id == execution_id)
    )
    if row is None:
        raise ValueError("stage evidence references an unknown execution")
    if (
        row.analysis_id != analysis_id
        or row.attempt != attempt
        or row.stage_code != stage_code
        or row.generation != generation
        or row.request_hash != request_hash
    ):
        raise ValueError("stage evidence execution identity mismatch")
    latest_generation = session.scalar(
        select(func.max(WgsStageExecution.generation)).where(
            WgsStageExecution.analysis_id == analysis_id,
            WgsStageExecution.attempt == attempt,
            WgsStageExecution.stage_code == stage_code,
        )
    )
    return row if row.generation == latest_generation else None


def _successful_predecessor(session, run: AnalysisRun, predecessor_code: str | None) -> WgsStageExecution | None:
    if predecessor_code is None:
        return None
    row = session.scalar(
        select(WgsStageExecution)
        .where(
            WgsStageExecution.analysis_id == run.analysis_id,
            WgsStageExecution.attempt == run.attempt,
            WgsStageExecution.stage_code == predecessor_code,
        )
        .order_by(WgsStageExecution.generation.desc())
        .limit(1)
    )
    if row is None or row.status != "success" or not row.receipt_hash:
        raise ValueError(f"stage predecessor {predecessor_code} has no exact successful receipt")
    return row


def _predecessor_code(run: AnalysisRun, definition) -> str | None:
    mapping = definition.predecessors_by_submission_mode
    if not mapping:
        return definition.predecessor
    mode = str((run.params_json or {}).get("submission_mode") or "default")
    return mapping.get(mode, mapping.get("default", definition.predecessor))


def _sha256(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
