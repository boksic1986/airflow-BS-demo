"""One synthetic recovery slice: durable action, frozen request and stale evidence."""
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, RunAction, RunStageState, WgsStageExecution
from app.wgs_stage_execution_service import transition_stage_execution

AID = 'WGS_20260915_010203_A1B2C3'
RELEASE = 'wgs-4.2.1-34bfcbf'


@pytest.fixture
def setup(tmp_path):
    engine = create_engine('sqlite+pysqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = SimpleNamespace(wgs_runtime_request_root=str(tmp_path/'requests'),
        wgs_stage_contract_path=str(Path(__file__).parents[2]/'config/wgs_stage_contract.yaml'),
        wgs_runtime_shared_gid=None, wgs_contract_v2_enabled=True)
    payload = {'schema_version':'wgs-runtime.request.v4', 'analysis_id':AID, 'attempt':1,
        'stage':'step3_monitor', 'pipeline_release_id':RELEASE, 'wgs_version':'V4.2.1',
        'wgs_source_commit':'34bfcbf'+'a'*33, 'control_workdir':'/frozen/control',
        'expected_batch_root':'/frozen/batch', 'analysis_project_root':'/frozen',
        'project_name':'synthetic', 'batch_no':'mock', 'fq_path':'/frozen/fastq',
        'orchestration_contract_version':2, 'execution_id':'old-step3', 'generation':1,
        'request_hash':'a'*64, 'predecessor_execution_id':'old-step2',
        'predecessor_generation':1, 'predecessor_receipt_hash':'b'*64}
    path = tmp_path/'requests'/AID/'attempt-1'/'step3_monitor.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload))
    now = datetime(2026, 9, 14, tzinfo=timezone.utc)
    with factory.begin() as s:
        s.add(AnalysisRun(analysis_id=AID, pipeline_name='wgs', dag_id='bio_wgs',
            dag_run_id='original', workdir='/frozen/control', status='failed',
            current_stage='step3_monitor', attempt=1, ended_at=now,
            params_json={'orchestration_contract_version':2, 'pipeline_release_id':RELEASE,
                'project_name':'synthetic','batch_no':'mock','fq_path':'/frozen/fastq',
                'wgs_version':'V4.2.1','wgs_source_commit':'34bfcbf'+'a'*33}))
        for code, identity, state in [('step2_master','old-step2','success'),('step3_monitor','old-step3','failed')]:
            s.add(WgsStageExecution(execution_id=identity,analysis_id=AID,attempt=1,
                stage_code=code,generation=1,status=state,request_hash='a'*64,
                release_id=RELEASE,receipt_hash='b'*64,started_at=now,ended_at=now))
            s.add(RunStageState(analysis_id=AID,attempt=1,stage_code=code,
                progress_source='synthetic',
                stage_status=state,stage_label=code,step_number=2 if code=='step2_master' else 3,
                started_at=now,ended_at=now,updated_at=now))
    class Airflow:
        def __init__(self): self.runs={}; self.posts=[]; self.lose_reply=False
        def get_dag_run(self, dag, identity):
            if identity in self.runs and getattr(self,'lose_lookup',False):
                self.lose_lookup=False
                raise httpx.ReadTimeout('synthetic lost reconciliation response')
            if identity not in self.runs:
                raise httpx.HTTPStatusError('missing',request=httpx.Request('GET','http://synthetic'),response=httpx.Response(404))
            return self.runs[identity]
        def trigger_dag_run(self, dag, *, dag_run_id, conf):
            self.posts.append((dag,dag_run_id,conf))
            self.runs[dag_run_id]={'dag_run_id':dag_run_id,'state':'queued','conf':conf}
            if self.lose_reply: raise httpx.ReadTimeout('synthetic lost response')
            return self.runs[dag_run_id]
    yield factory, settings, Airflow(), path, payload
    engine.dispose()


def service():
    assert importlib.util.find_spec('app.wgs_resume_service'), 'resume-stage service is not implemented'
    return importlib.import_module('app.wgs_resume_service')


def request(setup, key='same-click', **override):
    factory,settings,client,_,_=setup
    with factory() as session:
        return service().request_resume_stage(session=session,settings=settings,
            airflow_client=client,analysis_id=AID,attempt=override.get('attempt',1),
            stage=override.get('stage','step3_monitor'),idempotency_key=key,requested_by='operator')


