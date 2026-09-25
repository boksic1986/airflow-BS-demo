"""A lost Step4 reply must not spend compute budget or create another execution."""
from copy import deepcopy
from datetime import timedelta
import importlib

import pytest
from sqlalchemy import select
from app.models import AnalysisRun, RunAction, WgsStageExecution, PipelineStageExecution
from test_cce_recovery_budget import run_store, NOW


@pytest.fixture
def publish_store(run_store):
    with run_store.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.current_stage='step4_publish';run.status='publishing';run.dag_run_id='original-dag'
        model=WgsStageExecution if run.pipeline_name=='wgs' else PipelineStageExecution
        fields=dict(analysis_id=run.analysis_id,attempt=1,stage_code='step4_publish',generation=1,
            execution_id='original-publish',request_hash='a'*64,release_id='frozen-release',status='accepted')
        if model is PipelineStageExecution:fields['pipeline_name']=run.pipeline_name
        session.add(model(**fields))
    return run_store


def invoke(factory, method, *, seconds=0, **kw):
    module=importlib.import_module('app.cce_publish_recovery')
    with factory.begin() as session:
        return getattr(module,method)(session=session,analysis_id='SYNTHETIC_RECOVERY',attempt=1,
            dag_run_id='original-dag',execution_id='original-publish',now=NOW+timedelta(seconds=seconds),**kw)


def begin(factory):
    return invoke(factory,'begin_publish_dispatch',deadline=NOW+timedelta(seconds=600))


def poll(factory, seconds=0, observation=None):
    return invoke(factory,'poll_publish_dispatch',seconds=seconds,observation=observation)


def reply(answer, status='not_started'):
    return dict(answer['probe'],schema_version='cce.publish-observation.v1',status=status)


def returned(factory, sequence=0, seconds=0):
    return invoke(factory,'finish_publish_dispatch',seconds=seconds,sequence=sequence)


def test_two_redispatches_keep_original_operation_and_deadline(publish_store):
    factory=publish_store
    with factory() as session:compute=deepcopy(session.scalar(select(AnalysisRun)).params_json)
    first=begin(factory)
    assert first['dispatch'] is True and first['sequence']==0
    assert begin(factory)['dispatch'] is False
    returned(factory)
    answer=poll(factory)
    waiting=poll(factory,observation=reply(answer))
    assert waiting['status']=='waiting' and waiting['next_retry_at']==(NOW+timedelta(seconds=60)).isoformat()
    assert poll(factory,59,reply(waiting))['status']=='waiting'
    ready=poll(factory,60)
    refreshed=poll(factory,60,reply(ready))
    assert refreshed['dispatch'] is False  # Pre-delay observation cannot authorize send.
    second=poll(factory,60,reply(refreshed))
    assert second['dispatch'] is True and second['sequence']==1
    assert second['execution_id']==first['execution_id']=='original-publish'
    assert poll(factory,61,reply(refreshed))['dispatch'] is False  # Duplicate consumed proof.
    returned(factory,1,61)
    fresh=poll(factory,61)
    waiting=poll(factory,61,reply(fresh))
    assert waiting['next_retry_at']==(NOW+timedelta(seconds=241)).isoformat()
    ready=poll(factory,241)
    refreshed=poll(factory,241,reply(ready))
    assert refreshed['dispatch'] is False
    third=poll(factory,241,reply(refreshed))
    assert third['dispatch'] is True and third['sequence']==2
    returned(factory,2,242)
    ready=poll(factory,242)
    assert poll(factory,242,reply(ready))['status']=='exhausted'
    with factory() as session:
        actions=session.scalars(select(RunAction)).all()
        assert len(actions)==1 and actions[0].payload_json['deadline']==first['deadline']
        assert session.scalar(select(AnalysisRun)).params_json==compute


@pytest.mark.parametrize('state',['running','success','failed','uncertain'])
def test_original_outcome_is_observed_not_redispatched(publish_store,state):
    begin(publish_store)
    returned(publish_store)
    fresh=poll(publish_store)
    answer=poll(publish_store,observation=reply(fresh,state))
    assert answer['status']==state and answer['dispatch'] is False
    with publish_store() as session:
        assert session.scalar(select(RunAction)).payload_json['sequence']==0


@pytest.mark.parametrize('fault',['in_flight','stop','expired','wrong_hash','stale_nonce','new_generation'])
def test_uncertainty_or_control_fence_prevents_redispatch(publish_store,fault):
    factory=publish_store
    begin(factory)
    if fault!='in_flight':returned(factory)
    fresh=poll(factory)
    observation=reply(fresh)
    if fault=='wrong_hash':observation['request_hash']='f'*64
    elif fault=='stale_nonce':observation['nonce']='f'*32
    elif fault in {'stop','new_generation'}:
        with factory.begin() as session:
            run=session.scalar(select(AnalysisRun))
            if fault=='stop':run.status='pause_requested'
            else:
                model=WgsStageExecution if run.pipeline_name=='wgs' else PipelineStageExecution
                session.scalar(select(model)).generation=2
    if fault in {'wrong_hash','stale_nonce','new_generation'}:
        with pytest.raises(ValueError):poll(factory,1,observation)
    else:
        answer=poll(factory,600 if fault=='expired' else 1,observation)
        assert answer['dispatch'] is False and answer['status'] in {'uncertain','stopped','expired'}
    with factory() as session:assert session.scalar(select(RunAction)).payload_json['sequence']==0


def test_confirmed_started_operation_never_returns_to_not_started(publish_store):
    begin(publish_store);returned(publish_store)
    first=poll(publish_store)
    started=poll(publish_store,observation=reply(first,'running'))
    answer=poll(publish_store,70,reply(started,'not_started'))
    assert answer['status']=='uncertain' and answer['next_retry_at'] is None


def test_success_is_not_rewritten_by_later_poll_deadline(publish_store):
    begin(publish_store);returned(publish_store)
    first=poll(publish_store)
    poll(publish_store,observation=reply(first,'success'))
    assert poll(publish_store,601)['status']=='success'
