from __future__ import annotations

from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models import AnalysisRun
from app.workflow_summary_service import WORKFLOW_TEMPLATES, workflow_summaries_by_run


WORKFLOW_DEFINITIONS: dict[str, dict[str, str]] = {
    "pgta": {
        "name": "PGT-A Predict",
        "dag_id": "bio_pgta",
        "runtime_profile_id": "pgta-s9-predict-v1",
        "runtime": "Snakemake 9.23.1",
    },
    "nipt_docker": {
        "name": "NIPT Docker Full",
        "dag_id": "bio_nipt_docker",
        "runtime_profile_id": "niptpro-s9-full-v1",
        "runtime": "Snakemake 9.23.1 in NIPTPro",
    },
    "wgs": {
        "name": "WGS Host Full",
        "dag_id": "bio_wgs",
        "runtime_profile_id": "wgs-s9-host-v1",
        "runtime": "Snakemake 9.23.1 on BS host",
    },
}


def get_workflow_catalog(*, session: Session) -> dict[str, list[dict[str, Any]]]:
    deployed_filter = or_(*(_deployed_condition(pipeline) for pipeline in WORKFLOW_DEFINITIONS))
    stats_rows = session.execute(
        select(
            AnalysisRun.pipeline_name,
            func.count(AnalysisRun.id),
            func.sum(case((func.lower(AnalysisRun.status) == "success", 1), else_=0)),
        )
        .where(deployed_filter)
        .group_by(AnalysisRun.pipeline_name)
    ).all()
    stats_by_pipeline = {
        pipeline: {"count": int(run_count), "successes": int(successes or 0)}
        for pipeline, run_count, successes in stats_rows
    }
    latest_by_pipeline = {
        pipeline: session.scalar(
            select(AnalysisRun)
            .where(_deployed_condition(pipeline))
            .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
            .limit(1)
        )
        for pipeline in WORKFLOW_DEFINITIONS
    }

    latest_runs = [run for run in latest_by_pipeline.values() if run is not None]
    summaries = workflow_summaries_by_run(session=session, runs=latest_runs)
    items: list[dict[str, Any]] = []
    for pipeline, definition in WORKFLOW_DEFINITIONS.items():
        latest = latest_by_pipeline.get(pipeline)
        stages = summaries.get(latest.analysis_id, []) if latest else _empty_stages(pipeline)
        stats = stats_by_pipeline.get(pipeline, {"count": 0, "successes": 0})
        items.append(
            {
                "pipeline": pipeline,
                **definition,
                "stages": stages,
                "latest_run": _latest_run_payload(latest, stages),
                "run_count": stats["count"],
                "success_rate": round(stats["successes"] / stats["count"], 4) if stats["count"] else None,
            }
        )
    return {"items": items}


def _deployed_condition(pipeline: str):
    if pipeline == "pgta":
        return and_(AnalysisRun.pipeline_name == pipeline, AnalysisRun.params_json["target"].as_string() == "predict")
    if pipeline == "nipt_docker":
        return and_(AnalysisRun.pipeline_name == pipeline, AnalysisRun.params_json["run_mode"].as_string() == "full_run")
    if pipeline == "wgs":
        return and_(AnalysisRun.pipeline_name == pipeline, AnalysisRun.params_json["wgs_stage"].as_string().in_(("precalling", "full")))
    raise ValueError(f"Unsupported deployed workflow: {pipeline}")


def _empty_stages(pipeline: str) -> list[dict[str, object]]:
    return [
        {"key": key, "label": label, "status": "pending", "completed_jobs": 0, "total_jobs": 0}
        for key, label in WORKFLOW_TEMPLATES[pipeline]
    ]


def _latest_run_payload(run: AnalysisRun | None, stages: list[dict[str, Any]]) -> dict[str, Any] | None:
    if run is None:
        return None
    current_stage = next(
        (stage["label"] for stage in stages if stage["status"] in {"failed", "running", "canceled"}),
        "Completed" if str(run.status or "").lower() == "success" else run.current_stage,
    )
    params = run.params_json or {}
    return {
        "analysis_id": run.analysis_id,
        "project_name": str(params.get("project_name") or run.analysis_id),
        "status": run.status,
        "current_stage": current_stage,
        "submitted_at": run.submitted_at.isoformat() if run.submitted_at else None,
        "finished_at": (run.pipeline_finished_at or run.ended_at).isoformat()
        if (run.pipeline_finished_at or run.ended_at)
        else None,
    }
