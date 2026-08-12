import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, KubernetesWorkload, RuleEventRaw, RuleState
from app.wgs_observer import ingest_evidence_once


def make_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_observer_replays_rule_and_pod_events_idempotently(tmp_path: Path) -> None:
    sessions = make_sessionmaker()
    analysis_id = "WGS_20260812_000001_AAAAAA"
    with sessions() as session:
        session.add(AnalysisRun(analysis_id=analysis_id, pipeline_name="wgs", dag_id="bio_wgs_cce", execution_mode="cce", workdir=str(tmp_path), status="running"))
        session.commit()

    run_dir = tmp_path / analysis_id / "attempt-1"
    rule_dir = run_dir / "rule-status" / "raw"
    pod_dir = run_dir / "raw"
    rule_dir.mkdir(parents=True)
    pod_dir.mkdir(parents=True)
    (run_dir / "analysis.json").write_text(json.dumps({"analysis_id": analysis_id, "attempt": 1}), encoding="utf-8")
    events = [
        {"event": "rule_planned", "event_id": "evt-1", "rule_instance_id": "0123456789abcdef", "rule_name": "mapping", "timestamp": 1.0, "run_label": "wgs392-0123456789abcdef", "role": "master", "attempt": 1, "stream_id": "s1", "layer": 1},
        {"event": "job_started", "event_id": "evt-2", "rule_instance_id": "0123456789abcdef", "rule_name": "mapping", "timestamp": 2.0, "run_label": "wgs392-0123456789abcdef", "role": "worker", "attempt": 1, "stream_id": "s2", "job_id": "1"},
    ]
    (rule_dir / "master.jsonl").write_text("".join(json.dumps(row) + "\n" for row in events), encoding="utf-8")
    (pod_dir / "pod-status.jsonl").write_text(json.dumps({"event_id": "pod-1", "pod_hash": "abc", "job_name": "job-1", "phase": "Running", "reason": None, "timestamp": "2026-08-12T00:00:00+00:00"}) + "\n", encoding="utf-8")

    first = ingest_evidence_once(session_factory=sessions, evidence_root=tmp_path)
    second = ingest_evidence_once(session_factory=sessions, evidence_root=tmp_path)

    assert first["events_ingested"] == 3
    assert second["events_ingested"] == 0
    with sessions() as session:
        assert len(session.scalars(select(RuleEventRaw)).all()) == 2
        rule = session.scalar(select(RuleState).where(RuleState.analysis_id == analysis_id))
        assert rule.status == "running"
        assert session.scalar(select(KubernetesWorkload).where(KubernetesWorkload.analysis_id == analysis_id)).phase == "Running"

