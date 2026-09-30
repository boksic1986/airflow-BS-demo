"""One existing Airflow sensor poll -> durable recovery action; never a loop."""
from sqlalchemy import select
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from app.models import AnalysisRun, RunAction
from app.cce_recovery_budget import ACTION, FINISHED_ACTIONS, STOPPED, _date, bound_compute_terminal, reserve_compute_recovery
from app.cce_recovery_evidence import validate_schema2_recovery_evidence
from app.cce_recovery_service import reserve_monitored_recovery
from app.cce_compute_dispatch import dispatch_due_recovery
from app.cce_monitor_observation import query_unconfirmed


def poll_compute_recovery(*, session, settings, airflow_client, analysis_id, attempt,
                          pipeline, dag_run_id, resume_action_id, now,
                          worker_observation=None, native_stage_observation=None):
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==analysis_id)
        .with_for_update().execution_options(populate_existing=True))
    if (not run or run.attempt!=attempt or run.pipeline_name!=pipeline
            or pipeline not in {'wgs','gatk'} or run.execution_mode!='cce' or not dag_run_id):
        raise ValueError('unknown recovery polling identity')
    actions = session.scalars(select(RunAction).where(RunAction.analysis_id==analysis_id,
        RunAction.action==ACTION).order_by(RunAction.id.desc()).with_for_update()
        .execution_options(populate_existing=True)).all()
    actions = [a for a in actions if (a.payload_json or {}).get('attempt')==attempt]
    action = actions[0] if actions else None
    # The old sensor may only reconcile the action it originally requested.
    old_caller = bool(action and action.payload_json.get('original_dag_run_id')==dag_run_id
        and action.payload_json.get('original_resume_action_id')==resume_action_id)
    if dag_run_id != run.dag_run_id:
        if not old_caller:
            return dict(status='superseded')
        if action.result_status=='queued':
            return dict(status='delegated',action_id=action.payload_json['action_id'])
        if action.result_status in FINISHED_ACTIONS:
            return dict(status='needs_attention')
    elif (run.params_json or {}).get('resume_action_id')!=resume_action_id:
        return dict(status='superseded')
    if pipeline=='wgs':
        from app.wgs_resume_service import _latest as latest
    else:
        from app.gatk_runtime_service import _latest_gatk as latest
    monitor = latest(session,run,'step3_monitor')
    current_action = next((a for a in actions if a.payload_json.get('action_id')==resume_action_id),None)
    if current_action is None and resume_action_id and dag_run_id == run.dag_run_id:
        manual = session.scalar(select(RunAction).where(RunAction.analysis_id == analysis_id,
            RunAction.action == 'resume_stage').order_by(RunAction.id.desc()).limit(1)
            .with_for_update().execution_options(populate_existing=True))
        if manual and (manual.payload_json or {}).get('action_id') == resume_action_id:
            current_action = manual
    terminal = (bound_compute_terminal(session=session, run=run, action=current_action,
        settings=settings, native_stage_observation=native_stage_observation)
        if (current_action and dag_run_id == run.dag_run_id
            and current_action.payload_json.get('dag_run_id') == dag_run_id) else None)
    if terminal and (monitor is None or any(
            getattr(monitor, key) != terminal['binding'][key]
            for key in ('execution_id', 'generation', 'request_hash', 'receipt_hash'))):
        terminal = None  # A historical permit cannot settle the current monitor.
    initial_native = None
    if (current_action is None and resume_action_id is None
            and dag_run_id == run.dag_run_id and monitor is not None):
        from app.cce_recovery_budget import _marked_native_terminal
        initial_native = _marked_native_terminal(session=session, run=run,
            settings=settings, native_stage_observation=native_stage_observation)
    initial_native_exact = bool(initial_native and initial_native[0]
        and initial_native[1].execution_id == monitor.execution_id
        and initial_native[1].generation == monitor.generation
        and initial_native[1].request_hash == monitor.request_hash
        and initial_native[1].receipt_hash == monitor.receipt_hash
        and monitor.status in {'failed', 'canceled'})
    # The old Step3 reconnect snapshot is UI-only. A fresh exact native terminal
    # can resolve it, while a missing/unknown native observation cannot.
    if monitor and query_unconfirmed(monitor) and terminal is None and not initial_native_exact:
        session.commit()
        return dict(status='needs_attention' if monitor.status=='failed' else 'not_eligible')
    if (current_action and monitor and monitor.status in {'success', 'failed'}
            and dag_run_id == run.dag_run_id and terminal is None):
        session.commit()
        return dict(status='needs_attention')
    if current_action and monitor and dag_run_id==run.dag_run_id:
        data = current_action.payload_json
        if (terminal and monitor.generation==data.get('generation')
                and monitor.execution_id == terminal['binding']['execution_id']
                and data.get('dag_run_id')==dag_run_id and current_action.result_status=='queued'):
            # The same action still authorizes downstream after successful
            # compute; only the automatic budget/manual fence considers it done.
            if data.get('compute_terminal') not in {None, terminal['state']}:
                return dict(status='needs_attention')
            if (data.get('compute_terminal') is None
                    or data.get('compute_terminal_binding') is None):
                current_action.payload_json = dict(data,
                    compute_terminal=terminal['state'],
                    compute_terminal_binding=terminal['binding'])
                session.flush()
    if monitor and monitor.status=='success' and dag_run_id==run.dag_run_id:
        if resume_action_id and (terminal is None or terminal['state'] != 'success'):
            return dict(status='needs_attention')
        session.commit()
        return dict(status='complete')
    policy = (run.params_json or {}).get('cce_recovery_policy')
    if not isinstance(policy,dict) or policy.get('enabled') is not True or policy.get('attempt')!=attempt:
        session.commit()
        return dict(status='not_eligible')
    pending = bool(action and action.result_status in {'reserved','uncertain'}
        and not action.payload_json.get('compute_terminal'))
    try:
        if not pending:
            if (run.status in STOPPED or run.current_stage!='step3_monitor'
                    or not monitor or monitor.status!='failed' or dag_run_id!=run.dag_run_id):
                return dict(status='not_eligible')
            if current_action is None and resume_action_id is not None:
                raise ValueError('current recovery action is missing')
            if terminal is None:
                # Initial marked monitors have no queued action to bind yet.
                # They still need the same native terminal before reserving.
                native = initial_native
                if native is None:
                    from app.cce_recovery_budget import _marked_native_terminal
                    native = _marked_native_terminal(session=session, run=run,
                        settings=settings, native_stage_observation=native_stage_observation)
                if native is not None and (not native[0]
                        or native[1].execution_id != monitor.execution_id
                        or native[1].status != 'failed'):
                    raise ValueError('current native compute terminal is unconfirmed')
            receipt = reserve_monitored_recovery(session=session,analysis_id=analysis_id,attempt=attempt,
                monitor_execution_id=monitor.execution_id,evidence_root=None,now=now)
            action = session.scalar(select(RunAction).where(RunAction.analysis_id==analysis_id,
                RunAction.action==ACTION).order_by(RunAction.id.desc()).limit(1))
            if action.payload_json['action_id']!=receipt['action_id']:
                raise ValueError('automatic reservation was superseded')
        if 'original_dag_run_id' not in action.payload_json:
            action.payload_json = dict(action.payload_json,original_dag_run_id=dag_run_id,
                original_resume_action_id=resume_action_id)
        wait = _worker_wait(session=session,run=run,action=action,monitor=monitor,
            observation=worker_observation,now=now)
        session.commit()  # Sensor reschedule/process restart sees exactly this action.
        if wait is not None:
            return wait
        result = dispatch_due_recovery(session=session,settings=settings,airflow_client=airflow_client,
            analysis_id=analysis_id,attempt=attempt,action_id=action.payload_json['action_id'],now=now)
        if result['status']=='queued':
            return dict(result,status='delegated')
        return result
    except ValueError:
        # Preserve an ambiguous POST for GET-only reconciliation. A proven
        # untransmitted action can terminate so manual intervention is possible.
        if action and action.result_status in {'reserved','uncertain'}:
            if action.payload_json.get('dispatch_state') not in {'post_intent','confirmed'}:
                action.result_status='rejected'
                action.message='Automatic recovery requires manual review'
        session.commit()
        return dict(status='needs_attention')


