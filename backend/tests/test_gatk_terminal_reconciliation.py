import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import gatk_runtime_service
from app.models import (
    AnalysisRun,
    Base,
    PipelineStageExecution,
    RuleState,
    RunStageState,
    Sample,
)
from app.pipeline_registry_service import ADAPTERS


ANALYSIS_ID = "GATK_20260909_071908_F45CF7"


def _sessions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        gatk_runtime_request_root=str(tmp_path / "runtime" / "requests"),
        gatk_evidence_root=str(tmp_path / "evidence"),
        gatk_transfer_spool_root=str(tmp_path / "transfer-progress"),
    )


def test_terminal_sidecar_preserves_last_known_rule_progress(tmp_path: Path) -> None:
    sessions = _sessions()
    request_hash = "a" * 64
    execution_id = f"{ANALYSIS_ID}-a1-step3_monitor-g1"
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=ANALYSIS_ID,
                pipeline_name="gatk",
                dag_id="bio_gatk",
                status="running",
                current_stage="step3_monitor",
                progress_percent=98,
                attempt=1,
                workdir="/runtime/gatk/run",
                params_json={},
            )
        )
        session.add(
            PipelineStageExecution(
                execution_id=execution_id,
                pipeline_name="gatk",
                analysis_id=ANALYSIS_ID,
                attempt=1,
                stage_code="step3_monitor",
                generation=1,
                status="running",
                request_hash=request_hash,
                release_id="gatk-scmc-v7.6.0@bd04f6d",
            )
        )
        session.add(
            RunStageState(
                analysis_id=ANALYSIS_ID,
                attempt=1,
                stage_code="step3_monitor",
                stage_label="Run GATK analysis",
                stage_status="running",
                progress_available=True,
                progress_percent=98,
                completed_units=182,
                total_units=184,
                unit="rules",
                current_item="cloud_gatk_finalize",
                progress_source="gatk-runtime",
                updated_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

        request_path = (
            Path(_settings(tmp_path).gatk_runtime_request_root)
            / ANALYSIS_ID
            / "attempt-1"
            / "step3_monitor.request.json"
        )
        request_path.parent.mkdir(parents=True)
        request_path.with_suffix(".status.json").write_text(
            json.dumps(
                {
                    "analysis_id": ANALYSIS_ID,
                    "attempt": 1,
                    "stage": "step3_monitor",
                    "generation": 1,
                    "execution_id": execution_id,
                    "request_hash": request_hash,
                    "status": "failed",
                    "message": "Master Pod is in a fatal infrastructure state",
                }
            ),
            encoding="utf-8",
        )

        result = gatk_runtime_service.sync_gatk_stage_status(
            session=session,
            settings=_settings(tmp_path),
            analysis_id=ANALYSIS_ID,
            attempt=1,
            stage="step3_monitor",
        )
        stage = session.scalar(select(RunStageState))

    assert result["failed"] is True
    assert stage is not None
    assert stage.stage_status == "failed"
    assert stage.progress_available is True
    assert stage.progress_percent == 98
    assert stage.completed_units == 182
    assert stage.total_units == 184
    assert stage.current_item == "cloud_gatk_finalize"


def test_dag_failure_closes_rule_and_sample_projection_without_losing_progress() -> None:
    sessions = _sessions()
    timestamp = datetime(2026, 9, 9, 16, 44, tzinfo=timezone.utc)
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=ANALYSIS_ID,
                pipeline_name="gatk",
                dag_id="bio_gatk",
                dag_run_id=f"{ANALYSIS_ID}-a1",
                status="running",
                current_stage="step3_monitor",
                progress_percent=98,
                attempt=1,
                workdir="/runtime/gatk/run",
                params_json={},
            )
        )
        session.add_all(
            [
                Sample(analysis_id=ANALYSIS_ID, sample_id="SCMC001", status="running"),
                Sample(analysis_id=ANALYSIS_ID, sample_id="SCMC002", status="running"),
                RunStageState(
                    analysis_id=ANALYSIS_ID,
                    attempt=1,
                    stage_code="step3_monitor",
                    stage_label="Run GATK analysis",
                    stage_status="failed",
                    progress_available=True,
                    progress_percent=98,
                    completed_units=182,
                    total_units=184,
                    unit="rules",
                    current_item="cloud_gatk_finalize",
                    message="Master Pod is in a fatal infrastructure state",
                    progress_source="gatk-runtime",
                    ended_at=timestamp,
                    updated_at=timestamp,
                ),
                RuleState(
                    analysis_id=ANALYSIS_ID,
                    attempt=1,
                    rule_instance_id="cloud_gatk_finalize:183",
                    rule_name="cloud_gatk_finalize",
                    phase="Delivery",
                    status="running",
                ),
                RuleState(
                    analysis_id=ANALYSIS_ID,
                    attempt=1,
                    rule_instance_id="unstarted:184",
                    rule_name="cloud_gatk_all",
                    phase="Delivery",
                    status="planned",
                ),
            ]
        )
        session.commit()

        mark_failed = getattr(gatk_runtime_service, "mark_gatk_dag_failed", None)
        assert callable(mark_failed), "GATK needs a terminal DAG reconciliation service"
        result = mark_failed(
            session=session,
            analysis_id=ANALYSIS_ID,
            attempt=1,
            failed_task_ids=["wait_step3_analysis", "release_leases"],
            timestamp=timestamp,
        )
        run = session.scalar(select(AnalysisRun))
        rules = list(session.scalars(select(RuleState).order_by(RuleState.rule_name)).all())
        samples = list(session.scalars(select(Sample)).all())

    assert result["status"] == "failed"
    assert run is not None
    assert run.status == "failed"
    assert run.progress_percent == 98
    assert "cloud_gatk_finalize" in str(run.error_summary)
    assert {row.rule_name: row.status for row in rules} == {
        "cloud_gatk_all": "canceled",
        "cloud_gatk_finalize": "failed",
    }
    assert all(row.ended_at == timestamp for row in rules)
    assert {sample.status for sample in samples} == {"failed"}


def test_gatk_dashboard_projection_uses_terminal_stage_progress() -> None:
    sessions = _sessions()
    with sessions() as session:
        run = AnalysisRun(
            analysis_id=ANALYSIS_ID,
            pipeline_name="gatk",
            dag_id="bio_gatk",
            status="failed",
            current_stage="step3_monitor",
            progress_percent=10,
            attempt=1,
            workdir="/runtime/gatk/run",
            params_json={},
        )
        session.add(run)
        session.add(
            RunStageState(
                analysis_id=ANALYSIS_ID,
                attempt=1,
                stage_code="step3_monitor",
                stage_label="Run GATK analysis",
                stage_status="failed",
                progress_available=True,
                progress_percent=98,
                completed_units=182,
                total_units=184,
                unit="rules",
                current_item="cloud_gatk_finalize",
                progress_source="gatk-runtime",
                updated_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

        projector = ADAPTERS["gatk"].project_progress
        assert callable(projector), "GATK needs a stage-backed dashboard progress projector"
        projected = projector(session=session, run=run, payload={"progress_percent": 10})

    assert projected["progress_percent"] == 98
    assert projected["completed_units"] == 182
    assert projected["total_units"] == 184
    assert projected["current_item"] == "cloud_gatk_finalize"
    assert projected["stage_status"] == "failed"
