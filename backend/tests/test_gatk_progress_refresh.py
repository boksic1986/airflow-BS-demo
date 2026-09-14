from datetime import datetime, timezone
import pytest
from test_gatk_runtime_service import ANALYSIS_ID, _sessions, _run
from app.gatk_runtime_service import _upsert_gatk_stage_state


@pytest.mark.parametrize('stage', ['step1_upload', 'step5_download'])
def test_status_only_refresh_keeps_measured_transfer_progress(stage):
    with _sessions()() as session:
        session.add(_run()); session.commit()
        args=dict(analysis_id=ANALYSIS_ID, attempt=1, stage_code=stage,
                  stage_status='running', updated_at=datetime.now(timezone.utc))
        row=_upsert_gatk_stage_state(session, **args, progress_available=True,
            progress_percent=63, completed_units=63, total_units=100, unit='bytes')
        session.flush()
        _upsert_gatk_stage_state(session, **args)
        assert row.progress_available
        assert (row.progress_percent,row.completed_units,row.total_units)==(63,63,100)
        _upsert_gatk_stage_state(session, **args, reopen_terminal=True)
        assert not row.progress_available
