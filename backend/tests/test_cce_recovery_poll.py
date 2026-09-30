"""Existing Airflow sensor boundary owns waiting; no independent daemon."""
from datetime import timedelta
from copy import deepcopy
import importlib
import json

import pytest
from sqlalchemy import select

from app.models import AnalysisRun, RunAction
from test_cce_recovery_dispatch import automatic, setup, recovery, evidence, NOW
from test_cce_recovery_evidence import digest


def poll(case, seconds, dag='original', action_id=None, *,
         native_stage_observation=None, worker_observation=None):
    fixture, _, aid, _ = case
    factory, settings, airflow, _, _ = fixture
    with factory() as session:
        return importlib.import_module('app.cce_recovery_poll').poll_compute_recovery(
            session=session,settings=settings,airflow_client=airflow,analysis_id=aid,
            attempt=1,pipeline='wgs' if aid.startswith('WGS_') else 'gatk',
            dag_run_id=dag,resume_action_id=action_id,now=NOW+timedelta(seconds=seconds),
            native_stage_observation=native_stage_observation,
            worker_observation=worker_observation)


def native_terminal(case, generation, state):
    """Synthetic native read of the real current registered frozen Step3."""
    fixture, model, aid, _ = case
    factory, _, _, path, _ = fixture
    frozen = json.loads(path.read_text(encoding='utf-8'))
    assert frozen['stage_execution'] == {'protocol': 'cce.stage-execution.v1'}
    with factory() as session:
        row = session.scalar(select(model).where(model.stage_code == 'step3_monitor',
            model.generation == generation))
        assert row is not None
        assert all(frozen[key] == getattr(row, key)
            for key in ('execution_id', 'generation', 'request_hash'))
        assert frozen['resume_action_id']
        return {
            'schema': 'cce.stage-execution.snapshot.v1',
            'execution_ref': {
                'protocol': 'cce.stage-execution.v1',
                'pipeline': 'wgs' if aid.startswith('WGS_') else 'gatk',
                'analysis_id': aid, 'attempt': 1, 'stage': 'step3_monitor',
                'execution_id': row.execution_id, 'stage_generation': row.generation,
                'request_hash': row.request_hash, 'registration_sha256': 'e' * 64,
            },
            'state': state, 'evidence_ref': row.receipt_hash,
            'runtime_identity': None, 'compute_identity': None,
            'observation_health': 'healthy',
        }


def test_airflow_polls_reserved_action_then_hands_off_without_advancing_old_dag(automatic):
    from app.cce_monitor_observation import retain_monitor_observation
    fixture, model, _, data = automatic
    factory, _, airflow, path, _ = fixture
    assert poll(automatic,10)['status']=='waiting'
    assert not airflow.posts
    assert poll(automatic,60)['status']=='delegated'
    assert poll(automatic,61)['status']=='delegated'
    assert len(airflow.posts)==1
    dag=airflow.posts[0][1]
    # The new DagRun alone may settle this action's exact registered monitor.
    with factory.begin() as session:
        row=session.scalar(select(model).where(model.stage_code=='step3_monitor').order_by(model.generation.desc()))
        row.status='success'; row.receipt_hash='a'*64
        scope = dict(pipeline='wgs' if data['pipeline']=='wgs' else 'gatk',
            analysis_id=row.analysis_id, attempt=1, stage='step3_monitor',
            execution_id=row.execution_id, generation=row.generation,
            request_hash=row.request_hash)
        retain_monitor_observation(row, dict(updated_at=NOW.isoformat(),
            monitoring_health='degraded', monitor_reconnect=dict(version=1,
                scope=scope, phase='blocked', retries_used=6,
                deadline=(NOW+timedelta(hours=1)).timestamp())), pipeline=data['pipeline'])
    assert poll(automatic,62,dag,data['action_id'])['status']=='needs_attention'
    observation = native_terminal(automatic,2,'succeeded')
    wrong_ref = deepcopy(observation)
    wrong_ref['execution_ref']['request_hash'] = 'f'*64
    assert poll(automatic,62,dag,data['action_id'],
        native_stage_observation=wrong_ref)['status']=='needs_attention'
    original_request = path.read_bytes()
    for corrupted in ('marker','digest'):
        frozen = json.loads(original_request)
        if corrupted == 'marker':
            frozen.pop('stage_execution')
        else:
            frozen['request_hash'] = 'f'*64
        path.write_text(json.dumps(frozen), encoding='utf-8')
        assert poll(automatic,62,dag,data['action_id'],
            native_stage_observation=observation)['status']=='needs_attention'
    path.write_bytes(original_request)
    assert poll(automatic,62,dag,data['action_id'],
        native_stage_observation=observation)['status']=='complete'
    with factory() as session:
        action=session.scalar(select(RunAction))
        assert action.payload_json['compute_terminal']=='success'
        assert action.payload_json['compute_terminal_binding']['receipt_hash']=='a'*64
        assert action.result_status=='queued'  # Still authorizes necessary downstream stages.
    assert poll(automatic,63)['status']=='delegated'


