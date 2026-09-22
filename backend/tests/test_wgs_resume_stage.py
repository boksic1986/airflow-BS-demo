"""One synthetic recovery slice: durable action, frozen request and stale evidence."""
from datetime import datetime, timezone
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
    engine = create_engine('sqlite+pysqlite://', poolclass=StaticPool)
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
