from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.models import AnalysisRun

FAILED = {"failed", "fail", "error"}
RUNNING = {"planned", "submitted", "running", "started"}
COMPLETED = {"success", "skipped"}
CANCELED = {"canceled", "cancelled", "terminated"}


WorkflowProjector = Callable[..., dict[str, list[dict[str, Any]]]]


def workflow_summaries_by_run(
    *,
    session: Session,
    runs: list[AnalysisRun],
    projectors: Mapping[str, WorkflowProjector] | None = None,
) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {
        run.analysis_id: [] for run in runs
    }
    runs_by_pipeline: dict[str, list[AnalysisRun]] = {}
    for run in runs:
        runs_by_pipeline.setdefault(run.pipeline_name, []).append(run)
    for pipeline_id, pipeline_runs in runs_by_pipeline.items():
        projector = (projectors or {}).get(pipeline_id)
        if projector is None:
            continue
        result.update(projector(session=session, runs=pipeline_runs) or {})
    return result


def _stage_status(statuses: list[str]) -> str:
    if any(status in FAILED for status in statuses):
        return "failed"
    if any(status in RUNNING for status in statuses):
        return "running"
    if any(status in CANCELED for status in statuses):
        return "canceled"
    if statuses and all(status in COMPLETED for status in statuses):
        return "success"
    return "pending"
