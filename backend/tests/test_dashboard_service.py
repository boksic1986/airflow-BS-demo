from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, IntakeDiscovery, QcMetric, Sample, SnakemakeRuleEvent


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def seed_dashboard_data(session_factory, tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    rows = [
        ("PGTA_RUNNING", "pgta", "running", now - timedelta(minutes=15), now - timedelta(minutes=14), None, "bio_pgta", "manual__PGTA_RUNNING", {"project_name": "PGT-A active", "target": "baseline_qc"}),
        ("PGTA_HISTORY", "pgta", "success", now - timedelta(hours=4), now - timedelta(hours=4), now - timedelta(hours=2), "bio_pgta", "manual__PGTA_HISTORY", {"project_name": "PGT-A historical baseline", "target": "baseline_qc"}),
        ("NIPT_SUCCESS", "nipt_docker", "success", now - timedelta(hours=1), now - timedelta(hours=1), now - timedelta(minutes=55), "bio_nipt_docker", "manual__NIPT_SUCCESS", {"project_name": "NIPT done", "run_mode": "mount_smoke"}),
        ("PGTA_FAILED", "pgta", "failed", now - timedelta(hours=2), now - timedelta(hours=2), now - timedelta(hours=1, minutes=50), "bio_pgta", "manual__PGTA_FAILED", {"project_name": "PGT-A failed", "target": "invalid_target"}),
        ("NIPT_CREATED", "nipt_docker", "created", now - timedelta(hours=3), None, None, "bio_nipt_docker", None, {"project_name": "NIPT created", "run_mode": "mount_smoke"}),
    ]
    with session_factory() as session:
        for analysis_id, pipeline, status, created_at, started_at, ended_at, dag_id, dag_run_id, params in rows:
            workdir = tmp_path / analysis_id
            session.add(
                AnalysisRun(
                    analysis_id=analysis_id,
                    pipeline_name=pipeline,
                    dag_id=dag_id,
                    dag_run_id=dag_run_id,
                    mode="new",
                    status=status,
                    sample_sheet_path=str(workdir / "config" / "samples.selected.tsv"),
                    workdir=str(workdir),
                    params_json=params,
                    created_at=created_at,
                    started_at=started_at,
                    ended_at=ended_at,
                    error_summary="Missing rule" if status == "failed" else None,
                )
            )
            sample_count = 2 if analysis_id in {"PGTA_RUNNING", "PGTA_HISTORY", "NIPT_SUCCESS"} else 1
            for index in range(sample_count):
                session.add(
                    Sample(
                        analysis_id=analysis_id,
                        sample_id=f"{analysis_id}_S{index + 1}",
                        status="pending" if status == "created" else status,
                        qc_status="fail" if analysis_id == "PGTA_FAILED" else ("unknown" if status in {"created", "running"} else "pass"),
                    )
                )
        session.add(QcMetric(analysis_id="PGTA_FAILED", sample_id="PGTA_FAILED_S1", metric_name="qc", status="fail"))
        session.add(SnakemakeRuleEvent(analysis_id="PGTA_RUNNING", rule="fastp", status="success", snakemake_jobid="1"))
        session.add(SnakemakeRuleEvent(analysis_id="PGTA_RUNNING", rule="baseline_bam_uniformity_qc", status="running", snakemake_jobid="2"))
        session.add(SnakemakeRuleEvent(analysis_id="PGTA_FAILED", rule="mapping", status="failed", snakemake_jobid="3", message="mapping failed"))
        session.add(
            IntakeDiscovery(
                pipeline_name="pgta",
                root_path="/data/project/CNV/PGT-A/rawdata",
                batch_id="observed-batch",
                fingerprint="abc",
                file_count=2,
                total_bytes=200,
                ready_state="observed",
                submit_state="bootstrap",
                last_seen_at=now,
            )
        )
        session.commit()


class FakeAirflowClient:
    def __init__(self) -> None:
        self.task_calls: list[tuple[str, str]] = []

    def list_task_instances(self, dag_id: str, dag_run_id: str) -> dict:
        self.task_calls.append((dag_id, dag_run_id))
        if dag_run_id == "manual__PGTA_RUNNING":
            return {
                "task_instances": [
                    {"task_id": "validate_request", "state": "success"},
                    {"task_id": "prepare_pgta_config", "state": "success"},
                    {"task_id": "run_pgta_target", "state": "running"},
                ]
            }
        return {"task_instances": [{"task_id": "validate_request", "state": "success"}]}


def install_dashboard_fixtures(monkeypatch, session_factory, airflow_client) -> None:
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: airflow_client)


