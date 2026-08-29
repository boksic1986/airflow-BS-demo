from datetime import datetime, timezone
import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    AnalysisRun,
    Base,
    ObserverRunState,
    RuleState,
    RunAttempt,
)
from app.wgs_observer import ingest_observer_attempt_once
from app.wgs_observer_cli import run_observer_iteration
from app.wgs_observer_lifecycle import (
    activate_observer,
    list_observer_work,
    request_observer_drain,
)


RELEASE_ID = "wgs-4.1.1-1656b5d"


def make_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def add_run(sessions, analysis_id: str, attempt: int = 1) -> None:
    with sessions.begin() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                execution_mode="cce",
                attempt=attempt,
                workdir=f"/runs/{analysis_id}",
                status="running",
                params_json={"pipeline_release_id": RELEASE_ID},
            )
        )
        session.add(
            RunAttempt(
                analysis_id=analysis_id,
                attempt=attempt,
                execution_mode="cce",
                status="running",
            )
        )


def test_activation_and_drain_are_idempotent_and_notify_after_state_change() -> None:
    sessions = make_sessionmaker()
    analysis_id = "WGS_20260830_010203_A1B2C3"
    add_run(sessions, analysis_id)
    notifications: list[tuple[str, int]] = []

    with sessions.begin() as session:
        first = activate_observer(
            session,
            analysis_id=analysis_id,
            attempt=1,
            notify=lambda _session, value, attempt: notifications.append((value, attempt)),
        )
        first_id = first.id
        first_lifecycle = first.lifecycle_status
    with sessions.begin() as session:
        second = activate_observer(
            session,
            analysis_id=analysis_id,
            attempt=1,
            notify=lambda _session, value, attempt: notifications.append((value, attempt)),
        )
        second_id = second.id

    assert first_lifecycle == "active"
    assert second_id == first_id
    assert notifications == [(analysis_id, 1), (analysis_id, 1)]
    with sessions.begin() as session:
        drained = request_observer_drain(
            session,
            analysis_id=analysis_id,
            attempt=1,
            notify=lambda _session, value, attempt: notifications.append((value, attempt)),
        )
        drained_lifecycle = drained.lifecycle_status
    assert drained_lifecycle == "draining"
    assert list_observer_work(sessions) == [(analysis_id, 1)]


def test_drain_before_step3_is_an_idempotent_noop_without_creating_state() -> None:
    sessions = make_sessionmaker()
    analysis_id = "WGS_20260830_010203_A1B2C3"
    add_run(sessions, analysis_id)

    with sessions.begin() as session:
        state = request_observer_drain(
            session,
            analysis_id=analysis_id,
            attempt=1,
            notify=lambda *_: (_ for _ in ()).throw(AssertionError("must not notify")),
        )

    assert state is None
    with sessions() as session:
        assert session.scalar(select(ObserverRunState)) is None


def test_idle_iteration_blocks_for_notification_without_ingesting() -> None:
    waits: list[float | None] = []
    ingested: list[tuple[str, int]] = []

    class Source:
        def wait(self, timeout: float | None):
            waits.append(timeout)
            return [("WGS_20260830_010203_A1B2C3", 1)]

    active = run_observer_iteration(
        active=set(),
        notification_source=Source(),
        ingest_fn=lambda analysis_id, attempt: ingested.append((analysis_id, attempt)),
        interval_seconds=5,
    )

    assert waits == [None]
    assert ingested == []
    assert active == {("WGS_20260830_010203_A1B2C3", 1)}


def test_four_active_attempts_are_ingested_by_exact_identity() -> None:
    keys = {
        (f"WGS_20260830_01020{index}_{index:06X}", 1)
        for index in range(1, 5)
    }
    ingested: list[tuple[str, int]] = []

    class Source:
        def wait(self, timeout: float | None):
            assert timeout == 5
            return []

    remaining = run_observer_iteration(
        active=keys,
        notification_source=Source(),
        ingest_fn=lambda analysis_id, attempt: (
            ingested.append((analysis_id, attempt))
            or {"lifecycle_status": "active", "events_ingested": 0, "errors": 0}
        ),
        interval_seconds=5,
    )

    assert set(ingested) == keys
    assert remaining == keys


def test_targeted_ingest_does_not_consume_another_active_attempt(tmp_path: Path) -> None:
    sessions = make_sessionmaker()
    first = "WGS_20260830_010203_A1B2C3"
    second = "WGS_20260830_010204_D4E5F6"
    add_run(sessions, first)
    add_run(sessions, second)
    for analysis_id in (first, second):
        with sessions.begin() as session:
            activate_observer(session, analysis_id=analysis_id, attempt=1, notify=lambda *_: None)
        raw = tmp_path / analysis_id / "attempt-1" / "rule-status" / "raw"
        raw.mkdir(parents=True)
        event = {
            "schema_version": "1",
            "event": "job_started",
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "run_label": f"{analysis_id}-a1",
            "attempt": "1",
            "role": "worker",
            "stream_id": "worker-a",
            "event_id": f"{analysis_id}:event-1",
            "rule_instance_id": f"{analysis_id}:rule-1",
            "rule_name": "mapping",
            "snakemake_jobid": "1",
        }
        (raw / "events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")

    result = ingest_observer_attempt_once(
        session_factory=sessions,
        evidence_root=tmp_path,
        analysis_id=first,
        attempt=1,
    )

    assert result["events_ingested"] == 1
    with sessions() as session:
        rows = session.scalars(select(RuleState)).all()
        assert len(rows) == 1
        assert rows[0].analysis_id == first
