import base64
import json

import httpx

from app.airflow_client import AirflowClient


def test_airflow_client_reads_health_with_basic_auth() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"metadatabase": {"status": "healthy"}})

    client = AirflowClient(
        base_url="http://airflow-api-server:8080",
        username="admin",
        password="secret",
        transport=httpx.MockTransport(handler),
    )

    payload = client.health()

    expected_auth = "Basic " + base64.b64encode(b"admin:secret").decode()
    assert payload["metadatabase"]["status"] == "healthy"
    assert requests[0].method == "GET"
    assert requests[0].url.path == "/health"
    assert requests[0].headers["authorization"] == expected_auth


def test_airflow_client_lists_and_gets_dag_runs() -> None:
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path.endswith("/dagRuns/run-1"):
            return httpx.Response(200, json={"dag_run_id": "run-1"})
        return httpx.Response(200, json={"dag_runs": [{"dag_run_id": "run-1"}]})

    client = AirflowClient(
        base_url="http://airflow-api-server:8080",
        username="admin",
        password="secret",
        transport=httpx.MockTransport(handler),
    )

    list_payload = client.list_dag_runs("bio_demo")
    get_payload = client.get_dag_run("bio_demo", "run-1")

    assert list_payload["dag_runs"][0]["dag_run_id"] == "run-1"
    assert get_payload["dag_run_id"] == "run-1"
    assert seen_paths == [
        "/api/v1/dags/bio_demo/dagRuns",
        "/api/v1/dags/bio_demo/dagRuns/run-1",
    ]


def test_airflow_client_lists_task_instances_for_dag_run() -> None:
    seen_raw_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_raw_paths.append(request.url.raw_path.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "task_instances": [
                    {
                        "task_id": "run_pgta_target",
                        "state": "running",
                        "operator": "PythonOperator",
                        "try_number": 1,
                    }
                ],
                "total_entries": 1,
            },
        )

    client = AirflowClient(
        base_url="http://airflow-api-server:8080",
        username="admin",
        password="secret",
        transport=httpx.MockTransport(handler),
    )

    payload = client.list_task_instances("bio_demo", "manual__demo run")

    assert payload["task_instances"][0]["task_id"] == "run_pgta_target"
    assert seen_raw_paths == ["/api/v1/dags/bio_demo/dagRuns/manual__demo%20run/taskInstances"]


def test_airflow_client_triggers_dag_run_with_conf() -> None:
    captured_json: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_json.update(json.loads(request.content))
        return httpx.Response(200, json={"dag_run_id": "manual__demo"})

    client = AirflowClient(
        base_url="http://airflow-api-server:8080",
        username="admin",
        password="secret",
        transport=httpx.MockTransport(handler),
    )

    payload = client.trigger_dag_run(
        "bio_demo",
        dag_run_id="manual__demo",
        conf={"analysis_id": "DEMO_001"},
    )

    assert payload["dag_run_id"] == "manual__demo"
    assert captured_json == {
        "dag_run_id": "manual__demo",
        "conf": {"analysis_id": "DEMO_001"},
    }
