"""Synthetic maintenance control flow; no SSH or real cleanup."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bio_wgs_maintenance as m


def context():
    conf = {'analysis_id': 'WGS_20260922_010203_A1B2C3', 'attempt': 1,
        'maintenance_action_id': 'step7-sfs-123456abcdef', 'step7_generation': 2,
        'maintenance_mode': 'cleanup_step7'}
    return {'dag_run': SimpleNamespace(conf=conf, run_id='synthetic-maintenance')}


def test_independent_dag_has_no_analysis_or_transfer_tasks():
    assert m.dag.dag_id == 'bio_wgs_maintenance'
    assert m.dag.max_active_runs == 1
    assert set(m.dag.task_ids) == {'step7_cleanup', 'wait_step7_cleanup'}
    assert all(t.pool == 'default_pool' and t.retries == 0 for t in m.dag.tasks)


@pytest.mark.parametrize('state', ['running', 'success'])
def test_original_execution_reattaches_without_registration_or_launch(state):
    source = {'registered': True, 'action': 'step7-sfs-abcdef123456', 'generation': 1}
    with patch.object(m, 'registered_context', return_value=source), \
         patch.object(m, 'probe', return_value={'status': state}), \
         patch.object(m, 'report') as report, patch.object(m, 'remote') as remote, \
         patch.object(m, '_backend_json') as backend:
        result = m.start_cleanup(**context())
    assert result == {'action': source['action'], 'generation': 1}
    remote.assert_not_called()
    backend.assert_not_called()
    assert report.call_args.args[1] == state


def test_lost_launch_response_queries_and_does_not_relaunch_running_worker():
    with patch.object(m, 'registered_context', return_value={'registered': False}), \
         patch.object(m, 'probe', side_effect=[{'status': 'not_started'}, {'status': 'running'}]), \
         patch.object(m, 'remote', side_effect=ConnectionError) as remote, \
         patch.object(m, 'report'), patch.object(m, '_backend_json') as backend:
        result = m.start_cleanup(**context())
    assert result['generation'] == 2
    assert remote.call_count == 1
    assert backend.call_count == 1
    assert backend.call_args.kwargs['payload']['command'] == 'wgs-runtime WGS_20260922_010203_A1B2C3 1 step7_cleanup'


def test_probe_retry_budget_and_uncertainty():
    with patch.object(m, 'remote', side_effect=ConnectionError) as remote, \
         patch.object(m.time, 'sleep') as sleep:
        with pytest.raises(m.AirflowFailException, match='清理状态待确认'):
            m.probe(context())
    assert remote.call_count == 4
    assert [call.args[0] for call in sleep.call_args_list] == [30, 60, 120]


def test_identity_failure_is_not_retried():
    with patch.object(m, 'remote', side_effect=m.AirflowFailException('identity mismatch')) as remote:
        with pytest.raises(m.AirflowFailException):
            m.probe(context())
    assert remote.call_count == 1


def test_unknown_does_not_register_or_delete():
    with patch.object(m, 'registered_context', return_value={'registered': True, 'action': 'step7-sfs-abcdef123456', 'generation': 1}), \
         patch.object(m, 'probe', return_value={'status': 'unknown'}), \
         patch.object(m, 'remote') as remote, patch.object(m, '_backend_json') as backend:
        with pytest.raises(m.AirflowFailException):
            m.start_cleanup(**context())
    remote.assert_not_called()
    backend.assert_not_called()


def test_failed_current_operation_is_not_automatically_restarted():
    conf = context()['dag_run'].conf
    with patch.object(m, 'registered_context', return_value={'registered': True,
            'action': conf['maintenance_action_id'], 'generation': 2}), \
         patch.object(m, 'probe', return_value={'status': 'failed'}), \
         patch.object(m, 'remote') as remote:
        with pytest.raises(m.AirflowFailException):
            m.start_cleanup(**context())
    remote.assert_not_called()


def test_successful_poll_and_failure_callback_do_not_dispatch():
    ctx = context()
    ctx['ti'] = SimpleNamespace(xcom_pull=lambda **_: {'action': 'step7-sfs-abcdef123456', 'generation': 1})
    with patch.object(m, 'probe', return_value={'status': 'success'}), \
         patch.object(m, 'report', return_value={'status': 'success'}) as report, patch.object(m, 'remote') as remote:
        assert m.cleanup_ready(**ctx) is True
        m.mark_failed(ctx)
    assert [c.args[1] for c in report.call_args_list] == ['success', 'failed']
    remote.assert_not_called()
