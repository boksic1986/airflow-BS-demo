from __future__ import annotations

from datetime import datetime, timezone
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AnalysisRun, KubernetesWorkload, WgsMaintenanceAction


ACTION_TYPE = "repair_step4_cram"
LINKAGE_GROUP = "cram"
ACTIVE_ACTION_STATES = {"requested", "queued", "running"}


def get_step4_repair_capability(
    *,
    session: Session,
    run: AnalysisRun,
    execution_enabled: bool,
    runtime_adapter_enabled: bool,
) -> dict[str, object]:
    latest = session.scalar(
        select(WgsMaintenanceAction)
        .where(
            WgsMaintenanceAction.analysis_id == run.analysis_id,
            WgsMaintenanceAction.attempt == run.attempt,
            WgsMaintenanceAction.action_type == ACTION_TYPE,
        )
        .order_by(WgsMaintenanceAction.id.desc())
    )
    reason = _repair_block_reason(
        session,
        run,
        execution_enabled=execution_enabled,
        runtime_adapter_enabled=runtime_adapter_enabled,
    )
    if latest is not None and latest.status in ACTIVE_ACTION_STATES:
        reason = "repair_in_progress"
    return {
        "linkage_group": LINKAGE_GROUP,
        "available": reason is None,
        "reason": reason,
        "latest_action": serialize_maintenance_action(latest) if latest else None,
    }


def request_step4_repair(
    *,
    session: Session,
    airflow_client,
    analysis_id: str,
    requested_by: str,
) -> dict[str, object] | None:
    run = session.scalar(
        select(AnalysisRun).where(
            AnalysisRun.analysis_id == analysis_id,
            AnalysisRun.pipeline_name == "wgs",
        ).with_for_update()
    )
    if run is None:
        return None

    existing = session.scalar(
        select(WgsMaintenanceAction).where(
            WgsMaintenanceAction.analysis_id == analysis_id,
            WgsMaintenanceAction.attempt == run.attempt,
            WgsMaintenanceAction.action_type == ACTION_TYPE,
        )
    )
    if existing is not None:
        return serialize_maintenance_action(existing)

    reason = _repair_block_reason(
        session,
        run,
        execution_enabled=True,
        runtime_adapter_enabled=True,
    )
    if reason is not None:
        raise ValueError(reason)

    action_id = f"step4-cram-{secrets.token_hex(6)}"
    dag_run_id = (
        f"maintenance__{analysis_id}__a{run.attempt}__step4_cram__{action_id[-12:]}"
    )
    continue_after_repair = str(run.status or "").lower() in {
        "failed",
        "cancelled",
        "unknown_interrupted",
    }
    conf = {
        "analysis_id": run.analysis_id,
        "pipeline": "wgs",
        "execution_mode": "cce",
        "attempt": run.attempt,
        "workdir": run.workdir,
        "params": dict(run.params_json or {}),
        "maintenance_mode": "repair_step4",
        "repair_group": LINKAGE_GROUP,
        "continue_after_repair": continue_after_repair,
        "source_dag_run_id": run.dag_run_id,
        "maintenance_action_id": action_id,
    }
    airflow_client.trigger_dag_run("bio_wgs", dag_run_id=dag_run_id, conf=conf)
    action = WgsMaintenanceAction(
        action_id=action_id,
        analysis_id=run.analysis_id,
        attempt=run.attempt,
        action_type=ACTION_TYPE,
        linkage_group=LINKAGE_GROUP,
        status="queued",
        requested_by=requested_by,
        source_dag_run_id=run.dag_run_id,
        maintenance_dag_run_id=dag_run_id,
    )
    session.add(action)
    session.commit()
    session.refresh(action)
    return serialize_maintenance_action(action)


def serialize_maintenance_action(action: WgsMaintenanceAction) -> dict[str, object]:
    return {
        "action_id": action.action_id,
        "analysis_id": action.analysis_id,
        "attempt": action.attempt,
        "action_type": action.action_type,
        "linkage_group": action.linkage_group,
        "status": action.status,
        "requested_by": action.requested_by,
        "source_dag_run_id": action.source_dag_run_id,
        "maintenance_dag_run_id": action.maintenance_dag_run_id,
        "evidence_path": action.evidence_path,
        "error_message": action.error_message,
        "created_at": _iso_datetime(action.created_at),
        "started_at": _iso_datetime(action.started_at),
        "ended_at": _iso_datetime(action.ended_at),
    }


def _repair_block_reason(
    session: Session,
    run: AnalysisRun,
    *,
    execution_enabled: bool,
    runtime_adapter_enabled: bool,
) -> str | None:
    if not execution_enabled or not runtime_adapter_enabled:
        return "runtime_unavailable"
    if run.attempt < 1:
        return "attempt_unavailable"
    succeeded_workloads = session.scalars(
        select(KubernetesWorkload)
        .where(
            KubernetesWorkload.analysis_id == run.analysis_id,
            KubernetesWorkload.attempt == run.attempt,
            KubernetesWorkload.phase == "Succeeded",
        )
    ).all()
    # Step3 ingestion has already checked the exact frozen binding identity.
    # Require its canonical event key instead of coupling repair to a name prefix.
    master_succeeded = any(
        workload.job_name
        and workload.event_id == f"step3:{workload.job_name}"
        for workload in succeeded_workloads
    )
    if not master_succeeded:
        return "master_not_successful"
    stage = str(run.current_stage or "").lower()
    if "step4" not in stage and "publish" not in stage:
        return "not_step4_failure"
    if str(run.status or "").lower() not in {
        "failed",
        "running",
        "publishing",
        "unknown_interrupted",
    }:
        return "not_step4_failure"
    resolved = (run.params_json or {}).get("resolved_runtime")
    repair_groups = resolved.get("repair_groups") if isinstance(resolved, dict) else None
    if not isinstance(repair_groups, dict) or LINKAGE_GROUP not in repair_groups:
        return "repair_contract_unavailable"
    return None


def _iso_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
