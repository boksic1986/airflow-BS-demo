from fastapi.testclient import TestClient

from app import main


def test_db_health_returns_ok_when_database_check_passes(monkeypatch) -> None:
    monkeypatch.setattr(main, "check_database", lambda: None)
    client = TestClient(main.app)

    response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_airflow_health_returns_payload_when_airflow_is_reachable(monkeypatch) -> None:
    class FakeAirflowClient:
        def health(self) -> dict[str, object]:
            return {"metadatabase": {"status": "healthy"}}

    monkeypatch.setattr(main, "get_airflow_client", lambda: FakeAirflowClient())
    client = TestClient(main.app)

    response = client.get("/api/health/airflow")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "airflow": {"metadatabase": {"status": "healthy"}},
    }
