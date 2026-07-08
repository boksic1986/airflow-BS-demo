from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.diagnostics_service import sync_airflow_status
from app.models import AnalysisRun, Base, SnakemakeRuleEvent


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def insert_pgta_run(
    session_factory,
    tmp_path,
    *,
    analysis_id: str = "PGTA_20260708_120000_PROGRESS",
    status: str = "submitted",
    dag_run_id: str | None = None,
) -> str:
    workdir = tmp_path / "shared" / "runs" / analysis_id
    (workdir / "logs" / "events").mkdir(parents=True)
    (workdir / "logs").mkdir(exist_ok=True)
    (workdir / "logs" / "snakemake.stderr.log").write_text("", encoding="utf-8")
    (workdir / "config").mkdir(exist_ok=True)
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="pgta",
                dag_id="bio_pgta",
                dag_run_id=dag_run_id,
                mode="new",
                status=status,
                sample_sheet_path=str(workdir / "config" / "samples.selected.tsv"),
                workdir=str(workdir),
                params_json={"target": "metadata", "project_name": "Progress smoke"},
            )
        )
        session.commit()
    return analysis_id


class FakeAirflowClient:
    def __init__(self, *, state: str = "running", tasks: list[dict] | None = None) -> None:
        self.state = state
        self.tasks = tasks or []
        self.dag_run_calls: list[tuple[str, str]] = []
        self.task_calls: list[tuple[str, str]] = []

    def get_dag_run(self, dag_id: str, dag_run_id: str) -> dict:
        self.dag_run_calls.append((dag_id, dag_run_id))
        return {
            "dag_id": dag_id,
            "dag_run_id": dag_run_id,
            "state": self.state,
            "start_date": "2026-07-08T12:00:00+00:00",
            "end_date": "2026-07-08T12:10:00+00:00" if self.state in {"success", "failed"} else None,
        }

    def list_task_instances(self, dag_id: str, dag_run_id: str) -> dict:
        self.task_calls.append((dag_id, dag_run_id))
        return {"task_instances": self.tasks, "total_entries": len(self.tasks)}


def install_app_fixtures(monkeypatch, session_factory, shared_root, airflow_client=None) -> None:
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            container_shared_root=str(shared_root),
            airflow_base_url="http://airflow-api-server:8080",
        ),
    )
    if airflow_client is not None:
        monkeypatch.setattr(main, "get_airflow_client", lambda: airflow_client)


