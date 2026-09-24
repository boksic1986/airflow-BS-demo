"""Reserved automatic action uses real adapter registration and shared dispatch.

Only Airflow is a synthetic HTTP peer. Native producer coverage lives in the
source/normal-receipt slice; these fixtures represent its authenticated DB rows.
"""
import importlib
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from app.models import AnalysisRun, RunAction, WgsStageExecution, PipelineStageExecution
from app.cce_recovery_service import reserve_monitored_recovery
from test_wgs_resume_stage import setup
from test_gatk_resume_stage import recovery
from test_cce_recovery_evidence import evidence, digest

NOW = datetime(2026, 9, 25, tzinfo=timezone.utc)


@pytest.fixture
def automatic(setup, recovery, evidence):
    context, candidate, terminal = evidence
    fixture = setup if context['pipeline'] == 'wgs' else recovery
    factory, settings, airflow, path, frozen = fixture
    pipeline = context['pipeline']
    model = WgsStageExecution if pipeline == 'wgs' else PipelineStageExecution
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.execution_mode = 'cce'
        deadline = (NOW + timedelta(hours=1)).isoformat()
        run.params_json = dict(run.params_json,
            cce_recovery_policy=dict(version=1,attempt=1,enabled=True,original_deadline=deadline),
            cce_recovery_budget=dict(attempt=1,count=0,original_deadline=deadline))
        source = session.scalar(select(model).where(model.stage_code == 'step2_master'))
        monitor = session.scalar(select(model).where(model.stage_code == 'step3_monitor'))
        platform = dict(pipeline=pipeline,analysis_id=run.analysis_id,attempt=1,stage='step2_master',
            execution_id=source.execution_id,generation=1,request_hash=source.request_hash)
        identity = dict(context, analysis_id=run.analysis_id,execution_id='native:analysis',
            generation=3,request_hash='d'*64)
        identity.pop('schema')
        candidate.update(identity); terminal.update(identity)
        terminal.update(plugin_failure_sha256=digest(candidate),submission_snapshot_sha256='e'*64)
        binding = dict(schema_version=2,platform_execution=platform,
            source_bundle='/frozen/source/cce',selected_bundle='/frozen/selected',
            native=dict(attempt=1,execution_generation=3,request_hash='d'*64,
                run_id=context['run_id'],namespace=context['namespace'],
                job_uid=context['master_job_uid'],pod_uid=context['master_pod_uid'],
                recovery_context=dict(pipeline=pipeline,analysis_id=run.analysis_id,execution_id='native')))
        source.terminal_payload_json = dict(cce_master_binding=binding)
        monitor.terminal_payload_json = dict(cce_master_submit_execution_id=source.execution_id,
            cce_master_binding=binding,cce_recovery_evidence=dict(schema_version=2,
                binding=binding,phase='analysis',candidate=candidate,terminal=terminal))
        aid, mid = run.analysis_id, monitor.execution_id
    with factory.begin() as session:
        data = reserve_monitored_recovery(session=session,analysis_id=aid,attempt=1,
            monitor_execution_id=mid,evidence_root=None,now=NOW)
    return fixture, model, aid, data


def dispatch(automatic, seconds):
    fixture, _, aid, action = automatic
    factory, settings, airflow, _, _ = fixture
    module = importlib.import_module('app.cce_compute_dispatch')
    with factory() as session:
        return module.dispatch_due_recovery(session=session,settings=settings,
            airflow_client=airflow,analysis_id=aid,attempt=1,action_id=action['action_id'],
            now=NOW+timedelta(seconds=seconds))


