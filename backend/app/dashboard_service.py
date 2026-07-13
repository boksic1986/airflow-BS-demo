from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

from sqlalchemy import String, case, cast, desc, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import AnalysisRun, IntakeDiscovery, QcMetric, Sample, SnakemakeRuleEvent
from app.progress_service import get_run_progress
from app.qc_highlights import qc_highlights_by_run


SUPPORTED_DASHBOARD_PIPELINES = {"all", "pgta", "nipt_docker"}
ACTIVE_STATUSES = {"running", "submitted", "queued", "scheduled"}
FAILED_STATUSES = {"failed", "fail", "error", "terminated"}
STATUS_ORDER = {
    "running": 0,
    "submitted": 1,
    "queued": 2,
    "scheduled": 3,
    "failed": 4,
    "terminated": 5,
    "success": 6,
    "created": 7,
}


def get_dashboard_overview(*, session: Session, pipeline: str, period: str) -> dict[str, Any]:
    _validate_pipeline(pipeline)
    since = _period_start(period)
    runs = _runs_for_pipeline(session=session, pipeline=pipeline, since=since)
    status_distribution = _status_distribution(runs)
    pipeline_breakdown = {}
    for name in ["pgta", "nipt_docker"]:
        pipeline_runs = [run for run in runs if run.pipeline_name == name]
        pipeline_breakdown[name] = {
            "runs": len(pipeline_runs),
            "running": sum(1 for run in pipeline_runs if _status(run.status) in ACTIVE_STATUSES),
            "failed": sum(1 for run in pipeline_runs if _status(run.status) in FAILED_STATUSES),
            "success": sum(1 for run in pipeline_runs if _status(run.status) == "success"),
        }
    return {
        "pipeline": pipeline,
        "period": period,
        "totals": {
            "runs": len(runs),
            "running": sum(1 for run in runs if _status(run.status) in ACTIVE_STATUSES),
            "failed": sum(1 for run in runs if _status(run.status) in FAILED_STATUSES),
            "success": sum(1 for run in runs if _status(run.status) == "success"),
            "created": sum(1 for run in runs if _status(run.status) == "created"),
        },
        "status_distribution": status_distribution,
        "pipeline_breakdown": pipeline_breakdown,
        "trend": _daily_trend(runs, since=since),
        "qc_summary": _qc_summary(session=session, pipeline=pipeline, since=since),
        "sample_summary": _sample_summary(session=session, pipeline=pipeline, since=since),
        "sample_trend": _sample_trend(session=session, pipeline=pipeline, since=since),
        "failure_summary": _failure_summary(runs),
        "intake_summary": _intake_summary(session=session, pipeline=pipeline),
    }


