import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    AnalysisRun,
    Base,
    EvidenceCursor,
    KubernetesWorkload,
    ObserverRunState,
    RuleEventRaw,
    RuleState,
    RunAttempt,
    RunStageState,
    Sample,
    TransferJob,
    TransferFileState,
    WgsStageExecution,
    WgsMaintenanceAction,
)
from app.wgs_observer import (
    ingest_evidence_once,
    ingest_observer_attempt_once,
    sync_runtime_stage_artifacts,
    upsert_stage_state,
)


RELEASE_ID = "wgs-4.1.1-1656b5d"
RUN_LABEL = "WGS_20260812_000001_AAAAAA-a1"


def make_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def write_catalog(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                'schema_version: "3"',
                "release:",
                f"  release_id: {RELEASE_ID}",
                "  version: V4.1.1",
                "  source_commit: 1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
                "  bs10610_repo_path: /mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1",
                "  node200_repo_path: /bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1",
                '  rule_event_schema_version: "1"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def rule_event(event: str, timestamp: float, **fields) -> dict:
    return {
        "schema_version": "1",
        "event": event,
        "timestamp": timestamp,
        "run_label": RUN_LABEL,
        "attempt": "1",
        "role": fields.pop("role", "worker"),
        "stream_id": fields.pop("stream_id", "worker-a"),
        **fields,
    }


def prepare_run(tmp_path: Path, *, attempt: int = 1, bind_attempt: int | None = None):
    sessions = make_sessionmaker()
    analysis_id = "WGS_20260812_000001_AAAAAA"
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs_cce",
                execution_mode="cce",
                attempt=attempt,
                workdir=str(tmp_path),
                status="running",
                params_json={
                    "pipeline_release_id": RELEASE_ID,
                    "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
                },
            )
        )
        session.add(
            RunAttempt(
                analysis_id=analysis_id,
                attempt=attempt,
                execution_mode="cce",
                status="running",
                run_label=RUN_LABEL,
            )
        )
        session.commit()

    evidence_root = tmp_path / "evidence"
    binding_root = tmp_path / "bindings"
    catalog_path = tmp_path / "wgs_releases.yaml"
    relative_evidence = Path(analysis_id) / f"attempt-{attempt}"
    rule_dir = evidence_root / relative_evidence / "rule-status" / "raw"
    rule_dir.mkdir(parents=True)
    binding_root.mkdir()
    write_catalog(catalog_path)
    binding = {
        "schema_version": "3",
        "analysis_id": analysis_id,
        "attempt": bind_attempt if bind_attempt is not None else attempt,
        "pipeline_release_id": RELEASE_ID,
        "run_id": RUN_LABEL,
        "evidence_path": relative_evidence.as_posix(),
    }
    (binding_root / "run.json").write_text(json.dumps(binding), encoding="utf-8")
    return sessions, analysis_id, evidence_root, binding_root, catalog_path, rule_dir


def poll(sessions, evidence_root, binding_root, catalog_path):
    return ingest_evidence_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        binding_root=binding_root,
        catalog_path=catalog_path,
    )


def write_runtime_binding(
    runtime_root: Path,
    analysis_id: str,
    *,
    master_job: str = "cce-master-0123456789abcdef0123",
) -> Path:
    path = runtime_root / "runs" / analysis_id / "attempt-1" / "batch-binding.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.batch-binding.v2",
                "analysis_id": analysis_id,
                "attempt": 1,
                "pipeline_release_id": RELEASE_ID,
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
                "master_job": master_job,
                "namespace": "snakemake-ns",
                "resolved_runtime": {
                    "cce_pipeline_version": "0.8.1",
                    "profile_id": "wgs-4.1.1-r1",
                    "profile_revision": "r1",
                    "master_image_digest": "swr.example/master@sha256:" + "b" * 64,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_prepare_binding_persists_resolved_runtime_audit(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, _ = prepare_run(
        tmp_path
    )
    runtime_root = tmp_path / "runtime"
    binding = runtime_root / "runs" / analysis_id / "attempt-1" / "batch-binding.json"
    binding.parent.mkdir(parents=True)
    binding.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.batch-binding.v2",
                "analysis_id": analysis_id,
                "attempt": 1,
                "pipeline_release_id": RELEASE_ID,
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
                "resolved_runtime": {
                    "cce_pipeline_version": "0.7.0",
                    "profile_id": "wgs-4.1.1",
                    "profile_revision": "r1",
                    "profile_sha256": "a" * 64,
                    "master_image_digest": "swr.example/wgs-master@sha256:" + "b" * 64,
                    "repair_groups": {"cram": {"target": "linkage/cram"}},
                },
            }
        ),
        encoding="utf-8",
    )

    ingest_evidence_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        binding_root=binding_root,
        catalog_path=catalog_path,
        runtime_root=runtime_root,
    )

    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        assert run.params_json["resolved_runtime"]["cce_pipeline_version"] == "0.7.0"
        assert run.params_json["resolved_runtime"]["profile_revision"] == "r1"
        assert run.params_json["resolved_runtime"]["repair_groups"] == {
            "cram": {"target": "linkage/cram"}
        }


def test_stage_sensor_sync_ingests_only_its_attempt_runtime_binding(
    tmp_path: Path,
) -> None:
    sessions, analysis_id, _, _, _, _ = prepare_run(tmp_path)
    runtime_root = tmp_path / "runtime"
    request_root = runtime_root / "runner-requests"
    request_root.mkdir(parents=True)
    spool = runtime_root / "transfer-progress"
    binding = (
        runtime_root / "runs" / analysis_id / "attempt-1" / "batch-binding.json"
    )
    binding.parent.mkdir(parents=True)
    binding.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.batch-binding.v2",
                "analysis_id": analysis_id,
                "attempt": 1,
                "pipeline_release_id": RELEASE_ID,
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
                "resolved_runtime": {
                    "cce_pipeline_version": "0.8.1",
                    "profile_id": "wgs-4.1.1-r1",
                    "profile_revision": "r1",
                    "master_image_digest": "swr.example/master@sha256:" + "b" * 64,
                },
            }
        ),
        encoding="utf-8",
    )

    result = sync_runtime_stage_artifacts(
        session_factory=sessions,
        request_root=request_root,
        transfer_spool_root=spool,
        analysis_id=analysis_id,
        attempt=1,
        stage="step1_upload",
    )

    assert result == {"files": 1, "events_ingested": 1}
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        assert run.params_json["resolved_runtime"]["cce_pipeline_version"] == "0.8.1"