def test_same_attempt_action_preserves_frozen_identity_and_reserves_only_new_stage_generation(setup):
    first=request(setup); second=request(setup)
    factory,_,client,path,original=setup
    assert first==second and first['generation']==2 and first['attempt']==1
    assert len(client.posts)==1
    conf=client.posts[0][2]
    assert conf['resume_stage']=='step3_monitor' and conf['resume_action_id']==first['action_id']
    assert conf['resume_stages']==['step3_monitor','step4_publish','step5_download','step6_materialize']
    assert conf['workdir']=='/frozen/control' and conf['params']['pipeline_release_id']==RELEASE
    saved=json.loads(path.read_text())
    assert saved['generation']==2 and saved['resume_action_id']==first['action_id']
    for key in ('analysis_id','attempt','pipeline_release_id','control_workdir','expected_batch_root','wgs_source_commit'):
        assert saved[key]==original[key]
    with factory() as session:
        run=session.scalar(select(AnalysisRun)); rows=session.scalars(select(WgsStageExecution)).all()
        assert run.attempt==1 and run.workdir=='/frozen/control' and run.dag_run_id!= 'original'
        assert run.ended_at is None and len(rows)==3
        assert session.get(WgsStageExecution, rows[0].id).status=='success'
        old=session.scalar(select(WgsStageExecution).where(WgsStageExecution.execution_id=='old-step3'))
        assert old.status=='failed' and old.ended_at is not None
        assert not transition_stage_execution(session=session,execution_id='old-step3',generation=1,status='running')
        assert len(session.scalars(select(RunAction).where(RunAction.action=='resume_stage')).all())==1


@pytest.mark.parametrize('recovery_status', ['reserved', 'queued', 'uncertain'])
def test_manual_resume_cannot_bypass_pending_compute_recovery(setup, recovery_status):
    factory, _, client, path, _ = setup
    original = path.read_bytes()
    with factory.begin() as session:
        session.add(RunAction(analysis_id=AID, action='cce_compute_recovery',
            result_status=recovery_status, payload_json={'attempt': 1, 'action_id': 'synthetic-auto'}))
    with pytest.raises(ValueError, match='automatic recovery'):
        request(setup)
    assert client.posts == []
    assert path.read_bytes() == original
    with factory() as session:
        assert len(session.scalars(select(WgsStageExecution)).all()) == 2
        assert session.scalar(select(RunAction).where(RunAction.action == 'resume_stage')) is None


def test_manual_resume_after_automatic_exhaustion_preserves_history(setup):
    factory, _, client, _, _ = setup
    with factory.begin() as session:
        session.add(RunAction(analysis_id=AID, action='cce_compute_recovery',
            result_status='failed', payload_json={'attempt': 1, 'action_id': 'synthetic-auto', 'ordinal': 2}))
    result = request(setup)
    assert result['attempt'] == 1 and len(client.posts) == 1
    with factory() as session:
        previous = session.scalar(select(RunAction).where(RunAction.action == 'cce_compute_recovery'))
        assert previous.payload_json['ordinal'] == 2 and previous.result_status == 'failed'


def test_lost_airflow_post_response_is_reconciled_without_second_submission(setup):
    setup[2].lose_reply=True
    setup[2].lose_lookup=True
    first=request(setup)
    assert first['status']=='uncertain'
    with setup[0]() as session:
        assert session.scalar(select(AnalysisRun)).status=='failed'
    assert request(setup,key='refresh-click')['action_id']==first['action_id']
    assert request(setup)['action_id']==first['action_id']
    assert len(setup[2].posts)==1


def test_foreign_attempt_prepare_and_competing_action_are_rejected(setup):
    with pytest.raises(ValueError): request(setup,attempt=2)
    with pytest.raises(ValueError): request(setup,stage='prepare')
    request(setup)
    assert request(setup,key='second-click')['action_id']==request(setup)['action_id']
    with pytest.raises(ValueError): request(setup,key='other-stage',stage='step4_publish')
    assert len(setup[2].posts)==1


def test_original_dag_failure_cannot_reclose_recovery(setup):
    request(setup)
    from app.wgs_submission_service import mark_submission_dag_failed
    with setup[0]() as session:
        result=mark_submission_dag_failed(session=session,analysis_id=AID,attempt=1,
            failed_task_ids=['wait_step3_analysis'])
        assert result.get('ignored') is True
        assert session.scalar(select(AnalysisRun)).status!='failed'
        run=session.scalar(select(AnalysisRun))
        result=mark_submission_dag_failed(session=session,analysis_id=AID,attempt=1,
            failed_task_ids=['wait_step3_analysis'],dag_run_id=run.dag_run_id,
            resume_action_id=run.params_json['resume_action_id'])
        assert not result.get('ignored') and run.status=='failed'