def test_run_progress_created_run_is_not_in_airflow(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(session_factory, tmp_path, status="created", dag_run_id=None)
    fake_airflow = FakeAirflowClient()
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["percent"] == 0
    assert payload["current_step"] == "Created only"
    assert payload["current_source"] == "backend"
    assert payload["not_in_airflow"] is True
    assert payload["progress_source"] == "estimate"
    assert payload["airflow_tasks"] == []
    assert fake_airflow.task_calls == []


def test_run_progress_uses_airflow_task_instances(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(
        session_factory,
        tmp_path,
        status="running",
        dag_run_id="manual__PGTA_20260708_120000_PROGRESS",
    )
    fake_airflow = FakeAirflowClient(
        tasks=[
            {
                "task_id": "validate_request",
                "state": "success",
                "start_date": "2026-07-08T12:00:00+00:00",
                "end_date": "2026-07-08T12:00:01+00:00",
                "duration": 1.0,
                "try_number": 1,
                "operator": "PythonOperator",
            },
            {
                "task_id": "prepare_pgta_config",
                "state": "success",
                "start_date": "2026-07-08T12:00:01+00:00",
                "end_date": "2026-07-08T12:00:03+00:00",
                "duration": 2.0,
                "try_number": 1,
                "operator": "PythonOperator",
            },
            {
                "task_id": "run_pgta_target",
                "state": "running",
                "start_date": "2026-07-08T12:00:03+00:00",
                "end_date": None,
                "duration": None,
                "try_number": 1,
                "operator": "PythonOperator",
            },
        ]
    )
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["percent"] == 10
    assert payload["current_step"] == "run_pgta_target"
    assert payload["current_source"] == "airflow_task_instances"
    assert payload["progress_source"] == "airflow_task_instances"
    assert payload["note"] == "waiting for pipeline events"
    assert [task["task_id"] for task in payload["airflow_tasks"]] == [
        "validate_request",
        "prepare_pgta_config",
        "run_pgta_target",
    ]
    assert fake_airflow.task_calls == [("bio_pgta", "manual__PGTA_20260708_120000_PROGRESS")]


def test_run_progress_uses_pgta_staged_airflow_tasks(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(
        session_factory,
        tmp_path,
        status="running",
        dag_run_id="manual__PGTA_20260708_120000_PROGRESS",
    )
    fake_airflow = FakeAirflowClient(
        tasks=[
            {"task_id": "validate_request", "state": "success"},
            {"task_id": "prepare_pgta_config", "state": "success"},
            {"task_id": "choose_pgta_path", "state": "success"},
            {"task_id": "pgta_pipeline.run_pgta_mapping", "state": "success"},
            {"task_id": "pgta_pipeline.run_pgta_metadata", "state": "running"},
        ]
    )
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["percent"] == 55
    assert payload["current_step"] == "pgta_pipeline.run_pgta_metadata"
    assert payload["progress_source"] == "airflow_task_instances"
    assert [task["task_id"] for task in payload["airflow_tasks"]] == [
        "validate_request",
        "prepare_pgta_config",
        "choose_pgta_path",
        "pgta_pipeline.run_pgta_mapping",
        "pgta_pipeline.run_pgta_metadata",
    ]


def test_run_progress_refines_running_airflow_task_with_rule_events(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(
        session_factory,
        tmp_path,
        status="running",
        dag_run_id="manual__PGTA_20260708_120000_PROGRESS",
    )
    with session_factory() as session:
        session.add(
            SnakemakeRuleEvent(
                analysis_id=analysis_id,
                rule="fastp",
                status="success",
                snakemake_jobid="1",
                start_time=datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 7, 8, 12, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 7, 8, 12, 1, tzinfo=timezone.utc),
            )
        )
        session.add(
            SnakemakeRuleEvent(
                analysis_id=analysis_id,
                rule="baseline_bam_uniformity_qc",
                status="running",
                snakemake_jobid="2",
                start_time=datetime(2026, 7, 8, 12, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 7, 8, 12, 1, tzinfo=timezone.utc),
            )
        )
        session.commit()
    fake_airflow = FakeAirflowClient(
        tasks=[
            {"task_id": "validate_request", "state": "success"},
            {"task_id": "prepare_pgta_config", "state": "success"},
            {"task_id": "run_pgta_target", "state": "running"},
        ]
    )
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["progress_source"] == "snakemake_events"
    assert payload["current_source"] == "snakemake_events"
    assert payload["current_step"] == "baseline_bam_uniformity_qc"
    assert payload["percent"] == 52
    assert [event["rule"] for event in payload["rule_events"]] == ["fastp", "baseline_bam_uniformity_qc"]


def test_sync_airflow_imports_events_jsonl_idempotently(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(
        session_factory,
        tmp_path,
        status="submitted",
        dag_run_id="manual__PGTA_20260708_120000_PROGRESS",
    )
    events_path = tmp_path / "shared" / "runs" / analysis_id / "logs" / "events" / "snakemake_events.jsonl"
    events_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "analysis_id": analysis_id,
                        "event": "job_started",
                        "rule": "metadata",
                        "snakemake_jobid": "1",
                        "status": "running",
                        "timestamp": "2026-07-08T12:00:00+00:00",
                    }
                ),
                json.dumps(
                    {
                        "analysis_id": analysis_id,
                        "event": "job_finished",
                        "rule": "metadata",
                        "snakemake_jobid": "1",
                        "status": "success",
                        "return_code": 0,
                        "timestamp": "2026-07-08T12:00:05+00:00",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_airflow = FakeAirflowClient(state="success")
    settings = SimpleNamespace(container_shared_root=str(tmp_path / "shared"))

    with session_factory() as session:
        sync_airflow_status(
            session=session,
            airflow_client=fake_airflow,
            analysis_id=analysis_id,
            settings=settings,
        )
        sync_airflow_status(
            session=session,
            airflow_client=fake_airflow,
            analysis_id=analysis_id,
            settings=settings,
        )
        events = session.scalars(select(SnakemakeRuleEvent).where(SnakemakeRuleEvent.analysis_id == analysis_id)).all()

    assert len(events) == 1
    assert events[0].rule == "metadata"
    assert events[0].status == "success"
    assert events[0].return_code == 0