def test_step4_repair_status_updates_the_idempotent_maintenance_action(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, _ = prepare_run(
        tmp_path
    )
    runtime_root = tmp_path / "runtime"
    status_path = (
        runtime_root
        / "runner-requests"
        / analysis_id
        / "attempt-1"
        / "step4_repair_cram.status.json"
    )
    status_path.parent.mkdir(parents=True)
    with sessions() as session:
        session.add(
            WgsMaintenanceAction(
                action_id="step4-cram-test",
                analysis_id=analysis_id,
                attempt=1,
                action_type="repair_step4_cram",
                linkage_group="cram",
                status="queued",
                requested_by="operator",
            )
        )
        session.commit()
    status_path.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step4_repair_cram",
                "status": "success",
                "message": "CRAM linkage repaired",
                "updated_at": "2026-08-29T10:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    first = ingest_evidence_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        binding_root=binding_root,
        catalog_path=catalog_path,
        runtime_root=runtime_root,
    )
    second = ingest_evidence_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        binding_root=binding_root,
        catalog_path=catalog_path,
        runtime_root=runtime_root,
    )

    assert first["events_ingested"] == 1
    assert second["events_ingested"] == 0
    with sessions() as session:
        action = session.scalar(select(WgsMaintenanceAction))
        assert action.status == "success"
        assert action.ended_at is not None
        assert action.evidence_path.endswith("step4_repair_cram.status.json")
        assert action.error_message is None


