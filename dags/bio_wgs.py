from __future__ import annotations

from datetime import datetime, timedelta
from http.client import IncompleteRead, RemoteDisconnected
import json
import logging
import os
import re
import subprocess
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from airflow import DAG
from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.sensors.python import PythonSensor
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

from common.stage_execution import (
    DispatchUncertain,
    execution_ref_from_registration,
    observe_stage,
    submit_and_await,
    submit_stage,
)
from common.ssh_transport import SSHCallBudget, pre_session_failure, run_ssh


ANALYSIS_ID_RE = re.compile(r"^WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")
RUNNER_STAGES = {
    "prepare",
    "prepare_sampleinfo",
    "prepare_analysis",
    "step1_upload",
    "step2_master",
    "step3_monitor",
    "step4_publish",
    "step5_download",
    "step6_materialize",
    "step7_cleanup",
}
ASYNC_RUNNER_STAGES = {
    "step1_upload",
    "step3_monitor",
    "step4_publish",
    "step5_download",
    "step7_cleanup",
}
LOG = logging.getLogger(__name__)
RECOVERY_STAGES = {'step1_upload', 'step2_master', 'step3_monitor', 'step4_publish', 'step5_download', 'step6_materialize'}


class BackendTransportUnavailable(RuntimeError):
    pass


class BackendStagePredecessorPending(RuntimeError):
    pass


RUNNER_REQUEST_VISIBILITY_ATTEMPTS = 5
RUNNER_REQUEST_VISIBILITY_DELAY_SECONDS = 1.0
STAGE_GENERATION_VISIBILITY_TIMEOUT_SECONDS = 120.0
STAGE_PREDECESSOR_VISIBILITY_ATTEMPTS = 5
STAGE_PREDECESSOR_VISIBILITY_DELAY_SECONDS = 5.0
FAILED_STAGE_SYNC_TIMEOUT_SECONDS = 30.0
def _runner_request_not_yet_visible(completed: subprocess.CompletedProcess[str]) -> bool:
    if completed.returncode == 0:
        return False
    error = "\n".join(
        part for part in (completed.stdout, completed.stderr) if part
    )
    return (
        "registered runtime request is missing" in error
        or (
            "runner-requests/" in error
            and "FileNotFoundError: [Errno 2] No such file or directory" in error
        )
    )


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
    maintenance_mode = conf.get("maintenance_mode")
    if conf.get('resume_action_id'):
        stages = conf.get('resume_stages')
        if maintenance_mode or conf.get('resume_stage') not in RECOVERY_STAGES or not isinstance(stages, list) or not stages or stages[0] != conf['resume_stage'] or any(stage not in RECOVERY_STAGES for stage in stages):
            raise AirflowFailException('invalid WGS recovery stage selection')
    if maintenance_mode is not None:
        if maintenance_mode not in {"repair_step4", "cleanup_step7"}:
            raise ValueError("unsupported WGS maintenance mode")
        if maintenance_mode == "repair_step4":
            if conf.get("repair_group") != "cram":
                raise ValueError("Step4 maintenance is fixed to the cram linkage group")
            if not isinstance(conf.get("continue_after_repair"), bool):
                raise ValueError("continue_after_repair must be boolean")
    validation_scope = params.get("validation_scope")
    if validation_scope is not None:
        if validation_scope not in {"step1_only", "step3_dryrun", "node97_full"}:
            raise ValueError("unsupported WGS validation scope")
        if validation_scope == "step1_only" and not _truthy(
            "WGS_STEP1_CANARY_ENABLED"
        ):
            raise ValueError("Step1 canary is disabled")
        if validation_scope == "step3_dryrun" and not _truthy(
            "WGS_STEP3_DRYRUN_CANARY_ENABLED"
        ):
            raise ValueError("Step3 dry-run canary is disabled")
        if validation_scope == "node97_full" and not _truthy(
            "WGS_NODE97_FULL_CANARY_ENABLED"
        ):
            raise ValueError("node97 full canary is disabled")
        if not _truthy("WGS_CONTRACT_V2_ENABLED"):
            raise ValueError("WGS validation canary requires contract v2")
    return conf


def choose_run_path(**context: Any) -> str:
    """Route Step7 maintenance before any production preparation or transfer gate."""

    conf = dict(context["dag_run"].conf or {})
    if conf.get("maintenance_mode") == "cleanup_step7":
        return "step7_cleanup"
    return "prepare_wgs_sampleinfo"


def choose_after_step1(**context: Any) -> str:
    params = dict((context["dag_run"].conf or {}).get("params") or {})
    if params.get("validation_scope") == "step1_only":
        return "finalize_step1_canary"
    return "submit_step2_master"


def choose_after_step3(**context: Any) -> str:
    params = dict((context["dag_run"].conf or {}).get("params") or {})
    if params.get("validation_scope") == "step3_dryrun":
        return "finalize_step3_dryrun"
    return "start_step4_publish"


def uses_staged_prepare(conf: dict[str, Any]) -> bool:
    return str(dict(conf.get("params") or {}).get("submission_mode") or "") in {
        "three_stage",
        "auto_dispatch",
    }


def stage_should_run(stage: str, conf: dict[str, Any]) -> bool:
    if conf.get('resume_action_id'):
        stages = conf['resume_stages']
        if stage in {'acquire_input_transfer_slot', 'release_input_transfer_slot'}:
            return 'step1_upload' in stages
        if stage in {'acquire_result_transfer_slot', 'release_result_transfer_slot'}:
            return 'step5_download' in stages
        return stage in stages or stage in {'finalize_run', 'release_leases'}
    if conf.get("maintenance_mode") == "cleanup_step7":
        return stage == "step7_cleanup"
    if conf.get("maintenance_mode") != "repair_step4":
        if stage == "prepare_analysis" and not uses_staged_prepare(conf):
            return False
        return True
    if stage == "step4_publish":
        return True
    if stage in {
        "prepare",
        "prepare_sampleinfo",
        "prepare_analysis",
        "acquire_input_transfer_slot",
        "step1_upload",
        "release_input_transfer_slot",
        "step2_master",
        "step3_monitor",
    }:
        return False
    if stage in {
        "acquire_result_transfer_slot",
        "step5_download",
        "release_result_transfer_slot",
        "step6_materialize",
        "finalize_run",
    }:
        return bool(conf.get("continue_after_repair"))
    return True


