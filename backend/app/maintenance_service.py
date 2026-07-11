from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Artifact, IntakeDiscovery, QcMetric, RunAction, Sample, SnakemakeRuleEvent


ACTIVE_STATUSES = {"running", "submitted", "queued", "scheduled"}


class CleanupSafetyError(RuntimeError):
    pass


@dataclass(frozen=True)
class CleanupPlan:
    snapshot_ids: tuple[str, ...]
    keep_ids: tuple[str, ...]
    delete_ids: tuple[str, ...]


def build_cleanup_plan(
    *,
    session: Session,
    keep_ids: set[str],
    expected_total: int,
    allow_active_delete_ids: set[str] | None = None,
) -> CleanupPlan:
    snapshot = tuple(sorted(session.scalars(select(AnalysisRun.analysis_id)).all()))
    if len(snapshot) != expected_total:
        raise CleanupSafetyError(f"expected {expected_total} runs, found {len(snapshot)}")
    missing = sorted(set(keep_ids) - set(snapshot))
    if missing:
        raise CleanupSafetyError(f"keep ids are missing: {', '.join(missing)}")
    active = set(
        session.scalars(
            select(AnalysisRun.analysis_id).where(AnalysisRun.status.in_(ACTIVE_STATUSES))
        ).all()
    )
    allowed_active = set(allow_active_delete_ids or ())
    invalid_allowed = sorted(allowed_active - active)
    if invalid_allowed:
        raise CleanupSafetyError(
            "active-delete overrides are not active runs: " + ", ".join(invalid_allowed)
        )
    protected_active = sorted(active - allowed_active)
    if protected_active:
        raise CleanupSafetyError(
            f"active runs must finish before cleanup: {', '.join(protected_active)}"
        )
    retained_active = sorted(active & set(keep_ids))
    if retained_active:
        raise CleanupSafetyError(
            f"active runs cannot be retained during cleanup: {', '.join(retained_active)}"
        )
    delete_ids = tuple(sorted(set(snapshot) - set(keep_ids)))
    return CleanupPlan(snapshot_ids=snapshot, keep_ids=tuple(sorted(keep_ids)), delete_ids=delete_ids)


def execute_cleanup_plan(*, session: Session, plan: CleanupPlan) -> dict[str, int]:
    current_ids = tuple(sorted(session.scalars(select(AnalysisRun.analysis_id)).all()))
    if current_ids != plan.snapshot_ids:
        raise CleanupSafetyError("database changed after preview; generate a new cleanup plan")

    delete_ids = list(plan.delete_ids)
    cleared_refs = 0
    if delete_ids:
        referenced = session.scalars(
            select(IntakeDiscovery).where(IntakeDiscovery.analysis_id.in_(delete_ids))
        ).all()
        for row in referenced:
            row.analysis_id = None
            row.ready_state = "observed"
            row.submit_state = "bootstrap"
            cleared_refs += 1

        for model in (QcMetric, SnakemakeRuleEvent, Artifact, RunAction, Sample):
            session.execute(delete(model).where(model.analysis_id.in_(delete_ids)))
        session.execute(delete(AnalysisRun).where(AnalysisRun.analysis_id.in_(delete_ids)))
    session.commit()
    retained = len(plan.keep_ids)
    return {
        "before": len(plan.snapshot_ids),
        "deleted": len(delete_ids),
        "retained": retained,
        "cleared_intake_references": cleared_refs,
    }