def test_legacy_transfer_progress_is_rejected_instead_of_marked_exact(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, _ = prepare_run(tmp_path)
    spool = tmp_path / "transfer-spool"
    progress = spool / analysis_id / "attempt-1" / "input-1" / "progress.json"
    progress.parent.mkdir(parents=True)
    progress.write_text(json.dumps({
        "analysis_id": analysis_id, "attempt": 1, "transfer_id": "input-1",
        "transfer_type": "input_upload", "direction": "upload", "status": "running",
        "source": "/registered/manifest", "destination": "obs://approved/prefix",
        "bytes_total": 1000, "bytes_transferred": 500, "progress_percent": 50,
        "files_total": 2, "files_completed": 1, "current_file": "S1_R2.fastq.gz",
        "speed_bps": 100, "eta_seconds": 5, "checkpoint_ref": "input-1",
        "heartbeat_at": "2026-08-12T02:00:00Z",
    }), encoding="utf-8")

    first = ingest_evidence_once(session_factory=sessions, evidence_root=evidence_root, binding_root=binding_root, catalog_path=catalog_path, transfer_spool_root=spool)
    second = ingest_evidence_once(session_factory=sessions, evidence_root=evidence_root, binding_root=binding_root, catalog_path=catalog_path, transfer_spool_root=spool)

    assert first["events_ingested"] == 0
    assert first["errors"] == 1
    assert second["events_ingested"] == 0
    assert second["errors"] == 1
    with sessions() as session:
        row = session.scalar(select(TransferJob).where(TransferJob.transfer_id == "input-1"))
        assert row is None


def test_cce_pipeline_transfer_schema_is_normalized_without_api_breakage(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, _ = prepare_run(tmp_path)
    spool = tmp_path / "transfer-spool"
    progress = spool / analysis_id / "attempt-1" / "input-2" / "progress.json"
    progress.parent.mkdir(parents=True)
    progress.write_text(json.dumps({
        "schema_version": "cce-pipeline.transfer-progress.v1",
        "transfer_id": "input-2", "run_id": f"{analysis_id}-a1",
        "analysis_id": analysis_id, "attempt": 1,
        "direction": "upload", "state": "running",
        "bytes_total": 2000, "bytes_done": 750,
        "files_total": 4, "files_done": 1,
        "current_file": "S2_R1.fastq.gz",
        "speed_bytes_per_second": 125, "eta_seconds": 10,
        "estimated_completion_at": "2026-08-12T02:00:10Z",
        "checkpoint_path": "/registered/checkpoints/input-2",
        "heartbeat_at": "2026-08-12T02:00:00Z",
        "error_summary": "",
    }), encoding="utf-8")

    result = ingest_evidence_once(
        session_factory=sessions, evidence_root=evidence_root,
        binding_root=binding_root, catalog_path=catalog_path,
        transfer_spool_root=spool,
    )

    assert result["events_ingested"] == 1
    with sessions() as session:
        row = session.scalar(select(TransferJob).where(TransferJob.transfer_id == "input-2"))
        assert row.transfer_type == "input_upload"
        assert row.status == "running"
        assert row.bytes_transferred == 750
        assert row.files_completed == 1
        assert row.progress_percent == 38
        assert row.speed_bps == 125
        assert row.checkpoint_ref == "/registered/checkpoints/input-2"
        assert row.estimated_finish_at.isoformat().startswith("2026-08-12T02:00:10")
        stage = session.scalar(
            select(RunStageState).where(
                RunStageState.analysis_id == analysis_id,
                RunStageState.stage_code == "step1_upload",
            )
        )
        assert stage.stage_label == "Uploading FASTQ"
        assert stage.progress_available is True
        assert stage.progress_percent == 38
        assert stage.completed_units == 750
        assert stage.total_units == 2000
        assert stage.unit == "bytes"
        assert stage.speed_bps == 125
        assert stage.eta_seconds == 10


def test_contract_v2_transfer_progress_imports_files_and_rejects_old_generation(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, _ = prepare_run(tmp_path)
    spool = tmp_path / "transfer-spool"
    progress = spool / analysis_id / "attempt-1" / "step1_upload" / "progress.json"
    progress.parent.mkdir(parents=True)
    with sessions() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        run.params_json = {**run.params_json, "orchestration_contract_version": 2}
        session.add_all([
            WgsStageExecution(
                execution_id="wse_old_transfer_generation",
                analysis_id=analysis_id,
                attempt=1,
                stage_code="step1_upload",
                generation=1,
                status="failed",
                request_hash="a" * 64,
                release_id=RELEASE_ID,
            ),
            WgsStageExecution(
                execution_id="wse_current_transfer_generation",
                analysis_id=analysis_id,
                attempt=1,
                stage_code="step1_upload",
                generation=2,
                status="running",
                request_hash="b" * 64,
                release_id=RELEASE_ID,
            ),
        ])
        session.commit()

    base = {
        "schema_version": "wgs-runtime.transfer-progress.v2",
        "orchestration_contract_version": 2,
        "analysis_id": analysis_id,
        "attempt": 1,
        "transfer_id": f"{analysis_id}-a1-input",
        "stage": "step1_upload",
        "direction": "upload",
        "state": "running",
        "bytes_total": 300,
        "bytes_done": 100,
        "files_total": 2,
        "files_done": 1,
        "speed_bytes_per_second": 50,
        "heartbeat_at": "2026-09-04T03:00:00Z",
        "files": [
            {"file_key": "1" * 64, "display_name": "S1_R1.fastq.gz", "bytes_total": 100, "bytes_done": 100, "status": "success", "speed_bps": 50, "checksum_status": "verified", "error_message": None},
            {"file_key": "2" * 64, "display_name": "S1_R2.fastq.gz", "bytes_total": 200, "bytes_done": 0, "status": "accepted", "speed_bps": 0, "checksum_status": None, "error_message": None},
        ],
    }
    progress.write_text(json.dumps({**base, "execution_id": "wse_old_transfer_generation", "generation": 1, "request_hash": "a" * 64}), encoding="utf-8")
    stale = ingest_evidence_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        binding_root=binding_root,
        catalog_path=catalog_path,
        transfer_spool_root=spool,
    )
    assert stale["events_ingested"] == 0
    with sessions() as session:
        assert session.scalar(select(TransferJob)) is None

    progress.write_text(json.dumps({**base, "execution_id": "wse_current_transfer_generation", "generation": 2, "request_hash": "b" * 64}), encoding="utf-8")
    current = ingest_evidence_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        binding_root=binding_root,
        catalog_path=catalog_path,
        transfer_spool_root=spool,
    )
    assert current["events_ingested"] == 1
    with sessions() as session:
        transfer = session.scalar(select(TransferJob))
        files = session.scalars(select(TransferFileState).order_by(TransferFileState.file_key)).all()
        assert transfer.bytes_transferred == 100
        assert [(row.display_name, row.status) for row in files] == [
            ("S1_R1.fastq.gz", "success"),
            ("S1_R2.fastq.gz", "accepted"),
        ]


def test_later_phase_status_does_not_erase_structured_transfer_progress(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, _ = prepare_run(tmp_path)
    runtime = tmp_path / "runtime"
    request_root = runtime / "runner-requests"
    request_dir = request_root / analysis_id / "attempt-1"
    request_dir.mkdir(parents=True)
    spool = tmp_path / "transfer-spool"
    transfer_id = f"{analysis_id}-a1-input"
    progress = spool / analysis_id / "attempt-1" / transfer_id / "progress.json"
    progress.parent.mkdir(parents=True)
    progress.write_text(json.dumps({
        "schema_version": "cce-pipeline.transfer-progress.v1",
        "transfer_id": transfer_id,
        "run_id": f"{analysis_id}-a1",
        "analysis_id": analysis_id,
        "attempt": 1,
        "direction": "upload",
        "state": "running",
        "bytes_total": 2000,
        "bytes_done": 750,
        "files_total": 4,
        "files_done": 1,
        "current_file": "S2_R1.fastq.gz",
        "speed_bytes_per_second": 125,
        "eta_seconds": 10,
        "heartbeat_at": "2026-08-12T02:00:00Z",
    }), encoding="utf-8")
    ingest_evidence_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        binding_root=binding_root,
        catalog_path=catalog_path,
        transfer_spool_root=spool,
    )
    (request_dir / "step1_upload.status.json").write_text(json.dumps({
        "schema_version": "wgs-runtime.stage-status.v1",
        "analysis_id": analysis_id,
        "attempt": 1,
        "stage": "step1_upload",
        "status": "success",
        "updated_at": "2026-08-12T02:00:05Z",
        "message": "upload complete",
    }), encoding="utf-8")

    sync_runtime_stage_artifacts(
        session_factory=sessions,
        request_root=request_root,
        transfer_spool_root=spool,
        analysis_id=analysis_id,
        attempt=1,
        stage="step1_upload",
    )

    with sessions() as session:
        transfer = session.scalar(select(TransferJob).where(TransferJob.transfer_id == transfer_id))
        stage = session.scalar(select(RunStageState).where(
            RunStageState.analysis_id == analysis_id,
            RunStageState.stage_code == "step1_upload",
        ))
        assert transfer.status == "success"
        assert transfer.progress_detail_available is True
        assert transfer.bytes_transferred == 750
        assert stage.stage_status == "success"
        assert stage.progress_available is True
        assert stage.progress_percent == 38
        assert stage.completed_units == 750
        assert stage.speed_bps == 125


def test_terminal_stage_state_cannot_reverse_success_or_failure(tmp_path: Path) -> None:
    sessions, analysis_id, _, _, _, _ = prepare_run(tmp_path)
    first = datetime(2026, 8, 12, 2, 0, tzinfo=timezone.utc)
    with sessions() as session:
        success = upsert_stage_state(
            session,
            analysis_id=analysis_id,
            attempt=1,
            stage_code="step1_upload",
            stage_status="success",
            updated_at=first,
        )
        session.commit()
        upsert_stage_state(
            session,
            analysis_id=analysis_id,
            attempt=1,
            stage_code="step1_upload",
            stage_status="failed",
            updated_at=first + timedelta(seconds=5),
        )
        failed = upsert_stage_state(
            session,
            analysis_id=analysis_id,
            attempt=1,
            stage_code="step5_download",
            stage_status="failed",
            updated_at=first,
        )
        session.commit()
        upsert_stage_state(
            session,
            analysis_id=analysis_id,
            attempt=1,
            stage_code="step5_download",
            stage_status="success",
            updated_at=first + timedelta(seconds=5),
        )
        session.commit()
        session.refresh(success)
        session.refresh(failed)
        assert success.stage_status == "success"
        assert failed.stage_status == "failed"


def test_retry_generation_can_replace_prior_failed_transfer_stage(tmp_path: Path) -> None:
    sessions, analysis_id, _, _, _, _ = prepare_run(tmp_path)
    request_root = tmp_path / "runtime" / "runner-requests"
    request_dir = request_root / analysis_id / "attempt-1"
    request_dir.mkdir(parents=True)
    spool = tmp_path / "transfer-spool"
    failed_at = datetime(2026, 8, 12, 2, 0, tzinfo=timezone.utc)
    with sessions() as session:
        upsert_stage_state(
            session,
            analysis_id=analysis_id,
            attempt=1,
            stage_code="step5_download",
            stage_status="failed",
            updated_at=failed_at,
        )
        session.add(
            TransferJob(
                analysis_id=analysis_id,
                attempt=1,
                transfer_id=f"{analysis_id}-a1-result",
                transfer_type="result_download",
                direction="download",
                status="success",
                heartbeat_at=failed_at + timedelta(seconds=5),
                updated_at=failed_at + timedelta(seconds=5),
            )
        )
        session.commit()
    (request_dir / "step5_download.status.json").write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "retry_no": 1,
                "stage": "step5_download",
                "status": "success",
                "updated_at": (failed_at + timedelta(seconds=5)).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    sync_runtime_stage_artifacts(
        session_factory=sessions,
        request_root=request_root,
        transfer_spool_root=spool,
        analysis_id=analysis_id,
        attempt=1,
        stage="step5_download",
    )

    with sessions() as session:
        stage = session.scalar(
            select(RunStageState).where(
                RunStageState.analysis_id == analysis_id,
                RunStageState.attempt == 1,
                RunStageState.stage_code == "step5_download",
            )
        )
        assert stage.stage_status == "success"
        assert stage.ended_at.replace(tzinfo=timezone.utc) == failed_at + timedelta(
            seconds=5
        )


def test_stage_sensor_sync_reads_only_the_registered_transfer_path(tmp_path: Path) -> None:
    sessions, analysis_id, _, _, _, _ = prepare_run(tmp_path)
    request_root = tmp_path / "runtime" / "runner-requests"
    request_root.mkdir(parents=True)
    spool = tmp_path / "transfer-spool"
    expected_id = f"{analysis_id}-a1-input"
    for transfer_id in (expected_id, "unrelated-transfer"):
        progress = spool / analysis_id / "attempt-1" / transfer_id / "progress.json"
        progress.parent.mkdir(parents=True)
        progress.write_text(
            json.dumps(
                {
                    "schema_version": "cce-pipeline.transfer-progress.v1",
                    "transfer_id": transfer_id,
                    "run_id": f"{analysis_id}-a1",
                    "analysis_id": analysis_id,
                    "attempt": 1,
                    "direction": "upload",
                    "state": "running",
                    "bytes_total": 100,
                    "bytes_done": 50,
                    "files_total": 2,
                    "files_done": 1,
                    "heartbeat_at": "2026-08-30T02:00:00Z",
                }
            ),
            encoding="utf-8",
        )

    result = sync_runtime_stage_artifacts(
        session_factory=sessions,
        request_root=request_root,
        transfer_spool_root=spool,
        analysis_id=analysis_id,
        attempt=1,
        stage="step1_upload",
    )

    assert result == {"files": 1, "events_ingested": 1}
    with sessions() as session:
        rows = session.scalars(select(TransferJob)).all()
        assert [row.transfer_id for row in rows] == [expected_id]


def test_wgs_4_1_1_stage_status_is_phase_only_and_master_only(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, _ = prepare_run(tmp_path)
    runtime = tmp_path / "runtime"
    request_dir = runtime / "runner-requests" / analysis_id / "attempt-1"
    request_dir.mkdir(parents=True)
    write_runtime_binding(
        runtime,
        analysis_id,
        master_job="wgs-master-0123456789abcdef0123",
    )
    common = {
        "schema_version": "wgs-runtime.stage-status.v1",
        "analysis_id": analysis_id,
        "attempt": 1,
        "updated_at": "2026-08-26T10:00:00Z",
        "message": "running",
    }
    (request_dir / "step1_upload.status.json").write_text(
        json.dumps({**common, "stage": "step1_upload", "status": "running"}),
        encoding="utf-8",
    )
    (request_dir / "step3_monitor.status.json").write_text(
        json.dumps(
            {
                **common,
                "stage": "step3_monitor",
                "status": "running",
                "monitoring_health": "degraded",
                "monitoring_error": "Rule evidence bridge failed",
                "master_job": "wgs-master-0123456789abcdef0123",
                "namespace": "snakemake-ns",
                "run_label": "cce-run-0123456789abcdef",
                "master": {
                    "master_state": "RUNNING",
                    "normal": True,
                    "percent": 12.5,
                    "completed": 26,
                    "total": 209,
                    "current_rule": "pre_process_mapping",
                    "message": "analysis running",
                },
            }
        ),
        encoding="utf-8",
    )

    result = ingest_evidence_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        binding_root=binding_root,
        catalog_path=catalog_path,
        runtime_root=runtime,
    )
    replay = ingest_evidence_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        binding_root=binding_root,
        catalog_path=catalog_path,
        runtime_root=runtime,
    )

    assert result["events_ingested"] == 3
    assert replay["events_ingested"] == 0
    with sessions() as session:
        transfer = session.scalar(select(TransferJob))
        assert transfer.status == "running"
        assert transfer.progress_detail_available is False
        workload = session.scalar(select(KubernetesWorkload))
        assert workload.job_name.startswith("wgs-master-")
        assert workload.phase == "Running"
        observer = session.scalar(select(ObserverRunState))
        assert observer.status == "degraded"
        assert observer.last_error == "Rule evidence bridge failed"
        stage = session.scalar(
            select(RunStageState).where(
                RunStageState.analysis_id == analysis_id,
                RunStageState.stage_code == "step3_monitor",
            )
        )
        assert stage.stage_label == "WGS workflow running"
        assert stage.progress_available is True
        assert stage.progress_percent == 12
        assert stage.completed_units == 26
        assert stage.total_units == 209
        assert stage.current_item == "pre_process_mapping"


