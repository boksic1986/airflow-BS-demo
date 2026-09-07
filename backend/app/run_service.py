from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping
from typing import Any, Callable

from sqlalchemy import String, case, cast, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Sample
from app.qc_highlights import qc_highlights_by_run
from app.workflow_summary_service import workflow_summaries_by_run


def list_runs(
    *,
    session: Session,
    pipeline: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    sort: str = "created_desc",
    limit: int = 50,
    offset: int = 0,
    deployed_pipelines: tuple[str, ...] = (),
    workflow_projectors: Mapping[str, Callable[..., dict[str, list[dict[str, Any]]]]] | None = None,
) -> dict:
    query = select(AnalysisRun)
    if pipeline == "deployed":
        query = query.where(AnalysisRun.pipeline_name.in_(deployed_pipelines))
    elif pipeline:
        query = query.where(AnalysisRun.pipeline_name == pipeline)
    if status:
        query = query.where(AnalysisRun.status == status)
    normalized_keyword = keyword.strip().lower() if keyword else ""
    if normalized_keyword:
        pattern = f"%{normalized_keyword}%"
        sample_match = (
            select(Sample.id)
            .where(
                Sample.analysis_id == AnalysisRun.analysis_id,
                or_(
                    func.lower(Sample.sample_id).like(pattern),
                    func.lower(Sample.family_id).like(pattern),
                ),
            )
            .exists()
        )
        query = query.where(
            or_(
                func.lower(AnalysisRun.analysis_id).like(pattern),
                func.lower(cast(AnalysisRun.params_json["project_name"].as_string(), String)).like(pattern),
                func.lower(cast(AnalysisRun.params_json["batch_no"].as_string(), String)).like(pattern),
                func.lower(cast(AnalysisRun.params_json["analysis_batch"].as_string(), String)).like(pattern),
                func.lower(cast(AnalysisRun.params_json["sequencing_batch"].as_string(), String)).like(pattern),
                sample_match,
            )
        )

    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    page = list(
        session.scalars(
            query.order_by(*_run_list_order(session=session, sort=sort)).limit(limit).offset(offset)
        ).all()
    )
    sample_rows = (
        session.execute(
            select(Sample.analysis_id, Sample.qc_status).where(
                Sample.analysis_id.in_([run.analysis_id for run in page])
            )
        ).all()
        if page
        else []
    )
    sample_qc: dict[str, list[str | None]] = {}
    for analysis_id, qc_status in sample_rows:
        sample_qc.setdefault(analysis_id, []).append(qc_status)
    qc_highlights = qc_highlights_by_run(session=session, runs=page)
    workflow_summaries = workflow_summaries_by_run(
        session=session,
        runs=page,
        projectors=workflow_projectors,
    )
    return {
        "items": [
            _run_list_payload(
                run,
                sample_count=len(sample_qc.get(run.analysis_id, [])),
                sample_qc_statuses=sample_qc.get(run.analysis_id, []),
                qc_highlights=qc_highlights.get(run.analysis_id, []),
                workflow_summary=workflow_summaries.get(run.analysis_id, []),
            )
            for run in page
        ],
        "total": total,
    }


def get_run_detail(*, session: Session, analysis_id: str) -> dict | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    return _run_detail_payload(session, run) if run is not None else None


def list_run_samples(*, session: Session, analysis_id: str) -> list[dict]:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    samples = session.scalars(
        select(Sample).where(Sample.analysis_id == analysis_id).order_by(Sample.sample_id)
    ).all()
    return [
        {
            "sample_id": sample.sample_id,
            "data_id": str((sample.metadata_json or {}).get("data_id") or sample.sample_id),
            "family_id": sample.family_id,
            "family_relation": str((sample.metadata_json or {}).get("family_relation") or "") or None,
            "sample_type": sample.sample_type,
            "sex": sample.sex,
            "sequencing_batch": str(
                (sample.metadata_json or {}).get("sequencing_batch")
                or ((run.params_json or {}).get("sequencing_batch") if run else "")
                or ""
            ) or None,
            "r1_filename": Path(sample.fq1).name if sample.fq1 else None,
            "r2_filename": Path(sample.fq2).name if sample.fq2 else None,
            "status": sample.status,
            "qc_status": sample.qc_status,
            "pending_source": str((sample.metadata_json or {}).get("pending_source") or "") or None,
            "pending_reason": str((sample.metadata_json or {}).get("pending_reason") or "") or None,
        }
        for sample in samples
    ]