def effective_runner_stage(stage: str, conf: dict[str, Any]) -> str:
    if conf.get("maintenance_mode") == "repair_step4" and stage == "step4_publish":
        return "step4_repair_cram"
    if stage == "prepare_sampleinfo" and not uses_staged_prepare(conf):
        return "prepare"
    return stage


def register_stage(stage: str, **context: Any) -> dict[str, Any]:
    conf = dict(context["dag_run"].conf or {})
    if not stage_should_run(stage, conf):
        return {"skipped": True, "stage": stage, "maintenance_mode": conf.get("maintenance_mode")}
    _require_runtime_enabled()
    runner_stage = effective_runner_stage(stage, conf)
    request_payload = {
        "attempt": conf["attempt"],
        "adapter": "wgs-runtime-200",
        "command": f"wgs-runtime {conf['analysis_id']} {conf['attempt']} {runner_stage}",
        "maintenance_action_id": conf.get("maintenance_action_id"),
        "resume_action_id": conf.get("resume_action_id"),
    }
    if conf.get('resume_action_id') or stage in {"step4_publish", "finalize_run", "release_input_transfer_slot", "release_result_transfer_slot", "release_leases"}:
        request_payload["dag_run_id"] = context["dag_run"].run_id
    if stage == "finalize_run":
        terminal = _step6_finalization_observation(conf, context)
        if terminal is not None:
            request_payload["worker_observation"] = terminal
    task_instance = context.get("ti") or context.get("task_instance")
    # A retried Step1-6 task must reattach its registered execution. A new
    # generation is authorized by the explicit recovery API, not try_number.
    if (int(getattr(task_instance, "try_number", 1) or 1) > 1
            and (stage not in RECOVERY_STAGES or conf.get("maintenance_mode") is not None
                 or runner_stage != stage)):
        request_payload["force_new_generation"] = True
    path = f"/api/internal/wgs/runs/{conf['analysis_id']}/stages/{runner_stage}"
    for registration_attempt in range(
        1, STAGE_PREDECESSOR_VISIBILITY_ATTEMPTS + 1
    ):
        try:
            response = _backend_json(path, method="POST", payload=request_payload)
            _raise_if_transfer_lease_retained(stage=stage, response=response)
            return response
        except BackendStagePredecessorPending:
            if registration_attempt == STAGE_PREDECESSOR_VISIBILITY_ATTEMPTS:
                raise
            LOG.warning(
                "exact predecessor receipt is not visible to backend yet; "
                "retrying stage registration (%s/%s)",
                registration_attempt,
                STAGE_PREDECESSOR_VISIBILITY_ATTEMPTS,
            )
            time.sleep(STAGE_PREDECESSOR_VISIBILITY_DELAY_SECONDS)
    raise RuntimeError("unreachable WGS stage registration state")


