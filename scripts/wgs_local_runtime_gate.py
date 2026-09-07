#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import traceback
from typing import Any

import yaml


ANALYSIS_RE = re.compile(r"^WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
STAGE = "local_analysis"
REQUEST_ROOT = Path(
    os.getenv(
        "WGS_LOCAL_REQUEST_ROOT",
        "/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud/runtime/runner-requests",
    )
)
ANALYSIS_ROOT = Path(
    os.getenv(
        "WGS_LOCAL_ANALYSIS_ROOT",
        "/sg2/50.ctapa/project/HWcloud/WGS_Clinical",
    )
)
EVIDENCE_ROOT = Path(
    os.getenv(
        "WGS_LOCAL_EVIDENCE_ROOT",
        "/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud/runtime/cce-evidence",
    )
)
WGS_REPO_ROOT = Path(
    os.getenv(
        "WGS_LOCAL_REPO_ROOT",
        "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1",
    )
)
LOGGER_ROOT = Path(
    os.getenv(
        "WGS_LOCAL_LOGGER_ROOT",
        "/bi/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current/dags",
    )
)
LOCAL_CORES = int(os.getenv("WGS_LOCAL_CORES", "96"))
LOCAL_SNAKEMAKE_PYTHON = Path(
    os.getenv(
        "WGS_LOCAL_SNAKEMAKE_PYTHON",
        "/bi/biodevrwbi/33.chenjiucheng/project/airflow-WGS/envs/"
        "wgs-snakemake9/bin/python3.12",
    )
)


def parse_command(value: str) -> tuple[str, int, str]:
    parts = shlex.split(str(value or ""), posix=True)
    if len(parts) != 4 or parts[0] != "wgs-local-runtime":
        raise ValueError(
            "Only wgs-local-runtime <analysis_id> <attempt> local_analysis is accepted"
        )
    analysis_id, attempt_text, stage = parts[1:]
    if ANALYSIS_RE.fullmatch(analysis_id) is None or stage != STAGE:
        raise ValueError("invalid WGS local runtime command")
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
        raise ValueError("local runtime request escapes request root")
    return path


def load_request(analysis_id: str, attempt: int, stage: str) -> dict[str, Any]:
    path = _request_path(analysis_id, attempt, stage)
    if path.is_symlink() or not path.is_file():
        raise ValueError("registered local runtime request is missing or unsafe")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != "wgs-runtime.request.v4"
        or payload.get("analysis_id") != analysis_id
        or int(payload.get("attempt") or 0) != attempt
        or payload.get("stage") != stage
    ):
        raise ValueError("local runtime request identity mismatch")
    if int(payload.get("orchestration_contract_version") or 0) != 2:
        raise ValueError("node97 local runtime requires orchestration contract v2")
    for key in ("execution_id", "generation", "request_hash"):
        if payload.get(key) in {None, ""}:
            raise ValueError(f"local runtime request is missing {key}")
    return payload


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".partial"
    )
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o640)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _status_path(payload: dict[str, Any]) -> Path:
    return _request_path(
        str(payload["analysis_id"]), int(payload["attempt"]), str(payload["stage"])
    ).with_suffix(".status.json")


def write_status(
    payload: dict[str, Any], status: str, message: str, **details: Any
) -> bool:
    if status not in {"accepted", "running", "success", "failed"}:
        raise ValueError("unsupported local runtime status")
    value = {
        "schema_version": "wgs-runtime.stage-status.v1",
        "analysis_id": payload["analysis_id"],
        "attempt": int(payload["attempt"]),
        "stage": payload["stage"],
        "status": status,
        "message": str(message)[-4000:],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "retry_no": int(payload.get("retry_no") or 0),
        "orchestration_contract_version": 2,
        "execution_id": payload["execution_id"],
        "generation": int(payload["generation"]),
        "request_hash": payload["request_hash"],
        **details,
    }
    path = _status_path(payload)
    lock = path.with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    rank = {"accepted": 0, "running": 1, "success": 2, "failed": 2}
    with lock.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        current: dict[str, Any] = {}
        if path.is_file() and not path.is_symlink():
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                current = {}
        if current.get("execution_id") not in {None, payload["execution_id"]}:
            raise ValueError("local status belongs to a different execution")
        current_status = str(current.get("status") or "")
        if current_status in {"success", "failed"}:
            return False
        if rank.get(current_status, -1) > rank[status]:
            return False
        _atomic_json(path, value)
    return True


def validate_batch_root(payload: dict[str, Any]) -> Path:
    root = ANALYSIS_ROOT.resolve()
    expected = (root / str(payload.get("batch_no") or "")).resolve()
    requested = Path(str(payload.get("expected_batch_root") or "")).resolve()
    if requested != expected or root not in requested.parents:
        raise ValueError("WGS batch is outside the approved analysis root")
    if requested.is_symlink() or not requested.is_dir():
        raise ValueError("frozen WGS batch is unavailable")
    required = (requested / "config.yaml", requested / "pipeline", requested / "raw")
    if not required[0].is_file() or not required[1].is_dir() or not required[2].is_dir():
        raise ValueError("frozen WGS batch snapshot is incomplete")
    return requested


