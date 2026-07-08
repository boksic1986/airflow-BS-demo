from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, IntakeDiscovery, QcMetric, Sample, SnakemakeRuleEvent
from app.progress_service import get_run_progress


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
    "created": 6,
    "success": 7,
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
    if status:
        normalized_status = _status(status)
        if normalized_status == "active":
            base_query = base_query.where(AnalysisRun.status.in_(ACTIVE_STATUSES))
        elif normalized_status == "failed":
            base_query = base_query.where(AnalysisRun.status.in_(FAILED_STATUSES))
        else:
            base_query = base_query.where(AnalysisRun.status == normalized_status)

    runs = session.scalars(base_query.order_by(desc(AnalysisRun.created_at))).all()
    if keyword:
        needle = keyword.strip().lower()
        runs = [run for run in runs if needle in run.analysis_id.lower() or needle in _project_name(run).lower()]
    sorted_runs = sorted(runs, key=_run_sort_key)
    page = sorted_runs[offset : offset + limit]
    return {
        "items": [_tracker_row(session=session, airflow_client=airflow_client, run=run) for run in page],
        "total": len(sorted_runs),
        "limit": limit,
        "offset": offset,
        "pipeline": pipeline,
    }


def _tracker_row(*, session: Session, airflow_client, run: AnalysisRun) -> dict[str, Any]:
    progress = _progress_for_tracker_row(session=session, airflow_client=airflow_client, run=run)
    rules = progress.get("rule_events", []) if progress else []
    airflow_tasks = progress.get("airflow_tasks", []) if progress else []
    current_airflow_task = _current_airflow_task(airflow_tasks)
    current_pipeline_rule = _current_pipeline_rule(rules)
    elapsed_seconds = _elapsed_seconds(run)
    average_duration_seconds = _average_duration_seconds(session=session, run=run)
    estimated_remaining_seconds = _estimated_remaining_seconds(
        run=run,
        elapsed_seconds=elapsed_seconds,
        average_duration_seconds=average_duration_seconds,
    )
    estimated_finish_at = _estimated_finish_at(estimated_remaining_seconds)
    return {
        "analysis_id": run.analysis_id,
        "project_name": _project_name(run),
        "pipeline": run.pipeline_name,
        "status": run.status,
        "qc_status": _run_qc_status(session=session, analysis_id=run.analysis_id),
        "sample_count": session.scalar(select(func.count()).select_from(Sample).where(Sample.analysis_id == run.analysis_id)) or 0,
        "created_at": _iso(run.created_at),
        "started_at": _iso(run.started_at),
        "ended_at": _iso(run.ended_at),
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
        "estimated_remaining_seconds": estimated_remaining_seconds,
        "estimated_finish_at": _iso(estimated_finish_at),
        "progress_source": progress.get("progress_source", "estimate") if progress else "estimate",
        "not_in_airflow": progress.get("not_in_airflow", False) if progress else False,
        "note": progress.get("note", "") if progress else "",
    }


def _progress_for_tracker_row(*, session: Session, airflow_client, run: AnalysisRun) -> dict[str, Any]:
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
        rule_events = _latest_rule_events(session=session, analysis_id=run.analysis_id)
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
    return get_run_progress(session=session, airflow_client=airflow_client, analysis_id=run.analysis_id)


def _latest_rule_events(*, session: Session, analysis_id: str) -> list[dict[str, Any]]:
    rows = (
        session.execute(
            select(SnakemakeRuleEvent)
            .where(SnakemakeRuleEvent.analysis_id == analysis_id)
            .order_by(SnakemakeRuleEvent.updated_at)
        )
        .scalars()
        .all()
    )
    return [
        {
            "rule": row.rule,
            "sample_id": row.sample_id,
            "status": row.status,
            "message": row.message,
        }
        for row in rows
    ]


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
    query = select(IntakeDiscovery.ready_state, IntakeDiscovery.submit_state, func.count()).group_by(IntakeDiscovery.ready_state, IntakeDiscovery.submit_state)
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


def _run_qc_status(*, session: Session, analysis_id: str) -> str:
    statuses = [str(value or "unknown").lower() for value in session.scalars(select(Sample.qc_status).where(Sample.analysis_id == analysis_id)).all()]
    if not statuses:
        return "unknown"
    if any(status in {"failed", "fail", "error"} for status in statuses):
        return "fail"
    if any(status == "warn" for status in statuses):
        return "warn"
    if all(status == "pass" for status in statuses):
        return "pass"
    return "unknown"


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
        return "Workflow complete"
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
    return "Backend state"


def _elapsed_seconds(run: AnalysisRun) -> int | None:
    if not run.started_at:
        return None
    end = run.ended_at or datetime.now(timezone.utc)
    started_at = _as_aware(run.started_at)
    ended_at = _as_aware(end)
    return max(0, int((ended_at - started_at).total_seconds()))


def _average_duration_seconds(*, session: Session, run: AnalysisRun) -> int | None:
    kind_key, kind_value = _run_kind(run)
    query = (
        select(AnalysisRun)
        .where(
            AnalysisRun.pipeline_name == run.pipeline_name,
            AnalysisRun.status == "success",
            AnalysisRun.started_at.is_not(None),
            AnalysisRun.ended_at.is_not(None),
            AnalysisRun.analysis_id != run.analysis_id,
        )
        .order_by(desc(AnalysisRun.ended_at))
    )
    candidates = []
    for candidate in session.scalars(query).all():
        if _run_kind(candidate) == (kind_key, kind_value):
            candidates.append(candidate)
        if len(candidates) >= 10:
            break
    durations = [
        max(0, int((_as_aware(candidate.ended_at) - _as_aware(candidate.started_at)).total_seconds()))
        for candidate in candidates
        if candidate.started_at and candidate.ended_at
    ]
    if not durations:
        return None
    return int(sum(durations) / len(durations))


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


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _humanize_identifier(value: str | None) -> str:
    if not value:
        return "Unknown"
    label = value.split(".")[-1].replace("_", " ").strip()
    return label[:1].upper() + label[1:]


def _run_sort_key(run: AnalysisRun) -> tuple[int, float]:
    created = run.created_at.timestamp() if run.created_at else 0
    return (STATUS_ORDER.get(_status(run.status), 99), -created)


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
    return value.isoformat() if value else None


def _status(value: Any) -> str:
    return str(value or "unknown").strip().lower() or "unknown"
