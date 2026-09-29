"""GATK same-attempt recovery through its own frozen stage contract."""
import json
from types import SimpleNamespace
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import gatk_runtime_service as runtime
from app.models import AnalysisRun, Base, PipelineStageExecution, RunAction, WgsStageExecution

AID = 'GATK_SYNTHETIC_RECOVERY'


@pytest.fixture
def recovery(tmp_path):
    engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = SimpleNamespace(gatk_execution_enabled=True,
        gatk_runtime_request_root=str(tmp_path / 'requests'),
        gatk_runtime_node200_root='/frozen/node200')
    request = dict(schema_version='gatk-runtime.request.v1', pipeline='gatk',
        analysis_id=AID, attempt=1, stage='step3_monitor', generation=1,
        execution_id='old-monitor', orchestration_contract_version=2,
        runtime_workdir='/frozen/node200/runs/' + AID + '/attempt-1',
        cce_bundle='/frozen/node200/runs/' + AID + '/attempt-1/cce',
        profile_id='synthetic', profile_revision='r1',
        predecessor_execution_id='old-submit', predecessor_receipt_hash='b'*64)
    request['request_hash'] = runtime._canonical_hash(request)
    path = runtime._request_path(settings, AID, 1, 'step3_monitor')
    runtime._atomic_json(path, request)
    with factory.begin() as session:
        session.add(AnalysisRun(analysis_id=AID, pipeline_name='gatk', dag_id='bio_gatk',
            dag_run_id='original', execution_mode='cce', workdir='/frozen/source',
            status='failed', current_stage='step3_monitor', attempt=1,
            params_json={'runtime_profile_id':'synthetic', 'runtime_profile_revision':'r1'}))
        for stage, identity, status in [('step2_master','old-submit','success'),
                                        ('step3_monitor','old-monitor','failed')]:
            session.add(PipelineStageExecution(pipeline_name='gatk', analysis_id=AID,
                attempt=1, stage_code=stage, execution_id=identity, generation=1,
                status=status, request_hash=request['request_hash'], receipt_hash='b'*64,
                release_id='synthetic@r1'))
    class Airflow:
        def __init__(self): self.posts = []; self.runs = {}; self.lost = False
        def get_dag_run(self, dag, identity):
            if identity not in self.runs:
                raise httpx.HTTPStatusError('missing', request=httpx.Request('GET','http://synthetic'),
                    response=httpx.Response(404))
            return self.runs[identity]
        def trigger_dag_run(self, dag, *, dag_run_id, conf):
            self.posts.append((dag, dag_run_id, conf))
            self.runs[dag_run_id] = dict(dag_run_id=dag_run_id, conf=conf, state='queued')
            if self.lost: raise httpx.ReadTimeout('lost reply')
            return self.runs[dag_run_id]
    yield factory, settings, Airflow(), path, request
    engine.dispose()


def resume(fixture, **overrides):
    factory, settings, airflow, _, _ = fixture
    with factory() as session:
        return runtime.request_gatk_resume_stage(session=session, settings=settings,
            airflow_client=airflow, analysis_id=AID, attempt=1,
            stage=overrides.get('stage','step3_monitor'), idempotency_key='same-click',
            requested_by='operator')


@pytest.mark.parametrize('stage', runtime.STAGES[1:])
def test_gatk_stage_status_projects_frozen_native_marker_for_every_step(recovery, monkeypatch, stage):
    factory, settings, _, _, original = recovery
    request = {**original, 'stage': stage,
        'execution_id': f'synthetic-{stage}',
        'stage_execution': {'protocol': 'cce.stage-execution.v1'}}
    request.pop('request_hash')
    request['request_hash'] = runtime._canonical_hash(request)
    runtime._atomic_json(runtime._request_path(settings, AID, 1, stage), request)
    monkeypatch.setattr(runtime, '_ingest_gatk_evidence', lambda **_kw: None)
    with factory.begin() as session:
        row = session.scalar(select(PipelineStageExecution).where(
            PipelineStageExecution.stage_code == stage))
        if row is None:
            row = PipelineStageExecution(pipeline_name='gatk', analysis_id=AID,
                attempt=1, stage_code=stage, execution_id=request['execution_id'],
                generation=1, status='accepted', request_hash=request['request_hash'],
                release_id='synthetic@r1')
            session.add(row)
        else:
            row.execution_id = request['execution_id']
            row.request_hash = request['request_hash']
    with factory() as session:
        status = runtime.sync_gatk_stage_status(session=session, settings=settings,
            analysis_id=AID, attempt=1, stage=stage)
    assert status['stage_execution'] == request['stage_execution']
    assert status['execution_id'] == request['execution_id']
    assert status['request_hash'] == request['request_hash']


