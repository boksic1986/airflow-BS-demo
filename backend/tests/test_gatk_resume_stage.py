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
