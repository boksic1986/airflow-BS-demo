from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
import re
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule


ANALYSIS_ID_RE = re.compile(r"^WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")
RUNNER_STAGES = {
    "prepare",
    "step1_upload",
    "step2_master",
    "step3_monitor",
    "step4_publish",
    "step5_download",
    "step6_materialize",
}
ASYNC_RUNNER_STAGES = {
    "step1_upload",
    "step3_monitor",
    "step4_publish",
    "step5_download",
}


def validate_request(**context: Any) -> dict[str, Any]:
    conf = dict(context["dag_run"].conf or {})
    params = dict(conf.get("params") or {})
    analysis_id = str(conf.get("analysis_id") or "")
    if conf.get("pipeline") != "wgs" or conf.get("execution_mode") != "cce":
        raise ValueError("pipeline=wgs and execution_mode=cce are required")
    if not ANALYSIS_ID_RE.fullmatch(analysis_id):
        raise ValueError("analysis_id must be a generated WGS identifier")
    if not isinstance(conf.get("attempt"), int) or int(conf["attempt"]) < 1:
        raise ValueError("attempt must be a positive integer")
    if not str(conf.get("workdir") or "").strip():
        raise ValueError("workdir is required")
    for field in (
        "project_name",
        "batch_no",
        "fq_path",
        "pipeline_release_id",
        "wgs_version",
        "wgs_source_commit",
    ):
        if not str(params.get(field) or "").strip():
            raise ValueError(f"{field} is required")
    return conf


def register_stage(stage: str, **context: Any) -> dict[str, Any]:
    _require_runtime_enabled()
    conf = dict(context["dag_run"].conf or {})
    return _backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/stages/{stage}",
        method="POST",
        payload={
            "attempt": conf["attempt"],
            "adapter": "wgs-runtime-200",
            "command": f"wgs-runtime {conf['analysis_id']} {conf['attempt']} {stage}",
        },
    )


def run_stage_on_200(stage: str, **context: Any) -> dict[str, Any]:
    if stage not in RUNNER_STAGES:
        raise ValueError(f"unsupported runner stage: {stage}")
    registered = register_stage(stage, **context)
    conf = dict(context["dag_run"].conf or {})
    command = [
        "ssh",
        "-tt",
        "-F",
        os.getenv("WGS_SSH_CONFIG_PATH", "/opt/airflow/ssh/config"),
        os.getenv("WGS_RUNNER_200_ALIAS", "wgs-node200"),
        "/home/chenjc/.config/airflow-wgs/forced-command.sh",
        "wgs-runtime",
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
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "")[-2000:]
        raise RuntimeError(
            f"restricted node200 WGS stage failed ({completed.returncode}): {error}"
        )
    return {**registered, "runner_status": "accepted"}


def stage_ready(stage: str, **context: Any) -> bool:
    _require_runtime_enabled()
    conf = dict(context["dag_run"].conf or {})
    query = urlencode({"attempt": conf["attempt"], "stage": stage})
    payload = _backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/stage-status?{query}"
    )
    if payload.get("failed"):
        raise RuntimeError(str(payload.get("message") or f"WGS stage failed: {stage}"))
    return bool(payload.get("ready"))


def release_leases(**context: Any) -> dict[str, Any]:
    conf = dict(context["dag_run"].conf or {})
    if not _runtime_enabled():
        return {"released": False, "reason": "runtime adapter disabled"}
    return _backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/stages/release_leases",
        method="POST",
        payload={"attempt": conf["attempt"], "adapter": "wgs-runtime-200"},
    )


def acquire_transfer_slot(stage: str, **context: Any) -> bool:
    return bool(register_stage(stage, **context).get("acquired"))


def _backend_json(
    path: str, *, method: str = "GET", payload: dict | None = None
) -> dict[str, Any]:
    base_url = os.getenv("BACKEND_BASE_URL", "http://backend:8000").rstrip("/")
    token = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["X-Airflow-Demo-Token"] = token
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(f"{base_url}{path}", headers=headers, data=body, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"backend WGS stage API is unavailable: {exc}") from exc


