from __future__ import annotations

from datetime import datetime, timezone
from statistics import median

from sqlalchemy import select

from app.models import AnalysisRun, RuleState


def serialize_rule_states(*, session, run: AnalysisRun, rows: list[RuleState]) -> list[dict]:
    now = datetime.now(timezone.utc)
    history_runs = _history_runs(session, run)
    items = []
    for row in rows:
        durations = _rule_durations(session, history_runs, row.rule_name, row.layer)
        history_median = median(durations) if len(durations) >= 3 else None
        elapsed = _seconds(row.started_at, row.ended_at or now) if row.started_at else None
        remaining = max(0.0, history_median - elapsed) if history_median is not None and elapsed is not None and row.status == "running" else None
        items.append({"attempt": row.attempt, "rule_instance_id": row.rule_instance_id, "rule": row.rule_name, "sample_id": row.sample_id, "layer": row.layer, "status": row.status, "start_time": _iso(row.started_at), "end_time": _iso(row.ended_at), "elapsed_seconds": elapsed, "historical_median_seconds": history_median, "estimated_remaining_seconds": remaining, "eta_history_count": len(durations), "eta_model": "rule_wall_median_v1" if len(durations) >= 3 else "insufficient_history"})
    return items


def enrich_progress(*, session, run: AnalysisRun, payload: dict) -> dict:
    stage = str(run.current_stage or payload.get("current_step") or "created")
    payload.update({"current_airflow_stage": stage, "overall_progress_percent": _stage_percent(stage)})
    history = _history_runs(session, run)
    totals = [_seconds(item.started_at, item.pipeline_finished_at or item.ended_at) for item in history if item.started_at and (item.pipeline_finished_at or item.ended_at)]
    totals = totals[-20:]
    if len(totals) < 3:
        payload.update({"analysis_eta_seconds": None, "analysis_eta_model": "insufficient_history", "analysis_eta_history_count": len(totals)})
    else:
        baseline = float(median(totals))
        percent = float(payload["overall_progress_percent"])
        payload.update({"analysis_eta_seconds": max(0, int(baseline * (100 - percent) / 100)), "analysis_eta_model": "snapshot_stage_wall_median_v1", "analysis_eta_history_count": len(totals)})
    active = session.scalar(select(RuleState).where(RuleState.analysis_id == run.analysis_id, RuleState.status == "running").order_by(RuleState.updated_at.desc()))
    payload["current_rule"] = active.rule_name if active else payload.get("current_rule")
    return payload


def _history_runs(session, run: AnalysisRun) -> list[AnalysisRun]:
    snapshot = str((run.params_json or {}).get("pipeline_snapshot_id") or "")
    rows = session.scalars(select(AnalysisRun).where(AnalysisRun.pipeline_name == "wgs", AnalysisRun.execution_mode == run.execution_mode, AnalysisRun.status == "success").order_by(AnalysisRun.ended_at.desc()).limit(20)).all()
    return [item for item in rows if str((item.params_json or {}).get("pipeline_snapshot_id") or "") == snapshot]


def _rule_durations(session, runs, rule_name, layer) -> list[float]:
    ids = [run.analysis_id for run in runs]
    if not ids:
        return []
    rows = session.scalars(select(RuleState).where(RuleState.analysis_id.in_(ids), RuleState.rule_name == rule_name, RuleState.status == "success")).all()
    return [_seconds(row.started_at, row.ended_at) for row in rows if row.started_at and row.ended_at and (layer is None or row.layer == layer)]


def _stage_percent(stage: str) -> int:
    values = {
        "created": 0,
        "validate_request": 3,
        "prepare": 8,
        "acquire_input_transfer_slot": 12,
        "step1_upload": 20,
        "release_input_transfer_slot": 30,
        "step2_master": 33,
        "step3_monitor": 55,
        "step4_publish": 87,
        "acquire_result_transfer_slot": 90,
        "step5_download": 94,
        "release_result_transfer_slot": 97,
        "step6_materialize": 99,
        "finalize_run": 100,
        "success": 100,
    }
    return values.get(stage, 0)


def _seconds(start, end) -> float:
    return max(0.0, (end - start).total_seconds())


def _iso(value):
    return value.isoformat() if value else None
