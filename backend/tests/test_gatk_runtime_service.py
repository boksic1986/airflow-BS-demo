from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.gatk_runtime_service import register_gatk_stage, sync_gatk_stage_status
from app.models import (
    AnalysisRun,
    Base,
    PipelineStageExecution,
    RunStageState,
)


ANALYSIS_ID = "GATK_20260908_120000_A1B2C3"


def _sessions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _settings(tmp_path: Path):
    return SimpleNamespace(
        gatk_runtime_request_root=str(tmp_path / "runtime" / "requests"),
        gatk_runtime_node200_root="/approved/gatk-runtime",
        gatk_transfer_spool_root=str(tmp_path / "runtime" / "transfer-progress"),
        gatk_evidence_root=str(tmp_path / "evidence"),
    )


def _run() -> AnalysisRun:
    return AnalysisRun(
        analysis_id=ANALYSIS_ID,
        pipeline_name="gatk",
        dag_id="bio_gatk",
        attempt=1,
        status="running",
        current_stage="step4_publish",
        workdir="/approved/gatk-runtime/run",
        params_json={
            "runtime_profile_id": "gatk-scmc-v7.6.0",
            "runtime_profile_revision": "bd04f6d",
        },
    )


def _execution(stage: str, generation: int, status: str) -> PipelineStageExecution:
    return PipelineStageExecution(
        execution_id=f"{ANALYSIS_ID}-a1-{stage}-g{generation}",
        pipeline_name="gatk",
        analysis_id=ANALYSIS_ID,
        attempt=1,
        stage_code=stage,
        generation=generation,
        status=status,
        request_hash=(str(generation) * 64)[:64],
        release_id="gatk-scmc-v7.6.0@bd04f6d",
        receipt_hash="a" * 64 if status == "success" else None,
    )


def test_failed_stage_projects_terminal_run_state(tmp_path: Path) -> None:
    sessions = _sessions()
    settings = _settings(tmp_path)
    request = (
        Path(settings.gatk_runtime_request_root)
        / ANALYSIS_ID
        / "attempt-1"
        / "step4_publish.request.json"
    )
    request.parent.mkdir(parents=True)
    execution = _execution("step4_publish", 1, "accepted")
    request.write_text(
        json.dumps(
            {
                "analysis_id": ANALYSIS_ID,
                "attempt": 1,
                "stage": "step4_publish",
                "generation": 1,
                "request_hash": execution.request_hash,
                "execution_id": execution.execution_id,
            }
        ),
        encoding="utf-8",
    )
    request.with_suffix(".status.json").write_text(
        json.dumps(
            {
                "analysis_id": ANALYSIS_ID,
                "attempt": 1,
                "stage": "step4_publish",
                "generation": 1,
                "request_hash": execution.request_hash,
                "execution_id": execution.execution_id,
                "status": "failed",
                "message": "SFS export did not become visible",
                "receipt_hash": "b" * 64,
            }
        ),
        encoding="utf-8",
    )
    with sessions() as session:
        session.add_all([_run(), execution])
        session.commit()

        result = sync_gatk_stage_status(
            session=session,
            settings=settings,
            analysis_id=ANALYSIS_ID,
            attempt=1,
            stage="step4_publish",
        )
        run = session.scalar(select(AnalysisRun))

    assert result["failed"] is True
    assert run is not None
    assert run.status == "failed"
    assert run.current_stage == "step4_publish"
    assert run.error_summary == "SFS export did not become visible"
    assert run.pipeline_finished_at is not None
    assert run.ended_at is not None


def test_new_generation_reopens_failed_stage_projection(tmp_path: Path) -> None:
    sessions = _sessions()
    settings = _settings(tmp_path)
    terminal_at = datetime(2026, 9, 9, 4, 40, tzinfo=timezone.utc)
    run = _run()
    run.status = "failed"
    run.error_summary = "old failure"
    run.ended_at = terminal_at
    run.pipeline_finished_at = terminal_at
    failed = _execution("step4_publish", 1, "failed")
    failed.receipt_hash = "b" * 64
    stage_state = RunStageState(
        analysis_id=ANALYSIS_ID,
        attempt=1,
        stage_code="step4_publish",
        step_number=4,
        stage_label="Publish results",
        stage_status="failed",
        progress_source="gatk-runtime",
        started_at=terminal_at,
        ended_at=terminal_at,
        updated_at=terminal_at,
    )
    with sessions() as session:
        session.add_all([
            run,
            _execution("step3_monitor", 1, "success"),
            failed,
            stage_state,
        ])
        session.commit()

        result = register_gatk_stage(
            session=session,
            settings=settings,
            analysis_id=ANALYSIS_ID,
            attempt=1,
            stage="step4_publish",
        )
        refreshed_run = session.scalar(select(AnalysisRun))
        refreshed_stage = session.scalar(select(RunStageState))

    assert result["generation"] == 2
    assert refreshed_run is not None
    assert refreshed_run.status == "running"
    assert refreshed_run.error_summary is None
    assert refreshed_run.ended_at is None
    assert refreshed_run.pipeline_finished_at is None
    assert refreshed_stage is not None
    assert refreshed_stage.stage_status == "accepted"
    assert refreshed_stage.ended_at is None


def test_previous_generation_sidecar_is_pending_not_invalid(tmp_path: Path) -> None:
    sessions = _sessions()
    settings = _settings(tmp_path)
    request = (
        Path(settings.gatk_runtime_request_root)
        / ANALYSIS_ID
        / "attempt-1"
        / "step4_publish.request.json"
    )
    request.parent.mkdir(parents=True)
    current = _execution("step4_publish", 2, "accepted")
    previous = _execution("step4_publish", 1, "failed")
    request.write_text("{}", encoding="utf-8")
    request.with_suffix(".status.json").write_text(
        json.dumps(
            {
                "analysis_id": ANALYSIS_ID,
                "attempt": 1,
                "stage": "step4_publish",
                "generation": 1,
                "request_hash": previous.request_hash,
                "execution_id": previous.execution_id,
                "status": "failed",
            }
        ),
        encoding="utf-8",
    )
    with sessions() as session:
        session.add_all([_run(), previous, current])
        session.commit()

        result = sync_gatk_stage_status(
            session=session,
            settings=settings,
            analysis_id=ANALYSIS_ID,
            attempt=1,
            stage="step4_publish",
        )
        refreshed = session.scalar(
            select(PipelineStageExecution).where(
                PipelineStageExecution.execution_id == current.execution_id
            )
        )

    assert result["generation"] == 2
    assert result["status"] == "accepted"
    assert result["ready"] is False
    assert result["failed"] is False
    assert "generation 2" in result["message"]
    assert refreshed is not None
    assert refreshed.status == "accepted"