def run_stage_on_200(stage: str, **context: Any) -> dict[str, Any]:
    if stage not in RUNNER_STAGES:
        raise ValueError(f"unsupported runner stage: {stage}")
    registered = register_stage(stage, **context)
    conf = dict(context["dag_run"].conf or {})
    if registered.get("skipped"):
        return registered
    runner_stage = effective_runner_stage(stage, conf)
    from cce_publish_dispatch import enabled, start_publish
    if runner_stage == 'step4_publish' and enabled(conf):
        return start_publish(_stage_query_json,pipeline='wgs',conf=conf,dag_run_id=context['dag_run'].run_id)
    marker = registered.get("stage_execution")
    if marker is not None:
        if marker != {"protocol": "cce.stage-execution.v1"} or runner_stage not in RECOVERY_STAGES:
            raise AirflowFailException("unsupported registered WGS stage execution")
        initial = _native_observe_stage(conf, runner_stage, registered)
        ref = execution_ref_from_registration(
            initial, registered, pipeline="wgs", stage=runner_stage
        )
        dispatch = lambda exact: _native_dispatch_stage(conf, runner_stage, exact)
        observe = lambda current: _native_observe_stage(conf, runner_stage, current)
        if runner_stage == "step2_master":
            result = submit_and_await(
                execution_ref=ref, dispatch=dispatch, observe=observe,
                deadline=None,
            )
        else:
            result = submit_stage(
                execution_ref=ref, dispatch=dispatch, observe=observe, deadline=None
            )
        if result["state"] in {"failed", "canceled"}:
            raise AirflowFailException(f"registered WGS stage {runner_stage} ended {result['state']}")
        if runner_stage == "step3_monitor" and result["state"] != "unknown":
            _backend_json(
                f"/api/internal/wgs/runs/{conf['analysis_id']}/observer/activate",
                method="POST", payload={"attempt": conf["attempt"]},
            )
        return result
    command = [
        "ssh",
        "-tt",
        "-F",
        os.getenv("WGS_SSH_CONFIG_PATH", "/opt/airflow/ssh/config"),
        os.getenv("WGS_RUNNER_200_ALIAS", "wgs-node200"),
        os.getenv(
            "WGS_RUNNER_200_COMMAND",
            "/home/ctapa/.config/airflow-wgs/forced-command.sh",
        ),
        "wgs-runtime",
        str(conf["analysis_id"]),
        str(conf["attempt"]),
        runner_stage,
    ]
    # The current Step1–6 path shares one connection and wall-time allowance
    # across the separate request-visibility invocations below. Historical
    # prepare/Step7 retain their existing runner behavior.
    ssh_budget = SSHCallBudget.start(120) if runner_stage in RECOVERY_STAGES else None
    connection_failures = 0
    invocation = 1
    while True:
        try:
            if ssh_budget is None:
                completed = subprocess.run(
                    command, check=False, stdin=subprocess.DEVNULL,
                    capture_output=True, text=True,
                )
            else:
                completed = run_ssh(command, timeout_seconds=120, budget=ssh_budget)
        except (OSError, subprocess.SubprocessError) as error:
            if ssh_budget is None:
                raise
            _wait_for_terminal_stage_projection(
                analysis_id=str(conf["analysis_id"]), attempt=int(conf["attempt"]),
                stage=runner_stage,
                expected_retry_no=(
                    int(registered["generation"]) - 1
                    if isinstance(registered.get("generation"), int) else None
                ),
            )
            raise RuntimeError("restricted node200 WGS stage SSH outcome is uncertain") from error
        if ssh_budget is None and pre_session_failure(completed):
            if connection_failures >= 2:
                LOG.warning("WGS SSH pre-execution connection attempts exhausted (3/3)")
                break
            delay = (5.0, 10.0)[connection_failures]
            connection_failures += 1
            LOG.warning(
                "WGS SSH pre-execution connection failure; reconnecting (%s/3) in %ss",
                connection_failures + 1, delay,
            )
            time.sleep(delay)
            continue
        if not _runner_request_not_yet_visible(completed):
            break
        if invocation == RUNNER_REQUEST_VISIBILITY_ATTEMPTS:
            break
        if ssh_budget is not None and ssh_budget.remaining() <= RUNNER_REQUEST_VISIBILITY_DELAY_SECONDS:
            break
        LOG.warning(
            "registered WGS runtime request is not visible on node200 yet; "
            "retrying restricted runner invocation (%s/%s)",
            invocation,
            RUNNER_REQUEST_VISIBILITY_ATTEMPTS,
        )
        time.sleep(RUNNER_REQUEST_VISIBILITY_DELAY_SECONDS)
        invocation += 1
    if completed.returncode != 0:
        if completed.returncode == 255 and not pre_session_failure(completed):
            LOG.warning(
                "WGS SSH failure is not proven pre-execution; command will not be "
                "replayed. Checking the registered generation's terminal evidence."
            )
        _wait_for_terminal_stage_projection(
            analysis_id=str(conf["analysis_id"]),
            attempt=int(conf["attempt"]),
            stage=runner_stage,
            expected_retry_no=(
                int(registered["generation"]) - 1
                if isinstance(registered.get("generation"), int)
                else None
            ),
        )
        error = " | ".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part and part.strip()
        )[-2000:]
        raise RuntimeError(
            f"restricted node200 WGS stage failed ({completed.returncode}): {error}"
        )
    runner_reply = _runner_reply(completed.stdout)
    if runner_stage in ASYNC_RUNNER_STAGES and runner_reply.get("status") == "accepted":
        retry_no = runner_reply.get("retry_no")
        if not isinstance(retry_no, int) or retry_no < 0:
            raise RuntimeError(
                f"{runner_stage} runner did not return a valid retry generation"
            )
        _wait_for_registered_stage_generation(
            analysis_id=str(conf["analysis_id"]),
            attempt=int(conf["attempt"]),
            stage=runner_stage,
            expected_retry_no=retry_no,
        )
    if runner_stage == "step3_monitor":
        _backend_json(
            f"/api/internal/wgs/runs/{conf['analysis_id']}/observer/activate",
            method="POST",
            payload={"attempt": conf["attempt"]},
        )
    return {**registered, "runner_status": "accepted"}


def _wait_for_terminal_stage_projection(
    *,
    analysis_id: str,
    attempt: int,
    stage: str,
    expected_retry_no: int | None,
    timeout_seconds: float = FAILED_STAGE_SYNC_TIMEOUT_SECONDS,
) -> None:
    """Give delayed shared-filesystem terminal evidence time to reach the backend."""

    deadline = time.monotonic() + timeout_seconds
    query = urlencode({"attempt": attempt, "stage": stage})
    while True:
        try:
            payload = _backend_json(
                f"/api/internal/wgs/runs/{analysis_id}/stage-status?{query}"
            )
        except BackendTransportUnavailable as exc:
            LOG.warning("Could not synchronize failed %s evidence: %s", stage, exc)
            return
        status = str(payload.get("status") or "pending").lower()
        retry_no = payload.get("retry_no")
        generation_matches = (
            expected_retry_no is None or retry_no == expected_retry_no
        )
        if generation_matches and status in {
            "success",
            "complete",
            "succeeded",
            "failed",
            "canceled",
            "cancelled",
        }:
            return
        if time.monotonic() >= deadline:
            LOG.warning(
                "Runtime terminal evidence for %s was not visible within %ss",
                stage,
                timeout_seconds,
            )
            return
        time.sleep(1)


def _wait_for_registered_stage_generation(
    *,
    analysis_id: str,
    attempt: int,
    stage: str,
    expected_retry_no: int,
    timeout_seconds: float = STAGE_GENERATION_VISIBILITY_TIMEOUT_SECONDS,
) -> None:
    """Do not expose a failed status from a previous async worker generation."""
    deadline = time.monotonic() + timeout_seconds
    query = urlencode({"attempt": attempt, "stage": stage})
    while True:
        payload = _backend_json(
            f"/api/internal/wgs/runs/{analysis_id}/stage-status?{query}"
        )
        if payload.get("retry_no") == expected_retry_no:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"{stage} retry generation {expected_retry_no} was not visible "
                f"within {timeout_seconds:g} seconds"
            )
        time.sleep(1)


