"""First Step4 freezes authority; replay must not slide it or grant another send."""
from datetime import timedelta
from types import SimpleNamespace
import json

import pytest
from sqlalchemy import select
from app.models import AnalysisRun, PipelineStageExecution, WgsStageExecution, RunAction
from test_cce_recovery_budget import run_store, NOW


@pytest.fixture
def registered(run_store, tmp_path):
    from app.wgs_stage_execution_service import register_stage_execution
    from app.wgs_stage_catalog import load_wgs_stage_contract
    from app.gatk_runtime_service import register_gatk_stage, _request_path
    from test_wgs_stage_execution import contract_path
    settings = SimpleNamespace(wgs_runtime_request_root=str(tmp_path),
        gatk_runtime_request_root=str(tmp_path),gatk_runtime_node200_root='/synthetic/runtime')
    with run_store.begin() as session:
        run=session.scalar(select(AnalysisRun)); pipeline=run.pipeline_name
        run.status='running';run.dag_run_id='original-dag'
        model=WgsStageExecution if pipeline=='wgs' else PipelineStageExecution
        kw=dict(analysis_id=run.analysis_id,attempt=1,stage_code='step3_monitor',
            execution_id='monitor',generation=1,status='success',request_hash='b'*64,
            receipt_hash='c'*64,release_id='frozen')
        if pipeline=='gatk':kw['pipeline_name']='gatk'
        session.add(model(**kw))
        run.params_json=dict(run.params_json,orchestration_contract_version=2)
    with run_store() as session:
        run=session.scalar(select(AnalysisRun))
        if pipeline=='wgs':
            payload=dict(analysis_id=run.analysis_id,attempt=1,stage='step4_publish',orchestration_contract_version=2)
            row=register_stage_execution(session=session,run=run,
                contract=load_wgs_stage_contract(contract_path()),stage_code='step4_publish',
                request_payload=payload,now=NOW)
            payload.update(execution_id=row.execution_id,generation=row.generation,
                request_hash=row.request_hash,orchestration_contract_version=2)
            path=tmp_path/run.analysis_id/'attempt-1'/'step4_publish.json'
            path.parent.mkdir(parents=True);path.write_text(json.dumps(payload))
            run.current_stage='step4_publish';session.commit()
        else:
            register_gatk_stage(session=session,settings=settings,analysis_id=run.analysis_id,
                attempt=1,stage='step4_publish')
            path=_request_path(settings,run.analysis_id,1,'step4_publish')
            payload=json.loads(path.read_text())
    return run_store,settings,pipeline,payload,path


def test_real_registration_freezes_publish_marker_and_reuses_original_deadline(registered):
    factory,settings,pipeline,payload,path=registered
    assert payload.get('publish_dispatch_version')==1
    assert payload.get('publish_deadline')
    with factory() as session:
        run=session.scalar(select(AnalysisRun))
        assert run.params_json['cce_publish_deadline']==payload['publish_deadline']
        assert run.params_json['cce_recovery_budget']['count']==0
        if pipeline=='wgs':
            from app.wgs_stage_execution_service import register_stage_execution
            from app.wgs_stage_catalog import load_wgs_stage_contract
            from test_wgs_stage_execution import contract_path
            again=dict(analysis_id=run.analysis_id,attempt=1,stage='step4_publish',orchestration_contract_version=2)
            row=register_stage_execution(session=session,run=run,
                contract=load_wgs_stage_contract(contract_path()),stage_code='step4_publish',
                request_payload=again,now=NOW+timedelta(hours=1))
            assert row.execution_id==payload['execution_id']
            assert again['publish_deadline']==payload['publish_deadline']
        else:
            from app.gatk_runtime_service import register_gatk_stage
            raw=path.read_bytes()
            register_gatk_stage(session=session,settings=settings,analysis_id=run.analysis_id,
                attempt=1,stage='step4_publish')
            assert path.read_bytes()==raw


def call(registered,operation,**kw):
    from app.cce_publish_recovery import control_publish_dispatch
    factory,settings,pipeline,payload,_=registered
    with factory() as session:
        return control_publish_dispatch(session=session,settings=settings,pipeline=pipeline,
            analysis_id=payload['analysis_id'],attempt=1,dag_run_id='original-dag',
            resume_action_id=None,operation=operation,now=NOW,**kw)


