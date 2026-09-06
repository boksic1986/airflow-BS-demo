from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    AnalysisRun,
    ObsTransferLease,
    PlatformResourceSnapshot,
    RunAction,
    RunAttempt,
    Sample,
    WgsExecutionDispatch,
    WgsExecutionTargetSlot,
)
from app.wgs_run_projection import public_wgs_batch
from app.wgs_transfer_lease import OBS_UPLOAD_SLOT


TARGET_MODES = {
    "cce": "cce",
    "node-97": "local",
    "node-96": "local",
    "sge-default": "sge",
}
TERMINAL_STATES = {"terminal", "needs_recovery"}
LOCKED_STATES = {"committed", "running", *TERMINAL_STATES}


@dataclass(frozen=True)
class ExecutionDispatchConflict(ValueError):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


def ensure_execution_dispatch(*, session, run: AnalysisRun) -> WgsExecutionDispatch:
    if run.pipeline_name != "wgs":
        raise ValueError("execution dispatch is only available for WGS")
    params = dict(run.params_json or {})
    project_id = str(params.get("project_id") or params.get("project_name") or "").strip()
    batch = public_wgs_batch(params)
    if not project_id or not batch:
        raise ValueError("WGS project and batch are required for execution dispatch")
    existing = session.scalar(
        select(WgsExecutionDispatch).where(
            WgsExecutionDispatch.project_id == project_id,
            WgsExecutionDispatch.batch == batch,
        )
    )
    if existing is not None:
        if existing.analysis_id != run.analysis_id:
            raise ExecutionDispatchConflict(
                "BATCH_EXECUTION_EXISTS",
                f"batch {batch} already belongs to {existing.analysis_id}",
            )
        return existing
    row = WgsExecutionDispatch(
        project_id=project_id,
        batch=batch,
        analysis_id=run.analysis_id,
        desired_mode="cce",
        desired_target="cce",
        dispatch_state="preparing",
        dispatch_revision=1,
    )
    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError as exc:
        existing = session.scalar(
            select(WgsExecutionDispatch).where(
                WgsExecutionDispatch.project_id == project_id,
                WgsExecutionDispatch.batch == batch,
            )
        )
        if existing is not None and existing.analysis_id == run.analysis_id:
            return existing
        raise ExecutionDispatchConflict(
            "BATCH_EXECUTION_EXISTS", f"batch {batch} already has an execution claim"
        ) from exc
    return row


def reset_execution_dispatch_for_attempt(*, session, run: AnalysisRun) -> WgsExecutionDispatch:
    row = _locked_dispatch(session, run.analysis_id)
    if row is None:
        row = ensure_execution_dispatch(session=session, run=run)
    _release_local_slot(session=session, dispatch=row)
    row.desired_mode = "cce"
    row.desired_target = "cce"
    row.dispatch_state = "preparing"
    row.dispatch_revision += 1
    row.committed_at = None
    row.committed_attempt = None
    row.blocking_reason = None
    row.updated_at = _now()
    run.execution_mode = "cce"
    params = dict(run.params_json or {})
    params["execution_mode"] = "cce"
    run.params_json = params
    return row


def mark_execution_waiting(*, session, run: AnalysisRun) -> WgsExecutionDispatch:
    row = _locked_dispatch(session, run.analysis_id)
    if row is None:
        row = ensure_execution_dispatch(session=session, run=run)
    if row.dispatch_state not in LOCKED_STATES:
        row.dispatch_state = "waiting_resource"
        row.blocking_reason = _waiting_reason(row.desired_target)
        row.updated_at = _now()
    return row


def project_execution_dispatch(*, session, settings, run: AnalysisRun) -> dict[str, Any] | None:
    row = session.scalar(
        select(WgsExecutionDispatch).where(
            WgsExecutionDispatch.analysis_id == run.analysis_id
        )
    )
    if row is None:
        try:
            row = ensure_execution_dispatch(session=session, run=run)
        except ExecutionDispatchConflict:
            # The migration deliberately does not backfill historical runs.
            # Multiple pre-migration attempts for one batch must remain
            # readable without competing for the new unique execution claim.
            submission_mode = str((run.params_json or {}).get("submission_mode") or "")
            if submission_mode in {"three_stage", "auto_dispatch"}:
                raise
            return None
        except ValueError:
            # Historical WGS rows may predate catalogued project/batch identity.
            # They remain readable but cannot participate in target switching.
            return None
        session.commit()
    targets = [
        _cce_target(session=session, analysis_id=run.analysis_id),
        _local_target(session=session, settings=settings, target="node-97", analysis_id=run.analysis_id),
        _local_target(session=session, settings=settings, target="node-96", analysis_id=run.analysis_id),
        _sge_target(settings),
    ]
    allow_switch = row.dispatch_state not in LOCKED_STATES and row.committed_at is None
    blocking_reason = row.blocking_reason
    if not allow_switch:
        blocking_reason = blocking_reason or "Execution target is locked after dispatch commit"
    return {
        "desired_mode": row.desired_mode,
        "desired_target": row.desired_target,
        "dispatch_state": row.dispatch_state,
        "dispatch_revision": row.dispatch_revision,
        "allow_switch": allow_switch,
        "committed_at": _iso(row.committed_at),
        "committed_attempt": row.committed_attempt,
        "blocking_reason": blocking_reason,
        "targets": targets,
    }


