"""Browser-independent, attempt-fenced Airflow state reconciliation."""
import logging
import threading
import time
from sqlalchemy import select
from app.models import AnalysisRun
from app.airflow_client import AirflowClient
from app.diagnostics_service import sync_wgs_airflow_status

ACTIVE = {'submitted', 'queued', 'running'}


class _SnapshotClient:
    def __init__(self, client, dag_id, dag_run_id, payload):
        self.client, self.identity, self.payload = client, (dag_id, dag_run_id), payload

    def get_dag_run(self, dag_id, dag_run_id):
        if (dag_id, dag_run_id) != self.identity:
            raise ValueError('Airflow snapshot identity changed')
        return self.payload

    def __getattr__(self, name):
        return getattr(self.client, name)


def sync_active_airflow_once(*, session_factory, airflow_client, settings):
    result = {'synced': 0, 'errors': 0}
    with session_factory() as session:
        targets = session.execute(select(AnalysisRun.analysis_id, AnalysisRun.attempt,
            AnalysisRun.dag_id, AnalysisRun.dag_run_id).where(
            AnalysisRun.pipeline_name == 'wgs', AnalysisRun.status.in_(ACTIVE),
            AnalysisRun.dag_run_id.is_not(None))).all()
    for analysis_id, attempt, dag_id, dag_run_id in targets:
        try:
            payload = airflow_client.get_dag_run(dag_id, dag_run_id)
            if payload.get('state') not in {'queued', 'running', 'success', 'failed'}:
                raise ValueError('Airflow returned no authoritative execution state')
            with session_factory() as session:
                run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id).with_for_update())
                if run is None or (run.attempt, run.dag_run_id) != (attempt, dag_run_id) or run.status not in ACTIVE:
                    continue
                sync_wgs_airflow_status(session=session, analysis_id=analysis_id, settings=settings,
                    airflow_client=_SnapshotClient(airflow_client, dag_id, dag_run_id, payload))
                result['synced'] += 1
        except Exception as error:
            # Rollback through context manager; connectivity is monitoring failure, not workflow failure.
            result['errors'] += 1
            logging.getLogger(__name__).warning('Airflow observer sync deferred for %s attempt %s (%s)',
                                               analysis_id, attempt, type(error).__name__)
    return result


def start_airflow_sync(*, session_factory, settings):
    stop = threading.Event()
    def loop():
        client = AirflowClient(base_url=settings.airflow_base_url, username=settings.airflow_api_username,
                               password=settings.airflow_api_password, timeout=5.0)
        while not stop.is_set():
            started = time.monotonic()
            try:
                sync_active_airflow_once(session_factory=session_factory, airflow_client=client, settings=settings)
            except Exception as error:
                logging.getLogger(__name__).warning('Airflow observer cycle deferred (%s)', type(error).__name__)
            stop.wait(max(1.0, 10.0 - (time.monotonic() - started)))
    threading.Thread(target=loop, name='airflow-state-sync', daemon=True).start()
    return stop
