from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main


def test_capabilities_register_gatk_as_manual_cce_pipeline(tmp_path: Path, monkeypatch) -> None:
    registry = tmp_path / "pipelines.yaml"
    registry.write_text(
        """version: 1
pipelines:
  wgs:
    display_name: Whole genome sequencing
    dag_id: bio_wgs
    version: 4.1.1
    adapter: wgs
    enabled: true
    submit_enabled: true
    capabilities: [submit, rules, qc, artifacts]
    execution_targets: [cce, local, sge]
  gatk:
    display_name: GATK Cloud
    dag_id: bio_gatk
    version: 7.6.0
    adapter: gatk
    enabled: true
    submit_enabled: true
    capabilities: [submit, rules, artifacts]
    execution_targets: [cce]
""",
        encoding="utf-8",
    )
    settings = SimpleNamespace(
        auth_required=False,
        deployed_pipelines=("wgs", "gatk"),
        pipeline_registry_path=str(registry),
        platform_environment="test",
        public_airflow_url="",
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    main.clear_pipeline_registry_cache()

    response = TestClient(main.app).get("/api/platform/capabilities")

    assert response.status_code == 200
    gatk = next(item for item in response.json()["pipelines"] if item["id"] == "gatk")
    assert gatk["dag_id"] == "bio_gatk"
    assert gatk["execution_targets"] == ["cce"]
    assert "intake" not in gatk["capabilities"]