def get_dashboard_runs(
    *,
    session: Session,
    airflow_client,
    pipeline: str,
    status: str | None,
    keyword: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    _validate_pipeline(pipeline)
    base_query = select(AnalysisRun)
    if pipeline != "all":
        base_query = base_query.where(AnalysisRun.pipeline_name == pipeline)
    else:
        base_query = base_query.where(AnalysisRun.pipeline_name.in_(["pgta", "nipt_docker"]))
    qc_failed = (
        select(Sample.id)
        .where(
            Sample.analysis_id == AnalysisRun.analysis_id,
            func.lower(Sample.qc_status).in_(["fail", "failed", "error"]),
        )
        .exists()
    )
    if status:
        normalized_status = _status(status)
        if normalized_status == "active":
            base_query = base_query.where(AnalysisRun.status.in_(ACTIVE_STATUSES))
        elif normalized_status == "failed":
            base_query = base_query.where(or_(AnalysisRun.status.in_(FAILED_STATUSES), qc_failed))
        elif normalized_status == "success":
            base_query = base_query.where(AnalysisRun.status == "success", ~qc_failed)
        else:
            base_query = base_query.where(AnalysisRun.status == normalized_status)

    if keyword:
        pattern = f"%{keyword.strip().lower()}%"
        base_query = base_query.where(
            or_(
                func.lower(AnalysisRun.analysis_id).like(pattern),
                func.lower(cast(AnalysisRun.params_json, String)).like(pattern),
            )
        )
    total = session.scalar(select(func.count()).select_from(base_query.order_by(None).subquery())) or 0
    status_order = case(
        (AnalysisRun.status.in_(ACTIVE_STATUSES), 0),
        (or_(AnalysisRun.status.in_(FAILED_STATUSES), qc_failed), 1),
        (AnalysisRun.status == "success", 2),
        (AnalysisRun.status == "created", 3),
        else_=4,
    )
    page = list(
        session.scalars(
            base_query.order_by(
                status_order,
                desc(AnalysisRun.progress_percent),
                AnalysisRun.submitted_at.asc().nulls_last(),
                desc(AnalysisRun.ended_at),
                desc(AnalysisRun.created_at),
            ).limit(limit).offset(offset)
        ).all()
    )
    sample_qc = _sample_qc_by_run(session=session, runs=page)
    rule_events = _rule_events_by_run(session=session, runs=page)
    duration_estimates = _duration_estimates_by_run(session=session, runs=page, sample_qc=sample_qc)
    qc_highlights = qc_highlights_by_run(session=session, runs=page)
    return {
        "items": [
            _tracker_row(
                session=session,
                airflow_client=airflow_client,
                run=run,
                sample_qc_statuses=sample_qc.get(run.analysis_id, []),
                persisted_rule_events=rule_events.get(run.analysis_id, []),
                duration_estimate=duration_estimates.get(run.analysis_id),
                qc_highlights=qc_highlights.get(run.analysis_id, []),
            )
            for run in page
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "pipeline": pipeline,
    }


def _tracker_row(
    *,
    session: Session,
    airflow_client,
    run: AnalysisRun,
    sample_qc_statuses: list[str | None],
    persisted_rule_events: list[dict[str, Any]],
    duration_estimate: dict[str, Any] | None,
    qc_highlights: list[dict[str, Any]],
) -> dict[str, Any]:
    progress = _progress_for_tracker_row(
        session=session,
        airflow_client=airflow_client,
        run=run,
        persisted_rule_events=persisted_rule_events,
    )
    rules = progress.get("rule_events", []) if progress else []
    airflow_tasks = progress.get("airflow_tasks", []) if progress else []
    terminal_success = _status(run.status) == "success"
    current_airflow_task = None if terminal_success else _current_airflow_task(airflow_tasks)
    current_pipeline_rule = None if terminal_success else _current_pipeline_rule(rules)
    elapsed_seconds = _elapsed_seconds(run)
    average_duration_seconds = int(duration_estimate["seconds"]) if duration_estimate else None
    estimated_remaining_seconds = _estimated_remaining_seconds(
        run=run,
        elapsed_seconds=elapsed_seconds,
        average_duration_seconds=average_duration_seconds,
    )
    estimated_finish_at = _estimated_finish_at(estimated_remaining_seconds)
    qc_status = _qc_status_from_values(sample_qc_statuses)
    qc_display_status, qc_display_note = _qc_display_state(run_status=run.status, qc_status=qc_status)
    params = run.params_json or {}
    return {
        "analysis_id": run.analysis_id,
        "project_name": _project_name(run),
        "pipeline": run.pipeline_name,
        "status": run.status,
        "display_status": _display_status(run_status=run.status, qc_status=qc_status),
        "qc_status": qc_status,
        "qc_display_status": qc_display_status,
        "qc_display_note": qc_display_note,
        "run_source": "intake" if params.get("intake_request_id") else "manual",
        "source_batch_id": str(
            params.get("intake_request_id")
            or params.get("source_batch_id")
            or params.get("chip_name")
            or ""
        ) or None,
        "sample_count": len(sample_qc_statuses),
        "created_at": _iso(run.created_at),
        "submitted_at": _iso(run.submitted_at),
        "submitted_by": run.submitted_by,
        "started_at": _iso(run.started_at),
        "ended_at": _iso(run.ended_at),
        "pipeline_finished_at": _iso(run.pipeline_finished_at),
        "dag_id": run.dag_id,
        "dag_run_id": run.dag_run_id,
        "percent": progress.get("percent", 0) if progress else 0,
        "current_airflow_task": current_airflow_task,
        "current_pipeline_rule": current_pipeline_rule,
        "current_stage_label": _current_stage_label(
            current_airflow_task=current_airflow_task,
            current_pipeline_rule=current_pipeline_rule,
            status=run.status,
            not_in_airflow=progress.get("not_in_airflow", False) if progress else False,
        ),
        "current_stage_source": _current_stage_source(
            current_airflow_task=current_airflow_task,
            current_pipeline_rule=current_pipeline_rule,
            not_in_airflow=progress.get("not_in_airflow", False) if progress else False,
        ),
        "elapsed_seconds": elapsed_seconds,
        "average_duration_seconds": average_duration_seconds,
        "eta_history_count": int(duration_estimate["history_count"]) if duration_estimate else 0,
        "eta_model": str(duration_estimate["model"]) if duration_estimate else None,
        "estimated_remaining_seconds": estimated_remaining_seconds,
        "estimated_finish_at": _iso(estimated_finish_at),
        "progress_source": progress.get("progress_source", "estimate") if progress else "estimate",
        "not_in_airflow": progress.get("not_in_airflow", False) if progress else False,
        "note": progress.get("note", "") if progress else "",
        "qc_highlights": qc_highlights,
    }


def _progress_for_tracker_row(
    *,
    session: Session,
    airflow_client,
    run: AnalysisRun,
    persisted_rule_events: list[dict[str, Any]],
) -> dict[str, Any]:
    status = _status(run.status)
    if status == "created":
        return {
            "percent": 0,
            "current_step": "Created only",
            "current_source": "estimate",
            "note": "Created in backend only; not visible in Airflow until submitted",
            "not_in_airflow": True,
            "progress_source": "estimate",
            "airflow_tasks": [],
            "rule_events": [],
        }
    if status == "success":
        rule_events = persisted_rule_events
        return {
            "percent": 100,
            "current_step": "Workflow complete",
            "current_source": "snakemake_events" if rule_events else "estimate",
            "note": "Workflow complete",
            "not_in_airflow": False,
            "progress_source": "snakemake_events" if rule_events else "estimate",
            "airflow_tasks": [],
            "rule_events": rule_events,
        }
    if status in FAILED_STATUSES:
        rule_events = persisted_rule_events
        return {
            "percent": 90 if rule_events else 10,
            "current_step": _current_pipeline_rule(rule_events) or "Workflow failed",
            "current_source": "snakemake_events" if rule_events else "estimate",
            "note": "Workflow failed; open run detail for Airflow task attempts and stderr.",
            "not_in_airflow": False,
            "progress_source": "snakemake_events" if rule_events else "estimate",
            "airflow_tasks": [],
            "rule_events": rule_events,
        }
    return get_run_progress(session=session, airflow_client=airflow_client, analysis_id=run.analysis_id)


def _sample_qc_by_run(*, session: Session, runs: list[AnalysisRun]) -> dict[str, list[str | None]]:
    run_ids = [run.analysis_id for run in runs]
    if not run_ids:
        return {}
    values: dict[str, list[str | None]] = {}
    for analysis_id, qc_status in session.execute(
        select(Sample.analysis_id, Sample.qc_status).where(Sample.analysis_id.in_(run_ids))
    ).all():
        values.setdefault(analysis_id, []).append(qc_status)
    return values


def _rule_events_by_run(*, session: Session, runs: list[AnalysisRun]) -> dict[str, list[dict[str, Any]]]:
    run_ids = [run.analysis_id for run in runs if _status(run.status) not in ACTIVE_STATUSES | {"created"}]
    if not run_ids:
        return {}
    values: dict[str, list[dict[str, Any]]] = {}
    rows = session.scalars(
        select(SnakemakeRuleEvent)
        .where(SnakemakeRuleEvent.analysis_id.in_(run_ids))
        .order_by(SnakemakeRuleEvent.analysis_id, SnakemakeRuleEvent.updated_at)
    ).all()
    for row in rows:
        values.setdefault(row.analysis_id, []).append(
            {"rule": row.rule, "sample_id": row.sample_id, "status": row.status, "message": row.message}
        )
    return values


def _duration_estimates_by_run(
    *,
    session: Session,
    runs: list[AnalysisRun],
    sample_qc: dict[str, list[str | None]],
) -> dict[str, dict[str, Any]]:
    keys = {_run_history_key(run) for run in runs}
    pipelines = {run.pipeline_name for run in runs}
    if not keys:
        return {}
    histories: dict[tuple[str, str, str, str], list[tuple[int, int]]] = {}
    failed_sample = aliased(Sample)
    counted_sample = aliased(Sample)
    failed_qc = (
        select(failed_sample.id)
        .where(
            failed_sample.analysis_id == AnalysisRun.analysis_id,
            func.lower(failed_sample.qc_status).in_(["fail", "failed", "error"]),
        )
        .exists()
    )
    candidates = session.execute(
        select(AnalysisRun, func.count(counted_sample.id).label("sample_count"))
        .join(counted_sample, counted_sample.analysis_id == AnalysisRun.analysis_id)
        .where(
            AnalysisRun.pipeline_name.in_(pipelines),
            AnalysisRun.status == "success",
            AnalysisRun.mode == "new",
            AnalysisRun.submitted_at.is_not(None),
            AnalysisRun.pipeline_finished_at.is_not(None),
            ~failed_qc,
        )
        .group_by(AnalysisRun.id)
        .order_by(desc(AnalysisRun.ended_at))
        .limit(500)
    ).all()
    for candidate, sample_count in candidates:
        key = _run_history_key(candidate)
        if key not in keys or len(histories.get(key, [])) >= 20:
            continue
        if candidate.submitted_at and candidate.pipeline_finished_at and sample_count:
            duration = max(
                0,
                int(
                    (
                        _as_aware(candidate.pipeline_finished_at)
                        - _as_aware(candidate.submitted_at)
                    ).total_seconds()
                ),
            )
            histories.setdefault(key, []).append((int(sample_count), duration))

    estimates: dict[str, dict[str, Any]] = {}
    for run in runs:
        values = histories.get(_run_history_key(run), [])
        estimate = _estimate_duration(values=values, sample_count=len(sample_qc.get(run.analysis_id, [])))
        if estimate is not None:
            estimates[run.analysis_id] = estimate
    return estimates


def _estimate_duration(*, values: list[tuple[int, int]], sample_count: int) -> dict[str, Any] | None:
    if not values or sample_count <= 0:
        return None
    exact = [duration for count, duration in values if count == sample_count]
    if exact:
        return {
            "seconds": int(median(exact)),
            "history_count": len(values),
            "model": "exact_sample_count",
        }

    distinct_counts = {count for count, _ in values}
    if len(distinct_counts) >= 2:
        mean_count = sum(count for count, _ in values) / len(values)
        mean_duration = sum(duration for _, duration in values) / len(values)
        variance = sum((count - mean_count) ** 2 for count, _ in values)
        slope = 0.0 if variance == 0 else max(
            0.0,
            sum((count - mean_count) * (duration - mean_duration) for count, duration in values) / variance,
        )
        intercept = max(0.0, mean_duration - slope * mean_count)
        return {
            "seconds": int(round(intercept + slope * sample_count)),
            "history_count": len(values),
            "model": "linear_sample_count",
        }

    baseline_count = values[0][0]
    baseline_duration = int(median([duration for _, duration in values]))
    scale = min(2.0, max(0.5, sample_count / baseline_count))
    return {
        "seconds": int(round(baseline_duration * scale)),
        "history_count": len(values),
        "model": "scaled_sample_count",
    }


def _runs_for_pipeline(*, session: Session, pipeline: str, since: datetime) -> list[AnalysisRun]:
    query = select(AnalysisRun).where(AnalysisRun.created_at >= since)
    if pipeline != "all":
        query = query.where(AnalysisRun.pipeline_name == pipeline)
    else:
        query = query.where(AnalysisRun.pipeline_name.in_(["pgta", "nipt_docker"]))
    return list(session.scalars(query).all())


def _qc_summary(*, session: Session, pipeline: str, since: datetime) -> dict[str, int]:
    query = (
        select(QcMetric.status, func.count())
        .join(AnalysisRun, AnalysisRun.analysis_id == QcMetric.analysis_id)
        .where(AnalysisRun.created_at >= since)
        .group_by(QcMetric.status)
    )
    if pipeline != "all":
        query = query.where(AnalysisRun.pipeline_name == pipeline)
    return _counts_from_rows(session.execute(query).all(), keys=["pass", "warn", "fail", "unknown"])


def _sample_summary(*, session: Session, pipeline: str, since: datetime) -> dict[str, int]:
    samples = _samples_for_period(session=session, pipeline=pipeline, since=since)
    return {
        "total": len(samples),
        "running": sum(1 for sample in samples if _status(sample.status) in ACTIVE_STATUSES),
        "workflow_failed": sum(1 for sample in samples if _status(sample.status) in FAILED_STATUSES),
        "qc_failed": sum(1 for sample in samples if _status(sample.qc_status) in FAILED_STATUSES),
        "completed": sum(1 for sample in samples if _status(sample.status) == "success"),
    }


def _sample_trend(*, session: Session, pipeline: str, since: datetime) -> list[dict[str, Any]]:
    query = (
        select(AnalysisRun.created_at, Sample.status, Sample.qc_status)
        .join(Sample, Sample.analysis_id == AnalysisRun.analysis_id)
        .where(AnalysisRun.created_at >= since)
    )
    if pipeline != "all":
        query = query.where(AnalysisRun.pipeline_name == pipeline)
    else:
        query = query.where(AnalysisRun.pipeline_name.in_(["pgta", "nipt_docker"]))
    buckets: dict[str, dict[str, int]] = {}
    for created_at, sample_status, qc_status in session.execute(query).all():
        key = (created_at or since).date().isoformat()
        bucket = buckets.setdefault(
            key,
            {
                "date": key,
                "total": 0,
                "running": 0,
                "workflow_failed": 0,
                "qc_failed": 0,
                "completed": 0,
            },
        )
        bucket["total"] += 1
        if _status(sample_status) in ACTIVE_STATUSES:
            bucket["running"] += 1
        if _status(sample_status) in FAILED_STATUSES:
            bucket["workflow_failed"] += 1
        if _status(qc_status) in FAILED_STATUSES:
            bucket["qc_failed"] += 1
        if _status(sample_status) == "success":
            bucket["completed"] += 1
    return [buckets[key] for key in sorted(buckets)]


def _samples_for_period(*, session: Session, pipeline: str, since: datetime) -> list[Sample]:
    query = (
        select(Sample)
        .join(AnalysisRun, AnalysisRun.analysis_id == Sample.analysis_id)
        .where(AnalysisRun.created_at >= since)
    )
    if pipeline != "all":
        query = query.where(AnalysisRun.pipeline_name == pipeline)
    else:
        query = query.where(AnalysisRun.pipeline_name.in_(["pgta", "nipt_docker"]))
    return list(session.scalars(query).all())


def _intake_summary(*, session: Session, pipeline: str) -> dict[str, int]:
    query = (
        select(IntakeDiscovery.ready_state, IntakeDiscovery.submit_state, func.count())
        .where(IntakeDiscovery.archived_at.is_(None))
        .group_by(IntakeDiscovery.ready_state, IntakeDiscovery.submit_state)
    )
    if pipeline != "all":
        query = query.where(IntakeDiscovery.pipeline_name == pipeline)
    summary = {"observed": 0, "ready": 0, "submitted": 0, "bootstrap": 0, "error": 0, "disabled": 0}
    for ready_state, submit_state, count in session.execute(query).all():
        ready_state = _status(ready_state)
        submit_state = _status(submit_state)
        if submit_state == "submitted":
            summary["submitted"] += count
        elif submit_state == "bootstrap":
            summary["bootstrap"] += count
        elif ready_state in summary:
            summary[ready_state] += count
    return summary


def _failure_summary(runs: list[AnalysisRun]) -> list[dict[str, Any]]:
    failures = [run for run in runs if _status(run.status) in FAILED_STATUSES]
    failures.sort(key=lambda run: run.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return [
        {
            "analysis_id": run.analysis_id,
            "pipeline": run.pipeline_name,
            "project_name": _project_name(run),
            "status": run.status,
            "error_summary": run.error_summary,
            "created_at": _iso(run.created_at),
        }
        for run in failures[:5]
    ]


def _daily_trend(runs: list[AnalysisRun], *, since: datetime) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, int]] = {}
    for run in runs:
        key = (run.created_at or since).date().isoformat()
        buckets.setdefault(key, {"date": key, "runs": 0, "failed": 0, "success": 0})
        buckets[key]["runs"] += 1
        if _status(run.status) in FAILED_STATUSES:
            buckets[key]["failed"] += 1
        if _status(run.status) == "success":
            buckets[key]["success"] += 1
    return [buckets[key] for key in sorted(buckets)]


def _status_distribution(runs: list[AnalysisRun]) -> dict[str, int]:
    counts = {"created": 0, "submitted": 0, "queued": 0, "running": 0, "success": 0, "failed": 0, "other": 0}
    for run in runs:
        status = _status(run.status)
        counts[status if status in counts else "other"] += 1
    return counts


def _counts_from_rows(rows, *, keys: list[str]) -> dict[str, int]:
    counts = {key: 0 for key in keys}
    for key, count in rows:
        key = _status(key)
        counts[key if key in counts else "unknown"] = count
    return counts


def _qc_status_from_values(values: list[str | None]) -> str:
    statuses = [str(value or "unknown").lower() for value in values]
    if not statuses:
        return "unknown"
    if any(status in {"failed", "fail", "error"} for status in statuses):
        return "fail"
    if any(status == "warn" for status in statuses):
        return "warn"
    if all(status == "pass" for status in statuses):
        return "pass"
    return "unknown"


def _display_status(*, run_status: str | None, qc_status: str) -> str:
    normalized_run = _status(run_status)
    if normalized_run in FAILED_STATUSES:
        return "failed"
    if normalized_run != "success":
        return normalized_run
    if qc_status == "fail":
        return "qc_failed"
    if qc_status == "warn":
        return "qc_warning"
    if qc_status == "unknown":
        return "qc_pending"
    return "success"


def _qc_display_state(*, run_status: str | None, qc_status: str) -> tuple[str, str]:
    normalized_run = _status(run_status)
    if qc_status in {"pass", "warn", "fail"}:
        return qc_status, "Sample QC is based on decision metrics."
    if normalized_run in ACTIVE_STATUSES | {"created"}:
        return "pending", "QC is available after the pipeline reaches its QC collection stage."
    if normalized_run in FAILED_STATUSES:
        return "unavailable", "The workflow ended before sample QC could be collected."
    return "unknown", "No decision QC metrics were captured for this run."


def _current_airflow_task(tasks: list[dict[str, Any]]) -> str | None:
    for task in tasks:
        if _status(task.get("state")) in ACTIVE_STATUSES | FAILED_STATUSES:
            return str(task.get("task_id") or "")
    for task in reversed(tasks):
        if task.get("task_id"):
            return str(task["task_id"])
    return None


def _current_pipeline_rule(rules: list[dict[str, Any]]) -> str | None:
    for rule in rules:
        if _status(rule.get("status")) in ACTIVE_STATUSES | FAILED_STATUSES:
            return str(rule.get("rule") or "")
    for rule in reversed(rules):
        if rule.get("rule"):
            return str(rule["rule"])
    return None


AIRFLOW_TASK_LABELS = {
    "validate_request": "Validate request",
    "prepare_pgta_config": "Prepare PGT-A config",
    "run_pgta_target": "Running PGT-A workflow",
    "pgta_pipeline.run_pgta_mapping": "Mapping reads",
    "pgta_pipeline.run_pgta_metadata": "Collect metadata",
    "pgta_pipeline.run_pgta_baseline_qc": "Baseline QC",
    "collect_pgta_artifact": "Collect PGT-A artifacts",
    "prepare_nipt_docker_run": "Prepare NIPT Docker run",
    "run_nipt_docker": "Run NIPT Docker workflow",
    "collect_nipt_artifacts": "Collect NIPT artifacts",
}

PIPELINE_RULE_LABELS = {
    "fastp": "FASTQ preprocessing",
    "mapping": "Mapping reads",
    "metadata": "Collect metadata",
    "baseline_qc": "Baseline QC",
    "baseline_bam_uniformity_qc": "Baseline BAM uniformity QC",
    "__airflow_demo_invalid_target__": "Demo invalid target",
    "nipt_mount_smoke": "NIPT mount smoke",
}


def _current_stage_label(
    *,
    current_airflow_task: str | None,
    current_pipeline_rule: str | None,
    status: str | None,
    not_in_airflow: bool,
) -> str:
    if not_in_airflow:
        return "Created only"
    if current_pipeline_rule:
        return PIPELINE_RULE_LABELS.get(current_pipeline_rule, _humanize_identifier(current_pipeline_rule))
    if current_airflow_task:
        return AIRFLOW_TASK_LABELS.get(current_airflow_task, _humanize_identifier(current_airflow_task))
    normalized = _status(status)
    if normalized == "success":
        return "Completed"
    if normalized in FAILED_STATUSES:
        return "Workflow failed"
    if normalized in ACTIVE_STATUSES:
        return "Airflow handoff"
    return _humanize_identifier(normalized)


def _current_stage_source(*, current_airflow_task: str | None, current_pipeline_rule: str | None, not_in_airflow: bool) -> str:
    if not_in_airflow:
        return "Backend state"
    if current_pipeline_rule:
        if current_pipeline_rule == "nipt_mount_smoke":
            return "Runner event"
        return "Snakemake rule event"
    if current_airflow_task:
        return "Airflow project task"
    return "Pipeline state" if not_in_airflow is False else "Backend state"


def _elapsed_seconds(run: AnalysisRun) -> int | None:
    if not run.submitted_at:
        return None
    terminal = _status(run.status) not in ACTIVE_STATUSES
    end = (run.pipeline_finished_at or run.ended_at) if terminal else datetime.now(timezone.utc)
    if end is None:
        end = datetime.now(timezone.utc)
    started_at = _as_aware(run.submitted_at)
    ended_at = _as_aware(end)
    return max(0, int((ended_at - started_at).total_seconds()))


def _estimated_remaining_seconds(*, run: AnalysisRun, elapsed_seconds: int | None, average_duration_seconds: int | None) -> int | None:
    if _status(run.status) not in ACTIVE_STATUSES:
        return None
    if elapsed_seconds is None or average_duration_seconds is None:
        return None
    return max(0, average_duration_seconds - elapsed_seconds)


def _estimated_finish_at(estimated_remaining_seconds: int | None) -> datetime | None:
    if estimated_remaining_seconds is None:
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=estimated_remaining_seconds)


