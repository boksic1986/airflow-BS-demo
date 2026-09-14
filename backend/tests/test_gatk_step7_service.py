import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Base, PipelineStageExecution
from app.gatk_step7_service import request_cleanup, register_cleanup, sync_cleanup


def write_status(path,payload):
    from app.gatk_runtime_service import _canonical_hash
    if payload.get('status') in {'success','failed','canceled'}:
        payload={**payload,'receipt_hash':_canonical_hash(payload)}
    path.write_text(json.dumps(payload))


class Airflow:
    def __init__(self):
        self.calls = []
    def get_dag_run(self, *args):
        return None
    def trigger_dag_run(self, dag_id, **kwargs):
        self.calls.append((dag_id, kwargs))
        return kwargs


@pytest.fixture
def setup(tmp_path):
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        aid = 'GATK_20260914_010203_A1B2C3'
        run = AnalysisRun(analysis_id=aid, pipeline_name='gatk', attempt=1,
            dag_id='bio_gatk', dag_run_id=aid+'-a1', status='success',
            execution_mode='cce', workdir='/results/batch', params_json={'batch':'0910A','project':'synthetic'})
        session.add(run)
        session.flush()
        for stage in ('step5_download', 'step6_materialize'):
            session.add(PipelineStageExecution(execution_id=aid+'-'+stage,
                pipeline_name='gatk', analysis_id=aid, attempt=1, stage_code=stage,
                generation=1, status='success', request_hash='a'*64,
                receipt_hash='b'*64, release_id='gatk@1'))
        session.commit()
        binding = tmp_path/'runs'/aid/'attempt-1'/'batch-binding.json'
        binding.parent.mkdir(parents=True)
        binding.write_text(json.dumps({'schema_version':'gatk-runtime.batch-binding.v1',
            'analysis_id':aid,'attempt':1,'run_id':aid+'-a1'}))
        bundle = binding.parent/'cce'
        bundle.mkdir()
        (bundle/'BATCH_RUNTIME.yaml').write_text(json.dumps({'identity':{'project':'synthetic','batch':'0910A','run_id':aid+'-a1'}}))
        for name in ('cleanup-job.yaml','Step7_cleanup_sfs.sh','cce_batch_runtime.py'):
            (bundle/name).write_text('# synthetic')
        prepare={'analysis_id':aid,'attempt':1,'project_name':'synthetic','batch':'0910A'}
        from app.gatk_runtime_service import _canonical_hash
        prepare['request_hash']=_canonical_hash(prepare)
        prepare_path=tmp_path/'requests'/aid/'attempt-1'/'prepare.request.json'
        prepare_path.parent.mkdir(parents=True)
        prepare_path.write_text(json.dumps(prepare))
        settings = SimpleNamespace(gatk_runtime_request_root=str(tmp_path/'requests'),
            gatk_runtime_node200_root='/runtime', gatk_execution_enabled=True)
        yield session, run, settings, Airflow()


def test_independent_cleanup_is_fenced_and_preserves_analysis(setup):
    session, run, settings, airflow = setup
    action = request_cleanup(session=session, settings=settings, airflow_client=airflow,
        analysis_id=run.analysis_id, batch_confirmation='0910A', requested_by='admin')
    assert airflow.calls[0][0] == 'bio_gatk_maintenance'
    payload = register_cleanup(session=session, settings=settings, analysis_id=run.analysis_id,
        attempt=1, action_id=action['action_id'])
    assert payload['generation'] == 1
    assert run.status == 'success'
    assert run.dag_id == 'bio_gatk'
    again = request_cleanup(session=session, settings=settings, airflow_client=airflow,
        analysis_id=run.analysis_id, batch_confirmation='0910A', requested_by='admin')
    assert again['action_id'] == action['action_id']
    assert len(airflow.calls) == 1


def test_cleanup_requires_latest_receipt_and_confirmation(setup):
    session, run, settings, airflow = setup
    with pytest.raises(ValueError, match='confirmation'):
        request_cleanup(session=session, settings=settings, airflow_client=airflow,
            analysis_id=run.analysis_id, batch_confirmation='', requested_by='admin')
    run.status = 'running'
    with pytest.raises(ValueError, match='run_not_successful'):
        request_cleanup(session=session, settings=settings, airflow_client=airflow,
            analysis_id=run.analysis_id, batch_confirmation='0910A', requested_by='admin')