def _runner_reply(stdout: str) -> dict[str, Any]:
    for line in reversed(str(stdout or "").splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


_NATIVE_SUBMIT_TASK = {
    "step1_upload": "input_transfer.start_step1_upload",
    "step2_master": "submit_step2_master",
    "step3_monitor": "start_step3_monitor",
    "step4_publish": "start_step4_publish",
    "step5_download": "result_transfer.start_step5_download",
    "step6_materialize": "materialize_step6_results",
}


def _native_ssh_command(*arguments: str) -> list[str]:
    return [
        "ssh", "-tt", "-F",
        os.getenv("WGS_SSH_CONFIG_PATH", "/opt/airflow/ssh/config"),
        os.getenv("WGS_RUNNER_200_ALIAS", "wgs-node200"),
        os.getenv("WGS_RUNNER_200_COMMAND", "/home/ctapa/.config/airflow-wgs/forced-command.sh"),
        *arguments,
    ]


def _native_observe_stage(conf: dict, stage: str, identity: dict) -> dict:
    if (identity.get("analysis_id") != conf["analysis_id"]
            or identity.get("attempt") != conf["attempt"]
            or identity.get("stage") != stage):
        raise AirflowFailException("native WGS observation identity differs")
    generation = identity.get("stage_generation", identity.get("generation"))
    command = _native_ssh_command(
        "--native-observe", str(conf["analysis_id"]), str(conf["attempt"]), stage,
        str(identity.get("execution_id")), str(generation), str(identity.get("request_hash")),
    )
    ssh_budget = SSHCallBudget.start(120)
    for attempt in range(1, RUNNER_REQUEST_VISIBILITY_ATTEMPTS + 1):
        try:
            completed = run_ssh(command, timeout_seconds=120, budget=ssh_budget)
        except (OSError, subprocess.SubprocessError) as error:
            raise BackendTransportUnavailable("native WGS observation transport unavailable") from error
        if completed.returncode == 0:
            return _runner_reply(completed.stdout)
        if not _runner_request_not_yet_visible(completed) or attempt == RUNNER_REQUEST_VISIBILITY_ATTEMPTS:
            break
        if ssh_budget.remaining() <= RUNNER_REQUEST_VISIBILITY_DELAY_SECONDS:
            raise BackendTransportUnavailable("native WGS observation time budget exhausted")
        time.sleep(RUNNER_REQUEST_VISIBILITY_DELAY_SECONDS)
    if completed.returncode == 255:
        raise BackendTransportUnavailable("native WGS observation transport unavailable")
    raise AirflowFailException("native WGS observation rejected the registered identity")


def _native_dispatch_stage(conf: dict, stage: str, identity: dict) -> dict:
    if (identity.get("analysis_id") != conf["analysis_id"]
            or identity.get("attempt") != conf["attempt"]
            or identity.get("stage") != stage):
        raise AirflowFailException("native WGS dispatch identity differs")
    command = _native_ssh_command(
        "--native-submit", str(conf["analysis_id"]), str(conf["attempt"]), stage,
        str(identity["execution_id"]), str(identity["stage_generation"]),
        str(identity["request_hash"]),
    )
    try:
        completed = run_ssh(command, timeout_seconds=120)
    except (OSError, subprocess.SubprocessError) as error:
        raise DispatchUncertain("native WGS dispatch outcome requires exact observation") from error
    if completed.returncode:
        raise DispatchUncertain("native WGS dispatch outcome requires exact observation")
    result = _runner_reply(completed.stdout)
    if result.get("schema") != "cce.stage-execution.snapshot.v1":
        raise DispatchUncertain("native WGS dispatch reply lacks a full snapshot")
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
        raise AirflowFailException("WGS submit XCom contains an invalid native snapshot")
    return None


def _status_matches_native_ref(payload: dict, ref: dict) -> bool:
    return (
        payload.get("stage_execution") == {"protocol": "cce.stage-execution.v1"}
        and ref.get("pipeline") == "wgs"
        and payload.get("analysis_id") == ref.get("analysis_id")
        and payload.get("attempt") == ref.get("attempt")
        and payload.get("stage") == ref.get("stage")
        and payload.get("execution_id") == ref.get("execution_id")
        and payload.get("generation") == ref.get("stage_generation")
        and payload.get("request_hash") == ref.get("request_hash")
    )


def _step6_finalization_observation(conf: dict, context: dict) -> dict | None:
    """Read the current Step6 native terminal even when this DagRun reused Step6."""
    stage = "step6_materialize"
    query = urlencode({"attempt": conf["attempt"], "stage": stage})
    status = _stage_query_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/stage-status?{query}"
    )
    if status is None:
        raise AirflowFailException("Step6 status is unavailable for finalization")
    submitted = _native_submitted_snapshot(stage, context)
    marker = status.get("stage_execution")
    if marker is None:
        if submitted is not None:
            raise AirflowFailException("Step6 native registration is unavailable")
        return None
    if marker != {"protocol": "cce.stage-execution.v1"}:
        raise AirflowFailException("Step6 native registration differs")
    if status.get("ready") is not True or status.get("failed") is True:
        raise AirflowFailException("Step6 business receipt is not ready")
    identity = {
        "analysis_id": conf["analysis_id"],
        "attempt": conf["attempt"],
        "stage": stage,
        "execution_id": status.get("execution_id"),
        "stage_generation": status.get("generation"),
        "request_hash": status.get("request_hash"),
    }
    if submitted is None:
        observed = _native_observe_stage(conf, stage, identity)
        ref = observed.get("execution_ref") if isinstance(observed, dict) else None
        if not isinstance(ref, dict) or not _status_matches_native_ref(status, ref):
            raise AirflowFailException("Step6 native terminal identity differs")
        terminal = observe_stage(execution_ref=ref, observe=lambda _ref: observed)
    else:
        ref = submitted.get("execution_ref")
        if not isinstance(ref, dict) or not _status_matches_native_ref(status, ref):
            raise AirflowFailException("Step6 submitted identity differs from current receipt")
        terminal = observe_stage(
            execution_ref=ref,
            observe=lambda exact: _native_observe_stage(conf, stage, exact),
        )
    if terminal["state"] != "succeeded":
        raise AirflowFailException("Step6 native terminal is not successful")
    return terminal


