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


@dataclass(frozen=True)
class IntakeCleanupPlan:
    analysis_snapshot: tuple[tuple[str, str], ...]
    discovery_snapshot: tuple[tuple[object, ...], ...]
    keep_analysis_ids: tuple[str, ...]
    delete_ids: tuple[int, ...]


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


def build_intake_cleanup_plan(
    *,
    session: Session,
    expected_analysis_ids: set[str],
    keep_analysis_ids: set[str],
    expected_discovery_total: int,
) -> IntakeCleanupPlan:
    analysis_snapshot = _analysis_snapshot(session)
    actual_analysis_ids = {analysis_id for analysis_id, _status in analysis_snapshot}
    if actual_analysis_ids != expected_analysis_ids:
        raise CleanupSafetyError(
            "analysis run snapshot does not match expected ids: "
            f"expected {sorted(expected_analysis_ids)}, found {sorted(actual_analysis_ids)}"
        )
    active = sorted(
        analysis_id for analysis_id, status in analysis_snapshot if status in ACTIVE_STATUSES
    )
    if active:
        raise CleanupSafetyError("active runs must finish before intake cleanup: " + ", ".join(active))
    not_success = sorted(
        analysis_id for analysis_id, status in analysis_snapshot if status != "success"
    )
    if not_success:
        raise CleanupSafetyError("retained business snapshot contains non-success runs: " + ", ".join(not_success))
    if not keep_analysis_ids.issubset(expected_analysis_ids):
        raise CleanupSafetyError("intake keep ids must be part of the expected analysis snapshot")

    discovery_snapshot = _discovery_snapshot(session)
    if len(discovery_snapshot) != expected_discovery_total:
        raise CleanupSafetyError(
            f"expected {expected_discovery_total} discovery rows, found {len(discovery_snapshot)}"
        )
    retained_counts = {
        analysis_id: sum(1 for row in discovery_snapshot if row[4] == analysis_id)
        for analysis_id in keep_analysis_ids
    }
    invalid_retained = sorted(
        analysis_id for analysis_id, count in retained_counts.items() if count != 1
    )
    if invalid_retained:
        raise CleanupSafetyError(
            "each intake keep id must match exactly one discovery row: " + ", ".join(invalid_retained)
        )
    delete_ids = tuple(
        int(row[0]) for row in discovery_snapshot if row[4] not in keep_analysis_ids
    )
    return IntakeCleanupPlan(
        analysis_snapshot=analysis_snapshot,
        discovery_snapshot=discovery_snapshot,
        keep_analysis_ids=tuple(sorted(keep_analysis_ids)),
        delete_ids=delete_ids,
    )


def execute_intake_cleanup_plan(*, session: Session, plan: IntakeCleanupPlan) -> dict[str, int]:
    if _analysis_snapshot(session) != plan.analysis_snapshot or _discovery_snapshot(session) != plan.discovery_snapshot:
        raise CleanupSafetyError("database changed after preview; generate a new intake cleanup plan")
    if plan.delete_ids:
        session.execute(delete(IntakeDiscovery).where(IntakeDiscovery.id.in_(plan.delete_ids)))
    session.commit()
    return {
        "before": len(plan.discovery_snapshot),
        "deleted": len(plan.delete_ids),
        "retained": len(plan.discovery_snapshot) - len(plan.delete_ids),
    }


def _analysis_snapshot(session: Session) -> tuple[tuple[str, str], ...]:
    rows = session.execute(select(AnalysisRun.analysis_id, AnalysisRun.status)).all()
    return tuple(sorted((str(analysis_id), str(status)) for analysis_id, status in rows))


def _discovery_snapshot(session: Session) -> tuple[tuple[object, ...], ...]:
    rows = session.scalars(select(IntakeDiscovery).order_by(IntakeDiscovery.id)).all()
    return tuple(
        (
            row.id,
            row.pipeline_name,
            row.root_path,
            row.batch_id,
            row.analysis_id,
            row.ready_state,
            row.submit_state,
            row.fingerprint,
            row.file_count,
            row.total_bytes,
            row.stable_observation_count,
            row.last_seen_at.isoformat() if row.last_seen_at else None,
        )
        for row in rows
    )
