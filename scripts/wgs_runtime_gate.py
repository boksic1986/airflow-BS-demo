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
WGS_PREPARE_CONFIG = str(WGS_REPO_ROOT / "prepare" / "config.yaml")
CCE_OPERATOR_CONFIG = os.getenv(
    "CCE_OPERATOR_CONFIG", "/home/hanjj/.config/wgs/cce.yaml"
)
WGS_GIT_MNT_PREFIX = os.getenv("WGS_GIT_MNT_PREFIX", "/mnt/biodevrwbi")
WGS_GIT_NODE_PREFIX = os.getenv("WGS_GIT_NODE_PREFIX", "/bi/biodevrwbi")
MONITOR_INTERVAL_SECONDS = int(os.getenv("WGS_MONITOR_INTERVAL_SECONDS", "5"))
MONITOR_TIMEOUT_SECONDS = int(os.getenv("WGS_MONITOR_TIMEOUT_SECONDS", "432000"))
STEP4_MASTER_COMPLETION_GRACE_SECONDS = int(
    os.getenv("WGS_STEP4_MASTER_COMPLETION_GRACE_SECONDS", "600")
)
STEP5_TRANSFER_PLAN_GRACE_SECONDS = int(
    os.getenv("WGS_STEP5_TRANSFER_PLAN_GRACE_SECONDS", "60")
)
STEP4_MASTER_NOT_SUCCESSFUL = "Step4 requires a successful Master Job"
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


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
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