def test_wrong_dag_or_identity_never_reserves_or_dispatches(automatic):
    fixture, _, _, _ = automatic
    assert poll(automatic,60,dag='unrelated')['status']=='superseded'
    assert not fixture[2].posts
    with fixture[0]() as session:
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count']==1


@pytest.mark.parametrize('phase', ['waiting', 'blocked', 'exhausted'])
def test_monitor_query_failure_does_not_settle_compute_or_reserve_another_slot(automatic, phase):
    from app.cce_monitor_observation import retain_monitor_observation
    fixture, model, _, data = automatic
    factory, _, airflow, _, _ = fixture
    assert poll(automatic,60)['status']=='delegated'
    dag = airflow.posts[0][1]
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.status = 'running'
        row = session.scalar(select(model).where(model.stage_code=='step3_monitor',model.generation==2))
        row.status = 'failed'
        scope = dict(pipeline=run.pipeline_name,analysis_id=run.analysis_id,attempt=1,
            stage=row.stage_code,execution_id=row.execution_id,generation=row.generation,request_hash=row.request_hash)
        retain_monitor_observation(row, dict(updated_at=NOW.isoformat(),monitoring_health='degraded',
            monitor_reconnect=dict(version=1,scope=scope,phase=phase,retries_used=6,
                deadline=(NOW+timedelta(hours=1)).timestamp())), pipeline=run.pipeline_name)
    assert poll(automatic,62,dag,data['action_id'])['status']=='needs_attention'
    with factory() as session:
        action = session.scalar(select(RunAction))
        assert 'compute_terminal' not in action.payload_json
        assert action.result_status == 'queued'
        run = session.scalar(select(AnalysisRun))
        assert run.status == 'running'
        assert run.params_json['cce_recovery_budget']['count'] == 1
        assert len(session.scalars(select(RunAction)).all()) == 1
    assert len(airflow.posts) == 1


def test_second_terminal_master_consumes_only_remaining_slot_and_old_history_does_not_fence_cleanup(automatic):
    from app.cce_recovery_budget import require_current_dag_cleanup
    fixture,model,aid,first=automatic
    factory,_,airflow,_,_=fixture
    assert poll(automatic,60)['status']=='delegated'
    first_dag=airflow.posts[-1][1]
    with factory.begin() as session:
        previous=session.scalar(select(model).where(model.stage_code=='step3_monitor',model.generation==1))
        row=session.scalar(select(model).where(model.stage_code=='step3_monitor',model.generation==2))
        payload=deepcopy(previous.terminal_payload_json)
        binding=payload['cce_master_binding']
        binding['platform_execution'].update(stage='step3_monitor',execution_id=row.execution_id,
            generation=row.generation,request_hash=row.request_hash)
        binding['native'].update(execution_generation=4,job_uid='master-two',pod_uid='master-pod-two')
        proof=payload['cce_recovery_evidence'];proof['binding']=binding
        for value in (proof['candidate'],proof['terminal']):
            value.update(generation=4,master_job_uid='master-two',master_pod_uid='master-pod-two')
        proof['terminal']['plugin_failure_sha256']=digest(proof['candidate'])
        payload['cce_master_submit_execution_id']=row.execution_id
        row.status='failed';row.receipt_hash='b'*64;row.terminal_payload_json=payload
        session.scalar(select(AnalysisRun)).current_stage='step3_monitor'
    observation = native_terminal(automatic, 2, 'failed')
    assert poll(automatic,70,first_dag,first['action_id'])['status']=='needs_attention'
    second=poll(automatic,70,first_dag,first['action_id'],
        native_stage_observation=observation)
    assert second['status']=='waiting'
    with factory() as session:
        first_action=session.scalar(select(RunAction).where(RunAction.action=='cce_compute_recovery')
            .order_by(RunAction.id))
        assert first_action.payload_json['compute_terminal_binding']['receipt_hash']=='b'*64
    assert poll(automatic,249,first_dag,first['action_id'])['status']=='waiting'
    assert len(airflow.posts)==1
    assert poll(automatic,250,first_dag,first['action_id'])['status']=='delegated'
    assert len(airflow.posts)==2
    with factory.begin() as session:
        run=session.scalar(select(AnalysisRun))
        assert run.params_json['cce_recovery_budget']['count']==2
        require_current_dag_cleanup(session=session,analysis_id=aid,attempt=1,
            pipeline=run.pipeline_name,dag_run_id=airflow.posts[-1][1],resume_action_id=second['action_id'])
        with pytest.raises(ValueError):
            require_current_dag_cleanup(session=session,analysis_id=aid,attempt=1,
                pipeline=run.pipeline_name,dag_run_id=first_dag,resume_action_id=first['action_id'])


