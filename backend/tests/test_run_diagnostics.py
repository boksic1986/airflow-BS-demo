from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, QcMetric, Sample


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def insert_submitted_run(session_factory, tmp_path, *, analysis_id: str = "PGTA_20260703_020000_TEST01") -> str:
    workdir = tmp_path / "shared" / "runs" / analysis_id
    logs_dir = workdir / "logs"
    config_dir = workdir / "config"
    logs_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    (logs_dir / "snakemake.stdout.log").write_text("stdout line 1\nstdout line 2\n", encoding="utf-8")
    (logs_dir / "snakemake.stderr.log").write_text("stderr line 1\nstderr line 2\n", encoding="utf-8")
    (logs_dir / "run_metadata.tsv").write_text("key\tvalue\ngenerated_utc\t2026-07-03T00:00:00Z\n", encoding="utf-8")
    (workdir / "config.yaml").write_text("pipeline:\n  targets:\n    - metadata\n", encoding="utf-8")
    (config_dir / "pgta_metadata_config.json").write_text('{"target":"metadata"}\n', encoding="utf-8")
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="pgta",
                dag_id="bio_pgta",
                dag_run_id=f"manual__{analysis_id}",
                mode="new",
                status="submitted",
                sample_sheet_path=str(config_dir / "samples.selected.tsv"),
                workdir=str(workdir),
                params_json={"target": "metadata"},
                email_to="demo@example.com",
            )
        )
        session.commit()
    return analysis_id


def insert_wes_submitted_run(session_factory, tmp_path, *, analysis_id: str = "WES_20260706_010000_QC01") -> str:
    workdir = tmp_path / "shared" / "runs" / analysis_id
    reports_dir = workdir / "reports"
    logs_dir = workdir / "logs"
    config_dir = workdir / "config"
    reports_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    (logs_dir / "snakemake.stdout.log").write_text("wes stdout\n", encoding="utf-8")
    (logs_dir / "snakemake.stderr.log").write_text("", encoding="utf-8")
    (reports_dir / "final_summary.tsv").write_text(
        "sample_id\tstatus\nS001\tmock_success\nS002\tmock_success\n",
        encoding="utf-8",
    )
    (reports_dir / "qc_summary.tsv").write_text(
        "\n".join(
            [
                "sample_id\tmetric_name\tmetric_value\tmetric_numeric\tthreshold\tstatus",
                "S001\tworkflow_status\tmock_success\t\tmock_success\tpass",
                "S001\tmock_mean_depth\t100\t100\t>=80\tpass",
                "S001\tmock_pct_20x\t0.95\t0.95\t>=0.90\tpass",
                "S002\tworkflow_status\tmock_success\t\tmock_success\tpass",
                "S002\tmock_mean_depth\t100\t100\t>=80\tpass",
                "S002\tmock_pct_20x\t0.95\t0.95\t>=0.90\tpass",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wes_qsub",
                dag_id="bio_wes_qsub",
                dag_run_id=f"manual__{analysis_id}",
                mode="new",
                status="submitted",
                sample_sheet_path=str(config_dir / "samples.selected.tsv"),
                workdir=str(workdir),
                params_json={"target": "final_summary"},
            )
        )
        for sample_id in ("S001", "S002"):
            session.add(
                Sample(
                    analysis_id=analysis_id,
                    sample_id=sample_id,
                    fq1=f"pipelines/wes/mock_data/{sample_id}.input.txt",
                    status="pending",
                    qc_status="unknown",
                    metadata_json={"input_mode": "mock_wes"},
                )
            )
        session.commit()
    return analysis_id


class FakeAirflowClient:
    def __init__(self, state: str) -> None:
        self.state = state
        self.calls: list[dict] = []

    def get_dag_run(self, dag_id: str, dag_run_id: str) -> dict:
        self.calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id})
        return {
            "dag_id": dag_id,
            "dag_run_id": dag_run_id,
            "state": self.state,
            "start_date": "2026-07-03T00:00:00+00:00",
            "end_date": "2026-07-03T00:05:00+00:00",
        }


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


