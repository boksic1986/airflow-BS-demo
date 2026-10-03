"""A verified same-attempt recovery must replace stale tracker projections."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.diagnostics_service import sync_wgs_airflow_status
from app.models import AnalysisRun, Base, RunStageState, WgsStageExecution
from app.wgs_observer import _ingest_runtime_stage_status


def test_current_prepare_generation_replaces_failed_projection_only(tmp_path):
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    analysis_id = "WGS_SYNTHETIC_PREPARE_RECOVERY"
    old_at = datetime(2026, 9, 28, 1, 0, tzinfo=timezone.utc)
    request_root = tmp_path / "runner-requests"
    status_path = request_root / analysis_id / "attempt-1" / "prepare_analysis.status.json"
    status_path.parent.mkdir(parents=True)

    with sessions.begin() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                dag_run_id=f"{analysis_id}-a1",
                attempt=1,
                status="running",
                execution_mode="cce",
                workdir=str(tmp_path),
                params_json={"orchestration_contract_version": 2},
            )
        )
        session.add_all(
            [
                WgsStageExecution(
                    execution_id="synthetic-prepare-g1",
                    analysis_id=analysis_id,
                    attempt=1,
                    stage_code="prepare_analysis",
                    generation=1,
                    status="failed",
                    request_hash="a" * 64,
                    release_id="synthetic-release",
                    ended_at=old_at,
                ),
                WgsStageExecution(
                    execution_id="synthetic-prepare-g2",
                    analysis_id=analysis_id,
                    attempt=1,
                    stage_code="prepare_analysis",
                    generation=2,
                    status="success",
                    request_hash="b" * 64,
                    release_id="synthetic-release",
                    receipt_hash="c" * 64,
                    ended_at=datetime(2026, 9, 28, 2, 0, tzinfo=timezone.utc),
                ),
                RunStageState(
                    analysis_id=analysis_id,
                    attempt=1,
                    stage_code="prepare_analysis",
                    stage_label="Preparing WGS analysis",
                    stage_status="failed",
                    progress_source="wgs-runtime.stage-status.v1",
                    message="old prepare failure",
                    ended_at=old_at,
                    updated_at=old_at,
                ),
            ]
        )

    def ingest(execution_id, generation, request_hash, status):
        status_path.write_text(
            json.dumps(
                {
                    "schema_version": "wgs-runtime.stage-status.v1",
                    "orchestration_contract_version": 2,
                    "analysis_id": analysis_id,
                    "attempt": 1,
                    "stage": "prepare_analysis",
                    "execution_id": execution_id,
                    "generation": generation,
                    "request_hash": request_hash,
                    "retry_no": 0,
                    "status": status,
                    "updated_at": "2026-09-28T02:00:00Z",
                    "message": "new prepare receipt",
                }
            ),
            encoding="utf-8",
        )
        return _ingest_runtime_stage_status(sessions, request_root, status_path)

    assert ingest("synthetic-prepare-g1", 1, "a" * 64, "success") is False
    with pytest.raises(ValueError, match="identity mismatch"):
        ingest("synthetic-prepare-g2", 2, "foreign" * 9 + "x", "success")
    with sessions() as session:
        assert session.scalar(select(RunStageState)).stage_status == "failed"

    assert ingest("synthetic-prepare-g2", 2, "b" * 64, "success") is True
    with sessions() as session:
        stage = session.scalar(select(RunStageState))
        execution = session.scalar(
            select(WgsStageExecution).where(WgsStageExecution.generation == 2)
        )
        assert execution.status == stage.stage_status == "success"
        assert stage.message == "new prepare receipt"
        assert stage.ended_at.replace(tzinfo=timezone.utc) > old_at

    assert ingest("synthetic-prepare-g2", 2, "b" * 64, "failed") is False
    assert ingest("synthetic-prepare-g2", 2, "b" * 64, "canceled") is False
    with sessions() as session:
        assert session.scalar(select(RunStageState)).stage_status == "success"
    engine.dispose()


def test_airflow_reopens_failed_run_without_old_pipeline_finished_time(tmp_path):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    analysis_id = "WGS_SYNTHETIC_AIRFLOW_RECOVERY"
    old_at = datetime(2026, 9, 28, 1, 0, tzinfo=timezone.utc)
    with sessions.begin() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                dag_run_id=f"{analysis_id}-a1",
                attempt=1,
                status="failed",
                current_stage="prepare_analysis",
                execution_mode="cce",
                workdir=str(tmp_path),
                params_json={"orchestration_contract_version": 2},
                ended_at=old_at,
                pipeline_finished_at=old_at,
                error_summary="old prepare failure",
            )
        )

    airflow = SimpleNamespace(
        get_dag_run=lambda dag_id, dag_run_id: {
            "state": "running",
            "start_date": "2026-09-28T00:30:00Z",
            "end_date": None,
        }
    )
    with sessions() as session:
        payload = sync_wgs_airflow_status(
            session=session,
            airflow_client=airflow,
            analysis_id=analysis_id,
            settings=SimpleNamespace(),
        )
        run = session.scalar(select(AnalysisRun))
        assert payload["status"] == run.status == "running"
        assert run.ended_at is None
        assert run.pipeline_finished_at is None
        assert run.error_summary is None
        assert run.current_stage == "prepare_analysis"
    engine.dispose()