def test_gatk_recovery_preserves_frozen_bundle_and_replays_one_dispatch(recovery):
    factory, settings, airflow, path, original = recovery
    airflow.lost = True
    first = resume(recovery)
    assert resume(recovery) == first
    assert first['generation'] == 2 and first['attempt'] == 1
    assert len(airflow.posts) == 1 and airflow.posts[0][0] == 'bio_gatk'
    conf = airflow.posts[0][2]
    assert conf['pipeline'] == 'gatk'
    assert conf['resume_stages'] == ['step3_monitor','step4_publish','step5_download','step6_materialize']
    saved = json.loads(path.read_text())
    for key in ('runtime_workdir','cce_bundle','profile_id','profile_revision'):
        assert saved[key] == original[key]
    assert json.loads((path.parent/'request-history/step3_monitor/generation-1.json').read_text()) == original
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).dag_run_id == airflow.posts[0][1]
        assert session.scalar(select(AnalysisRun)).status == 'queued'
        assert session.scalar(select(WgsStageExecution)) is None
        assert len(session.scalars(select(PipelineStageExecution)).all()) == 3
        action = session.scalar(select(RunAction))
        replay = runtime.register_gatk_stage(session=session, settings=settings,
            analysis_id=AID, attempt=1, stage='step3_monitor', recovery_action=action)
        assert replay['generation'] == 2


@pytest.mark.parametrize('corruption', ['bundle', 'hash', 'legacy', 'pending'])
def test_gatk_recovery_rejects_unbound_input_before_dispatch(recovery, corruption):
    factory, _, airflow, path, _ = recovery
    payload = json.loads(path.read_text())
    if corruption == 'bundle': payload['cce_bundle'] = '/another/project'
    if corruption == 'hash': payload['request_hash'] = 'f'*64
    if corruption == 'legacy': payload.pop('orchestration_contract_version')
    if corruption == 'pending':
        with factory.begin() as session:
            session.add(RunAction(analysis_id=AID, action='cce_compute_recovery', requested_by='auto',
                result_status='reserved', payload_json={'attempt':1}))
    else: path.write_text(json.dumps(payload))
    with pytest.raises(ValueError): resume(recovery)
    assert airflow.posts == []
    with factory() as session:
        assert len(session.scalars(select(PipelineStageExecution)).all()) == 2


