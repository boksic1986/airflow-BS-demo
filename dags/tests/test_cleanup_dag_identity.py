"""Run actual DAG cleanup functions against a recording HTTP boundary."""
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class CleanupDagIdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dags = {name: runpy.run_path(str(Path(__file__).parents[1] / f'bio_{name}.py'))
                    for name in ('wgs', 'gatk')}

    def context(self):
        return {'dag_run': SimpleNamespace(run_id='replacement-dag', conf={
            'analysis_id': 'SYNTHETIC_CLEANUP', 'attempt': 1,
            'dag_run_id': 'original-dag', 'resume_action_id': 'manual-current',
            'resume_stages': ['step1_upload', 'step3_monitor', 'step5_download']})}

    def test_directional_release_sends_actual_dagrun(self):
        for pipeline, ns in self.dags.items():
            for stage in ('release_input_transfer_slot', 'release_result_transfer_slot', 'release_leases'):
                with self.subTest(pipeline=pipeline, stage=stage):
                    calls = []
                    def backend(path, **kwargs):
                        calls.append((path, kwargs['payload']))
                        return {'released': True}
                    fn = ns['register_stage']
                    with patch.dict(fn.__globals__, {'_backend_json': backend, '_runtime_enabled': lambda: True}):
                        fn(stage, **self.context())
                    self.assertEqual(calls[0][0], f'/api/internal/{pipeline}/runs/SYNTHETIC_CLEANUP/stages/{stage}')
                    self.assertEqual(calls[0][1].get('dag_run_id'), 'replacement-dag')

    def test_final_release_and_step3_drain_send_current_identity(self):
        ns = self.dags['wgs']
        for function, args in [('release_leases', ()), ('stage_ready', ('step3_monitor',))]:
            with self.subTest(function=function):
                calls = []
                def backend(path, **kwargs):
                    calls.append((path, kwargs['payload']))
                    return {'released': True, 'lifecycle_status': 'draining'}
                fn = ns[function]
                with patch.dict(fn.__globals__, {'_backend_json': backend,
                        '_runtime_enabled': lambda: True, '_stage_query_json': lambda path: {'ready': True}}):
                    fn(*args, **self.context())
                self.assertTrue(calls[-1][0].endswith('/observer/deactivate'))
                for path, payload in calls:
                    self.assertEqual(payload.get('dag_run_id'), 'replacement-dag', path)
                    self.assertEqual(payload.get('resume_action_id'), 'manual-current', path)

    def test_rejected_or_retained_lease_never_continues_to_observer_drain(self):
        fn = self.dags['wgs']['release_leases']
        for rejected in (True, False):
            with self.subTest(rejected=rejected):
                calls = []
                def backend(path, **kwargs):
                    calls.append(path)
                    if rejected:
                        raise RuntimeError('superseded_dag_run')
                    return {'released': False, 'retained': True, 'reason': 'transfer_not_terminal'}
                with patch.dict(fn.__globals__, {'_backend_json': backend, '_runtime_enabled': lambda: True}):
                    with self.assertRaises(RuntimeError):
                        fn(**self.context())
                self.assertEqual(calls, ['/api/internal/wgs/runs/SYNTHETIC_CLEANUP/stages/release_leases'])


if __name__ == '__main__':
    unittest.main()
