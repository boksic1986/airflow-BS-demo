"""Recovered orchestration must not leave the locked GATK samples failed."""
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, PipelineStageExecution, RunAction, Sample
from app.observer_airflow_sync import sync_active_airflow_once


@pytest.fixture
def factory(tmp_path):
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    registry = tmp_path / 'registry.json'
    registry.write_text(json.dumps({'version': 1, 'pipelines': {'gatk': {
        'display_name': 'GATK', 'dag_id': 'bio_gatk', 'adapter': 'gatk',
        'enabled': True, 'submit_enabled': False,
        'capabilities': [], 'execution_targets': ['cce'],
    }}}))
    sessions.observer_settings = SimpleNamespace(pipeline_registry_path=str(registry),
                                                deployed_pipelines=('gatk',))
    terminal = datetime(2026, 9, 14, 9, 23, tzinfo=timezone.utc)
    with sessions() as session:
        session.add(AnalysisRun(analysis_id='GATK_MOCK', pipeline_name='gatk',
            dag_id='bio_gatk', dag_run_id='GATK_MOCK-a1', attempt=1,
            workdir='/mock', status='failed', current_stage='step3_monitor',
            ended_at=terminal, pipeline_finished_at=terminal, error_summary='network failed'))
        session.add(Sample(analysis_id='GATK_MOCK', sample_id='SYNTHETIC', status='failed'))
        session.add(PipelineStageExecution(execution_id='GATK_MOCK-a1-step3-g1',
            pipeline_name='gatk', analysis_id='GATK_MOCK', attempt=1,
            stage_code='step3_monitor', generation=1, status='running',
            request_hash='a' * 64, release_id='mock-release'))
        session.commit()
    return sessions


def sync(factory, state='running', **payload):
    client = SimpleNamespace(get_dag_run=lambda *_: {
        'dag_id': 'bio_gatk', 'dag_run_id': 'GATK_MOCK-a1',
        'state': state, 'start_date': '2026-09-14T10:00:00Z', 'end_date': None,
        **payload,
    })
    return sync_active_airflow_once(session_factory=factory, airflow_client=client,
                                    settings=factory.observer_settings)


def test_current_running_dag_recovers_run_samples_and_failed_clock(factory):
    sync(factory)
    sync(factory)
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.status == 'running'
        assert run.pipeline_finished_at is None
        assert run.ended_at is None
        assert run.error_summary is None
        assert session.scalar(select(Sample)).status == 'running'
        assert len(session.scalars(select(RunAction)).all()) == 1


@pytest.mark.parametrize('runtime_status', ['failed', 'canceled'])
def test_failed_runtime_is_not_resurrected_by_airflow_clear(factory, runtime_status):
    with factory() as session:
        session.scalar(select(PipelineStageExecution)).status = runtime_status
        session.commit()
    sync(factory)
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'failed'
        assert session.scalar(select(Sample)).status == 'failed'


def test_new_generation_running_supersedes_failed_stage_generation(factory):
    with factory() as session:
        session.scalar(select(PipelineStageExecution)).status = 'failed'
        session.add(PipelineStageExecution(execution_id='GATK_MOCK-a1-step3-g2',
            pipeline_name='gatk', analysis_id='GATK_MOCK', attempt=1,
            stage_code='step3_monitor', generation=2, status='running',
            request_hash='b' * 64, release_id='mock-release'))
        session.commit()
    sync(factory)
    with factory() as session:
        assert session.scalar(select(Sample)).status == 'running'


def test_wrong_airflow_identity_cannot_recover_samples(factory):
    sync(factory, dag_run_id='GATK_MOCK-a0')
    with factory() as session:
        assert session.scalar(select(Sample)).status == 'failed'


def test_network_failure_does_not_recover_or_fail_samples(factory):
    def unavailable(*_):
        raise OSError('network unavailable')
    result = sync_active_airflow_once(session_factory=factory,
        airflow_client=SimpleNamespace(get_dag_run=unavailable), settings=factory.observer_settings)
    assert result['errors'] == 1
    with factory() as session:
        assert session.scalar(select(Sample)).status == 'failed'


