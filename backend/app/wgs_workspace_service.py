from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from sqlalchemy import case, func, select

from app.models import AnalysisRun, KubernetesWorkload, RuleState, RunStageState, RunValidationIssue, Sample, TransferJob
from app.qc_highlights import aggregate_qc_status
from app.sample_selection_scope import selected_clause
from app.wgs_sample_projection import get_wgs_batch_qc_status
from app.wgs_stage_contract import canonical_wgs_stage, project_wgs_orchestration, wgs_stage_definition
from app.wgs_transfer_projection import serialize_transfer_job


ACTIVE_TRANSFER_STATUSES = {
    "accepted",
    "submitted",
    "queued",
    "running",
    "started",
    "retrying",
    "publishing",
    "downloading",
}
FAILED_RULE_STATUSES = {"failed", "error", "terminated"}


def build_wgs_workspace(*, session, run: AnalysisRun, run_payload: dict, heavy_slot_limit: int = 25, heavy_slot_mode: str = "monitor-only", evidence_root: str | None = None, settings=None) -> dict:
    sample_qc_statuses = list(session.scalars(
        select(Sample.qc_status).where(Sample.analysis_id == run.analysis_id, selected_clause())
    ).all())
    sample_count = len(sample_qc_statuses)
    batch_qc_status = (
        get_wgs_batch_qc_status(session=session, settings=settings, run=run)
        if settings is not None
        else aggregate_qc_status(sample_qc_statuses)
    )
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
    run_status = str(run.status or "").lower()
    preferred_stage_row = None
    if run_status in ACTIVE_TRANSFER_STATUSES:
        preferred_stage_row = max(
            (
                row
                for row in stage_rows
                if str(row.stage_status or "").lower() in ACTIVE_TRANSFER_STATUSES
            ),
            key=lambda row: row.updated_at,
            default=None,
        )
    elif run_status in FAILED_RULE_STATUSES:
        preferred_stage_row = max(
            (
                row
                for row in stage_rows
                if str(row.stage_status or "").lower() in FAILED_RULE_STATUSES
            ),
            key=lambda row: row.updated_at,
            default=None,
        )
    raw_stage = str(
        preferred_stage_row.stage_code
        if preferred_stage_row is not None
        else (run.current_stage or "created")
    )
    validation_scope = str((run.params_json or {}).get("validation_scope") or "") or None
    terminal_validation_stages = {
        "step1_only": "step1_canary_complete",
        "step3_dryrun": "step3_dryrun_complete",
    }
    stage_code = (
        terminal_validation_stages[validation_scope]
        if validation_scope in terminal_validation_stages
        and str(run.status or "").lower() == "success"
        else canonical_wgs_stage(raw_stage, run.status)
    )
    stage_definition = wgs_stage_definition(stage_code)
    stage_row = next((item for item in stage_rows if item.stage_code == stage_code), None)
    progress_percent = (
        stage_row.progress_percent
        if stage_row is not None and stage_row.progress_available
        else int(run.progress_percent or 0)
    )
    transfer_payload = serialize_transfer_job(active_transfer)
    transfer_stage = stage_code in {"step1_upload", "step5_download"}
    if transfer_stage and transfer_payload is not None:
        progress_percent = transfer_payload["progress_percent"]
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
        "progress_available": bool(
            transfer_payload is not None
            if transfer_stage
            else stage_row and stage_row.progress_available
        ),
        "progress_percent": progress_percent,
        "completed_units": (
            transfer_payload["bytes_transferred"]
            if transfer_stage and transfer_payload is not None
            else stage_row.completed_units if stage_row is not None else None
        ),
        "total_units": (
            transfer_payload["bytes_total"]
            if transfer_stage and transfer_payload is not None
            else stage_row.total_units if stage_row is not None else None
        ),
        "unit": stage_row.unit if stage_row is not None else None,
        "current_item": stage_row.current_item if stage_row is not None else None,
        "speed_bps": (
            transfer_payload["speed_bps"]
            if transfer_stage and transfer_payload is not None
            else stage_row.speed_bps if stage_row is not None else None
        ),
        "eta_seconds": stage_row.eta_seconds if stage_row is not None else None,
        "stage_updated_at": (
            transfer_payload["heartbeat_at"]
            if transfer_stage and transfer_payload is not None
            else stage_row.updated_at.isoformat() if stage_row is not None else None
        ),
        "orchestration_stages": _workspace_stages(
            run_status=run.status,
            current_stage=raw_stage,
            stage_rows=stage_rows,
            validation_scope=validation_scope,
        ),
    }
    return {
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "run": run_payload,
        "summary": {
            "sample_count": int(sample_count),
            "rule_count": int(rule_count or 0),
            "failed_rule_count": int(failed_rule_count or 0),
            "batch_qc_status": batch_qc_status,
        },
        "progress": progress,
        "active_transfer": transfer_payload,
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
        "slot_usage": project_global_heavy_slot(
            session=session,
            limit=heavy_slot_limit,
            mode=heavy_slot_mode,
            evidence_root=evidence_root,
        ),
    }


def _workspace_stages(*, run_status: str | None, current_stage: str | None, stage_rows: list[object], validation_scope: str | None) -> list[dict[str, object]]:
    items = project_wgs_orchestration(
        run_status=run_status,
        current_stage=current_stage,
        stage_rows=stage_rows,
    )
    if validation_scope == "step1_only" and str(run_status or "").lower() == "success":
        for item in items:
            item["status"] = item["stage_status"] = (
                "success" if item["stage_code"] == "step1_upload" else "skipped"
            )
            item["completed_jobs"] = 1 if item["stage_code"] == "step1_upload" else 0
    if validation_scope == "step3_dryrun" and str(run_status or "").lower() == "success":
        completed = {"step1_upload", "step2_master", "step3_monitor"}
        for item in items:
            item["status"] = item["stage_status"] = (
                "success" if item["stage_code"] in completed else "skipped"
            )
            item["completed_jobs"] = 1 if item["stage_code"] in completed else 0
    return items


def _active_heavy_pod_count(session) -> int:
    rows = session.scalars(
        select(KubernetesWorkload).where(
            KubernetesWorkload.phase.in_(("Pending", "Running")),
        )
    ).all()
    return sum(1 for row in rows if bool((row.resources_json or {}).get("heavy_io")))


def project_global_heavy_slot(*, session, limit, mode, evidence_root):
    from app.heavy_global_snapshot import read_snapshot
    return read_snapshot(evidence_root)


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