def test_post_intent_is_durable_before_airflow_side_effect(setup):
    factory, _, client, path, _ = setup
    original = client.trigger_dag_run
    def post(dag, *, dag_run_id, conf):
        with factory() as session:
            action = session.scalar(select(RunAction))
            run = session.scalar(select(AnalysisRun))
            assert action.payload_json['dispatch_state'] == 'post_intent'
            assert action.payload_json['dag_run_id'] == run.dag_run_id == dag_run_id
            assert json.loads(path.read_text())['generation'] == action.payload_json['generation']
        return original(dag, dag_run_id=dag_run_id, conf=conf)
    client.trigger_dag_run = post
    assert request(setup)['status'] == 'queued'


def test_lost_response_followed_by_404_never_posts_again(setup):
    client = setup[2]
    def lost(dag, *, dag_run_id, conf):
        client.posts.append((dag, dag_run_id, conf))
        raise httpx.ReadTimeout('synthetic POST may have reached Airflow')
    client.trigger_dag_run = lost
    first = request(setup)
    assert first['status'] == 'uncertain'
    assert request(setup, key='refresh-click') == first
    assert len(client.posts) == 1
    dag, identity, conf = client.posts[0]
    client.runs[identity] = {'dag_run_id': identity, 'conf': conf, 'state': 'running'}
    assert request(setup)['status'] == 'queued'
    assert len(client.posts) == 1


def test_lookup_failure_before_post_does_not_consume_submission_intent(setup):
    client = setup[2]
    original = client.get_dag_run
    def unavailable(*args):
        raise httpx.ReadTimeout('synthetic GET unavailable before any POST')
    client.get_dag_run = unavailable
    assert request(setup)['status'] == 'uncertain'
    assert client.posts == []
    client.get_dag_run = original
    assert request(setup)['status'] == 'queued'
    assert len(client.posts) == 1


@pytest.mark.parametrize('wrong', ['dag_run_id', 'conf'])
def test_wrong_dagrun_response_is_not_confirmation(setup, wrong):
    client = setup[2]
    original = client.trigger_dag_run
    def post(dag, **kwargs):
        found = dict(original(dag, **kwargs))
        found[wrong] = 'foreign-dag' if wrong == 'dag_run_id' else {}
        return found
    client.trigger_dag_run = post
    assert request(setup)['status'] == 'uncertain'
    with setup[0]() as session:
        assert session.scalar(select(AnalysisRun)).status == 'failed'
    assert request(setup)['status'] == 'queued'
    assert len(client.posts) == 1


def test_legacy_uncertain_action_without_post_journal_is_read_only(setup):
    first = request(setup)
    with setup[0].begin() as session:
        action = session.scalar(select(RunAction))
        action.result_status = 'uncertain'
        data = dict(action.payload_json)
        data.pop('dispatch_state', None)
        action.payload_json = data
    setup[2].runs.clear()
    assert request(setup)['status'] == 'uncertain'
    assert len(setup[2].posts) == 1
    assert first['attempt'] == 1


@pytest.mark.parametrize('state', ['running', 'success', 'pause_requested', 'canceled'])
def test_late_airflow_reply_does_not_regress_current_control_or_progress(setup, state):
    factory, _, client, _, _ = setup
    original = client.trigger_dag_run
    def post(dag, **kwargs):
        result = original(dag, **kwargs)
        with factory.begin() as session:
            run = session.scalar(select(AnalysisRun))
            run.status = state
            run.current_stage = 'step4_publish'
        return result
    client.trigger_dag_run = post
    request(setup)
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.status == state and run.current_stage == 'step4_publish'


@pytest.mark.parametrize('dag_id', [None, 'original'])
@pytest.mark.parametrize('stage', ['step3_monitor', 'acquire_result_transfer_slot', 'finalize_run'])
def test_old_dag_cannot_advance_current_recovery(setup, monkeypatch, dag_id, stage):
    from app import main
    from fastapi import HTTPException
    receipt = request(setup)
    monkeypatch.setattr(main, 'get_sessionmaker', lambda: setup[0])
    monkeypatch.setattr(main, 'get_settings', lambda: setup[1])
    monkeypatch.setattr(main, '_wgs_runtime_adapter_enabled', lambda: True)
    calls = []
    monkeypatch.setattr(main, 'load_wgs_release_catalog', lambda *a: calls.append('catalog'))
    with pytest.raises(HTTPException) as error:
        main.internal_wgs_runtime_stage(AID, stage, main.WgsRuntimeStageRequest(
            attempt=1, adapter='wgs-runtime-200', command=f'wgs-runtime {AID} 1 {stage}',
            resume_action_id=receipt['action_id'], dag_run_id=dag_id))
    assert error.value.status_code == 400
    assert calls == []