def stage_ready(stage: str, **context: Any) -> bool:
    conf = dict(context["dag_run"].conf or {})
    if not stage_should_run(stage, conf):
        return True
    _require_runtime_enabled()
    runner_stage = effective_runner_stage(stage, conf)
    query = urlencode({"attempt": conf["attempt"], "stage": runner_stage})
    query_json = _stage_query_json if runner_stage in RECOVERY_STAGES else _sensor_backend_json
    payload = query_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/stage-status?{query}"
    )
    if payload is None:
        return False
    policy = dict(dict(conf.get('params') or {}).get('cce_recovery_policy') or {})
    if runner_stage == 'step4_publish' and policy.get('enabled') is True and policy.get('attempt') == conf['attempt']:
        from cce_publish_dispatch import poll_publish
        recovery = poll_publish(_stage_query_json,pipeline='wgs',conf=conf,dag_run_id=context['dag_run'].run_id)
        if recovery.get('status') != 'success':
            return False
    if runner_stage == 'step3_monitor' and policy.get('enabled') is True and policy.get('attempt') == conf['attempt']:
        # Also reconcile after a lost response: the latest monitor may already
        # belong to the replacement, not to this sensor's DagRun.
        from cce_worker_wait import poll_recovery
        recovery = poll_recovery(_stage_query_json,pipeline='wgs',conf=conf,
            dag_run_id=context['dag_run'].run_id)
        if recovery.get('status') in {'waiting', 'uncertain'}:
            return False
        if recovery.get('status') in {'delegated', 'superseded'}:
            raise AirflowSkipException('Compute recovery delegated to the current DagRun')
    submitted = _native_submitted_snapshot(runner_stage, context)
    fresh_without_xcom = None
    marker = payload.get("stage_execution")
    if submitted is None and marker is not None:
        if marker != {"protocol": "cce.stage-execution.v1"} or runner_stage not in RECOVERY_STAGES:
            raise AirflowFailException("WGS sensor stage execution marker is invalid")
        if payload.get("ready") is True:
            identity = {
                "analysis_id": conf["analysis_id"], "attempt": conf["attempt"],
                "stage": runner_stage, "execution_id": payload.get("execution_id"),
                "stage_generation": payload.get("generation"),
                "request_hash": payload.get("request_hash"),
            }
            fresh_without_xcom = _native_observe_stage(conf, runner_stage, identity)
            ref = (fresh_without_xcom.get("execution_ref")
                   if isinstance(fresh_without_xcom, dict) else None)
            if not isinstance(ref, dict) or not _status_matches_native_ref(payload, ref):
                raise AirflowFailException("WGS sensor native execution identity differs")
            submitted = fresh_without_xcom
    if submitted is not None:
        ref = submitted["execution_ref"]
        if (ref.get("pipeline") != "wgs" or ref.get("analysis_id") != conf["analysis_id"]
                or ref.get("attempt") != conf["attempt"] or ref.get("stage") != runner_stage):
            raise AirflowFailException("WGS sensor native execution identity differs")
        current = observe_stage(
            execution_ref=ref,
            observe=lambda exact: (fresh_without_xcom if fresh_without_xcom is not None
                                   else _native_observe_stage(conf, runner_stage, exact)),
        )
        if current["state"] == "succeeded":
            visible = (payload.get("retry_no") == ref["stage_generation"] - 1
                       and payload.get("ready") is True
                       and _status_matches_native_ref(payload, ref))
            payload = {**payload, "ready": visible, "failed": False}
        elif current["state"] in {"failed", "canceled"}:
            payload = {**payload, "ready": False, "failed": True,
                       "message": f"registered WGS stage {runner_stage} ended {current['state']}"}
        else:
            return False
    if runner_stage == "step3_monitor" and (
        payload.get("failed") or payload.get("ready")
    ):
        try:
            _backend_json(
                f"/api/internal/wgs/runs/{conf['analysis_id']}/observer/deactivate",
                method="POST",
                payload={"attempt": conf["attempt"], "dag_run_id": context["dag_run"].run_id,
                         "resume_action_id": conf.get("resume_action_id")},
            )
        except Exception as error:
            raise AirflowFailException('Observer deactivation outcome requires reconciliation') from error
    if payload.get("failed"):
        error_type = AirflowFailException if runner_stage in RECOVERY_STAGES else RuntimeError
        raise error_type(str(payload.get("message") or f"WGS stage failed: {stage}"))
    return bool(payload.get("ready"))


def submission_gate_ready(gate: str, **context: Any) -> bool:
    if gate not in {"config", "execution"}:
        raise ValueError("unsupported WGS submission gate")
    conf = dict(context["dag_run"].conf or {})
    if conf.get('resume_action_id'):
        return True
    if dict(conf.get("params") or {}).get("submission_mode") != "three_stage":
        return True
    query = urlencode({"attempt": conf["attempt"]})
    payload = _sensor_backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/submission-state?{query}"
    )
    if payload is None:
        return False
    return bool(payload.get(f"{gate}_approved"))


def _sensor_backend_json(
    path: str, *, method: str = "GET", payload: dict | None = None
) -> dict[str, Any] | None:
    try:
        return _backend_json(path, method=method, payload=payload)
    except BackendTransportUnavailable as exc:
        LOG.warning(
            "WGS sensor backend is temporarily unavailable; rescheduling: %s",
            exc,
        )
        return None


