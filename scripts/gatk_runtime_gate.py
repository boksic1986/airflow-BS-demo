#!/usr/bin/env python3
"""Restricted node200 runtime for one immutable GATK Step1-Step6 bundle."""

from __future__ import annotations

from datetime import datetime, timezone
from contextlib import contextmanager
import fcntl
import csv
import io
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
    "step7_cleanup": "Step7_cleanup_sfs.sh",
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
    if payload.get('stage') == 'step3_monitor' and '_monitor_reconnect' in payload:
        progress['monitor_reconnect'] = payload['_monitor_reconnect']
        if payload['_monitor_reconnect']['phase'] != 'healthy':
            progress['monitoring_health'] = 'degraded'
        else:
            progress.setdefault('monitoring_health', 'healthy')
    master_fields = {}
    if '_cce_master_result' in payload or {'cce_master_binding', 'cce_master_submit_execution_id'}.intersection(progress):
        if __package__:
            from .cce_recovery_inventory import master_receipt_fields
        else:
            from cce_recovery_inventory import master_receipt_fields
        master_fields = master_receipt_fields(payload, pipeline='gatk', details=progress)
    if payload.get("stage") in STAGE_SCRIPTS and payload.get("stage") != "step7_cleanup":
        if request_path.with_suffix(".worker.state.json").exists():
            _assert_current_dispatch(request_path, payload)
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
        **master_fields,
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
        # Keep a concise diagnostic, not kubectl arguments/private paths from a traceback.
        return f"GATK evidence bridge failed (exit {completed.returncode})"
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
    from cce_paired_runtime import stage_command
    paired = stage_command(_bundle(payload), stage, payload=payload, gate=sys.modules[__name__], pipeline='gatk')
    if paired is not None:
        return paired
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
    result_project_name = str(prepare.get("result_project_name") or "")
    if result_project_name:
        source_project_name = Path(str(prepare.get("source_project_dir") or "")).name
        expected_project_name = f"{source_project_name}_GATK"
        if not source_project_name or result_project_name != expected_project_name:
            raise ValueError("GATK result project name does not match the frozen source project")
        expected_root = (configured_root / result_project_name).resolve()
    else:
        expected_root = (
            configured_root
            / str(prepare.get("batch") or "")
            / str(payload["analysis_id"])
        ).resolve()
    if requested_root != expected_root or configured_root not in requested_root.parents:
        raise ValueError("GATK result_root is outside the approved delivery location")
    return requested_root


def _transfer_stage_root(payload: dict[str, Any]) -> Path:
    configured_root = os.environ.get("GATK_TRANSFER_SPOOL_ROOT", "").strip()
    spool_root = (
        Path(configured_root).resolve()
        if configured_root
        else (_root().parent / "transfer-progress").resolve()
    )
    path = (
        spool_root
        / str(payload["analysis_id"])
        / f"attempt-{int(payload['attempt'])}"
        / str(payload["stage"])
    ).resolve()
    if spool_root not in path.parents:
        raise ValueError("GATK transfer progress path escapes spool root")
    return path


def _transfer_progress_root(payload: dict[str, Any]) -> Path:
    stage_root = _transfer_stage_root(payload)
    if payload.get("stage") not in {"step1_upload", "step5_download"}:
        return stage_root
    generation = int(payload.get("generation") or 1)
    if generation < 1:
        raise ValueError("GATK transfer generation must be positive")
    path = (stage_root / f"generation-{generation}").resolve()
    if stage_root not in path.parents:
        raise ValueError("GATK transfer generation path escapes stage root")
    return path


def _transfer_plan_path(payload: dict[str, Any]) -> Path:
    return _transfer_progress_root(payload) / "transfer-plan.json"


def _transfer_environment(payload: dict[str, Any]) -> dict[str, str]:
    root = _transfer_progress_root(payload)
    return {
        "WGS_TRANSFER_PROGRESS_ROOT": str(root),
        "WGS_TRANSFER_ANALYSIS_ID": str(payload["analysis_id"]),
        "WGS_TRANSFER_ATTEMPT": str(payload["attempt"]),
        "WGS_TRANSFER_STAGE": str(payload["stage"]),
        "WGS_TRANSFER_DIRECTION": (
            "upload" if payload["stage"] == "step1_upload" else "download"
        ),
        "WGS_TRANSFER_PLAN_PATH": str(_transfer_plan_path(payload)),
        "WGS_ORCHESTRATION_CONTRACT_VERSION": str(
            payload.get("orchestration_contract_version") or 1
        ),
        "WGS_STAGE_EXECUTION_ID": str(payload.get("execution_id") or ""),
        "WGS_STAGE_GENERATION": str(payload.get("generation") or 1),
        "WGS_STAGE_REQUEST_HASH": str(payload.get("request_hash") or ""),
    }


