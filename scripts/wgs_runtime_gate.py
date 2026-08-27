#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from typing import Any

import yaml


ANALYSIS_RE = re.compile(r"^WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
STAGES = {
    "prepare",
    "step1_upload",
    "step2_master",
    "step3_monitor",
    "step4_publish",
    "step5_download",
    "step6_materialize",
}
ASYNC_STAGES = {
    "step1_upload",
    "step3_monitor",
    "step4_publish",
    "step5_download",
}
STEP_SCRIPTS = {
    "step1_upload": "Step1_upload_fastq.sh",
    "step2_master": "Step2_run.sh",
    "step3_monitor": "Step3_status.sh",
    "step4_publish": "Step4_publish_results.sh",
    "step5_download": "Step5_download_verify.sh",
    "step6_materialize": "Step6_materialize_results.sh",
}
STAGE_STATUS_SCHEMA = "wgs-runtime.stage-status.v1"
BINDING_SCHEMA = "wgs-runtime.batch-binding.v2"
REQUEST_ROOT = Path(
    os.getenv(
        "WGS_RUNTIME_REQUEST_ROOT",
        "/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime/runner-requests",
    )
)
WGS_REPO_ROOT = Path(
    os.getenv(
        "WGS_REPO_ROOT",
        "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1",
    )
)
WGS_PYTHON = os.getenv("WGS_PYTHON", "/bi/software/mamba/envs/WGS/bin/python")
WGS_PREPARE_CONFIG = os.getenv(
    "WGS_PREPARE_CONFIG", "/home/chenjc/.config/wgs/prepare.yaml"
)
CCE_OPERATOR_CONFIG = os.getenv(
    "CCE_OPERATOR_CONFIG", "/home/chenjc/.config/wgs/cce.yaml"
)
MONITOR_INTERVAL_SECONDS = int(os.getenv("WGS_MONITOR_INTERVAL_SECONDS", "5"))
MONITOR_TIMEOUT_SECONDS = int(os.getenv("WGS_MONITOR_TIMEOUT_SECONDS", "432000"))
CCE_EVIDENCE_ROOT = Path(
    os.getenv(
        "WGS_CCE_EVIDENCE_ROOT",
        "/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence",
    )
)
EVIDENCE_BRIDGE = Path(__file__).with_name("wgs_evidence_bridge.py")


def parse_command(value: str) -> tuple[str, int, str]:
    parts = shlex.split(value)
    if len(parts) != 4 or parts[0] != "wgs-runtime":
        raise ValueError("Only wgs-runtime <analysis_id> <attempt> <stage> is accepted")
    analysis_id, attempt_text, stage = parts[1:]
    if ANALYSIS_RE.fullmatch(analysis_id) is None or stage not in STAGES:
        raise ValueError("invalid WGS runtime command")
    try:
        attempt = int(attempt_text)
    except ValueError as error:
        raise ValueError("attempt must be a positive integer") from error
    if attempt < 1:
        raise ValueError("attempt must be a positive integer")
    return analysis_id, attempt, stage


def _request_path(analysis_id: str, attempt: int, stage: str) -> Path:
    root = REQUEST_ROOT.resolve()
    path = (root / analysis_id / f"attempt-{attempt}" / f"{stage}.json").resolve()
    if root not in path.parents:
        raise ValueError("runtime request path escapes request root")
    return path


def load_request(analysis_id: str, attempt: int, stage: str) -> dict[str, Any]:
    path = _request_path(analysis_id, attempt, stage)
    if not path.is_file() or path.is_symlink():
        raise ValueError("registered runtime request is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        payload.get("schema_version") != "wgs-runtime.request.v3"
        or payload.get("analysis_id") != analysis_id
        or int(payload.get("attempt", 0)) != attempt
        or payload.get("stage") != stage
    ):
        raise ValueError("runtime request identity mismatch")
    return payload


def _sidecar_path(payload: dict[str, Any], suffix: str) -> Path:
    return _request_path(
        str(payload["analysis_id"]), int(payload["attempt"]), str(payload["stage"])
    ).with_suffix(suffix)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _write_status(
    payload: dict[str, Any], status: str, message: str = "", **details: Any
) -> None:
    value = {
        "schema_version": STAGE_STATUS_SCHEMA,
        "analysis_id": payload["analysis_id"],
        "attempt": payload["attempt"],
        "stage": payload["stage"],
        "status": status,
        "message": message[-2000:],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **details,
    }
    _atomic_json(_sidecar_path(payload, ".status.json"), value)


def _truthy(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def validate_release_repository(payload: dict[str, Any]) -> Path:
    repo = WGS_REPO_ROOT.resolve()
    prepare = repo / "prepare" / "prepare_wgs_batch.py"
    if not repo.is_dir() or repo.is_symlink() or not prepare.is_file() or prepare.is_symlink():
        raise RuntimeError("release_unavailable: fixed WGS repository is unavailable")
    revision = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != str(payload.get("wgs_source_commit") or ""):
        raise RuntimeError(
            "release_unavailable: fixed WGS repository commit does not match the run"
        )
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    unsafe = [line for line in status if not line.startswith("?? docs/")]
    if unsafe:
        raise RuntimeError(
            "release_unavailable: fixed WGS repository contains runtime changes"
        )
    return repo


def _workdir(payload: dict[str, Any]) -> Path:
    value = Path(str(payload["node200_workdir"])).resolve()
    runtime_root = Path(
        "/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime/runs"
    ).resolve()
    if runtime_root not in value.parents:
        raise ValueError("node200 workdir is outside the approved runtime root")
    return value


def _binding_path(payload: dict[str, Any]) -> Path:
    return _workdir(payload) / "batch-binding.json"


def build_prepare_command(payload: dict[str, Any]) -> list[str]:
    workdir = Path(str(payload["node200_workdir"]))
    project_name = str(payload["project_name"])
    batch_no = str(payload["batch_no"])
    fq_path = str(payload["fq_path"])
    for value in (project_name, batch_no):
        if SAFE_COMPONENT_RE.fullmatch(value) is None:
            raise ValueError("project_name and batch_no must be safe path components")
    command = [
        WGS_PYTHON,
        str(WGS_REPO_ROOT / "prepare" / "prepare_wgs_batch.py"),
        "all",
        "--outpath",
        str(workdir / project_name),
        "--analysis-batch",
        batch_no,
        "--run-mode",
        "cce",
        "--run-id",
        f"{payload['analysis_id']}-a{int(payload['attempt'])}",
        "--fastq-root",
        fq_path,
        "--prepare-config",
        WGS_PREPARE_CONFIG,
        "--cce-config",
        CCE_OPERATOR_CONFIG,
    ]
    platform = str(payload.get("platform") or "").strip()
    if platform:
        command.extend(["--platform", platform])
    return command


def _clean_env() -> dict[str, str]:
    return {**os.environ, "PYTHONNOUSERSITE": "1"}


def _run_prepare(payload: dict[str, Any]) -> None:
    binding_path = _binding_path(payload)
    if binding_path.is_file():
        _load_binding(payload)
        return
    validate_release_repository(payload)
    workdir = _workdir(payload)
    workdir.mkdir(parents=True, exist_ok=True)
    project_root = workdir / str(payload["project_name"])
    project_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(build_prepare_command(payload), check=True, env=_clean_env())
    candidates = sorted(
        path.parent.parent
        for path in project_root.glob("*/cce/BATCH_RUNTIME.yaml")
        if path.is_file()
    )
    if len(candidates) != 1:
        raise RuntimeError("WGS prepare did not create exactly one frozen CCE batch")
    batch_root = candidates[0].resolve()
    runtime = yaml.safe_load(
        (batch_root / "cce" / "BATCH_RUNTIME.yaml").read_text(encoding="utf-8")
    )
    profile = yaml.safe_load(
        (batch_root / "cce" / "RESOLVED_PROFILE.yaml").read_text(encoding="utf-8")
    )
    identity = runtime.get("identity") if isinstance(runtime, dict) else None
    expected_run_id = f"{payload['analysis_id']}-a{int(payload['attempt'])}"
    if not isinstance(identity, dict) or identity.get("run_id") != expected_run_id:
        raise RuntimeError("BATCH_RUNTIME.yaml identifies a different run")
    if not isinstance(profile, dict):
        raise RuntimeError("RESOLVED_PROFILE.yaml is invalid")
    platform = profile.get("platform") if isinstance(profile.get("platform"), dict) else {}
    pipeline = profile.get("pipeline") if isinstance(profile.get("pipeline"), dict) else {}
    resolved_runtime = {
        "cce_pipeline_version": str(
            platform.get("wheel_version") or platform.get("version") or ""
        ),
        "cce_pipeline_source_commit": str(platform.get("source_commit") or ""),
        "profile_id": str(profile.get("profile_id") or ""),
        "profile_revision": str(
            profile.get("profile_revision") or profile.get("revision") or ""
        ),
        "profile_sha256": str(profile.get("sha256") or ""),
        "master_image_digest": str(pipeline.get("master_image") or ""),
        "pipeline_build_sha256": str(pipeline.get("build_sha256") or ""),
        "resource_manifest_sha256": str(
            pipeline.get("resource_manifest_sha256") or ""
        ),
    }
    _atomic_json(
        binding_path,
        {
            "schema_version": BINDING_SCHEMA,
            "analysis_id": payload["analysis_id"],
            "attempt": payload["attempt"],
            "pipeline_release_id": payload["pipeline_release_id"],
            "wgs_version": payload["wgs_version"],
            "wgs_source_commit": payload["wgs_source_commit"],
            "resolved_runtime": resolved_runtime,
            "batch_root": str(batch_root),
            "cce_bundle": str(batch_root / "cce"),
            "project": identity.get("project"),
            "batch": identity.get("batch"),
            "run_id": identity.get("run_id"),
            "master_job": (runtime.get("kubernetes") or {}).get("master_job"),
            "namespace": (runtime.get("kubernetes") or {}).get("namespace"),
            "rule_source_dir": str(
                Path(str((runtime.get("paths") or {}).get("run_dir")))
                / "evidence"
                / str(identity.get("run_id"))
                / "rule-status"
                / "raw"
            ),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def _load_binding(payload: dict[str, Any]) -> dict[str, Any]:
    path = _binding_path(payload)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value.get("schema_version") != BINDING_SCHEMA
        or value.get("analysis_id") != payload["analysis_id"]
        or int(value.get("attempt", 0)) != int(payload["attempt"])
        or value.get("pipeline_release_id") != payload["pipeline_release_id"]
    ):
        raise ValueError("batch binding identity mismatch")
    bundle = Path(str(value["cce_bundle"])).resolve()
    workdir = _workdir(payload)
    if workdir not in bundle.parents or not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("frozen CCE bundle is outside the attempt workdir")
    return value


def _step_command(payload: dict[str, Any], stage: str, *arguments: str) -> list[str]:
    binding = _load_binding(payload)
    script = Path(str(binding["cce_bundle"])) / STEP_SCRIPTS[stage]
    if not script.is_file() or script.is_symlink():
        raise FileNotFoundError(f"frozen WGS step is missing: {script.name}")
    return ["bash", str(script), *arguments]


def validate_step3_status(value: dict[str, Any]) -> dict[str, Any]:
    state = value.get("master_state")
    if state not in {"PENDING", "RUNNING", "SUCCEEDED", "FAILED"}:
        raise ValueError("Step3 master_state is invalid")
    if not isinstance(value.get("normal"), bool):
        raise ValueError("Step3 normal must be boolean")
    result = {
        "master_state": state,
        "normal": value["normal"],
        "current_rule": value.get("current_rule"),
        "current_rules": list(value.get("current_rules") or []),
        "last_completed_rule": value.get("last_completed_rule"),
        "completed": int(value.get("completed") or 0),
        "total": int(value.get("total") or 0),
        "percent": float(value.get("percent") or 0.0),
        "message": str(value.get("message") or ""),
    }
    if result["completed"] < 0 or result["total"] < 0:
        raise ValueError("Step3 progress cannot be negative")
    return result


def build_evidence_bridge_command(
    payload: dict[str, Any], binding: dict[str, Any], *, terminal: bool
) -> list[str]:
    output = (
        CCE_EVIDENCE_ROOT
        / str(payload["analysis_id"])
        / f"attempt-{int(payload['attempt'])}"
    )
    command = [
        WGS_PYTHON,
        str(EVIDENCE_BRIDGE),
        "--operator-config",
        CCE_OPERATOR_CONFIG,
        "--output",
        str(output),
        "--namespace",
        str(binding["namespace"]),
        "--master-job",
        str(binding["master_job"]),
        "--master-manifest",
        str(Path(str(binding["cce_bundle"])) / "master-job.yaml"),
        "--rule-source-dir",
        str(binding["rule_source_dir"]),
    ]
    if terminal:
        command.append("--terminal")
    return command


def _sync_rule_evidence(
    payload: dict[str, Any], binding: dict[str, Any], *, terminal: bool
) -> str | None:
    completed = subprocess.run(
        build_evidence_bridge_command(payload, binding, terminal=terminal),
        check=False,
        capture_output=True,
        text=True,
        env=_clean_env(),
    )
    if completed.returncode == 0:
        return None
    return (completed.stderr or completed.stdout or "Rule evidence bridge failed")[-2000:]


def _monitor_step3(payload: dict[str, Any]) -> None:
    started = time.monotonic()
    binding = _load_binding(payload)
    while True:
        monitoring_error = _sync_rule_evidence(payload, binding, terminal=False)
        completed = subprocess.run(
            _step_command(payload, "step3_monitor", "--output", "json"),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout)[-2000:])
        value = validate_step3_status(json.loads(completed.stdout))
        terminal = value["master_state"] in {"SUCCEEDED", "FAILED"}
        if terminal:
            monitoring_error = _sync_rule_evidence(payload, binding, terminal=True)
        _write_status(
            payload,
            "running" if value["master_state"] not in {"SUCCEEDED", "FAILED"} else value["master_state"].lower(),
            value["message"],
            master=value,
            master_job=binding.get("master_job"),
            monitoring_health="degraded" if monitoring_error else "healthy",
            monitoring_error=monitoring_error,
        )
        if value["master_state"] == "SUCCEEDED":
            return
        if value["master_state"] == "FAILED":
            raise RuntimeError(value["message"] or "Master Job failed")
        if time.monotonic() - started > MONITOR_TIMEOUT_SECONDS:
            raise TimeoutError("Step3 monitoring timed out")
        time.sleep(MONITOR_INTERVAL_SECONDS)


def _wait_step4(payload: dict[str, Any]) -> None:
    started = time.monotonic()
    retry_text = "SFS backend export is not ready in OBS; retry Step4"
    while True:
        completed = subprocess.run(
            _step_command(payload, "step4_publish"),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            return
        message = (completed.stderr or completed.stdout)[-2000:]
        if retry_text not in message:
            raise RuntimeError(message)
        _write_status(payload, "running", message)
        if time.monotonic() - started > MONITOR_TIMEOUT_SECONDS:
            raise TimeoutError("Step4 publish monitoring timed out")
        time.sleep(MONITOR_INTERVAL_SECONDS)


def run_stage(payload: dict[str, Any]) -> None:
    if not _truthy("WGS_EXECUTION_ENABLED") or not _truthy(
        "WGS_RUNTIME_ADAPTER_ENABLED"
    ):
        raise RuntimeError("WGS execution gate is disabled")
    stage = str(payload["stage"])
    if stage == "prepare":
        _run_prepare(payload)
    elif stage == "step3_monitor":
        _monitor_step3(payload)
    elif stage == "step4_publish":
        _wait_step4(payload)
    else:
        subprocess.run(_step_command(payload, stage), check=True)


def _boot_id() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()


def _process_start_time(pid: int) -> str:
    return Path(f"/proc/{pid}/stat").read_text(encoding="ascii").split()[21]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _process_matches(state: dict[str, Any]) -> bool:
    try:
        pid = int(state["pid"])
        return state.get("boot_id") == _boot_id() and state.get(
            "process_start_time"
        ) == _process_start_time(pid)
    except (KeyError, TypeError, ValueError, OSError, IndexError):
        return False


def build_async_worker_command(
    *, analysis_id: str, attempt: int, stage: str, lock_path: Path
) -> list[str]:
    return [
        "nohup",
        "setsid",
        "flock",
        "-n",
        str(lock_path),
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "wgs-runtime",
        analysis_id,
        str(attempt),
        stage,
    ]


def start_async_stage(payload: dict[str, Any]) -> dict[str, Any]:
    if not _truthy("WGS_EXECUTION_ENABLED") or not _truthy(
        "WGS_RUNTIME_ADAPTER_ENABLED"
    ):
        raise RuntimeError("WGS execution gate is disabled")
    request_path = _request_path(
        str(payload["analysis_id"]), int(payload["attempt"]), str(payload["stage"])
    )
    request_sha = hashlib.sha256(request_path.read_bytes()).hexdigest()
    state_path = _sidecar_path(payload, ".worker.json")
    launch_lock = _sidecar_path(payload, ".launch.lock")
    worker_lock = _sidecar_path(payload, ".worker.lock")
    log_path = _sidecar_path(payload, ".worker.log")
    launch_lock.parent.mkdir(parents=True, exist_ok=True)
    with launch_lock.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        previous = _read_json(state_path)
        if previous and previous.get("request_sha256") != request_sha:
            raise RuntimeError("registered request changed after worker launch")
        status = _read_json(_sidecar_path(payload, ".status.json"))
        if status.get("status") in {"success", "complete", "succeeded"}:
            return {"status": "complete", "pid": previous.get("pid")}
        if previous and _process_matches(previous):
            return {"status": "running", "pid": previous["pid"]}
        command = build_async_worker_command(
            analysis_id=str(payload["analysis_id"]),
            attempt=int(payload["attempt"]),
            stage=str(payload["stage"]),
            lock_path=worker_lock,
        )
        with log_path.open("ab", buffering=0) as log_handle:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                close_fds=True,
            )
        state = {
            "analysis_id": payload["analysis_id"],
            "attempt": payload["attempt"],
            "stage": payload["stage"],
            "pid": process.pid,
            "boot_id": _boot_id(),
            "process_start_time": _process_start_time(process.pid),
            "request_sha256": request_sha,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        _atomic_json(state_path, state)
        _write_status(payload, "accepted")
        return {"status": "accepted", "pid": process.pid}


def _run_worker(payload: dict[str, Any]) -> int:
    _write_status(payload, "running")
    try:
        run_stage(payload)
    except Exception as error:
        _write_status(payload, "failed", str(error))
        raise
    _write_status(payload, "success")
    return 0


def main() -> int:
    worker_mode = len(sys.argv) > 1 and sys.argv[1] == "--worker"
    command = (
        " ".join(sys.argv[2:])
        if worker_mode
        else os.getenv("SSH_ORIGINAL_COMMAND", "") or " ".join(sys.argv[1:])
    )
    analysis_id, attempt, stage = parse_command(command)
    payload = load_request(analysis_id, attempt, stage)
    if worker_mode:
        return _run_worker(payload)
    if stage in ASYNC_STAGES:
        print(json.dumps(start_async_stage(payload), sort_keys=True))
        return 0
    return _run_worker(payload)


if __name__ == "__main__":
    raise SystemExit(main())