def test_partial_rule_progress_or_dag_success_is_not_sample_success(factory):
    sync(factory, state='success')
    with factory() as session:
        assert session.scalar(select(Sample)).status == 'failed'


def test_completed_runtime_materialization_permits_dag_success(factory):
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        run.current_stage = 'step6_materialize'
        stage = session.scalar(select(PipelineStageExecution))
        stage.stage_code = 'step6_materialize'
        stage.status = 'success'
        session.commit()
    sync(factory, state='success', end_date='2026-09-14T12:00:00Z')
    with factory() as session:
        assert session.scalar(select(Sample)).status == 'success'
        assert session.scalar(select(AnalysisRun)).pipeline_finished_at.hour == 12


@pytest.mark.parametrize('runtime_status', ['failed', 'canceled', 'cancelled'])
def test_dag_success_does_not_hide_latest_failed_runtime(factory, runtime_status):
    with factory() as session:
        session.scalar(select(PipelineStageExecution)).status = runtime_status
        session.add(PipelineStageExecution(execution_id='GATK_MOCK-a1-step6-g1',
            pipeline_name='gatk', analysis_id='GATK_MOCK', attempt=1,
            stage_code='step6_materialize', generation=1, status='success',
            request_hash='b' * 64, receipt_hash='c' * 64, release_id='mock-release'))
        session.commit()
    sync(factory, state='success', end_date='2026-09-14T12:00:00Z')
    with factory() as session:
        assert session.scalar(select(Sample)).status == 'failed'
        assert session.scalar(select(AnalysisRun)).status == 'failed'


def test_new_stage_after_control_plane_failure_reopens_samples_and_clock(factory, tmp_path):
    from app.gatk_runtime_service import register_gatk_stage
    with factory() as session:
        stage = session.scalar(select(PipelineStageExecution))
        stage.status = 'success'
        stage.receipt_hash = 'd' * 64
        session.commit()
        register_gatk_stage(session=session, analysis_id='GATK_MOCK', attempt=1,
            stage='step4_publish', settings=SimpleNamespace(
                gatk_runtime_node200_root='/approved/mock',
                gatk_runtime_request_root=str(tmp_path)))
        assert session.scalar(select(Sample)).status == 'running'
        assert session.scalar(select(AnalysisRun)).pipeline_finished_at is None


def test_already_registered_stage_does_not_fake_recovery(factory, tmp_path):
    from app.gatk_runtime_service import register_gatk_stage
    with factory() as session:
        session.add(PipelineStageExecution(execution_id='GATK_MOCK-a1-step2-g1',
            pipeline_name='gatk', analysis_id='GATK_MOCK', attempt=1,
            stage_code='step2_master', generation=1, status='success',
            request_hash='b' * 64, receipt_hash='c' * 64, release_id='mock-release'))
        session.commit()
        register_gatk_stage(session=session, analysis_id='GATK_MOCK', attempt=1,
            stage='step3_monitor', settings=SimpleNamespace())
        assert session.scalar(select(Sample)).status == 'failed'
        assert session.scalar(select(AnalysisRun)).pipeline_finished_at is not None


def test_old_successful_predecessor_cannot_authorize_after_newer_failure(factory, tmp_path):
    from app.gatk_runtime_service import register_gatk_stage
    with factory() as session:
        stage = session.scalar(select(PipelineStageExecution))
        stage.status = 'success'
        stage.receipt_hash = 'd' * 64
        session.add(PipelineStageExecution(execution_id='GATK_MOCK-a1-step3-g2',
            pipeline_name='gatk', analysis_id='GATK_MOCK', attempt=1,
            stage_code='step3_monitor', generation=2, status='failed',
            request_hash='b' * 64, release_id='mock-release'))
        session.commit()
        with pytest.raises(ValueError, match='predecessor'):
            register_gatk_stage(session=session, analysis_id='GATK_MOCK', attempt=1,
                stage='step4_publish', settings=SimpleNamespace(
                    gatk_runtime_node200_root='/approved/mock',
                    gatk_runtime_request_root=str(tmp_path)))
        assert session.scalar(select(Sample)).status == 'failed'