def test_stage_handler_replays_current_stage_and_blocks_prepare(setup, monkeypatch):
    from app import main
    from fastapi import HTTPException
    receipt = request(setup)
    monkeypatch.setattr(main, 'get_sessionmaker', lambda: setup[0])
    monkeypatch.setattr(main, 'get_settings', lambda: setup[1])
    monkeypatch.setattr(main, '_wgs_runtime_adapter_enabled', lambda: True)
    dag_id = setup[2].posts[0][1]
    def register(stage):
        return main.internal_wgs_runtime_stage(AID, stage, main.WgsRuntimeStageRequest(
            attempt=1, adapter='wgs-runtime-200', command=f'wgs-runtime {AID} 1 {stage}',
            resume_action_id=receipt['action_id'], dag_run_id=dag_id))
    current = register('step3_monitor')
    assert current['generation'] == receipt['generation']
    frozen = json.loads(setup[3].read_text())
    assert current['request_hash'] == frozen['request_hash']
    assert current['stage_execution'] == frozen['stage_execution']
    assert register('step3_monitor') == current
    with pytest.raises(HTTPException) as error:
        register('prepare')
    assert error.value.status_code == 400
    assert len(setup[2].posts) == 1
    with setup[0].begin() as session:
        session.scalar(select(AnalysisRun)).status = 'pause_requested'
    with pytest.raises(HTTPException) as error:
        register('step3_monitor')
    assert 'control state' in str(error.value.detail)


def test_http_resume_requires_login_csrf_and_operator_then_replays(setup, monkeypatch):
    from app import main
    from app.auth_service import AuthenticatedUser
    from fastapi.testclient import TestClient
    settings = setup[1]
    settings.auth_required = True
    settings.internal_service_token = ''
    monkeypatch.setattr(main, 'get_settings', lambda: settings)
    monkeypatch.setattr(main, 'get_sessionmaker', lambda: setup[0])
    monkeypatch.setattr(main, 'get_airflow_client', lambda: setup[2])
    monkeypatch.setattr(main, '_wgs_platform_execution_enabled', lambda: True)
    monkeypatch.setattr(main, '_wgs_runtime_adapter_enabled', lambda: True)
    actor = ['viewer']
    monkeypatch.setattr(main, 'authenticate_session', lambda **kw:
        AuthenticatedUser(1, 'synthetic-operator', actor[0], 'synthetic-csrf') if kw['raw_token'] else None)
    client = TestClient(main.app)
    url = f'/api/runs/{AID}/actions/resume-stage'
    body = {'attempt': 1, 'stage': 'step3_monitor', 'idempotency_key': 'http-same-click'}
    assert client.post(url, json=body).status_code == 401
    client.cookies.set(main.SESSION_COOKIE, 'synthetic-session')
    assert client.post(url, json=body).status_code == 403
    client.headers['X-CSRF-Token'] = 'synthetic-csrf'
    assert client.post(url, json=body).status_code == 403
    assert setup[2].posts == []
    actor[0] = 'operator'
    first = client.post(url, json=body)
    assert first.status_code == 200, first.text
    assert client.post(url, json=body).json() == first.json()
    assert len(setup[2].posts) == 1
    with setup[0]() as session:
        assert session.scalar(select(RunAction)).requested_by == 'synthetic-operator'
    client.close()


@pytest.mark.parametrize('observed_state', ['failed', 'queued'])
def test_reconciliation_preserves_current_dag_failure_before_executor_starts(setup, observed_state):
    from app.wgs_submission_service import mark_submission_dag_failed
    factory, _, client, _, _ = setup
    client.lose_reply = client.lose_lookup = True
    result = request(setup)
    assert result['status'] == 'uncertain'
    dag_id = client.posts[0][1]
    with factory() as session:
        failed = mark_submission_dag_failed(session=session, analysis_id=AID, attempt=1,
            dag_run_id=dag_id, resume_action_id=result['action_id'], failed_task_ids=['validate_request'])
        ended = session.scalar(select(AnalysisRun)).ended_at
    client.runs[dag_id]['state'] = observed_state
    assert request(setup)['status'] == 'queued'  # dispatch confirmed, NOT analysis queued
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.status == 'failed' and run.error_summary == failed['error_summary']
        assert run.ended_at == ended and run.pipeline_finished_at is not None


