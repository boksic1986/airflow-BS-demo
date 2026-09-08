from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisRun,
    Sample,
    WgsIntakeBatch,
    WgsLifecycleStatus,
    WgsMaintenanceAction,
)
from app.wgs_run_projection import public_wgs_batch


FAILED_STATUSES = {"failed", "fail", "error", "terminated"}
SUCCESS_STATUSES = {"success", "succeeded", "complete", "completed", "released", "delivered"}
STEP7_ACTION = "cleanup_step7_sfs"


def project_wgs_dashboard_attention(
    *,
    session: Session,
    runs: Iterable[AnalysisRun],
    since: datetime | None = None,
    now: datetime | None = None,
    **_: Any,
) -> list[dict[str, Any]]:
    """Project privacy-safe WGS conditions that still need operator attention."""

    current = _as_utc(now or datetime.now(timezone.utc))
    selected = list(runs)
    run_ids = [run.analysis_id for run in selected]
    samples = list(
        session.scalars(select(Sample).where(Sample.analysis_id.in_(run_ids))).all()
    ) if run_ids else []
    items: list[dict[str, Any]] = []

    for run in selected:
        status = _status(run.status)
        batch = public_wgs_batch(run.params_json or {})
        if status in FAILED_STATUSES:
            items.append(_item(
                item_id=f"workflow-{run.analysis_id}",
                category="workflow_failed",
                severity="danger",
                title="Workflow failed",
                detail=f"Batch {batch or 'unknown'} requires failure triage.",
                run=run,
                batch=batch,
            ))
        if run.attempt > 1 or _status(run.mode) not in {"", "new"} or run.parent_analysis_id:
            items.append(_item(
                item_id=f"reanalysis-{run.analysis_id}",
                category="reanalysis",
                severity="info",
                title="Reanalysis recorded",
                detail=f"Batch {batch or 'unknown'} is attempt {run.attempt} ({run.mode}).",
                run=run,
                batch=batch,
            ))

    _append_qc_failures(items, selected, samples)
    _append_intake_alerts(items, session=session, since=since)
    _append_duplicate_families(items, selected, samples)
    _append_sfs_overdue(items, session=session, runs=selected, now=current)
    _append_report_overdue(items, session=session, runs=selected, samples=samples, today=current.date())
    priority = {"danger": 0, "warning": 1, "info": 2}
    return sorted(
        items,
        key=lambda item: (
            priority.get(str(item.get("severity")), 9),
            str(item.get("occurred_at") or ""),
            str(item.get("id") or ""),
        ),
    )[:20]


def _append_qc_failures(
    items: list[dict[str, Any]],
    runs: list[AnalysisRun],
    samples: list[Sample],
) -> None:
    by_run = {run.analysis_id: run for run in runs}
    counts: dict[str, int] = {}
    for sample in samples:
        if _status(sample.qc_status) in FAILED_STATUSES:
            counts[sample.analysis_id] = counts.get(sample.analysis_id, 0) + 1
    for analysis_id, count in counts.items():
        run = by_run[analysis_id]
        batch = public_wgs_batch(run.params_json or {})
        items.append(_item(
            item_id=f"qc-{analysis_id}",
            category="qc_failed",
            severity="danger",
            title="QC failed",
            detail=f"Batch {batch or 'unknown'} has {count} failed sample QC result(s).",
            run=run,
            batch=batch,
        ))


def _append_intake_alerts(
    items: list[dict[str, Any]],
    *,
    session: Session,
    since: datetime | None,
) -> None:
    query = select(WgsIntakeBatch).where(
        (WgsIntakeBatch.state == "needs_review")
        | (WgsIntakeBatch.excluded_addon_pair_count > 0)
        | (WgsIntakeBatch.pair_issue_count > 0)
    )
    if since is not None:
        query = query.where(WgsIntakeBatch.last_scanned_at >= since)
    for row in session.scalars(query).all():
        if row.excluded_addon_pair_count:
            items.append({
                "id": f"intake-addon-{row.id}",
                "category": "intake_addon_excluded",
                "severity": "info",
                "title": "Add-on samples excluded",
                "detail": f"Batch {row.sequencing_batch} excluded {row.excluded_addon_pair_count} add-on pair(s).",
                "analysis_id": row.analysis_id,
                "batch_id": row.sequencing_batch,
                "occurred_at": _iso(row.last_scanned_at),
            })
        if row.state == "needs_review" or row.pair_issue_count:
            items.append({
                "id": f"intake-review-{row.id}",
                "category": "intake_pair_issue",
                "severity": "warning",
                "title": "Intake needs review",
                "detail": f"Batch {row.sequencing_batch} has {row.pair_issue_count} abnormal FASTQ pair(s).",
                "analysis_id": row.analysis_id,
                "batch_id": row.sequencing_batch,
                "occurred_at": _iso(row.last_scanned_at),
            })


