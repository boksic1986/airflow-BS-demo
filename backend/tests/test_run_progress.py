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
from app.rule_event_service import finalize_dry_run_rule_events


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


def insert_wgs_run(
    session_factory,
    tmp_path,
    *,
    analysis_id: str = "WGS_20260714_120000_PROGRESS",
    status: str = "running",
    dag_run_id: str = "manual__WGS_20260714_120000_PROGRESS",
) -> str:
    workdir = tmp_path / "shared" / "runs" / analysis_id
    workdir.mkdir(parents=True)
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                dag_run_id=dag_run_id,
                mode="new",
                status=status,
                workdir=str(workdir),
                params_json={"stage": "full", "project_name": "WGS progress"},
            )
        )
        session.commit()
    return analysis_id


def test_finalize_dry_run_rule_events_marks_planned_jobs_skipped(tmp_path) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_wgs_run(session_factory, tmp_path, status="success")
    finished_at = datetime(2026, 7, 15, 6, 22, 36, tzinfo=timezone.utc)
    with session_factory() as session:
        session.add_all(
            [
                SnakemakeRuleEvent(
                    analysis_id=analysis_id,
                    rule="mapping",
                    sample_id="WGS-01",
                    snakemake_jobid="1",
                    status="running",
                ),
                SnakemakeRuleEvent(
                    analysis_id=analysis_id,
                    rule="cleanFastq",
                    sample_id="WGS-01",
                    snakemake_jobid="2",
                    status="skipped",
                ),
            ]
        )
        session.commit()

        updated = finalize_dry_run_rule_events(
            session=session,
            analysis_id=analysis_id,
            timestamp=finished_at,
        )
        session.commit()
        rows = session.scalars(
            select(SnakemakeRuleEvent)
            .where(SnakemakeRuleEvent.analysis_id == analysis_id)
            .order_by(SnakemakeRuleEvent.rule)
        ).all()

    assert updated == 1
    assert [row.status for row in rows] == ["skipped", "skipped"]
    assert rows[1].end_time.replace(tzinfo=timezone.utc) == finished_at
    assert "dry-run planned" in str(rows[1].message).lower()


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


def test_wgs_progress_does_not_use_airflow_task_count_as_percentage(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_wgs_run(session_factory, tmp_path)
    fake_airflow = FakeAirflowClient(
        tasks=[
            {"task_id": "validate_request", "state": "success", "operator": "PythonOperator"},
            {"task_id": "prepare_wgs_run", "state": "success", "operator": "SSHOperator"},
            {"task_id": "wgs_pipeline.pre_calling", "state": "success", "operator": "SSHOperator"},
            {"task_id": "wgs_pipeline.variant_analysis", "state": "running", "operator": "SSHOperator"},
        ]
    )
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)

    response = TestClient(main.app).get(f"/api/runs/{analysis_id}/progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["percent"] is None
    assert payload["current_step"] == "wgs_pipeline.variant_analysis"
    assert payload["progress_source"] == "stage-status-unavailable"
    assert [task["task_id"] for task in payload["airflow_tasks"]] == [
        "validate_request",
        "prepare_wgs_run",
        "wgs_pipeline.pre_calling",
        "wgs_pipeline.variant_analysis",
    ]


def test_wgs_progress_uses_the_same_pipeline_specific_phase_as_rules(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_wgs_run(session_factory, tmp_path)
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    with session_factory() as session:
        session.add(
            SnakemakeRuleEvent(
                analysis_id=analysis_id,
                rule="mapping",
                sample_id="W1",
                status="running",
                snakemake_jobid="1",
                start_time=now,
                updated_at=now,
            )
        )
        session.commit()
    fake_airflow = FakeAirflowClient(tasks=[{"task_id": "wgs_pipeline.pre_calling", "state": "running"}])
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)

    response = TestClient(main.app).get(f"/api/runs/{analysis_id}/progress")

    assert response.status_code == 200
    assert response.json()["current_rule"] == "mapping"
    assert response.json()["current_phase"] == "Pre-calling"
    assert response.json()["rule_events"][0]["phase"] == "Pre-calling"


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


def test_run_progress_prefers_latest_sample_rule_over_stage_wrapper(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(
        session_factory,
        tmp_path,
        status="running",
        dag_run_id="manual__PGTA_20260711_SAMPLE_RULE",
    )
    with session_factory() as session:
        session.add_all(
            [
                SnakemakeRuleEvent(
                    analysis_id=analysis_id,
                    rule="mapping",
                    status="running",
                    start_time=datetime(2026, 7, 11, 6, 0, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 11, 6, 0, tzinfo=timezone.utc),
                ),
                SnakemakeRuleEvent(
                    analysis_id=analysis_id,
                    rule="fastp_bwa",
                    sample_id="PGTA-DEMO-01",
                    status="running",
                    snakemake_jobid="1",
                    start_time=datetime(2026, 7, 11, 6, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 11, 6, 1, tzinfo=timezone.utc),
                ),
            ]
        )
        session.commit()
    fake_airflow = FakeAirflowClient(
        tasks=[{"task_id": "pgta_predict.run_pgta_mapping", "state": "running"}]
    )
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/progress")

    assert response.status_code == 200
    assert response.json()["current_step"] == "fastp_bwa"


def test_nipt_progress_exposes_current_phase_rule_sample_and_counts(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = "NIPT_20260711_120000_PROGRESS"
    workdir = tmp_path / "shared" / "runs" / analysis_id
    (workdir / "config").mkdir(parents=True)
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="nipt_docker",
                dag_id="bio_nipt_docker",
                dag_run_id=f"manual__{analysis_id}",
                mode="new",
                status="running",
                sample_sheet_path=str(workdir / "config" / "samples.selected.tsv"),
                workdir=str(workdir),
                params_json={"run_mode": "full_run", "project_name": "NIPT S9 progress"},
            )
        )
        session.add_all(
            [
                SnakemakeRuleEvent(
                    analysis_id=analysis_id,
                    rule="map",
                    sample_id="S1",
                    status="success",
                    snakemake_jobid="1",
                    start_time=datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc),
                    end_time=datetime(2026, 7, 11, 12, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 11, 12, 1, tzinfo=timezone.utc),
                ),
                SnakemakeRuleEvent(
                    analysis_id=analysis_id,
                    rule="aneuscreen_predict",
                    sample_id="S2",
                    status="running",
                    snakemake_jobid="2",
                    start_time=datetime(2026, 7, 11, 12, 2, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 11, 12, 2, tzinfo=timezone.utc),
                ),
            ]
        )
        session.commit()
    fake_airflow = FakeAirflowClient(tasks=[{"task_id": "run_nipt_docker", "state": "running"}])
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_phase"] == "T21 classifier"
    assert payload["current_rule"] == "aneuscreen_predict"
    assert payload["current_sample"] == "S2"
    assert payload["rule_counts"] == {"total": 2, "running": 1, "success": 1, "failed": 0, "terminal": 1}


