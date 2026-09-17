"""Monitor-only graph must never dispatch native work or fail business state."""
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class NativeMonitorTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module('bio_wgs_native_monitor')
        self.conf = dict(pipeline='wgs', monitor_only=True,
            analysis_id='WGS_20260915_010203_A1B2C3', attempt=1,
            execution_id='wse_' + 'a' * 24, generation=2)
        self.context = {'dag_run': SimpleNamespace(conf=self.conf)}

    def test_graph_only_observes_and_native_result_is_not_terminal(self):
        dag = self.module.dag
        self.assertEqual(dag.task_ids, ['observe_native_execution'])
        self.assertIsNone(dag.on_failure_callback)
        task = dag.get_task('observe_native_execution')
        self.assertEqual(task.mode, 'reschedule')
        response = {**self.conf, 'status': 'running', 'done': False,
                    'observation': 'native_result_reported', 'monitoring_health': 'healthy'}
        calls = []
        def backend(path, **kwargs):
            calls.append((path, kwargs))
            return response
        with patch.dict('os.environ', {'WGS_ONPREM_MONITOR_ENABLED': 'true'}), \
             patch.object(self.module, '_backend_json', side_effect=backend):
            self.assertFalse(task.python_callable(**self.context))
        self.assertEqual(calls, [(f"/api/internal/wgs/onprem/runs/{self.conf['analysis_id']}/executions/{self.conf['execution_id']}/observe",
                                 {'method': 'POST', 'payload': {'attempt': 1, 'generation': 2}})])

    def test_stale_response_is_rejected_and_disabled_monitor_makes_no_request(self):
        from airflow.exceptions import AirflowFailException
        with patch.dict('os.environ', {'WGS_ONPREM_MONITOR_ENABLED': 'false'}), \
             patch.object(self.module, '_backend_json', side_effect=AssertionError('disabled called API')):
            with self.assertRaises(AirflowFailException):
                self.module.observe(**self.context)
        with patch.dict('os.environ', {'WGS_ONPREM_MONITOR_ENABLED': 'true'}), \
             patch.object(self.module, '_backend_json', return_value={**self.conf, 'generation': 1,
                                                                   'done': True, 'status': 'success'}):
            with self.assertRaises(AirflowFailException):
                self.module.observe(**self.context)


if __name__ == '__main__':
    unittest.main()