def test_manual_terminal_allows_one_budgeted_recovery(automatic):
    from test_cce_manual_monitor_reconnect import interrupted, resume
    fixture, model, aid, first = automatic
    factory, _, airflow, _, _ = fixture
    assert poll(automatic, 10)['status'] == 'waiting'
    assert poll(automatic, 60)['status'] == 'delegated'
    interrupted(automatic)
    manual = resume(automatic, 'manual-after-observer-loss')
    assert manual['status'] == 'queued'
    manual_dag = airflow.posts[-1][1]
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        prior = session.scalar(select(model).where(model.stage_code == 'step3_monitor',
            model.generation == 1))
        row = session.scalar(select(model).where(model.stage_code == 'step3_monitor',
            model.generation == manual['generation']))
        payload = deepcopy(prior.terminal_payload_json)
        binding = payload['cce_master_binding']
        binding['platform_execution'].update(stage='step3_monitor',execution_id=row.execution_id,
            generation=row.generation,request_hash=row.request_hash)
        binding['native'].update(execution_generation=5,job_uid='manual-master',pod_uid='manual-pod')
        proof = payload['cce_recovery_evidence']
        proof['binding'] = binding
        for value in (proof['candidate'],proof['terminal']):
            value.update(generation=5,master_job_uid='manual-master',master_pod_uid='manual-pod')
        proof['terminal']['plugin_failure_sha256'] = digest(proof['candidate'])
        payload['cce_master_submit_execution_id'] = row.execution_id
        row.status = 'failed'
        row.receipt_hash = 'c' * 64
        row.terminal_payload_json = payload
        run.current_stage = 'step3_monitor'
    observation = native_terminal(automatic, manual['generation'], 'failed')
    with factory.begin() as session:
        row = session.scalar(select(model).where(model.stage_code == 'step3_monitor',
            model.generation == manual['generation']))
        valid_payload = deepcopy(row.terminal_payload_json)
        row.terminal_payload_json = dict(valid_payload, cce_recovery_evidence=None)
    assert poll(automatic, 70, manual_dag, manual['action_id'],
        native_stage_observation=observation)['status'] == 'needs_attention'
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count'] == 1
        assert len(session.scalars(select(RunAction)).all()) == 2
    with factory.begin() as session:
        row = session.scalar(select(model).where(model.stage_code == 'step3_monitor',
            model.generation == manual['generation']))
        row.terminal_payload_json = valid_payload
    assert poll(automatic, 70, manual_dag, manual['action_id'])['status'] == 'needs_attention'
    # A Worker probe payload is not a native Step3 terminal snapshot.
    assert poll(automatic, 70, manual_dag, manual['action_id'],
        worker_observation=observation)['status'] == 'needs_attention'
    for changed in ('generation', 'evidence', 'unknown'):
        bad = deepcopy(observation)
        if changed == 'generation':
            bad['execution_ref']['stage_generation'] += 1
        elif changed == 'evidence':
            bad['evidence_ref'] = 'f' * 64
        else:
            bad['state'] = 'unknown'
        assert poll(automatic, 70, manual_dag, manual['action_id'],
            native_stage_observation=bad)['status'] == 'needs_attention'
    second = poll(automatic, 70, manual_dag, manual['action_id'],
        native_stage_observation=observation)
    assert second['status'] == 'waiting'
    from app.cce_recovery_budget import compute_finished
    with factory() as session:
        manual_action = session.scalar(select(RunAction).where(
            RunAction.action == 'resume_stage'))
        original_action_data = deepcopy(manual_action.payload_json)
    for key in ('action_id', 'dag_run_id'):
        altered = deepcopy(original_action_data)
        altered[key] = 'foreign-identity'
        if key == 'action_id':
            altered['conf']['resume_action_id'] = 'foreign-identity'
        with factory.begin() as session:
            session.scalar(select(RunAction).where(
                RunAction.action == 'resume_stage')).payload_json = altered
        with factory() as session:
            manual_action = session.scalar(select(RunAction).where(
                RunAction.action == 'resume_stage'))
            assert not compute_finished(manual_action, session=session,
                run=session.scalar(select(AnalysisRun)))
    with factory.begin() as session:
        session.scalar(select(RunAction).where(
            RunAction.action == 'resume_stage')).payload_json = original_action_data
    assert poll(automatic, 249, manual_dag, manual['action_id'])['status'] == 'waiting'
    delegated = poll(automatic, 250, manual_dag, manual['action_id'])
    assert delegated['status'] == 'delegated'
    assert poll(automatic, 251, manual_dag, manual['action_id'])['status'] == 'delegated'
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        actions = session.scalars(select(RunAction).order_by(RunAction.id)).all()
        assert run.params_json['cce_recovery_budget']['count'] == 2
        assert actions[1].result_status == 'queued'  # The manual action still authorizes later stages.
        assert actions[1].payload_json['compute_terminal']=='failed'
        assert actions[1].payload_json['compute_terminal_binding']['receipt_hash']=='c'*64
        assert actions[2].payload_json['ordinal'] == 2
        assert actions[2].payload_json['original_deadline'] == first['original_deadline']
        from app.cce_resume_dispatch import authorize_recovery_stage
        authorize_recovery_stage(session=session, run=run, action_id=second['action_id'],
            dag_run_id=run.dag_run_id, stage='step4_publish')
    assert len(airflow.posts) == 3
    with factory.begin() as session:
        row = session.scalar(select(model).where(model.stage_code == 'step3_monitor',
            model.generation == delegated['generation']))
        row.status = 'failed'  # An observer failure without a native terminal proof.
    second_dag = airflow.posts[-1][1]
    assert poll(automatic, 252, second_dag, second['action_id'])['status'] == 'needs_attention'
    with factory() as session:
        actions = session.scalars(select(RunAction).order_by(RunAction.id)).all()
        assert 'compute_terminal' not in actions[2].payload_json
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count'] == 2
    assert len(airflow.posts) == 3
    with factory.begin() as session:
        row = session.scalar(select(model).where(model.stage_code == 'step3_monitor',
            model.generation == delegated['generation']))
        row.status = 'success'
        row.receipt_hash = 'd' * 64
    exact = native_terminal(automatic, delegated['generation'], 'succeeded')
    assert poll(automatic, 253, second_dag, second['action_id'],
        native_stage_observation=exact)['status'] == 'complete'
    with factory.begin() as session:
        current = session.scalar(select(model).where(model.stage_code == 'step3_monitor',
            model.generation == delegated['generation']))
        fields = dict(analysis_id=aid, attempt=1, stage_code='step3_monitor',
            generation=delegated['generation'] + 1, execution_id='synthetic-newer-step3',
            status='success', request_hash='f' * 64, receipt_hash='e' * 64,
            release_id=current.release_id)
        if model.__name__ == 'PipelineStageExecution':
            fields['pipeline_name'] = 'gatk'
        session.add(model(**fields))
    assert poll(automatic, 254, second_dag, second['action_id'],
        native_stage_observation=exact)['status'] == 'needs_attention'