def _run_payload(run: AnalysisRun, *, sample_count: int) -> dict:
    params = dict(run.params_json or {})
    params["batch_no"] = _public_batch(params)
    return {
        "analysis_id": run.analysis_id,
        "pipeline": run.pipeline_name,
        "dag_id": run.dag_id,
        "dag_run_id": run.dag_run_id,
        "status": run.status,
        "execution_mode": getattr(run, "execution_mode", None),
        "attempt": getattr(run, "attempt", 1),
        "workdir": run.workdir,
        "sample_count": sample_count,
        "params": params,
        "submitted_by": run.submitted_by,
        "submitted_at": run.submitted_at.isoformat() if run.submitted_at else None,
        "pipeline_finished_at": run.pipeline_finished_at.isoformat() if run.pipeline_finished_at else None,
    }


def _run_list_payload(
    run: AnalysisRun,
    *,
    sample_count: int,
    sample_qc_statuses: list[str | None],
    qc_highlights: list[dict],
    workflow_summary: list[dict[str, object]],
) -> dict:
    params = run.params_json or {}
    return {
        "analysis_id": run.analysis_id,
        "project_name": str(params.get("project_name") or run.analysis_id),
        "batch_no": _public_batch(params),
        "pipeline": run.pipeline_name,
        "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "submitted_at": run.submitted_at.isoformat() if run.submitted_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        "pipeline_finished_at": run.pipeline_finished_at.isoformat() if run.pipeline_finished_at else None,
        "submitted_by": run.submitted_by,
        "sample_count": sample_count,
        "qc_status": _aggregate_sample_qc_status(sample_qc_statuses),
        "qc_highlights": qc_highlights,
        "workflow_summary": workflow_summary,
    }


def _run_list_order(*, session: Session, sort: str):
    if sort == "duration_desc":
        if session.bind is not None and session.bind.dialect.name == "sqlite":
            duration = (func.julianday(func.coalesce(AnalysisRun.ended_at, func.current_timestamp())) - func.julianday(AnalysisRun.started_at)) * 86400
        else:
            duration = func.extract("epoch", func.coalesce(AnalysisRun.ended_at, func.now()) - AnalysisRun.started_at)
        return (desc(func.coalesce(duration, 0)), desc(AnalysisRun.created_at))
    if sort == "status":
        priority = {"running": 0, "submitted": 1, "queued": 2, "failed": 3, "created": 4, "success": 5}
        return (case(priority, value=AnalysisRun.status, else_=99), desc(AnalysisRun.created_at))
    return (desc(AnalysisRun.created_at),)


def _run_detail_payload(session: Session, run: AnalysisRun) -> dict:
    payload = _run_payload(
        run,
        sample_count=session.scalar(
            select(func.count()).select_from(Sample).where(Sample.analysis_id == run.analysis_id)
        ) or 0,
    )
    payload.update(
        {
            "mode": run.mode,
            "sample_sheet_path": run.sample_sheet_path,
            "airflow_url": run.airflow_url,
            "error_summary": run.error_summary,
            "email_to": run.email_to,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        }
    )
    return payload


def _aggregate_sample_qc_status(statuses: list[str | None]) -> str:
    normalized = {str(item or "unknown").strip().lower() or "unknown" for item in statuses}
    if not normalized:
        return "unknown"
    if normalized & {"fail", "failed", "error"}:
        return "fail"
    if normalized & {"warn", "warning", "qc_warning"}:
        return "warn"
    if normalized <= {"pass", "success"}:
        return "pass"
    return "unknown"


def _public_batch(params: dict) -> str | None:
    return str(
        params.get("analysis_batch")
        or params.get("sequencing_batch")
        or params.get("batch_no")
        or ""
    ) or None