def _create_step1_transfer_plan(payload: dict[str, Any]) -> dict[str, Any]:
    path = _transfer_plan_path(payload)
    if path.is_file() and not path.is_symlink():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if (
            existing.get("schema_version") == "wgs-runtime.transfer-plan.v1"
            and existing.get("analysis_id") == payload["analysis_id"]
            and int(existing.get("attempt") or 0) == int(payload["attempt"])
            and existing.get("stage") == "step1_upload"
            and existing.get("execution_id") == payload.get("execution_id")
            and int(existing.get("generation") or 0)
            == int(payload.get("generation") or 1)
            and existing.get("request_hash") == payload.get("request_hash")
        ):
            return existing
        raise RuntimeError("existing GATK transfer plan identity mismatch")

    runtime = yaml.safe_load(
        (_bundle(payload) / "BATCH_RUNTIME.yaml").read_text(encoding="utf-8")
    )
    sources = runtime.get("transfer_sources") if isinstance(runtime, dict) else None
    if not isinstance(sources, list) or not sources:
        raise RuntimeError("GATK Step1 transfer sources are unavailable")
    entries: list[dict[str, Any]] = []
    labels: set[str] = set()
    for item in sources:
        if not isinstance(item, dict):
            raise RuntimeError("GATK Step1 transfer source is invalid")
        source = Path(str(item.get("source") or "")).expanduser().resolve(strict=True)
        label = str(item.get("target") or "")
        if not source.is_file() or source.stat().st_size <= 0:
            raise RuntimeError("GATK Step1 transfer source is missing or empty")
        if not label or Path(label).name != label or label in labels:
            raise RuntimeError("GATK Step1 transfer target is invalid or duplicated")
        labels.add(label)
        entries.append({"relative_path": label, "size_bytes": source.stat().st_size})
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    plan = {
        "schema_version": "wgs-runtime.transfer-plan.v1",
        "analysis_id": payload["analysis_id"],
        "attempt": int(payload["attempt"]),
        "stage": "step1_upload",
        "execution_id": payload.get("execution_id"),
        "generation": int(payload.get("generation") or 1),
        "request_hash": payload.get("request_hash"),
        "entries": entries,
        "files_total": len(entries),
        "bytes_total": sum(int(item["size_bytes"]) for item in entries),
        "manifest_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(path, plan)
    return plan


def _marker_values(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("transfer marker is unavailable")
    return dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)


def _create_step5_transfer_plan(payload: dict[str, Any], *, persist: bool = True) -> dict[str, Any] | None:
    """Discover totals only after READY and its bound manifest have been published."""
    delivery = _bundle(payload) / "cloud_delivery"
    try:
        runtime = yaml.safe_load((_bundle(payload) / "BATCH_RUNTIME.yaml").read_text())
        identity = runtime["identity"]
        if identity["run_id"] != f"{payload['analysis_id']}-a{int(payload['attempt'])}":
            return None
        ready = _marker_values(delivery / "READY")
        if ready.get("status") != "READY" or any(ready.get(key) != identity.get(key) for key in ("project", "batch", "run_id")):
            return None
        manifest = delivery / "payload-manifest.tsv"
        if delivery.is_symlink() or manifest.is_symlink():
            return None
        content = manifest.read_bytes()
        if hashlib.md5(content).hexdigest() != ready.get("manifest_md5"):
            return None
        entries = []
        labels = set()
        for row in csv.DictReader(io.StringIO(content.decode("utf-8")), delimiter="\t"):
            label = row["relative_path"]
            target = delivery / label
            if (not label or Path(label).is_absolute() or ".." in Path(label).parts
                    or "\\" in label or label in labels or target.is_symlink()
                    or delivery.resolve() not in target.resolve().parents):
                return None
            total = int(row["size_bytes"])
            if total < 0 or not re.fullmatch(r"[0-9a-f]{32}", row["md5"]):
                return None
            if row.get("status") != "source_verified":
                return None
            labels.add(label)
            entries.append(dict(relative_path=label, size_bytes=total, md5=row["md5"]))
        if not entries:
            return None
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        return None
    plan = {
        "schema_version": "wgs-runtime.transfer-plan.v1",
        **{key: payload.get(key) for key in ("analysis_id", "attempt", "stage", "execution_id", "request_hash")},
        "generation": int(payload.get("generation") or 1),
        "entries": entries, "files_total": len(entries),
        "bytes_total": sum(item["size_bytes"] for item in entries),
        "manifest_sha256": hashlib.sha256(content).hexdigest(),
        "manifest_md5": ready["manifest_md5"],
        "delivery_identity": {key: identity[key] for key in ("project", "batch", "run_id")},
    }
    path = _transfer_plan_path(payload)
    if not persist:
        return plan
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = json.loads(path.read_text())
        if existing != plan:
            raise RuntimeError("GATK download transfer plan changed within one generation")
    else:
        _atomic_json(path, plan)
    return plan


def _finalize_step5_transfer_progress(payload: dict[str, Any], plan: dict[str, Any], *, publish: bool = True) -> dict[str, Any]:
    """Publish completion from the successful stage receipt and unchanged verified files."""
    request = _request_path(str(payload["analysis_id"]), int(payload["attempt"]), "step5_download")
    receipt = json.loads(_status_path(request).read_text())
    expected_hash = receipt.pop("receipt_hash", None)
    actual_hash = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if (receipt.get("status") != "success" or actual_hash != expected_hash
            or any(receipt.get(key) != payload.get(key) for key in
                   ("analysis_id", "attempt", "stage", "execution_id", "generation", "request_hash"))):
        raise ValueError("GATK download has no matching successful stage receipt")
    delivery = _bundle(payload) / "cloud_delivery"
    marker = _marker_values(delivery / "DOWNLOAD_VERIFIED")
    ledger_path = delivery / "DOWNLOAD_VERIFIED.json"
    if ledger_path.is_symlink():
        raise ValueError("unsafe download verification ledger")
    ledger = json.loads(ledger_path.read_text())
    expected = {**plan["delivery_identity"], "manifest_md5": plan["manifest_md5"]}
    if (marker.get("status") != "PASS"
            or any(marker.get(key) != value or ledger.get(key) != value for key, value in expected.items())
            or int(marker.get("total_bytes", -1)) != plan["bytes_total"]
            or int(marker.get("file_count", -1)) != len(plan["entries"])):
        raise ValueError("download verification does not match manifest")
    verified = {item["relative_path"]: item for item in ledger["files"]}
    if len(verified) != len(plan["entries"]):
        raise ValueError("download verification file count mismatch")
    for entry in plan["entries"]:
        target = delivery / entry["relative_path"]
        stat = target.stat()
        record = verified.get(entry["relative_path"], {})
        if (target.is_symlink() or delivery.resolve() not in target.resolve().parents
                or stat.st_size != entry["size_bytes"]
                or any(record.get(key) != entry[key] for key in ("size_bytes", "md5"))
                or any(record.get(key) != getattr(stat, key) for key in ("st_dev", "st_ino", "st_mtime_ns"))):
            raise ValueError("downloaded file changed since MD5 verification")
    progress = _aggregate_transfer_progress(payload, plan, publish=False)
    progress.update(state="success", bytes_done=plan["bytes_total"], files_done=len(plan["entries"]),
                    source="verified-download-receipt", completed_at=receipt["updated_at"],
                    heartbeat_at=receipt["updated_at"], recorded_at=datetime.now(timezone.utc).isoformat(),
                    verification_status="verified", message="Download manifest and MD5 verification completed",
                    receipt_hash=expected_hash, current_file=None, speed_bytes_per_second=0, eta_seconds=0)
    for item in progress["files"]:
        item.update(status="success", bytes_done=item["bytes_total"], checksum_status="verified")
    if publish:
        _transfer_progress_root(payload).mkdir(parents=True, exist_ok=True)
        _atomic_json(_transfer_progress_root(payload) / "progress.json", progress)
        if not _publish_step1_progress(payload, progress):
            raise ValueError("download progress request superseded; public snapshot unchanged")
    return progress


def _raw_transfer_identity_matches(
    row: dict[str, Any], payload: dict[str, Any]
) -> bool:
    if row.get("execution_id") not in {None, "", payload.get("execution_id")}:
        return False
    if row.get("request_hash") not in {None, "", payload.get("request_hash")}:
        return False
    generation = row.get("generation")
    if generation in {None, ""}:
        return True
    try:
        return int(generation) == int(payload.get("generation") or 1)
    except (TypeError, ValueError):
        return False


def _aggregate_transfer_progress(
    payload: dict[str, Any], plan: dict[str, Any], *, publish: bool = True
) -> dict[str, Any]:
    root = _transfer_progress_root(payload)
    rows: dict[str, dict[str, Any]] = {}
    for path in root.glob("*.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        key = str(row.get("file_key") or "")
        if (
            row.get("schema_version") == "wgs-runtime.transfer-progress.v1"
            and row.get("analysis_id") == payload["analysis_id"]
            and int(row.get("attempt") or 0) == int(payload["attempt"])
            and row.get("stage") == payload["stage"]
            and _raw_transfer_identity_matches(row, payload)
            and re.fullmatch(r"[0-9a-f]{64}", key)
            and str(row.get("heartbeat_at") or "")
            >= str(rows.get(key, {}).get("heartbeat_at") or "")
        ):
            rows[key] = row
    files = []
    for entry in plan["entries"]:
        label = str(entry["relative_path"])
        total = int(entry["size_bytes"])
        key = hashlib.sha256(label.encode("utf-8")).hexdigest()
        row = rows.get(key, {})
        status = str(row.get("state") or "accepted").lower()
        if status not in {"accepted", "running", "success", "failed", "canceled"}:
            status = "running"
        done = min(max(0, int(row.get("bytes_done") or 0)), total)
        if status == "success":
            done = total
        files.append(
            {
                "file_key": key,
                "display_name": label,
                "bytes_total": total,
                "bytes_done": done,
                "speed_bps": max(0, int(row.get("speed_bytes_per_second") or 0)),
                "status": status,
                "checksum_status": str(row.get("checksum_status") or "pending"),
                "error_message": str(row.get("error_summary") or "")[-2000:] or None,
            }
        )
    states = {item["status"] for item in files}
    completed = sum(item["status"] == "success" for item in files)
    state = (
        "failed"
        if "failed" in states
        else "success"
        if files and completed == len(files)
        else "running"
    )
    download = payload["stage"] == "step5_download"
    # File-copy completion does not certify manifest/MD5 verification.
    if download and state == "success":
        state = "running"
    total = sum(int(item["bytes_total"]) for item in files)
    done = sum(int(item["bytes_done"]) for item in files)
    speed = sum(
        int(item["speed_bps"]) for item in files if item["status"] == "running"
    )
    progress = {
        "schema_version": "wgs-runtime.transfer-progress.v2",
        "transfer_id": f"{payload['analysis_id']}-a{int(payload['attempt'])}-{'result' if download else 'input'}",
        "analysis_id": payload["analysis_id"],
        "attempt": int(payload["attempt"]),
        "stage": payload["stage"],
        "direction": "download" if download else "upload",
        "state": state,
        "bytes_total": total,
        "bytes_done": done,
        "files_total": len(files),
        "files_done": completed,
        "message": "Verifying downloaded results" if download and files and completed == len(files) else None,
        "current_file": next(
            (item["display_name"] for item in files if item["status"] == "running"),
            None,
        ),
        "speed_bytes_per_second": speed,
        "eta_seconds": int((total - done) / speed) if speed and done < total else None,
        "heartbeat_at": datetime.now(timezone.utc).isoformat(),
        "monitoring_health": "healthy",
        "source": "obsutil-checkpoint",
        "checkpoint_ref": "obsutil-multipart",
        "manifest_sha256": plan["manifest_sha256"],
        "orchestration_contract_version": int(
            payload.get("orchestration_contract_version") or 1
        ),
        "execution_id": payload.get("execution_id"),
        "generation": int(payload.get("generation") or 1),
        "request_hash": payload.get("request_hash"),
        "files": files,
    }
    if publish:
        root.mkdir(parents=True, exist_ok=True)
        _atomic_json(root / "progress.json", progress)
        _publish_step1_progress(payload, progress)
    return progress


def _aggregate_step1_transfer_progress(
    payload: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    return _aggregate_transfer_progress(payload, plan)


def _publish_step1_progress(
    payload: dict[str, Any], progress: dict[str, Any]
) -> bool:
    stage_root = _transfer_stage_root(payload)
    stage_root.mkdir(parents=True, exist_ok=True)
    lock_path = stage_root / ".progress.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            try:
                current = json.loads(
                    _request_path(
                        str(payload["analysis_id"]),
                        int(payload["attempt"]),
                        str(payload["stage"]),
                    ).read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                return False
            expected_identity = (
                payload.get("analysis_id"),
                int(payload.get("attempt") or 0),
                payload.get("stage"),
                payload.get("execution_id"),
                int(payload.get("generation") or 1),
                payload.get("request_hash"),
            )
            current_identity = (
                current.get("analysis_id"),
                int(current.get("attempt") or 0),
                current.get("stage"),
                current.get("execution_id"),
                int(current.get("generation") or 1),
                current.get("request_hash"),
            )
            if current_identity != expected_identity:
                return False
            public_path = stage_root / "progress.json"
            if public_path.is_file() and not public_path.is_symlink():
                try:
                    existing = json.loads(public_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    return False
                existing_generation = int(existing.get("generation") or 0)
                if existing_generation > expected_identity[4]:
                    return False
                if existing_generation == expected_identity[4] and (
                    existing.get("execution_id") != payload.get("execution_id")
                    or existing.get("request_hash") != payload.get("request_hash")
                ):
                    return False
            _atomic_json(public_path, progress)
            return True
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _run_step1_with_progress(
    payload: dict[str, Any], environment: dict[str, str]
) -> None:
    plan = _create_step1_transfer_plan(payload)
    process = subprocess.Popen(_step(payload, "step1_upload"), env=environment)
    while process.poll() is None:
        _aggregate_step1_transfer_progress(payload, plan)
        time.sleep(1)
    _aggregate_step1_transfer_progress(payload, plan)
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, process.args)


def _run_step5_with_progress(payload: dict[str, Any], environment: dict[str, str]) -> None:
    ready_path = _bundle(payload) / "cloud_delivery" / "READY"
    def ready_stamp():
        try:
            stat = ready_path.stat()
            return stat.st_ino, stat.st_mtime_ns, stat.st_size
        except OSError:
            return None
    before = ready_stamp()
    process = subprocess.Popen(_step(payload, "step5_download"), env=environment)
    while True:
        # Metadata is downloaded first; the wrapper discovers this plan while copying.
        try:
            # Do not freeze a previous generation's READY while new metadata downloads.
            stamp = ready_stamp()
            plan = _create_step5_transfer_plan(payload) if stamp is not None and stamp != before else None
            if plan is not None:
                _aggregate_transfer_progress(payload, plan)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            # A monitoring failure must not orphan or restart a real transfer.
            print(f"GATK download progress unavailable: {type(exc).__name__}", flush=True)
        if process.poll() is not None:
            break
        time.sleep(1)
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, process.args)


def _materialize(payload: dict[str, Any]) -> Path:
    from cce_paired_runtime import load_runtime, downstream_registered
    paired = load_runtime()
    if paired is None:
        return _materialize_to_approved_root(payload)
    downstream_registered(payload, binding=_load_binding(payload), gate=sys.modules[__name__], pipeline='gatk',
        materialize=_materialize_to_approved_root)
    return _materialize_result_root(payload)


def _materialize_to_approved_root(payload: dict[str, Any]) -> Path:
    bundle = _bundle(payload)
    runtime = yaml.safe_load((bundle / "BATCH_RUNTIME.yaml").read_text(encoding="utf-8"))
    if not isinstance(runtime, dict) or runtime.get("schema_version") != 3:
        raise RuntimeError("GATK BATCH_RUNTIME.yaml is invalid")
    identity = runtime.get("identity") or {}
    tools = runtime.get("tools") or {}
    permissions = runtime.get("permissions")
    if not isinstance(permissions, dict):
        raise RuntimeError("GATK BATCH_RUNTIME.yaml permissions are invalid")
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
    bundle_path = str(bundle)
    sys.path.insert(0, bundle_path)
    try:
        spec.loader.exec_module(delivery)
    finally:
        sys.path.remove(bundle_path)

    result_root = _materialize_result_root(payload)
    delivery.materialize_results(
        bundle / "cloud_delivery",
        result_root,
        str(identity.get("batch") or ""),
        run_id=expected_run_id,
        zstd_bin=str(tools.get("zstd_bin") or ""),
        project_name=str(identity.get("project") or ""),
        permissions=permissions,
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
    master_match = re.search(
        r"(?m)^master_state=(PENDING|RUNNING|SUCCEEDED|FAILED)(?:\s|$)", stdout
    )
    if master_match:
        progress_match = re.search(
            r"(?m)^progress=(\d+)/(\d+).*?\(([0-9]+(?:\.[0-9]+)?)%\)",
            stdout,
        )

        def text_value(name: str) -> str | None:
            match = re.search(rf"(?m)^{re.escape(name)}=(.*)$", stdout)
            return match.group(1).strip() if match else None

        return {
            "master_state": master_match.group(1),
            "completed": int(progress_match.group(1)) if progress_match else 0,
            "total": int(progress_match.group(2)) if progress_match else 0,
            "percent": float(progress_match.group(3)) if progress_match else 0.0,
            "current_rule": text_value("current_rule_or_group"),
            "bioinformatics_stage": text_value("bioinformatics_stage"),
            "message": text_value("message"),
        }
    raise RuntimeError("Step3 did not return a valid Master status")


def _failure_message(error: Exception) -> str:
    if isinstance(error, subprocess.CalledProcessError):
        detail = error.stderr or error.stdout
        if detail:
            return str(detail).strip()[-2000:]
    return str(error)


def _execute_stage(
    analysis_id: str,
    attempt: int,
    stage: str,
    generation: int | None = None,
) -> None:
    request_path, payload = _load(analysis_id, attempt, stage, generation)
    if stage == "step7_cleanup":
        from gatk_maintenance_gate import execute_cleanup
        execute_cleanup(payload, _root(),
            lambda state, message: _write_status(request_path, payload, state, message))
        return
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
    }
    if stage in {"step1_upload", "step5_download"}:
        environment.update(_transfer_environment(payload))
    try:
        if stage == 'step2_master' and not payload.get('resume_action_id'):
            if __package__:
                from .cce_paired_runtime import submit_registered
            else:
                from cce_paired_runtime import submit_registered
            result = submit_registered(payload, binding=_load_binding(payload), gate=sys.modules[__name__], pipeline='gatk')
            if result is not None:
                payload['_cce_master_result'] = result
                _write_status(request_path,payload,'success','Verified initial Master handoff completed')
                return
        if payload.get('resume_action_id') and stage == 'step2_master':
            if __package__:
                from .cce_paired_runtime import resume_registered
            else:
                from cce_paired_runtime import resume_registered
            result = resume_registered(payload, binding=_load_binding(payload),
                gate=sys.modules[__name__], pipeline='gatk')
            if result is None:
                raise RuntimeError('GATK Resume requires paired registered recovery')
            payload['_cce_master_result'] = result
            payload['resume_master_uid'] = result['master_uid']
            _write_status(request_path, payload, 'success', 'Verified Master recovery completed')
            return
        if stage == "prepare":
            completed = subprocess.run(
                _prepare(payload), check=True, text=True, capture_output=True, env=environment
            )
            _write_binding(payload)
            _write_status(request_path, payload, "success", completed.stdout[-2000:] or "GATK contract prepared")
            return
        if stage == "step3_monitor":
            if __package__:
                from .cce_paired_runtime import monitor_registered, prepare_monitor_registered
                from .cce_recovery_deadline import monitor_wait
            else:
                from cce_paired_runtime import monitor_registered, prepare_monitor_registered
                from cce_recovery_deadline import monitor_wait
            binding = _load_binding(payload)
            monitor_wait(payload, 0)
            prepare_monitor_registered(payload, binding=binding, gate=sys.modules[__name__], pipeline='gatk')
            while True:
                monitor_wait(payload, 0)
                state = monitor_registered(payload, binding=binding, gate=sys.modules[__name__], pipeline='gatk')
                paired = state is not None
                if not paired:
                    if payload.get('resume_action_id'):
                        raise RuntimeError('GATK Resume requires paired registered recovery')
                    completed = subprocess.run(
                        _step(payload, stage), check=False, text=True, capture_output=True, env=environment
                    )
                    if completed.returncode:
                        raise RuntimeError((completed.stderr or completed.stdout)[-2000:])
                    state = _parse_step3(completed.stdout)
                master = state["master_state"]
                evidence_binding = {**binding, 'cce_bundle': payload['_cce_master_result']['bundle']} if paired else binding
                monitoring_error = _sync_evidence(payload, evidence_binding, terminal=master in {'SUCCEEDED','FAILED'})
                progress = {
                    "progress_percent": int(float(state.get("percent") or 0)),
                    "completed_units": int(state.get("completed") or 0),
                    "total_units": int(state.get("total") or 0),
                    "unit": "rules",
                    "current_item": state.get("current_rule"),
                }
                if master == "SUCCEEDED":
                    _write_status(
                        request_path,
                        payload,
                        "success",
                        "分析完成，日志采集异常" if monitoring_error else "GATK Master and logger evidence completed",
                        monitoring_health="degraded" if monitoring_error else "healthy",
                        monitoring_error=monitoring_error,
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
                time.sleep(monitor_wait(payload, int(os.environ.get("GATK_MONITOR_INTERVAL_SECONDS", "30"))))
        elif stage == "step1_upload":
            _run_step1_with_progress(payload, environment)
            _write_status(
                request_path,
                payload,
                "success",
                "step1_upload completed with transfer progress evidence",
            )
        elif stage == "step5_download":
            _run_step5_with_progress(payload, environment)
            _write_status(request_path, payload, "success", "GATK download and verification completed")
            # Telemetry cannot change an already verified stage outcome.
            try:
                plan = _create_step5_transfer_plan(payload)
                if plan is not None:
                    _finalize_step5_transfer_progress(payload, plan)
            except (OSError, ValueError, KeyError, RuntimeError) as exc:
                print(f"GATK download progress finalization unavailable: {type(exc).__name__}", flush=True)
        elif stage == "step6_materialize":
            _materialize(payload)
            # The terminal reader is deleted asynchronously. Refresh once after
            # delivery so its earlier Running observation cannot strand Step7.
            try:
                monitoring_error = _sync_evidence(payload, _load_binding(payload), terminal=False)
            except (OSError, ValueError, RuntimeError) as exc:
                monitoring_error = f"GATK workload finalization unavailable: {type(exc).__name__}"
            _write_status(
                request_path,
                payload,
                "success",
                "GATK delivery materialized to the approved result root",
                monitoring_health="degraded" if monitoring_error else "healthy",
                monitoring_error=monitoring_error,
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


def _start_legacy(
    analysis_id: str,
    attempt: int,
    stage: str,
    generation: int | None = None,
) -> dict[str, Any]:
    request_path, payload = _load(analysis_id, attempt, stage, generation)
    status_path = _status_path(request_path)
    if status_path.is_file():
        if stage == "step7_cleanup":
            from gatk_maintenance_gate import _safe_bytes
            existing = json.loads(_safe_bytes(status_path, _root()))
        else:
            existing = json.loads(status_path.read_text(encoding="utf-8"))
        if (
            int(existing.get("generation") or 1) == int(payload["generation"])
            and existing.get("status") in {"running", "success"}
            and (stage != "step7_cleanup" or all(existing.get(key) == payload.get(key)
                for key in ("analysis_id", "attempt", "stage", "execution_id", "request_hash")))
        ):
            return {"status": existing["status"], "stage": stage}
    if stage == "step7_cleanup":
        from gatk_maintenance_gate import check_start
        check_start(payload, _root())
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


_DISPATCH_KEYS = ("analysis_id", "attempt", "stage", "generation", "execution_id", "request_hash")


def _dispatch_identity(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: payload.get(key) for key in _DISPATCH_KEYS}


def _assert_current_dispatch(path: Path, payload: dict[str, Any]) -> None:
    current = json.loads(path.read_text(encoding="utf-8"))
    if _dispatch_identity(current) != _dispatch_identity(payload):
        raise RuntimeError("GATK dispatcher superseded by another execution")


@contextmanager
def _dispatch_lock(path: Path, *, blocking: bool = False):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError as exc:
            raise RuntimeError("GATK dispatcher is still active") from exc
        yield
    finally:
        os.close(fd)


def _process_identity(pid: int) -> dict[str, Any] | None:
    try:
        # comm can contain spaces: starttime is field 22, after the closing ')'.
        stat = Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()
        return {"pid": pid, "starttime": stat[19],
                "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}
    except FileNotFoundError:
        return None


def _dispatch_state(path: Path) -> dict[str, Any] | None:
    state_path = path.with_suffix(".worker.state.json")
    try:
        fd = os.open(state_path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict) or value.get("schema_version") != "gatk-runtime.dispatcher.v1":
        raise RuntimeError("GATK dispatcher evidence is invalid")
    return value


def _save_dispatch(path: Path, payload: dict[str, Any], state: str,
                   process: dict[str, Any] | None = None) -> None:
    target = path.with_suffix(".worker.state.json")
    temporary = target.with_suffix(".partial")
    value = {"schema_version": "gatk-runtime.dispatcher.v1",
             **_dispatch_identity(payload), "state": state, "process": process}
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _dispatch_receipt(path: Path, payload: dict[str, Any]) -> dict[str, Any] | None:
    status_path = _status_path(path)
    if not status_path.exists():
        return None
    value = json.loads(status_path.read_text(encoding="utf-8"))
    return value if _dispatch_identity(value) == _dispatch_identity(payload) else None


def _execute(analysis_id: str, attempt: int, stage: str, generation: int | None = None) -> None:
    if stage in {"prepare", "step7_cleanup"}:
        return _execute_stage(analysis_id, attempt, stage, generation)
    path = _request_path(analysis_id, attempt, stage)
    with _dispatch_lock(path.with_suffix(".worker.lock")):
        path, payload = _load(analysis_id, attempt, stage, generation)
        with _dispatch_lock(path.with_suffix(".launch.lock"), blocking=True):
            existing = _dispatch_receipt(path, payload)
            if existing and existing.get("status") in TERMINAL:
                return
            previous = _dispatch_state(path)
            if previous and _dispatch_identity(previous) != _dispatch_identity(payload):
                raise RuntimeError("GATK dispatcher superseded; launch authorization required")
            _save_dispatch(path, payload, "running", _process_identity(os.getpid()))
        try:
            _execute_stage(analysis_id, attempt, stage, generation)
        finally:
            # Hold the worker lock through the durable completion record. A new
            # generation cannot mistake a stopped parent for a finished writer.
            with _dispatch_lock(path.with_suffix(".launch.lock"), blocking=True):
                receipt = _dispatch_receipt(path, payload)
                state = "finished" if receipt and receipt.get("status") in TERMINAL else "uncertain"
                _save_dispatch(path, payload, state, _process_identity(os.getpid()))


def start(analysis_id: str, attempt: int, stage: str,
          generation: int | None = None, *, expected_hash: str | None = None) -> dict[str, Any]:
    if stage in {"prepare", "step7_cleanup"}:
        return _start_legacy(analysis_id, attempt, stage, generation)
    path = _request_path(analysis_id, attempt, stage)
    with _dispatch_lock(path.with_suffix(".launch.lock")):
        path, payload = _load(analysis_id, attempt, stage, generation)
        if expected_hash is not None and payload.get('request_hash') != expected_hash:
            raise ValueError('Step4 dispatch was superseded')
        if stage=='step4_publish' and ('publish_dispatch_version' in payload or expected_hash is not None):
            if __package__:
                from .cce_publish_recovery import registered_publish, require_publish_deadline
            else:
                from cce_publish_recovery import registered_publish, require_publish_deadline
            registered_publish(payload,gate=sys.modules[__name__],pipeline='gatk')
            require_publish_deadline(payload)
        previous = _dispatch_state(path)
        same = previous is not None and _dispatch_identity(previous) == _dispatch_identity(payload)
        receipt = _dispatch_receipt(path, payload)
        if receipt and receipt.get("status") in TERMINAL:
            return {"status": receipt["status"], "stage": stage}
        if previous and previous.get("state") != "finished":
            process = previous.get("process")
            if not process:
                raise RuntimeError("GATK dispatcher launch outcome is uncertain")
            if _process_identity(int(process["pid"])) == process:
                if same:
                    return {"status": "accepted", "stage": stage,
                            "generation": payload["generation"]}
                raise RuntimeError("GATK dispatcher from previous generation is still active")
            # An interrupted dispatcher can leave subprocesses behind. A dead
            # parent alone is not evidence authorizing another protected writer.
            raise RuntimeError("GATK dispatcher stopped without final quiescence evidence")
        if previous is None and _status_path(path).exists():
            raise RuntimeError("GATK dispatcher legacy execution needs quiescence evidence")
        with _dispatch_lock(path.with_suffix(".worker.lock")):
            pass
        _save_dispatch(path, payload, "launching")
        command = [sys.executable, str(Path(__file__).resolve()), "_worker",
                   analysis_id, str(attempt), stage, str(payload["generation"])]
        with path.with_suffix(".worker.log").open("a", encoding="utf-8") as log:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
        _save_dispatch(path, payload, "launching", _process_identity(process.pid))
        return {"status": "accepted", "stage": stage, "generation": payload["generation"]}


def main() -> None:
    if sys.argv[1:2] == ['--publish-dispatch']:
        from cce_publish_recovery import publish_dispatch_command
        print(json.dumps(publish_dispatch_command(sys.argv[1:],gate=sys.modules[__name__],pipeline='gatk'),sort_keys=True))
        return
    if sys.argv[1:2] == ['--publish-probe']:
        from cce_publish_recovery import publish_probe_command
        print(json.dumps(publish_probe_command(sys.argv[1:],gate=sys.modules[__name__],pipeline='gatk'),sort_keys=True))
        return
    if sys.argv[1:2] == ['--recovery-probe']:
        from cce_paired_runtime import worker_probe_command
        print(json.dumps(worker_probe_command(sys.argv[1:],gate=sys.modules[__name__],pipeline='gatk'),sort_keys=True))
        return
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
