from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main


def write_registry(path: Path) -> None:
    path.write_text(
        """\
version: 1
pipelines:
  wgs:
    display_name: Whole genome sequencing
    dag_id: bio_wgs
    version: 4.1.1
    adapter: wgs
    enabled: true
    submit_enabled: true
    capabilities: [intake, submit, rules, qc, artifacts]
    execution_targets: [cce, local, sge]
  wes:
    display_name: Whole exome sequencing
    dag_id: bio_wes
    adapter: generic
    enabled: false
    submit_enabled: false
    capabilities: [submit, rules, qc]
    execution_targets: [local]
""",
        encoding="utf-8",
    )


def make_client(tmp_path, monkeypatch):
    registry = tmp_path / "pipelines.yaml"
    write_registry(registry)
    settings = SimpleNamespace(
        auth_required=False,
        deployed_pipelines=("wgs",),
        pipeline_registry_path=str(registry),
        platform_environment="test",
        public_airflow_url="",
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    main.clear_pipeline_registry_cache()
    return TestClient(main.app)


def test_platform_capabilities_are_projected_from_pipeline_registry(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    response = client.get("/api/platform/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["deployed_pipelines"] == ["wgs"]
    assert [item["id"] for item in payload["pipelines"]] == ["wgs", "wes"]
    assert payload["pipelines"][0]["execution_targets"] == ["cce", "local", "sge"]
    assert payload["pipelines"][1]["enabled"] is False


def test_generic_input_scan_reports_registry_errors(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    unknown = client.post(
        "/api/input/scan",
        json={"pipeline": "unknown", "rawdata_root": "/input"},
    )
    disabled = client.post(
        "/api/input/scan",
        json={"pipeline": "wes", "rawdata_root": "/input"},
    )
    unsupported = client.post(
        "/api/input/scan",
        json={"pipeline": "wgs", "rawdata_root": "/input"},
    )

    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "PIPELINE_NOT_REGISTERED"
    assert disabled.status_code == 409
    assert disabled.json()["detail"]["code"] == "PIPELINE_NOT_AVAILABLE"
    assert unsupported.status_code == 409
    assert unsupported.json()["detail"]["code"] == "PIPELINE_CAPABILITY_UNAVAILABLE"