def _truthy(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def _runtime_enabled() -> bool:
    return _truthy("WGS_EXECUTION_ENABLED") and _truthy(
        "WGS_RUNTIME_ADAPTER_ENABLED"
    )


def _require_runtime_enabled() -> None:
    if not _runtime_enabled():
        raise RuntimeError("WGS runtime adapter is disabled")


def control_stage(
    task_id: str, *, stage: str, pool: str | None = None
) -> PythonOperator:
    return PythonOperator(
        task_id=task_id,
        python_callable=register_stage,
        op_kwargs={"stage": stage},
        pool=pool,
        execution_timeout=timedelta(minutes=2),
    )


def transfer_slot_sensor(task_id: str, *, stage: str) -> PythonSensor:
    return PythonSensor(
        task_id=task_id,
        python_callable=acquire_transfer_slot,
        op_kwargs={"stage": stage},
        mode="reschedule",
        poke_interval=5,
        timeout=48 * 3600,
        pool="wgs_obs_transfer",
    )


def runner_stage(
    task_id: str,
    *,
    stage: str,
    pool: str | None = None,
    timeout_hours: int = 2,
) -> PythonOperator:
    return PythonOperator(
        task_id=task_id,
        python_callable=run_stage_on_200,
        op_kwargs={"stage": stage},
        pool=pool,
        execution_timeout=(
            timedelta(minutes=2)
            if stage in ASYNC_RUNNER_STAGES
            else timedelta(hours=timeout_hours)
        ),
    )


def stage_sensor(
    task_id: str,
    *,
    stage: str,
    pool: str | None = None,
    timeout_hours: int = 72,
) -> PythonSensor:
    return PythonSensor(
        task_id=task_id,
        python_callable=stage_ready,
        op_kwargs={"stage": stage},
        mode="reschedule",
        poke_interval=5,
        timeout=timeout_hours * 3600,
        pool=pool,
    )


with DAG(
    dag_id="bio_wgs",
    description="Current WGS release CCE Step1-Step6 orchestration through node200",
    start_date=datetime(2026, 8, 26),
    schedule=None,
    catchup=False,
    max_active_runs=4,
    is_paused_upon_creation=True,
    tags=["airflow-demo", "wgs", "cce", "node200"],
) as dag:
    validate = PythonOperator(
        task_id="validate_request", python_callable=validate_request
    )
    prepare = runner_stage(
        "prepare_wgs_batch", stage="prepare", timeout_hours=2
    )

    with TaskGroup(group_id="input_transfer") as input_transfer:
        input_lease = transfer_slot_sensor(
            "acquire_obs_transfer_slot",
            stage="acquire_input_transfer_slot",
        )
        input_upload = runner_stage(
            "start_step1_upload",
            stage="step1_upload",
            pool="wgs_obs_transfer",
            timeout_hours=48,
        )
        input_wait = stage_sensor(
            "wait_step1_upload", stage="step1_upload", timeout_hours=48
        )
        input_release = control_stage(
            "release_obs_transfer_slot", stage="release_input_transfer_slot"
        )
        input_lease >> input_upload >> input_wait >> input_release

    submit = runner_stage(
        "submit_step2_master", stage="step2_master", pool="wgs_cce_runs"
    )
    start_monitor = runner_stage(
        "start_step3_monitor", stage="step3_monitor", pool="wgs_cce_runs"
    )
    wait_analysis = stage_sensor(
        "wait_step3_analysis",
        stage="step3_monitor",
        pool="wgs_cce_runs",
        timeout_hours=120,
    )
    start_publish = runner_stage(
        "start_step4_publish", stage="step4_publish", timeout_hours=48
    )
    wait_publish = stage_sensor(
        "wait_step4_publish", stage="step4_publish", timeout_hours=48
    )

    with TaskGroup(group_id="result_transfer") as result_transfer:
        result_lease = transfer_slot_sensor(
            "acquire_obs_transfer_slot",
            stage="acquire_result_transfer_slot",
        )
        result_download = runner_stage(
            "start_step5_download",
            stage="step5_download",
            pool="wgs_obs_transfer",
            timeout_hours=48,
        )
        result_wait = stage_sensor(
            "wait_step5_download", stage="step5_download", timeout_hours=48
        )
        result_release = control_stage(
            "release_obs_transfer_slot", stage="release_result_transfer_slot"
        )
        result_lease >> result_download >> result_wait >> result_release

    materialize = runner_stage(
        "materialize_step6_results", stage="step6_materialize", timeout_hours=24
    )
    finalize = control_stage("finalize_run", stage="finalize_run")
    release = PythonOperator(
        task_id="release_leases",
        python_callable=release_leases,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    validate >> prepare >> input_transfer >> submit
    submit >> start_monitor >> wait_analysis >> start_publish >> wait_publish
    wait_publish >> result_transfer >> materialize >> finalize >> release
