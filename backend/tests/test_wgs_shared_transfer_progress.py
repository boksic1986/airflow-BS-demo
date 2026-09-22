from datetime import datetime, timedelta, timezone

import pytest
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Base, RunStageState, TransferJob, WgsExecutionDispatch
from app.wgs_timing_service import enrich_progress
from app.wgs_workspace_service import build_wgs_workspace


@pytest.mark.parametrize("lease_state,start_state,run_status,transfer_status,waiting", [
    ("up_for_reschedule", None, "publishing", None, True),
    ("queued", None, "running", None, True),
    ("success", "queued", "running", None, True),
    (None, None, "running", None, False),
    ("failed", None, "running", None, False),
    ("unavailable", None, "running", None, False),
    ("success", "running", "running", None, False),
    ("up_for_reschedule", None, "failed", None, False),
    ("up_for_reschedule", None, "running", "running", False),
    ("up_for_reschedule", None, "running", "success", False),
    ("up_for_reschedule", None, "running", "failed", False),
])
def test_download_queue_requires_current_airflow_evidence(
    lease_state, start_state, run_status, transfer_status, waiting,
):
    tasks = [
        {"task_id": "result_transfer.acquire_obs_transfer_slot", "state": lease_state},
        {"task_id": "result_transfer.start_step5_download", "state": start_state},
    ]
    class Airflow:
        def list_task_instances(self, dag_id, dag_run_id):
            assert (dag_id, dag_run_id) == ("bio_wgs", "MOCK_DOWNLOAD-a2")
            if lease_state == "unavailable":
                raise httpx.ConnectError("synthetic unavailable")
            return {"task_instances": tasks}

    engine = create_engine("sqlite+pysqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = AnalysisRun(analysis_id="MOCK_DOWNLOAD", pipeline_name="wgs",
            dag_id="bio_wgs", dag_run_id="MOCK_DOWNLOAD-a2", status=run_status,
            attempt=2, current_stage="step4_publish", workdir="/synthetic")
        session.add(run)
        session.add(RunStageState(analysis_id=run.analysis_id, attempt=2,
            stage_code="step4_publish", stage_label="Publishing WGS results",
            stage_status="success", progress_available=True, progress_percent=100,
            progress_source="synthetic"))
        # Historical transfer must not hide a current-attempt wait.
        session.add(TransferJob(analysis_id=run.analysis_id, attempt=1,
            transfer_id="old-download", transfer_type="result_download",
            direction="download", status="success"))
        if transfer_status:
            session.add(TransferJob(analysis_id=run.analysis_id, attempt=2,
                transfer_id="current-download", transfer_type="result_download",
                direction="download", status=transfer_status))
        session.commit()
        tracker = enrich_progress(session=session, run=run, payload={"airflow_tasks": tasks})
        assert tracker["stage_code"] == ("step5_download" if waiting else "step4_publish")
        detail = build_wgs_workspace(session=session, run=run, run_payload={},
                                     airflow_client=Airflow())["progress"]
        for progress in (tracker, detail):
            assert progress["stage_code"] == ("step5_download" if waiting else "step4_publish")
            if waiting:
                assert progress["stage_status"] == "waiting"
                assert progress["stage_label"] == "Downloading WGS results"
                assert progress["progress_available"] is False
                assert progress["progress_percent"] is None
                assert progress["speed_bps"] is None
                assert progress["eta_seconds"] is None
                assert progress.get("estimated_progress_percent") is None
                assert progress["orchestration_stages"][4]["stage_status"] == "waiting"
        assert run.current_stage == "step4_publish"
        assert run.status == run_status
        assert not session.dirty


@pytest.mark.parametrize("approved,target,dispatch_state,run_status,waiting", [
    (True, "cce", "waiting_resource", "running", True),
    (False, "cce", "waiting_resource", "running", False),
    (True, "node-97", "waiting_resource", "running", False),
    (True, "cce", "committed", "running", False),
    (True, "cce", "waiting_resource", "failed", False),
])
def test_upload_queue_replaces_finished_preparation_without_changing_execution(
    approved, target, dispatch_state, run_status, waiting,
):
    engine = create_engine("sqlite+pysqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = AnalysisRun(analysis_id="WGS_QUEUE_SYNTH", pipeline_name="wgs",
            dag_id="bio_wgs", status=run_status, attempt=1, current_stage="prepare_analysis",
            workdir="/synthetic", params_json={"execution_approved_at": "2026-09-22T00:00:00Z" if approved else None})
        session.add(run)
        session.add(RunStageState(analysis_id=run.analysis_id, attempt=1,
            stage_code="prepare_analysis", stage_label="Preparing WGS analysis",
            stage_status="success", progress_available=False, progress_source="synthetic"))
        session.add(WgsExecutionDispatch(analysis_id=run.analysis_id, project_id="MOCK",
            batch="MOCK", desired_mode="cce" if target == "cce" else "local",
            desired_target=target, dispatch_state=dispatch_state))
        session.commit()
        tracker = enrich_progress(session=session, run=run, payload={})
        detail = build_wgs_workspace(session=session, run=run, run_payload={})["progress"]
        for progress in (tracker, detail):
            assert progress["stage_code"] == ("step1_upload" if waiting else "prepare_analysis")
            assert progress["stage_status"] == ("waiting" if waiting else "success")
            if waiting:
                assert progress["stage_label"] == "Uploading FASTQ"
                assert progress["step_number"] == 1
                assert progress["progress_available"] is False
                assert progress["progress_percent"] is None
                assert progress["speed_bps"] is None
                assert progress["eta_seconds"] is None
                assert progress["orchestration_stages"][0]["stage_status"] == "waiting"
        assert run.current_stage == "prepare_analysis"
        assert run.status == run_status
        assert not session.dirty


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
