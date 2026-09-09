#!/usr/bin/env python3
"""Restricted node200 runtime for one immutable GATK Step1-Step6 bundle."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable

import yaml


ANALYSIS_ID = re.compile(r"^GATK_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")
STAGE_SCRIPTS = {
    "step1_upload": "Step1_upload_fastq.sh",
    "step2_master": "Step2_run.sh",
    "step3_monitor": "Step3_status.sh",
    "step4_publish": "Step4_publish_results.sh",
    "step5_download": "Step5_download_verify.sh",
    "step6_materialize": "Step6_materialize_results.sh",
}
TERMINAL = {"success", "failed", "canceled"}
EVIDENCE_BRIDGE = Path(__file__).with_name("wgs_evidence_bridge.py")
GATK_EVIDENCE_ROOT = Path(
    os.environ.get(
        "GATK_CCE_EVIDENCE_ROOT",
        "/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud/runtime/gatk-evidence",
    )
)
CCE_OPERATOR_CONFIG = os.environ.get(
    "GATK_CCE_OPERATOR_CONFIG",
    "/home/ctapa/.config/cce-pipeline/operator.yaml",
)
STEP4_EXPORT_PENDING = "SFS backend export is not ready in OBS; retry Step4"


def _root() -> Path:
    root = Path(os.environ["GATK_RUNTIME_REQUEST_ROOT"]).resolve()
    if not root.is_absolute():
        raise RuntimeError("GATK_RUNTIME_REQUEST_ROOT must be absolute")
    return root


def _request_path(analysis_id: str, attempt: int, stage: str) -> Path:
    if ANALYSIS_ID.fullmatch(analysis_id) is None or attempt < 1:
        raise ValueError("invalid GATK runtime identity")
    if stage not in {"prepare", *STAGE_SCRIPTS}:
        raise ValueError("unsupported GATK runtime stage")
    path = (_root() / analysis_id / f"attempt-{attempt}" / f"{stage}.request.json").resolve()
    if _root() not in path.parents:
        raise ValueError("GATK request path escapes runtime root")
    return path


def _load(
    analysis_id: str,
    attempt: int,
    stage: str,
    generation: int | None = None,
) -> tuple[Path, dict[str, Any]]:
    path = _request_path(analysis_id, attempt, stage)
    if not path.is_file():
        raise RuntimeError("GATK runtime request does not exist")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("GATK runtime request is not valid JSON") from exc
    if payload.get("analysis_id") != analysis_id or payload.get("attempt") != attempt:
        raise ValueError("GATK request identity mismatch")
    request_generation = int(payload.get("generation") or 1)
    generation = request_generation if generation is None else generation
    if generation < 1:
        raise ValueError("GATK runtime generation must be positive")
    if stage != "prepare" and payload.get("stage") != stage:
        raise ValueError("GATK request stage mismatch")
    if stage != "prepare":
        if int(payload.get("orchestration_contract_version") or 0) != 2:
            raise ValueError("GATK runtime stage requires orchestration contract v2")
        expected_execution_id = (
            f"{analysis_id}-a{attempt}-{stage}-g{int(payload.get('generation') or 0)}"
        )
        if payload.get("execution_id") != expected_execution_id:
            raise ValueError("GATK runtime execution identity mismatch")
        if request_generation != generation:
            raise ValueError("GATK runtime generation does not match its request")
    else:
        payload = dict(payload)
        payload["generation"] = generation
        payload["execution_id"] = f"{analysis_id}-a{attempt}-prepare-g{generation}"
    return path, payload


def _status_path(request_path: Path) -> Path:
    return request_path.with_suffix(".status.json")


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _write_status(
    request_path: Path,
    payload: dict[str, Any],
    status: str,
    message: str,
    **progress: Any,
) -> dict[str, Any]:
    value = {
        "schema_version": "gatk-runtime.status.v1",
        "analysis_id": payload["analysis_id"],
        "attempt": payload["attempt"],
        "stage": payload.get("stage") or "prepare",
        "generation": int(payload.get("generation") or 1),
        "request_hash": payload["request_hash"],
        "orchestration_contract_version": int(
            payload.get("orchestration_contract_version") or 1
        ),
        "execution_id": payload.get("execution_id"),
        "status": status,
        "message": message[-2000:],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **progress,
    }
    if status in TERMINAL:
        value["receipt_hash"] = hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    _atomic_json(_status_path(request_path), value)
    return value


def _bundle(payload: dict[str, Any]) -> Path:
    if payload.get("kind") == "gatk-airflow-prepare":
        root = Path(str(payload["output_root"])).resolve()
    else:
        root = Path(str(payload["runtime_workdir"])).resolve()
    bundle = root / "cce"
    if not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("frozen GATK CCE bundle is unavailable")
    return bundle


def _binding_path(payload: dict[str, Any]) -> Path:
    root = (
        Path(str(payload["output_root"])).resolve()
        if payload.get("kind") == "gatk-airflow-prepare"
        else Path(str(payload["runtime_workdir"])).resolve()
    )
    return root / "batch-binding.json"


def _write_binding(payload: dict[str, Any]) -> dict[str, Any]:
    bundle = _bundle(payload)
    runtime = yaml.safe_load((bundle / "BATCH_RUNTIME.yaml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((bundle / "master-job.yaml").read_text(encoding="utf-8"))
    if not isinstance(runtime, dict) or runtime.get("schema_version") != 3:
        raise RuntimeError("GATK BATCH_RUNTIME.yaml is invalid")
    identity = runtime.get("identity") or {}
    kubernetes = runtime.get("kubernetes") or {}
    paths = runtime.get("paths") or {}
    expected_run_id = f"{payload['analysis_id']}-a{int(payload['attempt'])}"
    if identity.get("run_id") != expected_run_id:
        raise RuntimeError("GATK runtime identifies another analysis attempt")
    labels = (manifest.get("metadata") or {}).get("labels") if isinstance(manifest, dict) else {}
    run_label = str((labels or {}).get("cce.biosan.cn/run-id") or "")
    if re.fullmatch(r"cce-run-[0-9a-f]{16}", run_label) is None:
        raise RuntimeError("GATK Master manifest has no valid opaque run label")
    run_dir = Path(str(paths.get("run_dir") or ""))
    if not run_dir.is_absolute():
        raise RuntimeError("GATK runtime evidence directory is invalid")
    run_id = str(identity["run_id"])
    evidence_output = (
        GATK_EVIDENCE_ROOT
        / str(payload["analysis_id"])
        / f"attempt-{int(payload['attempt'])}"
    )
    value = {
        "schema_version": "gatk-runtime.batch-binding.v1",
        "analysis_id": payload["analysis_id"],
        "attempt": int(payload["attempt"]),
        "pipeline_release_id": (
            f"{payload.get('profile_id') or 'gatk-scmc-v7.6.0'}@"
            f"{payload.get('profile_revision') or 'unknown'}"
        ),
        "run_id": run_id,
        "run_label": run_label,
        "namespace": str(kubernetes.get("namespace") or ""),
        "master_job": str(kubernetes.get("master_job") or ""),
        "cce_bundle": str(bundle),
        "rule_source_dir": str(run_dir / "evidence" / run_id / "rule-status" / "raw"),
        "analysis_log_source": str(run_dir / "evidence" / run_id / "analysis.log"),
        "evidence_output": str(evidence_output),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if not value["namespace"] or not value["master_job"]:
        raise RuntimeError("GATK runtime has no Kubernetes identity")
    _atomic_json(_binding_path(payload), value)
    return value


def _load_binding(payload: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(_binding_path(payload).read_text(encoding="utf-8"))
    if (
        value.get("schema_version") != "gatk-runtime.batch-binding.v1"
        or value.get("analysis_id") != payload["analysis_id"]
        or int(value.get("attempt") or 0) != int(payload["attempt"])
    ):
        raise ValueError("GATK batch binding identity mismatch")
    return value


def _bridge_command(
    payload: dict[str, Any], binding: dict[str, Any], *, terminal: bool
) -> list[str]:
    command = [
        os.environ.get("GATK_PYTHON", sys.executable),
        str(EVIDENCE_BRIDGE),
        "--operator-config",
        CCE_OPERATOR_CONFIG,
        "--output",
        str(binding["evidence_output"]),
        "--namespace",
        str(binding["namespace"]),
        "--master-job",
        str(binding["master_job"]),
        "--master-manifest",
        str(Path(str(binding["cce_bundle"])) / "master-job.yaml"),
        "--rule-source-dir",
        str(binding["rule_source_dir"]),
        "--analysis-log-source",
        str(binding["analysis_log_source"]),
        "--run-label-key",
        "cce.biosan.cn/run-id",
    ]
    if terminal:
        command.append("--terminal")
    return command


def _sync_evidence(
    payload: dict[str, Any], binding: dict[str, Any], *, terminal: bool
) -> str | None:
    completed = subprocess.run(
        _bridge_command(payload, binding, terminal=terminal),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        return (completed.stderr or completed.stdout or "GATK evidence bridge failed")[-2000:]
    if terminal:
        rule_root = Path(str(binding["evidence_output"])) / "rule-status" / "raw"
        if not any(path.is_file() and path.stat().st_size for path in rule_root.glob("*.jsonl")):
            return "GATK rule logger produced no terminal JSONL evidence"
    return None


def _prepare(payload: dict[str, Any]) -> list[str]:
    repository = Path(os.environ["GATK_REPOSITORY_ROOT"]).resolve()
    script = repository / "scripts" / "airflow_handoff.py"
    if not script.is_file() or script.is_symlink():
        raise RuntimeError("approved GATK handoff entrypoint is unavailable")
    python = os.environ.get("GATK_PYTHON", sys.executable)
    return [python, str(script), "--handoff-request", str(_request_path(payload["analysis_id"], int(payload["attempt"]), "prepare"))]


def _step(payload: dict[str, Any], stage: str) -> list[str]:
    script = _bundle(payload) / STAGE_SCRIPTS[stage]
    if not script.is_file() or script.is_symlink():
        raise RuntimeError(f"frozen GATK stage script is unavailable: {script.name}")
    return ["bash", str(script)]


def _run_frozen_stage(
    command: list[str],
    *,
    stage: str,
    environment: dict[str, str],
    on_wait: Callable[[str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    wait_seconds = max(0, int(os.environ.get("GATK_PUBLISH_WAIT_SECONDS", "7200")))
    poll_seconds = max(1, int(os.environ.get("GATK_PUBLISH_POLL_SECONDS", "30")))
    deadline = time.monotonic() + wait_seconds
    attempts = 0
    while True:
        attempts += 1
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            env=environment,
        )
        if completed.returncode == 0:
            return completed
        detail = "\n".join(
            value.strip()
            for value in (completed.stdout, completed.stderr)
            if value and value.strip()
        )[-2000:]
        retryable = stage == "step4_publish" and STEP4_EXPORT_PENDING in detail
        if not retryable:
            raise RuntimeError(
                detail or f"{stage} command failed with exit code {completed.returncode}"
            )
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"GATK Step4 timed out after {wait_seconds}s waiting for the SFS "
                f"backend export to become visible in OBS: {detail}"
            )
        message = (
            "Waiting for the SFS backend export to become visible in OBS "
            f"(check {attempts})"
        )
        if on_wait is not None:
            on_wait(message)
        time.sleep(poll_seconds)


def _materialize_result_root(payload: dict[str, Any]) -> Path:
    prepare_path = _request_path(
        str(payload["analysis_id"]), int(payload["attempt"]), "prepare"
    )
    prepare = json.loads(prepare_path.read_text(encoding="utf-8"))
    configured_root = Path(os.environ["GATK_RESULT_ROOT"]).resolve()
    requested_root = Path(str(prepare.get("result_root") or "")).resolve()
    expected_root = (
        configured_root
        / str(prepare.get("batch") or "")
        / str(payload["analysis_id"])
    ).resolve()
    if requested_root != expected_root or configured_root not in requested_root.parents:
        raise ValueError("GATK result_root is outside the approved delivery location")
    return requested_root


def _materialize(payload: dict[str, Any]) -> Path:
    bundle = _bundle(payload)
    runtime = yaml.safe_load((bundle / "BATCH_RUNTIME.yaml").read_text(encoding="utf-8"))
    if not isinstance(runtime, dict) or runtime.get("schema_version") != 3:
        raise RuntimeError("GATK BATCH_RUNTIME.yaml is invalid")
    identity = runtime.get("identity") or {}
    tools = runtime.get("tools") or {}
    expected_run_id = f"{payload['analysis_id']}-a{int(payload['attempt'])}"
    if identity.get("run_id") != expected_run_id:
        raise RuntimeError("GATK materialization identifies another analysis attempt")

    delivery_path = bundle / "cce_delivery.py"
    if not delivery_path.is_file() or delivery_path.is_symlink():
        raise RuntimeError("frozen GATK delivery helper is unavailable")
    spec = importlib.util.spec_from_file_location(
        f"gatk_cce_delivery_{payload['analysis_id']}", delivery_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("frozen GATK delivery helper cannot be loaded")
    delivery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(delivery)

    result_root = _materialize_result_root(payload)
    delivery.materialize_results(
        bundle / "cloud_delivery",
        result_root,
        str(identity.get("batch") or ""),
        run_id=expected_run_id,
        zstd_bin=str(tools.get("zstd_bin") or ""),
        project_name=str(identity.get("project") or ""),
    )
    return result_root


def _parse_step3(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("master_state") in {"PENDING", "RUNNING", "SUCCEEDED", "FAILED"}:
            return value
    raise RuntimeError("Step3 did not return a valid Master status")


def _failure_message(error: Exception) -> str:
    if isinstance(error, subprocess.CalledProcessError):
        detail = error.stderr or error.stdout
        if detail:
            return str(detail).strip()[-2000:]
    return str(error)


def _execute(
    analysis_id: str,
    attempt: int,
    stage: str,
    generation: int | None = None,
) -> None:
    request_path, payload = _load(analysis_id, attempt, stage, generation)
    _write_status(request_path, payload, "running", f"{stage} started")
    environment = {
        **os.environ,
        "WGS_TRANSFER_ANALYSIS_ID": analysis_id,
        "WGS_TRANSFER_ATTEMPT": str(attempt),
        "WGS_TRANSFER_STAGE": stage,
        "WGS_ORCHESTRATION_CONTRACT_VERSION": str(
            payload.get("orchestration_contract_version") or 1
        ),
        "WGS_STAGE_EXECUTION_ID": str(payload.get("execution_id") or ""),
        "WGS_STAGE_GENERATION": str(payload.get("generation") or 1),
        "WGS_STAGE_REQUEST_HASH": str(payload.get("request_hash") or ""),
        "WGS_TRANSFER_SPOOL_ROOT": os.environ.get(
            "GATK_TRANSFER_SPOOL_ROOT",
            str(_root().parent / "transfer-progress"),
        ),
    }
    try:
        if stage == "prepare":
            completed = subprocess.run(
                _prepare(payload), check=True, text=True, capture_output=True, env=environment
            )
            _write_binding(payload)
            _write_status(request_path, payload, "success", completed.stdout[-2000:] or "GATK contract prepared")
            return
        if stage == "step3_monitor":
            binding = _load_binding(payload)
            while True:
                monitoring_error = _sync_evidence(payload, binding, terminal=False)
                completed = subprocess.run(
                    _step(payload, stage), check=False, text=True, capture_output=True, env=environment
                )
                if completed.returncode:
                    raise RuntimeError((completed.stderr or completed.stdout)[-2000:])
                state = _parse_step3(completed.stdout)
                master = state["master_state"]
                progress = {
                    "progress_percent": int(float(state.get("percent") or 0)),
                    "completed_units": int(state.get("completed") or 0),
                    "total_units": int(state.get("total") or 0),
                    "unit": "rules",
                    "current_item": state.get("current_rule"),
                }
                if master == "SUCCEEDED":
                    monitoring_error = _sync_evidence(payload, binding, terminal=True)
                    if monitoring_error:
                        raise RuntimeError(monitoring_error)
                    _write_status(
                        request_path,
                        payload,
                        "success",
                        "GATK Master and logger evidence completed",
                        **progress,
                    )
                    return
                if master == "FAILED":
                    raise RuntimeError(str(state.get("message") or "GATK Master failed"))
                _write_status(
                    request_path,
                    payload,
                    "running",
                    monitoring_error or str(state.get("message") or master),
                    monitoring_health="degraded" if monitoring_error else "healthy",
                    **progress,
                )
                time.sleep(int(os.environ.get("GATK_MONITOR_INTERVAL_SECONDS", "30")))
        elif stage == "step6_materialize":
            _materialize(payload)
            _write_status(
                request_path,
                payload,
                "success",
                "GATK delivery materialized to the approved result root",
            )
        else:
            completed = _run_frozen_stage(
                _step(payload, stage),
                stage=stage,
                environment=environment,
                on_wait=lambda message: _write_status(
                    request_path, payload, "running", message
                ),
            )
            _write_status(request_path, payload, "success", completed.stdout[-2000:] or f"{stage} completed")
    except Exception as exc:
        _write_status(request_path, payload, "failed", _failure_message(exc))
        raise


def start(
    analysis_id: str,
    attempt: int,
    stage: str,
    generation: int | None = None,
) -> dict[str, Any]:
    request_path, payload = _load(analysis_id, attempt, stage, generation)
    status_path = _status_path(request_path)
    if status_path.is_file():
        existing = json.loads(status_path.read_text(encoding="utf-8"))
        if (
            int(existing.get("generation") or 1) == int(payload["generation"])
            and existing.get("status") in {"running", "success"}
        ):
            return {"status": existing["status"], "stage": stage}
    log_path = request_path.with_suffix(".worker.log")
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "_worker",
        analysis_id,
        str(attempt),
        stage,
        str(payload["generation"]),
    ]
    with log_path.open("a", encoding="utf-8") as log:
        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    return {"status": "accepted", "stage": stage, "generation": int(payload.get("generation") or 1)}


def main() -> None:
    if len(sys.argv) not in {5, 6} or sys.argv[1] not in {"gatk-runtime", "_worker"}:
        raise SystemExit(
            "usage: gatk_runtime_gate.py gatk-runtime ANALYSIS_ID ATTEMPT STAGE [GENERATION]"
        )
    mode, analysis_id, attempt_text, stage, *generation_text = sys.argv[1:]
    generation = int(generation_text[0]) if generation_text else None
    try:
        if mode == "_worker":
            _execute(analysis_id, int(attempt_text), stage, generation)
        else:
            print(
                json.dumps(
                    start(analysis_id, int(attempt_text), stage, generation),
                    sort_keys=True,
                )
            )
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"GATK runtime rejected: {exc}") from exc


if __name__ == "__main__":
    main()
