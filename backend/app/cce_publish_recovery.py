"""Step4 same-operation dispatch budget; internal, default-off, no I/O caller yet.

The caller commits the returned dispatch intent BEFORE SSH, and acknowledges its
sequence only when that exact local SSH invocation has exited. A crashed caller
leaves in_flight set: negative remote evidence alone cannot grant another send.
Airflow owns rescheduling. No new execution, compute budget or background timer.
"""
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from app.models import AnalysisRun, RunAction, WgsStageExecution, PipelineStageExecution
from app.cce_recovery_budget import STOPPED, _date

ACTION = 'cce_publish_dispatch'
DELAYS = (60, 180)
TERMINAL = {'success', 'failed', 'canceled', 'stopped', 'expired', 'exhausted'}


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
