"""Late Airflow callbacks must not close a reserved or replacement execution."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, RuleState, RunAction, Sample
from app.wgs_submission_service import mark_submission_dag_failed
from app.gatk_runtime_service import mark_gatk_dag_failed


@pytest.fixture(params=['wgs', 'gatk'])
def store(request):
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    pipeline = request.param
    with factory.begin() as session:
        session.add(AnalysisRun(analysis_id='SYNTHETIC_CALLBACK', pipeline_name=pipeline,
            dag_id='bio_' + pipeline, dag_run_id='original', execution_mode='cce',
            attempt=1, status='running', current_stage='step3_monitor', progress_percent=25,
            workdir='/synthetic/project', params_json={}))
        session.add(Sample(analysis_id='SYNTHETIC_CALLBACK', sample_id='SYN001', status='running'))
        session.add(RuleState(analysis_id='SYNTHETIC_CALLBACK', attempt=1,
            rule_instance_id='rule-1', rule_name='synthetic_rule', status='running'))
    yield factory, pipeline
    engine.dispose()


def notify(session, pipeline, **kwargs):
    method = mark_submission_dag_failed if pipeline == 'wgs' else mark_gatk_dag_failed
    return method(session=session, analysis_id='SYNTHETIC_CALLBACK', attempt=1,
        failed_task_ids=['wait_step3_analysis'], **kwargs)


def add_recovery(store, status, payload):
    with store[0].begin() as session:
        session.add(RunAction(analysis_id='SYNTHETIC_CALLBACK', action='cce_compute_recovery',
            result_status=status, payload_json=payload))


def assert_preserved(session):
    run = session.scalar(select(AnalysisRun))
    assert run.status == 'running' and run.progress_percent == 25
    assert run.ended_at is None and run.pipeline_finished_at is None
    assert run.error_summary is None
    assert session.scalar(select(Sample)).status == 'running'
    rule = session.scalar(select(RuleState))
    assert rule.status == 'running' and rule.ended_at is None
    assert session.scalar(select(RunAction).where(RunAction.action == 'airflow_dag_failed')) is None


@pytest.mark.parametrize('state,payload', [
    ('reserved', {'attempt': 1}), ('queued', {'attempt': 1}),
    ('uncertain', {'attempt': 1}), ('reserved', {'attempt': '1'}),
])
def test_pending_action_preserves_run_samples_rules_and_failure_history(store, state, payload):
    add_recovery(store, state, payload)
    with store[0]() as session:
        # Older callbacks can lack DagRun identity; neither adapter may mutate.
        result = notify(session, store[1])
        assert result.get('ignored') is True
        assert_preserved(session)
        action = session.scalar(select(RunAction))
        assert (action.result_status, action.payload_json) == (state, payload)


def test_superseded_dag_is_ignored_even_after_recovery_action_finishes(store):
    add_recovery(store, 'success', {'attempt': 1, 'dag_run_id': 'replacement'})
    with store[0].begin() as session:
        session.scalar(select(AnalysisRun)).dag_run_id = 'replacement'
    with store[0]() as session:
        assert notify(session, store[1], dag_run_id='original').get('ignored') is True
        assert_preserved(session)
        assert notify(session, store[1]).get('ignored') is True
        assert_preserved(session)


def test_bound_current_recovery_callback_is_not_hidden(store):
    add_recovery(store, 'queued', {'attempt': 1, 'dag_run_id': 'replacement'})
    with store[0].begin() as session:
        session.scalar(select(AnalysisRun)).dag_run_id = 'replacement'
    with store[0]() as session:
        result = notify(session, store[1], dag_run_id='replacement')
        assert not result.get('ignored') and result['status'] == 'failed'
        assert session.scalar(select(AnalysisRun)).ended_at is not None
        if store[1] == 'gatk':
            assert session.scalar(select(Sample)).status == 'failed'
            assert session.scalar(select(RuleState)).status == 'canceled'


def test_reserved_target_does_not_authorize_failure_projection(store):
    add_recovery(store, 'reserved', {'attempt': 1, 'dag_run_id': 'original'})
    with store[0]() as session:
        assert notify(session, store[1], dag_run_id='original').get('ignored') is True
        assert_preserved(session)


def test_legacy_callback_without_recovery_retains_terminal_behavior(store):
    with store[0]() as session:
        assert notify(session, store[1])['status'] == 'failed'


def test_old_attempt_action_does_not_block_current_legacy_callback(store):
    add_recovery(store, 'queued', {'attempt': 2})
    with store[0]() as session:
        assert notify(session, store[1])['status'] == 'failed'


def test_locked_run_refresh_prevents_stale_session_overwrite(store):
    with store[0]() as stale:
        held = stale.scalar(select(AnalysisRun))
        assert held.dag_run_id == 'original'
        with store[0].begin() as fresh:
            fresh.scalar(select(AnalysisRun)).dag_run_id = 'replacement'
        assert notify(stale, store[1], dag_run_id='original').get('ignored') is True
        assert held.dag_run_id == 'replacement'
        assert_preserved(stale)


@pytest.mark.parametrize('store', ['gatk'], indirect=True)
def test_gatk_endpoint_forwards_dag_identity_to_real_service(store, monkeypatch):
    from app import main
    monkeypatch.setattr(main, 'get_sessionmaker', lambda: store[0])
    request = main.GatkDagTerminalRequest(attempt=1, status='failed',
        failed_task_ids=['wait_step3_analysis'], dag_run_id='superseded')
    result = main.internal_gatk_dag_terminal('SYNTHETIC_CALLBACK', request)
    assert result.get('ignored') is True
    with store[0]() as session:
        assert_preserved(session)


@pytest.mark.parametrize('store', ['wgs'], indirect=True)
def test_new_dag_failure_is_not_deduplicated_against_old_dag_end_time(store):
    old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    add_recovery(store, 'queued', {'attempt': 1, 'dag_run_id': 'replacement'})
    with store[0].begin() as session:
        session.scalar(select(AnalysisRun)).dag_run_id = 'replacement'
        session.add(RunAction(analysis_id='SYNTHETIC_CALLBACK', action='airflow_dag_failed',
            result_status='failed', created_at=old_time, payload_json={
                'attempt': 1, 'dag_run_id': 'original', 'failed_task_ids': ['wait_step3_analysis']}))
    with store[0]() as session:
        notify(session, 'wgs', dag_run_id='replacement')
        ended_at = session.scalar(select(AnalysisRun)).ended_at
        assert ended_at.replace(tzinfo=timezone.utc) > old_time
        # Replay still deduplicates the same new DagRun, without altering history.
        notify(session, 'wgs', dag_run_id='replacement')
        rows = session.scalars(select(RunAction).where(
            RunAction.action == 'airflow_dag_failed').order_by(RunAction.id)).all()
        assert [row.payload_json['dag_run_id'] for row in rows] == ['original', 'replacement']
        assert session.scalar(select(AnalysisRun)).ended_at == ended_at
