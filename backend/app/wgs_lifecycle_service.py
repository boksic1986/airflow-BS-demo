from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select

from app.models import (
    AnalysisRun,
    AuditLog,
    WgsInputSnapshot,
    WgsLifecycleStatus,
    WgsMaintenanceAction,
)


KINDS = {"raw_fastq_backup", "downstream_release"}
STATUSES = {"not_started", "pending", "running", "success", "failed"}
STEP7_ACTION_TYPE = "cleanup_step7_sfs"


class LifecycleConflict(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def project_wgs_lifecycle(*, session, run: AnalysisRun) -> dict[str, dict]:
    workflow_status = _workflow_status(run.status)
    workflow_updated_at = run.pipeline_finished_at or run.ended_at or run.progress_updated_at
    cloud_release = _project_cloud_release(session=session, run=run)
    return {
        "workflow": _projection(
            status=workflow_status,
            revision=None,
            updated_at=workflow_updated_at,
            updated_by=None,
            message=None,
        ),
        "cloud_release": cloud_release,
        "raw_fastq_backup": _project_registered_kind(
            session=session, run=run, kind="raw_fastq_backup", attempt=run.attempt
        ),
        "downstream_release": _project_registered_kind(
            session=session, run=run, kind="downstream_release", attempt=run.attempt
        ),
    }


def project_wgs_lifecycles(
    *, session, runs: list[AnalysisRun]
) -> dict[str, dict[str, dict]]:
    """Project a dashboard page in a fixed number of database queries."""
    wgs_runs = [run for run in runs if run.pipeline_name == "wgs"]
    if not wgs_runs:
        return {}
    run_ids = [run.analysis_id for run in wgs_runs]
    snapshots = session.scalars(
        select(WgsInputSnapshot)
        .where(WgsInputSnapshot.analysis_id.in_(run_ids))
        .order_by(WgsInputSnapshot.analysis_id, WgsInputSnapshot.attempt.desc())
    ).all()
    snapshots_by_run: dict[str, list[WgsInputSnapshot]] = {}
    for snapshot in snapshots:
        snapshots_by_run.setdefault(snapshot.analysis_id, []).append(snapshot)
    current_snapshots: dict[str, WgsInputSnapshot] = {}
    for run in wgs_runs:
        current = next(
            (
                snapshot
                for snapshot in snapshots_by_run.get(run.analysis_id, [])
                if snapshot.attempt <= run.attempt
            ),
            None,
        )
        if current is not None:
            current_snapshots[run.analysis_id] = current

    raw_scope_keys = {
        _input_snapshot_scope_key(snapshot) for snapshot in current_snapshots.values()
    }
    status_conditions = [
        (
            (WgsLifecycleStatus.kind == "downstream_release")
            & WgsLifecycleStatus.analysis_id.in_(run_ids)
        )
    ]
    if raw_scope_keys:
        status_conditions.append(
            (WgsLifecycleStatus.kind == "raw_fastq_backup")
            & WgsLifecycleStatus.scope_key.in_(raw_scope_keys)
        )
    status_rows = session.scalars(
        select(WgsLifecycleStatus).where(or_(*status_conditions))
    ).all()
    raw_rows = {
        row.scope_key: row for row in status_rows if row.kind == "raw_fastq_backup"
    }
    downstream_rows = {
        (row.analysis_id, row.attempt): row
        for row in status_rows
        if row.kind == "downstream_release"
    }
    maintenance_rows = session.scalars(
        select(WgsMaintenanceAction).where(
            WgsMaintenanceAction.analysis_id.in_(run_ids),
            WgsMaintenanceAction.action_type == STEP7_ACTION_TYPE,
        )
    ).all()
    maintenance_by_attempt = {
        (row.analysis_id, row.attempt): row for row in maintenance_rows
    }

    projected: dict[str, dict[str, dict]] = {}
    for run in wgs_runs:
        snapshot = current_snapshots.get(run.analysis_id)
        raw_row = (
            raw_rows.get(_input_snapshot_scope_key(snapshot))
            if snapshot is not None
            else None
        )
        projected[run.analysis_id] = _project_from_records(
            run=run,
            cloud_release_action=maintenance_by_attempt.get(
                (run.analysis_id, run.attempt)
            ),
            raw_status=raw_row,
            downstream_status=downstream_rows.get((run.analysis_id, run.attempt)),
            raw_snapshot_available=snapshot is not None,
        )
    return projected


def update_wgs_lifecycle_status(
    *,
    session,
    run: AnalysisRun,
    kind: str,
    attempt: int,
    status: str,
    expected_revision: int,
    message: str | None,
    updated_by: str,
) -> dict:
    if kind not in KINDS:
        raise ValueError("unsupported WGS lifecycle kind")
    if status not in STATUSES:
        raise ValueError("unsupported WGS lifecycle status")
    if attempt != run.attempt:
        raise LifecycleConflict(
            "LIFECYCLE_ATTEMPT_MISMATCH",
            "The requested attempt is not the run's current attempt",
        )
    scope_type, scope_key = _scope_for_kind(
        session=session, run=run, kind=kind, attempt=attempt
    )
    row = session.scalar(
        select(WgsLifecycleStatus)
        .where(
            WgsLifecycleStatus.kind == kind,
            WgsLifecycleStatus.scope_type == scope_type,
            WgsLifecycleStatus.scope_key == scope_key,
        )
        .with_for_update()
    )
    current_revision = row.revision if row is not None else 1
    if expected_revision != current_revision:
        raise LifecycleConflict(
            "STALE_LIFECYCLE_STATUS",
            "The lifecycle status changed; refresh before updating it",
        )
    now = datetime.now(timezone.utc)
    if row is None:
        row = WgsLifecycleStatus(
            kind=kind,
            scope_type=scope_type,
            scope_key=scope_key,
            analysis_id=run.analysis_id,
            attempt=attempt,
            status=status,
            revision=2,
            message=_clean_message(message),
            updated_by=updated_by,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
    else:
        row.status = status
        row.revision += 1
        row.message = _clean_message(message)
        row.updated_by = updated_by
        row.updated_at = now
    session.add(
        AuditLog(
            username=updated_by,
            action=f"wgs.lifecycle.{kind}.update",
            analysis_id=run.analysis_id,
            payload_json={
                "attempt": attempt,
                "status": status,
                "revision": row.revision,
                "message": row.message,
            },
        )
    )
    session.commit()
    return _serialize_registered(row)


def _project_registered_kind(*, session, run: AnalysisRun, kind: str, attempt: int) -> dict:
    try:
        scope_type, scope_key = _scope_for_kind(
            session=session, run=run, kind=kind, attempt=attempt
        )
    except LifecycleConflict as exc:
        return _projection(
            status="not_started",
            revision=1,
            updated_at=None,
            updated_by=None,
            message=exc.message,
        )
    row = session.scalar(
        select(WgsLifecycleStatus).where(
            WgsLifecycleStatus.kind == kind,
            WgsLifecycleStatus.scope_type == scope_type,
            WgsLifecycleStatus.scope_key == scope_key,
        )
    )
    if row is None:
        return _projection(
            status="not_started",
            revision=1,
            updated_at=None,
            updated_by=None,
            message=None,
        )
    return _serialize_registered(row)


def _project_cloud_release(*, session, run: AnalysisRun) -> dict:
    if str(run.execution_mode or "").lower() == "local":
        return _projection(
            status="not_applicable",
            revision=None,
            updated_at=None,
            updated_by=None,
            message=None,
        )
    action = session.scalar(
        select(WgsMaintenanceAction)
        .where(
            WgsMaintenanceAction.analysis_id == run.analysis_id,
            WgsMaintenanceAction.attempt == run.attempt,
            WgsMaintenanceAction.action_type == STEP7_ACTION_TYPE,
        )
        .order_by(WgsMaintenanceAction.id.desc())
    )
    if action is None:
        return _projection(
            status="not_started",
            revision=None,
            updated_at=None,
            updated_by=None,
            message=None,
        )
    status = str(action.status or "not_started").lower()
    if status in {"requested", "queued"}:
        status = "pending"
    if status not in STATUSES:
        status = "failed" if action.error_message else "not_started"
    return _projection(
        status=status,
        revision=None,
        updated_at=action.updated_at,
        updated_by=action.requested_by,
        message=action.error_message,
    )


def _project_from_records(
    *,
    run: AnalysisRun,
    cloud_release_action: WgsMaintenanceAction | None,
    raw_status: WgsLifecycleStatus | None,
    downstream_status: WgsLifecycleStatus | None,
    raw_snapshot_available: bool,
) -> dict[str, dict]:
    workflow_updated_at = run.pipeline_finished_at or run.ended_at or run.progress_updated_at
    if str(run.execution_mode or "").lower() == "local":
        cloud_release = _projection(
            status="not_applicable",
            revision=None,
            updated_at=None,
            updated_by=None,
            message=None,
        )
    elif cloud_release_action is None:
        cloud_release = _projection(
            status="not_started",
            revision=None,
            updated_at=None,
            updated_by=None,
            message=None,
        )
    else:
        cloud_status = str(cloud_release_action.status or "not_started").lower()
        if cloud_status in {"requested", "queued"}:
            cloud_status = "pending"
        if cloud_status not in STATUSES:
            cloud_status = "failed" if cloud_release_action.error_message else "not_started"
        cloud_release = _projection(
            status=cloud_status,
            revision=None,
            updated_at=cloud_release_action.updated_at,
            updated_by=cloud_release_action.requested_by,
            message=cloud_release_action.error_message,
        )
    raw_projection = (
        _serialize_registered(raw_status)
        if raw_status is not None
        else _projection(
            status="not_started",
            revision=1,
            updated_at=None,
            updated_by=None,
            message=(
                None
                if raw_snapshot_available
                else "Raw FASTQ backup status requires a frozen input snapshot"
            ),
        )
    )
    downstream_projection = (
        _serialize_registered(downstream_status)
        if downstream_status is not None
        else _projection(
            status="not_started",
            revision=1,
            updated_at=None,
            updated_by=None,
            message=None,
        )
    )
    return {
        "workflow": _projection(
            status=_workflow_status(run.status),
            revision=None,
            updated_at=workflow_updated_at,
            updated_by=None,
            message=None,
        ),
        "cloud_release": cloud_release,
        "raw_fastq_backup": raw_projection,
        "downstream_release": downstream_projection,
    }


def _scope_for_kind(*, session, run: AnalysisRun, kind: str, attempt: int) -> tuple[str, str]:
    if kind == "downstream_release":
        return "analysis_attempt", f"{run.analysis_id}:attempt-{attempt}"
    snapshot = session.scalar(
        select(WgsInputSnapshot)
        .where(
            WgsInputSnapshot.analysis_id == run.analysis_id,
            WgsInputSnapshot.attempt <= attempt,
        )
        .order_by(WgsInputSnapshot.attempt.desc())
    )
    if snapshot is None:
        raise LifecycleConflict(
            "INPUT_SNAPSHOT_NOT_FOUND",
            "Raw FASTQ backup status requires a frozen input snapshot",
        )
    return "input_snapshot", _input_snapshot_scope_key(snapshot)


def _input_snapshot_scope_key(snapshot: WgsInputSnapshot) -> str:
    if snapshot.manifest_sha256:
        return f"sha256:{snapshot.manifest_sha256}"
    return f"{snapshot.analysis_id}:attempt-{snapshot.attempt}"


def _serialize_registered(row: WgsLifecycleStatus) -> dict:
    return _projection(
        status=row.status,
        revision=row.revision,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
        message=row.message,
    )


def _projection(
    *, status: str, revision: int | None, updated_at, updated_by: str | None, message: str | None
) -> dict:
    payload = {
        "status": status,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "updated_by": updated_by,
        "message": message,
    }
    if revision is not None:
        payload["revision"] = revision
    return payload


def _workflow_status(value: str | None) -> str:
    normalized = str(value or "not_started").lower()
    if normalized in {"submitted", "queued", "approved", "snapshotting", "created"}:
        return "pending" if normalized != "created" else "not_started"
    if normalized in {"running", "publishing", "downloading"}:
        return "running"
    if normalized in {"success", "failed"}:
        return normalized
    if normalized in {"cancelled", "canceled", "terminated", "unknown_interrupted"}:
        return "failed"
    return "not_started"


def _clean_message(message: str | None) -> str | None:
    cleaned = str(message or "").strip()
    return cleaned or None