def change_execution_choice(
    *,
    session,
    settings,
    analysis_id: str,
    desired_mode: str,
    desired_target: str,
    expected_revision: int,
    requested_by: str,
    reason: str,
) -> dict[str, Any]:
    if TARGET_MODES.get(desired_target) != desired_mode:
        raise ValueError("execution mode and target do not match")
    audit_reason = str(reason or "").strip()
    if not audit_reason or len(audit_reason) > 500:
        raise ValueError("an audit reason of at most 500 characters is required")
    run = session.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs")
        .with_for_update()
    )
    if run is None:
        raise ValueError("WGS run was not found")
    attempt = session.scalar(
        select(RunAttempt)
        .where(RunAttempt.analysis_id == analysis_id, RunAttempt.attempt == run.attempt)
        .with_for_update()
    )
    row = _locked_dispatch(session, analysis_id)
    if row is None:
        row = ensure_execution_dispatch(session=session, run=run)
    if row.dispatch_state in LOCKED_STATES or row.committed_at is not None:
        raise ExecutionDispatchConflict(
            "EXECUTION_ALREADY_COMMITTED",
            "CCE Step1 or the selected execution backend has already started; the target is locked",
        )
    if row.dispatch_revision != expected_revision:
        raise ExecutionDispatchConflict(
            "STALE_EXECUTION_CHOICE",
            "Execution choice changed after this page was loaded",
        )
    target_state = _target_by_name(
        session=session,
        settings=settings,
        target=desired_target,
        analysis_id=analysis_id,
    )
    if not target_state["available"]:
        raise ExecutionDispatchConflict(
            "TARGET_UNAVAILABLE", str(target_state["reason"])
        )
    old_target = row.desired_target
    if old_target != desired_target:
        row.desired_mode = desired_mode
        row.desired_target = desired_target
        row.dispatch_revision += 1
        row.blocking_reason = _waiting_reason(desired_target)
        row.updated_at = _now()
        run.execution_mode = desired_mode
        params = dict(run.params_json or {})
        params["execution_mode"] = desired_mode
        params["execution_target"] = desired_target
        run.params_json = params
        if attempt is not None:
            attempt.execution_mode = desired_mode
        session.add(
            RunAction(
                analysis_id=analysis_id,
                action="change_execution_choice",
                requested_by=requested_by,
                result_status="accepted",
                payload_json={
                    "attempt": run.attempt,
                    "from_target": old_target,
                    "to_target": desired_target,
                    "revision": row.dispatch_revision,
                    "reason": audit_reason,
                },
            )
        )
    session.commit()
    return project_execution_dispatch(session=session, settings=settings, run=run)