def stage_handler(setup, monkeypatch):
    from app import main
    setup[1].wgs_release_catalog_path = '/synthetic/catalog'
    monkeypatch.setattr(main, 'get_sessionmaker', lambda: setup[0])
    monkeypatch.setattr(main, 'get_settings', lambda: setup[1])
    monkeypatch.setattr(main, '_wgs_runtime_adapter_enabled', lambda: True)
    monkeypatch.setattr(main, 'load_wgs_release_catalog', lambda path:
        SimpleNamespace(by_id=lambda release_id: SimpleNamespace()))
    return main


def _step2_status_marker(setup):
    path = setup[3].parent / 'step2_master.status.json'
    path.write_text(json.dumps({
        'schema_version': 'wgs-runtime.stage-status.v1',
        'orchestration_contract_version': 2,
        'analysis_id': AID, 'attempt': 1, 'stage': 'step2_master',
        'execution_id': 'old-step2', 'generation': 1, 'request_hash': 'a' * 64,
        'status': 'success', 'updated_at': datetime.now(timezone.utc).isoformat(),
    }))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normal_step3_handler(setup, monkeypatch):
    main = stage_handler(setup, monkeypatch)
    settings = setup[1]
    settings.wgs_transfer_spool_root = str(setup[3].parents[2] / 'transfer-spool')
    settings.wgs_runtime_node200_root = '/synthetic/runtime'
    settings.wgs_results_host_root = '/synthetic/results'
    monkeypatch.setattr(main, 'load_wgs_release_catalog', lambda path: SimpleNamespace(
        by_id=lambda release_id: SimpleNamespace(profile_id='synthetic', profile_revision='r1',
            profile_sha256='a' * 64, node200_profile_path='/synthetic/profile',
            cce_pipeline_version='synthetic', pipeline_build_sha256='b' * 64,
            resource_manifest_sha256='c' * 64)))
    monkeypatch.setattr(main, 'build_stage_request', lambda **kwargs: {
        'analysis_id': kwargs['analysis_id'], 'attempt': kwargs['attempt'],
        'stage': kwargs['stage'], 'pipeline_release_id': kwargs['pipeline_release_id'],
        'wgs_source_commit': kwargs['wgs_source_commit'],
        'control_workdir': '/synthetic/control', 'expected_batch_root': '/synthetic/batch',
    })
    with setup[0].begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.status = 'running'
        run.params_json = dict(run.params_json, fastq_root='/synthetic/fastq')
    return main


@pytest.mark.parametrize('receipt_lagging', [False, True])
def test_predecessor_receipt_visible_before_step3_registration(setup, monkeypatch, receipt_lagging):
    main = _normal_step3_handler(setup, monkeypatch)
    with setup[0].begin() as session:
        if receipt_lagging:
            step2 = session.scalar(select(WgsStageExecution).where(WgsStageExecution.stage_code == 'step2_master'))
            step2.status = 'running'
            step2.receipt_hash = None
    expected_hash = _step2_status_marker(setup) if receipt_lagging else 'b' * 64
    real_sync = main.sync_runtime_stage_artifacts
    calls = []
    def ingest(**kwargs):
        calls.append(kwargs['stage'])
        return real_sync(**kwargs)
    monkeypatch.setattr(main, 'sync_runtime_stage_artifacts', ingest)
    result = main.internal_wgs_runtime_stage(AID, 'step3_monitor', main.WgsRuntimeStageRequest(
        attempt=1, adapter='wgs-runtime-200', command=f'wgs-runtime {AID} 1 step3_monitor'))
    assert calls == (['step2_master'] if receipt_lagging else [])
    assert result['status'] == 'registered'
    with setup[0]() as session:
        latest = session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor').order_by(WgsStageExecution.generation.desc()))
        assert latest.predecessor_execution_id == 'old-step2'
        assert latest.predecessor_generation == 1
        assert latest.predecessor_receipt_hash == expected_hash


