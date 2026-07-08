from typing import Any
from urllib.parse import quote

import httpx


class AirflowClient:
    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            auth=(username, password),
            timeout=timeout,
            transport=transport,
        )

    def health(self) -> dict[str, Any]:
        response = self._client.get("/health")
        response.raise_for_status()
        return response.json()

    def get_dag(self, dag_id: str) -> dict[str, Any]:
        response = self._client.get(f"/api/v1/dags/{quote(dag_id, safe='')}")
        response.raise_for_status()
        return response.json()

    def list_dag_runs(self, dag_id: str, *, limit: int = 100, order_by: str | None = None) -> dict[str, Any]:
        params: dict[str, object] = {"limit": limit}
        if order_by:
            params["order_by"] = order_by
        response = self._client.get(
            f"/api/v1/dags/{quote(dag_id, safe='')}/dagRuns",
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def get_dag_run(self, dag_id: str, dag_run_id: str) -> dict[str, Any]:
        response = self._client.get(
            f"/api/v1/dags/{quote(dag_id, safe='')}/dagRuns/{quote(dag_run_id, safe='')}"
        )
        response.raise_for_status()
        return response.json()

    def list_task_instances(self, dag_id: str, dag_run_id: str) -> dict[str, Any]:
        response = self._client.get(
            f"/api/v1/dags/{quote(dag_id, safe='')}/dagRuns/{quote(dag_run_id, safe='')}/taskInstances"
        )
        response.raise_for_status()
        return response.json()

    def trigger_dag_run(
        self,
        dag_id: str,
        *,
        dag_run_id: str | None = None,
        conf: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"conf": conf or {}}
        if dag_run_id:
            payload["dag_run_id"] = dag_run_id

        response = self._client.post(
            f"/api/v1/dags/{quote(dag_id, safe='')}/dagRuns",
            json=payload,
        )
        response.raise_for_status()
        return response.json()
