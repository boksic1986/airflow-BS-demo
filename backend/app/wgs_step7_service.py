from __future__ import annotations

from datetime import datetime, timezone
import secrets
import json
import hashlib
from pathlib import Path

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
    dag_run_id = f"wgs_maintenance__{analysis_id}__a{run.attempt}__step7__{action_id[-12:]}"
    action = WgsMaintenanceAction(
        action_id=action_id,
        analysis_id=analysis_id,
        attempt=run.attempt,
        action_type=ACTION_TYPE,
        generation=generation,
        retry_of_action_id=existing.action_id if existing else None,
        target_snapshot_json=(dict(existing.target_snapshot_json or {}) if existing
                              else _target_snapshot(session=session, run=run)),
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
        dag_id=("bio_wgs_maintenance" if str(action.maintenance_dag_run_id).startswith('wgs_maintenance__') else "bio_wgs"),
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
            "step7_previous_action_id": action.retry_of_action_id,
            "step7_previous_generation": action.generation - 1 if action.retry_of_action_id else None,
            "step7_target_snapshot": dict(action.target_snapshot_json or {}),
            "source_dag_run_id": run.dag_run_id,
        },
    )


def maintenance_context(*, session, request_root, analysis_id, action_id, attempt, generation, dag_run_id):
    latest = session.scalar(select(WgsMaintenanceAction).where(
        WgsMaintenanceAction.analysis_id == analysis_id, WgsMaintenanceAction.attempt == attempt,
        WgsMaintenanceAction.action_type == ACTION_TYPE).order_by(WgsMaintenanceAction.generation.desc()))
    if (not latest or latest.action_id != action_id or latest.generation != generation
            or latest.maintenance_dag_run_id != dag_run_id):
        raise ValueError('stale_step7_observation')
    root = Path(request_root).resolve()
    path = root / analysis_id / f'attempt-{attempt}' / 'step7_cleanup.json'
    if root not in path.resolve().parents or path.is_symlink():
        raise ValueError('unsafe_step7_request')
    if not path.exists():
        if latest.retry_of_action_id:
            raise ValueError('Step7 prior request unavailable; cleanup state unknown')
        return {'registered': False}
    payload = json.loads(path.read_text())
    source = session.scalar(select(WgsMaintenanceAction).where(
        WgsMaintenanceAction.analysis_id == analysis_id, WgsMaintenanceAction.attempt == attempt,
        WgsMaintenanceAction.action_type == ACTION_TYPE,
        WgsMaintenanceAction.action_id == payload.get('maintenance_action_id')))
    if (not source or source.generation > generation or payload.get('analysis_id') != analysis_id
            or payload.get('attempt') != attempt or payload.get('stage') != 'step7_cleanup'
            or payload.get('step7_generation', 1) != source.generation):
        raise ValueError('Step7 registered identity mismatch')
    result = {'registered': True, 'action': source.action_id, 'generation': source.generation}
    if payload.get('orchestration_contract_version') == 2:
        result['runtime_identity'] = {key: payload.get(key) for key in ('execution_id', 'generation', 'request_hash')}
    return result


