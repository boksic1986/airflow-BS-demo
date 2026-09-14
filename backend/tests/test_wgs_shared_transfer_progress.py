from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Base, RunStageState, TransferJob
from app.wgs_timing_service import enrich_progress
from app.wgs_workspace_service import build_wgs_workspace


@pytest.mark.parametrize("stage,direction,kind", [
    ("step1_upload", "upload", "input_upload"),
    ("step5_download", "download", "result_download"),
])
@pytest.mark.parametrize("detailed", [True, False, None])
def test_tracker_and_detail_share_exact_transfer_snapshot(stage, direction, kind, detailed):
    engine = create_engine("sqlite+pysqlite://")
    Base.metadata.create_all(engine)
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)
    with Session(engine) as session:
        run = AnalysisRun(analysis_id="WGS_SYNTHETIC_PROGRESS", pipeline_name="wgs",
                          dag_id="bio_wgs", status="running", attempt=2,
                          current_stage=stage, workdir="/synthetic", params_json={})
        session.add(run)
        session.add(RunStageState(analysis_id=run.analysis_id, attempt=2,
            stage_code=stage, stage_label="Transfer", stage_status="running",
            progress_available=True, progress_percent=1, completed_units=100,
            total_units=10000, speed_bps=3, eta_seconds=999, unit="bytes",
            progress_source="old-stage-snapshot", updated_at=now))
        for suffix, attempt, transfer_direction, transfer_kind, newer in [
            ("correct", 2, direction, kind, 0),
            ("old-attempt", 1, direction, kind, 2),
            ("opposite", 2, "download" if direction == "upload" else "upload",
             "result_download" if direction == "upload" else "input_upload", 3),
        ]:
            if detailed is None and suffix == "correct":
                continue
            session.add(TransferJob(analysis_id=run.analysis_id, attempt=attempt,
                transfer_id=suffix, transfer_type=transfer_kind, direction=transfer_direction,
                status="running", bytes_transferred=147 if suffix == "correct" else 9000,
                bytes_total=10240, progress_percent=1, progress_detail_available=bool(detailed),
                speed_bps=10, eta_seconds=1010, heartbeat_at=now + timedelta(seconds=1),
                updated_at=now + timedelta(seconds=newer)))
        session.commit()
        tracker = enrich_progress(session=session, run=run, payload={})
        detail = build_wgs_workspace(session=session, run=run, run_payload={})["progress"]
        fields = ("progress_percent", "percent", "completed_units", "total_units",
                  "speed_bps", "eta_seconds", "stage_updated_at", "progress_available")
        assert {k: tracker[k] for k in fields} == {k: detail[k] for k in fields}
        assert tracker["progress_percent"] == (1.4 if detailed else None)
        assert tracker["completed_units"] == (147 if detailed else None)
        assert tracker["eta_seconds"] == (1010 if detailed else None)
        assert tracker["progress_available"] is bool(detailed)