def test_step3_transitional_status_without_master_is_not_an_ingest_error(
    tmp_path: Path,
) -> None:
    sessions, analysis_id, _, _, _, _ = prepare_run(tmp_path)
    runtime = tmp_path / "runtime"
    request_root = runtime / "runner-requests"
    request_dir = request_root / analysis_id / "attempt-1"
    request_dir.mkdir(parents=True)
    write_runtime_binding(runtime, analysis_id)
    (request_dir / "step3_monitor.status.json").write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step3_monitor",
                "status": "accepted",
                "message": "",
                "updated_at": "2026-09-01T04:24:41Z",
            }
        ),
        encoding="utf-8",
    )

    result = sync_runtime_stage_artifacts(
        session_factory=sessions,
        request_root=request_root,
        transfer_spool_root=runtime / "transfer-progress",
        analysis_id=analysis_id,
        attempt=1,
        stage="step3_monitor",
    )

    assert result == {"files": 2, "events_ingested": 1}
    with sessions() as session:
        assert session.scalar(select(KubernetesWorkload)) is None
        stage = session.scalar(select(RunStageState))
        assert stage.stage_code == "step3_monitor"
        assert stage.stage_status == "accepted"
        assert stage.progress_available is False


def test_step3_accepts_cce_master_only_when_it_matches_frozen_binding(
    tmp_path: Path,
) -> None:
    sessions, analysis_id, evidence_root, _, _, rule_dir = prepare_run(tmp_path)
    runtime = tmp_path / "runtime"
    request_root = runtime / "runner-requests"
    request_dir = request_root / analysis_id / "attempt-1"
    request_dir.mkdir(parents=True)
    master_job = "cce-master-0123456789abcdef0123"
    write_runtime_binding(runtime, analysis_id, master_job=master_job)
    with sessions.begin() as session:
        session.add(
            ObserverRunState(
                analysis_id=analysis_id,
                attempt=1,
                pipeline_release_id=RELEASE_ID,
                run_label=RUN_LABEL,
                relative_evidence_path=f"{analysis_id}/attempt-1",
                lifecycle_status="active",
                monitoring_health="healthy",
            )
        )
    status_path = request_dir / "step3_monitor.status.json"
    status_path.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step3_monitor",
                "status": "running",
                "message": "running",
                "updated_at": "2026-09-01T04:25:00Z",
                "monitoring_health": "healthy",
                "master_job": master_job,
                "namespace": "snakemake-ns",
                "run_label": "cce-run-0123456789abcdef",
                "master": {"master_state": "RUNNING", "percent": 1.4},
            }
        ),
        encoding="utf-8",
    )

    result = sync_runtime_stage_artifacts(
        session_factory=sessions,
        request_root=request_root,
        transfer_spool_root=runtime / "transfer-progress",
        analysis_id=analysis_id,
        attempt=1,
        stage="step3_monitor",
    )

    assert result == {"files": 2, "events_ingested": 2}
    with sessions() as session:
        workload = session.scalar(select(KubernetesWorkload))
        assert workload.job_name == master_job
        assert workload.phase == "Running"
        observer = session.scalar(select(ObserverRunState))
        assert observer.run_label == "cce-run-0123456789abcdef"

    (rule_dir / "master.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "event": "job_info",
                "timestamp": 1788236700.0,
                "run_label": "cce-run-0123456789abcdef",
                "attempt": "attempt-1",
                "role": "master",
                "stream_id": "master-a",
                "event_id": "event-1",
                "rule_instance_id": "mapping:sample-a",
                "rule_name": "mapping",
                "snakemake_jobid": "1",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    evidence = ingest_observer_attempt_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        analysis_id=analysis_id,
        attempt=1,
    )
    assert evidence["events_ingested"] == 1


