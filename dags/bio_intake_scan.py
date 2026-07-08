from __future__ import annotations

from datetime import datetime
import json
import os
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
    request = Request(
        _intake_endpoint(),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
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
    is_paused_upon_creation=_bool_env("INTAKE_SCAN_PAUSED_ON_CREATION", default=True),
    tags=["airflow-demo", "intake", "pgta", "nipt"],
) as dag:
    scan_and_submit = PythonOperator(
        task_id="scan_and_submit",
        python_callable=run_intake_scan,
    )
