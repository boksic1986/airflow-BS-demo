import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import (
    AnalysisRun,
    Base,
    PipelineStageExecution,
    RuleState,
    RunAttempt,
    TransferJob,
)
from app.wgs_observer import ingest_bound_pipeline_evidence_once


def test_gatk_logger_jsonl_projects_rule_and_phase(tmp_path: Path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    analysis_id = "GATK_20260908_120000_A1B2C3"
    release = "gatk-scmc-v7.6.0@bd04f6d"
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="gatk",
                dag_id="bio_gatk",
                status="running",
                attempt=1,
                workdir="/runtime/gatk/run",
                params_json={"pipeline_release_id": release},
            )
        )
        session.add(
            RunAttempt(
                analysis_id=analysis_id,
                attempt=1,
                execution_mode="cce",
                status="running",
            )
        )
        session.commit()

    evidence_root = tmp_path / "evidence"
    evidence = evidence_root / analysis_id / "attempt-1"
    raw = evidence / "rule-status" / "raw"
    raw.mkdir(parents=True)
    payload = {
        "schema_version": "rule-event.v1",
        "event": "job_started",
        "event_id": "event-1",
        "analysis_id": analysis_id,
        "attempt": 1,
        "run_id": f"{analysis_id}-a1",
        "pipeline_release_id": release,
        "sequence": 1,
        "timestamp": "2026-09-08T12:00:00+00:00",
        "rule_name": "sentieon_mapping",
        "rule_instance_id": "sentieon_mapping:SCMC001:17",
        "sample_id": "SCMC001",
        "job_id": "17",
    }
    (raw / "events.jsonl").write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = ingest_bound_pipeline_evidence_once(
        session_factory=sessions,
        analysis_id=analysis_id,
        attempt=1,
        pipeline_release_id=release,
        run_label="cce-run-0123456789abcdef",
        evidence_root=evidence_root,
        evidence_directory=evidence,
    )

    assert result["events_ingested"] == 1
    with sessions() as session:
        row = session.scalar(select(RuleState))
        assert row is not None
        assert row.rule_name == "sentieon_mapping"
        assert row.phase == "Mapping"


def test_gatk_transfer_progress_is_fenced_by_generic_stage_execution(
    tmp_path: Path,
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    analysis_id = "GATK_20260908_120000_A1B2C3"
    execution_id = f"{analysis_id}-a1-step1_upload-g1"
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="gatk",
                dag_id="bio_gatk",
                status="running",
                attempt=1,
                workdir="/runtime/gatk/run",
                params_json={"orchestration_contract_version": 2},
            )
        )
        session.add(
            PipelineStageExecution(
                execution_id=execution_id,
                pipeline_name="gatk",
                analysis_id=analysis_id,
                attempt=1,
                stage_code="step1_upload",
                generation=1,
                status="running",
                request_hash="a" * 64,
                release_id="gatk-scmc-v7.6.0@bd04f6d",
            )
        )
        session.commit()

    evidence_root = tmp_path / "evidence"
    evidence = evidence_root / analysis_id / "attempt-1"
    evidence.mkdir(parents=True)
    spool = tmp_path / "transfer"
    progress = spool / analysis_id / "attempt-1" / "step1_upload" / "progress.json"
    progress.parent.mkdir(parents=True)
    payload = {
        "schema_version": "wgs-runtime.transfer-progress.v2",
        "orchestration_contract_version": 2,
        "analysis_id": analysis_id,
        "attempt": 1,
        "execution_id": execution_id,
        "generation": 1,
        "request_hash": "a" * 64,
        "transfer_id": f"{analysis_id}-a1-input",
        "stage": "step1_upload",
        "direction": "upload",
        "state": "running",
        "bytes_total": 100,
        "bytes_done": 25,
        "files_total": 1,
        "files_done": 0,
        "speed_bytes_per_second": 10,
        "heartbeat_at": "2026-09-08T12:00:00Z",
        "files": [],
    }
    progress.write_text(json.dumps(payload), encoding="utf-8")

    result = ingest_bound_pipeline_evidence_once(
        session_factory=sessions,
        analysis_id=analysis_id,
        attempt=1,
        pipeline_release_id="gatk-scmc-v7.6.0@bd04f6d",
        run_label="cce-run-0123456789abcdef",
        evidence_root=evidence_root,
        evidence_directory=evidence,
        transfer_spool_root=spool,
    )

    assert result["events_ingested"] == 1
    with sessions() as session:
        transfer = session.scalar(select(TransferJob))
        assert transfer is not None
        assert transfer.bytes_transferred == 25