def test_step3_rejects_master_that_differs_from_frozen_binding(
    tmp_path: Path,
) -> None:
    sessions, analysis_id, _, _, _, _ = prepare_run(tmp_path)
    runtime = tmp_path / "runtime"
    request_root = runtime / "runner-requests"
    request_dir = request_root / analysis_id / "attempt-1"
    request_dir.mkdir(parents=True)
    write_runtime_binding(runtime, analysis_id, master_job="cce-master-expected")
    (request_dir / "step3_monitor.status.json").write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step3_monitor",
                "status": "running",
                "message": "running",
                "updated_at": "2026-09-01T04:25:00Z",
                "monitoring_health": "healthy",
                "master_job": "cce-master-other",
                "namespace": "snakemake-ns",
                "run_label": "cce-run-fedcba9876543210",
                "master": {"master_state": "RUNNING", "percent": 1.4},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="frozen binding"):
        sync_runtime_stage_artifacts(
            session_factory=sessions,
            request_root=request_root,
            transfer_spool_root=runtime / "transfer-progress",
            analysis_id=analysis_id,
            attempt=1,
            stage="step3_monitor",
        )


def test_terminal_observer_is_degraded_when_rule_jsonl_is_missing(
    tmp_path: Path,
) -> None:
    sessions, analysis_id, evidence_root, _, _, rule_dir = prepare_run(tmp_path)
    rule_dir.rmdir()
    with sessions.begin() as session:
        session.add(
            ObserverRunState(
                analysis_id=analysis_id,
                attempt=1,
                pipeline_release_id=RELEASE_ID,
                run_label=RUN_LABEL,
                relative_evidence_path=f"{analysis_id}/attempt-1",
                lifecycle_status="draining",
                monitoring_health="healthy",
            )
        )

    result = ingest_observer_attempt_once(
        session_factory=sessions,
        evidence_root=evidence_root,
        analysis_id=analysis_id,
        attempt=1,
    )

    assert result["lifecycle_status"] == "stopped"
    with sessions() as session:
        observer = session.scalar(select(ObserverRunState))
        assert observer.monitoring_health == "degraded"
        assert observer.last_error == "Rule event JSONL was not produced"


