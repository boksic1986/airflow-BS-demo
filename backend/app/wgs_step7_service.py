from __future__ import annotations

from datetime import datetime, timezone
import secrets

from sqlalchemy import select

from app.airflow_idempotency import ensure_dag_run
from app.models import AnalysisRun, KubernetesWorkload, ObsTransferLease, RunAttempt, RunStageState, WgsMaintenanceAction
from app.wgs_run_projection import public_wgs_batch
from app.wgs_step4_service import serialize_maintenance_action


ACTION_TYPE = "cleanup_step7_sfs"
ACTIVE_STATES = {"requested", "queued", "running"}


def get_step7_capability(*, session, run: AnalysisRun, execution_enabled: bool,
                         runtime_adapter_enabled: bool) -> dict:
    history = list(session.scalars(
        select(WgsMaintenanceAction)
        .where(
            WgsMaintenanceAction.analysis_id == run.analysis_id,
            WgsMaintenanceAction.attempt == run.attempt,
            WgsMaintenanceAction.action_type == ACTION_TYPE,
        )
        .order_by(WgsMaintenanceAction.id.desc())
    ).all())
    latest = history[0] if history else None
    reason = _block_reason(session, run, execution_enabled, runtime_adapter_enabled)
    if latest:
        if latest.status in ACTIVE_STATES:
            reason = "cleanup_in_progress"
        elif latest.status == "success":
            reason = "cleanup_completed"
        elif latest.status == "failed":
            reason = "cleanup_failed"
    return {
        "available": reason is None,
        "reason": reason,
        "retry_available": bool(
            latest and latest.status == "failed" and _block_reason(
                session, run, execution_enabled, runtime_adapter_enabled
            ) is None
        ),
        "required_batch": _confirmation_batch(run),
        "latest_action": serialize_maintenance_action(latest) if latest else None,
        "history": [serialize_maintenance_action(item) for item in history],
    }