def validate_release_repository(payload: dict[str, Any]) -> Path:
    repo = WGS_REPO_ROOT.resolve()
    prepare = repo / "prepare" / "prepare_wgs_batch.py"
    if not repo.is_dir() or repo.is_symlink() or not prepare.is_file() or prepare.is_symlink():
        raise RuntimeError("release_unavailable: fixed WGS repository is unavailable")
    git = _git_repository_command(repo)
    revision = subprocess.run(
        [*git, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != str(payload.get("wgs_source_commit") or ""):
        raise RuntimeError(
            "release_unavailable: fixed WGS repository commit does not match the run"
        )
    status = subprocess.run(
        [*git, "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    def is_documentation_change(line: str) -> bool:
        path = line[3:].strip()
        return path == "README.md" or path.startswith("docs/")

    unsafe = [line for line in status if not is_documentation_change(line)]
    if unsafe:
        raise RuntimeError(
            "release_unavailable: fixed WGS repository contains runtime changes"
        )
    return repo


def _git_repository_command(repo: Path) -> list[str]:
    marker = repo / ".git"
    if marker.is_dir():
        return ["git", "-C", str(repo)]
    if not marker.is_file() or marker.is_symlink():
        raise RuntimeError("release_unavailable: fixed WGS Git metadata is unavailable")
    line = marker.read_text(encoding="utf-8").strip()
    if not line.startswith("gitdir: "):
        raise RuntimeError("release_unavailable: fixed WGS Git metadata is invalid")
    gitdir = Path(line.removeprefix("gitdir: "))
    if not gitdir.is_dir():
        source_prefix = Path(WGS_GIT_MNT_PREFIX)
        target_prefix = Path(WGS_GIT_NODE_PREFIX)
        try:
            gitdir = target_prefix / gitdir.relative_to(source_prefix)
        except ValueError as error:
            raise RuntimeError(
                "release_unavailable: WGS worktree metadata is outside the approved mapping"
            ) from error
    if not gitdir.is_dir():
        raise RuntimeError("release_unavailable: mapped WGS worktree metadata is unavailable")
    return ["git", f"--git-dir={gitdir}", f"--work-tree={repo}"]


def _workdir(payload: dict[str, Any]) -> Path:
    value = Path(str(payload["control_workdir"])).resolve()
    runtime_root = (REQUEST_ROOT.resolve().parent / "runs").resolve()
    if runtime_root not in value.parents:
        raise ValueError("node200 workdir is outside the approved runtime root")
    return value


def _binding_path(payload: dict[str, Any]) -> Path:
    return _workdir(payload) / "batch-binding.json"


def build_prepare_command(payload: dict[str, Any]) -> list[str]:
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
        str(WGS_REPO_ROOT / "prepare" / "prepare_wgs_batch.py"),
        subcommand,
        "--outpath",
        str(analysis_project_root),
        "--prepare-config",
        WGS_PREPARE_CONFIG,
    ]
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
            CCE_OPERATOR_CONFIG,
            "--skip-samplelist-ready-check",
        ])
        use_reference = str(payload.get("use_reference") or "").strip()
        if use_reference:
            if use_reference not in {"all", "ref", "no"}:
                raise ValueError("use_reference must be all, ref, or no")
            command.extend(["--use-reference", use_reference])
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
    _write_prepare_binding(payload)


def _run_prepare_sampleinfo(payload: dict[str, Any]) -> None:
    validate_release_repository(payload)
    workdir = _workdir(payload)
    workdir.mkdir(parents=True, exist_ok=True)
    project_root = Path(str(payload["analysis_project_root"])).resolve()
    sampleinfo = project_root / "sampleinfo" / f"{payload['batch_no']}.sampleinfo.txt"
    if sampleinfo.is_file() and not sampleinfo.is_symlink():
        return
    if not project_root.is_dir() or not os.access(project_root, os.W_OK):
        raise RuntimeError("WGS analysis project root is unavailable")
    subprocess.run(build_prepare_command(payload), check=True, env=_clean_env())
    if not sampleinfo.is_file() or sampleinfo.is_symlink():
        raise RuntimeError("WGS sampleinfo prepare did not publish the expected table")


def _run_prepare_analysis(payload: dict[str, Any]) -> None:
    binding_path = _binding_path(payload)
    if binding_path.is_file():
        _load_binding(payload)
        return
    validate_release_repository(payload)
    project_root = Path(str(payload["analysis_project_root"])).resolve()
    expected_batch_root = Path(str(payload["expected_batch_root"])).resolve()
    if expected_batch_root != project_root / str(payload["batch_no"]):
        raise RuntimeError("WGS analysis batch path is outside the approved project root")
    subprocess.run(build_prepare_command(payload), check=True, env=_clean_env())
    _write_prepare_binding(payload)


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
    }
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
    binding = _load_binding(payload)
    components = [
        str(binding.get("project") or ""),
        str(binding.get("batch") or ""),
        str(binding.get("run_id") or ""),
    ]
    if any(SAFE_COMPONENT_RE.fullmatch(value) is None for value in components):
        raise RuntimeError("frozen WGS cleanup identity is invalid")
    confirmation = f"DELETE-SFS:{components[0]}/{components[1]}/{components[2]}"
    return _step_command(payload, "step7_cleanup", "--confirm", confirmation)


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
            raise RuntimeError((completed.stderr or completed.stdout)[-2000:])
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
    return _request_path(
        str(payload["analysis_id"]), int(payload["attempt"]), str(payload["stage"])
    ).parent / "transfer-progress" / str(payload["stage"])


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
    binding = _load_binding(payload)
    delivery_root = (
        Path(str(binding["batch_root"])) / "cce" / "cloud_delivery"
    ).resolve()
    files_done = 0
    bytes_done = 0
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
                files_done += 1
                bytes_done += expected_size
        except (OSError, TypeError, ValueError):
            continue
    return files_done, bytes_done


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
        retry_no = 0
        if status.get("status") == "failed":
            if payload["stage"] not in {"step4_publish", "step5_download"}:
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
        _atomic_json(state_path, state)
        return {"status": "accepted", "pid": process.pid, "retry_no": retry_no}


def _run_worker(payload: dict[str, Any]) -> int:
    current_status = _read_json(_sidecar_path(payload, ".status.json"))
    retry_no = int(current_status.get("retry_no", 0))
    if payload["stage"] != "step3_monitor":
        _write_status(payload, "running", retry_no=retry_no)
    try:
        run_stage(payload)
    except Exception as error:
        _write_status(payload, "failed", str(error), retry_no=retry_no)
        raise
    _write_status(payload, "success", retry_no=retry_no)
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
