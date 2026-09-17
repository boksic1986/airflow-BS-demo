"""The monitor DAG is not the analysis controller."""
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.diagnostics_service import sync_airflow_status, sync_wgs_airflow_status
from app.models import AnalysisRun
from test_wgs_onprem_registration import context


@pytest.mark.parametrize('sync', [sync_wgs_airflow_status, sync_airflow_status])
def test_monitor_dag_state_cannot_replace_native_analysis_state(context, sync):
    client, factory, settings, data = context
    registered = client.post('/api/wgs/onprem/projects', json=data).json()
    airflow = SimpleNamespace(get_dag_run=lambda *args: pytest.fail('Monitor state is not analysis evidence'))
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        run.dag_id, run.dag_run_id, run.status = 'bio_wgs_native_monitor', 'native__SYN', 'running'
        session.commit()
        result = sync(session=session, airflow_client=airflow, settings=settings,
                      analysis_id=registered['analysis_id'])
        assert run.status == result['status'] == 'running'
