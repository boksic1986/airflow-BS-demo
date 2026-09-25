"""Step4 same-operation dispatch budget; internal and default-off.

The caller commits the returned dispatch intent BEFORE SSH, and acknowledges its
sequence only when that exact local SSH invocation has exited. A crashed caller
leaves in_flight set: negative remote evidence alone cannot grant another send.
Airflow owns rescheduling. No new execution, compute budget or background timer.
"""
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from app.models import AnalysisRun, RunAction, WgsStageExecution, PipelineStageExecution, WgsMaintenanceAction
from app.cce_recovery_budget import STOPPED, CONTROL_ACTIONS, FINISHED_ACTIONS, _date

ACTION = 'cce_publish_dispatch'
DELAYS = (60, 180)
TERMINAL = {'success', 'failed', 'canceled', 'stopped', 'expired', 'exhausted'}


def freeze_publish_request(*, run, request, latest, now, timeout_seconds):
    """Only first Step4 may establish the same-attempt original stage deadline."""
    params = dict(run.params_json or {})
    policy = params.get('cce_recovery_policy') or {}
    if policy.get('enabled') is not True or policy.get('attempt') != run.attempt:
        return
    if (run.execution_mode != 'cce' or policy.get('version') != 1
            or type(timeout_seconds) is not int or timeout_seconds <= 0 or now.tzinfo is None):
        raise ValueError('invalid Step4 policy or timeout')
    deadline = params.get('cce_publish_deadline')
    if deadline is None:
        if latest is not None:
            raise ValueError('existing Step4 has no original publish deadline')
        deadline = (now + timedelta(seconds=timeout_seconds)).isoformat()
        run.params_json = dict(params,cce_publish_deadline=deadline)
    _date(deadline)
    request.update(publish_dispatch_version=1,publish_deadline=deadline)


def _controls(session, run, resume_action_id):
    if (run.params_json or {}).get('resume_action_id') != resume_action_id:
        raise ValueError('Step4 recovery caller was superseded')
    if resume_action_id:
        from app.cce_resume_dispatch import authorize_recovery_stage
        authorize_recovery_stage(session=session,run=run,action_id=resume_action_id,
            dag_run_id=run.dag_run_id,stage='step4_publish')
    for row in session.scalars(select(RunAction).where(RunAction.analysis_id==run.analysis_id)):
        data=row.payload_json or {}
        if data.get('attempt') not in {None,run.attempt}:continue
        if row.action in CONTROL_ACTIONS | {'cce_compute_recovery'} and row.result_status not in FINISHED_ACTIONS:
            if (row.action in {'resume_stage','cce_compute_recovery'}
                    and data.get('action_id')==resume_action_id and resume_action_id):continue
            raise ValueError('active control or recovery action blocks Step4 dispatch')
    if any(row.status not in FINISHED_ACTIONS for row in session.scalars(select(WgsMaintenanceAction)
            .where(WgsMaintenanceAction.analysis_id==run.analysis_id,WgsMaintenanceAction.attempt==run.attempt))):
        raise ValueError('active maintenance blocks Step4 dispatch')


def authorize_publish_registration(*, session, run, dag_run_id, resume_action_id):
    policy=(run.params_json or {}).get('cce_recovery_policy') or {}
    if policy.get('enabled') is not True or policy.get('attempt')!=run.attempt:
        return
    if not dag_run_id or dag_run_id!=run.dag_run_id or run.status in STOPPED:
        raise ValueError('Step4 registration is not current or was stopped')
    _controls(session,run,resume_action_id)