def _stage_query_json(path: str, *, method: str = 'GET', payload: dict | None = None) -> dict[str, Any]:
    """Stage polling and idempotent recovery reconciliation share transport retries."""
    try:
        value = _backend_json(path, method=method, payload=payload)
        if not isinstance(value, dict):
            raise AirflowFailException('WGS stage query returned a non-object payload')
        return value
    except BackendTransportUnavailable:
        raise
    except (ConnectionError, IncompleteRead, RemoteDisconnected) as error:
        raise BackendTransportUnavailable('WGS stage query connection interrupted') from error
    except (RuntimeError, ValueError) as error:
        raise AirflowFailException(str(error)) from error


def execution_commit_ready(**context: Any) -> bool:
    """Atomically commit the latest database-backed target when its slot is ready."""
    conf = dict(context["dag_run"].conf or {})
    if conf.get('resume_action_id'):
        return True
    if dict(conf.get("params") or {}).get("maintenance_action"):
        return True
    payload = _sensor_backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/execution-commit",
        method="POST",
        payload={"attempt": conf["attempt"]},
    )
    return bool(payload and payload.get("committed"))


def choose_execution_target(**context: Any) -> str:
    """Route exactly once using the target frozen by ``execution_commit_ready``."""
    conf = dict(context["dag_run"].conf or {})
    if conf.get('resume_action_id'):
        return 'input_transfer.acquire_obs_transfer_slot'
    if dict(conf.get("params") or {}).get("maintenance_action"):
        return "input_transfer.acquire_obs_transfer_slot"
    payload = _backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/execution-commit",
        method="POST",
        payload={"attempt": conf["attempt"]},
    )
    if not payload.get("committed"):
        raise RuntimeError("WGS execution target was not committed")
    target = str(payload.get("desired_target") or "")
    branch = {
        "cce": "input_transfer.acquire_obs_transfer_slot",
        "node-97": "local_execution.start_local_wgs",
        "node-96": "local_execution.start_local_wgs",
        "sge-default": "sge_execution.submit_sge_wgs",
    }.get(target)
    if branch is None:
        raise RuntimeError(f"unsupported committed WGS execution target: {target}")
    return branch


def unavailable_execution_runner(target: str, **context: Any) -> None:
    """Fail closed until the separately accepted Local/SGE runner is installed."""
    conf = dict(context["dag_run"].conf or {})
    raise RuntimeError(
        f"{target} was committed for {conf.get('analysis_id')}, but its runner capability is disabled"
    )


def register_local_stage(**context: Any) -> dict[str, Any]:
    _require_runtime_enabled()
    if not _truthy("WGS_LOCAL_NODE97_ENABLED"):
        raise RuntimeError("node97 local WGS execution is disabled")
    conf = dict(context["dag_run"].conf or {})
    payload = {
        "attempt": conf["attempt"],
        "adapter": "wgs-runtime-node97",
        "command": (
            f"wgs-local-runtime {conf['analysis_id']} "
            f"{conf['attempt']} local_analysis"
        ),
    }
    task_instance = context.get("ti") or context.get("task_instance")
    if int(getattr(task_instance, "try_number", 1) or 1) > 1:
        payload["force_new_generation"] = True
    path = f"/api/internal/wgs/runs/{conf['analysis_id']}/stages/local_analysis"
    for registration_attempt in range(
        1, STAGE_PREDECESSOR_VISIBILITY_ATTEMPTS + 1
    ):
        try:
            return _backend_json(path, method="POST", payload=payload)
        except BackendStagePredecessorPending:
            if registration_attempt == STAGE_PREDECESSOR_VISIBILITY_ATTEMPTS:
                raise
            time.sleep(STAGE_PREDECESSOR_VISIBILITY_DELAY_SECONDS)
    raise RuntimeError("unreachable local WGS stage registration state")


def run_stage_on_node97(**context: Any) -> dict[str, Any]:
    registered = register_local_stage(**context)
    conf = dict(context["dag_run"].conf or {})
    command = [
        "ssh",
        "-T",
        "-F",
        os.getenv("WGS_SSH_CONFIG_PATH", "/opt/airflow/ssh/config"),
        os.getenv("WGS_RUNNER_NODE97_ALIAS", "wgs-node97"),
        os.getenv(
            "WGS_RUNNER_NODE97_COMMAND",
            "/home/ctapa/.config/airflow-wgs/forced-command-node97.sh",
        ),
        "wgs-local-runtime",
        str(conf["analysis_id"]),
        str(conf["attempt"]),
        "local_analysis",
    ]
    completed = subprocess.run(
        command,
        check=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        error = " | ".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part and part.strip()
        )[-2000:]
        raise RuntimeError(
            f"restricted node97 WGS stage failed ({completed.returncode}): {error}"
        )
    reply = _runner_reply(completed.stdout)
    if reply.get("status") not in {"accepted", "running", "success"}:
        raise RuntimeError("node97 WGS runner did not acknowledge the local workflow")
    _backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/observer/activate",
        method="POST",
        payload={"attempt": conf["attempt"]},
    )
    return {**registered, "runner_status": str(reply["status"])}


def local_stage_ready(**context: Any) -> bool:
    conf = dict(context["dag_run"].conf or {})
    query = urlencode({"attempt": conf["attempt"], "stage": "local_analysis"})
    payload = _sensor_backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/stage-status?{query}"
    )
    if payload is None:
        return False
    if payload.get("failed") or payload.get("ready"):
        _backend_json(
            f"/api/internal/wgs/runs/{conf['analysis_id']}/observer/deactivate",
            method="POST",
            payload={"attempt": conf["attempt"]},
        )
    if payload.get("failed"):
        raise RuntimeError(str(payload.get("message") or "node97 WGS workflow failed"))
    return bool(payload.get("ready"))