def _worker_wait(*, session, run, action, monitor, observation, now):
    """One bounded observation per existing sensor poll; no sleeping or dispatch."""
    data = action.payload_json
    wait = deepcopy(data.get('worker_wait'))
    if not wait or data.get('dispatch_state') in {'post_intent','confirmed'}:
        return None
    reserve_compute_recovery(session=session,analysis_id=run.analysis_id,attempt=run.attempt,
        source_execution_id=data['source_execution_id'],source_master_uid=data['source_master_uid'],now=now)
    deadline = _date(wait['deadline'])
    if (deadline != min(_date(wait['started_at'])+timedelta(seconds=600),_date(data['original_deadline']))
            or wait.get('state') not in {'waiting','ready'}):
        raise ValueError('invalid persisted Worker wait')
    if wait['state']=='ready':
        return None
    if now >= deadline:
        raise ValueError('Worker wait deadline exhausted')
    bound = data['evidence_binding']
    if (monitor is None or monitor.status!='failed' or monitor.execution_id!=bound['monitor_execution_id']
            or monitor.generation!=bound['monitor_generation'] or monitor.request_hash!=bound['monitor_request_hash']):
        raise ValueError('Worker wait monitor superseded')
    challenge = wait.get('probe')
    if observation is not None:
        if not isinstance(observation,dict) or not isinstance(observation.get('nonce'),str):
            raise ValueError('invalid Worker observation')
        if challenge and observation.get('nonce')==challenge['nonce']:
            if any(observation.get(k)!=v for k,v in challenge.items()):
                raise ValueError('Worker observation request identity differs')
            original = monitor.terminal_payload_json['cce_recovery_evidence']
            proof = observation.get('cce_recovery_evidence')
            binding = monitor.terminal_payload_json['cce_master_binding']
            result = validate_schema2_recovery_evidence(binding=binding,evidence=proof,
                expected_platform=binding['platform_execution'],allow_active_workers=True)
            # Only live counts may evolve. Never replace the immutable failure
            # cause, FINAL digest, selected Master, phase or submission identity.
            normalized = deepcopy(proof)
            for key in ('active_worker_jobs','active_worker_pods'):
                normalized['terminal'][key] = original['terminal'][key]
            if normalized != original:
                raise ValueError('Worker observation changed the failure proof')
            wait['last_nonce'] = challenge['nonce']
            wait.pop('probe',None)
            if not result['workers_active']:
                wait.update(state='ready',finished_at=now.isoformat())
                action.payload_json = dict(data,worker_wait=wait)
                return None
        elif observation.get('nonce') != wait.get('last_nonce'):
            raise ValueError('Worker observation is not the issued probe')
        # A duplicate consumed reply does not change wait start/deadline or state.
    if 'probe' not in wait:
        wait['probe'] = dict(nonce=uuid4().hex,execution_id=monitor.execution_id,
            generation=monitor.generation,request_hash=monitor.request_hash)
    action.payload_json = dict(data,worker_wait=wait)
    return dict(status='waiting',action_id=data['action_id'],reason='workers_active',
        worker_probe=wait['probe'],worker_wait_deadline=wait['deadline'])
