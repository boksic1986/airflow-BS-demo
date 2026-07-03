from fastapi.testclient import TestClient

from app.main import app


def test_frontend_origin_can_preflight_backend_api() -> None:
    client = TestClient(app)

    response = client.options(
        "/api/runs",
        headers={
            "Origin": "http://fengxian:12959",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] in {"*", "http://fengxian:12959"}