def test_dashboard_overview_aggregates_pipeline_status_without_per_run_airflow_calls(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    seed_dashboard_data(session_factory, tmp_path)
    airflow = FakeAirflowClient()
    install_dashboard_fixtures(monkeypatch, session_factory, airflow)
    client = TestClient(main.app)

    response = client.get("/api/dashboard/overview?pipeline=all&period=7d")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pipeline"] == "all"
    assert payload["totals"]["runs"] == 5
    assert payload["totals"]["running"] == 1
    assert payload["totals"]["failed"] == 1
    assert payload["status_distribution"]["success"] == 2
    assert payload["pipeline_breakdown"]["pgta"]["runs"] == 3
    assert payload["pipeline_breakdown"]["nipt_docker"]["runs"] == 2
    assert payload["qc_summary"]["fail"] == 1
    assert payload["sample_summary"] == {
        "total": 8,
        "running": 2,
        "workflow_failed": 1,
        "qc_failed": 1,
        "completed": 4,
    }
    assert payload["sample_trend"][0]["date"]
    assert payload["sample_trend"][0]["total"] >= 1
    assert payload["intake_summary"]["bootstrap"] == 1
    assert payload["failure_summary"][0]["analysis_id"] == "PGTA_FAILED"
    assert airflow.task_calls == []


def test_dashboard_runs_returns_paginated_tracker_rows_with_current_steps(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    seed_dashboard_data(session_factory, tmp_path)
    airflow = FakeAirflowClient()
    install_dashboard_fixtures(monkeypatch, session_factory, airflow)
    client = TestClient(main.app)

    response = client.get("/api/dashboard/runs?pipeline=all&limit=2&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 5
    assert len(payload["items"]) == 2
    first = payload["items"][0]
    assert first["analysis_id"] == "PGTA_RUNNING"
    assert first["project_name"] == "PGT-A active"
    assert first["percent"] == 52
    assert first["current_airflow_task"] == "run_pgta_target"
    assert first["current_pipeline_rule"] == "baseline_bam_uniformity_qc"
    assert first["current_stage_label"] == "Baseline BAM uniformity QC"
    assert first["current_stage_source"] == "Snakemake rule event"
    assert first["elapsed_seconds"] is not None
    assert first["average_duration_seconds"] == 7200
    assert first["estimated_remaining_seconds"] is not None
    assert first["estimated_finish_at"] is not None
    assert first["progress_source"] == "snakemake_events"
    assert first["not_in_airflow"] is False
    assert airflow.task_calls == [("bio_pgta", "manual__PGTA_RUNNING"), ("bio_pgta", "manual__PGTA_FAILED")]

    second_page = client.get("/api/dashboard/runs?pipeline=all&limit=2&offset=2").json()
    assert len(second_page["items"]) == 2
    assert second_page["items"][0]["analysis_id"] != first["analysis_id"]
    assert airflow.task_calls == [("bio_pgta", "manual__PGTA_RUNNING"), ("bio_pgta", "manual__PGTA_FAILED")]


def test_dashboard_runs_filters_pipeline_status_and_keyword(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    seed_dashboard_data(session_factory, tmp_path)
    airflow = FakeAirflowClient()
    install_dashboard_fixtures(monkeypatch, session_factory, airflow)
    client = TestClient(main.app)

    response = client.get("/api/dashboard/runs?pipeline=pgta&status=failed&keyword=failed&limit=10&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["analysis_id"] == "PGTA_FAILED"
    assert payload["items"][0]["current_pipeline_rule"] == "mapping"
    assert payload["items"][0]["current_stage_label"] == "Mapping reads"
    assert payload["items"][0]["percent"] >= 15