def control_publish_dispatch(*, session, settings, pipeline, analysis_id, attempt,
        dag_run_id, resume_action_id, operation, now, execution_id=None, sequence=None, observation=None):
    """Authenticated stage route owns commit; no SSH or arbitrary path from caller."""
    run=session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id==analysis_id)
        .with_for_update().execution_options(populate_existing=True))
    if not run or pipeline not in {'wgs','gatk'} or run.pipeline_name!=pipeline or run.attempt!=attempt:
        raise ValueError('unknown Step4 caller')
    _controls(session,run,resume_action_id)
    model=WgsStageExecution if pipeline=='wgs' else PipelineStageExecution
    query=select(model).where(model.analysis_id==analysis_id,model.attempt==attempt,model.stage_code=='step4_publish')
    if pipeline=='gatk':query=query.where(model.pipeline_name==pipeline)
    row=session.scalar(query.order_by(model.generation.desc()).limit(1))
    if row is None or (execution_id is not None and execution_id!=row.execution_id):
        raise ValueError('Step4 caller execution was superseded')
    # Use only the exact registered request; never backfill a historical marker.
    root=Path(getattr(settings,pipeline+'_runtime_request_root')).resolve()
    filename='step4_publish.json' if pipeline=='wgs' else 'step4_publish.request.json'
    path=root/analysis_id/f'attempt-{attempt}'/filename
    if not path.resolve().is_relative_to(root) or path.is_symlink() or path.stat().st_size>2*1024*1024:
        raise ValueError('invalid registered Step4 request path')
    request=json.loads(path.read_bytes())
    excluded={'request_hash'} if pipeline=='gatk' else {'execution_id','generation','request_hash',
        'predecessor_execution_id','predecessor_generation','predecessor_receipt_hash'}
    digest=hashlib.sha256(json.dumps({k:v for k,v in request.items() if k not in excluded},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if (request.get('analysis_id')!=analysis_id or request.get('attempt')!=attempt
            or request.get('stage')!='step4_publish' or request.get('orchestration_contract_version')!=2
            or type(request.get('publish_dispatch_version')) is not int or request['publish_dispatch_version']!=1
            or any(request.get(k)!=getattr(row,k) for k in ('execution_id','generation','request_hash'))
            or digest!=row.request_hash or request.get('publish_deadline')!=(run.params_json or {}).get('cce_publish_deadline')):
        raise ValueError('registered Step4 dispatch authority differs')
    deadline=_date(request['publish_deadline'])
    args=dict(session=session,analysis_id=analysis_id,attempt=attempt,dag_run_id=dag_run_id,
        execution_id=row.execution_id,now=now)
    if operation=='begin':answer=begin_publish_dispatch(**args,deadline=deadline)
    elif operation=='finish':
        if execution_id is None:raise ValueError('exited Step4 call identity is required')
        answer=finish_publish_dispatch(**args,sequence=sequence)
    elif operation=='poll':answer=poll_publish_dispatch(**args,observation=observation)
    elif operation=='check':
        _,_,action,_=_locked(**args)
        if (action is None or execution_id is None or type(sequence) is not int
                or action.payload_json['sequence']!=sequence or not action.payload_json['in_flight']
                or action.result_status in TERMINAL or run.status in STOPPED or now>=deadline):
            raise ValueError('Step4 send is no longer authorized')
        answer=_answer(action)
    else:raise ValueError('unknown Step4 dispatch operation')
    session.commit()  # Persistent intent / challenge always precedes external I/O.
    return answer


def _locked(session, analysis_id, attempt, dag_run_id, execution_id, now):
    if now.tzinfo is None:
        raise ValueError('Step4 requires an absolute clock')
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        .with_for_update().execution_options(populate_existing=True))
    if (run is None or type(attempt) is not int or run.attempt != attempt
            or run.execution_mode != 'cce' or run.pipeline_name not in {'wgs','gatk'}
            or run.current_stage != 'step4_publish' or not dag_run_id or run.dag_run_id != dag_run_id):
        raise ValueError('Step4 operation is not current')
    policy = (run.params_json or {}).get('cce_recovery_policy') or {}
    if (policy.get('enabled') is not True or policy.get('version') != 1
            or type(policy.get('attempt')) is not int or policy['attempt'] != attempt):
        raise ValueError('Step4 automatic dispatch policy is disabled')
    model = WgsStageExecution if run.pipeline_name == 'wgs' else PipelineStageExecution
    query = select(model).where(model.analysis_id == analysis_id, model.attempt == attempt,
        model.stage_code == 'step4_publish')
    if model is PipelineStageExecution: query = query.where(model.pipeline_name == run.pipeline_name)
    execution = session.scalar(query.order_by(model.generation.desc()).limit(1)
        .with_for_update().execution_options(populate_existing=True))
    if not execution or execution.execution_id != execution_id:
        raise ValueError('Step4 execution was superseded')
    identity = dict(pipeline=run.pipeline_name, analysis_id=analysis_id, attempt=attempt,
        stage='step4_publish', execution_id=execution_id, generation=execution.generation,
        request_hash=execution.request_hash)
    action = None
    for row in session.scalars(select(RunAction).where(RunAction.analysis_id == analysis_id,
            RunAction.action == ACTION).with_for_update().execution_options(populate_existing=True)):
        data = row.payload_json
        if not isinstance(data, dict) or 'attempt' not in data:
            raise ValueError('Step4 action lacks identity')
        if data['attempt'] != attempt or data.get('execution_id') != execution_id: continue
        if (action is not None or any(data.get(k) != v for k,v in identity.items())
                or data.get('dag_run_id') != dag_run_id or data.get('release_id') != execution.release_id
                or data.get('workdir') != run.workdir):
            raise ValueError('Step4 action identity changed')
        action = row
    return run, execution, action, identity


def _answer(action, *, dispatch=False):
    data = action.payload_json
    return dict(status=action.result_status, dispatch=dispatch, action_id=data['action_id'],
        execution_id=data['execution_id'], generation=data['generation'], request_hash=data['request_hash'],
        sequence=data['sequence'], deadline=data['deadline'], next_retry_at=data.get('next_retry_at'),
        probe=data.get('probe'))


def begin_publish_dispatch(*, session, analysis_id, attempt, dag_run_id, execution_id, deadline, now):
    """Called at first registered Step4, with its trusted original stage deadline."""
    run, execution, action, identity = _locked(session,analysis_id,attempt,dag_run_id,execution_id,now)
    if action:
        if _date(action.payload_json['deadline']) != deadline:
            raise ValueError('Step4 original deadline changed')
        return _answer(action)  # Lost begin reply never authorizes a second initial send.
    if deadline.tzinfo is None or deadline <= now or run.status in STOPPED or execution.status != 'accepted':
        raise ValueError('Step4 initial dispatch is not eligible')
    action = RunAction(analysis_id=analysis_id,action=ACTION,requested_by='airflow',result_status='uncertain',
        payload_json=dict(identity,action_id=uuid4().hex,dag_run_id=dag_run_id,release_id=execution.release_id,
            workdir=run.workdir,deadline=deadline.isoformat(),sequence=0,in_flight=True))
    session.add(action);session.flush()
    return _answer(action,dispatch=True)


def finish_publish_dispatch(*, session, analysis_id, attempt, dag_run_id, execution_id, sequence, now):
    """Not a timeout lease: only the owner of the exited SSH call may acknowledge."""
    _, _, action, _ = _locked(session,analysis_id,attempt,dag_run_id,execution_id,now)
    if action is None or type(sequence) is not int or not 0 <= sequence <= action.payload_json['sequence']:
        raise ValueError('unknown Step4 dispatch sequence')
    if sequence == action.payload_json['sequence']:
        action.payload_json = dict(action.payload_json,in_flight=False)
    return _answer(action)


def poll_publish_dispatch(*, session, analysis_id, attempt, dag_run_id, execution_id, now, observation=None):
    run, execution, action, identity = _locked(session,analysis_id,attempt,dag_run_id,execution_id,now)
    if action is None:
        raise ValueError('Step4 dispatch must be registered before reconciliation')
    if action.result_status in TERMINAL:
        return _answer(action)
    data = dict(action.payload_json)
    if run.status in STOPPED:
        action.result_status = 'stopped'
    elif now >= _date(data['deadline']):
        action.result_status = 'expired'
    if action.result_status in TERMINAL:
        return _answer(action)
    dispatch = False
    if observation is not None:
        if not isinstance(observation, dict) or not isinstance(observation.get('nonce'), str):
            raise ValueError('invalid Step4 observation')
        challenge = data.get('probe')
        if challenge and observation['nonce'] == challenge['nonce']:
            if (observation.get('schema_version') != 'cce.publish-observation.v1'
                    or any(type(observation.get(k)) is not type(v) or observation[k] != v for k,v in challenge.items())
                    or observation.get('status') not in {'not_started','running','success','complete','succeeded','failed','canceled','uncertain'}):
                raise ValueError('Step4 observation differs from the issued challenge')
            status = observation['status']
            data['last_nonce'] = challenge['nonce'];data.pop('probe')
            if status == 'not_started':
                if data['in_flight'] or data.get('started_observed') or execution.status != 'accepted':
                    action.result_status = 'uncertain'
                elif data['sequence'] >= len(DELAYS):
                    action.result_status = 'exhausted'
                else:
                    data.setdefault('next_retry_at', (now+timedelta(seconds=DELAYS[data['sequence']])).isoformat())
                    action.result_status = 'waiting'
                    if now >= _date(data['next_retry_at']) and _date(data['probe_issued_at']) >= _date(data['next_retry_at']):
                        data.update(sequence=data['sequence']+1,in_flight=True)
                        data.pop('next_retry_at')
                        action.result_status='uncertain';dispatch=True
            else:
                action.result_status = 'success' if status in {'complete','succeeded'} else status
                if status == 'running':
                    data['started_observed'] = True
                    data.pop('next_retry_at', None)
        elif observation['nonce'] != data.get('last_nonce'):
            raise ValueError('Step4 observation is stale or unissued')
    if 'probe' not in data and action.result_status not in TERMINAL:
        data['probe'] = dict(identity,nonce=uuid4().hex)
        data['probe_issued_at'] = now.isoformat()
    action.payload_json = data
    return _answer(action,dispatch=dispatch)
