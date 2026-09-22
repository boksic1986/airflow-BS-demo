"""Same-attempt WGS recovery, using frozen requests and durable RunAction identity."""
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets

import httpx
from sqlalchemy import select

from app.models import AnalysisRun, RunAction, RunStageState, WgsStageExecution, WgsExecutionDispatch
from app.cce_recovery_budget import ACTION as COMPUTE_RECOVERY_ACTION, FINISHED_ACTIONS
from app.wgs_runtime_adapter import write_stage_request
from app.wgs_stage_catalog import load_wgs_stage_contract
from app.wgs_stage_execution_service import register_stage_execution

STAGES = ('step1_upload', 'step2_master', 'step3_monitor', 'step4_publish', 'step5_download', 'step6_materialize')
EXECUTION_KEYS = ('execution_id', 'generation', 'request_hash', 'predecessor_execution_id', 'predecessor_generation', 'predecessor_receipt_hash')


def _latest(session, run, stage):
    return session.scalar(select(WgsStageExecution).where(WgsStageExecution.analysis_id == run.analysis_id,
        WgsStageExecution.attempt == run.attempt, WgsStageExecution.stage_code == stage)
        .order_by(WgsStageExecution.generation.desc()).limit(1))


def recovery_action(session, run, action_id):
    action = session.scalar(select(RunAction).where(RunAction.analysis_id == run.analysis_id,
        RunAction.action == 'resume_stage').order_by(RunAction.id.desc()).limit(1))
    if not action or action.payload_json.get('action_id') != action_id or action.payload_json.get('attempt') != run.attempt:
        raise ValueError('recovery action does not match the current attempt')
    if (run.params_json or {}).get('resume_action_id') != action_id:
        raise ValueError('recovery action has been superseded')
    return action


def register_recovery_stage(*, session, settings, run, stage, action):
    data = action.payload_json
    if stage not in data['resume_stages']:
        raise ValueError('stage is outside the recovery action')
    root = Path(settings.wgs_runtime_request_root) / run.analysis_id / f'attempt-{run.attempt}'
    path = root / f'{stage}.json'
    latest = _latest(session, run, stage)
    saved = json.loads(path.read_text()) if path.is_file() else None
    if latest and saved and saved.get('resume_action_id') == data['action_id']:
        if saved.get('execution_id') != latest.execution_id or saved.get('request_hash') != latest.request_hash:
            raise ValueError('frozen request does not match active execution')
        return saved
    payload = dict(saved or data['frozen_request'])
    if latest and saved:
        if any(saved.get(key) != getattr(latest, key) for key in ('execution_id', 'generation', 'request_hash')):
            raise ValueError('frozen request execution identity differs')
        payload['resume_previous_execution'] = {key: saved[key] for key in ('execution_id', 'generation', 'request_hash')}
        if latest.status in {'accepted', 'running'}:
            latest.status = 'canceled'
            latest.message = 'Superseded by explicit same-attempt recovery; executor may be reattached'
            latest.ended_at = datetime.now(timezone.utc)
    for key in EXECUTION_KEYS:
        payload.pop(key, None)
    payload.update(stage=stage, resume_action_id=data['action_id'])
    for key in ('analysis_id', 'attempt', 'pipeline_release_id', 'control_workdir', 'expected_batch_root', 'wgs_source_commit'):
        if payload.get(key) != data['frozen_request'].get(key):
            raise ValueError('recovery request differs from frozen identity')
    row = register_stage_execution(session=session, run=run,
        contract=load_wgs_stage_contract(Path(settings.wgs_stage_contract_path)), stage_code=stage,
        request_payload=payload, force_new_generation=True)
    payload.update(orchestration_contract_version=2, **{key: getattr(row, key) for key in EXECUTION_KEYS})
    if saved:
        history = root / 'request-history' / stage
        history.mkdir(parents=True, exist_ok=True)
        prior = history / f"generation-{saved.get('generation', 1)}.json"
        if not prior.exists():
            prior.write_text(json.dumps(saved, sort_keys=True) + '\n')
    write_stage_request(settings.wgs_runtime_request_root, payload, shared_gid=getattr(settings, 'wgs_runtime_shared_gid', None))
    state = session.scalar(select(RunStageState).where(RunStageState.analysis_id == run.analysis_id,
        RunStageState.attempt == run.attempt, RunStageState.stage_code == stage))
    if state:
        state.stage_status = 'accepted'
        state.started_at = state.ended_at = None
        state.updated_at = datetime.now(timezone.utc)
    session.flush()
    return payload