def test_existing_resume_endpoint_routes_gatk_and_fences_stage_scope(recovery, monkeypatch):
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from app import main
    from app.auth_service import AuthenticatedUser
    from app.pipeline_registry_service import get_pipeline_registry
    from app.pipeline_registry import PipelineRegistry
    factory, settings, airflow, _, _ = recovery
    settings.auth_required = True
    settings.internal_service_token = ''
    settings.pipeline_registry_path = str(Path(__file__).parents[2]/'config/pipelines.yaml')
    definition = get_pipeline_registry(settings).get('gatk')
    registry = PipelineRegistry({'gatk':replace(definition, capabilities=definition.capabilities | {'resume'})})
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    monkeypatch.setattr(main, 'get_sessionmaker', lambda: factory)
    monkeypatch.setattr(main, 'get_airflow_client', lambda: airflow)
    monkeypatch.setattr(main, 'get_pipeline_registry', lambda _: registry)
    monkeypatch.setattr(main, 'authenticate_session', lambda **kw:
        AuthenticatedUser(1,'synthetic-operator','operator','csrf') if kw['raw_token'] else None)
    client = TestClient(main.app)
    try:
        client.cookies.set(main.SESSION_COOKIE, 'session')
        client.headers['X-CSRF-Token'] = 'csrf'
        body = {'attempt':1,'stage':'step3_monitor','idempotency_key':'http-click'}
        response = client.post(f'/api/runs/{AID}/actions/resume-stage', json=body)
        assert response.status_code == 200, response.text
        assert client.post(f'/api/runs/{AID}/actions/resume-stage', json=body).json() == response.json()
    finally:
        client.close()
    assert len(airflow.posts) == 1 and airflow.posts[0][0] == 'bio_gatk'
    action_id = response.json()['action_id']
    def register(stage, **changes):
        data = dict(attempt=1,adapter='gatk-runtime-200',dag_run_id=airflow.posts[0][1],
            resume_action_id=action_id)
        data.update(changes)
        return main.internal_gatk_runtime_stage(AID, stage, main.GatkRuntimeStageRequest(**data))
    assert register('step3_monitor')['generation'] == 2
    for stage, changes in [('prepare',{}), ('step3_monitor',{'dag_run_id':'original'}),
                           ('step3_monitor',{'resume_action_id':None})]:
        with pytest.raises(HTTPException): register(stage, **changes)
    with factory.begin() as session:
        session.scalar(select(AnalysisRun)).status = 'pause_requested'
    with pytest.raises(HTTPException): register('step3_monitor')


def test_gatk_finalize_rechecks_control_after_evidence_ingestion(recovery, monkeypatch):
    from fastapi import HTTPException
    from app import main
    result = resume(recovery)
    factory, settings, airflow, _, _ = recovery
    with factory.begin() as session:
        session.add(PipelineStageExecution(pipeline_name='gatk', analysis_id=AID, attempt=1,
            stage_code='step6_materialize', execution_id='reused-step6', generation=1,
            status='success', request_hash='c'*64, receipt_hash='d'*64, release_id='synthetic@r1'))
    def changed_control(**kw):
        with factory.begin() as other:
            other.scalar(select(AnalysisRun)).status = 'pause_requested'
    monkeypatch.setattr(runtime, '_ingest_gatk_evidence', changed_control)
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    monkeypatch.setattr(main, 'get_sessionmaker', lambda: factory)
    with pytest.raises(HTTPException):
        main.internal_gatk_runtime_stage(AID, 'finalize_run', main.GatkRuntimeStageRequest(
            attempt=1, adapter='gatk-runtime-200', dag_run_id=airflow.posts[0][1],
            resume_action_id=result['action_id']))
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'pause_requested'


def _marked_step6_success(recovery):
    factory, settings, _, _, _ = recovery
    body = {
        'schema_version': 'gatk-runtime.request.v1', 'pipeline': 'gatk',
        'analysis_id': AID, 'attempt': 1, 'stage': 'step6_materialize',
        'execution_id': 'GATK_SYNTHETIC_RECOVERY-a1-step6_materialize-g1',
        'generation': 1, 'orchestration_contract_version': 2,
        'stage_execution': {'protocol': 'cce.stage-execution.v1'},
    }
    request_hash = runtime._canonical_hash(body)
    request = {**body, 'request_hash': request_hash}
    path = runtime._request_path(settings, AID, 1, 'step6_materialize')
    runtime._atomic_json(path, request)
    receipt_body = {
        'schema_version': 'gatk-runtime.status.v1', 'analysis_id': AID,
        'attempt': 1, 'stage': 'step6_materialize', 'generation': 1,
        'execution_id': body['execution_id'], 'request_hash': request_hash,
        'orchestration_contract_version': 2, 'status': 'success',
        'message': 'synthetic final materialization',
    }
    receipt_hash = runtime._canonical_hash(receipt_body)
    runtime._atomic_json(path.with_suffix('.status.json'), {
        **receipt_body, 'receipt_hash': receipt_hash,
    })
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.status = 'running'
        run.dag_run_id = 'current-dag'
        session.add(PipelineStageExecution(
            pipeline_name='gatk', analysis_id=AID, attempt=1,
            stage_code='step6_materialize', execution_id=body['execution_id'],
            generation=1, status='success', request_hash=request_hash,
            receipt_hash=receipt_hash, release_id='synthetic@r1',
            terminal_payload_json={**receipt_body, 'receipt_hash': receipt_hash},
        ))
    observation = {
        'schema': 'cce.stage-execution.snapshot.v1',
        'execution_ref': {
            'protocol': 'cce.stage-execution.v1', 'pipeline': 'gatk',
            'analysis_id': AID, 'attempt': 1, 'stage': 'step6_materialize',
            'execution_id': body['execution_id'], 'stage_generation': 1,
            'request_hash': request_hash, 'registration_sha256': 'a' * 64,
        },
        'state': 'succeeded', 'evidence_ref': receipt_hash,
        'runtime_identity': None, 'compute_identity': None,
        'observation_health': 'healthy',
    }
    return factory, settings, path, observation


