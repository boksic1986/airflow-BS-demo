from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from sqlalchemy import case, func, select

from app.models import AnalysisRun, KubernetesWorkload, RuleState, RunStageState, RunValidationIssue, Sample, TransferJob
from app.wgs_stage_contract import canonical_wgs_stage, project_wgs_orchestration, wgs_stage_definition


ACTIVE_TRANSFER_STATUSES = {"accepted", "submitted", "queued", "running", "started", "retrying"}
FAILED_RULE_STATUSES = {"failed", "error", "terminated"}


def build_wgs_workspace(*, session, run: AnalysisRun, run_payload: dict, heavy_slot_limit: int = 25, heavy_slot_mode: str = "monitor-only", evidence_root: str | None = None) -> dict:
    sample_count = session.scalar(
        select(func.count(Sample.id)).where(Sample.analysis_id == run.analysis_id)
    ) or 0
    rule_count, failed_rule_count = session.execute(
        select(
            func.count(RuleState.id),
            func.sum(case((RuleState.status.in_(FAILED_RULE_STATUSES), 1), else_=0)),
        ).where(
            RuleState.analysis_id == run.analysis_id,
            RuleState.attempt == run.attempt,
        )
    ).one()
    stage_rows = list(session.scalars(
        select(RunStageState).where(
            RunStageState.analysis_id == run.analysis_id,
            RunStageState.attempt == run.attempt,
        )
    ).all())
    active_rule = session.scalar(
        select(RuleState)
        .where(
            RuleState.analysis_id == run.analysis_id,
            RuleState.attempt == run.attempt,
            RuleState.status.in_(("accepted", "submitted", "running", "started")),
        )
        .order_by(RuleState.updated_at.desc())
        .limit(1)
    )
    active_transfer = session.scalar(
        select(TransferJob)
        .where(
            TransferJob.analysis_id == run.analysis_id,
            TransferJob.attempt == run.attempt,
            TransferJob.status.in_(ACTIVE_TRANSFER_STATUSES),
        )
        .order_by(TransferJob.updated_at.desc())
        .limit(1)
    )
    validation_issues = list(session.scalars(
        select(RunValidationIssue)
        .where(
            RunValidationIssue.analysis_id == run.analysis_id,
            RunValidationIssue.attempt == run.attempt,
            RunValidationIssue.status == "open",
        )
        .order_by(RunValidationIssue.id)
    ).all())
    raw_stage = str(run.current_stage or "created")
    stage_code = canonical_wgs_stage(raw_stage, run.status)
    stage_definition = wgs_stage_definition(stage_code)
    stage_row = next((item for item in stage_rows if item.stage_code == stage_code), None)
    progress_percent = (
        stage_row.progress_percent
        if stage_row is not None and stage_row.progress_available
        else int(run.progress_percent or 0)
    )
    progress = {
        "analysis_id": run.analysis_id,
        "pipeline": run.pipeline_name,
        "status": run.status,
        "dag_id": run.dag_id,
        "dag_run_id": run.dag_run_id,
        "percent": progress_percent,
        "current_step": active_rule.rule_name if active_rule is not None else stage_definition.label,
        "current_rule": active_rule.rule_name if active_rule is not None else None,
        "current_sample": active_rule.sample_id if active_rule is not None else None,
        "current_source": "snakemake_logger" if active_rule is not None else "database_snapshot",
        "note": "Database-backed workspace snapshot",
        "not_in_airflow": not bool(run.dag_run_id),
        "progress_source": stage_row.progress_source if stage_row is not None else "database_snapshot",
        "airflow_tasks": [],
        "rule_events": [],
        "stage_code": stage_code,
        "step_number": stage_row.step_number if stage_row is not None else stage_definition.step_number,
        "stage_label": stage_row.stage_label if stage_row is not None else stage_definition.label,
        "stage_status": stage_row.stage_status if stage_row is not None else run.status,
        "progress_available": bool(stage_row and stage_row.progress_available),
        "progress_percent": progress_percent,
        "completed_units": stage_row.completed_units if stage_row is not None else None,
        "total_units": stage_row.total_units if stage_row is not None else None,
        "unit": stage_row.unit if stage_row is not None else None,
        "current_item": stage_row.current_item if stage_row is not None else None,
        "speed_bps": stage_row.speed_bps if stage_row is not None else None,
        "eta_seconds": stage_row.eta_seconds if stage_row is not None else None,
        "stage_updated_at": stage_row.updated_at.isoformat() if stage_row is not None else None,
        "orchestration_stages": project_wgs_orchestration(
            run_status=run.status,
            current_stage=raw_stage,
            stage_rows=stage_rows,
        ),
    }
    return {
        "run": run_payload,
        "summary": {
            "sample_count": int(sample_count),
            "rule_count": int(rule_count or 0),
            "failed_rule_count": int(failed_rule_count or 0),
        },
        "progress": progress,
        "active_transfer": _serialize_transfer(active_transfer),
        "validation_issues": [
            {
                "id": row.id,
                "attempt": row.attempt,
                "code": row.code,
                "severity": row.severity,
                "scope_type": row.scope_type,
                "sample_id": row.sample_id,
                "family_id": row.family_id,
                "file_path": row.file_path,
                "message": row.message,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
                "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
            }
            for row in validation_issues
        ],
        "slot_usage": {
            "pool": "wgs-heavy-io",
            "limit": heavy_slot_limit,
            "used": _active_heavy_pod_count(session),
            "waiting": _heavy_slot_waiting_count(evidence_root),
            "mode": heavy_slot_mode,
        },
    }


def _active_heavy_pod_count(session) -> int:
    rows = session.scalars(
        select(KubernetesWorkload).where(
            KubernetesWorkload.phase.in_(("Pending", "Running")),
        )
    ).all()
    return sum(1 for row in rows if bool((row.resources_json or {}).get("heavy_io")))


def _heavy_slot_waiting_count(evidence_root: str | None) -> int:
    if not evidence_root:
        return 0
    root = Path(evidence_root)
    if not root.is_dir() or root.is_symlink():
        return 0
    now = datetime.now(timezone.utc)
    waiting = 0
    for path in root.glob("*/attempt-*/heavy-slot-status.json"):
        try:
            if path.is_symlink() or not path.is_file():
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
            updated = datetime.fromisoformat(
                str(value.get("updated_at") or "").replace("Z", "+00:00")
            )
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            if (
                value.get("schema_version") == "wgs-heavy-slot-status.v1"
                and value.get("state") == "waiting"
                and now - updated <= timedelta(minutes=2)
            ):
                waiting += 1
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return waiting


def _serialize_transfer(row: TransferJob | None) -> dict | None:
    if row is None:
        return None
    return {
        "transfer_id": row.transfer_id,
        "direction": row.direction,
        "status": row.status,
        "progress_percent": row.progress_percent if row.progress_detail_available else None,
        "bytes_total": row.bytes_total if row.progress_detail_available else None,
        "bytes_transferred": row.bytes_transferred if row.progress_detail_available else None,
        "files_total": row.files_total if row.progress_detail_available else None,
        "files_completed": row.files_completed if row.progress_detail_available else None,
        "current_file": row.current_file if row.progress_detail_available else None,
        "speed_bps": row.speed_bps if row.progress_detail_available else None,
        "eta_seconds": row.eta_seconds if row.progress_detail_available else None,
        "heartbeat_at": row.heartbeat_at.isoformat() if row.heartbeat_at else None,
    }