def finalize_local_run(**context: Any) -> dict[str, Any]:
    conf = dict(context["dag_run"].conf or {})
    return _backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/stages/finalize_local_run",
        method="POST",
        payload={
            "attempt": conf["attempt"],
            "adapter": "wgs-runtime-node97",
        },
    )


def release_leases(**context: Any) -> dict[str, Any]:
    conf = dict(context["dag_run"].conf or {})
    if not _runtime_enabled():
        return {"released": False, "reason": "runtime adapter disabled"}
    released = _backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/stages/release_leases",
        method="POST",
        payload={"attempt": conf["attempt"], "adapter": "wgs-runtime-200",
                 "dag_run_id": context["dag_run"].run_id, "resume_action_id": conf.get('resume_action_id')},
    )
    _raise_if_transfer_lease_retained(stage="release_leases", response=released)
    observer = _backend_json(
        f"/api/internal/wgs/runs/{conf['analysis_id']}/observer/deactivate",
        method="POST",
        payload={"attempt": conf["attempt"], "dag_run_id": context["dag_run"].run_id,
                 "resume_action_id": conf.get("resume_action_id")},
    )
    failed_tasks = _upstream_failure_task_ids(context)
    if failed_tasks:
        raise RuntimeError(
            "WGS upstream tasks failed after leases were released: "
            + ", ".join(failed_tasks)
        )
    return {**released, "observer_lifecycle_status": observer.get("lifecycle_status")}


def _raise_if_transfer_lease_retained(
    *, stage: str, response: dict[str, Any]
) -> None:
    if response.get("retained"):
        reason = str(response.get("reason") or "transfer terminal evidence unavailable")
        raise RuntimeError(f"{stage} retained OBS transfer lease: {reason}")


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


def report_dag_failure(context: dict[str, Any]) -> None:
    """Best-effort projection of a failed DagRun into the business run."""
    dag_run = context.get("dag_run")
    if dag_run is None:
        LOG.error("Cannot report WGS DAG failure without dag_run context")
        return
    conf = dict(dag_run.conf or {})
    analysis_id = str(conf.get("analysis_id") or "")
    attempt = int(conf.get("attempt") or 0)
    if not ANALYSIS_ID_RE.fullmatch(analysis_id) or attempt < 1:
        LOG.error("Cannot report WGS DAG failure with invalid run identity")
        return

    failed_task_ids = []
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
            f"/api/internal/wgs/runs/{analysis_id}/dag-terminal",
            method="POST",
            payload={
                "attempt": attempt,
                "status": "failed",
                "failed_task_ids": failed_task_ids,
                "dag_run_id": dag_run.run_id,
                "resume_action_id": conf.get('resume_action_id'),
            },
        )
    except Exception:
        LOG.exception(
            "Failed to project terminal WGS DagRun state for %s attempt %s",
            analysis_id,
            attempt,
        )


def acquire_transfer_slot(stage: str, **context: Any) -> bool:
    if not stage_should_run(stage, dict(context['dag_run'].conf or {})):
        return True
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
    except HTTPError as exc:
        response_payload: dict[str, Any] = {}
        try:
            decoded = json.loads(exc.read().decode("utf-8"))
            if isinstance(decoded, dict):
                response_payload = decoded
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
            response_payload = {}
        detail = response_payload.get("detail")
        if isinstance(detail, dict):
            code = str(detail.get("code") or "")
            message = str(detail.get("message") or exc)
            if exc.code == 409 and code == "WGS_STAGE_PREDECESSOR_PENDING":
                raise BackendStagePredecessorPending(message) from exc
        if 500 <= exc.code < 600 or (method == 'GET' and exc.code in {408, 429}):
            raise BackendTransportUnavailable(
                f"backend WGS stage API is temporarily unavailable: {exc}"
            ) from exc
        raise RuntimeError(f"backend WGS stage API is unavailable: {exc}") from exc
    except (URLError, TimeoutError) as exc:
        raise BackendTransportUnavailable(
            f"backend WGS stage API is temporarily unavailable: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"backend WGS stage API returned invalid JSON: {exc}") from exc


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
    task_id: str,
    *,
    stage: str,
    pool: str | None = None,
    trigger_rule: TriggerRule = TriggerRule.ALL_SUCCESS,
) -> PythonOperator:
    return PythonOperator(
        task_id=task_id,
        python_callable=register_stage,
        op_kwargs={"stage": stage},
        pool=pool,
        trigger_rule=trigger_rule,
        execution_timeout=timedelta(minutes=2),
    )


