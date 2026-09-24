"""Existing Airflow sensor boundary owns waiting; no independent daemon."""
from datetime import timedelta
from copy import deepcopy
import importlib

import pytest
from sqlalchemy import select

from app.models import AnalysisRun, RunAction
from test_cce_recovery_dispatch import automatic, setup, recovery, evidence, NOW
from test_cce_recovery_evidence import digest


def poll(case, seconds, dag='original', action_id=None):
    fixture, _, aid, _ = case
    factory, settings, airflow, _, _ = fixture
    with factory() as session:
        return importlib.import_module('app.cce_recovery_poll').poll_compute_recovery(
            session=session,settings=settings,airflow_client=airflow,analysis_id=aid,
            attempt=1,pipeline='wgs' if aid.startswith('WGS_') else 'gatk',
            dag_run_id=dag,resume_action_id=action_id,now=NOW+timedelta(seconds=seconds))


def test_airflow_polls_reserved_action_then_hands_off_without_advancing_old_dag(automatic):
    fixture, model, _, data = automatic
    factory, _, airflow, _, _ = fixture
    assert poll(automatic,10)['status']=='waiting'
    assert not airflow.posts
    assert poll(automatic,60)['status']=='delegated'
    assert poll(automatic,61)['status']=='delegated'
    assert len(airflow.posts)==1
    dag=airflow.posts[0][1]
    # The new DagRun alone may settle this action's exact registered monitor.
    with factory.begin() as session:
        row=session.scalar(select(model).where(model.stage_code=='step3_monitor').order_by(model.generation.desc()))
        row.status='success'
    assert poll(automatic,62,dag,data['action_id'])['status']=='complete'
    with factory() as session:
        action=session.scalar(select(RunAction))
        assert action.payload_json['compute_terminal']=='success'
        assert action.result_status=='queued'  # Still authorizes necessary downstream stages.
    assert poll(automatic,63)['status']=='delegated'


def test_wrong_dag_or_identity_never_reserves_or_dispatches(automatic):
    fixture, _, _, _ = automatic
    assert poll(automatic,60,dag='unrelated')['status']=='superseded'
    assert not fixture[2].posts
    with fixture[0]() as session:
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count']==1


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
        row.status='failed';row.terminal_payload_json=payload
        session.scalar(select(AnalysisRun)).current_stage='step3_monitor'
    second=poll(automatic,70,first_dag,first['action_id'])
    assert second['status']=='waiting'
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
