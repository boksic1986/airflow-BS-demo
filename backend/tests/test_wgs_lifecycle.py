from pathlib import Path
from types import SimpleNamespace
import hashlib
import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import Base


def make_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


class FakeAirflowClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trigger_dag_run(self, dag_id: str, *, dag_run_id: str | None = None, conf: dict | None = None) -> dict:
        self.calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf})
        return {"dag_run_id": dag_run_id}


def test_create_and_submit_controlled_wgs_run(tmp_path, monkeypatch) -> None:
    session_factory = make_sessionmaker()
    shared_root = tmp_path / "shared"
    validation_root = tmp_path / "validation"
    validation_root.mkdir()
    sample_info = validation_root / "sampleinfo.tsv"
    sample_info.write_text(
        "样本编号\t家系编号\t数据编号\n"
        "WGS-DEMO-01\tFAM-01\tWGS-DATA-01\n"
        "WGS-CONTEXT-02\tFAM-02\tWGS-DATA-02\n",
        encoding="utf-8",
    )
    config = validation_root / "config.yaml"
    config.write_text(
        f"version: V3.8.1-s9\nbatch: WGS-DEMO\nsample_info: {sample_info}\n"
        f"fastqDir: {validation_root}\nsample:\n  - WGS-DATA-01\n",
        encoding="utf-8",
    )
    targets = validation_root / "targets.txt"
    targets.write_text("00_PreCalling/WGS-DEMO-01.g.vcf.gz\n", encoding="utf-8")
    settings = SimpleNamespace(
        deployed_pipelines=("wgs",),
        container_shared_root=str(shared_root),
        host_results_root=str(tmp_path / "host-results"),
        wgs_config_roots=[str(validation_root)],
        wgs_validation_roots=[str(validation_root)],
        pipeline_profile_config_path=None,
    )
    airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: airflow)
    client = TestClient(main.app)

    created = client.post(
        "/api/runs",
        json={
            "pipeline": "wgs",
            "project_name": "WGS controlled validation",
            "wgs_config_path": str(config),
            "wgs_targets_path": str(targets),
            "wgs_stage": "precalling",
            "submitted_by": "jiucheng",
        },
    )

    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["analysis_id"].startswith("WGS_")
    assert payload["pipeline"] == "wgs"
    assert payload["sample_count"] == 1
    run_dir = tmp_path / "host-results" / "runs" / payload["analysis_id"]
    assert (run_dir / "config" / "wgs.precalling.requested.yaml").is_file()
    runner_request = run_dir / "config" / "wgs_runner_request.json"
    assert runner_request.is_file()
    runner_payload = json.loads(runner_request.read_text(encoding="utf-8"))
    host_run = tmp_path / "host-results" / "runs" / payload["analysis_id"]
    assert runner_payload["host_workdir"] == str(host_run)
    assert runner_payload["precalling_config_path"] == str(host_run / "config" / "wgs.precalling.requested.yaml")
    assert runner_payload["downstream_config_path"] == str(host_run / "config" / "wgs.downstream.requested.yaml")
    assert runner_payload["targets_path"] == str(host_run / "config" / "targets.requested.txt")
    assert runner_payload["source_analysis_root"] == str(validation_root)
    assert runner_payload["input_sha256"]["precalling_config"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert (run_dir / "config" / "targets.requested.txt").read_text(encoding="utf-8").strip() == targets.read_text(encoding="utf-8").strip()

    submitted = client.post(f"/api/runs/{payload['analysis_id']}/actions/submit")

    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"
    assert airflow.calls[0]["dag_id"] == "bio_wgs"
    assert airflow.calls[0]["conf"]["params"]["wgs_stage"] == "precalling"


def test_wgs_run_rejects_config_outside_approved_root(tmp_path, monkeypatch) -> None:
    session_factory = make_sessionmaker()
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("batch: unsafe\n", encoding="utf-8")
    targets = allowed / "targets.txt"
    targets.write_text("safe-target\n", encoding="utf-8")
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            deployed_pipelines=("wgs",),
            container_shared_root=str(tmp_path / "shared"),
            wgs_config_roots=[str(allowed)],
            wgs_validation_roots=[str(allowed)],
            pipeline_profile_config_path=None,
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)

    response = client.post(
        "/api/runs",
        json={
            "pipeline": "wgs",
            "project_name": "unsafe",
            "wgs_config_path": str(outside),
            "wgs_targets_path": str(targets),
            "wgs_stage": "precalling",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_INPUT_PATH"


def test_run_resources_returns_summary_artifact(tmp_path, monkeypatch) -> None:
    session_factory = make_sessionmaker()
    validation_root = tmp_path / "validation"
    validation_root.mkdir()
    sample_info = validation_root / "sampleinfo.tsv"
    sample_info.write_text("sample_id\nWGS-DEMO-01\n", encoding="utf-8")
    config = validation_root / "config.yaml"
    config.write_text(f"batch: demo\nsample_info: {sample_info}\n", encoding="utf-8")
    targets = validation_root / "targets.txt"
    targets.write_text("target\n", encoding="utf-8")
    shared_root = tmp_path / "shared"
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            deployed_pipelines=("wgs",),
            container_shared_root=str(shared_root),
            wgs_config_roots=[str(validation_root)],
            wgs_validation_roots=[str(validation_root)],
            pipeline_profile_config_path=None,
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)
    created = client.post(
        "/api/runs",
        json={
            "pipeline": "wgs",
            "project_name": "resources",
            "wgs_config_path": str(config),
            "wgs_targets_path": str(targets),
            "wgs_stage": "precalling",
        },
    ).json()
    summary_path = shared_root / "runs" / created["analysis_id"] / "reports" / "resource_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        '{"wall_seconds": 90.5, "peak_pss_bytes": 1048576, "peak_rss_bytes": 2097152, "read_bytes": 4096, "write_bytes": 8192, "cpu_seconds": 42.5, "sample_count": 18, "complete": true, "raw_samples_paths": ["logs/resources/pre_calling.jsonl"]}',
        encoding="utf-8",
    )

    response = client.get(f"/api/runs/{created['analysis_id']}/resources")

    assert response.status_code == 200
    assert response.json()["peak_pss_bytes"] == 1048576
    assert response.json()["write_bytes"] == 8192
    assert response.json()["complete"] is True
    assert response.json()["summary_artifact"] == "reports/resource_summary.json"
    assert response.json()["raw_samples_paths"] == ["logs/resources/pre_calling.jsonl"]
    assert "summary_path" not in response.json()