def test_sync_airflow_success_updates_run_status(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_submitted_run(session_factory, tmp_path)
    fake_airflow = FakeAirflowClient("success")
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/sync-airflow")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["error_summary"] is None
    assert fake_airflow.calls == [{"dag_id": "bio_pgta", "dag_run_id": f"manual__{analysis_id}"}]
    with session_factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    assert run.status == "success"
    assert run.ended_at is not None


def test_sync_airflow_failed_writes_error_summary_from_stderr(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_submitted_run(session_factory, tmp_path, analysis_id="PGTA_20260703_020000_FAIL01")
    fake_airflow = FakeAirflowClient("failed")
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/sync-airflow")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert "stderr line 2" in payload["error_summary"]
    assert "snakemake.stderr.log" in payload["error_summary"]
    with session_factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    assert run.status == "failed"
    assert run.error_summary == payload["error_summary"]
    assert run.ended_at is not None


def test_get_run_log_tails_known_pgta_streams(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_submitted_run(session_factory, tmp_path)
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/logs?stream=stdout&tail=1")

    assert response.status_code == 200
    assert response.json() == {
        "path": str(tmp_path / "shared" / "runs" / analysis_id / "logs" / "snakemake.stdout.log"),
        "stream": "stdout",
        "truncated": True,
        "lines": ["stdout line 2"],
    }


def test_get_run_log_returns_404_for_missing_file(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_submitted_run(session_factory, tmp_path)
    (tmp_path / "shared" / "runs" / analysis_id / "logs" / "snakemake.stderr.log").unlink()
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/logs?stream=stderr")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "LOG_NOT_FOUND"


def test_get_run_log_rejects_workdir_outside_shared_root(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = "PGTA_20260703_020000_ESCAPE"
    outside = tmp_path / "outside" / analysis_id
    (outside / "logs").mkdir(parents=True)
    (outside / "logs" / "snakemake.stdout.log").write_text("secret\n", encoding="utf-8")
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="pgta",
                dag_id="bio_pgta",
                dag_run_id=f"manual__{analysis_id}",
                mode="new",
                status="submitted",
                workdir=str(outside),
                params_json={"target": "metadata"},
            )
        )
        session.commit()
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/logs?stream=stdout")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_RUN_PATH"


def test_list_pgta_artifacts_discovers_existing_files(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_submitted_run(session_factory, tmp_path)
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/artifacts")

    assert response.status_code == 200
    items = response.json()["items"]
    keys = {item["key"] for item in items}
    assert {
        "run_metadata",
        "snakemake_stdout",
        "snakemake_stderr",
        "pgta_config_yaml",
        "pgta_metadata_config",
    } <= keys
    metadata = next(item for item in items if item["key"] == "run_metadata")
    assert metadata["type"] == "pgta_metadata"
    assert metadata["size_bytes"] > 0
    assert metadata["url"] == f"/api/runs/{analysis_id}/logs?stream=metadata"


def test_sync_airflow_success_imports_wes_qc_metrics_idempotently(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_wes_submitted_run(session_factory, tmp_path)
    fake_airflow = FakeAirflowClient("success")
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    first = client.post(f"/api/runs/{analysis_id}/actions/sync-airflow")
    second = client.post(f"/api/runs/{analysis_id}/actions/sync-airflow")

    assert first.status_code == 200
    assert second.status_code == 200
    with session_factory() as session:
        metrics = session.scalars(select(QcMetric).where(QcMetric.analysis_id == analysis_id)).all()
        samples = session.scalars(select(Sample).where(Sample.analysis_id == analysis_id).order_by(Sample.sample_id)).all()
    assert len(metrics) == 6
    assert {(metric.sample_id, metric.metric_name, metric.status) for metric in metrics} >= {
        ("S001", "mock_mean_depth", "pass"),
        ("S001", "mock_pct_20x", "pass"),
        ("S002", "workflow_status", "pass"),
    }
    assert [sample.qc_status for sample in samples] == ["pass", "pass"]


def test_get_run_qc_returns_summary_and_metric_rows(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_wes_submitted_run(session_factory, tmp_path)
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", FakeAirflowClient("success"))
    client = TestClient(main.app)

    client.post(f"/api/runs/{analysis_id}/actions/sync-airflow")
    response = client.get(f"/api/runs/{analysis_id}/qc")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"pass": 6, "warn": 0, "fail": 0, "unknown": 0}
    assert payload["items"][0]["sample_id"] == "S001"
    assert {item["metric_name"] for item in payload["items"]} >= {"workflow_status", "mock_mean_depth", "mock_pct_20x"}
    depth = next(item for item in payload["items"] if item["metric_name"] == "mock_mean_depth")
    assert depth["metric_value"] == "100"
    assert depth["metric_numeric"] == 100.0
    assert depth["threshold"] == ">=80"
    assert depth["status"] == "pass"


def test_list_wes_artifacts_discovers_qc_summary(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_wes_submitted_run(session_factory, tmp_path)
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/artifacts")

    assert response.status_code == 200
    items = response.json()["items"]
    qc_summary = next(item for item in items if item["key"] == "wes_qc_summary")
    assert qc_summary["type"] == "qc_tsv"
    assert qc_summary["label"] == "WES mock QC summary"
    assert qc_summary["path"].endswith("reports/qc_summary.tsv")