def test_control_commits_intent_and_lost_begin_does_not_resend(registered):
    first=call(registered,'begin')
    assert first['dispatch'] is True and first['sequence']==0
    with registered[0]() as session:
        assert session.scalar(select(RunAction)).payload_json['in_flight'] is True
    assert call(registered,'begin')['dispatch'] is False
    call(registered,'finish',execution_id=first['execution_id'],sequence=0)
    reply=call(registered,'poll')
    assert reply['probe']['execution_id']==first['execution_id']
    with registered[0]() as session:
        assert session.scalar(select(RunAction)).payload_json['in_flight'] is False


@pytest.mark.parametrize('fault',['paused','changed_request','foreign_dag','pending_control'])
def test_control_rejects_before_granting_initial_send(registered,fault):
    factory,_,_,payload,path=registered
    with factory.begin() as session:
        run=session.scalar(select(AnalysisRun))
        if fault=='paused':run.status='paused'
        if fault=='foreign_dag':run.dag_run_id='replacement'
        if fault=='pending_control':session.add(RunAction(analysis_id=run.analysis_id,
            action='delete',requested_by='operator',result_status='reserved',payload_json={'attempt':1}))
    if fault=='changed_request':
        path.write_text(json.dumps(dict(payload,publish_dispatch_version=2)))
    with pytest.raises(ValueError):call(registered,'begin')
    with factory() as session:
        assert not session.scalar(select(RunAction).where(RunAction.action=='cce_publish_dispatch'))


def test_pending_publish_blocks_manual_resume_but_not_stop(registered):
    from app.cce_recovery_budget import require_no_pending_compute_recovery
    call(registered,'begin')
    with registered[0]() as session:
        with pytest.raises(ValueError,match='publish'):
            require_no_pending_compute_recovery(session=session,run=session.scalar(select(AnalysisRun)))


def test_initial_registration_authorization_rejects_stale_dag_before_mutation(registered):
    from app.cce_publish_recovery import authorize_publish_registration
    with registered[0]() as session:
        run=session.scalar(select(AnalysisRun));before=dict(run.params_json)
        with pytest.raises(ValueError):
            authorize_publish_registration(session=session,run=run,dag_run_id='old-dag',resume_action_id=None)
        assert run.params_json==before


def test_lost_terminal_registration_reply_reuses_failed_operation(registered):
    factory,settings,pipeline,payload,_=registered
    with factory.begin() as session:
        model=WgsStageExecution if pipeline=='wgs' else PipelineStageExecution
        row=session.scalar(select(model).where(model.stage_code=='step4_publish'));row.status='failed'
    with factory() as session:
        if pipeline=='wgs':
            from app.wgs_stage_execution_service import register_stage_execution
            from app.wgs_stage_catalog import load_wgs_stage_contract
            from test_wgs_stage_execution import contract_path
            run=session.scalar(select(AnalysisRun))
            again=dict(analysis_id=run.analysis_id,attempt=1,stage='step4_publish',orchestration_contract_version=2)
            row=register_stage_execution(session=session,run=run,contract=load_wgs_stage_contract(contract_path()),
                stage_code='step4_publish',request_payload=again,now=NOW+timedelta(hours=1),force_new_generation=True)
            actual=row.execution_id
        else:
            from app.gatk_runtime_service import register_gatk_stage
            actual=register_gatk_stage(session=session,settings=settings,analysis_id=payload['analysis_id'],
                attempt=1,stage='step4_publish')['execution_id']
        assert actual==payload['execution_id']


def test_existing_authenticated_stage_route_uses_durable_publish_action(registered,monkeypatch):
    from app import main
    factory,settings,pipeline,payload,_=registered
    settings.gatk_execution_enabled=True
    monkeypatch.setattr(main,'get_sessionmaker',lambda:factory)
    monkeypatch.setattr(main,'get_settings',lambda:settings)
    monkeypatch.setattr(main,'_wgs_runtime_adapter_enabled',lambda:True)
    monkeypatch.setattr(main,'datetime',SimpleNamespace(now=lambda tz:NOW))
    kind=main.WgsRuntimeStageRequest if pipeline=='wgs' else main.GatkRuntimeStageRequest
    endpoint=main.internal_wgs_runtime_stage if pipeline=='wgs' else main.internal_gatk_runtime_stage
    request=kind(attempt=1,adapter=pipeline+'-runtime-200',dag_run_id='original-dag',publish_operation='begin')
    assert endpoint(payload['analysis_id'],'publish_recovery',request)['dispatch'] is True
    assert endpoint(payload['analysis_id'],'publish_recovery',request)['dispatch'] is False