def test_nipt_progress_does_not_fall_below_persisted_event_progress(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = "NIPT_20260711_120000_MONOTONIC"
    workdir = tmp_path / "shared" / "runs" / analysis_id
    (workdir / "config").mkdir(parents=True)
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="nipt_docker",
                dag_id="bio_nipt_docker",
                dag_run_id=f"manual__{analysis_id}",
                mode="new",
                status="running",
                progress_percent=85,
                sample_sheet_path=str(workdir / "config" / "samples.selected.tsv"),
                workdir=str(workdir),
                params_json={"run_mode": "full_run"},
            )
        )
        session.add_all(
            [
                SnakemakeRuleEvent(analysis_id=analysis_id, rule="map", sample_id="S1", status="success", snakemake_jobid="1"),
                SnakemakeRuleEvent(analysis_id=analysis_id, rule="predict", sample_id="S2", status="running", snakemake_jobid="2"),
            ]
        )
        session.commit()
    fake_airflow = FakeAirflowClient(tasks=[{"task_id": "run_nipt_docker", "state": "running"}])
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)

    response = TestClient(main.app).get(f"/api/runs/{analysis_id}/progress")

    assert response.status_code == 200
    assert response.json()["percent"] == 85


def test_terminal_success_progress_reports_completed_instead_of_last_rule(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = "NIPT_20260711_153000_COMPLETE"
    workdir = tmp_path / "shared" / "runs" / analysis_id
    (workdir / "config").mkdir(parents=True)
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="nipt_docker",
                dag_id="bio_nipt_docker",
                dag_run_id=f"manual__{analysis_id}",
                mode="new",
                status="success",
                sample_sheet_path=str(workdir / "config" / "samples.selected.tsv"),
                workdir=str(workdir),
                params_json={"run_mode": "full_run"},
            )
        )
        session.add(
            SnakemakeRuleEvent(
                analysis_id=analysis_id,
                rule="all",
                status="success",
                snakemake_jobid="0",
                updated_at=datetime(2026, 7, 11, 15, 36, 18, tzinfo=timezone.utc),
            )
        )
        session.commit()
    fake_airflow = FakeAirflowClient(
        state="success",
        tasks=[{"task_id": "collect_nipt_artifacts", "state": "success"}],
    )
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)

    response = TestClient(main.app).get(f"/api/runs/{analysis_id}/progress")

    assert response.status_code == 200
    assert response.json()["percent"] == 100
    assert response.json()["current_step"] == "Workflow complete"


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