def transfer_slot_sensor(task_id: str, *, stage: str, pool: str) -> PythonSensor:
    return PythonSensor(
        task_id=task_id,
        python_callable=acquire_transfer_slot,
        op_kwargs={"stage": stage},
        mode="reschedule",
        poke_interval=5,
        timeout=48 * 3600,
        pool=pool,
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
    retry_options = dict(retries=6, retry_delay=timedelta(seconds=30), retry_exponential_backoff=True,
                         max_retry_delay=timedelta(minutes=5)) if stage in RECOVERY_STAGES else {}
    return PythonSensor(
        task_id=task_id,
        python_callable=stage_ready,
        **retry_options,
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
    on_failure_callback=report_dag_failure,
    tags=["airflow-demo", "wgs", "cce", "node200"],
) as dag:
    validate = PythonOperator(
        task_id="validate_request", python_callable=validate_request
    )
    choose_path = BranchPythonOperator(
        task_id="choose_run_path", python_callable=choose_run_path
    )
    cleanup_step7 = runner_stage(
        "step7_cleanup", stage="step7_cleanup", timeout_hours=24
    )
    wait_cleanup_step7 = stage_sensor(
        "wait_step7_cleanup", stage="step7_cleanup", timeout_hours=24
    )
    prepare_sampleinfo = runner_stage(
        "prepare_wgs_sampleinfo", stage="prepare_sampleinfo", timeout_hours=2
    )
    wait_prepare_sampleinfo = stage_sensor(
        "wait_prepare_wgs_sampleinfo", stage="prepare_sampleinfo", timeout_hours=2
    )
    wait_config_approval = PythonSensor(
        task_id="wait_wgs_config_approval",
        python_callable=submission_gate_ready,
        op_kwargs={"gate": "config"},
        mode="reschedule",
        poke_interval=5,
        timeout=7 * 24 * 3600,
    )
    prepare_analysis = runner_stage(
        "prepare_wgs_analysis", stage="prepare_analysis", timeout_hours=2
    )
    wait_prepare_analysis = stage_sensor(
        "wait_prepare_wgs_analysis", stage="prepare_analysis", timeout_hours=2
    )
    wait_execution_approval = PythonSensor(
        task_id="wait_wgs_execution_approval",
        python_callable=submission_gate_ready,
        op_kwargs={"gate": "execution"},
        mode="reschedule",
        poke_interval=5,
        timeout=7 * 24 * 3600,
    )
    wait_execution_commit = PythonSensor(
        task_id="wait_execution_commit",
        python_callable=execution_commit_ready,
        mode="reschedule",
        poke_interval=5,
        timeout=7 * 24 * 3600,
    )
    choose_execution = BranchPythonOperator(
        task_id="choose_execution_target", python_callable=choose_execution_target
    )

    with TaskGroup(group_id="input_transfer") as input_transfer:
        input_lease = transfer_slot_sensor(
            "acquire_obs_transfer_slot",
            stage="acquire_input_transfer_slot",
            pool="wgs_obs_upload",
        )
        input_upload = runner_stage(
            "start_step1_upload",
            stage="step1_upload",
            pool="wgs_obs_upload",
            timeout_hours=48,
        )
        input_wait = stage_sensor(
            "wait_step1_upload", stage="step1_upload", timeout_hours=48
        )
        input_release = control_stage(
            "release_obs_transfer_slot",
            stage="release_input_transfer_slot",
            trigger_rule=TriggerRule.ALL_DONE,
        )
        input_lease >> input_upload >> input_wait >> input_release

    with TaskGroup(group_id="local_execution") as local_execution:
        start_local = PythonOperator(
            task_id="start_local_wgs",
            python_callable=run_stage_on_node97,
            execution_timeout=timedelta(minutes=2),
        )
        wait_local = PythonSensor(
            task_id="wait_local_wgs",
            python_callable=local_stage_ready,
            mode="reschedule",
            poke_interval=10,
            timeout=120 * 3600,
        )
        local_finalize = PythonOperator(
            task_id="finalize_local_wgs",
            python_callable=finalize_local_run,
            execution_timeout=timedelta(minutes=2),
        )
        start_local >> wait_local >> local_finalize

    with TaskGroup(group_id="sge_execution") as sge_execution:
        submit_sge = PythonOperator(
            task_id="submit_sge_wgs",
            python_callable=unavailable_execution_runner,
            op_kwargs={"target": "sge"},
        )

    submit = runner_stage(
        "submit_step2_master", stage="step2_master", pool="wgs_cce_runs"
    )
    choose_step1_exit = BranchPythonOperator(
        task_id="choose_after_step1", python_callable=choose_after_step1
    )
    finalize_step1_canary = control_stage(
        "finalize_step1_canary", stage="finalize_step1_canary"
    )
    start_monitor = runner_stage(
        "start_step3_monitor", stage="step3_monitor"
    )
    wait_analysis = stage_sensor(
        "wait_step3_analysis",
        stage="step3_monitor",
        timeout_hours=120,
    )
    choose_step3_exit = BranchPythonOperator(
        task_id="choose_after_step3", python_callable=choose_after_step3
    )
    finalize_step3_dryrun = control_stage(
        "finalize_step3_dryrun", stage="finalize_step3_dryrun"
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
            pool="wgs_obs_download",
        )
        result_download = runner_stage(
            "start_step5_download",
            stage="step5_download",
            pool="wgs_obs_download",
            timeout_hours=48,
        )
        result_wait = stage_sensor(
            "wait_step5_download", stage="step5_download", timeout_hours=48
        )
        result_release = control_stage(
            "release_obs_transfer_slot",
            stage="release_result_transfer_slot",
            trigger_rule=TriggerRule.ALL_DONE,
        )
        result_lease >> result_download >> result_wait >> result_release

    materialize = runner_stage(
        "materialize_step6_results", stage="step6_materialize", timeout_hours=24
    )
    wait_materialize = stage_sensor(
        "wait_step6_materialize", stage="step6_materialize", timeout_hours=24
    )
    finalize = control_stage("finalize_run", stage="finalize_run")
    release = PythonOperator(
        task_id="release_leases",
        python_callable=release_leases,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    validate >> choose_path >> [prepare_sampleinfo, cleanup_step7]
    cleanup_step7 >> wait_cleanup_step7
    prepare_sampleinfo >> wait_prepare_sampleinfo >> wait_config_approval
    wait_config_approval >> prepare_analysis >> wait_prepare_analysis >> wait_execution_approval
    wait_execution_approval >> wait_execution_commit >> choose_execution
    choose_execution >> [input_lease, start_local, submit_sge]
    input_transfer >> choose_step1_exit
    input_wait >> choose_step1_exit
    choose_step1_exit >> [submit, finalize_step1_canary]
    submit >> start_monitor >> wait_analysis >> choose_step3_exit
    choose_step3_exit >> [start_publish, finalize_step3_dryrun]
    start_publish >> wait_publish
    wait_publish >> result_transfer >> materialize >> wait_materialize >> finalize >> release
    result_wait >> materialize
    finalize_step1_canary >> release
    finalize_step3_dryrun >> release
    local_finalize >> release
    submit_sge >> release
