"""Internal due-action adapter for the existing durable Resume dispatcher.

No scheduler, policy activation or public endpoint. The existing Airflow stage
monitor will call this service. Restricted runtime still independently validates
live Master/Worker quiescence and directory ownership immediately before CREATE.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time

from sqlalchemy import select

from app.models import AnalysisRun, RunAction
from app.cce_recovery_budget import ACTION, STOPPED, _date, reserve_compute_recovery
from app.cce_recovery_service import reserve_monitored_recovery
from app.cce_resume_dispatch import dispatch_recovery


def dispatch_due_recovery(*, session, settings, airflow_client, analysis_id,
                          attempt, action_id, now):
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError('timezone-aware dispatch time required')
    started = time.monotonic()
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        .with_for_update().execution_options(populate_existing=True))
    action = session.scalar(select(RunAction).where(RunAction.analysis_id == analysis_id,
        RunAction.action == ACTION).order_by(RunAction.id.desc()).limit(1)
        .with_for_update().execution_options(populate_existing=True))
    if (run is None or action is None or run.attempt != attempt
            or action.payload_json.get('action_id') != action_id
            or action.payload_json.get('attempt') != attempt
            or action.payload_json.get('workdir') != run.workdir
            or action.payload_json.get('pipeline') != run.pipeline_name
            or run.execution_mode != 'cce'):
        raise ValueError('automatic action is not the current CCE identity')
    data = action.payload_json
    if action.result_status not in {'reserved','uncertain','queued'}:
        raise ValueError('automatic action is already terminal')
    if run.pipeline_name == 'wgs':
        from app.wgs_resume_service import _latest as latest, register_recovery_stage
        if not settings.wgs_contract_v2_enabled:
            raise ValueError('WGS recovery contract is disabled')
        path = Path(settings.wgs_runtime_request_root)/analysis_id/f'attempt-{attempt}'/'step3_monitor.json'
    elif run.pipeline_name == 'gatk':
        from app.gatk_runtime_service import _latest_gatk as latest, register_gatk_stage, _request_path, _validate_recovery_request
        if not settings.gatk_execution_enabled:
            raise ValueError('GATK execution is disabled')
        path = _request_path(settings,analysis_id,attempt,'step3_monitor')
    else:
        raise ValueError('unsupported automatic recovery adapter')

    def check_before_post(current, row):
        # Reuse the one budget/journal/control validator; replay never allocates
        # another slot. Recheck under the shared run lock after slow GET as well.
        stamp = now + timedelta(seconds=time.monotonic()-started)
        saved = reserve_compute_recovery(session=session,analysis_id=analysis_id,attempt=attempt,
            source_execution_id=data['source_execution_id'],source_master_uid=data['source_master_uid'],now=stamp)
        if saved['action_id'] != action_id or current.status in STOPPED:
            raise ValueError('automatic action was superseded or stopped')

    # A POST intent is irrevocably ambiguous: even after expiry/stop, reconcile
    # this exact DagRun by GET. Never recreate an action or spend a second slot.
    if data.get('dispatch_state') not in {'post_intent','confirmed'}:
        check_before_post(run, action)
        if data.get('worker_wait') and data['worker_wait'].get('state') != 'ready':
            return dict(action_id=action_id,status='waiting',reason='workers_active')
        if now < _date(data['next_retry_at']):
            return dict(action_id=action_id,status='waiting',next_retry_at=data['next_retry_at'])
    if 'dag_run_id' not in data:
        evidence = data.get('evidence_binding') or {}
        if not evidence.get('native_binding_sha256'):
            raise ValueError('automatic dispatch requires schema2 native evidence')
        verified = reserve_monitored_recovery(session=session,analysis_id=analysis_id,attempt=attempt,
            monitor_execution_id=evidence['monitor_execution_id'],evidence_root=None,now=now)
        if verified['action_id'] != action_id:
            raise ValueError('automatic evidence reservation changed')
        execution = latest(session,run,'step3_monitor')
        frozen = json.loads(path.read_text())
        if (frozen.get('orchestration_contract_version') != 2
                or frozen.get('analysis_id') != analysis_id or frozen.get('attempt') != attempt
                or frozen.get('stage') != 'step3_monitor'
                or any(frozen.get(key) != getattr(execution,key)
                       for key in ('execution_id','generation','request_hash'))):
            raise ValueError('automatic frozen monitor identity differs')
        if run.pipeline_name == 'gatk':
            _validate_recovery_request(run,execution,frozen)
        elif (frozen.get('pipeline_release_id') != run.params_json.get('pipeline_release_id')
              or frozen.get('wgs_source_commit') != run.params_json.get('wgs_source_commit')
              or frozen.get('control_workdir') != run.workdir):
            raise ValueError('automatic frozen WGS release or directory differs')
        stages = [code for code in ('step3_monitor','step4_publish','step5_download','step6_materialize')
            if not (latest(session,run,code) and latest(session,run,code).status == 'success')]
        action.payload_json = dict(data,stage='step3_monitor',
            original_dag_run_id=run.dag_run_id,dag_run_id=f'{analysis_id}-a{attempt}-{action_id}',
            resume_stages=stages,frozen_request=frozen,dispatch_state='not_started')
        run.params_json = dict(run.params_json or {},resume_action_id=action_id)
        run.dag_run_id = action.payload_json['dag_run_id']
        session.commit()  # Durable identity BEFORE request writes or Airflow POST.

    # Resume a prepared intent without allocating another generation. Existing
    # adapter writers reject mismatched disk/DB identity (including crash gaps).
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        .with_for_update().execution_options(populate_existing=True))
    action = session.scalar(select(RunAction).where(RunAction.id == action.id)
        .with_for_update().execution_options(populate_existing=True))
    if (run.attempt != attempt or run.dag_run_id != action.payload_json['dag_run_id']
            or (run.params_json or {}).get('resume_action_id') != action_id):
        raise ValueError('prepared automatic action was superseded')
    if 'generation' not in action.payload_json:
        check_before_post(run,action)
        # A crash after preparation must not turn the frozen snapshot into
        # independent authority. Revalidate the original current failed receipt.
        reserve_monitored_recovery(session=session,analysis_id=analysis_id,attempt=attempt,
            monitor_execution_id=action.payload_json['evidence_binding']['monitor_execution_id'],
            evidence_root=None,now=now)
        if run.pipeline_name == 'wgs':
            payload = register_recovery_stage(session=session,settings=settings,run=run,
                stage='step3_monitor',action=action)
        else:
            payload = register_gatk_stage(session=session,settings=settings,analysis_id=analysis_id,
                attempt=attempt,stage='step3_monitor',recovery_action=action,commit=False)
        conf = dict(analysis_id=analysis_id,attempt=attempt,pipeline=run.pipeline_name,execution_mode='cce',
            workdir=run.workdir,params=run.params_json,resume_stage='step3_monitor',
            resume_action_id=action_id,resume_stages=action.payload_json['resume_stages'])
        action.payload_json = dict(action.payload_json,generation=payload['generation'],conf=conf)
        session.commit()
    action = dispatch_recovery(session=session,run=run,action=action,airflow_client=airflow_client,
        latest_execution=latest,before_post=check_before_post)
    return dict(action_id=action_id,status=action.result_status,generation=action.payload_json['generation'])
