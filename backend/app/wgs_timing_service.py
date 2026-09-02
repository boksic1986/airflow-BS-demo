from __future__ import annotations

from datetime import datetime, timezone
from statistics import median

from sqlalchemy import select

from app.models import AnalysisRun, KubernetesWorkload, RuleState, RunStageState
from app.diagnostics_service import wgs_rule_failure_excerpts
from app.workflow_phases import phase_for_rule, phase_order


STAGE_DEFINITIONS = {
    "prepare": (None, "Preparing WGS batch"),
    "step1_upload": (1, "Uploading FASTQ"),
    "step2_master": (2, "Starting WGS workflow"),
    "step3_monitor": (3, "WGS workflow running"),
    "step4_publish": (4, "Publishing WGS results"),
    "step4_repair_cram": (4, "Repairing CRAM linkage"),
    "step5_download": (5, "Downloading WGS results"),
    "step6_materialize": (6, "Materializing local results"),
    "final": (None, "WGS workflow completed"),
}


def serialize_rule_states(*, session, run: AnalysisRun, rows: list[RuleState], settings=None) -> list[dict]:
    now = datetime.now(timezone.utc)
    history_runs = _history_runs(session, run)
    failure_logs = wgs_rule_failure_excerpts(run=run, rules=rows, settings=settings) if settings is not None else {}
    items = []
    for row in rows:
        phase = row.phase or phase_for_rule(row.rule_name, pipeline_name="wgs")
        durations = _rule_durations(session, history_runs, row.rule_name, row.layer)
        history_median = median(durations) if len(durations) >= 3 else None
        elapsed = _seconds(row.started_at, row.ended_at or now) if row.started_at else None
        remaining = max(0.0, history_median - elapsed) if history_median is not None and elapsed is not None and row.status == "running" else None
        items.append(
            {
                "attempt": row.attempt,
                "rule_instance_id": row.rule_instance_id,
                "sequence": row.sequence,
                "phase": phase,
                "phase_order": phase_order(phase, pipeline_name="wgs"),
                "layer": row.layer,
                "rule": row.rule_name,
                "snakemake_jobid": row.snakemake_jobid,
                "sample_id": row.sample_id,
                "family_id": row.family_id,
                "wildcards": dict(row.wildcards_json or {}),
                "status": row.status,
                "message": row.message,
                "log_keys": list(row.log_paths_json or []),
                "stderr_excerpt": (failure_logs.get(row.rule_instance_id) or {}).get("stderr_excerpt"),
                "analysis_log_key": (failure_logs.get(row.rule_instance_id) or {}).get("analysis_log_key"),
                "start_time": _iso(row.started_at),
                "end_time": _iso(row.ended_at),
                "elapsed_seconds": elapsed,
                "historical_median_seconds": history_median,
                "estimated_remaining_seconds": remaining,
                "eta_history_count": len(durations),
                "eta_model": "rule_wall_median_v1"
                if len(durations) >= 3
                else "insufficient_history",
            }
        )
    return items


