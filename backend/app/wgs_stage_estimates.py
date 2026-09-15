"""Display-only generation-fenced estimates; never author runtime progress."""
from datetime import datetime, timezone
from math import exp
from statistics import median

from sqlalchemy import select, func

from app.models import AnalysisRun, WgsStageExecution, PipelineStageExecution

STAGES = {"step4_publish", "step6_materialize"}
KEY = "_display_estimate_v1"


def freeze_stage_baseline(session, row):
    if row.stage_code not in STAGES or row.started_at is None or KEY in (row.terminal_payload_json or {}):
        return
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == row.analysis_id))
    if run is None:
        return
    model = PipelineStageExecution if isinstance(row, PipelineStageExecution) else WgsStageExecution
    history = session.scalars(select(model).join(AnalysisRun, AnalysisRun.analysis_id == model.analysis_id).where(
        AnalysisRun.pipeline_name == run.pipeline_name,
        AnalysisRun.execution_mode == run.execution_mode,
        func.coalesce(AnalysisRun.params_json["execution_target"].as_string(), AnalysisRun.execution_mode) == str((run.params_json or {}).get("execution_target") or run.execution_mode),
        model.release_id == row.release_id,
        model.stage_code == row.stage_code,
        model.execution_id != row.execution_id,
        model.status == "success",
        model.started_at.is_not(None),
        model.ended_at > model.started_at,
        model.ended_at <= row.started_at,
        *([model.pipeline_name == run.pipeline_name] if model is PipelineStageExecution else []),
    ).order_by(model.ended_at.desc(), model.id.desc()).limit(20)).all()
    values = [(_aware(h.ended_at) - _aware(h.started_at)).total_seconds() for h in history]
    row.terminal_payload_json = {**(row.terminal_payload_json or {}), KEY: {
        "baseline_seconds": median(values) if len(values) >= 3 else None,
        "history_count": len(values),
        "frozen_at": _aware(row.started_at).isoformat(),
        "execution_id": row.execution_id,
        "generation": row.generation,
        "history_execution_ids": [h.execution_id for h in history],
    }}


def stage_estimate(row, *, now=None, run_terminal=False, stopped_at=None):
    snapshot = (row.terminal_payload_json or {}).get(KEY, {}) if row else {}
    baseline = snapshot.get("baseline_seconds")
    linear = isinstance(row, WgsStageExecution)
    percent = None
    elapsed = None
    if row and row.status == "success":
        percent = 100
    elif row and row.started_at and baseline and row.status in {"running", "failed", "canceled", "cancelled", "terminated"}:
        stop = row.ended_at if row.status != "running" else stopped_at if run_terminal else now or datetime.now(timezone.utc)
        if stop is not None:
            elapsed = max(0, (_aware(stop) - _aware(row.started_at)).total_seconds())
            percent = min(99, round(elapsed / baseline * 100 if linear else 99 * (1 - exp(-elapsed / baseline)), 1))
    return {
        "estimated_progress_percent": percent,
        "estimate_baseline_seconds": baseline,
        "estimate_history_count": snapshot.get("history_count", 0),
        "estimate_model": "stage_median_linear_v1" if linear else "stage_median_eased_v1" if baseline else "insufficient_history",
        **({"estimate_elapsed_seconds": elapsed,
            "estimate_remaining_seconds": 0 if row.status == "success" else max(0, baseline - elapsed) if baseline and elapsed is not None else None} if linear else {}),
        "estimate_execution_id": row.execution_id if row else None,
        "estimate_generation": row.generation if row else None,
        "estimate_overrun": bool(elapsed is not None and baseline and elapsed >= baseline),
        "estimate_frozen": bool(row and (run_terminal or row.status in {"failed", "canceled", "cancelled", "terminated"})),
    }


def stage_estimates(session, run, *, now=None):
    model = PipelineStageExecution if run.pipeline_name == "gatk" else WgsStageExecution
    rows = session.scalars(select(model).where(model.analysis_id == run.analysis_id, model.attempt == run.attempt, model.stage_code.in_(STAGES), *([model.pipeline_name == run.pipeline_name] if model is PipelineStageExecution else [])).order_by(model.generation)).all()
    terminal = str(run.status or "").lower() in {"failed", "canceled", "cancelled", "terminated"}
    estimates = {r.stage_code: stage_estimate(r, now=now, run_terminal=terminal, stopped_at=run.pipeline_finished_at or run.ended_at) for r in rows}
    if run.pipeline_name == "wgs":
        for stage in STAGES:
            estimates.setdefault(stage, {**stage_estimate(None), "estimate_model": "stage_median_linear_v1"})
    return estimates


def attach_stage_estimates(session, run, payload, *, now=None):
    estimates = stage_estimates(session, run, now=now or datetime.now(timezone.utc))
    payload.update(estimates.get(payload.get("stage_code"), {}))
    for stage in payload.get("orchestration_stages", []):
        stage.update(estimates.get(stage["stage_code"], {}))
    return payload


def _aware(value):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
