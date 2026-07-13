from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.diagnostics_service import sync_airflow_status
from app.models import AnalysisRun, Base, IntakeDiscovery, Sample, SnakemakeRuleEvent


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def add_run(
    session,
    *,
    analysis_id: str,
    pipeline: str,
    status: str,
    params: dict,
    workdir: Path,
    sample_qc: str = "unknown",
    submitted_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> AnalysisRun:
    run = AnalysisRun(
        analysis_id=analysis_id,
        pipeline_name=pipeline,
        dag_id="bio_pgta" if pipeline == "pgta" else "bio_nipt_docker",
        dag_run_id=f"manual__{analysis_id}",
        mode="new",
        status=status,
        workdir=str(workdir),
        sample_sheet_path=str(workdir / "config" / "samples.selected.tsv"),
        params_json=params,
        submitted_at=submitted_at,
        started_at=submitted_at,
        ended_at=ended_at,
        pipeline_finished_at=ended_at if status == "success" else None,
    )
    session.add(run)
    session.add(Sample(analysis_id=analysis_id, sample_id=f"{analysis_id}_S1", status=status, qc_status=sample_qc))
    return run


def add_discovery(
    session,
    *,
    batch_id: str,
    analysis_id: str | None,
    ready_state: str = "observed",
    submit_state: str = "not_submitted",
    archived_at: datetime | None = None,
) -> None:
    session.add(
        IntakeDiscovery(
            pipeline_name="pgta",
            root_path="/data/pgta",
            batch_id=batch_id,
            fingerprint=f"fingerprint-{batch_id}",
            file_count=2,
            total_bytes=1024,
            ready_state=ready_state,
            submit_state=submit_state,
            analysis_id=analysis_id,
            last_seen_at=datetime.now(timezone.utc),
            archived_at=archived_at,
        )
    )


def test_intake_status_view_separates_pending_records_from_linked_history(monkeypatch, tmp_path) -> None:
    session_factory = make_test_sessionmaker()
    now = datetime.now(timezone.utc)
    with session_factory() as session:
        add_run(
            session,
            analysis_id="PGTA_LINKED_RUNNING",
            pipeline="pgta",
            status="running",
            params={"project_name": "Linked running", "target": "predict"},
            workdir=tmp_path / "running",
            submitted_at=now,
        )
        add_run(
            session,
            analysis_id="PGTA_LINKED_SUCCESS",
            pipeline="pgta",
            status="success",
            params={"project_name": "Linked success", "target": "predict"},
            workdir=tmp_path / "success",
            sample_qc="pass",
            submitted_at=now - timedelta(hours=1),
            ended_at=now,
        )
        add_discovery(session, batch_id="pending", analysis_id=None)
        add_discovery(session, batch_id="error", analysis_id=None, ready_state="error", submit_state="error")
        add_discovery(session, batch_id="linked-running", analysis_id="PGTA_LINKED_RUNNING", ready_state="ready", submit_state="submitted")
        add_discovery(
            session,
            batch_id="linked-success",
            analysis_id="PGTA_LINKED_SUCCESS",
            ready_state="ready",
            submit_state="submitted",
            archived_at=now,
        )
        session.commit()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)

    pending = client.get("/api/intake/status?lifecycle=all&view=pending&limit=10").json()
    history = client.get("/api/intake/status?lifecycle=all&view=history&limit=10").json()
    all_rows = client.get("/api/intake/status?lifecycle=all&view=all&limit=10").json()

    assert {item["batch_id"] for item in pending["items"]} == {"pending", "error"}
    assert {item["batch_id"] for item in history["items"]} == {"linked-running", "linked-success"}
    assert all_rows["total"] == 4


def test_dashboard_runs_exposes_run_source_batch_and_operator_qc_state(monkeypatch, tmp_path) -> None:
    session_factory = make_test_sessionmaker()
    now = datetime.now(timezone.utc)
    with session_factory() as session:
        add_run(
            session,
            analysis_id="NIPT_MANUAL_FAILED",
            pipeline="nipt_docker",
            status="failed",
            params={"project_name": "Manual failed", "run_mode": "full_run", "source_batch_id": "manual-batch"},
            workdir=tmp_path / "manual",
            submitted_at=now - timedelta(minutes=10),
            ended_at=now,
        )
        add_run(
            session,
            analysis_id="PGTA_INTAKE_RUNNING",
            pipeline="pgta",
            status="running",
            params={
                "project_name": "Intake running",
                "target": "predict",
                "source_batch_id": "params-batch",
                "intake_request_id": "manifest-batch",
            },
            workdir=tmp_path / "intake",
            submitted_at=now,
        )
        add_discovery(
            session,
            batch_id="manifest-batch",
            analysis_id="PGTA_INTAKE_RUNNING",
            ready_state="ready",
            submit_state="submitted",
        )
        session.commit()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: SimpleNamespace(list_task_instances=lambda *_: {"task_instances": []}))

    response = TestClient(main.app).get("/api/dashboard/runs?pipeline=all&limit=10&offset=0")

    assert response.status_code == 200
    rows = {item["analysis_id"]: item for item in response.json()["items"]}
    assert rows["NIPT_MANUAL_FAILED"]["run_source"] == "manual"
    assert rows["NIPT_MANUAL_FAILED"]["source_batch_id"] == "manual-batch"
    assert rows["NIPT_MANUAL_FAILED"]["qc_display_status"] == "unavailable"
    assert rows["PGTA_INTAKE_RUNNING"]["run_source"] == "intake"
    assert rows["PGTA_INTAKE_RUNNING"]["source_batch_id"] == "manifest-batch"
    assert rows["PGTA_INTAKE_RUNNING"]["qc_display_status"] == "pending"