@pytest.mark.parametrize('health', ['healthy', 'degraded'])
def test_gatk_marked_finalization_requires_native_current_success(recovery, health):
    factory, settings, _, observation = _marked_step6_success(recovery)
    observation['observation_health'] = health
    with factory() as session:
        status = runtime.sync_gatk_stage_status(
            session=session, settings=settings, analysis_id=AID,
            attempt=1, stage='step6_materialize',
        )
    assert status['stage_execution'] == {'protocol': 'cce.stage-execution.v1'}
    assert status['ready'] is True
    with factory() as session:
        result = runtime.finalize_gatk_run(
            session=session, settings=settings, analysis_id=AID, attempt=1,
            dag_run_id='current-dag', worker_observation=observation,
        )
    assert result['status'] == 'success'
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'success'


def test_gatk_internal_finalization_forwards_native_terminal(recovery, monkeypatch):
    from app import main
    factory, settings, _, observation = _marked_step6_success(recovery)
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    monkeypatch.setattr(main, 'get_sessionmaker', lambda: factory)
    result = main.internal_gatk_runtime_stage(
        AID, 'finalize_run', main.GatkRuntimeStageRequest(
            attempt=1, adapter='gatk-runtime-200', dag_run_id='current-dag',
            worker_observation=observation,
        ),
    )
    assert result['status'] == 'success'
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'success'


def test_gatk_current_recovery_finalizes_reused_successful_step6(recovery):
    factory, settings, _, observation = _marked_step6_success(recovery)
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.status = 'failed'  # Airflow/control failure after Step6 business receipt.
        run.params_json = dict(run.params_json or {}, resume_action_id='resume_synthetic')
        session.add(RunAction(
            analysis_id=AID, action='resume_stage', requested_by='operator',
            result_status='queued', payload_json={
                'action_id': 'resume_synthetic', 'attempt': 1,
                'dag_run_id': 'current-dag', 'dispatch_state': 'confirmed',
                'resume_stages': [],
            },
        ))
    with factory() as session:
        result = runtime.finalize_gatk_run(
            session=session, settings=settings, analysis_id=AID, attempt=1,
            dag_run_id='current-dag', resume_action_id='resume_synthetic',
            worker_observation=observation,
        )
    assert result['status'] == 'success'


@pytest.mark.parametrize('invalid', [
    'missing', 'running', 'unknown', 'old_generation', 'wrong_receipt',
    'invalid_schema', 'invalid_registration', 'invalid_health', 'wrong_dag',
    'changed_receipt',
])
def test_gatk_marked_finalization_rejects_unproven_terminal(recovery, invalid):
    factory, settings, path, observation = _marked_step6_success(recovery)
    observation = {**observation, 'execution_ref': dict(observation['execution_ref'])}
    dag_run_id = 'current-dag'
    if invalid == 'missing':
        observation = None
    elif invalid in {'running', 'unknown'}:
        observation['state'] = invalid
        if invalid == 'unknown':
            observation['observation_health'] = 'degraded'
    elif invalid == 'old_generation':
        observation['execution_ref']['stage_generation'] = 2
    elif invalid == 'wrong_receipt':
        observation['evidence_ref'] = 'b' * 64
    elif invalid == 'invalid_schema':
        observation['schema'] = 'cce.stage-execution.snapshot.v0'
    elif invalid == 'invalid_registration':
        observation['execution_ref']['registration_sha256'] = 'bad'
    elif invalid == 'invalid_health':
        observation['observation_health'] = []
    elif invalid == 'wrong_dag':
        dag_run_id = 'old-dag'
    elif invalid == 'changed_receipt':
        receipt_path = path.with_suffix('.status.json')
        changed = json.loads(receipt_path.read_text())
        changed['message'] = 'changed after native receipt'
        runtime._atomic_json(receipt_path, changed)
    with factory() as session, pytest.raises(ValueError):
        runtime.finalize_gatk_run(
            session=session, settings=settings, analysis_id=AID, attempt=1,
            dag_run_id=dag_run_id, worker_observation=observation,
        )
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'running'