def test_incremental_append_partial_line_and_restart_resume(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
    path = rule_dir / "worker-a.jsonl"
    planned = rule_event(
        "rule_planned",
        1.0,
        rule_instance_id="0123456789abcdef",
        rule_name="mapping",
        layer=1,
    )
    started = rule_event(
        "job_started", 2.0, rule_instance_id="0123456789abcdef", job_id="7"
    )
    planned_line = json.dumps(planned, sort_keys=True) + "\n"
    started_line = json.dumps(started, sort_keys=True)
    path.write_text(planned_line + started_line, encoding="utf-8")

    first = poll(sessions, evidence_root, binding_root, catalog_path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    second = poll(sessions, evidence_root, binding_root, catalog_path)
    third_after_restart = poll(sessions, evidence_root, binding_root, catalog_path)

    assert first == {"bindings": 1, "files": 1, "events_ingested": 1, "errors": 0}
    assert second["events_ingested"] == 1
    assert third_after_restart["events_ingested"] == 0
    with sessions() as session:
        assert len(session.scalars(select(RuleEventRaw)).all()) == 2
        state = session.scalar(select(RuleState).where(RuleState.analysis_id == analysis_id))
        assert state.status == "running"
        cursor = session.scalar(select(EvidenceCursor))
        assert cursor.byte_offset == path.stat().st_size
        assert cursor.line_number == 2
        observer = session.scalar(select(ObserverRunState))
        assert observer.pipeline_release_id == RELEASE_ID
        assert observer.status == "healthy"


def test_master_rule_status_accepts_attempt_label(tmp_path: Path) -> None:
    sessions, _, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(
        tmp_path
    )
    event = rule_event(
        "job_started",
        2.0,
        rule_instance_id="0123456789abcdef",
        job_id="7",
    )
    event["attempt"] = "attempt-1"
    (rule_dir / "master.jsonl").write_text(
        json.dumps(event, sort_keys=True) + "\n", encoding="utf-8"
    )

    result = poll(sessions, evidence_root, binding_root, catalog_path)

    assert result == {"bindings": 1, "files": 1, "events_ingested": 1, "errors": 0}
    with sessions() as session:
        assert session.scalar(select(RuleState)).status == "running"


def test_master_rule_status_uses_binding_attempt_for_logger_local_attempt(
    tmp_path: Path,
) -> None:
    sessions, _, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(
        tmp_path, attempt=7
    )
    event = rule_event(
        "job_started",
        2.0,
        rule_instance_id="0123456789abcdef",
        job_id="7",
    )
    event["attempt"] = "attempt-1"
    (rule_dir / "master.jsonl").write_text(
        json.dumps(event, sort_keys=True) + "\n", encoding="utf-8"
    )

    result = poll(sessions, evidence_root, binding_root, catalog_path)

    assert result == {"bindings": 1, "files": 1, "events_ingested": 1, "errors": 0}
    with sessions() as session:
        state = session.scalar(select(RuleState))
        assert state is not None
        assert state.attempt == 7
        assert state.status == "running"


def test_biosan_jsonl_contract_and_degraded_marker(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
    with sessions() as session:
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="S1",
                family_id="F1",
                status="running",
                qc_status="unknown",
            )
        )
        session.commit()
    path = rule_dir / "master.jsonl"
    base = {
        "schema_version": "rule-event.v1",
        "analysis_id": analysis_id,
        "run_id": f"{analysis_id}-a1",
        "attempt": 1,
        "pipeline_release_id": RELEASE_ID,
        "rule_instance_id": "biosan-rule-1",
        "rule_name": "mapping",
        "sample_id": "S1",
        "family_id": "F1",
        "phase": "pre-calling",
        "wildcards": {"sample": "S1"},
    }
    events = [
        {**base, "event_id": "evt-1", "sequence": 1, "timestamp": "2026-08-24T01:00:00Z", "event": "job_info", "status": "planned"},
        {**base, "event_id": "evt-2", "sequence": 2, "timestamp": "2026-08-24T01:00:01Z", "event": "job_started", "status": "running", "snakemake_jobid": 7},
        {**base, "event_id": "evt-3", "sequence": 3, "timestamp": "2026-08-24T01:00:02Z", "event": "job_finished", "status": "success", "snakemake_jobid": 7, "message": "done", "log_keys": ["stderr:biosan-rule-1"]},
    ]
    path.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")
    marker = rule_dir.parents[1] / "LOGGER_DEGRADED.json"
    marker.write_text(json.dumps({"message": "disk append failed"}), encoding="utf-8")

    result = poll(sessions, evidence_root, binding_root, catalog_path)

    assert result["events_ingested"] == 3
    with sessions() as session:
        state = session.scalar(select(RuleState))
        assert state.rule_name == "mapping"
        assert state.sequence == 1
        assert state.sample_id == "S1"
        assert state.family_id == "F1"
        assert state.phase == "Pre-calling"
        assert state.snakemake_jobid == "7"
        assert state.wildcards_json == {"sample": "S1"}
        assert state.message == "done"
        assert state.log_paths_json == ["stderr:biosan-rule-1"]
        assert state.status == "success"
        observer = session.scalar(select(ObserverRunState))
        assert observer.status == "degraded"
        assert observer.last_error == "disk append failed"


def test_bad_complete_json_stops_only_that_file(tmp_path: Path) -> None:
    sessions, _, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
    good = json.dumps(
        rule_event(
            "rule_planned",
            1.0,
            rule_instance_id="0123456789abcdef",
            rule_name="mapping",
            layer=1,
        )
    )
    (rule_dir / "a.jsonl").write_text(good + "\n{bad json}\n" + good + "\n", encoding="utf-8")
    (rule_dir / "b.jsonl").write_text(
        json.dumps(
            rule_event(
                "rule_planned",
                1.5,
                rule_instance_id="fedcba9876543210",
                rule_name="qc",
                layer=2,
                stream_id="worker-b",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    result = poll(sessions, evidence_root, binding_root, catalog_path)

    assert result == {"bindings": 1, "files": 2, "events_ingested": 2, "errors": 1}
    with sessions() as session:
        cursors = {row.relative_path: row for row in session.scalars(select(EvidenceCursor))}
        broken = next(row for key, row in cursors.items() if key.endswith("a.jsonl"))
        assert broken.byte_offset == len((good + "\n").encode())
        assert "invalid JSON" in broken.last_error
        assert len(session.scalars(select(RuleState)).all()) == 2


@pytest.mark.parametrize(
    ("change", "expected_error"),
    [
        ({"schema_version": "4"}, "schema_version"),
        ({"run_id": "unsafe"}, "run_label"),
        ({"evidence_path": "../escape"}, "evidence_path"),
        ({"attempt": 2}, "unknown analysis attempt"),
        ({"analysis_id": "WGS_UNKNOWN"}, "unknown analysis"),
        ({"pipeline_release_id": "unapproved"}, "release"),
    ],
)
def test_invalid_binding_isolated_as_diagnostic(tmp_path: Path, change: dict, expected_error: str) -> None:
    sessions, _, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
    binding_path = binding_root / "run.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    binding.update(change)
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    (rule_dir / "worker-a.jsonl").write_text("{}\n", encoding="utf-8")

    result = poll(sessions, evidence_root, binding_root, catalog_path)

    assert result["bindings"] == 0
    assert result["events_ingested"] == 0
    assert result["errors"] == 1
    with sessions() as session:
        assert session.scalar(select(ObserverRunState)) is None


def test_file_truncation_and_replacement_replay_safely(tmp_path: Path) -> None:
    sessions, _, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
    path = rule_dir / "worker-a.jsonl"
    first = rule_event(
        "rule_planned",
        1.0,
        rule_instance_id="0123456789abcdef",
        rule_name="mapping",
        layer=1,
    )
    second = rule_event(
        "job_started", 2.0, rule_instance_id="0123456789abcdef", job_id="7"
    )
    path.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")
    assert poll(sessions, evidence_root, binding_root, catalog_path)["events_ingested"] == 2

    replacement = rule_event(
        "job_finished", 3.0, rule_instance_id="0123456789abcdef", job_id="7"
    )
    new_path = rule_dir / "replacement.jsonl"
    new_path.write_text(json.dumps(replacement) + "\n", encoding="utf-8")
    os.replace(new_path, path)
    replay = poll(sessions, evidence_root, binding_root, catalog_path)

    assert replay["events_ingested"] == 1
    with sessions() as session:
        assert len(session.scalars(select(RuleEventRaw)).all()) == 3
        assert session.scalar(select(RuleState)).status == "success"


def test_job_info_mapping_and_worker_evidence_win_projection(tmp_path: Path) -> None:
    sessions, _, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
    events = [
        rule_event(
            "rule_planned",
            1.0,
            role="master",
            stream_id="master",
            rule_instance_id="0123456789abcdef",
            rule_name="mapping",
            layer=1,
        ),
        rule_event(
            "job_error",
            4.0,
            role="master",
            stream_id="master",
            rule_instance_id="0123456789abcdef",
            job_id="7",
            definitive=True,
        ),
        rule_event(
            "job_info",
            1.5,
            stream_id="worker-a",
            job_id="7",
            rule_instance_id="0123456789abcdef",
            rule_name="mapping",
            layer=1,
        ),
        rule_event("job_started", 2.0, stream_id="worker-a", job_id="7"),
        rule_event("job_finished", 3.0, stream_id="worker-a", job_id="7"),
    ]
    (rule_dir / "mixed.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in events), encoding="utf-8"
    )

    result = poll(sessions, evidence_root, binding_root, catalog_path)

    assert result["events_ingested"] == 5
    with sessions() as session:
        state = session.scalar(select(RuleState))
        assert state.rule_name == "mapping"
        assert state.status == "success"


def test_projection_derives_sample_from_wildcards_and_stable_event_order(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
    with sessions() as session:
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="WGS001-WGS",
                family_id="F001",
                status="running",
                qc_status="unknown",
            )
        )
        session.commit()
    events = [
        rule_event(
            "job_info",
            1.0,
            role="master",
            stream_id="master",
            rule_instance_id="0123456789abcdef",
            rule_name="pre_process_mapping",
            wildcards={"sample": "WGS001-WGS"},
            job_id="22",
        ),
        rule_event(
            "job_started",
            2.0,
            role="master",
            stream_id="master",
            rule_instance_id="0123456789abcdef",
            job_id="22",
        ),
        rule_event(
            "job_finished",
            3.0,
            role="master",
            stream_id="master",
            rule_instance_id="0123456789abcdef",
            job_id="22",
        ),
    ]
    (rule_dir / "master.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in events), encoding="utf-8"
    )

    poll(sessions, evidence_root, binding_root, catalog_path)

    with sessions() as session:
        state = session.scalar(select(RuleState))
        assert state.sequence == 1
        assert state.snakemake_jobid == "22"
        assert state.sample_id == "WGS001-WGS"
        assert state.family_id == "F001"


def test_analysis_log_enrichment_requires_exact_registered_sample_match(tmp_path: Path) -> None:
    from app import wgs_observer

    enrich = getattr(wgs_observer, "enrich_rule_states_from_analysis_log", None)
    assert callable(enrich), "analysis.log Rule context enrichment is not implemented"

    sessions = make_sessionmaker()
    analysis_id = "WGS_LOG_CONTEXT"
    log_path = tmp_path / "analysis.log"
    log_path.write_text(
        "rule pre_process_cleanFastq:\n"
        "    jobid: 23\n"
        "    wildcards: sample=WGS001-WGS\n"
        "\n"
        "rule pre_process_cleanFastq:\n"
        "    jobid: 24\n"
        "    wildcards: sample=UNREGISTERED\n",
        encoding="utf-8",
    )
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                execution_mode="cce",
                status="success",
                workdir="/data/wgs-results/runs/WGS_LOG_CONTEXT",
                params_json={"pipeline_release_id": RELEASE_ID},
            )
        )
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="WGS001-WGS",
                family_id="F001",
                status="success",
                qc_status="unknown",
            )
        )
        session.add_all(
            [
                RuleState(
                    analysis_id=analysis_id,
                    attempt=1,
                    rule_instance_id="rule-23",
                    rule_name="pre_process_cleanFastq",
                    snakemake_jobid="23",
                    status="success",
                ),
                RuleState(
                    analysis_id=analysis_id,
                    attempt=1,
                    rule_instance_id="rule-24",
                    rule_name="pre_process_cleanFastq",
                    snakemake_jobid="24",
                    status="success",
                ),
            ]
        )
        session.commit()

        updated = enrich(
            session,
            analysis_id=analysis_id,
            attempt=1,
            analysis_log=log_path,
        )
        session.commit()
        rows = session.scalars(
            select(RuleState).where(RuleState.analysis_id == analysis_id).order_by(RuleState.snakemake_jobid)
        ).all()

    assert updated == 1
    assert rows[0].sample_id == "WGS001-WGS"
    assert rows[0].family_id == "F001"
    assert rows[1].sample_id is None


