from __future__ import annotations

from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, RunStageState
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
        "name": "WGS 4.1.1 CCE",
        "dag_id": "bio_wgs",
        "runtime_profile_id": "resolved-by-wgs-prepare",
        "runtime": "External CCE Master / Snakemake",
    },
}


def get_workflow_catalog(*, session: Session, pipelines: tuple[str, ...] | list[str]) -> dict[str, list[dict[str, Any]]]:
    selected = [pipeline for pipeline in pipelines if pipeline in WORKFLOW_DEFINITIONS]
    if not selected:
        return {"items": []}
    deployed_filter = or_(*(_deployed_condition(pipeline) for pipeline in selected))
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
        for pipeline in selected
    }

    latest_runs = [run for run in latest_by_pipeline.values() if run is not None]
    summaries = workflow_summaries_by_run(session=session, runs=latest_runs)
    items: list[dict[str, Any]] = []
    for pipeline in selected:
        definition = WORKFLOW_DEFINITIONS[pipeline]
        latest = latest_by_pipeline.get(pipeline)
        stages = _wgs_stages(session, latest) if pipeline == "wgs" else (summaries.get(latest.analysis_id, []) if latest else _empty_stages(pipeline))
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
        return AnalysisRun.pipeline_name == pipeline
    raise ValueError(f"Unsupported deployed workflow: {pipeline}")


def _empty_stages(pipeline: str) -> list[dict[str, object]]:
    return [
        {"key": key, "label": label, "status": "pending", "completed_jobs": 0, "total_jobs": 0}
        for key, label in WORKFLOW_TEMPLATES[pipeline]
    ]


def _wgs_stages(session: Session, run: AnalysisRun | None) -> list[dict[str, object]]:
    definitions = [
        ("step1_upload", "Uploading FASTQ"),
        ("step2_master", "Starting WGS workflow"),
        ("step3_monitor", "WGS workflow running"),
        ("step4_publish", "Publishing WGS results"),
        ("step5_download", "Downloading WGS results"),
        ("step6_materialize", "Materializing local results"),
    ]
    states = {}
    if run is not None:
        states = {
            row.stage_code: row
            for row in session.scalars(
                select(RunStageState).where(
                    RunStageState.analysis_id == run.analysis_id,
                    RunStageState.attempt == run.attempt,
                )
            ).all()
        }
    return [
        {
            "key": key,
            "label": label,
            "status": states[key].stage_status if key in states else "pending",
            "completed_jobs": (states[key].completed_units or 0) if key in states else 0,
            "total_jobs": (states[key].total_units or 0) if key in states else 0,
            "progress_available": states[key].progress_available if key in states else False,
            "progress_percent": states[key].progress_percent if key in states else None,
        }
        for key, label in definitions
    ]


def _latest_run_payload(run: AnalysisRun | None, stages: list[dict[str, Any]]) -> dict[str, Any] | None:
    if run is None:
        return None
    current_stage = _current_stage_label(run=run, stages=stages)
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


def _current_stage_label(*, run: AnalysisRun, stages: list[dict[str, Any]]) -> str | None:
    for status in ("failed", "running"):
        matching = [str(stage["label"]) for stage in stages if stage["status"] == status]
        if matching:
            return matching[0]
    canceled = [str(stage["label"]) for stage in stages if stage["status"] == "canceled"]
    if canceled:
        return canceled[-1]
    return "Completed" if str(run.status or "").lower() == "success" else run.current_stage
