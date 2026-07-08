from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisRun
from app.rule_event_service import list_snakemake_rule_events


TASK_WEIGHTS: dict[str, dict[str, int]] = {
    "bio_pgta": {
        "validate_request": 5,
        "prepare_pgta_config": 15,
        "run_pgta_target": 90,
        "collect_pgta_artifact": 100,
    },
    "bio_nipt_docker": {
        "validate_request": 5,
        "prepare_nipt_docker_run": 15,
        "run_nipt_docker": 90,
        "collect_nipt_artifacts": 100,
    },
}

RUN_TASK_IDS = {
    "bio_pgta": "run_pgta_target",
    "bio_nipt_docker": "run_nipt_docker",
}

ACTIVE_STATUSES = {"running", "queued", "scheduled", "submitted", "up_for_retry", "up_for_reschedule", "deferred"}
FAILED_STATUSES = {"failed", "fail", "error", "upstream_failed"}
TERMINAL_RULE_STATUSES = {"success", "failed", "fail", "error", "skipped", "canceled", "cancelled", "terminated"}


def get_run_progress(*, session: Session, airflow_client, analysis_id: str) -> dict[str, Any] | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    if run is None:
        return None

    rule_events = list_snakemake_rule_events(session=session, analysis_id=analysis_id) or []
    if not run.dag_id or not run.dag_run_id:
        return _created_or_unsubmitted_payload(run=run, rule_events=rule_events)

    task_payload = airflow_client.list_task_instances(run.dag_id, run.dag_run_id)
    airflow_tasks = _normalize_airflow_tasks(run.dag_id, task_payload.get("task_instances") or [])
    payload = _progress_from_tasks(run=run, airflow_tasks=airflow_tasks, rule_events=rule_events)
    payload["airflow_tasks"] = airflow_tasks
    payload["rule_events"] = rule_events
    return payload


def _created_or_unsubmitted_payload(*, run: AnalysisRun, rule_events: list[dict[str, Any]]) -> dict[str, Any]:
    status = _status(run.status)
    if status == "created":
        percent = 0
        current_step = "Created only"
        note = "Created in backend only"
        not_in_airflow = True
    elif status in {"submitted", "queued", "scheduled"}:
        percent = 5
        current_step = "Airflow handoff"
        note = "No dag_run_id returned yet"
        not_in_airflow = True
    elif status == "success":
        percent = 100
        current_step = "Workflow complete"
        note = "Backend terminal status without Airflow task timeline"
        not_in_airflow = False
    elif _is_failed(status):
        percent = _rule_percent(rule_events, default=50)
        current_step = _active_or_failed_rule(rule_events, prefer_failed=True) or "Failed"
        note = "Backend failed status without Airflow task timeline"
        not_in_airflow = False
    else:
        percent = _rule_percent(rule_events, default=0)
        current_step = _active_or_failed_rule(rule_events) or "Unknown"
        note = "Progress estimate"
        not_in_airflow = False
    return {
        **_base_payload(run),
        "percent": percent,
        "current_step": current_step,
        "current_source": "backend" if not rule_events else "snakemake_events",
        "note": note,
        "not_in_airflow": not_in_airflow,
        "progress_source": "estimate" if not rule_events else "snakemake_events",
        "airflow_tasks": [],
        "rule_events": rule_events,
    }


def _progress_from_tasks(
    *,
    run: AnalysisRun,
    airflow_tasks: list[dict[str, Any]],
    rule_events: list[dict[str, Any]],
) -> dict[str, Any]:
    status = _status(run.status)
    weights = TASK_WEIGHTS.get(str(run.dag_id or ""), {})
    failed_task = _first_task_with_status(airflow_tasks, FAILED_STATUSES)
    active_task = _first_task_with_status(airflow_tasks, ACTIVE_STATUSES)
    latest_task = failed_task or active_task or _latest_task_by_weight(airflow_tasks, weights)

    percent = _percent_from_airflow(status=status, task=latest_task, weights=weights)
    current_step = str((latest_task or {}).get("task_id") or _step_from_status(status))
    current_source = "airflow_task_instances"
    note = _note_from_airflow(status=status, task=latest_task)
    progress_source = "airflow_task_instances" if airflow_tasks else "estimate"

    run_task_id = RUN_TASK_IDS.get(str(run.dag_id or ""))
    task_id = str((latest_task or {}).get("task_id") or "")
    if rule_events and (task_id == run_task_id or status in {"running", "failed", "success"}):
        rule_step = _active_or_failed_rule(rule_events, prefer_failed=_is_failed(status))
        if rule_step:
            current_step = rule_step
            current_source = "snakemake_events"
        percent = _blend_rule_progress(status=status, rule_events=rule_events)
        note = f"Airflow task {run_task_id or task_id}; pipeline rule events captured"
        progress_source = "snakemake_events"

    if status == "success":
        percent = 100
        if not rule_events:
            current_step = "Workflow complete"
            note = "Airflow success"
    elif _is_failed(status):
        if failed_task:
            current_step = str(failed_task.get("task_id") or current_step)
            current_source = "airflow_task_instances"
            note = "Airflow task failed"
        failed_rule = _active_or_failed_rule(rule_events, prefer_failed=True)
        if failed_rule:
            current_step = failed_rule
            current_source = "snakemake_events"
            note = "Pipeline rule failed"
            progress_source = "snakemake_events"

    return {
        **_base_payload(run),
        "percent": max(0, min(100, percent)),
        "current_step": current_step,
        "current_source": current_source,
        "note": note,
        "not_in_airflow": False,
        "progress_source": progress_source,
    }


