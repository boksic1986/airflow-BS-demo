from types import SimpleNamespace

from fastapi.testclient import TestClient

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
