from __future__ import annotations

from datetime import datetime, timezone
from statistics import median

from sqlalchemy import select

from app.models import AnalysisRun, KubernetesWorkload, RuleState, RunStageState
from app.diagnostics_service import wgs_rule_log_contexts
from app.workflow_phases import phase_for_rule, phase_order
from app.wgs_stage_contract import (
    canonical_wgs_stage,
    project_wgs_orchestration,
    wgs_stage_status_without_evidence,
    wgs_stage_definition,
)


def serialize_rule_states(*, session, run: AnalysisRun, rows: list[RuleState], settings=None) -> list[dict]:
    now = datetime.now(timezone.utc)
    history_runs = _history_runs(session, run)
    duration_history = _rule_duration_history(session, history_runs, rows)
    rule_logs = wgs_rule_log_contexts(run=run, rules=rows, settings=settings) if settings is not None else {}
    items = []
    for row in rows:
        phase = phase_for_rule(row.rule_name, pipeline_name="wgs")
        durations = duration_history.get((row.rule_name, row.layer), [])
        history_median = median(durations) if len(durations) >= 3 else None
        projected_status = row.status
        projected_ended_at = row.ended_at
        projected_message = row.message
        if (
            str(run.status or "").lower() == "success"
            and row.rule_name == "cloud_finalize_delivery"
            and str(row.status or "").lower() in {"planned", "submitted", "running", "started"}
        ):
            projected_status = "success"
            projected_ended_at = run.pipeline_finished_at or run.ended_at
            projected_message = (
                "Terminal event reconciled from the verified successful run."
            )
        elapsed = _seconds(row.started_at, projected_ended_at or now) if row.started_at else None
        remaining = max(0.0, history_median - elapsed) if history_median is not None and elapsed is not None and projected_status == "running" else None
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
                "status": projected_status,
                "message": projected_message,
                "log_keys": list(row.log_paths_json or []),
                "stderr_excerpt": (rule_logs.get(row.rule_instance_id) or {}).get("stderr_excerpt"),
                "analysis_log_key": (rule_logs.get(row.rule_instance_id) or {}).get("analysis_log_key"),
                "start_time": _iso(row.started_at),
                "end_time": _iso(projected_ended_at),
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
    stage = canonical_wgs_stage(raw_stage, run.status)
    stage_rows = session.scalars(
        select(RunStageState).where(
            RunStageState.analysis_id == run.analysis_id,
            RunStageState.attempt == run.attempt,
        )
    ).all()
    stage_row = next((row for row in stage_rows if row.stage_code == stage), None)
    stage_definition = wgs_stage_definition(stage)
    progress_available = bool(stage_row and stage_row.progress_available)
    stage_percent = stage_row.progress_percent if progress_available else None
    payload.update(
        {
            "stage_code": stage,
            "step_number": stage_row.step_number if stage_row else stage_definition.step_number,
            "stage_label": stage_row.stage_label if stage_row else stage_definition.label,
            "stage_status": stage_row.stage_status
            if stage_row
            else wgs_stage_status_without_evidence(run.status),
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
            "orchestration_stages": project_wgs_orchestration(
                run_status=run.status,
                current_stage=raw_stage,
                stage_rows=stage_rows,
            ),
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
    active = None if str(run.status or "").lower() == "success" else session.scalar(select(RuleState).where(RuleState.analysis_id == run.analysis_id, RuleState.status == "running").order_by(RuleState.updated_at.desc()))
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


def _rule_duration_history(session, runs, requested_rows) -> dict[tuple[str, int | None], list[float]]:
    ids = [run.analysis_id for run in runs]
    names = {row.rule_name for row in requested_rows}
    if not ids or not names:
        return {}
    rows = session.scalars(
        select(RuleState).where(
            RuleState.analysis_id.in_(ids),
            RuleState.rule_name.in_(names),
            RuleState.status == "success",
        )
    ).all()
    history: dict[tuple[str, int | None], list[float]] = {}
    for row in rows:
        if row.started_at and row.ended_at:
            history.setdefault((row.rule_name, row.layer), []).append(
                _seconds(row.started_at, row.ended_at)
            )
    return history


def _seconds(start, end) -> float:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(0.0, (end - start).total_seconds())


def _iso(value):
    return value.isoformat() if value else None
