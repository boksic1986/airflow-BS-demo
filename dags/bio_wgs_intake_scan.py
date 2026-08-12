from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any
from urllib.request import Request, urlopen

from airflow import DAG
from airflow.operators.python import PythonOperator


def build_scan_payload(**context: Any) -> dict[str, Any]:
    conf = dict((context.get("dag_run") and context["dag_run"].conf) or {})
    requested = conf.get("pipelines", ["wgs"])
    if requested != ["wgs"]:
        raise ValueError("WGS-only intake accepts pipelines=[wgs]")
    return {"pipelines": ["wgs"], "bootstrap": bool(conf.get("bootstrap", False)), "max_samples": int(conf.get("max_samples", 200))}


def scan_backend(**context: Any) -> dict[str, Any]:
    payload = build_scan_payload(**context)
    base = os.getenv("BACKEND_BASE_URL", "http://backend:8000").rstrip("/")
    token = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Airflow-Demo-Token"] = token
    request = Request(f"{base}/api/intake/scan-and-submit", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urlopen(request, timeout=int(os.getenv("INTAKE_SCAN_TIMEOUT_SECONDS", "60"))) as response:
        return json.loads(response.read().decode("utf-8"))


with DAG(
    dag_id="bio_wgs_intake_scan",
    description="WGS-only internal backend intake scan",
    start_date=datetime(2026, 8, 12),
    schedule="*/10 * * * *",
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    tags=["airflow-demo", "wgs", "intake"],
) as dag:
    PythonOperator(task_id="scan_backend", python_callable=scan_backend)