def test_due_action_keeps_single_budget_and_uses_existing_resume_generation(automatic):
    fixture, model, _, data = automatic
    factory, _, airflow, path, original = fixture
    before = path.read_bytes()
    assert dispatch(automatic,59)['status'] == 'waiting'
    assert path.read_bytes() == before and not airflow.posts
    first = dispatch(automatic,60)
    assert first['status'] == 'queued'
    assert dispatch(automatic,61) == first
    assert len(airflow.posts) == 1
    conf = airflow.posts[0][2]
    assert conf['resume_stage'] == 'step3_monitor'
    assert conf['resume_stages'] == ['step3_monitor','step4_publish','step5_download','step6_materialize']
    assert conf['resume_action_id'] == data['action_id']
    saved = json.loads(path.read_text())
    assert saved['generation'] == 2 and saved['attempt'] == 1
    assert saved['cce_recovery_deadline'] == (NOW+timedelta(hours=1)).isoformat()
    for key in ('control_workdir','expected_batch_root','wgs_source_commit',
                'runtime_workdir','cce_bundle','profile_id','profile_revision'):
        if key in original: assert saved[key] == original[key]
    from app.cce_resume_dispatch import authorize_recovery_stage
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.params_json['cce_recovery_budget']['count'] == 1
        actions = session.scalars(select(RunAction)).all()
        assert len(actions) == 1 and actions[0].action == 'cce_compute_recovery'
        assert len(session.scalars(select(model)).all()) == 3
        authorize_recovery_stage(session=session,run=run,action_id=data['action_id'],
            dag_run_id=run.dag_run_id,stage='step3_monitor')


def test_uncertain_post_is_get_only_even_after_deadline_and_stop(automatic):
    fixture, _, _, _ = automatic
    factory, _, airflow, _, _ = fixture
    original_post, original_get = airflow.trigger_dag_run, airflow.get_dag_run
    def post(*args, **kwargs):
        original_post(*args, **kwargs)
        raise httpx.ReadTimeout('lost POST reply')
    def get(*args, **kwargs):
        if airflow.posts: raise httpx.ReadTimeout('lost GET reply')
        return original_get(*args, **kwargs)
    airflow.trigger_dag_run, airflow.get_dag_run = post, get
    assert dispatch(automatic,60)['status'] == 'uncertain'
    with factory.begin() as session:
        session.scalar(select(AnalysisRun)).status = 'cancel_requested'
    airflow.get_dag_run = original_get
    assert dispatch(automatic,3601)['status'] == 'queued'
    assert len(airflow.posts) == 1
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'cancel_requested'


@pytest.mark.parametrize('change',['stop','deadline','changed_evidence','missing_policy'])
def test_dispatch_rechecks_fences_without_mutating_frozen_request(automatic,change):
    fixture, model, _, _ = automatic
    factory, _, airflow, path, _ = fixture
    before = path.read_bytes()
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        if change == 'stop': run.status = 'pause_requested'
        if change == 'missing_policy':
            params = dict(run.params_json);params.pop('cce_recovery_policy');run.params_json=params
        if change == 'changed_evidence':
            row = session.scalar(select(model).where(model.stage_code == 'step3_monitor'))
            row.terminal_payload_json = {}
    with pytest.raises(ValueError):dispatch(automatic,3601 if change=='deadline' else 60)
    assert not airflow.posts and path.read_bytes() == before
    with factory() as session:
        assert len(session.scalars(select(model)).all()) == 2


def test_prepared_crash_rechecks_original_proof_before_request_write(automatic,monkeypatch):
    fixture, model, _, _ = automatic
    factory, _, airflow, path, _ = fixture
    from app import wgs_resume_service, gatk_runtime_service
    owner, name = ((wgs_resume_service,'register_recovery_stage') if model is WgsStageExecution
        else (gatk_runtime_service,'register_gatk_stage'))
    real = getattr(owner,name)
    def crash(**kwargs): raise RuntimeError('synthetic death after durable preparation')
    monkeypatch.setattr(owner,name,crash)
    with pytest.raises(RuntimeError,match='synthetic death'): dispatch(automatic,60)
    before = path.read_bytes()
    with factory.begin() as session:
        action = session.scalar(select(RunAction))
        assert action.payload_json['dispatch_state'] == 'not_started'
        assert 'generation' not in action.payload_json
        row = session.scalar(select(model).where(model.stage_code == 'step3_monitor'))
        row.terminal_payload_json = {}
    monkeypatch.setattr(owner,name,real)
    with pytest.raises(ValueError): dispatch(automatic,61)
    assert path.read_bytes() == before and not airflow.posts
