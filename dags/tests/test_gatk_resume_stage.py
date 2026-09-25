import unittest
from types import SimpleNamespace
from unittest.mock import patch

import bio_gatk


class GatkRecoveryDagTest(unittest.TestCase):
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


if __name__ == '__main__': unittest.main()