def test_failed_maintenance_does_not_fail_analysis(setup):
    session, run, settings, airflow = setup
    action = request_cleanup(session=session, settings=settings, airflow_client=airflow,
        analysis_id=run.analysis_id, batch_confirmation='0910A', requested_by='admin')
    payload = register_cleanup(session=session, settings=settings, analysis_id=run.analysis_id,
        attempt=1, action_id=action['action_id'])
    from pathlib import Path
    path = Path(settings.gatk_runtime_request_root)/run.analysis_id/'attempt-1'/'step7_cleanup.request.status.json'
    write_status(path,{**payload,'status':'failed','message':'live worker'})
    result = sync_cleanup(session=session, settings=settings, analysis_id=run.analysis_id,
        attempt=1, action_id=action['action_id'])
    assert result['failed']
    assert run.status == 'success'


def test_active_transfer_blocks_cleanup(setup):
    from app.models import ObsTransferLease
    session, run, settings, airflow = setup
    session.add(ObsTransferLease(slot_name='download-1',analysis_id=run.analysis_id,attempt=1))
    session.commit()
    with pytest.raises(ValueError,match='transfer_lease_active'):
        request_cleanup(session=session,settings=settings,airflow_client=airflow,
            analysis_id=run.analysis_id,batch_confirmation='0910A',requested_by='admin')
    assert not airflow.calls


def test_old_success_cannot_hide_failed_new_generation(setup):
    session, run, settings, airflow = setup
    session.add(PipelineStageExecution(execution_id='new-step6',pipeline_name='gatk',
        analysis_id=run.analysis_id,attempt=1,stage_code='step6_materialize',generation=2,
        status='failed',request_hash='c'*64,release_id='gatk@1'))
    session.commit()
    with pytest.raises(ValueError,match='step6_materialize_not_verified'):
        request_cleanup(session=session,settings=settings,airflow_client=airflow,
            analysis_id=run.analysis_id,batch_confirmation='0910A',requested_by='admin')
    assert not airflow.calls


def test_generic_api_uses_registered_cleanup_and_admin_dependency(setup,monkeypatch):
    from contextlib import nullcontext
    from app import main
    from app.pipeline_registry_service import ADAPTERS
    session,run,settings,airflow=setup
    monkeypatch.setattr(main,'get_sessionmaker',lambda:lambda:nullcontext(session))
    monkeypatch.setattr(main,'get_settings',lambda:settings)
    monkeypatch.setattr(main,'get_airflow_client',lambda:airflow)
    monkeypatch.setattr(main,'audit',lambda **kwargs:None)
    class Registry:
        def require(self,pipeline):
            assert pipeline == 'gatk'
            return SimpleNamespace(adapter=ADAPTERS[pipeline])
    monkeypatch.setattr(main,'get_pipeline_registry',lambda settings:Registry())
    result=main.cleanup_step7(run.analysis_id,main.WgsStep7CleanupRequest(batch_confirmation='0910A'),
        SimpleNamespace(username='admin'))
    assert result['action_type'] == 'gatk_cleanup_step7_sfs'
    route=next(row for row in main.app.routes if getattr(row,'path',None) == '/api/runs/{analysis_id}/actions/cleanup-step7')
    assert any(row.call is main.admin_user for row in route.dependant.dependencies)


def test_wgs_adapter_keeps_existing_execution_gate(monkeypatch):
    from app.pipeline_registry_service import ADAPTERS
    from app.pipeline_registry import PipelineCleanupUnavailable
    monkeypatch.setenv('WGS_EXECUTION_ENABLED','false')
    monkeypatch.setenv('WGS_RUNTIME_ADAPTER_ENABLED','true')
    with pytest.raises(PipelineCleanupUnavailable) as error:
        ADAPTERS['wgs'].request_cleanup_step7(settings=None)
    assert error.value.code == 'WGS_RUNTIME_DISABLED'


def test_changed_bundle_after_approval_is_rejected(setup):
    from pathlib import Path
    session,run,settings,airflow=setup
    action=request_cleanup(session=session,settings=settings,airflow_client=airflow,
        analysis_id=run.analysis_id,batch_confirmation='0910A',requested_by='admin')
    script=Path(settings.gatk_runtime_request_root).parent/'runs'/run.analysis_id/'attempt-1'/'cce'/'Step7_cleanup_sfs.sh'
    script.write_text('# modified target')
    with pytest.raises(ValueError,match='frozen_cleanup_identity_changed'):
        register_cleanup(session=session,settings=settings,analysis_id=run.analysis_id,attempt=1,action_id=action['action_id'])