def enrich_progress(*, session, run: AnalysisRun, payload: dict) -> dict:
    raw_stage = str(run.current_stage or payload.get("current_step") or "created")
    stage = _canonical_stage(raw_stage, run.status)
    stage_row = session.scalar(
        select(RunStageState).where(
            RunStageState.analysis_id == run.analysis_id,
            RunStageState.attempt == run.attempt,
            RunStageState.stage_code == stage,
        )
    )
    step_number, fallback_label = STAGE_DEFINITIONS.get(
        stage, (None, "Preparing WGS batch")
    )
    progress_available = bool(stage_row and stage_row.progress_available)
    stage_percent = stage_row.progress_percent if progress_available else None
    payload.update(
        {
            "stage_code": stage,
            "step_number": stage_row.step_number if stage_row else step_number,
            "stage_label": stage_row.stage_label if stage_row else fallback_label,
            "stage_status": stage_row.stage_status
            if stage_row
            else _fallback_stage_status(run.status),
            "progress_available": progress_available,
            "progress_percent": stage_percent,
            "completed_units": stage_row.completed_units if stage_row else None,
            "total_units": stage_row.total_units if stage_row else None,
            "unit": stage_row.unit if stage_row else None,
            "current_item": stage_row.current_item if stage_row else None,
            "speed_bps": stage_row.speed_bps if stage_row else None,
            "eta_seconds": stage_row.eta_seconds if stage_row else None,
            "progress_source": stage_row.progress_source
            if stage_row
            else "stage-status-unavailable",
            "stage_updated_at": _iso(stage_row.updated_at) if stage_row else None,
            "current_airflow_stage": raw_stage,
            # Compatibility field for one release. WGS consumers must treat
            # null as indeterminate rather than fall back to Airflow task count.
            "percent": stage_percent,
        }
    )
    # A stage label is not a quantitative progress model. Until the runtime
    # emits an exact whole-analysis ETA, expose only the active stage ETA above.
    payload.update(
        {
            "analysis_eta_seconds": None,
            "analysis_eta_model": "runtime_exact_eta_unavailable",
            "analysis_eta_history_count": 0,
        }
    )
    active = session.scalar(select(RuleState).where(RuleState.analysis_id == run.analysis_id, RuleState.status == "running").order_by(RuleState.updated_at.desc()))
    current_rule = active.rule_name if active else payload.get("current_rule")
    if not current_rule:
        master = session.scalar(
            select(KubernetesWorkload)
            .where(
                KubernetesWorkload.analysis_id == run.analysis_id,
                KubernetesWorkload.attempt == run.attempt,
                KubernetesWorkload.event_id.like("step3:%"),
            )
            .order_by(KubernetesWorkload.updated_at.desc())
        )
        if master is not None:
            status = master.job_status_json or {}
            current_rule = str(status.get("current_rule") or "").strip() or None
    payload["current_rule"] = current_rule
    if not payload.get("current_item") and current_rule:
        payload["current_item"] = current_rule
    return payload


def _canonical_stage(stage: str, run_status: str | None) -> str:
    if str(run_status or "").lower() == "success":
        return "final"
    aliases = {
        "validate_request": "prepare",
        "prepare_wgs_batch": "prepare",
        "acquire_input_transfer_slot": "step1_upload",
        "release_input_transfer_slot": "step1_upload",
        "wait_step1_upload": "step1_upload",
        "submit_step2_master": "step2_master",
        "start_step3_monitor": "step3_monitor",
        "wait_step3_analysis": "step3_monitor",
        "wait_step4_publish": "step4_publish",
        "acquire_result_transfer_slot": "step5_download",
        "release_result_transfer_slot": "step5_download",
        "wait_step5_download": "step5_download",
        "materialize_step6_results": "step6_materialize",
        "finalize_run": "final",
    }
    return aliases.get(stage, stage if stage in STAGE_DEFINITIONS else "prepare")


def _fallback_stage_status(run_status: str | None) -> str:
    value = str(run_status or "created").lower()
    if value in {"failed", "cancelled", "unknown_interrupted"}:
        return "failed"
    if value == "success":
        return "success"
    if value in {"created", "submitted", "queued"}:
        return "pending"
    return "running"


def _history_runs(session, run: AnalysisRun) -> list[AnalysisRun]:
    release_id = str((run.params_json or {}).get("pipeline_release_id") or "")
    if not release_id:
        return []
    return session.scalars(
        select(AnalysisRun)
        .where(
            AnalysisRun.pipeline_name == "wgs",
            AnalysisRun.execution_mode == run.execution_mode,
            AnalysisRun.status == "success",
            AnalysisRun.params_json["pipeline_release_id"].as_string()
            == release_id,
        )
        .order_by(AnalysisRun.ended_at.desc())
        .limit(20)
    ).all()


def _rule_durations(session, runs, rule_name, layer) -> list[float]:
    ids = [run.analysis_id for run in runs]
    if not ids:
        return []
    rows = session.scalars(select(RuleState).where(RuleState.analysis_id.in_(ids), RuleState.rule_name == rule_name, RuleState.status == "success")).all()
    return [_seconds(row.started_at, row.ended_at) for row in rows if row.started_at and row.ended_at and (layer is None or row.layer == layer)]


def _seconds(start, end) -> float:
    return max(0.0, (end - start).total_seconds())


def _iso(value):
    return value.isoformat() if value else None
