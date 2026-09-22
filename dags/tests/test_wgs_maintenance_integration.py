"""One synthetic DAG run; never use the deployed metadata database."""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bio_wgs_maintenance as m


@pytest.mark.skipif(os.getenv('STEP7_ISOLATED_INTEGRATION') != '1', reason='explicit isolated Airflow metadata required')
def test_one_synthetic_cleanup_dag_run():
    from airflow.configuration import conf as airflow_conf
    assert airflow_conf.get('database', 'sql_alchemy_conn').startswith('sqlite:////')
    aid, action = 'WGS_20260922_010203_A1B2C3', 'step7-sfs-123456abcdef'
    state, observations, launches = {'status': 'not_started'}, [], []

    def backend(path, *, method='GET', payload=None):
        if '/context?' in path:
            return {'registered': False}
        if path.endswith('/observation'):
            observations.append(payload['status'])
            return {'status': payload['status']}
        return {'status': 'accepted'}

    def remote(context, verb, *args):
        if verb == 'wgs-step7-start':
            launches.append(verb)
            state['status'] = 'success'
        return dict(state)

    with patch.object(m, '_backend_json', side_effect=backend), patch.object(m, 'remote', side_effect=remote):
        run = m.dag.test(run_conf={'analysis_id': aid, 'attempt': 1,
            'maintenance_action_id': action, 'step7_generation': 1,
            'maintenance_mode': 'cleanup_step7'})
    assert run.state == 'success'
    assert launches == ['wgs-step7-start']
    assert observations == ['success', 'success']