def local_source_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("frozen WGS config must be a mapping")
    execution = payload.get("execution")
    if not isinstance(execution, dict):
        raise ValueError("frozen WGS config is missing execution settings")
    payload["execution"] = {**execution, "executor": "local"}
    return payload


def _load_module(name: str, path: Path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required local runtime module is unavailable: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load local runtime module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _atomic_yaml(path: Path, payload: dict[str, Any]) -> None:
    descriptor, name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".partial"
    )
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o640)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def normalize_local_fastq_links(raw_directory: Path) -> list[str]:
    """Flatten intake indirection so Apptainer only needs the final source bind."""
    fastq_sources: list[str] = []
    for path in sorted(raw_directory.iterdir()):
        if not path.is_symlink():
            continue
        target = path.resolve(strict=True)
        if not target.is_file():
            raise ValueError(f"FASTQ link target is not a file: {path.name}")
        temporary = path.with_name(f".{path.name}.node97-link")
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(target)
        os.replace(temporary, path)
        fastq_sources.append(str(target))
    if not fastq_sources:
        raise ValueError("frozen WGS batch has no FASTQ links")
    return fastq_sources


def prepare_local_snapshot(payload: dict[str, Any]) -> Path:
    batch = validate_batch_root(payload)
    pipeline = batch / "pipeline"
    config_path = batch / "config.yaml"
    original_path = batch / "config.cce-prepared.yaml"
    if not original_path.exists():
        original_path.write_bytes(config_path.read_bytes())
        original_path.chmod(0o640)
    source = local_source_config(original_path)
    overlay_module = _load_module(
        "wgs_local_runtime_overlay", pipeline / "script" / "runtime_overlay.py"
    )
    resolved = overlay_module.load_runtime_overlay(source, pipeline)
    if not isinstance(resolved, dict):
        raise ValueError("local runtime overlay did not return a config mapping")
    _atomic_yaml(config_path, resolved)

    runtime_module = _load_module(
        "wgs_local_prepare_runtime", pipeline / "prepare" / "runtime.py"
    )
    prepare_config_path = WGS_REPO_ROOT / "prepare" / "config.yaml"
    if prepare_config_path.is_symlink() or not prepare_config_path.is_file():
        raise ValueError("approved WGS prepare config is unavailable")
    prepare_config = yaml.safe_load(prepare_config_path.read_text(encoding="utf-8"))
    if not isinstance(prepare_config, dict):
        raise ValueError("approved WGS prepare config is invalid")
    fastq_sources = normalize_local_fastq_links(batch / "raw")
    runtime_module.write_step1(
        batch / "Step1_run.sh",
        batch,
        "local",
        prepare_config,
        resolved,
        fastq_sources=fastq_sources,
    )
    return batch


def _evidence_directory(payload: dict[str, Any]) -> Path:
    root = EVIDENCE_ROOT.resolve()
    directory = (
        root / str(payload["analysis_id"]) / f"attempt-{int(payload['attempt'])}"
    ).resolve()
    if root not in directory.parents:
        raise ValueError("local evidence path escapes evidence root")
    return directory


def build_local_command(payload: dict[str, Any], batch: Path) -> list[str]:
    if not 1 <= LOCAL_CORES <= 128:
        raise ValueError("WGS_LOCAL_CORES must be between 1 and 128")
    events = _evidence_directory(payload) / "rule-status" / "raw" / "node97.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    # This must match the immutable evidence binding created for the attempt.
    # The observer rejects logger events whose run label drifts from that binding.
    run_label = f"{payload['analysis_id']}-a{payload['attempt']}"
    return [
        "bash",
        str(batch / "Step1_run.sh"),
        "--",
        "--cores",
        str(LOCAL_CORES),
        "--logger",
        "airflow-demo",
        "--logger-airflow-demo-analysis-id",
        str(payload["analysis_id"]),
        "--logger-airflow-demo-attempt",
        str(payload["attempt"]),
        "--logger-airflow-demo-pipeline-release-id",
        str(payload["pipeline_release_id"]),
        "--logger-airflow-demo-run-label",
        run_label,
        "--logger-airflow-demo-role",
        "master",
        "--logger-airflow-demo-stream-id",
        "node97",
        "--logger-airflow-demo-workdir",
        str(batch),
        "--logger-airflow-demo-events-path",
        str(events),
    ]