def request_resume_stage(*, session, settings, airflow_client, analysis_id, attempt, stage, idempotency_key, requested_by):
    if stage not in STAGES or not idempotency_key or len(idempotency_key) > 128:
        raise ValueError('a canonical Step1–6 stage and idempotency key are required')
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id).with_for_update())
    if not run or run.pipeline_name != 'wgs' or run.attempt != attempt:
        raise ValueError('unknown current WGS attempt')
    # Serialize with automatic reservations on the same AnalysisRun row. Do not
    # replace frozen requests or contact Airflow while their outcome is pending.
    automatic_actions = session.scalars(select(RunAction).where(
        RunAction.analysis_id == analysis_id, RunAction.action == COMPUTE_RECOVERY_ACTION)).all()
    for automatic in automatic_actions:
        if automatic.result_status in FINISHED_ACTIONS:
            continue
        data = automatic.payload_json
        if (not isinstance(data, dict) or type(data.get('attempt')) is not int
                or data['attempt'] == attempt):
            raise ValueError('pending automatic recovery must be reconciled before manual resume')
    params = dict(run.params_json or {})
    if int(params.get('orchestration_contract_version', 1)) != 2 or not settings.wgs_contract_v2_enabled:
        raise ValueError('recovery requires the frozen v2 stage contract')
    dispatch = session.scalar(select(WgsExecutionDispatch).where(WgsExecutionDispatch.analysis_id == analysis_id))
    if run.execution_mode != 'cce' or (dispatch and dispatch.desired_target != 'cce'):
        raise ValueError('resume_stage is only available for WGS CCE')
    actions = session.scalars(select(RunAction).where(RunAction.analysis_id == analysis_id,
        RunAction.action == 'resume_stage').order_by(RunAction.id.desc())).all()
    action = None
    for previous in actions:
        data = previous.payload_json
        if data.get('attempt') != attempt:
            continue
        if data.get('idempotency_key') == idempotency_key:
            if data['stage'] != stage:
                raise ValueError('idempotency key belongs to another stage')
            action = previous
            break
        if previous.result_status in {'reserved', 'uncertain'} or (previous.result_status == 'queued' and run.status not in {'failed', 'success', 'canceled', 'cancelled', 'terminated'}):
            if data['stage'] != stage:
                raise ValueError('another recovery stage is active')
            action = previous
            break
    if action is None:
        interrupted = _latest(session, run, stage)
        if interrupted is None or interrupted.status == 'success':
            raise ValueError('stage has no interrupted execution')
        path = Path(settings.wgs_runtime_request_root) / analysis_id / f'attempt-{attempt}' / f'{stage}.json'
        frozen = json.loads(path.read_text())
        if frozen.get('analysis_id') != analysis_id or frozen.get('attempt') != attempt or frozen.get('pipeline_release_id') != params.get('pipeline_release_id') or frozen.get('wgs_source_commit') != params.get('wgs_source_commit'):
            raise ValueError('frozen request does not match the analysis')
        action_id = 'resume_' + secrets.token_hex(12)
        stages = [code for code in STAGES[STAGES.index(stage):] if not (_latest(session, run, code) and _latest(session, run, code).status == 'success')]
        data = dict(action_id=action_id, attempt=attempt, stage=stage, idempotency_key=idempotency_key,
            original_dag_run_id=run.dag_run_id, dag_run_id=f'{analysis_id}-a{attempt}-{action_id}',
            resume_stages=stages, frozen_request=frozen)
        action = RunAction(analysis_id=analysis_id, action='resume_stage', requested_by=requested_by,
            payload_json=data, result_status='reserved')
        session.add(action)
        params['resume_action_id'] = action_id
        run.params_json = params
        payload = register_recovery_stage(session=session, settings=settings, run=run, stage=stage, action=action)
        data = dict(data)
        data['generation'] = payload['generation']
        data['conf'] = dict(analysis_id=analysis_id, attempt=attempt, pipeline='wgs', execution_mode='cce',
            workdir=run.workdir, params=params, resume_stage=stage, resume_action_id=action_id, resume_stages=stages)
        action.payload_json = dict(data)
        run.dag_run_id = data['dag_run_id']
        run.current_stage = stage
        session.commit()  # Persist identity before an external side effect.
    data = action.payload_json
    if action.result_status == 'rejected':
        raise ValueError(action.message or 'recovery dispatch was rejected')
    if action.result_status != 'queued':
        try:
            try:
                found = airflow_client.get_dag_run(run.dag_id, data['dag_run_id'])
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 404:
                    raise
                try:
                    found = airflow_client.trigger_dag_run(run.dag_id, dag_run_id=data['dag_run_id'], conf=data['conf'])
                except httpx.HTTPStatusError as error:
                    if error.response.status_code not in {408, 409, 429} and error.response.status_code < 500:
                        raise
                    found = airflow_client.get_dag_run(run.dag_id, data['dag_run_id'])
                except httpx.TransportError:
                    found = airflow_client.get_dag_run(run.dag_id, data['dag_run_id'])
            if found.get('conf') != data['conf']:
                raise ValueError('existing recovery DagRun identity differs')
            action.result_status = 'queued'
            run.status = 'queued'
            run.ended_at = run.pipeline_finished_at = None
            run.error_summary = None
        except httpx.HTTPStatusError as error:
            code = error.response.status_code
            if code not in {404, 408, 429} and not 500 <= code < 600:
                action.result_status = 'rejected'
                action.message = f'Airflow rejected recovery dispatch (HTTP {code}); correct authorization or parameters before a new action'
                session.commit()
                raise ValueError(action.message) from error
            action.result_status = 'uncertain'
            run.error_summary = 'Recovery dispatch is unconfirmed; retry resume_stage to reconcile the same action'
        except httpx.TransportError:
            action.result_status = 'uncertain'
            run.error_summary = 'Recovery dispatch is unconfirmed; retry resume_stage to reconcile the same action'
        session.commit()
    return dict(analysis_id=analysis_id, attempt=attempt, stage=stage, generation=data['generation'],
        action_id=data['action_id'], status=action.result_status)