def _run_kind(run: AnalysisRun) -> tuple[str, str]:
    params = run.params_json or {}
    if run.pipeline_name == "pgta":
        return ("target", str(params.get("target") or "metadata"))
    if run.pipeline_name == "nipt_docker":
        return ("run_mode", str(params.get("run_mode") or "mount_smoke"))
    return ("pipeline", str(run.pipeline_name))


def _run_history_key(run: AnalysisRun) -> tuple[str, str, str, str]:
    kind_key, kind_value = _run_kind(run)
    profile = str((run.params_json or {}).get("runtime_profile_id") or "legacy")
    return (run.pipeline_name, kind_key, kind_value, profile)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _humanize_identifier(value: str | None) -> str:
    if not value:
        return "Unknown"
    label = value.split(".")[-1].replace("_", " ").strip()
    return label[:1].upper() + label[1:]


def _project_name(run: AnalysisRun) -> str:
    params = run.params_json or {}
    value = params.get("project_name") or params.get("analysis_id") or run.analysis_id
    return str(value)


def _period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "24h":
        return now - timedelta(hours=24)
    if period == "30d":
        return now - timedelta(days=30)
    return now - timedelta(days=7)


def _validate_pipeline(pipeline: str) -> None:
    if pipeline not in SUPPORTED_DASHBOARD_PIPELINES:
        raise ValueError("pipeline must be all, pgta, or nipt_docker")


def _iso(value: datetime | None) -> str | None:
    return _as_aware(value).astimezone(timezone.utc).isoformat() if value else None


def _status(value: Any) -> str:
    return str(value or "unknown").strip().lower() or "unknown"