def test_gatk_airflow_reconciliation_accepts_current_authorized_recovery_dag(recovery):
    from app.gatk_airflow_sync import sync_gatk_airflow_status
    from app.diagnostics_service import MissingDagRunError
    resume(recovery)
    factory, settings, airflow, _, _ = recovery
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        current_dag = run.dag_run_id
        action = session.scalar(select(RunAction))
        assert action.result_status == 'queued'
        assert action.payload_json['dispatch_state'] == 'confirmed'
        expected_conf = action.payload_json['conf']
        class Client:
            def get_dag_run(self, dag_id, dag_run_id):
                assert dag_run_id == current_dag
                return {'dag_id': dag_id, 'dag_run_id': dag_run_id,
                    'state': 'running', 'conf': expected_conf}
        class WrongConf:
            def get_dag_run(self, dag_id, dag_run_id):
                return {'dag_id': dag_id, 'dag_run_id': dag_run_id,
                    'state': 'running', 'conf': {**expected_conf, 'attempt': 2}}
        with pytest.raises(ValueError, match='conf'):
            sync_gatk_airflow_status(
                session=session, airflow_client=WrongConf(), analysis_id=AID,
                settings=settings,
            )
        assert run.status == 'queued'
        result = sync_gatk_airflow_status(
            session=session, airflow_client=Client(), analysis_id=AID,
            settings=settings,
        )
        assert result['status'] == 'running'
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.dag_run_id = current_dag + '-forged'
    with factory() as session:
        with pytest.raises(MissingDagRunError):
            sync_gatk_airflow_status(
                session=session, airflow_client=airflow, analysis_id=AID,
                settings=settings,
            )
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.dag_run_id = current_dag
        run.params_json = dict(run.params_json or {}, resume_action_id=action.payload_json['action_id'])
        session.scalar(select(RunAction)).result_status = 'failed'
    with factory() as session:
        with pytest.raises(MissingDagRunError):
            sync_gatk_airflow_status(
                session=session, airflow_client=airflow, analysis_id=AID,
                settings=settings,
            )
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.dag_run_id = current_dag
        run.params_json = dict(run.params_json or {}, resume_action_id='forged-action')
        session.scalar(select(RunAction)).result_status = 'queued'
    with factory() as session:
        with pytest.raises(MissingDagRunError):
            sync_gatk_airflow_status(
                session=session, airflow_client=airflow, analysis_id=AID,
                settings=settings,
            )


@pytest.mark.parametrize('prior_status', ['running', 'failed'])
def test_gatk_airflow_success_cannot_replace_native_finalization(recovery, prior_status):
    from app.gatk_airflow_sync import sync_gatk_airflow_status
    factory, settings, _, _ = _marked_step6_success(recovery)
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.status = prior_status
        run.dag_run_id = f'{AID}-a1'
        run.current_stage = 'step6_materialize'
        for row in session.scalars(select(PipelineStageExecution)):
            if row.stage_code == 'step3_monitor':
                row.status = 'success'
    class AdminSuccess:
        def get_dag_run(self, dag_id, dag_run_id):
            return {'dag_id': dag_id, 'dag_run_id': dag_run_id, 'state': 'success'}
    with factory() as session:
        result = sync_gatk_airflow_status(
            session=session, airflow_client=AdminSuccess(), analysis_id=AID,
            settings=settings,
        )
        assert result['status'] == prior_status
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.status == prior_status
        assert run.pipeline_finished_at is None
