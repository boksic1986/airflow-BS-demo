#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

import yaml


ANALYSIS_RE = re.compile(r"^WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
SEQUENCING_BATCH_RE = re.compile(r"(?:^|_)([0-9]{8}[A-Z])(?:_|$)")
CCE_RUN_LABEL_RE = re.compile(r"^cce-run-[0-9a-f]{16}$")
STAGES = {
    "prepare",
    "prepare_sampleinfo",
    "prepare_analysis",
    "step1_upload",
    "step2_master",
    "step3_monitor",
    "step4_publish",
    "step4_repair_cram",
    "step5_download",
    "step6_materialize",
    "step7_cleanup",
}
ASYNC_STAGES = {
    "step1_upload",
    "step3_monitor",
    "step4_publish",
    "step4_repair_cram",
    "step5_download",
    "step7_cleanup",
}
STEP_SCRIPTS = {
    "step1_upload": "Step1_upload_fastq.sh",
    "step2_master": "Step2_run.sh",
    "step3_monitor": "Step3_status.sh",
    "step4_publish": "Step4_publish_results.sh",
    "step4_repair_cram": "Step4_publish_results.sh",
    "step5_download": "Step5_download_verify.sh",
    "step6_materialize": "Step6_materialize_results.sh",
    "step7_cleanup": "Step7_cleanup_sfs.sh",
}
STAGE_STATUS_SCHEMA = "wgs-runtime.stage-status.v1"
BINDING_SCHEMA = "wgs-runtime.batch-binding.v2"
REQUEST_ROOT = Path(
    os.getenv(
        "WGS_RUNTIME_REQUEST_ROOT",
        "/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud/runtime/runner-requests",
    )
)
RUNTIME_RUN_ROOT = os.getenv("WGS_RUNTIME_RUN_ROOT", "").strip()
TRANSFER_SPOOL_ROOT = Path(
    os.getenv(
        "WGS_TRANSFER_SPOOL_ROOT",
        str(REQUEST_ROOT.parent / "transfer-progress"),
    )
)
WGS_REPO_ROOT = Path(
    os.getenv(
        "WGS_REPO_ROOT",
        "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1",
    )
)
DEFAULT_RELEASE_ROOTS = {
    "wgs-4.1.1-6c98281": "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1",
    "wgs-4.2.0-b067c72": "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0",
}
WGS_RELEASE_ROOTS_JSON = os.getenv("WGS_RELEASE_ROOTS_JSON", "").strip()
WGS_PYTHON = os.getenv("WGS_PYTHON", "/bi/software/mamba/envs/WGS/bin/python")
WGS_PREPARE_CONFIG = os.getenv(
    "WGS_PREPARE_CONFIG", str(WGS_REPO_ROOT / "prepare" / "config.yaml")
)
WGS_PREPARE_CONFIG_ROOT = Path(
    os.getenv("WGS_PREPARE_CONFIG_ROOT", str(WGS_REPO_ROOT / "prepare"))
)
CCE_OPERATOR_CONFIG = os.getenv(
    "CCE_OPERATOR_CONFIG", "/home/ctapa/.config/wgs/cce.yaml"
)
CCE_PIPELINE_BIN = os.getenv("CCE_PIPELINE_BIN", "").strip()
CCE_PROFILE_ROOT = Path(
    os.getenv(
        "WGS_CCE_PROFILE_ROOT",
        "/bi/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs",
    )
)
MONITOR_INTERVAL_SECONDS = int(os.getenv("WGS_MONITOR_INTERVAL_SECONDS", "5"))
MONITOR_TIMEOUT_SECONDS = int(os.getenv("WGS_MONITOR_TIMEOUT_SECONDS", "432000"))
STEP4_MASTER_COMPLETION_GRACE_SECONDS = int(
    os.getenv("WGS_STEP4_MASTER_COMPLETION_GRACE_SECONDS", "600")
)
STEP7_COMPAT_OBS_FIELDS = {
    "download_parallelism",
    "sdk_attach_crc64",
    "sdk_credentials_file",
    "sdk_download_part_size_bytes",
    "sdk_download_parallelism",
    "sdk_multipart_part_size_mib",
    "sdk_multipart_task_num",
    "sdk_multipart_threshold_bytes",
    "sdk_python",
    "sdk_transfer_adapter",
    "sdk_upload_part_size_bytes",
    "sdk_upload_parallelism",
    "transfer_adapter",
}
STEP5_TRANSFER_PLAN_GRACE_SECONDS = int(
    os.getenv("WGS_STEP5_TRANSFER_PLAN_GRACE_SECONDS", "60")
)
STEP4_MASTER_NOT_SUCCESSFUL = "Step4 requires a successful Master Job"
CCE_EVIDENCE_ROOT = Path(
    os.getenv(
        "WGS_CCE_EVIDENCE_ROOT",
        "/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud/runtime/cce-evidence",
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
        payload.get("schema_version") != "wgs-runtime.request.v4"
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


def _atomic_json(
    path: Path, payload: dict[str, Any], *, mode: int = 0o644
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".partial",
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".partial",
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _freeze_validation_execution_mode(
    payload: dict[str, Any], batch_root: Path
) -> dict[str, Any] | None:
    scope = payload.get("validation_scope")
    if scope is None or scope == "step1_only":
        return None
    if scope == "node97_full":
        if not _truthy("WGS_NODE97_FULL_CANARY_ENABLED"):
            raise RuntimeError("node97 full canary is disabled on node200")
        return None
    if scope != "step3_dryrun":
        raise RuntimeError("unsupported WGS validation scope")
    if not _truthy("WGS_STEP3_DRYRUN_CANARY_ENABLED"):
        raise RuntimeError("Step3 dry-run canary is disabled on node200")
    runtime_path = batch_root / "cce" / "BATCH_RUNTIME.yaml"
    if not runtime_path.is_file():
        raise RuntimeError(
            "WGS prepare did not create BATCH_RUNTIME.yaml; review sample selection and FASTQ readiness"
        )
    before = runtime_path.read_bytes()
    runtime = yaml.safe_load(before)
    workflow = runtime.get("workflow") if isinstance(runtime, dict) else None
    if not isinstance(workflow, dict):
        raise RuntimeError("BATCH_RUNTIME.yaml workflow is invalid")
    current_mode = workflow.get("execution_mode", "analysis")
    if current_mode not in {"analysis", "dry_run"}:
        raise RuntimeError("BATCH_RUNTIME.yaml execution mode is invalid")
    workflow["execution_mode"] = "dry_run"
    _atomic_yaml(runtime_path, runtime)
    after = runtime_path.read_bytes()
    provenance = {
        "schema_version": "wgs-runtime.validation-override.v1",
        "analysis_id": payload["analysis_id"],
        "attempt": payload["attempt"],
        "validation_scope": scope,
        "execution_mode_before": current_mode,
        "execution_mode_after": "dry_run",
        "runtime_sha256_before": hashlib.sha256(before).hexdigest(),
        "runtime_sha256_after": hashlib.sha256(after).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_json(batch_root / "cce" / "VALIDATION_OVERRIDE.json", provenance)
    return provenance


def _write_status(
    payload: dict[str, Any], status: str, message: str = "", **details: Any
) -> bool:
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
    if payload.get("maintenance_action_id"):
        value["maintenance_action_id"] = payload["maintenance_action_id"]
    if payload.get("step7_generation"):
        value["step7_generation"] = payload["step7_generation"]
    if int(payload.get("orchestration_contract_version") or 1) == 2:
        for key in ("execution_id", "generation", "request_hash"):
            if payload.get(key) in {None, ""}:
                raise ValueError(f"contract v2 runtime request is missing {key}")
            value[key] = payload[key]
        value["orchestration_contract_version"] = 2
    status_path = _sidecar_path(payload, ".status.json")
    lock_path = _sidecar_path(payload, ".status.lock")
    rank = {"accepted": 0, "running": 1, "success": 2, "failed": 2}
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        current = _read_json(status_path)
        current_retry_no = current.get("retry_no")
        if (
            "retry_no" not in details
            and type(current_retry_no) is int
            and current_retry_no >= 0
        ):
            value["retry_no"] = current_retry_no
        current_transfer = current.get("transfer")
        if "transfer" not in details and isinstance(current_transfer, dict):
            value["transfer"] = current_transfer
        current_status = str(current.get("status") or "")
        if current_status in {"success", "failed"}:
            return False
        if rank.get(current_status, -1) > rank.get(status, -1):
            return False
        _atomic_json(status_path, value)
    return True


def _truthy(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def _release_repository(payload: dict[str, Any]) -> Path:
    if str(WGS_REPO_ROOT) not in set(DEFAULT_RELEASE_ROOTS.values()):
        return WGS_REPO_ROOT.resolve()
    roots = dict(DEFAULT_RELEASE_ROOTS)
    if WGS_RELEASE_ROOTS_JSON:
        configured = json.loads(WGS_RELEASE_ROOTS_JSON)
        if not isinstance(configured, dict):
            raise RuntimeError("release_unavailable: WGS release root map is invalid")
        roots.update({str(key): str(value) for key, value in configured.items()})
    release_id = str(payload.get("pipeline_release_id") or "")
    value = roots.get(release_id)
    if not value and release_id.startswith("wgs-4.1.1-") and str(
        payload.get("wgs_version") or ""
    ) == "V4.1.1":
        value = DEFAULT_RELEASE_ROOTS["wgs-4.1.1-6c98281"]
    if not value:
        raise RuntimeError("release_unavailable: WGS release is not allowlisted")
    repo = Path(value).resolve()
    approved_root = Path("/bi/biodevrwbi/33.chenjiucheng/project").resolve()
    if approved_root not in repo.parents or not repo.name.startswith("wgs-"):
        raise RuntimeError("release_unavailable: WGS release root is outside the approved project")
    return repo


def validate_release_repository(payload: dict[str, Any]) -> Path:
    version = str(payload.get("wgs_version") or "")
    if version and version != "V4.2.0":
        raise RuntimeError(
            "release_unavailable: historical WGS release requires a frozen binding"
        )
    repo = _release_repository(payload)
    prepare = repo / "prepare" / "prepare_wgs_batch.py"
    if not repo.is_dir() or repo.is_symlink() or not prepare.is_file() or prepare.is_symlink():
        raise RuntimeError("release_unavailable: fixed WGS repository is unavailable")
    return repo


def validate_prepare_config(payload: dict[str, Any] | None = None) -> Path:
    repo = _release_repository(payload) if payload is not None else WGS_REPO_ROOT.resolve()
    config = repo / "prepare" / "config.yaml" if payload is not None else Path(WGS_PREPARE_CONFIG)
    if not config.is_absolute() or not config.is_file() or config.is_symlink():
        raise RuntimeError("release_unavailable: WGS prepare config is unavailable")
    resolved = config.resolve()
    approved_roots = {(repo / "prepare").resolve()}
    if payload is None:
        approved_roots.add(WGS_PREPARE_CONFIG_ROOT.resolve())
    if not any(
        root == resolved.parent or root in resolved.parents
        for root in approved_roots
    ):
        raise RuntimeError(
            "release_unavailable: WGS prepare config is outside approved roots"
        )
    return resolved


def _workdir(payload: dict[str, Any]) -> Path:
    value = Path(str(payload["control_workdir"])).resolve()
    if not RUNTIME_RUN_ROOT:
        raise RuntimeError("WGS_RUNTIME_RUN_ROOT is required")
    runtime_root = Path(RUNTIME_RUN_ROOT).resolve()
    if not runtime_root.is_absolute():
        raise RuntimeError("WGS_RUNTIME_RUN_ROOT must be absolute")
    if runtime_root not in value.parents:
        raise ValueError("node200 workdir is outside the approved runtime root")
    return value


def _binding_path(payload: dict[str, Any]) -> Path:
    return _workdir(payload) / "batch-binding.json"


def build_prepare_command(payload: dict[str, Any]) -> list[str]:
    repository = _release_repository(payload)
    prepare_config = repository / "prepare" / "config.yaml"
    analysis_project_root = Path(str(payload["analysis_project_root"]))
    project_name = str(payload["project_name"])
    batch_no = str(payload["batch_no"])
    fq_path = str(payload["fq_path"])
    for value in (project_name, batch_no):
        if SAFE_COMPONENT_RE.fullmatch(value) is None:
            raise ValueError("project_name and batch_no must be safe path components")
    explicit_prepare_contract = bool(payload.get("sequencing_batch") or payload.get("fastq_root"))
    sequencing_batch = str(payload.get("sequencing_batch") or "").strip()
    if not sequencing_batch:
        sequencing_batch_match = SEQUENCING_BATCH_RE.search(batch_no)
        if sequencing_batch_match is None:
            raise ValueError("analysis batch does not contain a valid sequencing batch")
        sequencing_batch = sequencing_batch_match.group(1)
    if not re.fullmatch(r"[0-9]{8}[A-Z]", sequencing_batch):
        raise ValueError("sequencing_batch is invalid")
    analysis_batch = str(payload.get("analysis_batch") or sequencing_batch).strip()
    if SAFE_COMPONENT_RE.fullmatch(analysis_batch) is None:
        raise ValueError("analysis_batch is invalid")
    fastq_directory = Path(fq_path)
    if not explicit_prepare_contract and sequencing_batch not in fastq_directory.name:
        raise ValueError("FASTQ directory does not identify the sequencing batch")
    fastq_root = Path(str(payload.get("fastq_root") or fastq_directory.parent))
    if not fastq_root.is_absolute():
        raise ValueError("FASTQ root must be absolute")
    stage = str(payload.get("stage") or "prepare")
    subcommand = {
        "prepare": "all",
        "prepare_sampleinfo": "sampleinfo",
        "prepare_analysis": "analysis",
    }.get(stage)
    if subcommand is None:
        raise ValueError("unsupported WGS prepare stage")
    command = [
        WGS_PYTHON,
        str(repository / "prepare" / "prepare_wgs_batch.py"),
        subcommand,
        "--outpath",
        str(analysis_project_root),
        "--prepare-config",
        str(prepare_config),
    ]
    handoff_request = _prepare_handoff_request(payload)
    if handoff_request is not None:
        command.extend(["--handoff-request", str(handoff_request)])
    platform = str(payload.get("platform") or "").strip()
    if platform:
        command.extend(["--platform", platform])
    if subcommand in {"all", "sampleinfo"}:
        command.extend(["--batch", sequencing_batch, "--analysis-batch", analysis_batch])
    if subcommand in {"all", "analysis"}:
        if subcommand == "analysis":
            command.extend([
                "--sampleinfo",
                str(analysis_project_root / "sampleinfo" / f"{batch_no}.sampleinfo.txt"),
            ])
        command.extend([
            "--run-mode",
            "cce",
            "--run-id",
            f"{payload['analysis_id']}-a{int(payload['attempt'])}",
            "--fastq-root",
            str(fastq_root),
            "--cce-config",
            str(_release_operator_config(payload)),
            "--skip-samplelist-ready-check",
        ])
        if payload.get("cce_pipeline_version"):
            if not CCE_PIPELINE_BIN:
                raise RuntimeError("release_unavailable: cce-pipeline executable is not configured")
            cce_pipeline = Path(CCE_PIPELINE_BIN).expanduser()
            if not cce_pipeline.is_absolute():
                raise ValueError("CCE_PIPELINE_BIN must be an absolute path")
            command.extend(["--cce-pipeline", str(cce_pipeline)])
        use_reference = str(payload.get("use_reference") or "").strip()
        if use_reference:
            if use_reference not in {"all", "ref", "no"}:
                raise ValueError("use_reference must be all, ref, or no")
            command.extend(["--use-reference", use_reference])
        if (
            subcommand == "analysis"
            and payload.get("validation_scope") == "node97_full"
            and int(payload["attempt"]) > 1
        ):
            command.extend(["--cce-from-zero", "clean"])
    return command


def _release_operator_config(
    payload: dict[str, Any], *, materialize: bool = False
) -> Path:
    target = Path(str(payload["control_workdir"])) / "release-runtime" / "cce-operator.yaml"
    if not materialize:
        return target
    source = Path(CCE_OPERATOR_CONFIG).expanduser()
    if not source.is_absolute() or not source.is_file() or source.is_symlink():
        raise RuntimeError("release_unavailable: CCE operator config is unavailable")
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    paths = config.get("paths") if isinstance(config, dict) else None
    if not isinstance(paths, dict):
        raise RuntimeError("release_unavailable: CCE operator config paths are invalid")
    paths["repository_root"] = str(_release_repository(payload))
    obs = config.get("obs")
    if isinstance(obs, dict):
        for key in STEP7_COMPAT_OBS_FIELDS:
            obs.pop(key, None)
    target = _workdir(payload) / "release-runtime" / "cce-operator.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = yaml.safe_dump(config, sort_keys=False).encode("utf-8")
    if target.is_file() and not target.is_symlink():
        if target.read_bytes() != encoded:
            raise RuntimeError("release_unavailable: frozen CCE operator config changed")
        return target
    fd, temporary_name = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".partial", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def validate_release_runtime(payload: dict[str, Any]) -> None:
    expected_version = str(payload.get("cce_pipeline_version") or "")
    if not expected_version:
        return
    if not CCE_PIPELINE_BIN:
        raise RuntimeError("release_unavailable: cce-pipeline executable is unavailable")
    executable = Path(CCE_PIPELINE_BIN).expanduser()
    if not executable.is_absolute() or not executable.is_file() or executable.is_symlink():
        raise RuntimeError("release_unavailable: cce-pipeline executable is unavailable")
    version_output = subprocess.run(
        [str(executable), "--version"],
        check=True,
        capture_output=True,
        text=True,
        env=_clean_env(),
    ).stdout.strip()
    if version_output.split()[-1:] != [expected_version]:
        raise RuntimeError("release_unavailable: cce-pipeline version does not match the run")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _uses_prepare_handoff(payload: dict[str, Any]) -> bool:
    return str(payload.get("wgs_version") or "") == "V4.2.0" and str(
        payload.get("stage") or ""
    ) in {"prepare_sampleinfo", "prepare_analysis"}


def _prepare_handoff_request(payload: dict[str, Any]) -> Path | None:
    if not _uses_prepare_handoff(payload):
        return None
    stage = str(payload["stage"])
    generation = int(payload.get("generation") or 1)
    root = _workdir(payload) / "prepare-handoff" / stage / f"generation-{generation}"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    request_path = root / "handoff-request.json"
    if request_path.is_file():
        _validate_existing_handoff_request(payload, request_path)
        return request_path
    request: dict[str, Any] = {
        "schema_version": "wgs.prepare-handoff.request.v1",
        "analysis_id": payload["analysis_id"],
        "attempt": int(payload["attempt"]),
        "execution_id": str(payload.get("execution_id") or f"{stage}-legacy"),
        "generation": generation,
        "stage": stage,
        "request_hash": str(payload.get("request_hash") or _sha256_file(_request_path(str(payload["analysis_id"]), int(payload["attempt"]), stage))),
        "release_id": payload["pipeline_release_id"],
        "artifact_root": str(root),
    }
    if stage == "prepare_sampleinfo":
        request["artifact_keys"] = {"sampleinfo": "sampleinfo.snapshot.tsv"}
    else:
        source = Path(str(payload["analysis_project_root"])) / "sampleinfo" / f"{payload['batch_no']}.sampleinfo.txt"
        if not source.is_file() or source.is_symlink():
            raise RuntimeError("prepare_analysis source sampleinfo is unavailable")
        pending_payload = root / "pending-input.tsv"
        pending_rows = _write_pending_input(payload, source, pending_payload)
        pending_manifest = root / "pending-input.manifest.json"
        _atomic_json(
            pending_manifest,
            {
                "schema_version": "wgs.pending-input.manifest.v1",
                "project_id": str(payload["project_name"]),
                "revision": generation,
                "payload": {
                    "path": str(pending_payload),
                    "sha256": _sha256_file(pending_payload),
                    "row_count": pending_rows,
                },
            },
            mode=0o600,
        )
        request.update(
            {
                "artifact_keys": {
                    "final_sampleinfo": "final-sampleinfo.snapshot.tsv",
                    "private_pending_payload": "private-pending-output.tsv",
                },
                "source_sampleinfo": {
                    "snapshot_id": f"{payload['analysis_id']}-a{payload['attempt']}-sampleinfo",
                    "sha256": _sha256_file(source),
                },
                "pending_input": {
                    "manifest_path": str(pending_manifest),
                    "manifest_sha256": _sha256_file(pending_manifest),
                    "revision": generation,
                },
            }
        )
    _atomic_json(request_path, request, mode=0o600)
    return request_path


def _validate_existing_handoff_request(
    payload: dict[str, Any], request_path: Path
) -> None:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    stage = str(payload["stage"])
    expected = {
        "schema_version": "wgs.prepare-handoff.request.v1",
        "analysis_id": payload["analysis_id"],
        "attempt": int(payload["attempt"]),
        "execution_id": str(payload.get("execution_id") or f"{stage}-legacy"),
        "generation": int(payload.get("generation") or 1),
        "stage": stage,
        "request_hash": str(payload.get("request_hash") or _sha256_file(_request_path(str(payload["analysis_id"]), int(payload["attempt"]), stage))),
        "release_id": payload["pipeline_release_id"],
        "artifact_root": str(request_path.parent),
    }
    if any(request.get(key) != value for key, value in expected.items()):
        raise RuntimeError("WGS prepare handoff request identity mismatch")
    if stage == "prepare_analysis":
        source = Path(str(payload["analysis_project_root"])) / "sampleinfo" / f"{payload['batch_no']}.sampleinfo.txt"
        source_spec = request.get("source_sampleinfo")
        if (
            not source.is_file()
            or source.is_symlink()
            or not isinstance(source_spec, dict)
            or source_spec.get("sha256") != _sha256_file(source)
        ):
            raise RuntimeError("WGS prepare handoff source sampleinfo changed")
        pending = request.get("pending_input")
        if not isinstance(pending, dict):
            raise RuntimeError("WGS prepare handoff pending input is missing")
        manifest = Path(str(pending.get("manifest_path") or "")).resolve()
        if (
            request_path.parent.resolve() not in manifest.parents
            or not manifest.is_file()
            or manifest.is_symlink()
            or pending.get("manifest_sha256") != _sha256_file(manifest)
        ):
            raise RuntimeError("WGS prepare handoff pending input changed")


def _write_pending_input(
    payload: dict[str, Any], source: Path, pending_payload: Path
) -> int:
    generation = int(payload.get("generation") or 1)
    if generation > 1:
        previous_root = pending_payload.parent.parent / f"generation-{generation - 1}"
        previous_request = previous_root / "handoff-request.json"
        if previous_request.is_file() and not previous_request.is_symlink():
            previous_payload = {**payload, "generation": generation - 1}
            _validated_prepare_receipt(previous_payload, previous_request)
            request = json.loads(previous_request.read_text(encoding="utf-8"))
            receipt = json.loads(
                (Path(str(request["artifact_root"])) / "prepare_analysis.receipt.json").read_text(
                    encoding="utf-8"
                )
            )
            descriptor = receipt["private_pending_payload"]
            previous_artifact = previous_root / str(descriptor["artifact_key"])
            pending_payload.touch(mode=0o600, exist_ok=False)
            with previous_artifact.open("rb") as source_handle, pending_payload.open("wb") as target_handle:
                shutil.copyfileobj(source_handle, target_handle, length=1024 * 1024)
            return int(descriptor.get("row_count") or 0)
    with source.open(encoding="utf-8-sig", newline="") as source_handle:
        header = next(csv.reader(source_handle, delimiter="\t"))
    pending_payload.touch(mode=0o600, exist_ok=False)
    with pending_payload.open("w", encoding="utf-8", newline="") as pending_handle:
        writer = csv.writer(pending_handle, delimiter="\t", lineterminator="\n")
        writer.writerow(
            header
            + [
                "pending_reason",
                "pending_at",
                "source_analysis_batch",
                "source_sampleinfo",
            ]
        )
    return 0


def _validated_prepare_receipt(payload: dict[str, Any], request_path: Path) -> dict[str, Any]:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    receipt_path = Path(str(request["artifact_root"])) / f"{payload['stage']}.receipt.json"
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise RuntimeError("WGS prepare handoff receipt is unavailable")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected_schema = (
        "wgs.prepare-sampleinfo.receipt.v1"
        if payload["stage"] == "prepare_sampleinfo"
        else "wgs.prepare-analysis.receipt.v1"
    )
    for key in ("analysis_id", "attempt", "execution_id", "generation", "request_hash", "release_id"):
        if receipt.get(key) != request.get(key):
            raise RuntimeError(f"WGS prepare handoff receipt {key} mismatch")
    if receipt.get("schema_version") != expected_schema:
        raise RuntimeError("WGS prepare handoff receipt schema mismatch")
    pending_payload_sha: str | None = None
    if payload["stage"] == "prepare_analysis":
        source_spec = request.get("source_sampleinfo")
        pending_spec = request.get("pending_input")
        if not isinstance(source_spec, dict) or not isinstance(pending_spec, dict):
            raise RuntimeError("WGS prepare handoff analysis inputs are missing")
        artifact_root = Path(str(request["artifact_root"])).resolve()
        pending_manifest_path = Path(str(pending_spec["manifest_path"])).resolve()
        if (
            artifact_root not in pending_manifest_path.parents
            or not pending_manifest_path.is_file()
            or pending_manifest_path.is_symlink()
            or pending_spec.get("manifest_sha256")
            != _sha256_file(pending_manifest_path)
        ):
            raise RuntimeError("WGS prepare handoff pending manifest changed")
        pending_manifest = json.loads(
            pending_manifest_path.read_text(encoding="utf-8")
        )
        pending_descriptor = pending_manifest.get("payload")
        if not isinstance(pending_descriptor, dict):
            raise RuntimeError("WGS prepare handoff pending manifest is invalid")
        pending_payload_sha = str(pending_descriptor.get("sha256") or "")
        pending_payload_path = Path(str(pending_descriptor.get("path") or "")).resolve()
        if (
            artifact_root not in pending_payload_path.parents
            or not pending_payload_path.is_file()
            or pending_payload_path.is_symlink()
            or pending_payload_sha != _sha256_file(pending_payload_path)
        ):
            raise RuntimeError("WGS prepare handoff pending payload changed")
        expected_inputs = {
            "source_sampleinfo_snapshot_id": source_spec.get("snapshot_id"),
            "source_sampleinfo_sha256": source_spec.get("sha256"),
            "pending_input_revision": pending_spec.get("revision"),
            "pending_input_sha256": pending_payload_sha,
        }
        if any(receipt.get(key) != value for key, value in expected_inputs.items()):
            raise RuntimeError("WGS prepare handoff receipt input identity mismatch")
    descriptor_names = (
        ("sampleinfo",)
        if payload["stage"] == "prepare_sampleinfo"
        else ("final_sampleinfo", "private_pending_payload")
    )
    artifact_root = Path(str(request["artifact_root"])).resolve()
    for name in descriptor_names:
        descriptor = receipt.get(name)
        if not isinstance(descriptor, dict):
            raise RuntimeError(f"WGS prepare handoff {name} descriptor is missing")
        if descriptor.get("artifact_key") != request["artifact_keys"][name]:
            raise RuntimeError(f"WGS prepare handoff {name} artifact key mismatch")
        artifact_sha = descriptor.get("sha256")
        row_count = int(descriptor.get("row_count") or 0)
        if artifact_sha is None and name == "final_sampleinfo" and row_count == 0:
            continue
        artifact = (artifact_root / str(descriptor["artifact_key"])).resolve()
        if artifact_root not in artifact.parents or not artifact.is_file() or artifact.is_symlink():
            raise RuntimeError(f"WGS prepare handoff {name} artifact is unavailable")
        if artifact_sha != _sha256_file(artifact):
            raise RuntimeError(f"WGS prepare handoff {name} SHA256 mismatch")
    safe_keys = {
        "sequencing_batch", "analysis_batch", "family_id", "sample_id", "data_id",
        "sample_type", "family_relation", "sex", "decision", "reason_code", "reason_message",
    }
    projected: dict[str, Any] = {"schema_version": expected_schema}
    expected_groups = (
        {"safe_candidates": "candidate"}
        if payload["stage"] == "prepare_sampleinfo"
        else {"selected": "selected", "pending": "pending", "excluded": "excluded"}
    )
    seen_samples: set[str] = set()
    for name, expected_decision in expected_groups.items():
        rows = receipt.get(name)
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or set(row) != safe_keys
            or row.get("decision") != expected_decision
            or not str(row.get("sample_id") or "").strip()
            for row in rows
        ):
            raise RuntimeError("WGS prepare handoff safe decision rows are invalid")
        sample_ids = [str(row["sample_id"]).strip() for row in rows]
        if len(sample_ids) != len(set(sample_ids)) or seen_samples.intersection(sample_ids):
            raise RuntimeError("WGS prepare handoff decision sample IDs are duplicated")
        seen_samples.update(sample_ids)
        projected[name] = rows
    if payload["stage"] == "prepare_sampleinfo":
        if int(receipt["sampleinfo"].get("row_count") or 0) != len(projected["safe_candidates"]):
            raise RuntimeError("WGS prepare handoff sampleinfo decision count mismatch")
    else:
        if (
            int(receipt["final_sampleinfo"].get("row_count") or 0)
            != len(projected["selected"])
            or int(receipt["private_pending_payload"].get("row_count") or 0)
            != len(projected["pending"])
        ):
            raise RuntimeError("WGS prepare handoff analysis decision count mismatch")
    return projected


def _clean_env() -> dict[str, str]:
    return {**os.environ, "PYTHONNOUSERSITE": "1"}


def _resolved_runtime_controls(profile: dict[str, Any]) -> dict[str, Any]:
    controls: dict[str, Any] = {}
    transfer = profile.get("transfer")
    if transfer is not None:
        if not isinstance(transfer, dict):
            raise RuntimeError("RESOLVED_PROFILE.yaml transfer audit is invalid")
        expected = {
            "upload_file_parallelism",
            "download_file_parallelism",
            "obsutil_parts_per_file",
        }
        if set(transfer) != expected:
            raise RuntimeError("RESOLVED_PROFILE.yaml transfer audit is incomplete")
        normalized_transfer: dict[str, int] = {}
        for name in sorted(expected):
            value = transfer[name]
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 32:
                raise RuntimeError(
                    f"RESOLVED_PROFILE.yaml transfer.{name} is invalid"
                )
            normalized_transfer[name] = value
        controls["transfer"] = normalized_transfer

    heavy_io = profile.get("heavy_io")
    if heavy_io is not None:
        if not isinstance(heavy_io, dict) or set(heavy_io) != {"limit", "mode", "unit"}:
            raise RuntimeError("RESOLVED_PROFILE.yaml heavy_io audit is invalid")
        limit = heavy_io["limit"]
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise RuntimeError("RESOLVED_PROFILE.yaml heavy_io.limit is invalid")
        if heavy_io["mode"] not in {"monitor-only", "enforce"}:
            raise RuntimeError("RESOLVED_PROFILE.yaml heavy_io.mode is invalid")
        if heavy_io["unit"] != "work_pod":
            raise RuntimeError("RESOLVED_PROFILE.yaml heavy_io.unit is invalid")
        controls["heavy_io"] = {
            "limit": limit,
            "mode": heavy_io["mode"],
            "unit": "work_pod",
        }
    return controls


def _validate_heavy_io_contract(
    payload: dict[str, Any], resolved_runtime: dict[str, Any]
) -> None:
    expected = payload.get("heavy_io_contract")
    if expected is None:
        return
    if not isinstance(expected, dict) or set(expected) != {"limit", "mode", "unit"}:
        raise RuntimeError("WGS stage contract heavy_io payload is invalid")
    if resolved_runtime.get("heavy_io") != expected:
        raise RuntimeError(
            "RESOLVED_PROFILE.yaml heavy_io does not match the WGS stage contract"
        )


def _run_prepare(payload: dict[str, Any]) -> None:
    binding_path = _binding_path(payload)
    if binding_path.is_file():
        _load_binding(payload)
        return
    validate_release_repository(payload)
    validate_prepare_config(payload)
    validate_release_runtime(payload)
    workdir = _workdir(payload)
    workdir.mkdir(parents=True, exist_ok=True)
    _release_operator_config(payload, materialize=True)
    project_root = Path(str(payload["analysis_project_root"])).resolve()
    expected_batch_root = Path(str(payload["expected_batch_root"])).resolve()
    expected = project_root / str(payload["batch_no"])
    if (
        expected_batch_root != expected
        or not project_root.is_dir()
        or not os.access(project_root, os.W_OK)
    ):
        raise RuntimeError("WGS analysis project root is unavailable or outside the approved batch path")
    subprocess.run(build_prepare_command(payload), check=True, env=_clean_env())
    _freeze_validation_execution_mode(payload, expected_batch_root)
    _write_prepare_binding(payload)


def _run_prepare_sampleinfo(payload: dict[str, Any]) -> None:
    validate_release_repository(payload)
    validate_prepare_config(payload)
    workdir = _workdir(payload)
    workdir.mkdir(parents=True, exist_ok=True)
    project_root = Path(str(payload["analysis_project_root"])).resolve()
    sampleinfo = project_root / "sampleinfo" / f"{payload['batch_no']}.sampleinfo.txt"
    handoff_request = _prepare_handoff_request(payload)
    if sampleinfo.is_file() and not sampleinfo.is_symlink():
        if handoff_request is not None:
            try:
                payload["prepare_handoff_receipt"] = _validated_prepare_receipt(payload, handoff_request)
            except RuntimeError as error:
                if str(error) != "WGS prepare handoff receipt is unavailable":
                    raise
                history = (
                    workdir
                    / "history"
                    / "prepare_sampleinfo"
                    / f"before-generation-{int(payload.get('generation') or 1)}"
                )
                history.mkdir(parents=True, exist_ok=True)
                archived = history / sampleinfo.name
                if archived.exists() or archived.is_symlink():
                    raise RuntimeError("WGS sampleinfo recovery archive already exists")
                os.replace(sampleinfo, archived)
                try:
                    subprocess.run(build_prepare_command(payload), check=True, env=_clean_env())
                except BaseException:
                    if not sampleinfo.exists():
                        os.replace(archived, sampleinfo)
                    raise
                payload["prepare_handoff_receipt"] = _validated_prepare_receipt(payload, handoff_request)
        return
    if not project_root.is_dir() or not os.access(project_root, os.W_OK):
        raise RuntimeError("WGS analysis project root is unavailable")
    subprocess.run(build_prepare_command(payload), check=True, env=_clean_env())
    if not sampleinfo.is_file() or sampleinfo.is_symlink():
        raise RuntimeError("WGS sampleinfo prepare did not publish the expected table")
    if handoff_request is not None:
        payload["prepare_handoff_receipt"] = _validated_prepare_receipt(payload, handoff_request)


def _run_prepare_analysis(payload: dict[str, Any]) -> None:
    binding_path = _binding_path(payload)
    if binding_path.is_file():
        if not _archive_missing_prepare_binding(payload, binding_path):
            _load_binding(payload)
            return
    validate_release_repository(payload)
    validate_prepare_config(payload)
    validate_release_runtime(payload)
    _release_operator_config(payload, materialize=True)
    project_root = Path(str(payload["analysis_project_root"])).resolve()
    expected_batch_root = Path(str(payload["expected_batch_root"])).resolve()
    if expected_batch_root != project_root / str(payload["batch_no"]):
        raise RuntimeError("WGS analysis batch path is outside the approved project root")
    existing_run_id = _prepared_batch_run_id(expected_batch_root)
    expected_run_id = f"{payload['analysis_id']}-a{int(payload['attempt'])}"
    if existing_run_id == expected_run_id:
        _freeze_validation_execution_mode(payload, expected_batch_root)
        _write_prepare_binding(payload)
        return
    if existing_run_id is not None:
        _retain_prior_attempt_batch(payload, expected_batch_root, existing_run_id)
    handoff_request = _prepare_handoff_request(payload)
    subprocess.run(build_prepare_command(payload), check=True, env=_clean_env())
    if handoff_request is not None:
        payload["prepare_handoff_receipt"] = _validated_prepare_receipt(payload, handoff_request)
        if not payload["prepare_handoff_receipt"].get("selected"):
            return
    _freeze_validation_execution_mode(payload, expected_batch_root)
    _write_prepare_binding(payload)


def _prepared_batch_run_id(batch_root: Path) -> str | None:
    if not batch_root.exists():
        return None
    if batch_root.is_symlink() or not batch_root.is_dir():
        raise RuntimeError("existing WGS analysis batch path is invalid")
    runtime_path = batch_root / "cce" / "BATCH_RUNTIME.yaml"
    if not runtime_path.is_file() or runtime_path.is_symlink():
        raise RuntimeError("existing WGS analysis batch has no frozen runtime identity")
    runtime = yaml.safe_load(runtime_path.read_text(encoding="utf-8"))
    identity = runtime.get("identity") if isinstance(runtime, dict) else None
    run_id = str((identity or {}).get("run_id") or "")
    if not run_id:
        raise RuntimeError("existing WGS analysis batch runtime identity is invalid")
    return run_id


def _retain_prior_attempt_batch(
    payload: dict[str, Any], batch_root: Path, existing_run_id: str
) -> Path:
    match = re.fullmatch(
        rf"{re.escape(str(payload['analysis_id']))}-a([1-9][0-9]*)",
        existing_run_id,
    )
    if match is None or int(match.group(1)) >= int(payload["attempt"]):
        raise RuntimeError("existing WGS analysis batch belongs to an unexpected run")
    history = (
        _workdir(payload)
        / "history"
        / "prepare_analysis"
        / f"prior-run-{existing_run_id}"
    )
    history.mkdir(parents=True, exist_ok=False)
    history.chmod(0o700)
    retained = history / batch_root.name
    os.replace(batch_root, retained)
    return retained


def _archive_missing_prepare_binding(payload: dict[str, Any], binding_path: Path) -> bool:
    """Archive an attempt binding only when a newer prepare generation lost its bundle."""
    generation = int(payload.get("generation") or 1)
    if generation <= 1:
        return False
    value = json.loads(binding_path.read_text(encoding="utf-8"))
    if (
        value.get("schema_version") != BINDING_SCHEMA
        or value.get("analysis_id") != payload["analysis_id"]
        or int(value.get("attempt", 0)) != int(payload["attempt"])
        or value.get("pipeline_release_id") != payload["pipeline_release_id"]
    ):
        _load_binding(payload)
        return False
    bundle = Path(str(value.get("cce_bundle") or "")).resolve()
    expected_batch_root = Path(str(payload["expected_batch_root"])).resolve()
    if expected_batch_root not in bundle.parents or bundle.is_symlink():
        _load_binding(payload)
        return False
    if bundle.is_dir():
        return False
    history = (
        _workdir(payload)
        / "history"
        / "prepare_analysis"
        / f"before-generation-{generation}"
    )
    history.mkdir(parents=True, exist_ok=True)
    os.replace(binding_path, history / "batch-binding.json")
    return True


def _write_prepare_binding(payload: dict[str, Any]) -> None:
    binding_path = _binding_path(payload)
    workdir = _workdir(payload)
    project_root = Path(str(payload["analysis_project_root"])).resolve()
    expected_batch_root = Path(str(payload["expected_batch_root"])).resolve()
    batch_root = expected_batch_root
    if not (batch_root / "cce" / "BATCH_RUNTIME.yaml").is_file():
        raise RuntimeError("WGS prepare did not create the expected frozen CCE batch")
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
    run_label = str(profile.get("run_label") or "")
    if CCE_RUN_LABEL_RE.fullmatch(run_label) is None:
        raise RuntimeError("RESOLVED_PROFILE.yaml run_label is invalid")
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
        "execution_mode": str((runtime.get("workflow") or {}).get("execution_mode") or "analysis"),
        "batch_runtime_sha256": hashlib.sha256(
            (batch_root / "cce" / "BATCH_RUNTIME.yaml").read_bytes()
        ).hexdigest(),
    }
    resolved_runtime.update(_resolved_runtime_controls(profile))
    expected_runtime = {
        key: str(payload.get(key) or "")
        for key in (
            "cce_pipeline_version",
            "profile_id",
            "profile_revision",
            "profile_sha256",
            "pipeline_build_sha256",
            "resource_manifest_sha256",
        )
        if payload.get(key) is not None
    }
    if any(resolved_runtime.get(key) != value for key, value in expected_runtime.items()):
        raise RuntimeError("resolved CCE runtime does not match the frozen WGS release")
    _validate_heavy_io_contract(payload, resolved_runtime)
    analysis = runtime.get("analysis") if isinstance(runtime.get("analysis"), dict) else {}
    runtime_paths = runtime.get("paths") if isinstance(runtime.get("paths"), dict) else {}
    run_dir = Path(str(runtime_paths.get("run_dir") or ""))
    if not run_dir.is_absolute():
        raise RuntimeError("BATCH_RUNTIME.yaml run directory is invalid")
    delivery = analysis.get("delivery") if isinstance(analysis.get("delivery"), dict) else {}
    raw_repair_groups = delivery.get("repair_groups")
    repair_groups = {
        str(name): {
            "target": str((contract or {}).get("target") or "")
            if isinstance(contract, dict)
            else ""
        }
        for name, contract in (raw_repair_groups or {}).items()
        if SAFE_COMPONENT_RE.fullmatch(str(name))
    } if isinstance(raw_repair_groups, dict) else {}
    resolved_runtime["repair_groups"] = repair_groups
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
            "control_workdir": str(workdir),
            "analysis_project_root": str(project_root),
            "expected_batch_root": str(expected_batch_root),
            "cce_bundle": str(batch_root / "cce"),
            "project": identity.get("project"),
            "batch": identity.get("batch"),
            "run_id": identity.get("run_id"),
            "run_label": run_label,
            "repair_groups": repair_groups,
            "master_job": (runtime.get("kubernetes") or {}).get("master_job"),
            "namespace": (runtime.get("kubernetes") or {}).get("namespace"),
            "rule_source_dir": str(
                run_dir
                / "evidence"
                / str(identity.get("run_id"))
                / "rule-status"
                / "raw"
            ),
            "analysis_log_source": str(
                run_dir / "evidence" / str(identity.get("run_id")) / "analysis.log"
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
    _validate_heavy_io_contract(payload, dict(value.get("resolved_runtime") or {}))
    bundle = Path(str(value["cce_bundle"])).resolve()
    expected_batch_root = Path(str(payload["expected_batch_root"])).resolve()
    if expected_batch_root not in bundle.parents or not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("frozen CCE bundle is outside the expected analysis batch")
    return value


def _binding_run_label(binding: dict[str, Any]) -> str:
    run_label = str(binding.get("run_label") or "")
    if not run_label:
        profile_path = Path(str(binding["cce_bundle"])) / "RESOLVED_PROFILE.yaml"
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        run_label = str(profile.get("run_label") or "") if isinstance(profile, dict) else ""
    if CCE_RUN_LABEL_RE.fullmatch(run_label) is None:
        raise ValueError("frozen CCE run label is invalid")
    return run_label


def _step_command(payload: dict[str, Any], stage: str, *arguments: str) -> list[str]:
    binding = _load_binding(payload)
    script = Path(str(binding["cce_bundle"])) / STEP_SCRIPTS[stage]
    if not script.is_file() or script.is_symlink():
        raise FileNotFoundError(f"frozen WGS step is missing: {script.name}")
    return ["bash", str(script), *arguments]


def build_step4_repair_command(payload: dict[str, Any]) -> list[str]:
    binding = _load_binding(payload)
    repair_groups = binding.get("repair_groups")
    if not isinstance(repair_groups, dict) or "cram" not in repair_groups:
        raise RuntimeError("frozen WGS bundle does not declare the cram repair contract")
    components = [
        str(binding.get("project") or ""),
        str(binding.get("batch") or ""),
        str(binding.get("run_id") or ""),
    ]
    if any(SAFE_COMPONENT_RE.fullmatch(value) is None for value in components):
        raise RuntimeError("frozen WGS repair identity is invalid")
    confirmation = f"REPAIR-LINKAGE:{components[0]}/{components[1]}/{components[2]}:cram"
    return _step_command(
        payload,
        "step4_repair_cram",
        "--repair-linkage-group",
        "cram",
        "--confirm",
        confirmation,
    )


def build_step7_cleanup_command(payload: dict[str, Any]) -> list[str]:
    try:
        binding = _load_binding(payload)
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as error:
        snapshot = payload.get("step7_target_snapshot")
        if not isinstance(snapshot, dict):
            raise RuntimeError(
                "frozen WGS cleanup identity is unavailable; needs recovery"
            ) from error
        expected_identity = {
            "analysis_id": str(payload.get("analysis_id") or ""),
            "attempt": int(payload.get("attempt") or 0),
            "run_id": f"{payload.get('analysis_id')}-a{int(payload.get('attempt') or 0)}",
        }
        if any(snapshot.get(key) != value for key, value in expected_identity.items()):
            raise RuntimeError(
                "frozen WGS cleanup identity does not match the request; needs recovery"
            ) from error
        target_text = str(snapshot.get("expected_batch_root") or "")
        target = Path(target_text)
        if not target.is_absolute() or ".." in target.parts:
            raise RuntimeError(
                "frozen WGS cleanup target is incomplete; needs recovery"
            ) from error
        if target.exists():
            raise RuntimeError(
                "frozen WGS cleanup target is partially present; needs recovery"
            ) from error
        _verify_step7_remote_absent(payload, snapshot)
        payload["step7_completion_mode"] = "verified_absent"
        return ["/usr/bin/true"]
    components = [
        str(binding.get("project") or ""),
        str(binding.get("batch") or ""),
        str(binding.get("run_id") or ""),
    ]
    if any(SAFE_COMPONENT_RE.fullmatch(value) is None for value in components):
        raise RuntimeError("frozen WGS cleanup identity is invalid")
    confirmation = f"DELETE-SFS:{components[0]}/{components[1]}/{components[2]}"
    compat_config = _step7_compat_operator_config(payload, binding)
    config_arguments = ["--config", str(compat_config)] if compat_config else []
    return _step_command(
        payload,
        "step7_cleanup",
        *config_arguments,
        "--confirm",
        confirmation,
    )


def _step7_compat_operator_config(
    payload: dict[str, Any], binding: dict[str, Any]
) -> Path | None:
    """Strip newer transfer-only keys for an older frozen Step7 parser."""

    bundle = Path(str(binding.get("cce_bundle") or ""))
    pointer = bundle / "CCE_OPERATOR_CONFIG_PATH"
    if not pointer.is_file() or pointer.is_symlink():
        return None
    source = Path(pointer.read_text(encoding="utf-8").strip()).expanduser().resolve()
    configured = Path(CCE_OPERATOR_CONFIG).expanduser().resolve()
    if source != configured or not source.is_file() or source.is_symlink():
        raise RuntimeError("frozen Step7 operator config path is not approved")
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise RuntimeError("Step7 operator config is invalid")
    obs = config.get("obs")
    if not isinstance(obs, dict) or not STEP7_COMPAT_OBS_FIELDS.intersection(obs):
        return None
    for key in STEP7_COMPAT_OBS_FIELDS:
        obs.pop(key, None)
    compat_path = _workdir(payload) / "step7-operator-config.compat.yaml"
    _atomic_yaml(compat_path, config)
    compat_path.chmod(0o600)
    return compat_path


def _verify_step7_remote_absent(
    payload: dict[str, Any], snapshot: dict[str, Any]
) -> None:
    config_path = Path(CCE_OPERATOR_CONFIG).expanduser().resolve()
    if not config_path.is_file() or config_path.is_symlink():
        raise RuntimeError("CCE cleanup identity cannot be verified; needs recovery")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    kubernetes = config.get("kubernetes") if isinstance(config, dict) else None
    if not isinstance(kubernetes, dict):
        raise RuntimeError("CCE cleanup identity cannot be verified; needs recovery")
    namespace = str(kubernetes.get("namespace") or "")
    frozen_namespace = str(snapshot.get("namespace") or "")
    if frozen_namespace and frozen_namespace != namespace:
        raise RuntimeError("CCE cleanup namespace mismatch; needs recovery")
    kubectl = Path(str(kubernetes.get("kubectl_bin") or ""))
    kubeconfig = Path(str(kubernetes.get("kubeconfig") or "")).expanduser()
    if (
        not namespace
        or not kubectl.is_absolute()
        or not kubectl.is_file()
        or not os.access(kubectl, os.X_OK)
        or not kubeconfig.is_absolute()
        or not kubeconfig.is_file()
    ):
        raise RuntimeError("CCE cleanup identity cannot be verified; needs recovery")
    project = str(payload.get("project_name") or snapshot.get("project") or "")
    batch = str(payload.get("batch_no") or snapshot.get("batch") or "")
    if any(SAFE_COMPONENT_RE.fullmatch(value) is None for value in (project, batch)):
        raise RuntimeError("CCE cleanup identity is invalid; needs recovery")
    digest = hashlib.sha256(f"{project}/{batch}".encode("utf-8")).hexdigest()[:20]
    job_names = [
        f"cce-master-{digest}",
        f"cce-cleanup-{digest}",
        f"cce-reset-{digest}",
        f"cce-repair-{digest}",
    ]
    base = [str(kubectl), "--kubeconfig", str(kubeconfig), "-n", namespace]
    remnants: list[str] = []
    for kind, name in [("job", item) for item in job_names] + [
        ("configmap", f"cce-batch-lock-{digest}")
    ]:
        completed = subprocess.run(
            [*base, "get", kind, name, "--ignore-not-found", "-o", "name"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError("CCE cleanup state cannot be verified; needs recovery")
        if completed.stdout.strip():
            remnants.append(completed.stdout.strip())
    for job_name in job_names:
        completed = subprocess.run(
            [
                *base,
                "get",
                "pods",
                "-l",
                f"job-name={job_name}",
                "--ignore-not-found",
                "-o",
                "name",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError("CCE cleanup state cannot be verified; needs recovery")
        if completed.stdout.strip():
            remnants.append(completed.stdout.strip())
    if remnants:
        raise RuntimeError(
            f"CCE cleanup remnants still exist ({', '.join(remnants)}); needs recovery"
        )


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
    execution_mode = value.get("execution_mode")
    if execution_mode is not None:
        if execution_mode not in {"analysis", "dry_run"}:
            raise ValueError("Step3 execution_mode is invalid")
        result["execution_mode"] = execution_mode
    for key in ("master_uid", "master_resource_version"):
        item = value.get(key)
        if item is not None:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"Step3 {key} is invalid")
            result[key] = item
    if result["completed"] < 0 or result["total"] < 0:
        raise ValueError("Step3 progress cannot be negative")
    return result


def parse_step3_status_output(value: str) -> dict[str, Any]:
    for line in reversed(value.splitlines()):
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return validate_step3_status(payload)
    raise ValueError("Step3 output does not contain a valid JSON status record")


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
        "--analysis-log-source",
        str(binding["analysis_log_source"]),
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
        if terminal:
            output = (
                CCE_EVIDENCE_ROOT
                / str(payload["analysis_id"])
                / f"attempt-{int(payload['attempt'])}"
            )
            rule_paths = list(
                (output / "rule-status" / "raw").glob("*.jsonl")
            )
            if not any(
                path.is_file() and path.stat().st_size > 0 for path in rule_paths
            ):
                return "Rule event JSONL was not produced"
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
            message = (completed.stderr or completed.stdout)[-2000:]
            if "kubectl query failed" in message:
                if time.monotonic() - started > MONITOR_TIMEOUT_SECONDS:
                    raise TimeoutError(
                        "Step3 status query remained unavailable until monitor timeout"
                    )
                time.sleep(MONITOR_INTERVAL_SECONDS)
                continue
            raise RuntimeError(message)
        value = parse_step3_status_output(completed.stdout)
        terminal = value["master_state"] in {"SUCCEEDED", "FAILED"}
        if terminal:
            monitoring_error = _sync_rule_evidence(payload, binding, terminal=True)
        _write_status(
            payload,
            {
                "SUCCEEDED": "success",
                "FAILED": "failed",
            }.get(value["master_state"], "running"),
            value["message"],
            master=value,
            master_job=binding.get("master_job"),
            namespace=binding.get("namespace"),
            run_label=_binding_run_label(binding),
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
    master_wait_started: float | None = None
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
        retry_master = (
            STEP4_MASTER_NOT_SUCCESSFUL in message
            and _step3_success_matches_binding(payload)
        )
        if retry_master:
            if master_wait_started is None:
                master_wait_started = time.monotonic()
            if (
                time.monotonic() - master_wait_started
                > STEP4_MASTER_COMPLETION_GRACE_SECONDS
            ):
                raise TimeoutError(
                    "Step4 timed out waiting for the bound Master Job to become Complete"
                )
        elif retry_text not in message:
            raise RuntimeError(message)
        _write_status(payload, "running", message)
        if time.monotonic() - started > MONITOR_TIMEOUT_SECONDS:
            raise TimeoutError("Step4 publish monitoring timed out")
        time.sleep(MONITOR_INTERVAL_SECONDS)


def _transfer_progress_root(payload: dict[str, Any]) -> Path:
    root = TRANSFER_SPOOL_ROOT.resolve()
    path = (
        root
        / str(payload["analysis_id"])
        / f"attempt-{int(payload['attempt'])}"
        / str(payload["stage"])
    ).resolve()
    if root not in path.parents:
        raise ValueError("transfer progress path escapes spool root")
    return path


def _transfer_plan_path(payload: dict[str, Any]) -> Path:
    return _transfer_progress_root(payload) / "transfer-plan.json"


def _create_transfer_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Freeze a transfer denominator from a stable local file contract."""
    path = _transfer_plan_path(payload)
    if path.is_file() and not path.is_symlink():
        value = _read_json(path)
        if (
            value.get("schema_version") == "wgs-runtime.transfer-plan.v1"
            and value.get("analysis_id") == payload["analysis_id"]
            and int(value.get("attempt", 0)) == int(payload["attempt"])
            and value.get("stage") == payload["stage"]
        ):
            return value
        raise RuntimeError("existing transfer plan identity mismatch")
    binding = _load_binding(payload)
    batch_root = Path(str(binding["batch_root"]))
    entries: list[dict[str, Any]] = []
    if payload["stage"] == "step1_upload":
        raw_root = batch_root / "raw"
        if not raw_root.is_dir() or raw_root.is_symlink():
            raise RuntimeError("Step1 raw FASTQ directory is unavailable")
        for item in sorted(raw_root.glob("*.fq.gz"), key=lambda value: value.name):
            if not (item.is_file() or item.is_symlink()):
                continue
            entries.append({"relative_path": f"raw/{item.name}", "size_bytes": item.stat().st_size})
    elif payload["stage"] == "step5_download":
        manifest = batch_root / "cce" / "cloud_delivery" / "payload-manifest.tsv"
        if not manifest.is_file() or manifest.is_symlink():
            raise RuntimeError("Step5 payload manifest is unavailable")
        with manifest.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                relative = str(row.get("relative_path") or "").strip()
                size = int(row.get("size_bytes") or 0)
                if not relative or size < 0:
                    raise RuntimeError("Step5 payload manifest contains an invalid entry")
                entries.append({"relative_path": relative, "size_bytes": size})
    else:
        raise RuntimeError("transfer plan requested for a non-transfer stage")
    if not entries:
        raise RuntimeError("transfer plan contains no files")
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    value = {
        "schema_version": "wgs-runtime.transfer-plan.v1",
        "analysis_id": payload["analysis_id"],
        "attempt": int(payload["attempt"]),
        "stage": payload["stage"],
        "files_total": len(entries),
        "bytes_total": sum(int(entry["size_bytes"]) for entry in entries),
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "entries": entries,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_json(path, value)
    return value


def _try_create_step5_transfer_plan(
    payload: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    """Read the manifest fetched by Step5 without treating NFS delay as failure."""
    try:
        return _create_transfer_plan(payload), None
    except (OSError, RuntimeError, ValueError) as error:
        if str(error) == "existing transfer plan identity mismatch":
            raise
        return None, str(error)


def _step5_completed_plan_totals(
    payload: dict[str, Any], plan: dict[str, Any]
) -> tuple[int, int]:
    completed = _step5_completed_plan_keys(payload, plan)
    bytes_done = sum(
        int(entry.get("size_bytes") or 0)
        for entry in plan.get("entries") or []
        if hashlib.sha256(
            str(entry.get("relative_path") or "").encode("utf-8")
        ).hexdigest()
        in completed
    )
    return len(completed), bytes_done


def _step5_completed_plan_keys(
    payload: dict[str, Any], plan: dict[str, Any]
) -> set[str]:
    binding = _load_binding(payload)
    delivery_root = (
        Path(str(binding["batch_root"])) / "cce" / "cloud_delivery"
    ).resolve()
    completed: set[str] = set()
    for entry in plan.get("entries") or []:
        relative = Path(str(entry.get("relative_path") or ""))
        if relative.is_absolute() or ".." in relative.parts:
            continue
        target = delivery_root / relative
        try:
            resolved = target.resolve()
            if delivery_root not in resolved.parents or target.is_symlink():
                continue
            expected_size = int(entry.get("size_bytes") or 0)
            if target.is_file() and target.stat().st_size == expected_size:
                completed.add(
                    hashlib.sha256(
                        str(entry.get("relative_path") or "").encode("utf-8")
                    ).hexdigest()
                )
        except (OSError, TypeError, ValueError):
            continue
    return completed


def _obsutil_file_progress(
    payload: dict[str, Any], plan: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any] | None:
    keyed_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        file_key = str(row.get("file_key") or "")
        if re.fullmatch(r"[0-9a-f]{64}", file_key) is None:
            continue
        previous = keyed_rows.get(file_key)
        if previous is None or str(row.get("heartbeat_at") or "") >= str(
            previous.get("heartbeat_at") or ""
        ):
            keyed_rows[file_key] = row
    if not keyed_rows:
        return None
    plan_keys = {
        hashlib.sha256(
            str(entry.get("relative_path") or "").encode("utf-8")
        ).hexdigest()
        for entry in plan.get("entries") or []
    }
    completed_step5 = (
        _step5_completed_plan_keys(payload, plan)
        if payload["stage"] == "step5_download"
        else set()
    )
    files: list[dict[str, Any]] = []
    monitoring_degraded = bool(set(keyed_rows) - plan_keys)
    for entry in plan.get("entries") or []:
        relative = str(entry.get("relative_path") or "")
        total = max(0, int(entry.get("size_bytes") or 0))
        file_key = hashlib.sha256(relative.encode("utf-8")).hexdigest()
        row = keyed_rows.get(file_key)
        status = "accepted"
        done = 0
        speed = 0
        checksum_status = "pending"
        started_at = None
        ended_at = None
        error_message = None
        if file_key in completed_step5:
            status = "success"
            done = total
            checksum_status = "verified"
        elif row is not None:
            raw_status = str(row.get("state") or "running").lower()
            status = {
                "complete": "success",
                "completed": "success",
                "succeeded": "success",
                "queued": "accepted",
                "pending": "accepted",
            }.get(raw_status, raw_status)
            if status not in {"accepted", "running", "success", "failed", "canceled"}:
                status = "running"
                monitoring_degraded = True
            done = min(max(0, int(row.get("bytes_done") or 0)), total)
            if status == "success":
                done = total
            speed = (
                max(0, int(row.get("speed_bytes_per_second") or 0))
                if status == "running"
                else 0
            )
            checksum_status = str(row.get("checksum_status") or "pending")
            started_at = str(row.get("started_at") or "") or None
            ended_at = str(row.get("ended_at") or "") or None
            error_message = str(row.get("error_summary") or "")[-2000:] or None
            monitoring_degraded = (
                monitoring_degraded or row.get("monitoring_health") == "degraded"
            )
        files.append(
            {
                "file_key": file_key,
                "display_name": Path(relative).name,
                "bytes_total": total,
                "bytes_done": done,
                "speed_bps": speed,
                "status": status,
                "checksum_status": checksum_status,
                "started_at": started_at,
                "ended_at": ended_at,
                "error_message": error_message,
            }
        )
    states = {str(item["status"]) for item in files}
    total = sum(int(item["bytes_total"]) for item in files)
    done = sum(int(item["bytes_done"]) for item in files)
    files_done = sum(item["status"] == "success" for item in files)
    speed = sum(int(item["speed_bps"]) for item in files if item["status"] == "running")
    if "running" in states:
        transfer_state = "running"
    elif "failed" in states:
        transfer_state = "failed"
    elif files and files_done == len(files):
        transfer_state = "success"
    else:
        transfer_state = "running"
    active = next((item for item in files if item["status"] == "running"), None)
    heartbeats = [
        str(row.get("heartbeat_at") or "")
        for key, row in keyed_rows.items()
        if key in plan_keys
    ]
    return {
        "schema_version": "wgs-runtime.transfer-progress.v2",
        "transfer_id": f"{payload['analysis_id']}-a{int(payload['attempt'])}-{'input' if payload['stage'] == 'step1_upload' else 'result'}",
        "analysis_id": payload["analysis_id"],
        "attempt": int(payload["attempt"]),
        "stage": payload["stage"],
        "direction": "upload" if payload["stage"] == "step1_upload" else "download",
        "state": transfer_state,
        "bytes_total": total,
        "bytes_done": done,
        "files_total": len(files),
        "files_done": files_done,
        "current_file": active["display_name"] if active else None,
        "speed_bytes_per_second": speed,
        "eta_seconds": (
            max(0, int((total - done) / speed))
            if total and speed and done < total
            else 0 if total and done >= total else None
        ),
        "heartbeat_at": max(heartbeats) if heartbeats else datetime.now(timezone.utc).isoformat(),
        "monitoring_health": "degraded" if monitoring_degraded else "healthy",
        "source": "obsutil-checkpoint",
        "checkpoint_ref": "obsutil-multipart",
        "plan_path": "transfer-progress/%s/transfer-plan.json" % payload["stage"],
        "manifest_sha256": plan.get("manifest_sha256"),
        "files": files,
    }


def _aggregate_transfer_progress(
    payload: dict[str, Any], plan: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    rows = []
    for path in _transfer_progress_root(payload).glob("*.json"):
        value = _read_json(path)
        if (
            value.get("schema_version") == "wgs-runtime.transfer-progress.v1"
            and value.get("analysis_id") == payload["analysis_id"]
            and int(value.get("attempt", 0)) == int(payload["attempt"])
            and value.get("stage") == payload["stage"]
        ):
            rows.append(value)
    if plan:
        file_progress = _obsutil_file_progress(payload, plan, rows)
        if file_progress is not None:
            return file_progress
    sdk_path = _transfer_progress_root(payload) / "progress.json"
    if sdk_path.is_file():
        sdk = _read_json(sdk_path)
        if (
            sdk.get("schema_version") == "wgs-runtime.transfer-progress.v2"
            and sdk.get("analysis_id") == payload["analysis_id"]
            and int(sdk.get("attempt", 0)) == int(payload["attempt"])
            and sdk.get("stage") == payload["stage"]
        ):
            total = int(plan["bytes_total"]) if plan else int(sdk.get("bytes_total") or 0)
            files_total = int(plan["files_total"]) if plan else int(sdk.get("files_total") or 0)
            if plan and (
                int(sdk.get("bytes_total") or 0) != total
                or int(sdk.get("files_total") or 0) != files_total
            ):
                raise RuntimeError("OBS SDK callback totals differ from the frozen transfer plan")
            done = min(max(0, int(sdk.get("bytes_done") or 0)), total)
            files_done = min(max(0, int(sdk.get("files_done") or 0)), files_total)
            speed = max(0, int(sdk.get("speed_bytes_per_second") or 0))
            return {
                **sdk,
                "bytes_total": total,
                "bytes_done": done,
                "files_total": files_total,
                "files_done": files_done,
                "eta_seconds": (
                    max(0, int((total - done) / speed))
                    if total and speed and done < total
                    else 0 if total and done >= total else None
                ),
                "monitoring_health": "healthy",
                "source": "obs-sdk-callback",
                "plan_path": (
                    "transfer-progress/%s/transfer-plan.json" % payload["stage"]
                    if plan
                    else None
                ),
                "manifest_sha256": plan.get("manifest_sha256") if plan else None,
            }
    if not rows:
        return None
    streamed_total = sum(max(0, int(row.get("bytes_total") or 0)) for row in rows)
    done = sum(max(0, int(row.get("bytes_done") or 0)) for row in rows)
    speed = sum(
        max(0, int(row.get("speed_bytes_per_second") or 0))
        for row in rows
        if row.get("state") == "running"
    )
    streamed_files_total = sum(max(0, int(row.get("files_total") or 0)) for row in rows)
    files_done = sum(max(0, int(row.get("files_done") or 0)) for row in rows)
    states = {str(row.get("state") or "") for row in rows}
    total = int(plan["bytes_total"]) if plan else streamed_total
    files_total = int(plan["files_total"]) if plan else streamed_files_total
    if plan and payload["stage"] == "step5_download":
        completed_files, completed_bytes = _step5_completed_plan_totals(payload, plan)
        done = max(done, completed_bytes)
        files_done = completed_files
    complete = bool(total and done >= total and files_done >= files_total)
    if "running" in states:
        transfer_state = "running"
    elif "failed" in states:
        transfer_state = "failed"
    elif complete:
        transfer_state = "success"
    else:
        transfer_state = "running"
    return {
        "schema_version": "wgs-runtime.transfer-progress.v1",
        "transfer_id": f"{payload['analysis_id']}-a{int(payload['attempt'])}-{'input' if payload['stage'] == 'step1_upload' else 'result'}",
        "analysis_id": payload["analysis_id"],
        "attempt": payload["attempt"],
        "stage": payload["stage"],
        "direction": "upload" if payload["stage"] == "step1_upload" else "download",
        "state": transfer_state,
        "bytes_total": total,
        "bytes_done": min(done, total) if total else done,
        "files_total": files_total,
        "files_done": min(files_done, files_total) if files_total else files_done,
        "current_file": None,
        "speed_bytes_per_second": speed,
        "eta_seconds": max(0, int((total - done) / speed)) if total and speed else None,
        "heartbeat_at": max(str(row.get("heartbeat_at") or "") for row in rows),
        "monitoring_health": "degraded" if any(row.get("monitoring_health") == "degraded" for row in rows) else "healthy",
        "source": "frozen-transfer-plan" if plan else "legacy-estimate",
        "plan_path": "transfer-progress/%s/transfer-plan.json" % payload["stage"] if plan else None,
        "manifest_sha256": plan.get("manifest_sha256") if plan else None,
    }


def _run_transfer_stage(payload: dict[str, Any]) -> None:
    root = _transfer_progress_root(payload)
    root.mkdir(parents=True, exist_ok=True)
    stage = str(payload["stage"])
    plan: dict[str, Any] | None
    plan_error: str | None = None
    if stage == "step1_upload" or _transfer_plan_path(payload).exists():
        plan = _create_transfer_plan(payload)
    else:
        # Step5_download_verify.sh fetches READY and payload-manifest.tsv from OBS
        # before downloading payload files. Starting the script is therefore the
        # producer side of the manifest contract; requiring the local manifest
        # here would form a circular prerequisite.
        plan = None
    environment = {
        **_clean_env(),
        "WGS_TRANSFER_PROGRESS_ROOT": str(root),
        "WGS_TRANSFER_ANALYSIS_ID": str(payload["analysis_id"]),
        "WGS_TRANSFER_ATTEMPT": str(payload["attempt"]),
        "WGS_TRANSFER_STAGE": stage,
        "WGS_TRANSFER_DIRECTION": "upload" if stage == "step1_upload" else "download",
        "WGS_TRANSFER_PLAN_PATH": str(_transfer_plan_path(payload)),
        "WGS_ORCHESTRATION_CONTRACT_VERSION": str(payload.get("orchestration_contract_version") or 1),
        "WGS_STAGE_EXECUTION_ID": str(payload.get("execution_id") or ""),
        "WGS_STAGE_GENERATION": str(payload.get("generation") or ""),
        "WGS_STAGE_REQUEST_HASH": str(payload.get("request_hash") or ""),
    }
    process = subprocess.Popen(_step_command(payload, stage), env=environment)
    while process.poll() is None:
        if plan is None:
            plan, plan_error = _try_create_step5_transfer_plan(payload)
            if plan is None:
                _write_status(
                    payload,
                    "running",
                    "Waiting for Step5 payload manifest from OBS",
                    monitoring_health="degraded" if plan_error and "unavailable" not in plan_error else "healthy",
                )
        if plan is not None:
            progress = _aggregate_transfer_progress(payload, plan)
            if progress is not None:
                _write_status(payload, "running", transfer=progress, monitoring_health=progress["monitoring_health"])
        time.sleep(MONITOR_INTERVAL_SECONDS)
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, process.args)
    if plan is None:
        deadline = time.monotonic() + STEP5_TRANSFER_PLAN_GRACE_SECONDS
        while plan is None:
            plan, plan_error = _try_create_step5_transfer_plan(payload)
            if plan is not None or time.monotonic() >= deadline:
                break
            time.sleep(MONITOR_INTERVAL_SECONDS)
    if plan is None:
        detail = f": {plan_error}" if plan_error else ""
        raise RuntimeError(
            "Step5 completed without a payload manifest; transfer totals cannot be verified"
            f"{detail}"
        )
    progress = _aggregate_transfer_progress(payload, plan)
    if progress is not None:
        _write_status(payload, "running", transfer=progress, monitoring_health=progress["monitoring_health"])


def _step3_success_matches_binding(payload: dict[str, Any]) -> bool:
    step3_path = _request_path(
        str(payload["analysis_id"]), int(payload["attempt"]), "step3_monitor"
    ).with_suffix(".status.json")
    step3 = _read_json(step3_path)
    try:
        binding = _load_binding(payload)
    except (OSError, RuntimeError, ValueError):
        return False
    return (
        step3.get("schema_version") == STAGE_STATUS_SCHEMA
        and step3.get("analysis_id") == payload["analysis_id"]
        and int(step3.get("attempt", 0)) == int(payload["attempt"])
        and step3.get("stage") == "step3_monitor"
        and step3.get("status") == "success"
        and bool(step3.get("master_job"))
        and step3.get("master_job") == binding.get("master_job")
    )


def run_stage(payload: dict[str, Any]) -> None:
    if not _truthy("WGS_EXECUTION_ENABLED") or not _truthy(
        "WGS_RUNTIME_ADAPTER_ENABLED"
    ):
        raise RuntimeError("WGS execution gate is disabled")
    stage = str(payload["stage"])
    if stage == "prepare":
        _run_prepare(payload)
    elif stage == "prepare_sampleinfo":
        _run_prepare_sampleinfo(payload)
    elif stage == "prepare_analysis":
        _run_prepare_analysis(payload)
    elif stage == "step3_monitor":
        _monitor_step3(payload)
    elif stage == "step4_publish":
        _wait_step4(payload)
    elif stage == "step4_repair_cram":
        subprocess.run(build_step4_repair_command(payload), check=True)
    elif stage == "step7_cleanup":
        subprocess.run(build_step7_cleanup_command(payload), check=True)
    elif stage in {"step1_upload", "step5_download"}:
        _run_transfer_stage(payload)
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


def _archive_failed_stage_generation(payload: dict[str, Any]) -> int:
    request_path = _request_path(
        str(payload["analysis_id"]), int(payload["attempt"]), str(payload["stage"])
    )
    history_root = request_path.parent / "history" / str(payload["stage"])
    history_root.mkdir(parents=True, exist_ok=True)
    retry_no = 1
    while (history_root / f"retry-{retry_no}").exists() or (
        history_root / f".retry-{retry_no}.partial"
    ).exists():
        retry_no += 1
    partial = history_root / f".retry-{retry_no}.partial"
    partial.mkdir(mode=0o750)
    for source, destination_name in (
        (request_path.with_suffix(".status.json"), "status.json"),
        (request_path.with_suffix(".worker.json"), "worker.json"),
        (request_path.with_suffix(".worker.log"), "worker.log"),
    ):
        if source.exists():
            os.replace(source, partial / destination_name)
    final = history_root / f"retry-{retry_no}"
    os.replace(partial, final)
    directory_descriptor = os.open(history_root, os.O_RDONLY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)
    return retry_no


def _archive_contract_generation(
    payload: dict[str, Any], generation: int
) -> None:
    request_path = _request_path(
        str(payload["analysis_id"]), int(payload["attempt"]), str(payload["stage"])
    )
    history_root = request_path.parent / "history" / str(payload["stage"])
    history_root.mkdir(parents=True, exist_ok=True)
    final = history_root / f"generation-{generation}"
    partial = history_root / f".generation-{generation}.partial"
    if final.exists() or partial.exists():
        raise RuntimeError("previous contract generation was already archived")
    partial.mkdir(mode=0o750)
    for source, destination_name in (
        (request_path.with_suffix(".status.json"), "status.json"),
        (request_path.with_suffix(".worker.json"), "worker.json"),
        (request_path.with_suffix(".worker.log"), "worker.log"),
    ):
        if source.exists():
            os.replace(source, partial / destination_name)
    os.replace(partial, final)
    directory_descriptor = os.open(history_root, os.O_RDONLY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)


def _prepare_contract_generation(
    payload: dict[str, Any], *, request_sha: str
) -> int | None:
    if int(payload.get("orchestration_contract_version") or 1) != 2:
        return None
    current_generation = int(payload["generation"])
    current_execution = str(payload["execution_id"])
    current_request_hash = str(payload["request_hash"])
    status = _read_json(_sidecar_path(payload, ".status.json"))
    worker = _read_json(_sidecar_path(payload, ".worker.json"))
    generations: set[int] = set()
    for label, value in (("status", status), ("worker", worker)):
        if not value:
            continue
        if int(value.get("orchestration_contract_version") or 1) != 2:
            raise RuntimeError(f"{label} sidecar lacks contract v2 identity")
        try:
            generation = int(value["generation"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(f"{label} sidecar has invalid generation") from error
        if generation > current_generation:
            raise RuntimeError(f"{label} sidecar belongs to a future generation")
        if generation == current_generation:
            if (
                value.get("execution_id") != current_execution
                or value.get("request_hash") != current_request_hash
            ):
                raise RuntimeError(f"{label} sidecar execution identity mismatch")
            if label == "worker" and value.get("request_sha256") != request_sha:
                raise RuntimeError("registered request changed after worker launch")
        generations.add(generation)
    old_generations = {value for value in generations if value < current_generation}
    if not old_generations:
        return None
    if len(old_generations) != 1 or current_generation in generations:
        raise RuntimeError("runtime sidecars contain mixed contract generations")
    if worker and _process_matches(worker):
        raise RuntimeError("previous generation worker is still active")
    previous_generation = old_generations.pop()
    _archive_contract_generation(payload, previous_generation)
    return previous_generation


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
        archived_generation = _prepare_contract_generation(
            payload, request_sha=request_sha
        )
        previous = _read_json(state_path)
        status = _read_json(_sidecar_path(payload, ".status.json"))
        retry_no = 0
        contract_v1_failed_retry = (
            int(payload.get("orchestration_contract_version") or 1) != 2
            and status.get("status") == "failed"
            and payload["stage"]
            in {"step3_monitor", "step4_publish", "step5_download", "step7_cleanup"}
        )
        if previous and previous.get("request_sha256") != request_sha:
            if contract_v1_failed_retry and not _process_matches(previous):
                retry_no = _archive_failed_stage_generation(payload)
                previous = _read_json(state_path)
                status = _read_json(_sidecar_path(payload, ".status.json"))
            else:
                raise RuntimeError("registered request changed after worker launch")
        if status.get("status") in {"success", "complete", "succeeded"}:
            return {
                "status": "complete",
                "pid": previous.get("pid") if previous else None,
            }
        if (
            int(payload.get("orchestration_contract_version") or 1) == 2
            and status.get("status") in {"failed", "canceled"}
        ):
            raise RuntimeError(
                "terminal contract generation requires a new registered generation"
            )
        if previous and _process_matches(previous):
            return {"status": "running", "pid": previous["pid"]}
        if archived_generation is not None:
            retry_no = int(payload["generation"]) - 1
        if status.get("status") == "failed" and int(
            payload.get("orchestration_contract_version") or 1
        ) != 2:
            if payload["stage"] not in {
                "step3_monitor",
                "step4_publish",
                "step5_download",
                "step7_cleanup",
            }:
                raise RuntimeError(
                    "failed runtime stages cannot be restarted by the restricted runner"
                )
            retry_no = _archive_failed_stage_generation(payload)
        command = build_async_worker_command(
            analysis_id=str(payload["analysis_id"]),
            attempt=int(payload["attempt"]),
            stage=str(payload["stage"]),
            lock_path=worker_lock,
        )
        with log_path.open("ab", buffering=0) as log_handle:
            _write_status(payload, "accepted", retry_no=retry_no)
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
            "retry_no": retry_no,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        if int(payload.get("orchestration_contract_version") or 1) == 2:
            state.update(
                {
                    "orchestration_contract_version": 2,
                    "execution_id": payload["execution_id"],
                    "generation": payload["generation"],
                    "request_hash": payload["request_hash"],
                }
            )
        _atomic_json(state_path, state)
        result = {"status": "accepted", "pid": process.pid, "retry_no": retry_no}
        if int(payload.get("orchestration_contract_version") or 1) == 2:
            result["generation"] = int(payload["generation"])
            result["execution_id"] = str(payload["execution_id"])
        return result


def _run_worker(payload: dict[str, Any]) -> int:
    current_status = _read_json(_sidecar_path(payload, ".status.json"))
    if (
        int(payload.get("orchestration_contract_version") or 1) == 2
        and current_status.get("execution_id") == payload.get("execution_id")
        and current_status.get("status") in {"success", "failed", "canceled"}
    ):
        raise RuntimeError(
            "terminal contract generation requires a new registered generation"
        )
    retry_no = int(current_status.get("retry_no", 0))
    if payload["stage"] != "step3_monitor":
        _write_status(payload, "running", retry_no=retry_no)
    try:
        run_stage(payload)
    except Exception as error:
        _write_status(payload, "failed", str(error), retry_no=retry_no)
        raise
    success_details = {"retry_no": retry_no}
    if payload.get("prepare_handoff_receipt"):
        success_details["prepare_handoff_receipt"] = payload["prepare_handoff_receipt"]
    if payload.get("step7_completion_mode"):
        success_details["completion_mode"] = payload["step7_completion_mode"]
    _write_status(payload, "success", **success_details)
    return 0


def _run_synchronous_stage(payload: dict[str, Any]) -> int:
    request_path = _request_path(
        str(payload["analysis_id"]), int(payload["attempt"]), str(payload["stage"])
    )
    request_sha = hashlib.sha256(request_path.read_bytes()).hexdigest()
    lock_path = _sidecar_path(payload, ".worker.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(
                lock_handle.fileno(), fcntl.LOCK_EX | getattr(fcntl, "LOCK_NB", 4)
            )
        except BlockingIOError as error:
            raise RuntimeError("stage worker is already active") from error
        _prepare_contract_generation(payload, request_sha=request_sha)
        return _run_worker(payload)


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
    return _run_synchronous_stage(payload)


if __name__ == "__main__":
    raise SystemExit(main())
