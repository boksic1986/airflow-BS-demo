from __future__ import annotations

from datetime import datetime, timedelta
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor


ANALYSIS_ID_RE = re.compile(r"^WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")


def validate_request(**context: Any) -> dict[str, Any]:
    conf = dict(context["dag_run"].conf or {})
    params = dict(conf.get("params") or {})
    if conf.get("pipeline") != "wgs":
        raise ValueError("pipeline must be wgs")
    if conf.get("execution_mode") not in {"local", "sge"}:
        raise ValueError("execution_mode must be local or sge")
    if not ANALYSIS_ID_RE.fullmatch(str(conf.get("analysis_id") or "")):
        raise ValueError("analysis_id must be a generated WGS identifier")
    if not isinstance(conf.get("attempt"), int) or int(conf["attempt"]) < 1:
        raise ValueError("attempt must be a positive integer")
    if not str(conf.get("workdir") or "").strip():
        raise ValueError("workdir is required")
    return conf


def execution_disabled(**context: Any) -> None:
    del context
    if os.getenv("WGS_EXECUTION_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("WGS execution is disabled; set WGS_EXECUTION_ENABLED=true only after runner approval.")
    raise RuntimeError("WGS runner integration is deferred; no local or SGE command is available in this release.")


def _pipeline_finished(**context: Any) -> bool:
    analysis_id = str((context["dag_run"].conf or {}).get("analysis_id") or "")
    base_url = os.getenv("BACKEND_BASE_URL", "http://backend:8000").rstrip("/")
    headers = {"Accept": "application/json"}
    token = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    if token:
        headers["X-Airflow-Demo-Token"] = token
    request = Request(f"{base_url}/api/runs/{analysis_id}", headers=headers, method="GET")
    try:
        with urlopen(request, timeout=15) as response:
            payload = response.read().decode("utf-8")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"backend on-prem run status is unavailable: {exc}") from exc
    compact = payload.replace(" ", "")
    return '"status":"success"' in compact or '"status":"failed"' in compact


with DAG(
    dag_id="bio_wgs_onprem",
    description="Paused project-level local or SGE WGS topology; runner integration is deferred",
    start_date=datetime(2026, 8, 12),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    tags=["airflow-demo", "wgs", "onprem", "project-level"],
) as dag:
    validate = PythonOperator(task_id="validate_request", python_callable=validate_request)
    prepare = PythonOperator(task_id="prepare_run", python_callable=execution_disabled, execution_timeout=timedelta(hours=1))
    run = PythonOperator(task_id="run_pipeline", python_callable=execution_disabled, execution_timeout=timedelta(hours=72))
    wait = PythonSensor(task_id="wait_for_pipeline", python_callable=_pipeline_finished, mode="reschedule", poke_interval=60, timeout=72 * 60 * 60)
    finalize = PythonOperator(task_id="finalize_run", python_callable=execution_disabled)
    validate >> prepare >> run >> wait >> finalize
