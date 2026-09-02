from __future__ import annotations

from typing import Any

import httpx


def ensure_dag_run(*, airflow_client, dag_id: str, dag_run_id: str,
                   conf: dict[str, Any]) -> dict[str, Any]:
    """Create one deterministic DagRun or verify the existing identity."""
    existing = _get_existing(airflow_client, dag_id, dag_run_id)
    if existing is not None:
        _verify_conf(existing, conf)
        return existing
    try:
        return airflow_client.trigger_dag_run(
            dag_id,
            dag_run_id=dag_run_id,
            conf=conf,
        )
    except httpx.HTTPStatusError as error:
        if error.response.status_code != 409:
            raise
        existing = _get_existing(airflow_client, dag_id, dag_run_id)
        if existing is None:
            raise
        _verify_conf(existing, conf)
        return existing


def _get_existing(airflow_client, dag_id: str, dag_run_id: str) -> dict[str, Any] | None:
    getter = getattr(airflow_client, "get_dag_run", None)
    if getter is None:
        return None
    try:
        value = getter(dag_id, dag_run_id)
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 404:
            return None
        raise
    return value if isinstance(value, dict) else None


def _verify_conf(existing: dict[str, Any], expected: dict[str, Any]) -> None:
    actual = existing.get("conf")
    if not isinstance(actual, dict):
        return
    for field in ("analysis_id", "attempt", "maintenance_mode", "maintenance_action_id"):
        if field in expected and actual.get(field) != expected.get(field):
            raise RuntimeError(f"existing Airflow DagRun has conflicting {field}")
