from __future__ import annotations

from datetime import datetime, timezone
import secrets

from sqlalchemy import select

from app.airflow_idempotency import ensure_dag_run
from app.models import AnalysisRun, KubernetesWorkload, RunStageState, WgsMaintenanceAction
from app.wgs_step4_service import serialize_maintenance_action


ACTION_TYPE = "cleanup_step7_sfs"
ACTIVE_STATES = {"requested", "queued", "running"}


def get_step7_capability(*, session, run: AnalysisRun, execution_enabled: bool,
                         runtime_adapter_enabled: bool) -> dict:
    latest = session.scalar(
        select(WgsMaintenanceAction)
        .where(
            WgsMaintenanceAction.analysis_id == run.analysis_id,
            WgsMaintenanceAction.attempt == run.attempt,
            WgsMaintenanceAction.action_type == ACTION_TYPE,
        )
        .order_by(WgsMaintenanceAction.id.desc())
    )
    reason = _block_reason(session, run, execution_enabled, runtime_adapter_enabled)
    if latest and latest.status in ACTIVE_STATES:
        reason = "cleanup_in_progress"
    return {
        "available": reason is None,
        "reason": reason,
        "required_batch": str((run.params_json or {}).get("batch_no") or ""),
        "latest_action": serialize_maintenance_action(latest) if latest else None,
    }


def request_step7_cleanup(*, session, airflow_client, analysis_id: str, batch_confirmation: str,
                          requested_by: str) -> dict | None:
    run = session.scalar(
        select(AnalysisRun).where(
            AnalysisRun.analysis_id == analysis_id,
            AnalysisRun.pipeline_name == "wgs",
        ).with_for_update()
    )
    if run is None:
        return None
    expected_batch = str((run.params_json or {}).get("batch_no") or "")
    if batch_confirmation != expected_batch:
        raise ValueError("batch_confirmation_mismatch")
    existing = session.scalar(
        select(WgsMaintenanceAction).where(
            WgsMaintenanceAction.analysis_id == analysis_id,
            WgsMaintenanceAction.attempt == run.attempt,
            WgsMaintenanceAction.action_type == ACTION_TYPE,
        )
    )
    if existing is not None:
        if existing.status == "requested":
            _trigger_step7_action(airflow_client, run, existing)
            existing.status = "queued"
            existing.updated_at = datetime.now(timezone.utc)
            session.commit()
        return serialize_maintenance_action(existing)
    reason = _block_reason(session, run, True, True)
    if reason:
        raise ValueError(reason)
    action_id = f"step7-sfs-{secrets.token_hex(6)}"
    dag_run_id = f"maintenance__{analysis_id}__a{run.attempt}__step7__{action_id[-12:]}"
    action = WgsMaintenanceAction(
        action_id=action_id,
        analysis_id=analysis_id,
        attempt=run.attempt,
        action_type=ACTION_TYPE,
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
    active = session.scalar(
        select(KubernetesWorkload.id).where(
            KubernetesWorkload.analysis_id == run.analysis_id,
            KubernetesWorkload.attempt == run.attempt,
            KubernetesWorkload.phase.in_(("Pending", "Running", "Active")),
        ).limit(1)
    )
    if active is not None:
        return "cce_workload_active"
    return None
