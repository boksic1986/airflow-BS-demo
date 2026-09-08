from __future__ import annotations

from sqlalchemy import case, func, select

from app.gatk_stage_contract import gatk_stage_definition, project_gatk_orchestration
from app.models import AnalysisRun, RuleState, RunStageState, Sample, TransferJob


ACTIVE = {"accepted", "submitted", "queued", "running", "started", "retrying"}
FAILED = {"failed", "error", "terminated", "canceled"}


def build_gatk_workspace(*, session, run: AnalysisRun, run_payload: dict) -> dict:
    sample_count = session.scalar(
        select(func.count(Sample.id)).where(Sample.analysis_id == run.analysis_id)
    ) or 0
    rule_count, failed_rule_count = session.execute(
        select(
            func.count(RuleState.id),
            func.sum(case((RuleState.status.in_(FAILED), 1), else_=0)),
        ).where(
            RuleState.analysis_id == run.analysis_id,
            RuleState.attempt == run.attempt,
        )
    ).one()
    stage_rows = list(
        session.scalars(
            select(RunStageState).where(
                RunStageState.analysis_id == run.analysis_id,
                RunStageState.attempt == run.attempt,
            )
        ).all()
    )
    active_rule = session.scalar(
        select(RuleState)
        .where(
            RuleState.analysis_id == run.analysis_id,
            RuleState.attempt == run.attempt,
            RuleState.status.in_(ACTIVE),
        )
        .order_by(RuleState.updated_at.desc())
        .limit(1)
    )
    active_transfer = session.scalar(
        select(TransferJob)
        .where(
            TransferJob.analysis_id == run.analysis_id,
            TransferJob.attempt == run.attempt,
            TransferJob.status.in_(ACTIVE),
        )
        .order_by(TransferJob.updated_at.desc())
        .limit(1)
    )
    raw_stage = str(run.current_stage or "validate_request")
    stage_definition = gatk_stage_definition(raw_stage)
    stage_row = next(
        (row for row in stage_rows if row.stage_code == stage_definition.code), None
    )
    progress_percent = (
        stage_row.progress_percent
        if stage_row is not None and stage_row.progress_available
        else int(run.progress_percent or 0)
    )
    return {
        "run": run_payload,
        "summary": {
            "sample_count": int(sample_count),
            "rule_count": int(rule_count or 0),
            "failed_rule_count": int(failed_rule_count or 0),
        },
        "progress": {
            "analysis_id": run.analysis_id,
            "pipeline": "gatk",
            "status": run.status,
            "dag_id": run.dag_id,
            "dag_run_id": run.dag_run_id,
            "percent": progress_percent,
            "current_step": active_rule.rule_name if active_rule else stage_definition.label,
            "current_rule": active_rule.rule_name if active_rule else None,
            "current_sample": active_rule.sample_id if active_rule else None,
            "current_source": "snakemake_logger" if active_rule else "database_snapshot",
            "note": "Database-backed GATK workspace snapshot",
            "not_in_airflow": not bool(run.dag_run_id),
            "progress_source": stage_row.progress_source if stage_row else "database_snapshot",
            "airflow_tasks": [],
            "rule_events": [],
            "stage_code": stage_definition.code,
            "step_number": stage_definition.step_number,
            "stage_label": stage_row.stage_label if stage_row else stage_definition.label,
            "stage_status": stage_row.stage_status if stage_row else run.status,
            "progress_available": bool(stage_row and stage_row.progress_available),
            "progress_percent": progress_percent,
            "completed_units": stage_row.completed_units if stage_row else None,
            "total_units": stage_row.total_units if stage_row else None,
            "unit": stage_row.unit if stage_row else None,
            "current_item": stage_row.current_item if stage_row else None,
            "speed_bps": stage_row.speed_bps if stage_row else None,
            "eta_seconds": stage_row.eta_seconds if stage_row else None,
            "stage_updated_at": stage_row.updated_at.isoformat() if stage_row else None,
            "orchestration_stages": project_gatk_orchestration(
                run_status=run.status,
                current_stage=raw_stage,
                stage_rows=stage_rows,
            ),
        },
        "active_transfer": _serialize_transfer(active_transfer),
        "validation_issues": [],
        "slot_usage": {
            "pool": "gatk_cce_runs",
            "limit": 1,
            "used": 1 if str(run.status or "").lower() in ACTIVE else 0,
            "waiting": 0,
            "mode": "project_serial",
        },
    }

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
