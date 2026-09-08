from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
from airflow.utils.trigger_rule import TriggerRule


RUNNER_STAGES = {
    "prepare",
    "step1_upload",
    "step2_master",
    "step3_monitor",
    "step4_publish",
    "step5_download",
    "step6_materialize",
}


def _backend_json(
    path: str, *, method: str = "GET", payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    base = os.getenv("BACKEND_BASE_URL", "http://backend:8000").rstrip("/")
    token = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base}{path}",
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Airflow-Demo-Token": token,
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            value = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"GATK backend rejected {path}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"GATK backend unavailable for {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("GATK backend response must be an object")
    return value


def validate_request(**context: Any) -> dict[str, Any]:
    if os.getenv("GATK_EXECUTION_ENABLED", "false").lower() not in {"1", "true", "yes", "on"}:
        raise ValueError("GATK execution is disabled")
    conf = dict(context["dag_run"].conf or {})
    if conf.get("pipeline") != "gatk" or conf.get("execution_mode") != "cce":
        raise ValueError("bio_gatk accepts only pipeline=gatk execution_mode=cce")
    if not str(conf.get("analysis_id") or "").startswith("GATK_"):
        raise ValueError("invalid GATK analysis_id")
    if int(conf.get("attempt") or 0) < 1:
        raise ValueError("invalid GATK attempt")
    return {"analysis_id": conf["analysis_id"], "attempt": conf["attempt"]}


def register_stage(stage: str, **context: Any) -> dict[str, Any]:
    conf = dict(context["dag_run"].conf or {})
    return _backend_json(
        f"/api/internal/gatk/runs/{conf['analysis_id']}/stages/{stage}",
        method="POST",
        payload={"attempt": conf["attempt"], "adapter": "gatk-runtime-200"},
    )


def run_stage(stage: str, **context: Any) -> dict[str, Any]:
    if stage not in RUNNER_STAGES:
        raise ValueError(f"unsupported GATK runner stage: {stage}")
    registered = register_stage(stage, **context)
    conf = dict(context["dag_run"].conf or {})
    command = [
        "ssh",
        "-tt",
        "-F",
        os.getenv("GATK_SSH_CONFIG_PATH", "/opt/airflow/ssh/config"),
        os.getenv("GATK_RUNNER_200_ALIAS", "gatk-node200"),
        os.getenv(
            "GATK_RUNNER_200_COMMAND",
            "/home/ctapa/.config/airflow-gatk/forced-command.sh",
        ),
        "gatk-runtime",
        str(conf["analysis_id"]),
        str(conf["attempt"]),
        stage,
    ]
    completed = subprocess.run(
        command,
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        error = " | ".join(
            item.strip()
            for item in (completed.stdout, completed.stderr)
            if item and item.strip()
        )[-2000:]
        raise RuntimeError(
            f"restricted node200 GATK stage failed ({completed.returncode}): {error}"
        )
    return {**registered, "runner_status": "accepted"}


def stage_ready(stage: str, **context: Any) -> bool:
    conf = dict(context["dag_run"].conf or {})
    query = urlencode({"attempt": conf["attempt"], "stage": stage})
    value = _backend_json(
        f"/api/internal/gatk/runs/{conf['analysis_id']}/stage-status?{query}"
    )
    if value.get("failed"):
        raise RuntimeError(str(value.get("message") or f"GATK stage failed: {stage}"))
    return bool(value.get("ready"))


def acquire_transfer_slot(kind: str, **context: Any) -> bool:
    stage = f"acquire_{kind}_transfer_slot"
    return bool(register_stage(stage, **context).get("acquired"))


def release_stage(stage: str, **context: Any) -> dict[str, Any]:
    return register_stage(stage, **context)


def _upstream_failure_task_ids(context: dict[str, Any]) -> list[str]:
    task_instance = context.get("ti") or context.get("task_instance")
    if task_instance is None:
        return []
    dag_run = task_instance.get_dagrun()
    current_task_id = str(getattr(task_instance, "task_id", "release_leases"))
    failed: list[str] = []
    for candidate in dag_run.get_task_instances():
        task_id = str(getattr(candidate, "task_id", ""))
        raw_state = getattr(candidate, "state", None)
        state = str(getattr(raw_state, "value", raw_state) or "").lower()
        if task_id != current_task_id and state in {"failed", "upstream_failed"}:
            failed.append(task_id)
    return sorted(failed)


def release_leases(**context: Any) -> dict[str, Any]:
    released = release_stage("release_leases", **context)
    failed_tasks = _upstream_failure_task_ids(context)
    if failed_tasks:
        raise RuntimeError(
            "GATK upstream tasks failed after leases were released: "
            + ", ".join(failed_tasks)
        )
    return released


def _runner_task(task_id: str, stage: str, *, pool: str | None = None) -> PythonOperator:
    return PythonOperator(
        task_id=task_id,
        python_callable=run_stage,
        op_kwargs={"stage": stage},
        pool=pool,
        execution_timeout=timedelta(minutes=15),
    )


def _stage_sensor(task_id: str, stage: str, timeout_hours: int = 48) -> PythonSensor:
    return PythonSensor(
        task_id=task_id,
        python_callable=stage_ready,
        op_kwargs={"stage": stage},
        mode="reschedule",
        poke_interval=30,
        timeout=timeout_hours * 3600,
    )


with DAG(
    dag_id="bio_gatk",
    description="Manual SCMC GATK Cloud Step1-Step6 orchestration",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0},
    tags=["ngs", "gatk", "cce", "manual"],
) as dag:
    validate = PythonOperator(task_id="validate_request", python_callable=validate_request)
    prepare = _runner_task("prepare_gatk_contract", "prepare")
    wait_prepare = _stage_sensor("wait_prepare_gatk_contract", "prepare", 2)
    acquire_input = PythonSensor(
        task_id="acquire_input_transfer_slot",
        python_callable=acquire_transfer_slot,
        op_kwargs={"kind": "input"},
        mode="reschedule",
        poke_interval=30,
        timeout=48 * 3600,
        pool="wgs_obs_upload",
    )
    step1 = _runner_task("start_step1_upload", "step1_upload")
    wait_step1 = _stage_sensor("wait_step1_upload", "step1_upload")
    release_input = PythonOperator(
        task_id="release_input_transfer_slot",
        python_callable=release_stage,
        op_kwargs={"stage": "release_input_transfer_slot"},
        trigger_rule=TriggerRule.ALL_DONE,
    )
    step2 = _runner_task("submit_step2_master", "step2_master", pool="gatk_cce_runs")
    wait_step2 = _stage_sensor("wait_step2_master", "step2_master", 2)
    step3 = _runner_task("start_step3_monitor", "step3_monitor")
    wait_step3 = _stage_sensor("wait_step3_analysis", "step3_monitor", 72)
    step4 = _runner_task("start_step4_publish", "step4_publish")
    wait_step4 = _stage_sensor("wait_step4_publish", "step4_publish")
    acquire_result = PythonSensor(
        task_id="acquire_result_transfer_slot",
        python_callable=acquire_transfer_slot,
        op_kwargs={"kind": "result"},
        mode="reschedule",
        poke_interval=30,
        timeout=48 * 3600,
        pool="wgs_obs_download",
    )
    step5 = _runner_task("start_step5_download", "step5_download")
    wait_step5 = _stage_sensor("wait_step5_download", "step5_download")
    release_result = PythonOperator(
        task_id="release_result_transfer_slot",
        python_callable=release_stage,
        op_kwargs={"stage": "release_result_transfer_slot"},
        trigger_rule=TriggerRule.ALL_DONE,
    )
    step6 = _runner_task("materialize_step6_results", "step6_materialize")
    wait_step6 = _stage_sensor("wait_step6_materialize", "step6_materialize", 24)
    finalize = PythonOperator(
        task_id="finalize_run",
        python_callable=release_stage,
        op_kwargs={"stage": "finalize_run"},
    )
    release = PythonOperator(
        task_id="release_leases",
        python_callable=release_leases,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    validate >> prepare >> wait_prepare >> acquire_input >> step1 >> wait_step1
    wait_step1 >> release_input >> step2 >> wait_step2 >> step3 >> wait_step3
    wait_step3 >> step4 >> wait_step4 >> acquire_result >> step5 >> wait_step5
    wait_step5 >> release_result >> step6 >> wait_step6 >> finalize >> release
