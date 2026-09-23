"""Execute the actual DAG callback; only the backend HTTP boundary is replaced."""
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class GatkCallbackIdentityTest(unittest.TestCase):
    def test_failure_callback_carries_actual_dagrun_not_original_conf_id(self):
        ns = runpy.run_path(str(Path(__file__).parents[1] / 'bio_gatk.py'))
        dag_run = SimpleNamespace(run_id='replacement-dag', conf={
            'analysis_id': 'GATK_SYNTHETIC', 'attempt': 1, 'dag_run_id': 'original-dag'},
            get_task_instances=lambda: [SimpleNamespace(task_id='wait_step3_analysis', state='failed'),
                SimpleNamespace(task_id='release_leases', state='failed')])
        calls = []
        with patch.dict(ns['report_dag_failure'].__globals__, {
            '_backend_json': lambda *args, **kwargs: calls.append((args, kwargs))}):
            ns['report_dag_failure']({'dag_run': dag_run})
        self.assertEqual(calls, [(('/api/internal/gatk/runs/GATK_SYNTHETIC/dag-terminal',), {
            'method': 'POST', 'payload': {'attempt': 1, 'status': 'failed',
                'failed_task_ids': ['wait_step3_analysis'], 'dag_run_id': 'replacement-dag'}})])


if __name__ == '__main__':
    unittest.main()
