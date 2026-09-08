from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.dashboard_service import ACTIVE_STATUSES
from app.models import (
    AnalysisRun,
    Base,
    RuleState,
    RunStageState,
    Sample,
    TransferFileState,
    TransferJob,
)
from app.pipeline_registry_service import _project_wgs_workflows
from app.wgs_sample_projection import _matrix_row
from app.wgs_stage_contract import project_wgs_orchestration
from app.wgs_timing_service import serialize_rule_states
from app.wgs_transfer_projection import transfer_file_order_by


def _sessions():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _run(*, analysis_id: str = "WGS_T229", status: str = "running", current_stage: str = "step5_download") -> AnalysisRun:
    return AnalysisRun(
        analysis_id=analysis_id,
        pipeline_name="wgs",
        dag_id="bio_wgs",
        execution_mode="cce",
        status=status,
        attempt=1,
        workdir=f"/runs/{analysis_id}",
        current_stage=current_stage,
        params_json={"pipeline_release_id": "wgs-4.1.1-test"},
    )


def _stage(code: str, status: str) -> RunStageState:
    number = int(code[4])
    return RunStageState(
        analysis_id="WGS_T229",
        attempt=1,
        stage_code=code,
        step_number=number,
        stage_label=code,
        stage_status=status,
        progress_available=False,
        progress_source="test",
    )


def test_step2_is_reconciled_when_later_stage_has_started() -> None:
    projected = project_wgs_orchestration(
        run_status="downloading",
        current_stage="step5_download",
        stage_rows=[
            _stage("step2_master", "failed"),
            _stage("step3_monitor", "success"),
            _stage("step5_download", "running"),
        ],
    )

    assert projected[1]["status"] == "success"
    assert projected[4]["status"] == "running"


def test_wgs_workflow_projector_returns_runtime_stage_rows() -> None:
    sessions = _sessions()
    with sessions() as session:
        run = _run()
        session.add_all([run, _stage("step5_download", "running")])
        session.commit()

        payload = _project_wgs_workflows(session=session, runs=[run])

    assert payload[run.analysis_id][4]["status"] == "running"


def test_transfer_files_are_ordered_running_then_accepted_then_success() -> None:
    sessions = _sessions()
    with sessions() as session:
        run = _run()
        transfer = TransferJob(
            transfer_id="WGS_T229-a1-result",
            analysis_id=run.analysis_id,
            attempt=1,
            direction="download",
            status="running",
        )
        session.add_all([run, transfer])
        for index, status in enumerate(("success", "accepted", "running"), start=1):
            session.add(
                TransferFileState(
                    transfer_id=transfer.transfer_id,
                    analysis_id=run.analysis_id,
                    attempt=1,
                    file_key=f"file-{index}",
                    display_name=f"file-{index}",
                    status=status,
                )
            )
        session.commit()

        rows = list(
            session.scalars(
                select(TransferFileState).order_by(*transfer_file_order_by())
            ).all()
        )

    assert [row.status for row in rows] == ["running", "accepted", "success"]


def test_publishing_and_downloading_are_active_dashboard_states() -> None:
    assert {"publishing", "downloading"} <= ACTIVE_STATUSES


def test_successful_workflow_reconciles_sample_and_rule_terminal_state() -> None:
    finished_at = datetime(2026, 9, 8, 2, 0, tzinfo=timezone.utc)
    sessions = _sessions()
    with sessions() as session:
        run = _run(status="success", current_stage="final")
        run.pipeline_finished_at = finished_at
        sample = Sample(
            analysis_id=run.analysis_id,
            sample_id="S1",
            status="running",
        )
        rule = RuleState(
            analysis_id=run.analysis_id,
            attempt=1,
            rule_instance_id="S1:late",
            rule_name="late_rule",
            sample_id="S1",
            status="queued",
            started_at=datetime(2026, 9, 8, 1, 0, tzinfo=timezone.utc),
        )
        session.add_all([run, sample, rule])
        session.commit()

        sample_payload = _matrix_row(
            sample=sample,
            run=run,
            rules=[rule],
            expected_total=1,
            qc={},
        )
        rule_payload = serialize_rule_states(
            session=session,
            run=run,
            rows=[rule],
        )[0]

    assert sample_payload["status"] == "success"
    assert sample_payload["progress_percent"] == 100.0
    assert sample_payload["current_rule"] is None
    assert rule_payload["status"] == "success"
    assert rule_payload["ended_at"].startswith("2026-09-08T02:00:00")
