import pytest
from sqlalchemy import select
from types import SimpleNamespace
from test_gatk_runtime_service import ANALYSIS_ID, _sessions, _run, _execution
from app.dashboard_service import get_dashboard_runs
from app.models import AnalysisRun, RunStageState
from app.gatk_workspace_service import build_gatk_workspace
from app.gatk_runtime_service import record_gatk_transfer_wait, _upsert_gatk_stage_state
from app.pipeline_registry_service import ADAPTERS
from datetime import datetime, timezone


def _tracker(session):
    return get_dashboard_runs(
        session=session,
        airflow_client=SimpleNamespace(list_task_instances=lambda *_: {'task_instances': []}),
        pipeline='gatk', status=None, keyword=None, limit=10, offset=0,
        deployed_pipelines=('gatk',), pipeline_adapters={'gatk': ADAPTERS['gatk']},
    )['items'][0]


@pytest.mark.parametrize('kind,stage,stored_label,display_label,direction',[
    ('input','step1_upload','等待上传','Uploading FASTQ','upload'),
    ('result','step5_download','等待下载','Downloading GATK results','download'),
])
def test_wait_projects_correct_stage_without_complete_progress(kind,stage,stored_label,display_label,direction):
    sessions=_sessions()
    with sessions() as s:
        run=_run();run.dag_run_id=f'{ANALYSIS_ID}-a1';s.add(run);s.commit()
        record_gatk_transfer_wait(session=s,analysis_id=ANALYSIS_ID,attempt=1,kind=kind,acquired=False)
        stored=s.scalar(select(RunStageState).where(RunStageState.stage_code==stage))
        assert (stored.stage_label,stored.stage_status,stored.progress_source)==(stored_label,'queued','gatk-transfer-slot')
        p=build_gatk_workspace(session=s,run=run,run_payload={})['progress']
        tracker=_tracker(s)
        assert (p['stage_label'],p['stage_status'],p['progress_available'],p['progress_percent'])==(display_label,'waiting',False,None)
        assert (tracker['current_stage_label'],tracker['stage_status'])==(display_label,'waiting')
        assert tracker['stage_progress']['available'] is False
        assert tracker['stage_progress']['percent'] is None
        assert p['current_step']==display_label
        assert p['current_item']==f'Waiting for OBS {direction} slot'
        assert tracker['stage_progress']['current_item']==p['current_item']
        assert next(x for x in p['orchestration_stages'] if x['stage_code']==stage)['stage_status']=='waiting'
        s.refresh(stored)
        assert (stored.stage_label,stored.stage_status,stored.progress_source)==(stored_label,'queued','gatk-transfer-slot')
        assert run.status=='running'
        assert p['stage_code']==stage
        record_gatk_transfer_wait(session=s,analysis_id=ANALYSIS_ID,attempt=1,kind=kind,acquired=True)
        assert build_gatk_workspace(session=s,run=run,run_payload={})['progress']['current_item']==f'Waiting for {direction} to start'
        _upsert_gatk_stage_state(s,analysis_id=ANALYSIS_ID,attempt=1,stage_code=stage,stage_status='running',updated_at=datetime.now(timezone.utc),progress_available=False,progress_percent=None,completed_units=None,total_units=None,unit=None,progress_source='gatk-runtime')
        s.commit()
        running=build_gatk_workspace(session=s,run=run,run_payload={})['progress']
        assert running['stage_label']!=display_label
        assert running['stage_status']=='running' and not running['progress_available']
        assert _tracker(s)['stage_status']=='running'


def test_late_wait_does_not_overwrite_started_transfer():
    sessions=_sessions()
    with sessions() as s:
        run=_run();run.current_stage='step3_monitor'
        s.add_all([run,_execution('step1_upload',1,'success')]);s.commit()
        record_gatk_transfer_wait(session=s,analysis_id=ANALYSIS_ID,attempt=1,kind='input',acquired=False)
        assert run.current_stage=='step3_monitor'


def test_wait_marker_does_not_mask_registered_or_terminal_execution():
    sessions=_sessions()
    with sessions() as s:
        run=_run();run.dag_run_id=f'{ANALYSIS_ID}-a1';s.add(run);s.commit()
        record_gatk_transfer_wait(session=s,analysis_id=ANALYSIS_ID,attempt=1,kind='input',acquired=False)
        s.add(_execution('step1_upload',1,'running'));s.commit()
        assert build_gatk_workspace(session=s,run=run,run_payload={})['progress']['stage_status']=='queued'
        assert _tracker(s)['stage_status']=='queued'
        run.status='failed';s.commit()
        assert build_gatk_workspace(session=s,run=run,run_payload={})['progress']['stage_status']=='queued'
        assert _tracker(s)['stage_status']=='queued'