@pytest.mark.parametrize('change', ['pause', 'action', 'dag', 'attempt', 'normal_dag', 'normal_pause'])
def test_predecessor_ingestion_rechecks_current_identity(setup, monkeypatch, change):
    receipt_hash = _step2_status_marker(setup)
    normal = change.startswith('normal_')
    if normal:
        main = _normal_step3_handler(setup, monkeypatch)
        recovery = None
    else:
        with setup[0].begin() as session:
            step2 = session.scalar(select(WgsStageExecution).where(WgsStageExecution.stage_code == 'step2_master'))
            step2.receipt_hash = receipt_hash
        recovery = request(setup)
        main = stage_handler(setup, monkeypatch)
    setup[1].wgs_transfer_spool_root = str(setup[3].parents[2] / 'transfer-spool')
    with setup[0].begin() as session:
        step2 = session.scalar(select(WgsStageExecution).where(WgsStageExecution.stage_code == 'step2_master'))
        step2.status = 'running'
        step2.receipt_hash = None
    saved = setup[3].read_bytes()
    real_sync = main.sync_runtime_stage_artifacts
    calls = []
    def ingest(**kwargs):
        calls.append(kwargs['stage'])
        result = real_sync(**kwargs)
        with setup[0].begin() as session:
            run = session.scalar(select(AnalysisRun))
            if change in {'pause', 'normal_pause'}:
                run.status = 'pause_requested'
            elif change == 'action':
                run.params_json = dict(run.params_json, resume_action_id='new-action')
            elif change in {'dag', 'normal_dag'}:
                run.dag_run_id = 'newer-dag'
            else:
                run.attempt = 2
        return result
    monkeypatch.setattr(main, 'sync_runtime_stage_artifacts', ingest)
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        request_data = dict(attempt=1, adapter='wgs-runtime-200',
            command=f'wgs-runtime {AID} 1 step3_monitor')
        if recovery is not None:
            request_data.update(resume_action_id=recovery['action_id'],
                dag_run_id=setup[2].posts[0][1])
        main.internal_wgs_runtime_stage(AID, 'step3_monitor', main.WgsRuntimeStageRequest(**request_data))
    assert calls == ['step2_master']
    assert setup[3].read_bytes() == saved
    with setup[0]() as session:
        assert len(session.scalars(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor')).all()) == (1 if normal else 2)


def test_public_resume_rechecks_dag_identity_after_step2_receipt_ingestion(setup, monkeypatch):
    main = stage_handler(setup, monkeypatch)
    monkeypatch.setattr(main, '_wgs_platform_execution_enabled', lambda: True)
    monkeypatch.setattr(main, 'get_airflow_client', lambda: setup[2])
    setup[1].wgs_transfer_spool_root = str(setup[3].parents[2] / 'transfer-spool')
    _step2_status_marker(setup)
    with setup[0].begin() as session:
        step2 = session.scalar(select(WgsStageExecution).where(WgsStageExecution.stage_code == 'step2_master'))
        step2.status = 'running'
        step2.receipt_hash = None
    original_request = setup[3].read_bytes()
    real_sync = main.sync_runtime_stage_artifacts
    calls = []

    def ingest(**kwargs):
        calls.append(kwargs['stage'])
        result = real_sync(**kwargs)
        with setup[0].begin() as session:
            session.scalar(select(AnalysisRun)).dag_run_id = 'newer-dag'
        return result

    monkeypatch.setattr(main, 'sync_runtime_stage_artifacts', ingest)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        main.resume_wgs_stage(AID, main.WgsResumeStageRequest(
            attempt=1, stage='step3_monitor', idempotency_key='synthetic-public'),
            user=SimpleNamespace(username='synthetic-operator'))
    assert error.value.status_code == 409
    assert calls == ['step2_master']
    assert setup[3].read_bytes() == original_request
    assert setup[2].posts == []
    with setup[0]() as session:
        assert session.scalar(select(RunAction).where(RunAction.action == 'resume_stage')) is None
        assert len(session.scalars(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor')).all()) == 1


@pytest.mark.parametrize('change', ['pause', 'supersede'])
def test_slot_commit_rechecks_control_before_projecting_acquired(setup, monkeypatch, change):
    from app.models import ObsTransferLease
    from app.wgs_platform_service import OBS_TRANSFER_SLOT_BY_KIND
    from fastapi import HTTPException
    result = request(setup)
    main = stage_handler(setup, monkeypatch)
    with setup[0].begin() as session:
        session.add(ObsTransferLease(slot_name=OBS_TRANSFER_SLOT_BY_KIND['result']))
    original = main.acquire_obs_transfer_slot
    def acquire(**kwargs):
        slot = original(**kwargs)  # real commit releases the run lock
        with setup[0].begin() as session:
            run = session.scalar(select(AnalysisRun))
            if change == 'pause':
                run.status = 'pause_requested'
            else:
                run.dag_run_id = 'newer-dag'
        return slot
    monkeypatch.setattr(main, 'acquire_obs_transfer_slot', acquire)
    with pytest.raises(HTTPException):
        main.internal_wgs_runtime_stage(AID, 'acquire_result_transfer_slot', main.WgsRuntimeStageRequest(
            attempt=1, adapter='wgs-runtime-200', resume_action_id=result['action_id'],
            dag_run_id=setup[2].posts[0][1]))
    with setup[0]() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.current_stage == 'step3_monitor'
        assert run.status == 'pause_requested' if change == 'pause' else run.dag_run_id == 'newer-dag'
        # Already committed lease is retained; never release a possibly live transfer.
        assert session.scalar(select(ObsTransferLease)).analysis_id == AID


def test_current_recovery_can_finalize_reused_successful_step6(setup, monkeypatch):
    step6_body = {'analysis_id': AID, 'attempt': 1, 'stage': 'step6_materialize'}
    step6_hash = hashlib.sha256(json.dumps(step6_body, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    with setup[0].begin() as session:
        session.add(WgsStageExecution(execution_id='old-step6', analysis_id=AID, attempt=1,
            stage_code='step6_materialize', generation=1, status='success', request_hash=step6_hash,
            release_id=RELEASE, receipt_hash='d'*64))
    result = request(setup)
    assert 'step6_materialize' not in setup[2].posts[0][2]['resume_stages']
    main = stage_handler(setup, monkeypatch)
    (setup[3].parent/'step6_materialize.json').write_text(json.dumps({
        'orchestration_contract_version': 2, 'analysis_id': AID, 'attempt': 1,
        'stage': 'step6_materialize', 'execution_id': 'old-step6',
        'generation': 1, 'request_hash': step6_hash,
    }))
    (setup[3].parent/'step6_materialize.status.json').write_text(json.dumps({
        'schema_version': 'wgs-runtime.stage-status.v1', 'analysis_id': AID, 'attempt': 1,
        'stage': 'step6_materialize', 'status': 'success'}))
    value = main.internal_wgs_runtime_stage(AID, 'finalize_run', main.WgsRuntimeStageRequest(
        attempt=1, adapter='wgs-runtime-200', resume_action_id=result['action_id'],
        dag_run_id=setup[2].posts[0][1]))
    assert value['status'] == 'success'
    with setup[0]() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.attempt == 1 and run.status == 'success'
        assert len(session.scalars(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step6_materialize')).all()) == 1


@pytest.mark.parametrize('terminal', [
    'old_generation', 'unknown_native', 'current_success', 'missing_marker', 'paused_normal',
])
def test_native_step6_finalize_requires_current_receipt_and_terminal(setup, monkeypatch, terminal):
    from fastapi import HTTPException

    frozen_body = {'analysis_id': AID, 'attempt': 1, 'stage': 'step6_materialize',
        'stage_execution': {'protocol': 'cce.stage-execution.v1'}}
    step6_hash = hashlib.sha256(json.dumps(frozen_body, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    status_path = setup[3].parent / 'step6_materialize.status.json'
    status = {
        'schema_version': 'wgs-runtime.stage-status.v1',
        'orchestration_contract_version': 2, 'analysis_id': AID, 'attempt': 1,
        'stage': 'step6_materialize', 'status': 'success',
        'execution_id': 'current-step6', 'generation': 2, 'request_hash': step6_hash,
    }
    if terminal == 'old_generation':
        status['execution_id'] = 'old-step6'
        status['generation'] = 1
    status_path.write_text(json.dumps(status))
    receipt_hash = hashlib.sha256(status_path.read_bytes()).hexdigest()
    request_path = setup[3].parent / 'step6_materialize.json'
    request_path.write_text(json.dumps({
        'orchestration_contract_version': 2,
        'analysis_id': AID, 'attempt': 1, 'stage': 'step6_materialize',
        'execution_id': 'current-step6', 'generation': 2, 'request_hash': step6_hash,
        'stage_execution': {'protocol': 'cce.stage-execution.v1'},
    }))
    with setup[0].begin() as session:
        session.add(WgsStageExecution(execution_id='old-step6', analysis_id=AID, attempt=1,
            stage_code='step6_materialize', generation=1, status='success', request_hash=step6_hash,
            release_id=RELEASE, receipt_hash='d'*64))
        session.add(WgsStageExecution(execution_id='current-step6', analysis_id=AID, attempt=1,
            stage_code='step6_materialize', generation=2, status='success', request_hash=step6_hash,
            release_id=RELEASE, receipt_hash=receipt_hash,
            evidence_type='wgs-runtime.stage-status.v1',
            evidence_key=f'{AID}/attempt-1/step6_materialize.status.json'))
        session.add(RunStageState(analysis_id=AID, attempt=1, stage_code='step6_materialize',
            stage_status='success', stage_label='Step6', progress_source='materialization',
            progress_available=True, progress_percent=100, updated_at=datetime.now(timezone.utc)))
    recovery = request(setup)
    main = stage_handler(setup, monkeypatch)
    setup[1].wgs_transfer_spool_root = str(setup[3].parents[2] / 'transfer-spool')
    monkeypatch.setattr(main, 'sync_runtime_stage_artifacts', lambda **_kwargs: None)
    projected = main.internal_wgs_runtime_stage_status(AID, attempt=1, stage='step6_materialize')
    assert projected['stage_execution'] == {'protocol': 'cce.stage-execution.v1'}
    if terminal == 'old_generation':
        assert projected['ready'] is False
    else:
        assert projected['ready'] is True
        assert (projected['execution_id'], projected['generation'], projected['request_hash']) == (
            'current-step6', 2, step6_hash)
    with setup[0].begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.status = 'pause_requested' if terminal == 'paused_normal' else 'running'
        run.current_stage = 'step6_materialize'
        run.progress_percent = 100
        if terminal == 'paused_normal':
            params = dict(run.params_json or {})
            params.pop('resume_action_id', None)
            run.params_json = params
            run.dag_run_id = 'original'
    if terminal == 'missing_marker':
        downgraded = json.loads(request_path.read_text())
        downgraded.pop('stage_execution')
        downgraded['orchestration_contract_version'] = 1
        request_path.write_text(json.dumps(downgraded))
        with pytest.raises(HTTPException):
            main.internal_wgs_runtime_stage_status(AID, attempt=1, stage='step6_materialize')
    native = {
        'schema': 'cce.stage-execution.snapshot.v1',
        'execution_ref': {
            'protocol': 'cce.stage-execution.v1', 'pipeline': 'wgs',
            'analysis_id': AID, 'attempt': 1, 'stage': 'step6_materialize',
            'execution_id': 'current-step6', 'stage_generation': 2,
            'request_hash': step6_hash, 'registration_sha256': 'e' * 64,
        },
        'state': 'unknown' if terminal == 'unknown_native' else 'succeeded',
        'evidence_ref': None if terminal == 'unknown_native' else receipt_hash,
        'runtime_identity': None, 'compute_identity': None,
        'observation_health': 'degraded' if terminal == 'unknown_native' else 'healthy',
    }
    command = main.WgsRuntimeStageRequest(
        attempt=1, adapter='wgs-runtime-200',
        resume_action_id=None if terminal == 'paused_normal' else recovery['action_id'],
        dag_run_id='original' if terminal == 'paused_normal' else setup[2].posts[0][1],
        worker_observation=native,
    )
    if terminal == 'current_success':
        assert main.internal_wgs_runtime_stage(AID, 'finalize_run', command)['status'] == 'success'
    else:
        with pytest.raises(HTTPException):
            main.internal_wgs_runtime_stage(AID, 'finalize_run', command)
    with setup[0]() as session:
        run = session.scalar(select(AnalysisRun))
        progress = session.scalar(select(RunStageState).where(RunStageState.stage_code == 'step6_materialize'))
        assert progress.progress_percent == 100
        assert run.status == ('success' if terminal == 'current_success' else
                              'pause_requested' if terminal == 'paused_normal' else 'running')
        assert run.progress_percent == 100


def test_administrative_dag_success_cannot_finalize_unverified_step6(setup, monkeypatch):
    from app import diagnostics_service

    monkeypatch.setattr(diagnostics_service, '_safe_workdir', lambda *_args: setup[3].parent)
    monkeypatch.setattr(diagnostics_service, '_safe_child_path',
        lambda root, child, _settings: root / child)

    with setup[0].begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.status = 'running'
        run.current_stage = 'step6_materialize'
        run.progress_percent = 100
    airflow = SimpleNamespace(
        get_dag_run=lambda *_args: {'state': 'success', 'end_date': datetime.now(timezone.utc).isoformat()},
        list_task_instances=lambda *_args: {'task_instances': []},
    )
    with setup[0]() as session:
        view = diagnostics_service.sync_wgs_airflow_status(session=session, airflow_client=airflow,
            analysis_id=AID, settings=setup[1])
        run = session.scalar(select(AnalysisRun))
        assert view['status'] == run.status == 'running'
        assert run.current_stage == 'step6_materialize'
        assert run.progress_percent == 100
