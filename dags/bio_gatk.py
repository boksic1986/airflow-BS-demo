from __future__ import annotations

from datetime import datetime, timedelta
from http.client import IncompleteRead, RemoteDisconnected
import json
import logging
import os
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from airflow import DAG
from airflow.exceptions import AirflowException, AirflowFailException, AirflowSkipException
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
from airflow.utils.trigger_rule import TriggerRule

from common.stage_execution import (
    DispatchUncertain,
    execution_ref_from_registration,
    observe_stage,
    submit_stage,
)
from common.ssh_transport import run_ssh


LOG = logging.getLogger(__name__)


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
        # Do not put upstream response bodies or credential-bearing URLs in logs.
        if exc.code in {408, 429, 500, 502, 503, 504}:
            raise AirflowException(
                f"GATK backend temporarily unavailable (HTTP {exc.code})"
            ) from None
        raise AirflowFailException(
            f"GATK backend rejected request (HTTP {exc.code})"
        ) from None
    except (URLError, TimeoutError, ConnectionError, IncompleteRead, RemoteDisconnected):
        raise AirflowException("GATK backend transport temporarily unavailable") from None
    except (ValueError, UnicodeError):
        raise AirflowFailException("GATK backend response is not valid UTF-8 JSON") from None
    if not isinstance(value, dict):
        raise AirflowFailException("GATK backend response must be an object")
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


def stage_should_run(stage: str, conf: dict[str, Any]) -> bool:
    if not conf.get('resume_action_id'):
        return True
    if stage in {'finalize_run', 'release_leases'}:
        return True
    required = {'acquire_input_transfer_slot':'step1_upload',
                'release_input_transfer_slot':'step1_upload',
                'acquire_result_transfer_slot':'step5_download',
                'release_result_transfer_slot':'step5_download'}.get(stage, stage)
    return required in conf.get('resume_stages', [])


def register_stage(
    stage: str, *, worker_observation: dict[str, Any] | None = None,
    **context: Any,
) -> dict[str, Any]:
    conf = dict(context["dag_run"].conf or {})
    if not stage_should_run(stage, conf):
        return {'stage':stage, 'status':'skipped', 'acquired':True}
    payload = {"attempt": conf["attempt"], "adapter": "gatk-runtime-200"}
    if conf.get('resume_action_id'):
        payload['resume_action_id'] = conf['resume_action_id']
    if conf.get('resume_action_id') or stage in {"step4_publish", "release_input_transfer_slot", "release_result_transfer_slot", "release_leases", "finalize_run"}:
        payload["dag_run_id"] = context["dag_run"].run_id
    if worker_observation is not None:
        if stage != "finalize_run":
            raise AirflowFailException("native GATK final observation has the wrong stage")
        payload["worker_observation"] = worker_observation
    return _backend_json(
        f"/api/internal/gatk/runs/{conf['analysis_id']}/stages/{stage}",
        method="POST",
        payload=payload,
    )


def run_stage(stage: str, **context: Any) -> dict[str, Any]:
    if stage not in RUNNER_STAGES:
        raise ValueError(f"unsupported GATK runner stage: {stage}")
    registered = register_stage(stage, **context)
    if registered.get('status') == 'skipped':
        return registered
    conf = dict(context["dag_run"].conf or {})
    from cce_publish_dispatch import enabled, start_publish
    if stage == 'step4_publish' and enabled(conf):
        return start_publish(_backend_json,pipeline='gatk',conf=conf,dag_run_id=context['dag_run'].run_id)
    marker = registered.get("stage_execution")
    if marker is not None:
        if marker != {"protocol": "cce.stage-execution.v1"} or stage == "prepare":
            raise AirflowFailException("unsupported registered GATK stage execution")
        initial = _native_observe_stage(conf, stage, registered)
        ref = execution_ref_from_registration(
            initial, registered, pipeline="gatk", stage=stage
        )
        result = submit_stage(
            execution_ref=ref,
            dispatch=lambda exact: _native_dispatch_stage(conf, stage, exact),
            observe=lambda exact: _native_observe_stage(conf, stage, exact),
            deadline=None,
        )
        if result["state"] in {"failed", "canceled"}:
            raise AirflowFailException(f"registered GATK stage {stage} ended {result['state']}")
        return result
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
        str(registered["generation"]),
    ]
    if stage == "prepare":
        completed = subprocess.run(
            command, check=False, stdin=subprocess.DEVNULL,
            capture_output=True, text=True,
        )
    else:
        try:
            completed = run_ssh(command, timeout_seconds=120)
        except (OSError, subprocess.SubprocessError) as error:
            raise RuntimeError("restricted node200 GATK stage SSH outcome is uncertain") from error
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


