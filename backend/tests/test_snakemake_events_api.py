from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, SnakemakeRuleEvent


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def insert_run(session_factory, *, analysis_id: str = "PGTA_20260703_090000_EVENTS") -> str:
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="pgta",
                dag_id="bio_pgta_airflow",
                dag_run_id=f"manual__{analysis_id}",
                mode="new",
                status="running",
                sample_sheet_path=f"/data/airflow-demo/runs/{analysis_id}/config/samples.selected.tsv",
                workdir=f"/data/airflow-demo/runs/{analysis_id}",
                params_json={"target": "metadata"},
            )
        )
        session.commit()
    return analysis_id


def test_snakemake_event_receiver_upserts_rule_event(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_run(session_factory)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)

    started = client.post(
        "/api/events/snakemake",
        json={
            "analysis_id": analysis_id,
            "event": "job_started",
            "rule": "metadata",
            "sample_id": "G1",
            "wildcards": {"sample": "G1"},
            "snakemake_jobid": "1",
            "status": "running",
            "stdout_path": "/data/airflow-demo/runs/test/logs/rules/metadata.G1.out",
            "stderr_path": "/data/airflow-demo/runs/test/logs/rules/metadata.G1.err",
            "message": "started",
            "timestamp": "2026-07-03T09:00:00+00:00",
        },
    )
    finished = client.post(
        "/api/events/snakemake",
        json={
            "analysis_id": analysis_id,
            "event": "job_finished",
            "rule": "metadata",
            "sample_id": "G1",
            "wildcards": {"sample": "G1"},
            "snakemake_jobid": "1",
            "status": "success",
            "message": "finished",
            "return_code": 0,
            "timestamp": "2026-07-03T09:01:30+00:00",
        },
    )

    assert started.status_code == 200
    assert started.json() == {"status": "ok"}
    assert finished.status_code == 200

    with session_factory() as session:
        events = session.scalars(select(SnakemakeRuleEvent)).all()

    assert len(events) == 1
    event = events[0]
    assert event.analysis_id == analysis_id
    assert event.rule == "metadata"
    assert event.sample_id == "G1"
    assert event.snakemake_jobid == "1"
    assert event.status == "success"
    assert event.wildcards_json == {"sample": "G1"}
    assert event.message == "finished"
    assert event.return_code == 0
    assert event.start_time.isoformat() == "2026-07-03T09:00:00"
    assert event.end_time.isoformat() == "2026-07-03T09:01:30"


def test_snakemake_event_receiver_rejects_missing_run(monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)

    response = client.post(
        "/api/events/snakemake",
        json={
            "analysis_id": "PGTA_MISSING",
            "event": "job_started",
            "rule": "metadata",
            "snakemake_jobid": "1",
            "status": "running",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "RUN_NOT_FOUND"


def test_snakemake_event_receiver_requires_rule(monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_run(session_factory)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)

    response = client.post(
        "/api/events/snakemake",
        json={
            "analysis_id": analysis_id,
            "event": "workflow_started",
            "status": "started",
        },
    )

    assert response.status_code == 422


def test_run_rules_endpoint_returns_rule_events(monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_run(session_factory)
    with session_factory() as session:
        session.add(
            SnakemakeRuleEvent(
                analysis_id=analysis_id,
                rule="metadata",
                sample_id="G1",
                wildcards_json={"sample": "G1"},
                snakemake_jobid="1",
                qsub_jobid=None,
                status="success",
                stdout_path="/data/stdout.log",
                stderr_path="/data/stderr.log",
                message="done",
                return_code=0,
                start_time=datetime(2026, 7, 3, 9, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 7, 3, 9, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 7, 3, 9, 1, tzinfo=timezone.utc),
            )
        )
        session.commit()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/rules")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "rule": "metadata",
            "sample_id": "G1",
            "status": "success",
            "snakemake_jobid": "1",
            "qsub_jobid": None,
            "stdout_path": "/data/stdout.log",
            "stderr_path": "/data/stderr.log",
            "start_time": "2026-07-03T09:00:00",
            "end_time": "2026-07-03T09:01:00",
            "message": "done",
            "return_code": 0,
            "wildcards": {"sample": "G1"},
        }
    ]