def test_analysis_log_enrichment_accepts_unique_registered_data_id_alias(
    tmp_path: Path,
) -> None:
    from app import wgs_observer

    sessions = make_sessionmaker()
    analysis_id = "WGS_LOG_DATA_ID_ALIAS"
    log_path = tmp_path / "analysis.log"
    log_path.write_text(
        "rule pre_process_mapping:\n"
        "    jobid: 6\n"
        "    wildcards: sample=WGS26080568-WGS\n",
        encoding="utf-8",
    )
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                execution_mode="cce",
                status="running",
                workdir="/data/wgs-results/runs/WGS_LOG_DATA_ID_ALIAS",
                params_json={"pipeline_release_id": RELEASE_ID},
            )
        )
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="WGS26080568",
                family_id="JX26G00230117",
                metadata_json={"data_id": "WGS26080568-WGS"},
                status="running",
                qc_status="unknown",
            )
        )
        session.add(
            RuleState(
                analysis_id=analysis_id,
                attempt=1,
                rule_instance_id="mapping-6",
                rule_name="pre_process_mapping",
                snakemake_jobid="6",
                status="planned",
            )
        )
        session.commit()

        updated = wgs_observer.enrich_rule_states_from_analysis_log(
            session,
            analysis_id=analysis_id,
            attempt=1,
            analysis_log=log_path,
        )
        session.commit()
        state = session.scalar(
            select(RuleState).where(RuleState.analysis_id == analysis_id)
        )

    assert updated == 1
    assert state.sample_id == "WGS26080568"
    assert state.family_id == "JX26G00230117"


def test_rule_event_sample_and_family_must_match_registered_sample(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
    with sessions() as session:
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="REGISTERED-WGS",
                family_id="F-CANONICAL",
                status="running",
                qc_status="unknown",
            )
        )
        session.commit()
    events = [
        rule_event(
            "job_info",
            1.0,
            role="master",
            stream_id="master",
            rule_instance_id="registered-rule",
            rule_name="pre_process_mapping",
            sample_id="REGISTERED-WGS",
            family_id="F-FORGED",
            job_id="31",
        ),
        rule_event(
            "job_info",
            2.0,
            role="master",
            stream_id="master",
            rule_instance_id="unregistered-rule",
            rule_name="pre_process_mapping",
            sample_id="UNREGISTERED-WGS",
            family_id="F-FORGED",
            job_id="32",
        ),
    ]
    (rule_dir / "master.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in events), encoding="utf-8"
    )

    poll(sessions, evidence_root, binding_root, catalog_path)

    with sessions() as session:
        rows = {
            row.rule_instance_id: row
            for row in session.scalars(select(RuleState)).all()
        }
    assert rows["registered-rule"].sample_id == "REGISTERED-WGS"
    assert rows["registered-rule"].family_id == "F-CANONICAL"
    assert rows["unregistered-rule"].sample_id is None
    assert rows["unregistered-rule"].family_id is None


def test_analysis_log_enrichment_indexes_appends_and_rejoins_current_samples(
    tmp_path: Path,
) -> None:
    from app import wgs_observer

    sessions = make_sessionmaker()
    analysis_id = "WGS_LOG_CACHE"
    log_path = tmp_path / "analysis.log"
    log_path.write_text(
        "rule pre_process_cleanFastq:\n"
        "    jobid: 23\n"
        "    wildcards: sample=WGS001-WGS\n"
        "rule pre_process_cleanFastq:\n"
        "    jobid: 24\n"
        "    wildcards: sample=WGS002-WGS\n",
        encoding="utf-8",
    )
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                execution_mode="cce",
                status="running",
                workdir="/data/wgs-results/runs/WGS_LOG_CACHE",
                params_json={"pipeline_release_id": RELEASE_ID},
            )
        )
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="WGS001-WGS",
                family_id="F001",
                status="running",
                qc_status="unknown",
            )
        )
        session.add_all(
            [
                RuleState(
                    analysis_id=analysis_id,
                    attempt=1,
                    rule_instance_id="rule-23",
                    rule_name="pre_process_cleanFastq",
                    snakemake_jobid="23",
                    status="success",
                ),
                RuleState(
                    analysis_id=analysis_id,
                    attempt=1,
                    rule_instance_id="rule-24",
                    rule_name="pre_process_cleanFastq",
                    snakemake_jobid="24",
                    status="running",
                ),
            ]
        )
        session.commit()

    wgs_observer._ANALYSIS_LOG_INDEX.clear()
    with sessions() as session:
        assert wgs_observer.enrich_rule_states_from_analysis_log(
            session, analysis_id=analysis_id, attempt=1, analysis_log=log_path
        ) == 1
        session.commit()
        first_offset = wgs_observer._ANALYSIS_LOG_INDEX[str(log_path)].byte_offset
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="WGS002-WGS",
                family_id="F002",
                status="running",
                qc_status="unknown",
            )
        )
        session.commit()
        assert wgs_observer.enrich_rule_states_from_analysis_log(
            session, analysis_id=analysis_id, attempt=1, analysis_log=log_path
        ) == 1
        assert wgs_observer._ANALYSIS_LOG_INDEX[str(log_path)].byte_offset == first_offset

        session.add(
            RuleState(
                analysis_id=analysis_id,
                attempt=1,
                rule_instance_id="rule-25",
                rule_name="pre_process_cleanFastq",
                snakemake_jobid="25",
                status="running",
            )
        )
        session.commit()
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(
                "rule pre_process_cleanFastq:\n"
                "    jobid: 25\n"
                "    wildcards: sample=WGS002-WGS\n"
            )
        assert wgs_observer.enrich_rule_states_from_analysis_log(
            session, analysis_id=analysis_id, attempt=1, analysis_log=log_path
        ) == 1
        assert wgs_observer._ANALYSIS_LOG_INDEX[str(log_path)].byte_offset > first_offset