def commit_execution_choice(*, session, settings, analysis_id: str, attempt: int) -> dict[str, Any]:
    run = session.scalar(
        select(AnalysisRun)
        .where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs")
        .with_for_update()
    )
    if run is None or run.attempt != attempt:
        raise ValueError("unknown active WGS attempt")
    current_attempt = session.scalar(
        select(RunAttempt)
        .where(
            RunAttempt.analysis_id == analysis_id,
            RunAttempt.attempt == attempt,
        )
        .with_for_update()
    )
    if current_attempt is None:
        raise ValueError("unknown active WGS attempt")
    row = _locked_dispatch(session, analysis_id)
    if row is None:
        row = ensure_execution_dispatch(session=session, run=run)
    if row.committed_at is not None:
        if row.committed_attempt != attempt:
            raise ExecutionDispatchConflict(
                "EXECUTION_ALREADY_COMMITTED", "another WGS attempt owns this execution claim"
            )
        return {**_serialize(row), "committed": True}
    params = dict(run.params_json or {})
    submission_mode = str(params.get("submission_mode") or "legacy")
    if submission_mode in {"three_stage", "auto_dispatch"} and (
        params.get("submission_phase") != "approved"
        or not params.get("execution_approved_at")
    ):
        raise ExecutionDispatchConflict(
            "EXECUTION_NOT_APPROVED",
            "WGS sample and analysis preparation must be approved before execution commit",
        )
    if submission_mode in {"three_stage", "auto_dispatch"} and session.scalar(
        select(Sample.id).where(Sample.analysis_id == analysis_id).limit(1)
    ) is None:
        raise ExecutionDispatchConflict(
            "EXECUTION_NOT_APPROVED",
            "WGS execution cannot commit before prepared samples are imported",
        )
    if row.dispatch_state not in {"preparing", "waiting_resource"}:
        raise ExecutionDispatchConflict(
            "EXECUTION_ALREADY_COMMITTED", "execution target can no longer be committed"
        )
    availability = _target_by_name(
        session=session,
        settings=settings,
        target=row.desired_target,
        analysis_id=analysis_id,
    )
    if not availability["available"]:
        row.dispatch_state = "waiting_resource"
        row.blocking_reason = str(availability["reason"])
        row.updated_at = _now()
        session.commit()
        return {**_serialize(row), "committed": False}
    acquired = True
    if row.desired_target == "cce":
        acquired = _acquire_cce_upload_slot(
            session=session, analysis_id=analysis_id, attempt=attempt
        )
    elif row.desired_target in {"node-97", "node-96"}:
        acquired = _acquire_local_slot(
            session=session,
            target=row.desired_target,
            analysis_id=analysis_id,
            attempt=attempt,
        )
    if not acquired:
        row.dispatch_state = "waiting_resource"
        row.blocking_reason = _waiting_reason(row.desired_target)
        row.updated_at = _now()
        session.commit()
        return {**_serialize(row), "committed": False}
    row.dispatch_state = "committed"
    row.committed_at = _now()
    row.committed_attempt = attempt
    row.blocking_reason = None
    row.dispatch_revision += 1
    row.updated_at = row.committed_at
    session.commit()
    return {**_serialize(row), "committed": True}


def mark_execution_running(*, session, analysis_id: str, attempt: int) -> None:
    row = _locked_dispatch(session, analysis_id)
    if row is None:
        # Pre-migration DagRuns have no target claim. They remain observable
        # during a rolling application upgrade and cannot be switched.
        return
    if row.committed_attempt != attempt or row.committed_at is None:
        raise ExecutionDispatchConflict(
            "EXECUTION_NOT_COMMITTED",
            "WGS execution cannot start before its target is committed",
        )
    if row.dispatch_state == "committed":
        row.dispatch_state = "running"
        row.updated_at = _now()


def mark_execution_terminal(*, session, analysis_id: str, attempt: int) -> None:
    row = _locked_dispatch(session, analysis_id)
    if row is None or row.committed_attempt != attempt:
        return
    row.dispatch_state = "terminal"
    row.blocking_reason = None
    row.updated_at = _now()
    _release_local_slot(session=session, dispatch=row)


def mark_execution_needs_recovery(
    *, session, analysis_id: str, attempt: int, reason: str
) -> None:
    row = _locked_dispatch(session, analysis_id)
    if row is None or row.committed_attempt != attempt:
        return
    row.dispatch_state = "needs_recovery"
    row.blocking_reason = str(reason or "Committed execution requires recovery")[:1000]
    row.updated_at = _now()


def _target_by_name(*, session, settings, target: str, analysis_id: str) -> dict[str, Any]:
    if target == "cce":
        return _cce_target(session=session, analysis_id=analysis_id)
    if target in {"node-97", "node-96"}:
        return _local_target(
            session=session, settings=settings, target=target, analysis_id=analysis_id
        )
    if target == "sge-default":
        return _sge_target(settings)
    raise ValueError("unsupported execution target")


def _cce_target(*, session, analysis_id: str) -> dict[str, Any]:
    slot = session.scalar(
        select(ObsTransferLease).where(
            ObsTransferLease.slot_name == OBS_UPLOAD_SLOT
        )
    )
    waiting = bool(
        slot is not None
        and slot.analysis_id not in {None, analysis_id}
    )
    return {
        "mode": "cce",
        "target": "cce",
        "label": "CCE",
        "status": "waiting_upload_slot" if waiting else "available",
        "available": True,
        "reason": "Waiting for CCE upload slot" if waiting else None,
        "metrics": None,
    }