def _append_duplicate_families(
    items: list[dict[str, Any]],
    runs: list[AnalysisRun],
    samples: list[Sample],
) -> None:
    by_family: dict[str, set[str]] = {}
    for sample in samples:
        family = str(sample.family_id or "").strip()
        if family:
            by_family.setdefault(family, set()).add(sample.analysis_id)
    runs_by_id = {run.analysis_id: run for run in runs}
    for analysis_ids in by_family.values():
        batches = {
            public_wgs_batch(runs_by_id[analysis_id].params_json or {})
            for analysis_id in analysis_ids
            if analysis_id in runs_by_id
        }
        batches.discard(None)
        if len(analysis_ids) < 2 or len(batches) < 2:
            continue
        fingerprint = hashlib.sha256(
            "|".join(sorted(analysis_ids)).encode("utf-8")
        ).hexdigest()[:12]
        items.append({
            "id": f"duplicate-family-{fingerprint}",
            "category": "duplicate_family",
            "severity": "warning",
            "title": "Family appears in multiple batches",
            "detail": f"One family is present in {len(batches)} batches and needs review.",
            "analysis_id": None,
            "batch_id": None,
            "occurred_at": None,
        })


def _append_sfs_overdue(
    items: list[dict[str, Any]],
    *,
    session: Session,
    runs: list[AnalysisRun],
    now: datetime,
) -> None:
    run_ids = [run.analysis_id for run in runs]
    completed = set(
        session.scalars(
            select(WgsMaintenanceAction.analysis_id).where(
                WgsMaintenanceAction.analysis_id.in_(run_ids),
                WgsMaintenanceAction.action_type == STEP7_ACTION,
                WgsMaintenanceAction.status.in_(tuple(SUCCESS_STATUSES | {"verified_absent"})),
            )
        ).all()
    ) if run_ids else set()
    cutoff = now - timedelta(days=2)
    for run in runs:
        finished = _as_utc(run.pipeline_finished_at) if run.pipeline_finished_at else None
        if _status(run.status) != "success" or run.execution_mode != "cce" or not finished:
            continue
        if finished > cutoff or run.analysis_id in completed:
            continue
        batch = public_wgs_batch(run.params_json or {})
        days = max(2, int((now - finished).total_seconds() // 86400))
        items.append(_item(
            item_id=f"sfs-overdue-{run.analysis_id}",
            category="sfs_cleanup_overdue",
            severity="warning",
            title="SFS cleanup overdue",
            detail=f"Batch {batch or 'unknown'} completed {days} days ago without a successful SFS release.",
            run=run,
            batch=batch,
        ))


def _append_report_overdue(
    items: list[dict[str, Any]],
    *,
    session: Session,
    runs: list[AnalysisRun],
    samples: list[Sample],
    today: date,
) -> None:
    run_ids = [run.analysis_id for run in runs]
    delivered = set(
        session.scalars(
            select(WgsLifecycleStatus.analysis_id).where(
                WgsLifecycleStatus.analysis_id.in_(run_ids),
                WgsLifecycleStatus.kind == "downstream_release",
                WgsLifecycleStatus.status.in_(tuple(SUCCESS_STATUSES)),
            )
        ).all()
    ) if run_ids else set()
    overdue: dict[str, int] = {}
    for sample in samples:
        if sample.analysis_id in delivered:
            continue
        value = str((sample.metadata_json or {}).get("estimated_report_date") or "").strip()
        try:
            expected = date.fromisoformat(value[:10])
        except ValueError:
            continue
        if expected < today:
            overdue[sample.analysis_id] = overdue.get(sample.analysis_id, 0) + 1
    runs_by_id = {run.analysis_id: run for run in runs}
    for analysis_id, count in overdue.items():
        run = runs_by_id[analysis_id]
        batch = public_wgs_batch(run.params_json or {})
        items.append(_item(
            item_id=f"report-overdue-{analysis_id}",
            category="report_delivery_overdue",
            severity="warning",
            title="Report delivery overdue",
            detail=f"Batch {batch or 'unknown'} has {count} sample report deadline(s) past due.",
            run=run,
            batch=batch,
        ))


def _item(
    *,
    item_id: str,
    category: str,
    severity: str,
    title: str,
    detail: str,
    run: AnalysisRun,
    batch: str | None,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "category": category,
        "severity": severity,
        "title": title,
        "detail": detail,
        "analysis_id": run.analysis_id,
        "batch_id": batch,
        "occurred_at": _iso(run.pipeline_finished_at or run.ended_at or run.created_at),
    }


def _status(value: object) -> str:
    return str(value or "").strip().lower()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return _as_utc(value).isoformat() if value else None
