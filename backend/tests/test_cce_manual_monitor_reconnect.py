"""Explicit same-attempt monitor handoff, never a new automatic compute slot."""
import importlib
import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import AnalysisRun, RunAction
from app.cce_monitor_observation import retain_monitor_observation
from app.cce_resume_dispatch import authorize_recovery_stage
from test_cce_recovery_dispatch import automatic, setup, recovery, evidence, NOW, dispatch


def interrupted(case, *, phase='exhausted'):
    fixture, model, _, _ = case
    with fixture[0].begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.status = 'running'
        row = session.scalar(select(model).where(model.stage_code=='step3_monitor')
            .order_by(model.generation.desc()))
        row.status = 'failed'
        scope = dict(pipeline=run.pipeline_name,analysis_id=run.analysis_id,attempt=1,
            stage=row.stage_code,execution_id=row.execution_id,generation=row.generation,request_hash=row.request_hash)
        retain_monitor_observation(row, dict(updated_at=NOW.isoformat(),monitoring_health='degraded',
            monitor_reconnect=dict(version=1,scope=scope,phase=phase,retries_used=6,
                deadline=(NOW+timedelta(hours=1)).timestamp())), pipeline=run.pipeline_name)


def resume(case, key):
    fixture, _, aid, _ = case
    factory, settings, airflow, _, _ = fixture
    if aid.startswith('WGS_'):
        fn = importlib.import_module('app.wgs_resume_service').request_resume_stage
    else:
        fn = importlib.import_module('app.gatk_runtime_service').request_gatk_resume_stage
    with factory() as session:
        return fn(session=session,settings=settings,airflow_client=airflow,analysis_id=aid,
            attempt=1,stage='step3_monitor',idempotency_key=key,requested_by='operator')


def test_explicit_reconnect_hands_off_auto_then_manual_without_resetting_budget(automatic):
    fixture, model, _, auto = automatic
    factory, _, airflow, path, _ = fixture
    assert dispatch(automatic,60)['status']=='queued'
    original = json.loads(path.read_text())
    old_dag = airflow.posts[-1][1]
    for key, generation in [('manual-one',3),('manual-two',4)]:
        interrupted(automatic)
        result = resume(automatic,key)
        assert result['generation']==generation and result['status']=='queued'
        assert resume(automatic,key)==result
        # A concurrent new click while the new observer is active is the same action.
        assert resume(automatic,key+'-duplicate')==result
        saved = json.loads(path.read_text())
        assert saved['cce_recovery_deadline']==original['cce_recovery_deadline']
        assert saved['attempt']==1
        assert len(airflow.posts)==generation-1
        with factory() as session:
            run = session.scalar(select(AnalysisRun))
            assert run.params_json['cce_recovery_budget']['count']==1
            assert run.params_json['cce_recovery_budget']['original_deadline']==original['cce_recovery_deadline']
            actions = session.scalars(select(RunAction).order_by(RunAction.id)).all()
            assert all(a.result_status=='canceled' for a in actions[:-1])
            assert all('compute_terminal' not in a.payload_json for a in actions)
            assert actions[-2].payload_json['monitor_handoff_to']==result['action_id']
            with pytest.raises(ValueError):
                authorize_recovery_stage(session=session,run=run,action_id=auto['action_id'],
                    dag_run_id=old_dag,stage='step4_publish')
            authorize_recovery_stage(session=session,run=run,action_id=result['action_id'],
                dag_run_id=run.dag_run_id,stage='step3_monitor')
            old_rows = session.scalars(select(model).where(model.stage_code=='step3_monitor',
                model.generation<generation)).all()
            assert all(row.status=='failed' for row in old_rows)


@pytest.mark.parametrize('change', ['reserved','uncertain','waiting','foreign_scope','generation','stop','frozen'])
def test_unconfirmed_dispatch_or_active_foreign_monitor_cannot_be_handed_off(automatic,change):
    fixture, model, _, _ = automatic
    factory, _, airflow, path, _ = fixture
    assert dispatch(automatic,60)['status']=='queued'
    interrupted(automatic,phase='waiting' if change=='waiting' else 'exhausted')
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        action = session.scalar(select(RunAction))
        if change in {'reserved','uncertain'}: action.result_status=change
        if change=='generation': action.payload_json=dict(action.payload_json,generation=99)
        if change=='stop': run.status='pause_requested'
        if change=='foreign_scope':
            row=session.scalar(select(model).where(model.stage_code=='step3_monitor',model.generation==2))
            payload=dict(row.terminal_payload_json)
            observation=dict(payload['cce_monitor_observation'])
            value=dict(observation['monitor_reconnect'])
            value['scope']=dict(value['scope'],generation=99)
            observation['monitor_reconnect']=value
            row.terminal_payload_json=dict(payload,cce_monitor_observation=observation)
    if change=='frozen':
        payload=json.loads(path.read_text());payload['execution_id']='foreign'
        path.write_text(json.dumps(payload))
    before=path.read_bytes()
    with pytest.raises(ValueError): resume(automatic,'new-manual')
    assert len(airflow.posts)==1 and path.read_bytes()==before
    with factory() as session:
        assert len(session.scalars(select(RunAction)).all())==1
        assert session.scalar(select(RunAction)).result_status!='canceled'
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count']==1