def _sge_target(settings) -> dict[str, Any]:
    enabled = bool(getattr(settings, "wgs_sge_enabled", False))
    return {
        "mode": "sge",
        "target": "sge-default",
        "label": "SGE",
        "status": "manual" if enabled else "unsupported",
        "available": enabled,
        "reason": None if enabled else "SGE runner has not passed production acceptance",
        "metrics": None,
    }


def _local_target(*, session, settings, target: str, analysis_id: str) -> dict[str, Any]:
    enabled_name = {
        "node-97": "wgs_local_node97_enabled",
        "node-96": "wgs_local_node96_enabled",
    }[target]
    label = {"node-97": "Local .97", "node-96": "Local .96"}[target]
    if not bool(getattr(settings, enabled_name, False)):
        return {
            "mode": "local",
            "target": target,
            "label": label,
            "status": "unsupported",
            "available": False,
            "reason": f"{label} runner has not passed production acceptance",
            "metrics": None,
        }
    row = session.scalar(
        select(PlatformResourceSnapshot).where(
            PlatformResourceSnapshot.resource_key == target,
            PlatformResourceSnapshot.resource_type == "node",
        )
    )
    if row is None:
        return _local_unavailable(target, label, "stale", "No node health snapshot is available")
    source_at = _aware(row.source_updated_at)
    if row.status != "healthy":
        return _local_unavailable(
            target, label, "stale" if row.status == "stale" else "busy", f"Node status is {row.status}"
        )
    if source_at is None or _now() - source_at > timedelta(minutes=3):
        return _local_unavailable(target, label, "stale", "Node metrics are older than 3 minutes")
    count = int(getattr(settings, "wgs_local_admission_samples", 3))
    history = list(row.history_json or [])[-count:]
    current = dict(row.current_json or {})
    metrics = _safe_metrics(current, source_at)
    if len(history) < count:
        return _local_unavailable(
            target, label, "stale", f"The latest {count} one-minute samples are not available", metrics
        )
    point_times = [_point_at(point) for point in history]
    if any(value is None for value in point_times):
        return _local_unavailable(
            target, label, "stale", "The latest three node samples have invalid timestamps", metrics
        )
    concrete_times = [value for value in point_times if value is not None]
    if _now() - concrete_times[-1] > timedelta(minutes=3):
        return _local_unavailable(
            target, label, "stale", "The latest three one-minute samples are stale", metrics
        )
    gaps = [
        (current - previous).total_seconds()
        for previous, current in zip(concrete_times, concrete_times[1:])
    ]
    if any(gap < 30 or gap > 90 for gap in gaps):
        return _local_unavailable(
            target,
            label,
            "stale",
            "The latest three node samples are not consecutive one-minute observations",
            metrics,
        )
    min_cpus = int(getattr(settings, "wgs_local_min_logical_cpus", 96))
    cpu_count = _number(current.get("logical_cpu_count"))
    if cpu_count is None or cpu_count < min_cpus:
        return _local_unavailable(target, label, "unsupported", f"Node provides fewer than {min_cpus} logical CPUs", metrics)
    active = session.scalar(
        select(WgsExecutionDispatch).where(
            WgsExecutionDispatch.analysis_id != analysis_id,
            WgsExecutionDispatch.desired_target == target,
            WgsExecutionDispatch.dispatch_state.in_(("committed", "running")),
        ).limit(1)
    )
    slot = session.get(WgsExecutionTargetSlot, target)
    if active is not None or (slot is not None and slot.analysis_id not in {None, analysis_id}):
        return _local_unavailable(target, label, "busy", "Another WGS batch owns this node", metrics)
    cpu_limit = float(getattr(settings, "wgs_local_admission_cpu_percent", 25.0))
    load_limit = float(getattr(settings, "wgs_local_admission_load_ratio", 0.25))
    for point in history:
        cpu = _metric(point, "cpu_used_percent", "cpu_percent")
        load = _metric(point, "node_load1", "load1")
        point_cpus = _number(point.get("logical_cpu_count")) or cpu_count
        if cpu is None or load is None or point_cpus is None or point_cpus <= 0:
            return _local_unavailable(target, label, "stale", "The latest three node samples are incomplete", metrics)
        if cpu >= cpu_limit or load / point_cpus >= load_limit:
            return _local_unavailable(
                target,
                label,
                "high_load",
                "CPU and normalized Load1 must both stay below 25% for the latest three samples",
                metrics,
            )
    return {
        "mode": "local",
        "target": target,
        "label": label,
        "status": "available",
        "available": True,
        "reason": None,
        "metrics": metrics,
        "warning": "Memory usage is at least 75%" if (_memory_percent(current) or 0) >= 75 else None,
    }