def test_existing_internal_stage_route_reconciles_the_same_action(automatic,monkeypatch):
    from app import main
    fixture, _, aid, _=automatic
    factory,settings,airflow,_,_=fixture
    monkeypatch.setattr(main,'get_sessionmaker',lambda:factory)
    monkeypatch.setattr(main,'get_settings',lambda:settings)
    monkeypatch.setattr(main,'get_airflow_client',lambda:airflow)
    monkeypatch.setattr(main,'_wgs_runtime_adapter_enabled',lambda:True)
    # Keep the route's real clock but make the already-reserved action due.
    with factory.begin() as session:
        action=session.scalar(select(RunAction))
        action.payload_json=dict(action.payload_json,next_retry_at='2000-01-01T00:00:00+00:00')
        run=session.scalar(select(AnalysisRun));params=dict(run.params_json)
        for key in ('cce_recovery_policy','cce_recovery_budget'):
            params[key]=dict(params[key],original_deadline='2099-01-01T00:00:00+00:00')
        action.payload_json=dict(action.payload_json,original_deadline='2099-01-01T00:00:00+00:00')
        run.params_json=params
    pipeline='wgs' if aid.startswith('WGS_') else 'gatk'
    kind=main.WgsRuntimeStageRequest if pipeline=='wgs' else main.GatkRuntimeStageRequest
    endpoint=main.internal_wgs_runtime_stage if pipeline=='wgs' else main.internal_gatk_runtime_stage
    request=kind(attempt=1,adapter=pipeline+'-runtime-200',dag_run_id='original')
    assert endpoint(aid,'compute_recovery',request)['status']=='delegated'
    assert endpoint(aid,'compute_recovery',request)['status']=='delegated'
    assert len(airflow.posts)==1
    if pipeline=='gatk':
        monkeypatch.setattr(main,'release_obs_transfer_slot',lambda **kw:dict(released=True))
        current=kind(attempt=1,adapter='gatk-runtime-200',dag_run_id=airflow.posts[-1][1],
            resume_action_id=airflow.posts[-1][2]['resume_action_id'])
        assert endpoint(aid,'release_leases',current)['released'] is True
        with pytest.raises(main.HTTPException):endpoint(aid,'release_leases',request)
