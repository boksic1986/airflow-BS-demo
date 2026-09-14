import pytest
from sqlalchemy import select
from test_gatk_runtime_service import ANALYSIS_ID, _sessions, _run, _execution
from app.models import AnalysisRun, RunStageState
from app.gatk_workspace_service import build_gatk_workspace
from app.gatk_runtime_service import record_gatk_transfer_wait, _upsert_gatk_stage_state
from datetime import datetime, timezone


@pytest.mark.parametrize('kind,stage,label',[('input','step1_upload','等待上传'),('result','step5_download','等待下载')])
def test_wait_projects_correct_stage_without_complete_progress(kind,stage,label):
    sessions=_sessions()
    with sessions() as s:
        run=_run();s.add(run);s.commit()
        record_gatk_transfer_wait(session=s,analysis_id=ANALYSIS_ID,attempt=1,kind=kind,acquired=False)
        p=build_gatk_workspace(session=s,run=run,run_payload={})['progress']
        assert p['stage_label']==label
        assert p['stage_status']=='queued'
        assert not p['progress_available']
        assert run.status=='running'
        assert p['stage_code']==stage
        _upsert_gatk_stage_state(s,analysis_id=ANALYSIS_ID,attempt=1,stage_code=stage,stage_status='running',updated_at=datetime.now(timezone.utc),progress_available=False,progress_percent=None,completed_units=None,total_units=None,unit=None,progress_source='gatk-runtime')
        s.commit()
        assert build_gatk_workspace(session=s,run=run,run_payload={})['progress']['stage_label']!=label


def test_late_wait_does_not_overwrite_started_transfer():
    sessions=_sessions()
    with sessions() as s:
        run=_run();run.current_stage='step3_monitor'
        s.add_all([run,_execution('step1_upload',1,'success')]);s.commit()
        record_gatk_transfer_wait(session=s,analysis_id=ANALYSIS_ID,attempt=1,kind='input',acquired=False)
        assert run.current_stage=='step3_monitor'