def _local_unavailable(target: str, label: str, status: str, reason: str, metrics=None) -> dict[str, Any]:
    return {
        "mode": "local",
        "target": target,
        "label": label,
        "status": status,
        "available": False,
        "reason": reason,
        "metrics": metrics,
    }


def _safe_metrics(current: dict[str, Any], source_at: datetime) -> dict[str, Any]:
    return {
        "cpu_percent": _metric(current, "cpu_used_percent", "cpu_percent"),
        "load1": _metric(current, "node_load1", "load1"),
        "load5": _metric(current, "node_load5", "load5"),
        "load15": _metric(current, "node_load15", "load15"),
        "memory_percent": _memory_percent(current),
        "logical_cpu_count": _number(current.get("logical_cpu_count")),
        "updated_at": source_at.isoformat(),
    }


def _metric(payload: dict[str, Any], primary: str, legacy: str) -> float | None:
    value = _number(payload.get(primary))
    return value if value is not None else _number(payload.get(legacy))


def _memory_percent(payload: dict[str, Any]) -> float | None:
    reported = _number(payload.get("memory_percent"))
    if reported is not None:
        return reported
    total = _number(payload.get("node_memory_MemTotal_bytes"))
    available = _number(payload.get("node_memory_MemAvailable_bytes"))
    if total is None or available is None or total <= 0:
        return None
    return max(0.0, min(100.0, (total - available) / total * 100.0))


def _acquire_cce_upload_slot(*, session, analysis_id: str, attempt: int) -> bool:
    slot = session.scalar(
        select(ObsTransferLease)
        .where(ObsTransferLease.slot_name == OBS_UPLOAD_SLOT)
        .with_for_update()
    )
    if slot is None:
        return False
    now = _now()
    if slot.analysis_id is not None:
        if slot.analysis_id != analysis_id or slot.attempt != attempt:
            return False
    slot.analysis_id = analysis_id
    slot.attempt = attempt
    slot.transfer_id = f"{analysis_id}-a{attempt}-input"
    slot.leased_at = now
    slot.lease_expires_at = None
    return True


def _acquire_local_slot(*, session, target: str, analysis_id: str, attempt: int) -> bool:
    slot = session.scalar(
        select(WgsExecutionTargetSlot)
        .where(WgsExecutionTargetSlot.target == target)
        .with_for_update()
    )
    if slot is None:
        slot = WgsExecutionTargetSlot(target=target)
        session.add(slot)
        session.flush()
    if slot.analysis_id not in {None, analysis_id}:
        return False
    slot.analysis_id = analysis_id
    slot.attempt = attempt
    slot.acquired_at = _now()
    slot.updated_at = slot.acquired_at
    return True


def _release_local_slot(*, session, dispatch: WgsExecutionDispatch) -> None:
    if dispatch.desired_target not in {"node-97", "node-96"}:
        return
    slot = session.get(WgsExecutionTargetSlot, dispatch.desired_target)
    if slot is not None and slot.analysis_id == dispatch.analysis_id:
        slot.analysis_id = None
        slot.attempt = None
        slot.acquired_at = None
        slot.updated_at = _now()


def _locked_dispatch(session, analysis_id: str) -> WgsExecutionDispatch | None:
    return session.scalar(
        select(WgsExecutionDispatch)
        .where(WgsExecutionDispatch.analysis_id == analysis_id)
        .with_for_update()
    )


def _serialize(row: WgsExecutionDispatch) -> dict[str, Any]:
    return {
        "desired_mode": row.desired_mode,
        "desired_target": row.desired_target,
        "dispatch_state": row.dispatch_state,
        "dispatch_revision": row.dispatch_revision,
        "committed_at": _iso(row.committed_at),
        "committed_attempt": row.committed_attempt,
        "blocking_reason": row.blocking_reason,
    }


def _waiting_reason(target: str) -> str:
    return {
        "cce": "Waiting for CCE upload slot",
        "node-97": "Waiting for Local .97 exclusive slot",
        "node-96": "Waiting for Local .96 exclusive slot",
        "sge-default": "Waiting for SGE dispatch",
    }[target]


def _point_at(point: dict[str, Any]) -> datetime | None:
    value = str(point.get("at") or "")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _aware(parsed)


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _iso(value: datetime | None) -> str | None:
    aware = _aware(value)
    return aware.isoformat() if aware else None


def _now() -> datetime:
    return datetime.now(timezone.utc)
