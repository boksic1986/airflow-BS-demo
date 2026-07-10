from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import String, cast, desc, func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from app.models import AnalysisRun, QcMetric, Sample, SnakemakeRuleEvent


FAILED_STATUSES = {"failed", "fail", "error", "terminated"}
ACTIVE_STATUSES = {"running", "submitted", "queued", "scheduled"}
STAGE_LABELS = {
    "mapping": "Mapping reads",
    "metadata": "Collect metadata",
    "baseline_qc": "Baseline QC",
    "baseline_bam_uniformity_qc": "Baseline BAM uniformity QC",
    "nipt_mount_smoke": "NIPT mount smoke",
}


def list_samples_resource(
    *,
    session: Session,
    pipeline: str | None,
    status: str | None,
    qc_status: str | None,
    keyword: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    query = select(Sample, AnalysisRun).join(
        AnalysisRun,
        AnalysisRun.analysis_id == Sample.analysis_id,
    )
    if pipeline and pipeline != "all":
        query = query.where(AnalysisRun.pipeline_name == pipeline)
    else:
        query = query.where(AnalysisRun.pipeline_name.in_(["pgta", "nipt_docker"]))
    if status:
        query = query.where(Sample.status == status)
    if qc_status:
        query = query.where(Sample.qc_status == qc_status)

    if keyword:
        pattern = f"%{keyword.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Sample.sample_id).like(pattern),
                func.lower(func.coalesce(Sample.family_id, "")).like(pattern),
                func.lower(AnalysisRun.analysis_id).like(pattern),
                func.lower(cast(AnalysisRun.params_json, String)).like(pattern),
            )
        )
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    page = list(
        session.execute(
            query.order_by(desc(AnalysisRun.created_at), Sample.sample_id).limit(limit).offset(offset)
        ).all()
    )
    return {
        "items": [_sample_item(sample=sample, run=run) for sample, run in page],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def list_failures_resource(
    *,
    session: Session,
    pipeline: str,
    kind: str,
    layer: str | None,
    period: str,
    keyword: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    since = _period_start(period)
    pattern = f"%{keyword.strip().lower()}%" if keyword else None
    failed_rule_exists = select(SnakemakeRuleEvent.id).where(
        SnakemakeRuleEvent.analysis_id == AnalysisRun.analysis_id,
        SnakemakeRuleEvent.status.in_(FAILED_STATUSES),
    ).exists()
    error_text = func.lower(func.coalesce(AnalysisRun.error_summary, ""))
    candidate_queries = []

    if kind in {"all", "workflow"} and layer != "qc":
        workflow_query = select(
            literal("workflow").label("failure_kind"),
            AnalysisRun.analysis_id.label("analysis_id"),
            cast(literal(None), String).label("sample_id"),
            AnalysisRun.created_at.label("created_at"),
        ).where(
            AnalysisRun.created_at >= since,
            AnalysisRun.status.in_(FAILED_STATUSES),
        )
        workflow_query = _filter_pipeline_runs(workflow_query, pipeline=pipeline)
        if pattern:
            rule_keyword_exists = select(SnakemakeRuleEvent.id).where(
                SnakemakeRuleEvent.analysis_id == AnalysisRun.analysis_id,
                or_(
                    func.lower(SnakemakeRuleEvent.rule).like(pattern),
                    func.lower(func.coalesce(SnakemakeRuleEvent.sample_id, "")).like(pattern),
                    func.lower(func.coalesce(SnakemakeRuleEvent.message, "")).like(pattern),
                ),
            ).exists()
            workflow_query = workflow_query.where(
                or_(
                    func.lower(AnalysisRun.analysis_id).like(pattern),
                    func.lower(cast(AnalysisRun.params_json, String)).like(pattern),
                    error_text.like(pattern),
                    rule_keyword_exists,
                )
            )
        if layer == "pipeline_rule":
            workflow_query = workflow_query.where(failed_rule_exists)
        elif layer == "runner":
            workflow_query = workflow_query.where(~failed_rule_exists, error_text.like("%docker%"))
        elif layer == "airflow":
            workflow_query = workflow_query.where(~failed_rule_exists, ~error_text.like("%docker%"))
        elif layer == "unknown":
            workflow_query = workflow_query.where(False)
        candidate_queries.append(workflow_query)

    if kind in {"all", "qc"} and layer in {None, "qc"}:
        qc_query = (
            select(
                literal("qc").label("failure_kind"),
                AnalysisRun.analysis_id.label("analysis_id"),
                Sample.sample_id.label("sample_id"),
                AnalysisRun.created_at.label("created_at"),
            )
            .join(AnalysisRun, AnalysisRun.analysis_id == Sample.analysis_id)
            .where(
                AnalysisRun.created_at >= since,
                Sample.qc_status.in_(["fail", "failed", "error"]),
            )
        )
        qc_query = _filter_pipeline_runs(qc_query, pipeline=pipeline)
        if pattern:
            metric_keyword_exists = select(QcMetric.id).where(
                QcMetric.analysis_id == AnalysisRun.analysis_id,
                QcMetric.sample_id == Sample.sample_id,
                or_(
                    func.lower(QcMetric.metric_name).like(pattern),
                    func.lower(func.coalesce(QcMetric.metric_value, "")).like(pattern),
                ),
            ).exists()
            qc_query = qc_query.where(
                or_(
                    func.lower(AnalysisRun.analysis_id).like(pattern),
                    func.lower(cast(AnalysisRun.params_json, String)).like(pattern),
                    func.lower(Sample.sample_id).like(pattern),
                    metric_keyword_exists,
                )
            )
        candidate_queries.append(qc_query)

    if not candidate_queries:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

    candidates = union_all(*candidate_queries).subquery()
    total = session.scalar(select(func.count()).select_from(candidates)) or 0
    candidate_rows = session.execute(
        select(
            candidates.c.failure_kind,
            candidates.c.analysis_id,
            candidates.c.sample_id,
            candidates.c.created_at,
        )
        .order_by(desc(candidates.c.created_at), candidates.c.analysis_id, candidates.c.sample_id)
        .limit(limit)
        .offset(offset)
    ).all()

    workflow_ids = [row.analysis_id for row in candidate_rows if row.failure_kind == "workflow"]
    workflow_runs = {
        run.analysis_id: run
        for run in session.scalars(select(AnalysisRun).where(AnalysisRun.analysis_id.in_(workflow_ids))).all()
    } if workflow_ids else {}
    failed_rules: dict[str, SnakemakeRuleEvent] = {}
    if workflow_ids:
        for rule in session.scalars(
            select(SnakemakeRuleEvent)
            .where(
                SnakemakeRuleEvent.analysis_id.in_(workflow_ids),
                SnakemakeRuleEvent.status.in_(FAILED_STATUSES),
            )
            .order_by(desc(SnakemakeRuleEvent.updated_at))
        ).all():
            failed_rules.setdefault(rule.analysis_id, rule)

    qc_pairs = {
        (row.analysis_id, row.sample_id)
        for row in candidate_rows
        if row.failure_kind == "qc" and row.sample_id is not None
    }
    qc_run_ids = list({analysis_id for analysis_id, _sample_id in qc_pairs})
    qc_rows = {
        (run.analysis_id, sample.sample_id): (sample, run)
        for sample, run in session.execute(
            select(Sample, AnalysisRun)
            .join(AnalysisRun, AnalysisRun.analysis_id == Sample.analysis_id)
            .where(AnalysisRun.analysis_id.in_(qc_run_ids))
        ).all()
        if (run.analysis_id, sample.sample_id) in qc_pairs
    } if qc_run_ids else {}
    metric_by_sample: dict[tuple[str, str | None], QcMetric] = {}
    if qc_run_ids:
        for metric in session.scalars(
            select(QcMetric)
            .where(QcMetric.analysis_id.in_(qc_run_ids), QcMetric.status.in_(["fail", "failed", "error"]))
            .order_by(desc(QcMetric.created_at))
        ).all():
            metric_by_sample.setdefault((metric.analysis_id, metric.sample_id), metric)

    items = []
    for candidate in candidate_rows:
        if candidate.failure_kind == "workflow":
            run = workflow_runs.get(candidate.analysis_id)
            if run is not None:
                items.append(_workflow_failure_item(run, failed_rules.get(run.analysis_id)))
            continue
        sample_run = qc_rows.get((candidate.analysis_id, candidate.sample_id))
        if sample_run is not None:
            sample, run = sample_run
            items.append(_qc_failure_item(sample, run, metric_by_sample.get((run.analysis_id, sample.sample_id))))
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _sample_item(*, sample: Sample, run: AnalysisRun) -> dict[str, Any]:
    metadata = sample.metadata_json or {}
    source_dir = str(metadata.get("source_dir") or "")
    if not source_dir:
        source_dir = str(PurePosixPath(str(sample.fq1 or "").replace("\\", "/")).parent)
    return {
        "analysis_id": run.analysis_id,
        "project_name": _project_name(run),
        "pipeline": run.pipeline_name,
        "sample_id": sample.sample_id,
        "family_id": sample.family_id,
        "status": sample.status,
        "qc_status": sample.qc_status,
        "source_folder": _basename(source_dir),
        "r1_name": _basename(sample.fq1),
        "r2_name": _basename(sample.fq2),
        "report_status": "available" if _status(run.status) == "success" else "not_generated",
    }


def _filter_pipeline_runs(query, *, pipeline: str):
    if pipeline == "all":
        return query.where(AnalysisRun.pipeline_name.in_(["pgta", "nipt_docker"]))
    return query.where(AnalysisRun.pipeline_name == pipeline)


def _workflow_failure_item(run: AnalysisRun, rule: SnakemakeRuleEvent | None) -> dict[str, Any]:
    error = _parse_error_summary(run.error_summary)
    failed_step = rule.rule if rule else str(error.get("failed_step") or "workflow")
    raw_excerpt = _stderr_excerpt(error, fallback=rule.message if rule else None)
    excerpt = _sanitize_excerpt(raw_excerpt)
    target = str((run.params_json or {}).get("target") or "")
    controlled_pgta = run.pipeline_name == "pgta" and target == "baseline_qc" and bool(run.dag_run_id) and bool(run.workdir)
    failure_layer = "pipeline_rule" if rule else ("runner" if "docker" in raw_excerpt.lower() else "airflow")
    return {
        "analysis_id": run.analysis_id,
        "project_name": _project_name(run),
        "pipeline": run.pipeline_name,
        "workflow_status": run.status,
        "qc_status": _run_qc_status_placeholder(),
        "failure_kind": "workflow",
        "failure_layer": failure_layer,
        "failed_step": failed_step,
        "failed_step_label": _stage_label(failed_step),
        "sample_id": rule.sample_id if rule else None,
        "return_code": rule.return_code if rule and rule.return_code is not None else error.get("return_code"),
        "stderr_excerpt": excerpt,
        "possible_reason": _possible_reason(raw_excerpt),
        "suggested_action_code": "resume_pgta" if controlled_pgta else "inspect_logs",
        "can_resume": controlled_pgta,
        "can_rerun_stage": controlled_pgta,
        "created_at": _iso(run.created_at),
    }


def _qc_failure_item(sample: Sample, run: AnalysisRun, metric: QcMetric | None) -> dict[str, Any]:
    failed_step = metric.metric_name if metric else "qc"
    value = metric.metric_value if metric else None
    threshold = metric.threshold if metric else None
    excerpt = f"{failed_step}: {value or 'failed'}"
    if threshold:
        excerpt += f"; threshold {threshold}"
    return {
        "analysis_id": run.analysis_id,
        "project_name": _project_name(run),
        "pipeline": run.pipeline_name,
        "workflow_status": run.status,
        "qc_status": sample.qc_status,
        "failure_kind": "qc",
        "failure_layer": "qc",
        "failed_step": failed_step,
        "failed_step_label": _stage_label(failed_step),
        "sample_id": sample.sample_id,
        "return_code": None,
        "stderr_excerpt": excerpt,
        "possible_reason": "Sample QC metric did not meet its configured threshold.",
        "suggested_action_code": "review_qc",
        "can_resume": False,
        "can_rerun_stage": False,
        "created_at": _iso(run.created_at),
    }


def _parse_error_summary(summary: str | None) -> dict[str, Any]:
    if not summary:
        return {}
    try:
        payload = json.loads(summary)
        return payload if isinstance(payload, dict) else {"last_100_lines": [summary]}
    except json.JSONDecodeError:
        return {"last_100_lines": [summary]}


def _stderr_excerpt(error: dict[str, Any], *, fallback: str | None) -> str:
    lines = error.get("last_100_lines")
    if isinstance(lines, list):
        excerpt = "\n".join(str(line) for line in lines[-8:]).strip()
        if excerpt:
            return excerpt
    return fallback or "No stderr excerpt captured."


SECRET_PATTERN = re.compile(
    r"(?i)\b([a-z0-9_]*(?:password|passwd|token|secret|api[_-]?key)[a-z0-9_]*)\s*[:=]\s*([^\s,;]+)"
)
AUTHORIZATION_PATTERN = re.compile(r"(?i)\b(authorization\s*:\s*(?:bearer|basic))\s+([^\s,;]+)")
POSIX_PATH_PATTERN = re.compile(r"(?<![\w.])/(?:[^/\s]+/)+([^/\s]+)")


def _sanitize_excerpt(excerpt: str) -> str:
    sanitized = SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=<redacted>", excerpt)
    sanitized = AUTHORIZATION_PATTERN.sub(lambda match: f"{match.group(1)} <redacted>", sanitized)
    return POSIX_PATH_PATTERN.sub(lambda match: f"<server-path>/{match.group(1)}", sanitized)


def _possible_reason(excerpt: str) -> str:
    lowered = excerpt.lower()
    if "permission denied" in lowered and "docker" in lowered:
        return "The workflow runner cannot access the Docker daemon socket."
    if "samtools" in lowered:
        return "A samtools command failed; inspect the stage stderr and input/output files."
    return "Inspect the failed task or pipeline-step stderr before retrying."


def _stage_label(step: str) -> str:
    return STAGE_LABELS.get(step, step.replace("_", " ").strip().title())


def _project_name(run: AnalysisRun) -> str:
    return str((run.params_json or {}).get("project_name") or run.analysis_id)


def _run_qc_status_placeholder() -> str:
    return "unknown"


def _period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    return now - {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}[period]


def _status(value: Any) -> str:
    return str(value or "unknown").strip().lower()


def _basename(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    return PurePosixPath(str(value).replace("\\", "/")).name


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