def _base_payload(run: AnalysisRun) -> dict[str, Any]:
    return {
        "analysis_id": run.analysis_id,
        "pipeline": run.pipeline_name,
        "status": run.status,
        "dag_id": run.dag_id,
        "dag_run_id": run.dag_run_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _normalize_airflow_tasks(dag_id: str | None, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weights = TASK_WEIGHTS.get(str(dag_id or ""), {})

    def sort_key(task: dict[str, Any]) -> tuple[int, str, str]:
        task_id = str(task.get("task_id") or "")
        return (weights.get(task_id, 1000), str(task.get("start_date") or ""), task_id)

    normalized = []
    for task in sorted(tasks, key=sort_key):
        normalized.append(
            {
                "task_id": str(task.get("task_id") or ""),
                "state": _status(task.get("state")),
                "start_date": task.get("start_date"),
                "end_date": task.get("end_date"),
                "duration": task.get("duration"),
                "try_number": task.get("try_number"),
                "operator": task.get("operator"),
            }
        )
    return normalized


def _percent_from_airflow(*, status: str, task: dict[str, Any] | None, weights: dict[str, int]) -> int:
    if status == "created":
        return 0
    if status in {"submitted", "queued", "scheduled"} and not task:
        return 10
    if status == "success":
        return 100
    if not task:
        return 50 if _is_failed(status) else 10

    task_id = str(task.get("task_id") or "")
    state = _status(task.get("state"))
    weight = weights.get(task_id, 50)
    if _is_failed(state):
        return max(5, min(99, weight))
    if state in ACTIVE_STATUSES:
        return _previous_weight(task_id, weights)
    return min(100, weight)


def _previous_weight(task_id: str, weights: dict[str, int]) -> int:
    current = weights.get(task_id)
    if current is None:
        return 15
    lower = [value for value in weights.values() if value < current]
    return max(lower) if lower else min(current, 5)


def _blend_rule_progress(*, status: str, rule_events: list[dict[str, Any]]) -> int:
    if status == "success":
        return 100
    if not rule_events:
        return 15
    terminal = sum(1 for item in rule_events if _status(item.get("status")) in TERMINAL_RULE_STATUSES)
    percent = 15 + int((terminal / len(rule_events)) * 75)
    if _is_failed(status):
        return max(15, min(95, percent))
    return max(15, min(90, percent))


def _rule_percent(rule_events: list[dict[str, Any]], *, default: int) -> int:
    if not rule_events:
        return default
    terminal = sum(1 for item in rule_events if _status(item.get("status")) in TERMINAL_RULE_STATUSES)
    return round((terminal / len(rule_events)) * 100)


def _active_or_failed_rule(rule_events: list[dict[str, Any]], *, prefer_failed: bool = False) -> str | None:
    candidates = list(rule_events)
    if prefer_failed:
        for item in candidates:
            if _is_failed(item.get("status")):
                return str(item.get("rule") or "")
    for item in candidates:
        if _status(item.get("status")) in ACTIVE_STATUSES:
            return str(item.get("rule") or "")
    for item in reversed(candidates):
        if item.get("rule"):
            return str(item["rule"])
    return None


def _first_task_with_status(tasks: list[dict[str, Any]], statuses: set[str]) -> dict[str, Any] | None:
    for task in tasks:
        if _status(task.get("state")) in statuses:
            return task
    return None


def _latest_task_by_weight(tasks: list[dict[str, Any]], weights: dict[str, int]) -> dict[str, Any] | None:
    if not tasks:
        return None
    return max(tasks, key=lambda task: weights.get(str(task.get("task_id") or ""), 0))


def _note_from_airflow(*, status: str, task: dict[str, Any] | None) -> str:
    if status == "success":
        return "Airflow success"
    if _is_failed(status):
        return "Airflow failed"
    if task and str(task.get("task_id") or "") in RUN_TASK_IDS.values() and _status(task.get("state")) in ACTIVE_STATUSES:
        return "waiting for pipeline events"
    if task:
        return f"Airflow task {task.get('task_id')} is {_status(task.get('state'))}"
    return "Airflow handoff"


def _step_from_status(status: str) -> str:
    if status == "success":
        return "Workflow complete"
    if _is_failed(status):
        return "Failed"
    if status in {"submitted", "queued", "scheduled"}:
        return "Airflow handoff"
    return status or "Unknown"


def _status(value: Any) -> str:
    return str(value or "unknown").strip().lower() or "unknown"


def _is_failed(value: Any) -> bool:
    return _status(value) in FAILED_STATUSES
