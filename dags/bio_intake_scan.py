from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_intake_scan(**context):
    dag_run = context.get("dag_run")
    conf = getattr(dag_run, "conf", None) or {}
    payload = {
        "pipelines": conf.get("pipelines") or _pipeline_list(os.getenv("INTAKE_SCAN_PIPELINES", "pgta,nipt_docker")),
        "bootstrap": bool(conf.get("bootstrap", _bool_env("INTAKE_SCAN_BOOTSTRAP", default=False))),
        "max_samples": int(conf.get("max_samples", os.getenv("INTAKE_SCAN_MAX_SAMPLES", "200"))),
    }
    headers = {"Content-Type": "application/json"}
    service_token = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    if service_token:
        headers["X-Airflow-Demo-Token"] = service_token
    request = Request(
        _intake_endpoint(),
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=int(os.getenv("INTAKE_SCAN_TIMEOUT_SECONDS", "60"))) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"backend intake scan failed: HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"backend intake scan failed: {exc}") from exc


def run_scanner_retention(**context):
    logical_date = context.get("logical_date")
    retention_hour = int(os.getenv("INTAKE_RETENTION_HOUR", "3"))
    retention_minute = int(os.getenv("INTAKE_RETENTION_MINUTE", "0"))
    if logical_date is not None and (logical_date.hour, logical_date.minute) != (retention_hour, retention_minute):
        return {"skipped": True, "reason": f"daily retention runs at {retention_hour:02d}:{retention_minute:02d}"}

    dag_run = context.get("dag_run")
    payload = {
        "dag_id": "bio_intake_scan",
        "current_dag_run_id": getattr(dag_run, "run_id", None),
        "dry_run": False,
    }
    response = _post_backend("/intake/retention", payload)
    response["task_logs_deleted"] = _prune_local_scanner_logs(days=30)
    return response


def propagate_scanner_result(**context):
    dag_run = context.get("dag_run")
    failed_tasks: list[str] = []
    for task_id in ("scan_and_submit", "prune_scanner_history"):
        task_instance = dag_run.get_task_instance(task_id=task_id) if dag_run is not None else None
        state = str(getattr(task_instance, "state", "missing") or "missing").lower()
        if state not in {"success", "skipped"}:
            failed_tasks.append(f"{task_id}={state}")
    if failed_tasks:
        raise RuntimeError(f"scanner DAG failed upstream: {', '.join(failed_tasks)}")
    return {"status": "success"}


def _post_backend(path: str, payload: dict[str, object]) -> dict[str, object]:
    base_url = os.getenv("BACKEND_BASE_URL", "http://backend:8000").rstrip("/")
    api_base = base_url if base_url.endswith("/api") else f"{base_url}/api"
    headers = {"Content-Type": "application/json"}
    service_token = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    if service_token:
        headers["X-Airflow-Demo-Token"] = service_token
    request = Request(
        f"{api_base}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=int(os.getenv("INTAKE_SCAN_TIMEOUT_SECONDS", "60"))) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"backend scanner maintenance failed: HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"backend scanner maintenance failed: {exc}") from exc


def _prune_local_scanner_logs(*, days: int) -> int:
    logs_root = Path(os.getenv("AIRFLOW_LOGS_ROOT", "/opt/airflow/logs")).resolve()
    scanner_root = (logs_root / "dag_id=bio_intake_scan").resolve()
    if logs_root not in scanner_root.parents or not scanner_root.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = 0
    for path in scanner_root.rglob("*"):
        if not path.is_file():
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified < cutoff:
            path.unlink()
            deleted += 1
    return deleted


def _intake_endpoint() -> str:
    base_url = os.getenv("BACKEND_BASE_URL", "http://backend:8000").rstrip("/")
    suffix = "/intake/scan-and-submit" if base_url.endswith("/api") else "/api/intake/scan-and-submit"
    return f"{base_url}{suffix}"


def _pipeline_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool_env(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


with DAG(
    dag_id="bio_intake_scan",
    description="Scan PGT-A and NIPT Docker input roots and auto-submit stable new batches",
    start_date=datetime(2026, 7, 1),
    schedule=os.getenv("INTAKE_SCAN_SCHEDULE", "*/10 * * * *"),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=_bool_env("INTAKE_SCAN_PAUSED_ON_CREATION", default=True),
    tags=["airflow-demo", "intake", *_pipeline_list(os.getenv("INTAKE_SCAN_PIPELINES", "pgta,nipt_docker"))],
) as dag:
    scan_and_submit = PythonOperator(
        task_id="scan_and_submit",
        python_callable=run_intake_scan,
    )
    prune_history = PythonOperator(
        task_id="prune_scanner_history",
        python_callable=run_scanner_retention,
        trigger_rule="all_done",
    )
    scanner_result = PythonOperator(
        task_id="propagate_scanner_result",
        python_callable=propagate_scanner_result,
        trigger_rule="all_done",
    )
    scan_and_submit >> prune_history >> scanner_result
