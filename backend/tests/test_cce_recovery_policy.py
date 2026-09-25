"""New attempts opt in once; original monitor deadline never slides on resume."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import importlib

import pytest

NOW = datetime(2026,9,25,tzinfo=timezone.utc)


@pytest.mark.parametrize('pipeline,seconds',[('wgs',432000),('gatk',259200)])
def test_new_attempt_freezes_own_adapter_policy_and_first_monitor_deadline(pipeline,seconds):
    module=importlib.import_module('app.cce_recovery_policy')
    settings=SimpleNamespace(wgs_contract_v2_enabled=True,wgs_cce_recovery_enabled=pipeline=='wgs',
        gatk_cce_recovery_enabled=pipeline=='gatk',
        wgs_stage_contract_path=str(Path(__file__).parents[2]/'config/wgs_stage_contract.yaml'))
    run=SimpleNamespace(pipeline_name=pipeline,execution_mode='cce',attempt=1,params_json={})
    module.freeze_new_attempt(run=run,settings=settings)
    assert run.params_json['cce_recovery_policy']['enabled'] is True
    assert run.params_json['cce_recovery_budget']['count']==0
    assert run.params_json['cce_recovery_budget']['original_deadline'] is None
    deadline=module.start_monitor_deadline(run=run,now=NOW)
    assert deadline==(NOW+timedelta(seconds=seconds)).isoformat()
    run.params_json['cce_recovery_budget']['count']=1
    assert module.start_monitor_deadline(run=run,now=NOW+timedelta(hours=1))==deadline
    assert run.params_json['cce_recovery_budget']['count']==1
    run.attempt=2  # Legacy manual Resume is not a fresh automatic quota.
    with pytest.raises(ValueError):module.start_monitor_deadline(run=run,now=NOW)


def test_default_off_and_missing_historical_policy_never_backfills():
    module=importlib.import_module('app.cce_recovery_policy')
    run=SimpleNamespace(pipeline_name='wgs',execution_mode='cce',attempt=1,params_json={})
    assert module.start_monitor_deadline(run=run,now=NOW) is None
    assert run.params_json=={}
    module.freeze_new_attempt(run=run,settings=SimpleNamespace())
    assert run.params_json['cce_recovery_policy']['enabled'] is False
    assert module.start_monitor_deadline(run=run,now=NOW) is None
    with pytest.raises(ValueError):module.freeze_new_attempt(run=run,settings=SimpleNamespace())


def test_first_wgs_registration_and_replay_keep_same_hash_deadline_and_generation():
    from sqlalchemy import select
    from app.models import AnalysisRun,WgsStageExecution
    from app.wgs_stage_catalog import load_wgs_stage_contract
    from app.wgs_stage_execution_service import register_stage_execution
    from app.cce_recovery_policy import freeze_new_attempt
    from test_wgs_stage_execution import sessions,add_run,contract_path
    factory=sessions();add_run(factory)
    contract=load_wgs_stage_contract(contract_path())
    with factory.begin() as session:
        run=session.scalar(select(AnalysisRun));run.execution_mode='cce'
        freeze_new_attempt(run=run,settings=SimpleNamespace(wgs_cce_recovery_enabled=True,
            wgs_contract_v2_enabled=True,wgs_stage_contract_path=str(contract_path())))
        session.add(WgsStageExecution(analysis_id=run.analysis_id,attempt=1,
            stage_code='step2_master',execution_id='synthetic-submit',generation=1,
            status='success',request_hash='a'*64,receipt_hash='b'*64,release_id='synthetic'))
    with factory.begin() as session:
        run=session.scalar(select(AnalysisRun));request={'synthetic':True}
        first=register_stage_execution(session=session,run=run,contract=contract,
            stage_code='step3_monitor',request_payload=request,now=NOW)
        identity=first.execution_id;deadline=request['cce_recovery_deadline']
    with factory.begin() as session:
        run=session.scalar(select(AnalysisRun));request={'synthetic':True}
        replay=register_stage_execution(session=session,run=run,contract=contract,
            stage_code='step3_monitor',request_payload=request,now=NOW+timedelta(hours=1))
        assert replay.execution_id==identity and replay.generation==1
        assert request['cce_recovery_deadline']==deadline
        assert run.params_json['cce_recovery_budget']['count']==0
        run.attempt=2  # Legacy manual path: keep old journal, do not grant new quota.
        session.add(WgsStageExecution(analysis_id=run.analysis_id,attempt=2,
            stage_code='step2_master',execution_id='synthetic-submit-2',generation=1,
            status='success',request_hash='c'*64,receipt_hash='d'*64,release_id='synthetic'))
    with factory.begin() as session:
        run=session.scalar(select(AnalysisRun));request={'synthetic':True}
        register_stage_execution(session=session,run=run,contract=contract,
            stage_code='step3_monitor',request_payload=request,now=NOW+timedelta(hours=2))
        assert 'cce_recovery_deadline' not in request
        assert run.params_json['cce_recovery_policy']['attempt']==1
        assert run.params_json['cce_recovery_policy']['original_deadline']==deadline


def test_real_wgs_creation_freezes_policy_and_does_not_reset_on_duplicate_input(tmp_path):
    from sqlalchemy import select
    from app.models import AnalysisRun
    from app.wgs_platform_service import create_wgs_platform_run
    from test_wgs_stage_execution import sessions,contract_path
    factory=sessions()
    settings=SimpleNamespace(wgs_release_catalog_path=str(Path(__file__).parents[2]/'config/wgs_releases.yaml'),
        host_results_root=str(tmp_path/'runs'),container_shared_root=str(tmp_path),
        wgs_cce_recovery_enabled=True,wgs_contract_v2_enabled=True,wgs_stage_contract_path=str(contract_path()))
    args=dict(settings=settings,project_name='synthetic',execution_mode='cce',batch_no='SYNTHETIC',
        fq_path='/synthetic/fastq',submitted_by='operator',validate_input=False)
    with factory() as session:
        first=create_wgs_platform_run(session=session,**args)
        run=session.scalar(select(AnalysisRun));params=dict(run.params_json)
        assert params['cce_recovery_policy']['enabled'] is True
        params['cce_recovery_budget']=dict(params['cce_recovery_budget'],count=1)
        run.params_json=params;session.commit()
        second=create_wgs_platform_run(session=session,**args)
        assert second['analysis_id']==first['analysis_id']
        assert second['params']['cce_recovery_budget']['count']==1


def test_real_gatk_monitor_registration_persists_deadline_and_replay(tmp_path):
    import json
    from sqlalchemy import select
    from app.models import AnalysisRun,PipelineStageExecution
    from app.cce_recovery_policy import freeze_new_attempt
    from app.gatk_runtime_service import register_gatk_stage,_request_path
    from test_wgs_stage_execution import sessions
    factory=sessions()
    settings=SimpleNamespace(gatk_cce_recovery_enabled=True,
        gatk_runtime_node200_root='/synthetic/runtime',gatk_runtime_request_root=str(tmp_path/'requests'))
    with factory.begin() as session:
        run=AnalysisRun(analysis_id='GATK_SYNTHETIC',pipeline_name='gatk',dag_id='bio_gatk',
            attempt=1,execution_mode='cce',workdir='/synthetic',status='running',params_json={})
        freeze_new_attempt(run=run,settings=settings);session.add(run)
        session.add(PipelineStageExecution(analysis_id=run.analysis_id,pipeline_name='gatk',attempt=1,
            stage_code='step2_master',execution_id='synthetic-submit',generation=1,
            status='success',request_hash='a'*64,receipt_hash='b'*64,release_id='synthetic'))
    with factory() as session:
        args=dict(session=session,settings=settings,analysis_id='GATK_SYNTHETIC',attempt=1,stage='step3_monitor')
        first=register_gatk_stage(**args)
        path=_request_path(settings,'GATK_SYNTHETIC',1,'step3_monitor');raw=path.read_bytes()
        assert register_gatk_stage(**args)==first and path.read_bytes()==raw
        run=session.scalar(select(AnalysisRun))
        assert json.loads(raw)['cce_recovery_deadline']==run.params_json['cce_recovery_policy']['original_deadline']
        assert run.params_json['cce_recovery_budget']['count']==0
