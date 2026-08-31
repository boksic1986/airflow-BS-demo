import json
import os
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
    TransferJob,
    WgsMaintenanceAction,
)
from app.wgs_observer import ingest_evidence_once, sync_runtime_stage_artifacts


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


def test_transfer_progress_spool_is_idempotent(tmp_path: Path) -> None:
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

    assert first["events_ingested"] == 1
    assert second["events_ingested"] == 0
    with sessions() as session:
        row = session.scalar(select(TransferJob).where(TransferJob.transfer_id == "input-1"))
        assert row.bytes_transferred == 500
        assert row.current_file == "S1_R2.fastq.gz"


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
                "master": {
                    "master_state": "RUNNING",
                    "normal": True,
                    "percent": 12.5,
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

    assert result["events_ingested"] == 2
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


def test_biosan_jsonl_contract_and_degraded_marker(tmp_path: Path) -> None:
    sessions, analysis_id, evidence_root, binding_root, catalog_path, rule_dir = prepare_run(tmp_path)
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
        "wildcards": {"sample": "S1"},
    }
    events = [
        {**base, "event_id": "evt-1", "sequence": 1, "timestamp": "2026-08-24T01:00:00Z", "event": "job_info", "status": "planned"},
        {**base, "event_id": "evt-2", "sequence": 2, "timestamp": "2026-08-24T01:00:01Z", "event": "job_started", "status": "running", "snakemake_jobid": 7},
        {**base, "event_id": "evt-3", "sequence": 3, "timestamp": "2026-08-24T01:00:02Z", "event": "job_finished", "status": "success", "snakemake_jobid": 7},
    ]
    path.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")
    marker = rule_dir.parents[1] / "LOGGER_DEGRADED.json"
    marker.write_text(json.dumps({"message": "disk append failed"}), encoding="utf-8")

    result = poll(sessions, evidence_root, binding_root, catalog_path)

    assert result["events_ingested"] == 3
    with sessions() as session:
        state = session.scalar(select(RuleState))
        assert state.rule_name == "mapping"
        assert state.sample_id == "S1"
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
