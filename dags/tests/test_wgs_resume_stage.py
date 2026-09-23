"""Bounded real-Airflow contract, runnable with stdlib unittest."""
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0,str(Path(__file__).parents[1]))
import bio_wgs


class ResumeStageDagTest(unittest.TestCase):
    def test_recovery_registrations_send_actual_dag_identity(self):
        conf = {'analysis_id':'SYNTHETIC_RECOVERY', 'attempt':1,
                'resume_action_id':'resume-mock', 'dag_run_id':'untrusted-conf-id',
                'resume_stages':['step3_monitor','step4_publish','step5_download','step6_materialize']}
        calls = []
        with patch.object(bio_wgs, '_require_runtime_enabled'), patch.object(
                bio_wgs, '_backend_json', side_effect=lambda path, **kw: calls.append(kw['payload']) or {}):
            for stage in ('step3_monitor','step4_publish','acquire_result_transfer_slot','step5_download','step6_materialize','finalize_run'):
                bio_wgs.register_stage(stage, dag_run=SimpleNamespace(conf=conf, run_id='actual-recovery-dag'))
        self.assertEqual(len(calls), 6)
        for payload in calls:
            self.assertEqual(payload.get('dag_run_id'), 'actual-recovery-dag')
            self.assertEqual(payload['resume_action_id'], 'resume-mock')

    def test_recovery_skips_preparation_and_completed_stages(self):
        conf={'resume_stage':'step3_monitor','resume_action_id':'resume-mock',
              'resume_stages':['step3_monitor','step4_publish','step5_download','step6_materialize']}
        self.assertFalse(bio_wgs.stage_should_run('prepare_sampleinfo',conf))
        self.assertFalse(bio_wgs.stage_should_run('step1_upload',conf))
        self.assertFalse(bio_wgs.stage_should_run('step2_master',conf))
        self.assertTrue(bio_wgs.stage_should_run('step3_monitor',conf))
        self.assertTrue(bio_wgs.stage_should_run('finalize_run',conf))
        self.assertTrue(bio_wgs.submission_gate_ready('config',dag_run=SimpleNamespace(conf=conf)))

    def test_stage_sensor_retries_transport_only_with_gatk_delay_semantics(self):
        sensor=bio_wgs.dag.get_task('wait_step3_analysis')
        self.assertEqual(sensor.retries,6)
        self.assertEqual(sensor.retry_delay.total_seconds(),30)
        self.assertTrue(sensor.retry_exponential_backoff)
        self.assertEqual(sensor.max_retry_delay.total_seconds(),300)
        from airflow.exceptions import AirflowFailException
        for code in (408,429,500,502,503,504):
            with patch.object(bio_wgs,'urlopen',side_effect=HTTPError('http://mock',code,'mock',{},BytesIO(b'{}'))):
                with self.assertRaises(bio_wgs.BackendTransportUnavailable):
                    bio_wgs._stage_query_json('/mock')
        for code in (400,401,403,409):
            with patch.object(bio_wgs,'urlopen',side_effect=HTTPError('http://mock',code,'mock',{},BytesIO(b'{}'))):
                with self.assertRaises(AirflowFailException): bio_wgs._stage_query_json('/mock')

if __name__=='__main__': unittest.main()