@pytest.mark.parametrize('runtime_state',['running',None])
def test_orchestration_failure_cannot_overwrite_unknown_or_running_worker(setup,runtime_state):
    from pathlib import Path
    from app.gatk_step7_service import mark_cleanup_failed
    session,run,settings,airflow=setup
    action=request_cleanup(session=session,settings=settings,airflow_client=airflow,
        analysis_id=run.analysis_id,batch_confirmation='0910A',requested_by='admin')
    payload=register_cleanup(session=session,settings=settings,analysis_id=run.analysis_id,attempt=1,action_id=action['action_id'])
    path=Path(settings.gatk_runtime_request_root)/run.analysis_id/'attempt-1'/'step7_cleanup.request.status.json'
    if runtime_state:
        path.write_text(json.dumps({**payload,'status':runtime_state}))
    mark_cleanup_failed(session=session,analysis_id=run.analysis_id,attempt=1,action_id=action['action_id'])
    from app.gatk_step7_service import capability
    assert capability(session=session,settings=settings,run=run)['retry_available'] is False
    with pytest.raises(ValueError,match='previous_cleanup_runtime_not_terminal'):
        request_cleanup(session=session,settings=settings,airflow_client=airflow,
            analysis_id=run.analysis_id,batch_confirmation='0910A',requested_by='admin',
            retry_failed=True,expected_action_id=action['action_id'])
    assert len(airflow.calls)==1


def test_retry_reconciles_late_success_without_new_generation(setup):
    from pathlib import Path
    from app.gatk_step7_service import mark_cleanup_failed
    session,run,settings,airflow=setup
    action=request_cleanup(session=session,settings=settings,airflow_client=airflow,
        analysis_id=run.analysis_id,batch_confirmation='0910A',requested_by='admin')
    payload=register_cleanup(session=session,settings=settings,analysis_id=run.analysis_id,attempt=1,action_id=action['action_id'])
    mark_cleanup_failed(session=session,analysis_id=run.analysis_id,attempt=1,action_id=action['action_id'])
    path=Path(settings.gatk_runtime_request_root)/run.analysis_id/'attempt-1'/'step7_cleanup.request.status.json'
    write_status(path,{**payload,'status':'success'})
    from app.gatk_step7_service import capability
    from app.models import WgsMaintenanceAction
    from sqlalchemy import select
    projected=capability(session=session,settings=settings,run=run)
    assert projected['latest_action']['status']=='success'
    assert session.scalar(select(WgsMaintenanceAction)).status=='failed'
    result=request_cleanup(session=session,settings=settings,airflow_client=airflow,
        analysis_id=run.analysis_id,batch_confirmation='0910A',requested_by='admin',
        retry_failed=True,expected_action_id=action['action_id'])
    assert result['status']=='success'
    assert result['action_id']==action['action_id']
    assert len(airflow.calls)==1


def test_sync_rejects_corrupt_terminal_receipt(setup):
    from pathlib import Path
    session,run,settings,airflow=setup
    action=request_cleanup(session=session,settings=settings,airflow_client=airflow,
        analysis_id=run.analysis_id,batch_confirmation='0910A',requested_by='admin')
    payload=register_cleanup(session=session,settings=settings,analysis_id=run.analysis_id,attempt=1,action_id=action['action_id'])
    path=Path(settings.gatk_runtime_request_root)/run.analysis_id/'attempt-1'/'step7_cleanup.request.status.json'
    path.write_text(json.dumps({**payload,'status':'success','receipt_hash':'a'*64}))
    with pytest.raises(ValueError,match='maintenance_sidecar_identity_mismatch'):
        sync_cleanup(session=session,settings=settings,analysis_id=run.analysis_id,attempt=1,action_id=action['action_id'])


def test_capability_fails_closed_for_bad_runtime_yaml(setup):
    from pathlib import Path
    from app.gatk_step7_service import capability
    session,run,settings,_=setup
    runtime=Path(settings.gatk_runtime_request_root).parent/'runs'/run.analysis_id/'attempt-1'/'cce'/'BATCH_RUNTIME.yaml'
    runtime.write_text('identity: [')
    assert capability(session=session,settings=settings,run=run)['available'] is False