def observe_maintenance(*, session, request_root, analysis_id, action_id, attempt,
                        generation, dag_run_id, status, message=''):
    """Fence callbacks without altering the successful biological run."""
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id,
        AnalysisRun.attempt == attempt).with_for_update())
    latest = session.scalar(select(WgsMaintenanceAction).where(
        WgsMaintenanceAction.analysis_id == analysis_id, WgsMaintenanceAction.attempt == attempt,
        WgsMaintenanceAction.action_type == ACTION_TYPE).order_by(WgsMaintenanceAction.generation.desc()))
    if (not run or not latest or latest.action_id != action_id or latest.generation != generation
            or latest.maintenance_dag_run_id != dag_run_id):
        raise ValueError('stale_step7_observation')
    if status not in {'running', 'success', 'failed', 'stopped'}:
        raise ValueError('invalid_step7_observation')
    if status == 'stopped':
        # Only the independent DAG sends this after a live, identity-bound probe
        # proves the previous executor has stopped. This is not a timeout callback.
        try:
            source = maintenance_context(session=session, request_root=request_root,
                analysis_id=analysis_id, action_id=action_id, attempt=attempt,
                generation=generation, dag_run_id=dag_run_id)
        except (ValueError, OSError):
            source = {}
        if not source.get('registered') or source['generation'] >= generation:
            raise ValueError('Step7 stopped predecessor identity missing')
        payload = json.loads((Path(request_root) / analysis_id / f'attempt-{attempt}' / 'step7_cleanup.json').read_text())
        if payload.get('orchestration_contract_version') == 2:
            from app.wgs_stage_execution_service import transition_stage_execution
            transition_stage_execution(session=session, execution_id=payload['execution_id'],
                generation=payload['generation'], status='failed',
                message='Step7 executor confirmed stopped before manual retry')
        session.commit()
        return serialize_maintenance_action(latest)
    # An Airflow timeout must not overwrite an exact successful runtime receipt.
    marker = Path(request_root) / analysis_id / f'attempt-{attempt}' / 'step7_cleanup.status.json'
    confirmed_success = False
    if marker.is_file() and not marker.is_symlink():
        try:
            evidence = json.loads(marker.read_text())
        except (OSError, ValueError):
            evidence = {}
        identities = {(action_id, generation)}
        if latest.retry_of_action_id:
            identities.add((latest.retry_of_action_id, generation - 1))
        try:
            source = maintenance_context(session=session, request_root=request_root,
                analysis_id=analysis_id, action_id=action_id, attempt=attempt,
                generation=generation, dag_run_id=dag_run_id)
        except (ValueError, OSError):
            source = {}
        if source.get('registered'):
            identities.add((source['action'], source['generation']))
        if (evidence.get('schema_version') == 'wgs-runtime.stage-status.v1'
                and evidence.get('analysis_id') == analysis_id and evidence.get('attempt') == attempt
                and evidence.get('stage') == 'step7_cleanup'
                and (evidence.get('maintenance_action_id'), evidence.get('step7_generation', 1)) in identities
                and (evidence.get('orchestration_contract_version') != 2 or
                     bool(source.get('runtime_identity')) and all(evidence.get(key) == value
                         for key, value in source['runtime_identity'].items()))
                and evidence.get('status') == 'success'):
            from app.wgs_observer import upsert_stage_state
            if evidence.get('orchestration_contract_version') == 2:
                from app.wgs_stage_execution_service import transition_stage_execution
                accepted = transition_stage_execution(session=session, execution_id=evidence['execution_id'],
                    generation=evidence['generation'], status='success',
                    receipt_hash=hashlib.sha256(marker.read_bytes()).hexdigest(),
                    evidence_type='wgs-runtime.stage-status.v1', terminal_payload=evidence)
            else:
                accepted = True
            if accepted:
                status, message = 'success', ''
                confirmed_success = True
                upsert_stage_state(session, analysis_id=analysis_id, attempt=attempt,
                    stage_code='step7_cleanup', stage_status='success',
                    updated_at=datetime.now(timezone.utc), allow_terminal_retry=True,
                    progress_percent=100, progress_source='wgs-runtime.stage-status.v1')
    if status == 'success' and not confirmed_success:
        status = 'running'  # Wait for the exact receipt on the shared mount.
    if latest.status == 'success':
        return serialize_maintenance_action(latest)
    now = datetime.now(timezone.utc)
    latest.status = status
    latest.error_message = (message or '清理状态待确认：监控已停止，重试前核对原执行')[:500] if status == 'failed' else None
    if status == 'running':
        latest.started_at = latest.started_at or now
        latest.ended_at = None
    else:
        latest.ended_at = now
    latest.updated_at = now
    session.commit()
    return serialize_maintenance_action(latest)


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
