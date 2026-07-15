from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, QcMetric, Sample, SnakemakeRuleEvent


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
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="G1",
                fq1="/data/project/CNV/PGT-A/rawdata/G1_R1.fastq.gz",
                fq2="/data/project/CNV/PGT-A/rawdata/G1_R2.fastq.gz",
                status="pending",
                qc_status="unknown",
                metadata_json={"input_mode": "server_path_scan"},
            )
        )
        session.commit()
    return analysis_id


def insert_pgta_baseline_submitted_run(session_factory, tmp_path, *, analysis_id: str = "PGTA_20260706_020000_BASE01") -> str:
    workdir = tmp_path / "shared" / "runs" / analysis_id
    baseline_dir = workdir / "qc" / "baseline"
    logs_dir = workdir / "logs"
    config_dir = workdir / "config"
    baseline_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    (logs_dir / "snakemake.stdout.log").write_text("baseline stdout\n", encoding="utf-8")
    (logs_dir / "snakemake.stderr.log").write_text("", encoding="utf-8")
    (logs_dir / "run_metadata.tsv").write_text("key\tvalue\ntarget\tbaseline_qc\n", encoding="utf-8")
    (baseline_dir / "baseline_qc_summary.tsv").write_text(
        "\n".join(
            [
                "sample_id\tbin_size\tqc_decision\tqc_reason\tmapped_fragments\tusable_bins\tzero_bin_fraction\tbin_cv\tadjacent_diff_mad\tgini_coefficient\tpearson_r\tspearman_r\tmedian_abs_z\toutlier_frac_abs_z_gt_3\toutlier_frac_abs_z_gt_5\tgc_fraction_mean\tgc_signal_pearson_r\tgc_signal_spearman_r\tgc_signal_slope\ttarget_bam\tsource_tsv",
                "G1\t100000\tPASS\tok\t123456\t25000\t0.01\t0.12\t0.03\t0.21\t0.95\t0.94\t0.45\t0.02\t0.01\t0.41\t0.02\t0.01\t0.001\t/data/G1.sorted.bam\t/data/G1.qc.tsv",
                "G2\t100000\tWARN\treview\t120000\t24900\t0.03\t0.18\t0.05\t0.25\t0.90\t0.89\t0.70\t0.04\t0.02\t0.42\t0.03\t0.02\t0.002\t/data/G2.sorted.bam\t/data/G2.qc.tsv",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "baseline_qc_pass_samples.txt").write_text("G1\n", encoding="utf-8")
    (baseline_dir / "baseline_qc_report.md").write_text("# baseline QC\n", encoding="utf-8")
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
                params_json={"target": "baseline_qc", "selected_count": 2},
            )
        )
        for sample_id in ("G1", "G2"):
            session.add(
                Sample(
                    analysis_id=analysis_id,
                    sample_id=sample_id,
                    fq1=f"/data/project/CNV/PGT-A/rawdata/{sample_id}_R1.fastq.gz",
                    fq2=f"/data/project/CNV/PGT-A/rawdata/{sample_id}_R2.fastq.gz",
                    status="pending",
                    qc_status="unknown",
                    metadata_json={"input_mode": "server_path_scan"},
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
        sample = session.scalar(select(Sample).where(Sample.analysis_id == analysis_id))
    assert run.status == "success"
    assert run.ended_at is not None
    assert sample.status == "success"


def test_sync_airflow_running_clears_stale_terminal_fields(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_submitted_run(session_factory, tmp_path)
    with session_factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        run.status = "failed"
        run.ended_at = datetime(2026, 7, 3, 0, 5, tzinfo=timezone.utc)
        run.error_summary = "previous failed attempt"
        session.commit()
    fake_airflow = FakeAirflowClient("running")
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/sync-airflow")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "running"
    assert payload["ended_at"] is None
    assert payload["error_summary"] is None


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
        sample = session.scalar(select(Sample).where(Sample.analysis_id == analysis_id))
    assert run.status == "failed"
    assert run.error_summary == payload["error_summary"]
    assert run.ended_at is not None
    assert sample.status == "failed"


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


def test_pgta_log_index_exposes_safe_stage_and_rule_logs(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_submitted_run(session_factory, tmp_path, analysis_id="PGTA_S9_LOG_TEST")
    workdir = tmp_path / "shared" / "runs" / analysis_id
    rule_log = workdir / "logs" / "cnv" / "G1.predict.log"
    rule_log.parent.mkdir(parents=True, exist_ok=True)
    rule_log.write_text("predict started\npredict complete\n", encoding="utf-8")
    with session_factory() as session:
        session.add(
            SnakemakeRuleEvent(
                analysis_id=analysis_id,
                rule="wisecondorx_predict_cnv",
                sample_id="G1",
                snakemake_jobid="7",
                status="success",
                stdout_path=str(rule_log),
                stderr_path=str(rule_log),
            )
        )
        session.commit()
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    index = client.get(f"/api/runs/{analysis_id}/logs/index")

    assert index.status_code == 200
    items = index.json()["items"]
    rule_item = next(item for item in items if item.get("rule") == "wisecondorx_predict_cnv")
    assert rule_item["sample_id"] == "G1"
    assert "/data/" not in rule_item["label"]

    tailed = client.get(f"/api/runs/{analysis_id}/logs?key={rule_item['key']}&tail=1")
    assert tailed.status_code == 200
    assert tailed.json()["lines"] == ["predict complete"]


def test_nipt_log_index_resolves_relative_rule_paths_inside_run_workdir(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_submitted_run(session_factory, tmp_path, analysis_id="NIPT_S9_LOG_TEST")
    workdir = tmp_path / "shared" / "runs" / analysis_id
    rule_log = workdir / "log" / "NIPT001.A01.map.log"
    rule_log.parent.mkdir(parents=True, exist_ok=True)
    rule_log.write_text("mapping started\nmapping complete\n", encoding="utf-8")
    with session_factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        assert run is not None
        run.pipeline_name = "nipt_docker"
        session.add(
            SnakemakeRuleEvent(
                analysis_id=analysis_id,
                rule="map",
                sample_id="NIPT001.A01",
                snakemake_jobid="21",
                status="success",
                stdout_path="log/NIPT001.A01.map.log",
            )
        )
        session.commit()
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    index = client.get(f"/api/runs/{analysis_id}/logs/index")

    assert index.status_code == 200
    rule_item = next(item for item in index.json()["items"] if item.get("rule") == "map")
    assert rule_item["sample_id"] == "NIPT001.A01"
    assert rule_item["relative_path"] == "log/NIPT001.A01.map.log"
    assert rule_item["label"] == "map - NIPT001.A01 - stdout"

    tailed = client.get(f"/api/runs/{analysis_id}/logs?key={rule_item['key']}&tail=1")
    assert tailed.status_code == 200
    assert tailed.json()["lines"] == ["mapping complete"]


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


def test_list_pgta_artifacts_discovers_baseline_qc_outputs(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_baseline_submitted_run(session_factory, tmp_path)
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/artifacts")

    assert response.status_code == 200
    items = response.json()["items"]
    keys = {item["key"] for item in items}
    assert {
        "pgta_baseline_qc_summary",
        "pgta_baseline_qc_pass_samples",
        "pgta_baseline_qc_report",
    } <= keys
    summary = next(item for item in items if item["key"] == "pgta_baseline_qc_summary")
    assert summary["type"] == "qc_tsv"
    assert summary["label"] == "PGT-A baseline QC summary"
    assert summary["path"].endswith("qc/baseline/baseline_qc_summary.tsv")


def test_list_pgta_artifacts_discovers_staged_baseline_logs(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_baseline_submitted_run(session_factory, tmp_path)
    logs_dir = tmp_path / "shared" / "runs" / analysis_id / "logs"
    for stage in ("mapping", "metadata", "baseline_qc"):
        (logs_dir / f"snakemake.{stage}.stdout.log").write_text(f"{stage} stdout\n", encoding="utf-8")
        (logs_dir / f"snakemake.{stage}.stderr.log").write_text("", encoding="utf-8")
        (logs_dir / f"snakemake.{stage}.command.txt").write_text(f"snakemake --configfile pgta_stage_{stage}.yaml\n", encoding="utf-8")
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/artifacts")

    assert response.status_code == 200
    keys = {item["key"] for item in response.json()["items"]}
    assert {
        "pgta_mapping_stdout",
        "pgta_mapping_stderr",
        "pgta_mapping_command",
        "pgta_metadata_stdout",
        "pgta_metadata_stderr",
        "pgta_metadata_command",
        "pgta_baseline_qc_stdout",
        "pgta_baseline_qc_stderr",
        "pgta_baseline_qc_command",
    } <= keys


def test_list_pgta_artifacts_discovers_resume_cleanup_log(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_baseline_submitted_run(session_factory, tmp_path)
    cleanup_log = tmp_path / "shared" / "runs" / analysis_id / "logs" / "pgta.resume.cleanup.tsv"
    cleanup_log.write_text(
        "deleted_at\tpath\tsize_bytes\n"
        "2026-07-07T10:00:00+00:00\t/data/airflow-demo/runs/PGTA/mapping/G11.sorted.bam.tmp.0000.bam\t180000000\n",
        encoding="utf-8",
    )
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/artifacts")

    assert response.status_code == 200
    items = response.json()["items"]
    cleanup = next(item for item in items if item["key"] == "pgta_resume_cleanup")
    assert cleanup["type"] == "snakemake_log"
    assert cleanup["label"] == "PGT-A resume cleanup log"
    assert cleanup["path"].endswith("logs/pgta.resume.cleanup.tsv")


def test_list_pgta_artifacts_discovers_python_preflight_log(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_baseline_submitted_run(session_factory, tmp_path)
    preflight_log = tmp_path / "shared" / "runs" / analysis_id / "logs" / "pgta.python_preflight.log"
    preflight_log.write_text("matplotlib\t3.10.8\n", encoding="utf-8")
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    response = client.get(f"/api/runs/{analysis_id}/artifacts")

    assert response.status_code == 200
    items = response.json()["items"]
    preflight = next(item for item in items if item["key"] == "pgta_python_preflight")
    assert preflight["type"] == "snakemake_log"
    assert preflight["label"] == "PGT-A Python preflight log"
    assert preflight["path"].endswith("logs/pgta.python_preflight.log")


def test_sync_airflow_success_imports_pgta_baseline_qc_metrics(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_baseline_submitted_run(session_factory, tmp_path)
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
    assert len(metrics) == 14
    assert {(metric.sample_id, metric.metric_name, metric.status) for metric in metrics} >= {
        ("G1", "baseline_qc_decision", "pass"),
        ("G1", "bin_cv", "pass"),
        ("G2", "baseline_qc_decision", "warn"),
    }
    assert [sample.qc_status for sample in samples] == ["pass", "warn"]


def test_sync_airflow_success_overrides_stale_failed_jsonl_event(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_submitted_run(
        session_factory,
        tmp_path,
        analysis_id="PGTA_20260713_094600_RESUME",
    )
    events_dir = tmp_path / "shared" / "runs" / analysis_id / "logs" / "events"
    events_dir.mkdir(parents=True)
    (events_dir / "snakemake_events.jsonl").write_text(
        "\n".join(
            [
                '{"rule":"metadata","status":"failed","timestamp":"2026-07-13T09:30:00+00:00"}',
                '{"rule":"metadata","status":"success","timestamp":"2026-07-13T09:46:00+00:00"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_airflow = FakeAirflowClient("success")
    install_app_fixtures(monkeypatch, session_factory, tmp_path / "shared", fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/sync-airflow")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    with session_factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        event = session.scalar(
            select(SnakemakeRuleEvent).where(
                SnakemakeRuleEvent.analysis_id == analysis_id,
                SnakemakeRuleEvent.rule == "metadata",
            )
        )
    assert run.status == "success"
    assert event.status == "success"


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
