import unittest
from types import SimpleNamespace
from unittest.mock import patch

import bio_gatk
from airflow.exceptions import AirflowException, AirflowFailException


class GatkRecoveryDagTest(unittest.TestCase):
    def test_marked_stage_sensor_without_submit_xcom_requires_current_native_terminal(self):
        status = {
            'analysis_id': 'GATK_SYNTHETIC', 'attempt': 1,
            'stage': 'step1_upload', 'execution_id': 'current-g2',
            'generation': 2, 'request_hash': 'a' * 64,
            'ready': True, 'failed': False,
            'stage_execution': {'protocol': 'cce.stage-execution.v1'},
        }
        ref = {
            'protocol': 'cce.stage-execution.v1', 'pipeline': 'gatk',
            'analysis_id': status['analysis_id'], 'attempt': 1,
            'stage': 'step1_upload', 'execution_id': status['execution_id'],
            'stage_generation': status['generation'], 'request_hash': status['request_hash'],
            'registration_sha256': 'b' * 64,
        }
        snapshot = {
            'schema': 'cce.stage-execution.snapshot.v1', 'execution_ref': ref,
            'state': 'running', 'evidence_ref': None, 'runtime_identity': None,
            'compute_identity': None, 'observation_health': 'healthy',
        }
        context = {
            'dag_run': SimpleNamespace(conf={'analysis_id': status['analysis_id'], 'attempt': 1},
                                       run_id='current-dag'),
            'ti': SimpleNamespace(xcom_pull=lambda **_kw: None),
        }
        with patch.object(bio_gatk, '_backend_json', return_value=status), \
             patch.object(bio_gatk, '_native_observe_stage', return_value=snapshot) as observe:
            self.assertFalse(bio_gatk.stage_ready('step1_upload', **context))
            observe.assert_called_once_with(context['dag_run'].conf, 'step1_upload', status)
            snapshot['state'] = 'succeeded'
            self.assertTrue(bio_gatk.stage_ready('step1_upload', **context))
            snapshot['execution_ref'] = {**ref, 'execution_id': 'stale-g1'}
            with self.assertRaisesRegex(ValueError, 'identity'):
                bio_gatk.stage_ready('step1_upload', **context)
        with patch.object(bio_gatk, '_backend_json', return_value={
                'ready': True, 'failed': False}), \
             patch.object(bio_gatk, '_native_observe_stage',
                          side_effect=AssertionError('legacy stage observed')):
            self.assertTrue(bio_gatk.stage_ready('step1_upload', **context))

    def test_monitor_resume_skips_prepare_upload_and_sends_real_dag_identity(self):
        conf = dict(analysis_id='GATK_SYNTHETIC', attempt=1, resume_action_id='resume-mock',
            resume_stage='step3_monitor', dag_run_id='untrusted-conf',
            resume_stages=['step3_monitor','step4_publish','step5_download','step6_materialize'])
        context = {'dag_run':SimpleNamespace(conf=conf, run_id='actual-dag')}
        calls = []
        with patch.object(bio_gatk, '_backend_json', side_effect=lambda path, **kw: calls.append(kw) or {'generation':2}), \
                patch.object(bio_gatk.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')) as ssh:
            for stage in ('prepare','step1_upload','step2_master'):
                self.assertEqual(bio_gatk.run_stage(stage, **context)['status'], 'skipped')
                self.assertTrue(bio_gatk.stage_ready(stage, **context))
            self.assertTrue(bio_gatk.acquire_transfer_slot('input', **context))
            bio_gatk.release_stage('release_input_transfer_slot', **context)
            ssh.assert_not_called()
            self.assertEqual(calls, [])
            for stage in ('step3_monitor','acquire_result_transfer_slot','finalize_run'):
                bio_gatk.register_stage(stage, **context)
        for call in calls:
            self.assertEqual(call['payload']['dag_run_id'], 'actual-dag')
            self.assertEqual(call['payload']['resume_action_id'], 'resume-mock')

    def test_reused_marked_step6_finalizes_with_fresh_native_observation(self):
        ref = {
            'protocol': 'cce.stage-execution.v1', 'pipeline': 'gatk',
            'analysis_id': 'GATK_SYNTHETIC', 'attempt': 1,
            'stage': 'step6_materialize', 'execution_id': 'GATK_SYNTHETIC-a1-step6_materialize-g1',
            'stage_generation': 1, 'request_hash': 'a' * 64,
            'registration_sha256': 'b' * 64,
        }
        observation = {
            'schema': 'cce.stage-execution.snapshot.v1', 'execution_ref': ref,
            'state': 'succeeded', 'evidence_ref': 'c' * 64,
            'runtime_identity': None, 'compute_identity': None,
            'observation_health': 'healthy',
        }
        status = {
            'analysis_id': ref['analysis_id'], 'attempt': 1,
            'stage': ref['stage'], 'execution_id': ref['execution_id'],
            'generation': 1, 'request_hash': ref['request_hash'],
            'status': 'success', 'ready': True, 'failed': False,
            'stage_execution': {'protocol': ref['protocol']},
        }
        context = {'dag_run': SimpleNamespace(
            conf={'analysis_id': ref['analysis_id'], 'attempt': 1,
                  'resume_action_id': 'synthetic-resume',
                  'resume_stages': ['step3_monitor']},
            run_id='current-dag'),
            'ti': SimpleNamespace(xcom_pull=lambda **_kw: None),
        }
        calls = []
        def backend(path, **kwargs):
            calls.append((path, kwargs))
            return status if kwargs.get('method', 'GET') == 'GET' else {'status': 'success'}
        with patch.object(bio_gatk, '_backend_json', side_effect=backend), \
             patch.object(bio_gatk, '_native_observe_stage', return_value=observation) as observe, \
             patch.object(bio_gatk, '_native_dispatch_stage', side_effect=AssertionError('dispatched')):
            self.assertEqual(bio_gatk.release_stage('finalize_run', **context), {'status': 'success'})
        observe.assert_called_once()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][1]['payload']['worker_observation'], observation)
        self.assertEqual(calls[1][1]['payload']['dag_run_id'], 'current-dag')

    def test_marked_step6_without_native_success_cannot_finalize(self):
        status = {
            'analysis_id': 'GATK_SYNTHETIC', 'attempt': 1, 'stage': 'step6_materialize',
            'execution_id': 'GATK_SYNTHETIC-a1-step6_materialize-g1',
            'generation': 1, 'request_hash': 'a' * 64, 'ready': True,
            'stage_execution': {'protocol': 'cce.stage-execution.v1'},
        }
        ref = {
            'protocol': 'cce.stage-execution.v1', 'pipeline': 'gatk',
            'analysis_id': 'GATK_SYNTHETIC', 'attempt': 1,
            'stage': 'step6_materialize', 'execution_id': status['execution_id'],
            'stage_generation': 1, 'request_hash': status['request_hash'],
            'registration_sha256': 'b' * 64,
        }
        observation = {
            'schema': 'cce.stage-execution.snapshot.v1', 'execution_ref': ref,
            'state': 'unknown', 'evidence_ref': None, 'runtime_identity': None,
            'compute_identity': None, 'observation_health': 'degraded',
        }
        context = {'dag_run': SimpleNamespace(
            conf={'analysis_id': 'GATK_SYNTHETIC', 'attempt': 1}, run_id='current-dag'),
            'ti': SimpleNamespace(xcom_pull=lambda **_kw: None),
        }
        with patch.object(bio_gatk, '_backend_json', return_value=status) as backend, \
             patch.object(bio_gatk, '_native_observe_stage', return_value=observation):
            with self.assertRaises(AirflowException):
                bio_gatk.release_stage('finalize_run', **context)
        self.assertEqual(backend.call_count, 1)

    def test_step6_finalizer_rejects_old_native_xcom_and_preserves_legacy(self):
        status = {
            'analysis_id': 'GATK_SYNTHETIC', 'attempt': 1,
            'stage': 'step6_materialize', 'execution_id': 'current-g2',
            'generation': 2, 'request_hash': 'a' * 64, 'ready': True,
            'stage_execution': {'protocol': 'cce.stage-execution.v1'},
        }
        old_ref = {
            'protocol': 'cce.stage-execution.v1', 'pipeline': 'gatk',
            'analysis_id': 'GATK_SYNTHETIC', 'attempt': 1,
            'stage': 'step6_materialize', 'execution_id': 'old-g1',
            'stage_generation': 1, 'request_hash': 'b' * 64,
            'registration_sha256': 'c' * 64,
        }
        old_snapshot = {
            'schema': 'cce.stage-execution.snapshot.v1', 'execution_ref': old_ref,
            'state': 'accepted', 'evidence_ref': None,
            'runtime_identity': None, 'compute_identity': None,
            'observation_health': 'healthy',
        }
        context = {
            'dag_run': SimpleNamespace(conf={'analysis_id': 'GATK_SYNTHETIC', 'attempt': 1},
                                       run_id='current-dag'),
            'ti': SimpleNamespace(xcom_pull=lambda **_kw: old_snapshot),
        }
        with patch.object(bio_gatk, '_backend_json', return_value=status) as backend, \
             patch.object(bio_gatk, '_native_observe_stage', side_effect=AssertionError('observed')):
            with self.assertRaisesRegex(ValueError, 'identity'):
                bio_gatk.release_stage('finalize_run', **context)
        self.assertEqual(backend.call_count, 1)

        context['ti'] = SimpleNamespace(xcom_pull=lambda **_kw: {
            'status': 'accepted', 'runner_status': 'accepted',
        })
        calls = []
        def backend_legacy(_path, **kwargs):
            calls.append(kwargs)
            return {'status': 'success'} if kwargs.get('method') == 'POST' else {
                'ready': True, 'status': 'success',
            }
        with patch.object(bio_gatk, '_backend_json', side_effect=backend_legacy), \
             patch.object(bio_gatk, '_native_observe_stage', side_effect=AssertionError('observed')):
            self.assertEqual(bio_gatk.release_stage('finalize_run', **context), {'status': 'success'})
        self.assertEqual(len(calls), 2)
        self.assertNotIn('worker_observation', calls[1]['payload'])
        malformed = {'schema': 'cce.stage-execution.snapshot.v0', 'execution_ref': old_ref}
        context['ti'] = SimpleNamespace(xcom_pull=lambda **_kw: malformed)
        with patch.object(bio_gatk, '_backend_json', return_value=status) as backend, \
             patch.object(bio_gatk, '_native_observe_stage', side_effect=AssertionError('observed')):
            with self.assertRaises(AirflowFailException):
                bio_gatk.release_stage('finalize_run', **context)
        self.assertEqual(backend.call_count, 1)


if __name__ == '__main__': unittest.main()
