from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.models import Base, AnalysisRun
from app.observer_airflow_sync import sync_active_airflow_once


@pytest.fixture
def factory():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as session:
        session.add(AnalysisRun(analysis_id='MOCK', pipeline_name='wgs', dag_id='bio_wgs', dag_run_id='MOCK-a3',
                                workdir='/mock', attempt=3, status='submitted'))
        session.commit()
    return factory


def test_airflow_sync_runs_without_browser(factory):
    client = SimpleNamespace(get_dag_run=lambda *_: {'state': 'running'})
    result = sync_active_airflow_once(session_factory=factory, airflow_client=client, settings=SimpleNamespace())
    assert result['synced'] == 1
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'running'


def test_network_error_does_not_fail_run(factory):
    def unavailable(*_): raise OSError('offline')
    result = sync_active_airflow_once(session_factory=factory, airflow_client=SimpleNamespace(get_dag_run=unavailable), settings=SimpleNamespace())
    assert result['errors'] == 1
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'submitted'


def test_old_attempt_response_is_discarded(factory):
    def response(*_):
        with factory() as session:
            run = session.scalar(select(AnalysisRun))
            run.attempt = 4
            run.dag_run_id = 'MOCK-a4'
            session.commit()
        return {'state': 'running'}
    result = sync_active_airflow_once(session_factory=factory, airflow_client=SimpleNamespace(get_dag_run=response), settings=SimpleNamespace())
    assert result['synced'] == 0
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'submitted'
