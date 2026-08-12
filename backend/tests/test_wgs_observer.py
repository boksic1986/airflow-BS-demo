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
)
from app.wgs_observer import ingest_evidence_once


SNAPSHOT_ID = "wgs-v4.0.1-dev-136da1a-b10cd8af"
RUN_LABEL = "wgs392-0123456789abcdef"


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
                'schema_version: "1"',
                f"default_snapshot_id: {SNAPSHOT_ID}",
                "snapshots:",
                f"  - snapshot_id: {SNAPSHOT_ID}",
                "    pipeline: wgs",
                "    version: V4.0.1",
                "    server_path: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs",
                "    source_commit: 136da1ad9e45ac1abcbeb3efa40bb2e2269b6ab9",
                "    snapshot_manifest_sha256: b10cd8af1db19c313e15167c295d007d9eca246d03b2721592c4c0532a05696c",
                '    rule_event_schema_version: "1"',
                "    status: development",
                "    execution_enabled: false",
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
                params_json={"pipeline_snapshot_id": SNAPSHOT_ID},
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
        "schema_version": "1",
        "analysis_id": analysis_id,
        "attempt": bind_attempt if bind_attempt is not None else attempt,
        "pipeline_snapshot_id": SNAPSHOT_ID,
        "run_label": RUN_LABEL,
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
        assert observer.pipeline_snapshot_id == SNAPSHOT_ID
        assert observer.status == "healthy"


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
        ({"schema_version": "2"}, "schema_version"),
        ({"run_label": "unsafe"}, "run_label"),
        ({"evidence_path": "../escape"}, "evidence_path"),
        ({"attempt": 2}, "unknown analysis attempt"),
        ({"analysis_id": "WGS_UNKNOWN"}, "unknown analysis"),
        ({"pipeline_snapshot_id": "unapproved"}, "snapshot"),
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