def test_run_resources_treats_corrupt_summary_as_unavailable(tmp_path, monkeypatch) -> None:
    session_factory = make_sessionmaker()
    validation_root = tmp_path / "validation"
    validation_root.mkdir()
    sample_info = validation_root / "sampleinfo.tsv"
    sample_info.write_text("sample_id\nWGS-DEMO-01\n", encoding="utf-8")
    config = validation_root / "config.yaml"
    config.write_text(f"sample_info: {sample_info}\nfastqDir: {validation_root}\n", encoding="utf-8")
    targets = validation_root / "targets.txt"
    targets.write_text("target\n", encoding="utf-8")
    shared_root = tmp_path / "shared"
    monkeypatch.setattr(main, "get_settings", lambda: SimpleNamespace(
        deployed_pipelines=("wgs",), container_shared_root=str(shared_root),
        wgs_config_roots=[str(validation_root)], wgs_validation_roots=[str(validation_root)],
        pipeline_profile_config_path=None,
    ))
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    created = TestClient(main.app).post("/api/runs", json={
        "pipeline": "wgs", "project_name": "bad resources", "wgs_config_path": str(config),
        "wgs_targets_path": str(targets), "wgs_stage": "precalling",
    }).json()
    summary = shared_root / "runs" / created["analysis_id"] / "reports" / "resource_summary.json"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text("not-json", encoding="utf-8")

    response = TestClient(main.app).get(f"/api/runs/{created['analysis_id']}/resources")

    assert response.status_code == 404