def test_analysis_log_incremental_index_resets_after_file_replacement(
    tmp_path: Path,
) -> None:
    from app import wgs_observer

    sessions = make_sessionmaker()
    analysis_id = "WGS_LOG_REPLACED"
    log_path = tmp_path / "analysis.log"
    log_path.write_text(
        "rule pre_process_cleanFastq:\n"
        "    jobid: 23\n"
        "    wildcards: sample=WGS001-WGS\n",
        encoding="utf-8",
    )
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                execution_mode="cce",
                status="running",
                workdir="/data/wgs-results/runs/WGS_LOG_REPLACED",
                params_json={"pipeline_release_id": RELEASE_ID},
            )
        )
        session.add_all(
            [
                Sample(
                    analysis_id=analysis_id,
                    sample_id="WGS001-WGS",
                    family_id="F001",
                    status="running",
                    qc_status="unknown",
                ),
                Sample(
                    analysis_id=analysis_id,
                    sample_id="WGS002-WGS",
                    family_id="F002",
                    status="running",
                    qc_status="unknown",
                ),
                RuleState(
                    analysis_id=analysis_id,
                    attempt=1,
                    rule_instance_id="rule-23",
                    rule_name="pre_process_cleanFastq",
                    snakemake_jobid="23",
                    status="success",
                ),
                RuleState(
                    analysis_id=analysis_id,
                    attempt=1,
                    rule_instance_id="rule-99",
                    rule_name="pre_process_cleanFastq",
                    snakemake_jobid="99",
                    status="success",
                ),
            ]
        )
        session.commit()

    wgs_observer._ANALYSIS_LOG_INDEX.clear()
    with sessions() as session:
        assert wgs_observer.enrich_rule_states_from_analysis_log(
            session, analysis_id=analysis_id, attempt=1, analysis_log=log_path
        ) == 1
        session.commit()
        old_identity = wgs_observer._ANALYSIS_LOG_INDEX[str(log_path)].file_identity

        replacement = tmp_path / "replacement.log"
        replacement.write_text(
            "rule pre_process_cleanFastq:\n"
            "    jobid: 99\n"
            "    wildcards: sample=WGS002-WGS\n"
            "replacement content is intentionally longer than the original\n",
            encoding="utf-8",
        )
        replacement.replace(log_path)
        assert wgs_observer.enrich_rule_states_from_analysis_log(
            session, analysis_id=analysis_id, attempt=1, analysis_log=log_path
        ) == 1
        session.commit()
        state = session.scalar(
            select(RuleState).where(RuleState.rule_instance_id == "rule-99")
        )
        new_identity = wgs_observer._ANALYSIS_LOG_INDEX[str(log_path)].file_identity

    assert old_identity != new_identity
    assert state.sample_id == "WGS002-WGS"
    assert state.family_id == "F002"


def test_pod_job_and_metrics_events_normalize_with_numeric_resource_versions(tmp_path: Path) -> None:
    sessions, _, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
    raw = rule_dir.parents[1] / "raw"
    raw.mkdir()
    pod_events = [
        {
            "event_key": "worker-a:9",
            "observed_at_utc": "2026-08-12T01:00:00+00:00",
            "job": "mapping-7",
            "pod_hash": "abc123",
            "resource_version": "9",
            "phase": "Running",
            "node_name": "cce-node-1",
        },
        {
            "event_key": "worker-a:10",
            "observed_at_utc": "2026-08-12T01:01:00+00:00",
            "job": "mapping-7",
            "pod_hash": "abc123",
            "resource_version": "10",
            "phase": "Failed",
            "container_status": {
                "imageID": "sha256:image",
                "state": {"terminated": {"reason": "OOMKilled", "exitCode": 137}},
            },
        },
        {
            "event_key": "worker-a:2",
            "observed_at_utc": "2026-08-12T00:59:00+00:00",
            "job": "mapping-7",
            "pod_hash": "abc123",
            "resource_version": "2",
            "phase": "Pending",
            "workload_role": "work",
            "run_label": "cce-run-0123456789abcdef",
            "workload_labels": {
                "wgs.biosan.cn/heavy-io": "true",
                "wgs.biosan.cn/heavy-slot": "07",
            },
        },
    ]
    metrics = {
        "event_key": "worker-a:metrics:1",
        "observed_at_utc": "2026-08-12T01:01:05+00:00",
        "pod_hash": "abc123",
        "metrics": {"timestamp": "2026-08-12T01:01:04Z", "containers": [{"usage": {"cpu": "2", "memory": "1Gi"}}]},
    }
    job = {
        "event_key": "mapping-7:11",
        "observed_at_utc": "2026-08-12T01:01:06+00:00",
        "job": "mapping-7",
        "resource_version": "11",
        "status": {"failed": 1, "conditions": [{"type": "Failed", "reason": "BackoffLimitExceeded", "message": "worker failed"}]},
    }
    (raw / "pod-events.jsonl").write_text("".join(json.dumps(row) + "\n" for row in pod_events), encoding="utf-8")
    (raw / "pod-metrics.jsonl").write_text(json.dumps(metrics) + "\n", encoding="utf-8")
    (raw / "job-events.jsonl").write_text(json.dumps(job) + "\n", encoding="utf-8")

    result = poll(sessions, evidence_root, binding_root, catalog_path)

    assert result == {"bindings": 1, "files": 3, "events_ingested": 5, "errors": 0}
    with sessions() as session:
        pod = session.scalar(select(KubernetesWorkload))
        assert pod.resource_version == "10"
        assert pod.phase == "Failed"
        assert pod.reason == "OOMKilled"
        assert pod.exit_code == 137
        assert pod.node_name == "cce-node-1"
        assert pod.image_id == "sha256:image"
        assert pod.resources_json["containers"][0]["usage"]["memory"] == "1Gi"
        assert pod.resources_json["heavy_io"] is True
        assert pod.resources_json["heavy_slot"] == "07"
        assert pod.job_status_json["failed"] == 1
        assert pod.message == "worker failed"


def test_image_pull_backoff_detail_is_preserved(tmp_path: Path) -> None:
    sessions, _, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
    raw = rule_dir.parents[1] / "raw"
    raw.mkdir()
    payload = {
        "event_key": "worker-b:20",
        "observed_at_utc": "2026-08-12T02:00:00+00:00",
        "job": "qc-8",
        "pod_hash": "def456",
        "resource_version": "20",
        "phase": "Pending",
        "container_status": {
            "state": {"waiting": {"reason": "ImagePullBackOff", "message": "pull access denied"}}
        },
    }
    (raw / "pod-events.jsonl").write_text(json.dumps(payload) + "\n", encoding="utf-8")

    poll(sessions, evidence_root, binding_root, catalog_path)

    with sessions() as session:
        pod = session.scalar(select(KubernetesWorkload))
        assert pod.phase == "Pending"
        assert pod.reason == "ImagePullBackOff"
        assert pod.message == "pull access denied"


@pytest.mark.parametrize(
    "stage", ["prepare", "prepare_sampleinfo", "prepare_analysis"]
)
def test_prepare_stages_are_valid_status_sync_targets(
    tmp_path: Path, stage: str
) -> None:
    sessions = make_sessionmaker()
    runtime = tmp_path / "runtime"

    result = sync_runtime_stage_artifacts(
        session_factory=sessions,
        request_root=runtime / "runner-requests",
        transfer_spool_root=runtime / "transfer-progress",
        analysis_id="WGS_20260903_062828_0858DC",
        attempt=2,
        stage=stage,
    )

    assert result == {"files": 0, "events_ingested": 0}
