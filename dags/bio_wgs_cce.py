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
    """Validate only the stable WGS handoff contract for the deferred runner."""
    conf = dict(context["dag_run"].conf or {})
    analysis_id = str(conf.get("analysis_id") or "")
    params = dict(conf.get("params") or {})
    if conf.get("pipeline") != "wgs":
        raise ValueError("pipeline must be wgs")
    if conf.get("execution_mode") != "cce":
        raise ValueError("execution_mode must be cce")
    if not ANALYSIS_ID_RE.fullmatch(analysis_id):
        raise ValueError("analysis_id must be a generated WGS identifier")
    if not isinstance(conf.get("attempt"), int) or int(conf["attempt"]) < 1:
        raise ValueError("attempt must be a positive integer")
    if not str(conf.get("workdir") or "").strip():
        raise ValueError("workdir is required")
    return conf


def execution_disabled(**context: Any) -> None:
    """Fail closed until a separately approved runner integration exists."""
    if os.getenv("WGS_EXECUTION_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("WGS execution is disabled; set WGS_EXECUTION_ENABLED=true only after runner approval.")
    raise RuntimeError("WGS runner integration is deferred; no CCE or OBS command is available in this release.")


def _disabled_stage(task_id: str, *, pool: str | None = None, timeout_hours: int = 12) -> PythonOperator:
    return PythonOperator(
        task_id=task_id,
        execution_timeout=timedelta(hours=timeout_hours),
        pool=pool,
        python_callable=execution_disabled,
    )


def _backend_finished(**context: Any) -> bool:
    """Poll only the backend's internal run projection, never CCE credentials."""
    dag_run = context["dag_run"]
    analysis_id = str((dag_run.conf or {}).get("analysis_id") or "")
    base_url = os.getenv("BACKEND_BASE_URL", "http://backend:8000").rstrip("/")
    token = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    headers = {"Accept": "application/json"}
    if token:
        headers["X-Airflow-Demo-Token"] = token
    request = Request(f"{base_url}/api/runs/{analysis_id}", headers=headers, method="GET")
    try:
        with urlopen(request, timeout=15) as response:
            payload = response.read().decode("utf-8")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"backend CCE run status is unavailable: {exc}") from exc
    return '"status":"success"' in payload.replace(" ", "") or '"status":"failed"' in payload.replace(" ", "")


with DAG(
    dag_id="bio_wgs_cce",
    description="Paused project-level WGS CCE topology; runner integration is deliberately deferred",
    start_date=datetime(2026, 8, 12),
    schedule=None,
    catchup=False,
    max_active_runs=4,
    is_paused_upon_creation=True,
    tags=["airflow-demo", "wgs", "cce", "project-level"],
) as dag:
    validate = PythonOperator(task_id="validate_request", python_callable=validate_request)
    upload = _disabled_stage("upload_to_obs", pool="wgs_obs_transfer")
    verify_upload = _disabled_stage("verify_obs_upload", pool="wgs_obs_transfer")
    preflight = _disabled_stage("cce_preflight")
    acquire_master = _disabled_stage("acquire_master_slot", pool="wgs_cce_runs")
    launch_master = _disabled_stage("launch_master", pool="wgs_cce_runs", timeout_hours=2)
    wait_master = PythonSensor(
        task_id="wait_for_master",
        python_callable=_backend_finished,
        mode="reschedule",
        poke_interval=60,
        timeout=48 * 60 * 60,
        pool="wgs_cce_runs",
    )
    publish = _disabled_stage("publish_evidence", pool="wgs_obs_transfer")
    download = _disabled_stage("download_results", pool="wgs_obs_transfer")
    verify = PythonSensor(
        task_id="verify_results",
        python_callable=_backend_finished,
        mode="reschedule",
        poke_interval=60,
        timeout=12 * 60 * 60,
    )
    finalize = _disabled_stage("finalize_run")

    validate >> upload >> verify_upload >> preflight >> acquire_master >> launch_master >> wait_master
    wait_master >> publish >> download >> verify >> finalize