class FailedAirflowClient:
    def get_dag_run(self, dag_id: str, dag_run_id: str) -> dict:
        return {
            "dag_id": dag_id,
            "dag_run_id": dag_run_id,
            "state": "failed",
            "start_date": "2026-07-13T14:54:58+00:00",
            "end_date": "2026-07-13T15:02:02+00:00",
        }

    def list_task_instances(self, dag_id: str, dag_run_id: str) -> dict:
        return {"task_instances": []}


def test_terminal_airflow_failure_cancels_only_stale_running_rule_events(tmp_path) -> None:
    session_factory = make_test_sessionmaker()
    workdir = tmp_path / "NIPT_FAILED"
    (workdir / "logs" / "events").mkdir(parents=True)
    with session_factory() as session:
        add_run(
            session,
            analysis_id="NIPT_FAILED",
            pipeline="nipt_docker",
            status="running",
            params={"project_name": "Failed NIPT", "run_mode": "full_run"},
            workdir=workdir,
            submitted_at=datetime.now(timezone.utc),
        )
        session.add_all(
            [
                SnakemakeRuleEvent(analysis_id="NIPT_FAILED", rule="map", sample_id="S1", snakemake_jobid="1", status="failed"),
                SnakemakeRuleEvent(analysis_id="NIPT_FAILED", rule="map", sample_id="S2", snakemake_jobid="2", status="running"),
                SnakemakeRuleEvent(analysis_id="NIPT_FAILED", rule="fastq_count", sample_id=None, snakemake_jobid="3", status="success"),
            ]
        )
        session.commit()

        sync_airflow_status(
            session=session,
            airflow_client=FailedAirflowClient(),
            analysis_id="NIPT_FAILED",
            settings=SimpleNamespace(container_shared_root=str(tmp_path)),
        )

        rows = {
            (row.rule, row.sample_id): row
            for row in session.scalars(select(SnakemakeRuleEvent).where(SnakemakeRuleEvent.analysis_id == "NIPT_FAILED"))
        }
        assert rows[("map", "S1")].status == "failed"
        assert rows[("map", "S2")].status == "canceled"
        assert rows[("map", "S2")].end_time is not None
        assert "parent workflow failed" in str(rows[("map", "S2")].message).lower()
        assert rows[("fastq_count", None)].status == "success"


def test_workflow_catalog_returns_live_pgta_predict_and_nipt_full_status(monkeypatch, tmp_path) -> None:
    session_factory = make_test_sessionmaker()
    now = datetime.now(timezone.utc)
    with session_factory() as session:
        add_run(
            session,
            analysis_id="PGTA_LIVE",
            pipeline="pgta",
            status="success",
            params={"project_name": "PGT-A live", "target": "predict", "runtime_profile_id": "pgta-s9-predict-v1"},
            workdir=tmp_path / "pgta",
            sample_qc="pass",
            submitted_at=now - timedelta(hours=1),
            ended_at=now - timedelta(minutes=30),
        )
        add_run(
            session,
            analysis_id="NIPT_LIVE",
            pipeline="nipt_docker",
            status="failed",
            params={"project_name": "NIPT live", "run_mode": "full_run", "runtime_profile_id": "niptpro-s9-full-v1"},
            workdir=tmp_path / "nipt",
            submitted_at=now - timedelta(minutes=20),
            ended_at=now,
        )
        session.add(SnakemakeRuleEvent(analysis_id="NIPT_LIVE", rule="map", sample_id="S1", status="failed"))
        session.commit()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    select_statements: list[str] = []
    event.listen(
        session_factory.kw["bind"],
        "before_cursor_execute",
        lambda _conn, _cursor, statement, _parameters, _context, _executemany: select_statements.append(statement)
        if statement.lstrip().upper().startswith("SELECT")
        else None,
    )

    response = TestClient(main.app).get("/api/workflows")

    assert response.status_code == 200
    items = {item["pipeline"]: item for item in response.json()["items"]}
    assert set(items) == {"pgta", "nipt_docker"}
    assert items["pgta"]["latest_run"]["analysis_id"] == "PGTA_LIVE"
    assert items["pgta"]["latest_run"]["status"] == "success"
    assert items["nipt_docker"]["latest_run"]["analysis_id"] == "NIPT_LIVE"
    assert items["nipt_docker"]["latest_run"]["status"] == "failed"
    assert any(stage["status"] == "failed" for stage in items["nipt_docker"]["stages"])
    assert len(select_statements) <= 4
