from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main
from app.config import get_settings


def _settings(**overrides):
    values = {
        "deployed_pipelines": ("nipt_docker",),
        "platform_environment": "BS10610",
        "public_airflow_url": "http://172.17.106.10:12958",
        "nipt_input_scan_roots": ["/data/nipt-fastq"],
        "pgta_input_scan_roots": [],
        "input_scan_roots": [],
        "container_shared_root": "/data/airflow-demo",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_settings_parse_nipt_only_capability(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("AIRFLOW_API_PASSWORD", "test")
    monkeypatch.setenv("DEPLOYED_PIPELINES", "nipt_docker")
    monkeypatch.setenv("PLATFORM_ENVIRONMENT", "BS10610")
    monkeypatch.setenv("PUBLIC_AIRFLOW_URL", "http://172.17.106.10:12958")
    get_settings.cache_clear()


def test_settings_parse_wgs_only_capability(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("AIRFLOW_API_PASSWORD", "test")
    monkeypatch.setenv("DEPLOYED_PIPELINES", "wgs")
    monkeypatch.setenv("PLATFORM_ENVIRONMENT", "BS10610-WGS")
    monkeypatch.setenv("PUBLIC_AIRFLOW_URL", "http://172.17.106.10:13958")
    monkeypatch.setenv("WGS_CONFIG_ROOTS", "/data/wgs-intake")
    monkeypatch.setenv("WGS_VALIDATION_ROOTS", "/data/wgs-validation")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.deployed_pipelines == ("wgs",)
    assert settings.wgs_config_roots == ["/data/wgs-intake"]
    assert settings.wgs_validation_roots == ["/data/wgs-validation"]
    assert settings.platform_environment == "BS10610-WGS"
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.deployed_pipelines == ("nipt_docker",)
    assert settings.platform_environment == "BS10610"
    assert settings.public_airflow_url == "http://172.17.106.10:12958"
    get_settings.cache_clear()


def test_platform_capabilities_are_safe_for_frontend(monkeypatch) -> None:
    monkeypatch.setattr(main, "get_settings", lambda: _settings())
    client = TestClient(main.app)

    response = client.get("/api/platform/capabilities")

    assert response.status_code == 200
    assert response.json() == {
        "environment": "BS10610",
        "deployed_pipelines": ["nipt_docker"],
        "airflow_url": "http://172.17.106.10:12958",
    }


def test_nipt_only_deployment_rejects_pgta_scan(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main, "get_settings", lambda: _settings())
    client = TestClient(main.app)

    response = client.post(
        "/api/input/scan",
        json={"pipeline": "pgta", "rawdata_root": str(tmp_path)},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "PIPELINE_NOT_DEPLOYED"