_NATIVE_SUBMIT_TASK = {
    "step1_upload": "start_step1_upload",
    "step2_master": "submit_step2_master",
    "step3_monitor": "start_step3_monitor",
    "step4_publish": "start_step4_publish",
    "step5_download": "start_step5_download",
    "step6_materialize": "materialize_step6_results",
}


def _native_ssh_command(*arguments: str) -> list[str]:
    return [
        "ssh", "-tt", "-F",
        os.getenv("GATK_SSH_CONFIG_PATH", "/opt/airflow/ssh/config"),
        os.getenv("GATK_RUNNER_200_ALIAS", "gatk-node200"),
        os.getenv("GATK_RUNNER_200_COMMAND", "/home/ctapa/.config/airflow-gatk/forced-command.sh"),
        *arguments,
    ]


def _native_reply(stdout: str) -> dict[str, Any]:
    for line in reversed(str(stdout or "").splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return {}


def _native_observe_stage(conf: dict, stage: str, identity: dict) -> dict:
    if (identity.get("analysis_id") != conf["analysis_id"]
            or identity.get("attempt") != conf["attempt"]
            or identity.get("stage") != stage):
        raise AirflowFailException("native GATK observation identity differs")
    generation = identity.get("stage_generation", identity.get("generation"))
    command = _native_ssh_command(
        "--native-observe", str(conf["analysis_id"]), str(conf["attempt"]), stage,
        str(identity.get("execution_id")), str(generation), str(identity.get("request_hash")),
    )
    try:
        completed = run_ssh(command, timeout_seconds=120)
    except (OSError, subprocess.SubprocessError) as error:
        raise AirflowException("native GATK observation transport unavailable") from error
    if completed.returncode == 255:
        raise AirflowException("native GATK observation transport unavailable")
    if completed.returncode:
        raise AirflowFailException("native GATK observation rejected the registered identity")
    return _native_reply(completed.stdout)


def _native_dispatch_stage(conf: dict, stage: str, identity: dict) -> dict:
    if (identity.get("analysis_id") != conf["analysis_id"]
            or identity.get("attempt") != conf["attempt"]
            or identity.get("stage") != stage):
        raise AirflowFailException("native GATK dispatch identity differs")
    command = _native_ssh_command(
        "--native-submit", str(conf["analysis_id"]), str(conf["attempt"]), stage,
        str(identity["execution_id"]), str(identity["stage_generation"]),
        str(identity["request_hash"]),
    )
    try:
        completed = run_ssh(command, timeout_seconds=120)
    except (OSError, subprocess.SubprocessError) as error:
        raise DispatchUncertain("native GATK dispatch outcome requires exact observation") from error
    if completed.returncode:
        raise DispatchUncertain("native GATK dispatch outcome requires exact observation")
    result = _native_reply(completed.stdout)
    if result.get("schema") != "cce.stage-execution.snapshot.v1":
        raise DispatchUncertain("native GATK dispatch reply lacks a full snapshot")
    return result


def _native_submitted_snapshot(stage: str, context: dict) -> dict | None:
    task = _NATIVE_SUBMIT_TASK.get(stage)
    ti = context.get("ti") or context.get("task_instance")
    if task is None or ti is None:
        return None
    value = ti.xcom_pull(task_ids=task)
    if isinstance(value, dict) and value.get("schema") == "cce.stage-execution.snapshot.v1":
        return value
    if isinstance(value, dict) and ("execution_ref" in value or "schema" in value):
        raise AirflowFailException("GATK submit XCom contains an invalid native snapshot")
    return None


def _step6_final_observation(**context: Any) -> dict[str, Any] | None:
    """Freshly observe the current Step6 before asking backend to finalize."""
    conf = dict(context["dag_run"].conf or {})
    stage = "step6_materialize"
    query = urlencode({"attempt": conf["attempt"], "stage": stage})
    status = _backend_json(
        f"/api/internal/gatk/runs/{conf['analysis_id']}/stage-status?{query}"
    )
    submitted = _native_submitted_snapshot(stage, context)
    marker = status.get("stage_execution")
    if marker is None:
        if submitted is not None:
            raise AirflowFailException("GATK Step6 native registration marker disappeared")
        return None  # Existing unmarked stage retains its legacy finalization.
    if marker != {"protocol": "cce.stage-execution.v1"}:
        raise AirflowFailException("GATK Step6 stage execution marker is invalid")
    if status.get("ready") is not True:
        raise AirflowException("GATK Step6 business receipt is not ready for finalization")
    if submitted is None:
        # Recovery may reuse a successful Step6 and skip its submit task. The
        # current backend status gives its registered tuple; the gate supplies
        # the full native ref without a new dispatch or generation.
        current = _native_observe_stage(conf, stage, status)
        execution_ref_from_registration(current, status, pipeline="gatk", stage=stage)
    else:
        ref = execution_ref_from_registration(
            submitted, status, pipeline="gatk", stage=stage
        )
        current = observe_stage(
            execution_ref=ref,
            observe=lambda exact: _native_observe_stage(conf, stage, exact),
        )
    if current["state"] != "succeeded":
        raise AirflowException("GATK Step6 native terminal is not confirmed")
    return current


def stage_ready(stage: str, **context: Any) -> bool:
    conf = dict(context["dag_run"].conf or {})
    if not stage_should_run(stage, conf):
        return True
    query = urlencode({"attempt": conf["attempt"], "stage": stage})
    value = _backend_json(
        f"/api/internal/gatk/runs/{conf['analysis_id']}/stage-status?{query}"
    )
    policy = dict(dict(conf.get('params') or {}).get('cce_recovery_policy') or {})
    if stage == 'step4_publish' and policy.get('enabled') is True and policy.get('attempt') == conf['attempt']:
        from cce_publish_dispatch import poll_publish
        recovery = poll_publish(_backend_json,pipeline='gatk',conf=conf,dag_run_id=context['dag_run'].run_id)
        if recovery.get('status') != 'success':
            return False
    if stage == 'step3_monitor' and policy.get('enabled') is True and policy.get('attempt') == conf['attempt']:
        from cce_worker_wait import poll_recovery
        recovery = poll_recovery(_backend_json,pipeline='gatk',conf=conf,
            dag_run_id=context['dag_run'].run_id)
        if recovery.get('status') in {'waiting', 'uncertain'}:
            return False
        if recovery.get('status') in {'delegated', 'superseded'}:
            raise AirflowSkipException('Compute recovery delegated to the current DagRun')
    submitted = _native_submitted_snapshot(stage, context)
    marker = value.get("stage_execution")
    if marker is None:
        if submitted is not None:
            raise AirflowFailException("GATK native registration marker disappeared")
    elif marker != {"protocol": "cce.stage-execution.v1"} or stage == "prepare":
        raise AirflowFailException("GATK stage execution marker is invalid")
    if value.get("failed"):
        # A terminal runtime receipt is not a transient polling failure.
        raise AirflowFailException(str(value.get("message") or f"GATK stage failed: {stage}"))
    if marker is None:
        return bool(value.get("ready"))  # Existing unmarked stage retains its legacy sensor.
    if submitted is None:
        # A same-attempt recovery may reuse the registered stage without a
        # submit XCom. Observe the latest backend tuple before advancing.
        current = _native_observe_stage(conf, stage, value)
        execution_ref_from_registration(current, value, pipeline="gatk", stage=stage)
    else:
        ref = execution_ref_from_registration(
            submitted, value, pipeline="gatk", stage=stage
        )
        current = observe_stage(
            execution_ref=ref,
            observe=lambda exact: _native_observe_stage(conf, stage, exact),
        )
    if current["state"] in {"failed", "canceled"}:
        raise AirflowFailException(f"registered GATK stage {stage} ended {current['state']}")
    return current["state"] == "succeeded" and value.get("ready") is True


def acquire_transfer_slot(kind: str, **context: Any) -> bool:
    stage = f"acquire_{kind}_transfer_slot"
    return bool(register_stage(stage, **context).get("acquired"))


def release_stage(stage: str, **context: Any) -> dict[str, Any]:
    observation = _step6_final_observation(**context) if stage == "finalize_run" else None
    result = register_stage(stage, worker_observation=observation, **context)
    if stage in {"release_input_transfer_slot", "release_result_transfer_slot", "release_leases"} and result.get("retained"):
        raise RuntimeError("GATK transfer lease was not released: " + str(result.get("reason") or "unknown"))
    return result


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


def report_dag_failure(context: dict[str, Any]) -> None:
    """Best-effort projection of a failed GATK DagRun into biodemo."""
    dag_run = context.get("dag_run")
    if dag_run is None:
        LOG.error("Cannot report GATK DAG failure without dag_run context")
        return
    conf = dict(dag_run.conf or {})
    analysis_id = str(conf.get("analysis_id") or "")
    attempt = int(conf.get("attempt") or 0)
    if not analysis_id.startswith("GATK_") or attempt < 1:
        LOG.error("Cannot report GATK DAG failure with invalid run identity")
        return

    failed_task_ids: list[str] = []
    for task_instance in dag_run.get_task_instances():
        raw_state = getattr(task_instance, "state", None)
        state = str(getattr(raw_state, "value", raw_state) or "").lower()
        if state == "failed":
            failed_task_ids.append(str(getattr(task_instance, "task_id", "")))
    failed_task_ids = sorted({task_id for task_id in failed_task_ids if task_id})
    if len(failed_task_ids) > 1 and "release_leases" in failed_task_ids:
        failed_task_ids.remove("release_leases")

    try:
        _backend_json(
            f"/api/internal/gatk/runs/{analysis_id}/dag-terminal",
            method="POST",
            payload={
                "attempt": attempt,
                "status": "failed",
                "failed_task_ids": failed_task_ids,
                "dag_run_id": dag_run.run_id,
            },
        )
    except Exception:
        LOG.exception(
            "Failed to project terminal GATK DagRun state for %s attempt %s",
            analysis_id,
            attempt,
        )


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
        # Retry only observation, never stage registration/SSH dispatch. Airflow
        # persists try_number across reschedules; analysis attempt stays fixed.
        retries=6,
        retry_delay=timedelta(seconds=30),
        retry_exponential_backoff=True,
        max_retry_delay=timedelta(minutes=5),
    )


with DAG(
    dag_id="bio_gatk",
    description="Manual SCMC GATK Cloud Step1-Step6 orchestration",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    on_failure_callback=report_dag_failure,
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
        # Same analysis/attempt/transfer identity reclaims its existing slot;
        # retry this gate only, never the upload or SSH stage itself.
        retries=6,
        retry_delay=timedelta(seconds=30),
        retry_exponential_backoff=True,
        max_retry_delay=timedelta(minutes=5),
    )
    step1 = _runner_task("start_step1_upload", "step1_upload")
    wait_step1 = _stage_sensor("wait_step1_upload", "step1_upload")
    release_input = PythonOperator(
        task_id="release_input_transfer_slot",
        python_callable=release_stage,
        op_kwargs={"stage": "release_input_transfer_slot"},
        trigger_rule=TriggerRule.ALL_DONE,
    )
    step2 = _runner_task("submit_step2_master", "step2_master")
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
        retries=6,
        retry_delay=timedelta(seconds=30),
        retry_exponential_backoff=True,
        max_retry_delay=timedelta(minutes=5),
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
    # ALL_DONE cleanup releases capacity; it does not prove the stage succeeded.
    wait_step1 >> step2
    wait_step5 >> step6
