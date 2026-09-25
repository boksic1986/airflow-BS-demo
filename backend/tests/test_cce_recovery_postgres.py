"""Opt-in, disposable PostgreSQL acceptance of real recovery lock ordering.

Removing the AnalysisRun FOR UPDATE/refresh or releasing it before dispatch must
break these cases. pg_stat_activity proves contention actually occurred; no
sleep-based race lottery. Only the external Airflow peer is synthetic.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import importlib
import os
from queue import Queue
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

from app.models import AnalysisRun, RunAction, WgsStageExecution, PipelineStageExecution
from app.cce_recovery_budget import reserve_compute_recovery
from test_wgs_resume_stage import setup
from test_gatk_resume_stage import recovery
from test_cce_manual_monitor_reconnect import interrupted, NOW


@pytest.fixture(params=['wgs','gatk'])
def pg_case(request, monkeypatch):
    dsn = os.environ.get('CCE_SYNTHETIC_PG_DSN')
    if not dsn:
        pytest.skip('requires isolated disposable PostgreSQL, not a service database')
    url = make_url(dsn)
    assert (url.host, url.database, url.username)==('127.0.0.1','p02_synthetic','p02_synthetic')
    schema = 'p02_' + uuid4().hex
    admin = create_engine(dsn)
    with admin.begin() as connection:
        connection.execute(text('CREATE SCHEMA '+schema))
    engine = create_engine(dsn, connect_args={'options':f'-csearch_path={schema} -clock_timeout=5000 -cstatement_timeout=10000'})
    module = importlib.import_module('test_wgs_resume_stage' if request.param=='wgs' else 'test_gatk_resume_stage')
    # Reuse existing complete fixtures, replacing their SQLite connection only.
    monkeypatch.setattr(module,'create_engine',lambda *args,**kwargs:engine)
    fixture = request.getfixturevalue('setup' if request.param=='wgs' else 'recovery')
    factory = fixture[0]
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.execution_mode='cce'
        deadline=(NOW+timedelta(hours=1)).isoformat()
        run.params_json=dict(run.params_json,
            cce_recovery_policy=dict(version=1,attempt=1,enabled=True,original_deadline=deadline),
            cce_recovery_budget=dict(attempt=1,count=0,original_deadline=deadline))
        aid=run.analysis_id
    yield fixture, aid, admin, request.param
    engine.dispose()
    admin.dispose()  # The runner removes only its own ephemeral PG container/data.


def reserve(case, session):
    return reserve_compute_recovery(session=session,analysis_id=case[1],attempt=1,
        source_execution_id='synthetic-failed-monitor',source_master_uid='synthetic-master',now=NOW)


def manual(case, session, key):
    fixture, aid, _, pipeline=case
    module=importlib.import_module('app.wgs_resume_service' if pipeline=='wgs' else 'app.gatk_runtime_service')
    fn=module.request_resume_stage if pipeline=='wgs' else module.request_gatk_resume_stage
    return fn(session=session,settings=fixture[1],airflow_client=fixture[2],analysis_id=aid,
        attempt=1,stage='step3_monitor',idempotency_key=key,requested_by='synthetic-operator')


def contender(case, pid_queue, operation):
    with case[0][0]() as session:
        pid_queue.put(session.scalar(text('SELECT pg_backend_pid()')))
        result=operation(session)
        session.commit()
        return result


def assert_blocked(case, pid_queue):
    pid=pid_queue.get(timeout=5)
    deadline=monotonic()+3
    while monotonic()<deadline:
        with case[2].connect() as connection:
            waiting=connection.scalar(text("SELECT wait_event_type FROM pg_stat_activity WHERE pid=:pid"),dict(pid=pid))
        if waiting=='Lock':
            return
        Event().wait(0.01)
    pytest.fail('contender never blocked on PostgreSQL row lock')


def test_simultaneous_automatic_reservations_share_one_slot(pg_case):
    factory=pg_case[0][0]
    with ThreadPoolExecutor(max_workers=1) as pool, factory() as first:
        expected=reserve(pg_case,first)
        pids=Queue()
        future=pool.submit(contender,pg_case,pids,lambda session:reserve(pg_case,session))
        try:
            assert_blocked(pg_case,pids)
        finally:
            first.commit()
        assert future.result(timeout=5)==expected
    with factory() as session:
        assert len(session.scalars(select(RunAction)).all())==1
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count']==1


def test_automatic_reservation_wins_before_manual_resume(pg_case):
    fixture=pg_case[0];factory=fixture[0];before=fixture[3].read_bytes()
    with ThreadPoolExecutor(max_workers=1) as pool, factory() as first:
        reserve(pg_case,first)
        pids=Queue()
        future=pool.submit(contender,pg_case,pids,lambda session:manual(pg_case,session,'manual'))
        try:
            assert_blocked(pg_case,pids)
        finally:
            first.commit()
        with pytest.raises(ValueError,match='pending automatic'):
            future.result(timeout=5)
    assert fixture[3].read_bytes()==before and not fixture[2].posts


@pytest.mark.parametrize('competitor',['manual','automatic'])
def test_manual_observer_handoff_serializes_dispatch_and_competing_recovery(pg_case,competitor):
    fixture,aid,_,pipeline=pg_case
    factory,_,airflow,_,_=fixture
    with factory() as session:
        prior=manual(pg_case,session,'prior')
    model=WgsStageExecution if pipeline=='wgs' else PipelineStageExecution
    interrupted((fixture,model,aid,None))
    entered,release=Event(),Event()
    original_post=airflow.trigger_dag_run
    def post(*args,**kwargs):
        entered.set()
        assert release.wait(5),'test did not release synthetic POST'
        return original_post(*args,**kwargs)
    airflow.trigger_dag_run=post
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(contender,pg_case,Queue(),lambda s:manual(pg_case,s,'successor'))
        assert entered.wait(5),'manual operation never reached POST'
        pids=Queue()
        operation=(lambda s:manual(pg_case,s,'another-click')) if competitor=='manual' else (lambda s:reserve(pg_case,s))
        second=pool.submit(contender,pg_case,pids,operation)
        try:
            assert_blocked(pg_case,pids)
        finally:
            release.set()
        result=first.result(timeout=5)
        if competitor=='manual':
            assert second.result(timeout=5)==result
        else:
            with pytest.raises(ValueError,match='active control'):
                second.result(timeout=5)
    with factory() as session:
        actions=session.scalars(select(RunAction).order_by(RunAction.id)).all()
        assert len(actions)==2 and actions[0].result_status=='canceled'
        assert actions[0].payload_json['monitor_handoff_to']==result['action_id']
        assert result['generation']==prior['generation']+1==3
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count']==0
    assert len(airflow.posts)==2  # Initial observer plus exactly one successor.


def test_committed_user_stop_wins_over_waiting_reservation(pg_case):
    factory=pg_case[0][0]
    with ThreadPoolExecutor(max_workers=1) as pool, factory() as first:
        run=first.scalar(select(AnalysisRun).with_for_update())
        run.status='pause_requested'
        pids=Queue()
        future=pool.submit(contender,pg_case,pids,lambda s:reserve(pg_case,s))
        try:
            assert_blocked(pg_case,pids)
        finally:
            first.commit()
        with pytest.raises(ValueError,match='stopped'):
            future.result(timeout=5)
    with factory() as session:
        assert session.scalar(select(RunAction)) is None
        assert session.scalar(select(AnalysisRun)).status=='pause_requested'
