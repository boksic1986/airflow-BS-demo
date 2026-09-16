"""Explicit GATK SFS maintenance; never changes scientific-run state."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import yaml

from sqlalchemy import select
from app.airflow_idempotency import ensure_dag_run
from app.models import AnalysisRun, KubernetesWorkload, ObsTransferLease, PipelineStageExecution, WgsMaintenanceAction
from app.gatk_runtime_service import _atomic_json, _canonical_hash, _request_path
from app.wgs_step4_service import serialize_maintenance_action

ACTION = 'gatk_cleanup_step7_sfs'
ACTIVE = {'requested', 'queued', 'running'}
FROZEN_FILES = {'BATCH_RUNTIME.yaml','cleanup-job.yaml','Step7_cleanup_sfs.sh','cce_batch_runtime.py'}


def _safe_bytes(path, root):
    path,root=Path(path),Path(root)
    if root not in path.parents or any(item.is_symlink() for item in (path,*path.parents) if item == root or root in item.parents):
        raise ValueError('unsafe_frozen_cleanup_path')
    if not path.is_file():
        raise ValueError('frozen_cleanup_file_unavailable')
    return path.read_bytes()


def _latest(session, run):
    return session.scalar(select(WgsMaintenanceAction).where(
        WgsMaintenanceAction.analysis_id == run.analysis_id,
        WgsMaintenanceAction.attempt == run.attempt,
        WgsMaintenanceAction.action_type == ACTION).order_by(WgsMaintenanceAction.generation.desc()))


def _receipt(session, run, stage):
    row = session.scalar(select(PipelineStageExecution).where(
        PipelineStageExecution.analysis_id == run.analysis_id,
        PipelineStageExecution.pipeline_name == 'gatk',
        PipelineStageExecution.attempt == run.attempt,
        PipelineStageExecution.stage_code == stage).order_by(PipelineStageExecution.generation.desc()))
    if row is None or row.status != 'success' or not row.receipt_hash:
        raise ValueError(stage + '_not_verified')
    return row


def _check(session, settings, run):
    if not getattr(settings, 'gatk_execution_enabled', False):
        raise ValueError('runtime_unavailable')
    if run.pipeline_name != 'gatk' or run.status != 'success':
        raise ValueError('run_not_successful')
    _receipt(session, run, 'step5_download')
    receipt = _receipt(session, run, 'step6_materialize')
    if session.scalar(select(ObsTransferLease.slot_name).where(
        ObsTransferLease.analysis_id == run.analysis_id,
        ObsTransferLease.attempt == run.attempt).limit(1)):
        raise ValueError('transfer_lease_active')
    workloads = session.scalars(select(KubernetesWorkload).where(
        KubernetesWorkload.analysis_id == run.analysis_id,
        KubernetesWorkload.attempt == run.attempt)).all()
    if any(row.phase not in {'Succeeded', 'Failed'} and not (
        row.phase == 'Deleted' and row.reason == 'PodNotFound'
    ) for row in workloads):
        raise ValueError('cce_workload_active')
    return receipt


def _snapshot(settings, run, receipt):
    try:
        return _snapshot_files(settings,run,receipt)
    except (OSError,yaml.YAMLError) as exc:
        raise ValueError('frozen_cleanup_file_unavailable') from exc


def _snapshot_files(settings, run, receipt):
    root = Path(settings.gatk_runtime_request_root).resolve().parent
    path = root/'runs'/run.analysis_id/f'attempt-{run.attempt}'/'batch-binding.json'
    try:
        raw = _safe_bytes(path,root)
        binding = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise ValueError('frozen_binding_unavailable') from exc
    if (binding.get('schema_version') != 'gatk-runtime.batch-binding.v1'
        or binding.get('analysis_id') != run.analysis_id or binding.get('attempt') != run.attempt):
        raise ValueError('frozen_binding_mismatch')
    prepare_raw=_safe_bytes(root/'requests'/run.analysis_id/f'attempt-{run.attempt}'/'prepare.request.json',root)
    prepare=json.loads(prepare_raw)
    if (prepare.get('analysis_id') != run.analysis_id or prepare.get('attempt') != run.attempt
        or prepare.get('batch') != (run.params_json or {}).get('batch')
        or prepare.get('request_hash') != _canonical_hash({k:v for k,v in prepare.items() if k != 'request_hash'})):
        raise ValueError('approved_prepare_identity_mismatch')
    bundle=path.parent/'cce'
    hashes={name:hashlib.sha256(_safe_bytes(bundle/name,root)).hexdigest()
        for name in FROZEN_FILES | {p.name for p in bundle.iterdir() if p.suffix in {'.py','.sh'}}}
    runtime=yaml.safe_load(_safe_bytes(bundle/'BATCH_RUNTIME.yaml',root))
    identity=runtime.get('identity') or {}
    if (identity.get('project') != prepare.get('project_name') or not prepare.get('project_name')
        or identity.get('batch') != prepare.get('batch')
        or identity.get('run_id') != f'{run.analysis_id}-a{run.attempt}'):
        raise ValueError('approved_runtime_identity_mismatch')
    return {'analysis_id':run.analysis_id, 'attempt':run.attempt,
        'approved_project':prepare['project_name'],'approved_batch':prepare['batch'],
        'prepare_sha256':hashlib.sha256(prepare_raw).hexdigest(),'bundle_hashes':hashes,
        'binding_sha256':hashlib.sha256(raw).hexdigest(),
        'run_id':str(binding.get('run_id') or run.analysis_id+f'-a{run.attempt}'),
        'predecessor_execution_id':receipt.execution_id,
        'predecessor_generation':receipt.generation,
        'predecessor_receipt_hash':receipt.receipt_hash}


def capability(*, session, settings, run):
    latest = _latest(session, run)
    reason = None
    try:
        receipt = _check(session, settings, run)
        _snapshot(settings, run, receipt)
    except ValueError as exc:
        reason = str(exc)
    blocked = reason
    observed_status=latest.status if latest else None
    if latest and latest.status == 'failed' and not blocked:
        try:
            state=_runtime_terminal(settings,run,latest)
            if state == 'success':
                observed_status='success'
        except ValueError as exc:
            blocked=str(exc)
    if latest:
        reason = {'success':'cleanup_completed', 'failed':'cleanup_failed'}.get(observed_status, 'cleanup_in_progress')
        if observed_status == 'failed' and blocked:
            reason=blocked
    return {'available': reason is None, 'reason':reason,
        'retry_available':bool(latest and observed_status == 'failed' and not blocked),
        'required_batch':str((run.params_json or {}).get('batch') or ''),
        'latest_action':({**serialize_maintenance_action(latest),'status':observed_status,
            **({'error_message':None} if observed_status == 'success' else {})} if latest else None),
        'history':[serialize_maintenance_action(row) for row in session.scalars(select(WgsMaintenanceAction).where(
            WgsMaintenanceAction.analysis_id == run.analysis_id,
            WgsMaintenanceAction.attempt == run.attempt,
            WgsMaintenanceAction.action_type == ACTION).order_by(WgsMaintenanceAction.generation.desc()))]}


def request_cleanup(*, session, settings, airflow_client, analysis_id, batch_confirmation,
                    requested_by, retry_failed=False, expected_action_id=None):
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id,
        AnalysisRun.pipeline_name == 'gatk').with_for_update())
    if run is None:
        return None
    expected = str((run.params_json or {}).get('batch') or '')
    if not expected or batch_confirmation.strip() != expected:
        raise ValueError('batch_confirmation_mismatch')
    receipt = _check(session, settings, run)
    existing = _latest(session, run)
    if existing and not retry_failed:
        if existing.status == 'requested':
            _trigger(airflow_client, run, existing)
            existing.status = 'queued'
            session.commit()
        return serialize_maintenance_action(existing)
    if retry_failed and (not existing or existing.status != 'failed' or existing.action_id != expected_action_id):
        raise ValueError('stale_step7_action')
    if retry_failed:
        state=_runtime_terminal(settings,run,existing)
        if state == 'success':
            existing.status='success'
            existing.error_message=None
            existing.ended_at=existing.updated_at=datetime.now(timezone.utc)
            session.commit()
            return serialize_maintenance_action(existing)
    action_id = 'gatk-step7-'+secrets.token_hex(6)
    action = WgsMaintenanceAction(action_id=action_id, analysis_id=analysis_id,
        attempt=run.attempt, action_type=ACTION, generation=existing.generation+1 if existing else 1,
        retry_of_action_id=existing.action_id if existing else None,
        target_snapshot_json=_snapshot(settings, run, receipt), linkage_group='sfs',
        status='requested', requested_by=requested_by, source_dag_run_id=run.dag_run_id,
        maintenance_dag_run_id=f'maintenance__{analysis_id}__a{run.attempt}__{action_id}')
    session.add(action)
    session.commit()
    _trigger(airflow_client, run, action)
    action.status = 'queued'
    session.commit()
    return serialize_maintenance_action(action)


def _runtime_terminal(settings,run,action):
    try:
        sidecar=_read_cleanup_receipt(settings,run,action)
    except (OSError,ValueError) as exc:
        raise ValueError('previous_cleanup_runtime_not_terminal') from exc
    if sidecar.get('status') not in {'success','failed','canceled'}:
        raise ValueError('previous_cleanup_runtime_not_terminal')
    return sidecar['status']


def _read_cleanup_receipt(settings,run,action):
    root=Path(settings.gatk_runtime_request_root).resolve()
    path=_request_path(settings,run.analysis_id,run.attempt,'step7_cleanup')
    try:
        request=json.loads(_safe_bytes(path,root))
        sidecar=json.loads(_safe_bytes(path.with_suffix('.status.json'),root))
    except (OSError,ValueError) as exc:
        raise ValueError('previous_cleanup_runtime_not_terminal') from exc
    if (request.get('analysis_id') != run.analysis_id or request.get('attempt') != run.attempt
        or request.get('stage') != 'step7_cleanup'
        or request.get('execution_id') != f'{run.analysis_id}-a{run.attempt}-step7_cleanup-g{action.generation}'
        or request.get('maintenance_action_id') != action.action_id
        or request.get('generation') != action.generation
        or request.get('request_hash') != _canonical_hash({k:v for k,v in request.items() if k != 'request_hash'})
        or any(sidecar.get(key) != request.get(key) for key in ('analysis_id','attempt','stage','generation','execution_id','request_hash'))
        or (sidecar.get('status') in {'success','failed','canceled'} and sidecar.get('receipt_hash') != _canonical_hash({k:v for k,v in sidecar.items() if k != 'receipt_hash'}))):
        raise ValueError('maintenance_sidecar_identity_mismatch')
    return sidecar


def _trigger(airflow, run, action):
    ensure_dag_run(airflow_client=airflow, dag_id='bio_gatk_maintenance',
        dag_run_id=action.maintenance_dag_run_id, conf={'analysis_id':run.analysis_id,
        'pipeline':'gatk','attempt':run.attempt,'maintenance_action_id':action.action_id})


def _action(session, analysis_id, attempt, action_id):
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id,
        AnalysisRun.pipeline_name == 'gatk').with_for_update())
    if run is None or run.attempt != attempt:
        raise ValueError('unknown_active_gatk_attempt')
    action = _latest(session, run)
    if action is None or action.action_id != action_id:
        raise ValueError('stale_step7_action')
    return run, action


def register_cleanup(*, session, settings, analysis_id, attempt, action_id):
    run, action = _action(session, analysis_id, attempt, action_id)
    receipt = _check(session, settings, run)
    if action.status not in ACTIVE:
        raise ValueError('maintenance_action_not_active')
    if _snapshot(settings, run, receipt) != action.target_snapshot_json:
        raise ValueError('frozen_cleanup_identity_changed')
    workdir = Path(settings.gatk_runtime_node200_root)/'runs'/analysis_id/f'attempt-{attempt}'
    request = {**action.target_snapshot_json, 'schema_version':'gatk-runtime.request.v1',
        'pipeline':'gatk', 'stage':'step7_cleanup', 'generation':action.generation,
        'orchestration_contract_version':2, 'maintenance_action_id':action.action_id,
        'execution_id':f'{analysis_id}-a{attempt}-step7_cleanup-g{action.generation}',
        'runtime_workdir':str(workdir),'cce_bundle':str(workdir/'cce')}
    request['request_hash'] = _canonical_hash(request)
    _atomic_json(_request_path(settings, analysis_id, attempt, 'step7_cleanup'), request)
    action.status = 'running'
    action.started_at = action.started_at or datetime.now(timezone.utc)
    session.commit()
    return request


def sync_cleanup(*, session, settings, analysis_id, attempt, action_id):
    run, action = _action(session, analysis_id, attempt, action_id)
    request_path = _request_path(settings, analysis_id, attempt, 'step7_cleanup')
    sidecar = request_path.with_suffix('.status.json')
    if sidecar.is_file() and request_path.is_file() and action.status in ACTIVE | {'failed'}:
        value = _read_cleanup_receipt(settings,run,action)
        state = value.get('status')
        if state in {'running','success','failed','canceled'} and (action.status != 'failed' or state == 'success'):
            action.status = 'failed' if state == 'canceled' else state
            action.error_message = str(value.get('message') or '') if state != 'success' else None
            action.updated_at = datetime.now(timezone.utc)
            if state in {'success','failed','canceled'}:
                action.ended_at = action.updated_at
            session.commit()
    return {'status':action.status,'ready':action.status == 'success','failed':action.status == 'failed',
        'message':action.error_message,'action_id':action.action_id}


def mark_cleanup_failed(*, session, analysis_id, attempt, action_id):
    _, action = _action(session, analysis_id, attempt, action_id)
    if action.status in ACTIVE:
        action.status = 'failed'
        action.error_message = 'Maintenance orchestration failed; inspect the exact runtime receipt before retrying.'
        action.ended_at = action.updated_at = datetime.now(timezone.utc)
        session.commit()
    return {'status':action.status,'action_id':action.action_id}