def request_step7_cleanup(*, session, airflow_client, analysis_id: str, batch_confirmation: str,
                          requested_by: str, retry_failed: bool = False,
                          expected_action_id: str | None = None) -> dict | None:
    run = session.scalar(
        select(AnalysisRun).where(
            AnalysisRun.analysis_id == analysis_id,
            AnalysisRun.pipeline_name == "wgs",
        ).with_for_update()
    )
    if run is None:
        return None
    expected_batch = _confirmation_batch(run)
    if batch_confirmation.strip() != expected_batch:
        raise ValueError("batch_confirmation_mismatch")
    existing = session.scalar(
        select(WgsMaintenanceAction).where(
            WgsMaintenanceAction.analysis_id == analysis_id,
            WgsMaintenanceAction.attempt == run.attempt,
            WgsMaintenanceAction.action_type == ACTION_TYPE,
        ).order_by(WgsMaintenanceAction.generation.desc())
    )
    if existing is not None:
        if existing.status == "requested":
            _trigger_step7_action(airflow_client, run, existing)
            existing.status = "queued"
            existing.updated_at = datetime.now(timezone.utc)
            session.commit()
        if not retry_failed:
            return serialize_maintenance_action(existing)
        if existing.status != "failed":
            raise ValueError("step7_retry_requires_failed_action")
        if not expected_action_id or existing.action_id != expected_action_id:
            raise ValueError("stale_step7_action")
    elif retry_failed:
        raise ValueError("step7_retry_requires_failed_action")
    reason = _block_reason(session, run, True, True)
    if reason:
        raise ValueError(reason)
    generation = int(existing.generation if existing else 0) + 1
    action_id = f"step7-sfs-{secrets.token_hex(6)}"
    dag_run_id = f"maintenance__{analysis_id}__a{run.attempt}__step7__{action_id[-12:]}"
    action = WgsMaintenanceAction(
        action_id=action_id,
        analysis_id=analysis_id,
        attempt=run.attempt,
        action_type=ACTION_TYPE,
        generation=generation,
        retry_of_action_id=existing.action_id if existing else None,
        target_snapshot_json=_target_snapshot(session=session, run=run),
        linkage_group="sfs",
        status="requested",
        requested_by=requested_by,
        source_dag_run_id=run.dag_run_id,
        maintenance_dag_run_id=dag_run_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(action)
    session.commit()
    session.refresh(action)
    _trigger_step7_action(airflow_client, run, action)
    action.status = "queued"
    action.updated_at = datetime.now(timezone.utc)
    session.commit()
    return serialize_maintenance_action(action)


def authorize_step7_runtime(*, session, run: AnalysisRun, action_id: str) -> WgsMaintenanceAction:
    action = session.scalar(
        select(WgsMaintenanceAction).where(
            WgsMaintenanceAction.action_id == action_id,
            WgsMaintenanceAction.analysis_id == run.analysis_id,
            WgsMaintenanceAction.attempt == run.attempt,
            WgsMaintenanceAction.action_type == ACTION_TYPE,
        ).with_for_update()
    )
    if action is None or action.status not in ACTIVE_STATES:
        raise ValueError("Step7 cleanup has no active admin maintenance action")
    reason = _block_reason(session, run, True, True)
    if reason:
        raise ValueError(reason)
    return action


def _trigger_step7_action(airflow_client, run: AnalysisRun, action: WgsMaintenanceAction) -> None:
    ensure_dag_run(
        airflow_client=airflow_client,
        dag_id="bio_wgs",
        dag_run_id=str(action.maintenance_dag_run_id),
        conf={
            "analysis_id": run.analysis_id,
            "pipeline": "wgs",
            "execution_mode": "cce",
            "attempt": run.attempt,
            "workdir": run.workdir,
            "params": dict(run.params_json or {}),
            "maintenance_mode": "cleanup_step7",
            "maintenance_action_id": action.action_id,
            "step7_generation": action.generation,
            "step7_target_snapshot": dict(action.target_snapshot_json or {}),
            "source_dag_run_id": run.dag_run_id,
        },
    )


def _block_reason(session, run: AnalysisRun, execution_enabled: bool, runtime_enabled: bool) -> str | None:
    if not execution_enabled or not runtime_enabled:
        return "runtime_unavailable"
    if str(run.status or "").lower() != "success":
        return "run_not_successful"
    stages = {
        row.stage_code: row.stage_status
        for row in session.scalars(
            select(RunStageState).where(
                RunStageState.analysis_id == run.analysis_id,
                RunStageState.attempt == run.attempt,
                RunStageState.stage_code.in_(("step5_download", "step6_materialize")),
            )
        ).all()
    }
    if stages.get("step5_download") != "success":
        return "download_not_verified"
    if stages.get("step6_materialize") != "success":
        return "results_not_materialized"
    workloads = list(session.scalars(
        select(KubernetesWorkload).where(
            KubernetesWorkload.analysis_id == run.analysis_id,
            KubernetesWorkload.attempt == run.attempt,
        )
    ).all())
    active_workloads = [
        row for row in workloads if row.phase in {"Pending", "Running", "Active"}
    ]
    terminal_masters = [
        row
        for row in workloads
        if row.phase == "Succeeded"
        and str((row.resources_json or {}).get("workload_role") or "master") == "master"
    ]
    latest_master = max(terminal_masters, key=_workload_timestamp, default=None)
    if active_workloads and (
        latest_master is None
        or any(_workload_timestamp(row) > _workload_timestamp(latest_master) for row in active_workloads)
    ):
        return "cce_workload_active"
    active_lease = session.scalar(
        select(ObsTransferLease.slot_name).where(
            ObsTransferLease.analysis_id == run.analysis_id,
            ObsTransferLease.attempt == run.attempt,
        ).limit(1)
    )
    if active_lease is not None:
        return "transfer_lease_active"
    return None


def _workload_timestamp(row: KubernetesWorkload) -> datetime:
    value = row.observed_at or row.updated_at
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _confirmation_batch(run: AnalysisRun) -> str:
    """Return the privacy-safe public batch identity used for typed confirmation."""

    return str(public_wgs_batch(run.params_json) or "").strip()


def _target_snapshot(*, session, run: AnalysisRun) -> dict[str, object]:
    params = dict(run.params_json or {})
    attempt = session.scalar(
        select(RunAttempt).where(
            RunAttempt.analysis_id == run.analysis_id,
            RunAttempt.attempt == run.attempt,
        )
    )
    resolved = params.get("resolved_runtime")
    resolved = resolved if isinstance(resolved, dict) else {}
    return {
        "analysis_id": run.analysis_id,
        "attempt": run.attempt,
        "project": str(params.get("project_name") or ""),
        "batch": _confirmation_batch(run),
        "run_id": f"{run.analysis_id}-a{run.attempt}",
        "run_label": str((attempt.run_label if attempt else None) or resolved.get("run_label") or ""),
        "namespace": str(resolved.get("namespace") or ""),
    }
