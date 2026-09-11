"""Recovery must not treat previous-attempt approvals as current approval."""
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import wgs_platform_service as service
from app.models import AnalysisRun, Base


def test_recovery_resets_staged_approvals():
    for action in ('resume', 'rerun_failed'):
        for mode in ('three_stage', 'legacy'):
            engine = create_engine('sqlite:///:memory:')
            Base.metadata.create_all(engine)
            with Session(engine) as session:
                run = AnalysisRun(analysis_id='mock-recovery', pipeline_name='wgs',
                                  dag_id='bio_wgs', status='failed', workdir='/synthetic',
                                  attempt=2, execution_mode='cce', params_json={
                                      'submission_mode': mode, 'submission_phase': 'failed',
                                      'project_name': 'Synthetic', 'batch_no': 'mock-batch',
                                      'config_approved_at': 'old-approval',
                                      'execution_approved_at': 'old-approval',
                                      'use_reference': 'all', 'resource_set': 'default',
                                  })
                session.add(run)
                session.commit()
                with patch.object(service, '_refresh_recovery_release', return_value={}), \
                     patch.object(service, 'submit_wgs_run', return_value={}):
                    service.action_wgs_run(session=session, settings=SimpleNamespace(),
                                           airflow_client=None, analysis_id=run.analysis_id,
                                           action=action, requested_by='test')
                session.refresh(run)
                assert run.attempt == 3
                assert run.params_json['use_reference'] == 'all'
                assert run.params_json['resource_set'] == 'default'
                if mode == 'three_stage':
                    assert run.params_json['config_approved_at'] is None
                    assert run.params_json['execution_approved_at'] is None
                    assert run.params_json['submission_phase'] == 'preparing_sampleinfo'
                else:
                    assert run.params_json['config_approved_at'] == 'old-approval'


if __name__ == '__main__':
    test_recovery_resets_staged_approvals()
    print('PASS: resume/rerun staged reset, legacy preserved, parameters preserved')
