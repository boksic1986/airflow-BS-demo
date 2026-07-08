from types import SimpleNamespace

from fastapi.testclient import TestClient
import httpx

from app import main
from app.intake_config import load_intake_config


def test_load_intake_config_reads_yaml_roots(tmp_path) -> None:
    config_path = tmp_path / "intake.yaml"
    config_path.write_text(
        """
version: 1
defaults:
  ready_rule: stable_fingerprint
  stable_scans: 2
  auto_submit: false
pipelines:
  pgta:
    enabled: true
    roots:
      - id: pgta_rawdata
        container_path: /data/project/CNV/PGT-A/rawdata
    auto_submit:
      target: metadata
  nipt_docker:
    enabled: true
    roots:
      - id: nipt_fastq
        host_path: /home/jiucheng/pipelines/NIPT/fastq
        container_path: /opt/pipelines/NIPT/fastq
    file_flavor: clean_fastq
    r1_pattern: "*.R1.clean.fastq.gz"
    r2_pattern: "*.R2.clean.fastq.gz"
    ignore_patterns: ["002/*.adapter.fastq.gz"]
    auto_submit:
      run_mode: mount_smoke
""",
        encoding="utf-8",
    )

    config = load_intake_config(
        path=str(config_path),
        fallback_pgta_roots=["/fallback/pgta"],
        fallback_nipt_roots=["/fallback/nipt"],
    )

    assert config.defaults.ready_rule == "stable_fingerprint"
    assert config.defaults.stable_scans == 2
    assert config.roots_for_pipeline("pgta") == ["/data/project/CNV/PGT-A/rawdata"]
    assert config.roots_for_pipeline("nipt_docker") == ["/opt/pipelines/NIPT/fastq"]
    assert config.pipeline("nipt_docker").file_flavor == "clean_fastq"
    assert config.pipeline("nipt_docker").auto_submit["run_mode"] == "mount_smoke"


def test_load_intake_config_falls_back_to_env_roots_when_file_missing(tmp_path) -> None:
    config = load_intake_config(
        path=str(tmp_path / "missing.yaml"),
        fallback_pgta_roots=["/fallback/pgta"],
        fallback_nipt_roots=["/fallback/nipt"],
    )

    assert config.source == "env_fallback"
    assert config.roots_for_pipeline("pgta") == ["/fallback/pgta"]
    assert config.roots_for_pipeline("nipt_docker") == ["/fallback/nipt"]


def test_intake_config_endpoint_returns_sanitized_config(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "intake.yaml"
    config_path.write_text(
        """
version: 1
pipelines:
  pgta:
    enabled: true
    roots:
      - id: pgta_rawdata
        container_path: /data/project/CNV/PGT-A/rawdata
  nipt_docker:
    enabled: false
    roots:
      - id: nipt_fastq
        host_path: /home/jiucheng/pipelines/NIPT/fastq
        container_path: /opt/pipelines/NIPT/fastq
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            intake_config_path=str(config_path),
            pgta_input_scan_roots=["/fallback/pgta"],
            nipt_input_scan_roots=["/fallback/nipt"],
        ),
    )
    client = TestClient(main.app)

    response = client.get("/api/intake/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == str(config_path)
    assert payload["pipelines"]["pgta"]["enabled"] is True
    assert payload["pipelines"]["pgta"]["roots"] == [{"id": "pgta_rawdata", "container_path": "/data/project/CNV/PGT-A/rawdata"}]
    assert payload["pipelines"]["nipt_docker"]["enabled"] is False
    assert "host_path" not in payload["pipelines"]["nipt_docker"]["roots"][0]


def test_intake_scanner_state_endpoint_reads_airflow_dag_pause_and_latest_run(monkeypatch) -> None:
    class FakeAirflowClient:
        def get_dag(self, dag_id: str) -> dict[str, object]:
            assert dag_id == "bio_intake_scan"
            return {"dag_id": dag_id, "is_paused": True}

        def list_dag_runs(self, dag_id: str, *, limit: int = 100, order_by: str | None = None) -> dict[str, object]:
            assert dag_id == "bio_intake_scan"
            assert limit == 1
            assert order_by == "-start_date"
            return {
                "dag_runs": [
                    {
                        "dag_run_id": "scheduled__2026-07-08T17:00:00+08:00",
                        "state": "success",
                        "start_date": "2026-07-08T17:00:01+08:00",
                        "end_date": "2026-07-08T17:00:05+08:00",
                    }
                ]
            }

    monkeypatch.setattr(main, "get_airflow_client", lambda: FakeAirflowClient())
    client = TestClient(main.app)

    response = client.get("/api/intake/scanner-state")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "dag_id": "bio_intake_scan",
        "airflow_reachable": True,
        "is_paused": True,
        "latest_dag_run_id": "scheduled__2026-07-08T17:00:00+08:00",
        "latest_dag_run_state": "success",
        "latest_start_date": "2026-07-08T17:00:01+08:00",
        "latest_end_date": "2026-07-08T17:00:05+08:00",
        "message": None,
    }


def test_intake_scanner_state_endpoint_degrades_when_airflow_is_unavailable(monkeypatch) -> None:
    class BrokenAirflowClient:
        def get_dag(self, dag_id: str) -> dict[str, object]:
            raise httpx.ConnectError("airflow unavailable")

    monkeypatch.setattr(main, "get_airflow_client", lambda: BrokenAirflowClient())
    client = TestClient(main.app)

    response = client.get("/api/intake/scanner-state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dag_id"] == "bio_intake_scan"
    assert payload["airflow_reachable"] is False
    assert payload["is_paused"] is None
    assert payload["latest_dag_run_id"] is None
    assert payload["latest_dag_run_state"] is None
    assert payload["message"] == "Airflow scanner state unavailable"