def build_smoke_command(payload: dict[str, Any]) -> tuple[Path, list[str]]:
    if payload.get("validation_scope") != "node97_smoke":
        raise ValueError("node97 smoke requires the exact validation scope")
    workdir = _evidence_directory(payload) / "synthetic-smoke"
    workdir.mkdir(parents=True, exist_ok=True)
    snakefile = workdir / "Snakefile"
    snakefile.write_text(
        'SAMPLE = "SMOKE001"\n\n'
        "rule all:\n"
        "    input:\n"
        '        f"results/{SAMPLE}.done"\n\n'
        "rule smoke_prepare:\n"
        "    output:\n"
        '        "work/input.ready"\n'
        "    shell:\n"
        '        "sleep 1; mkdir -p work; printf \'ready\\n\' > {output}"\n\n'
        "rule smoke_sample:\n"
        "    input:\n"
        '        "work/input.ready"\n'
        "    output:\n"
        '        "results/{sample}.done"\n'
        "    wildcard_constraints:\n"
        '        sample="SMOKE001"\n'
        "    shell:\n"
        '        "sleep 2; mkdir -p results; printf \'{wildcards.sample}\\n\' > {output}"\n',
        encoding="utf-8",
    )
    events = _evidence_directory(payload) / "rule-status" / "raw" / "node97.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    run_label = f"{payload['analysis_id']}-a{payload['attempt']}"
    return workdir, [
        str(LOCAL_SNAKEMAKE_PYTHON),
        "-m",
        "snakemake",
        "--snakefile",
        str(snakefile),
        "--directory",
        str(workdir),
        "--cores",
        "1",
        "--rerun-incomplete",
        "--printshellcmds",
        "--show-failed-logs",
        "--logger",
        "airflow-demo",
        "--logger-airflow-demo-analysis-id",
        str(payload["analysis_id"]),
        "--logger-airflow-demo-attempt",
        str(payload["attempt"]),
        "--logger-airflow-demo-pipeline-release-id",
        str(payload["pipeline_release_id"]),
        "--logger-airflow-demo-run-label",
        run_label,
        "--logger-airflow-demo-role",
        "master",
        "--logger-airflow-demo-stream-id",
        "node97-smoke",
        "--logger-airflow-demo-workdir",
        str(workdir),
        "--logger-airflow-demo-events-path",
        str(events),
    ]


def _runtime_environment(payload: dict[str, Any]) -> dict[str, str]:
    return {
        **os.environ,
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": os.pathsep.join(
            [str(LOGGER_ROOT), os.environ.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep),
        "WGS_ATTEMPT_ID": f"{payload['analysis_id']}-a{payload['attempt']}",
    }


def run_node97_smoke(payload: dict[str, Any]) -> None:
    workdir, command = build_smoke_command(payload)
    if not LOCAL_SNAKEMAKE_PYTHON.is_file():
        raise ValueError("approved node97 Snakemake 9 Python is unavailable")
    log_path = workdir / "smoke.log"
    with log_path.open("a", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=workdir,
            env=_runtime_environment(payload),
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, command)


def run_local_analysis(payload: dict[str, Any]) -> None:
    if payload.get("validation_scope") == "node97_smoke":
        run_node97_smoke(payload)
        return
    batch = prepare_local_snapshot(payload)
    command = build_local_command(payload, batch)
    log_dir = _evidence_directory(payload) / "mirror"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "analysis.log"
    with log_path.open("a", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=batch,
            env=_runtime_environment(payload),
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, command)


def _worker(analysis_id: str, attempt: int, stage: str) -> int:
    payload = load_request(analysis_id, attempt, stage)
    write_status(payload, "running", "WGS local workflow is running on node97")
    try:
        run_local_analysis(payload)
    except BaseException as error:
        write_status(
            payload,
            "failed",
            f"{type(error).__name__}: {error}",
            traceback=traceback.format_exc()[-12000:],
        )
        return 1
    write_status(payload, "success", "WGS local workflow completed on node97")
    return 0


def _start(payload: dict[str, Any]) -> dict[str, Any]:
    if os.getenv("WGS_LOCAL_EXECUTION_ENABLED", "false").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        raise RuntimeError("node97 local WGS execution is disabled")
    status = _status_path(payload)
    current = {}
    if status.is_file() and not status.is_symlink():
        current = json.loads(status.read_text(encoding="utf-8"))
        if current.get("execution_id") == payload["execution_id"] and current.get(
            "status"
        ) in {"accepted", "running", "success"}:
            return {
                "status": current["status"],
                "execution_id": payload["execution_id"],
                "idempotent": True,
            }
    write_status(payload, "accepted", "WGS local workflow accepted on node97")
    lock = status.with_suffix(".worker.lock")
    log = status.with_suffix(".worker.log")
    command = [
        "nohup",
        "setsid",
        "flock",
        "-n",
        str(lock),
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        str(payload["analysis_id"]),
        str(payload["attempt"]),
        str(payload["stage"]),
    ]
    with log.open("ab") as handle:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return {
        "status": "accepted",
        "execution_id": payload["execution_id"],
        "pid": process.pid,
        "idempotent": False,
    }


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--worker":
        if len(argv) != 4:
            raise ValueError("invalid local worker invocation")
        return _worker(argv[1], int(argv[2]), argv[3])
    command = os.getenv("SSH_ORIGINAL_COMMAND") or " ".join(argv)
    analysis_id, attempt, stage = parse_command(command)
    payload = load_request(analysis_id, attempt, stage)
    result = _start(payload)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as error:
        print(f"wgs local runtime rejected: {error}", file=sys.stderr)
        raise SystemExit(1) from error
