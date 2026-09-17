"""Native Local/SGE controller calls; no prepare, conversion or scheduler here."""
from __future__ import annotations

import importlib.util
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import re
import subprocess

import yaml


def _prepared_batch(payload: dict, request_root: Path, analysis_root: Path, target: str) -> Path:
    frozen = payload.get("prepare_execution") or {}
    modes = {"node-96": "local", "node-97": "local", "sge-default": "sge"}
    mode = modes.get(target)
    if not mode or frozen.get("target") != target or frozen.get("mode") != mode:
        raise ValueError("Native execution target differs from this runner")
    if payload.get("stage") != f"{mode}_analysis":
        raise ValueError("Native execution stage differs from frozen mode")
    expected = analysis_root.resolve() / str(payload["batch_no"])
    batch = Path(str(payload["expected_batch_root"]))
    if batch.is_symlink() or batch.resolve() != expected or analysis_root.resolve() not in batch.resolve().parents:
        raise ValueError("Native execution batch escapes approved analysis root")
    runtime_root = request_root.resolve().parent
    control = runtime_root / "runs" / payload["analysis_id"] / f"attempt-{payload['attempt']}"
    if Path(str(payload["control_workdir"])).resolve() != control:
        raise ValueError("Native execution control root mismatch")
    # Reuse identity and entry/profile checks, not mutable prepare input hashes.
    # Loading this
    # module does not execute its CLI or access any CCE service/configuration.
    spec = importlib.util.spec_from_file_location("native_prepare_validator", Path(__file__).with_name("wgs_runtime_gate.py"))
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    validator.RUNTIME_RUN_ROOT = str(runtime_root)
    validator._load_binding(payload, native_launch=True)
    return batch


def _execution_snapshot(payload: dict, batch: Path, evidence: Path, command: list[str]) -> Path:
    """Private write-once input evidence; never repeats WGS sample selection."""
    sources = {"config.yaml": batch / "config.yaml"}

    def read(path: Path) -> bytes:
        if path.is_symlink() or not path.is_file() or batch.resolve() not in path.resolve().parents:
            raise ValueError("Native snapshot input is missing or outside the project")
        return path.read_bytes()

    contents = {"config.yaml": read(sources["config.yaml"])}
    config = yaml.safe_load(contents["config.yaml"])
    if not isinstance(config, dict) or not isinstance(config.get("execution"), dict):
        raise ValueError("Native snapshot config is invalid")
    if config["execution"].get("executor") != payload["prepare_execution"]["mode"]:
        raise ValueError("Native snapshot execution mode mismatch")

    # Credentials must stay in private runtime settings, never in project evidence.
    def has_secret(value):
        if isinstance(value, dict):
            return any(
                (re.search(r"(?:password|passwd|token|secret|access[_-]?key|private[_-]?key)", str(key), re.I)
                 and child not in (None, "", False)) or has_secret(child)
                for key, child in value.items()
            )
        return isinstance(value, list) and any(has_secret(child) for child in value)

    if has_secret(config):
        raise ValueError("Project config contains credentials; keep them outside execution snapshots")
    for key in ("sample_info", "new_sample_info"):
        value = config.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Native config must reference its actual sample information")
        source = Path(value)
        source = source if source.is_absolute() else batch / source
        sources[f"{key}.tsv"] = source
        contents[f"{key}.tsv"] = read(source)
        table = csv.DictReader(io.StringIO(contents[f"{key}.tsv"].decode("utf-8-sig")), delimiter="\t")
        if not {"样本编号", "家系编号"}.issubset(table.fieldnames or []):
            raise ValueError("Native sample information lacks required identity columns")
        rows = list(table)
        if not rows or any(not str(row.get("样本编号") or "").strip() for row in rows):
            raise ValueError("Native sample information has no valid execution sample scope")
    # Detect edits during capture without imposing a new workflow locking scheme.
    if any(read(path) != contents[name] for name, path in sources.items()):
        raise ValueError("Native inputs changed during snapshot capture; retry before launch")
    snapshot = evidence / "snapshot"
    snapshot.mkdir(mode=0o700, exist_ok=False)
    manifest = {
        "schema_version": "wgs.native-execution-snapshot.v1",
        **{key: payload[key] for key in ("analysis_id", "attempt", "execution_id", "generation",
                                        "pipeline_release_id", "wgs_source_commit")},
        "execution_target": payload["prepare_execution"]["target"],
        "workdir": str(batch), "argv": command,
        "execution_user": pwd.getpwuid(os.geteuid()).pw_name, "execution_uid": os.geteuid(),
        "files": {name: {"source": str(sources[name]), "sha256": hashlib.sha256(data).hexdigest()}
                  for name, data in contents.items()},
    }
    contents["manifest.json"] = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
    for name, data in contents.items():
        descriptor = os.open(snapshot / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    return snapshot


def run_analysis(payload: dict, *, request_root: Path, analysis_root: Path,
                 evidence_root: Path, logger_root: Path, target: str) -> dict:
    """Run the unchanged foreground Step1 inside the existing background worker."""
    execution_id = str(payload.get("execution_id") or "")
    generation = payload.get("generation")
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", execution_id)
            or type(generation) is not int or generation < 1):
        raise ValueError("Native execution identity is invalid")
    batch = _prepared_batch(payload, request_root, analysis_root, target)
    run_label = f"{payload['analysis_id']}-a{payload['attempt']}"
    native_id = f"{run_label}-g{generation}-{execution_id}"
    evidence = evidence_root.resolve() / payload["analysis_id"] / f"attempt-{payload['attempt']}" / "executions" / execution_id
    if evidence_root.resolve() not in evidence.resolve().parents:
        raise ValueError("Native execution evidence escapes approved root")
    evidence.mkdir(mode=0o700, parents=True, exist_ok=True)
    events = evidence / "rules.jsonl"
    command = ["bash", str(batch / "Step1_run.sh"), "--", "--logger", "airflow-demo"]
    arguments = {
        "analysis-id": payload["analysis_id"], "attempt": payload["attempt"],
        "pipeline-release-id": payload["pipeline_release_id"], "run-label": run_label,
        "role": "master", "stream-id": f"{target}-{execution_id}",
        "workdir": batch, "events-path": events,
    }
    for name, value in arguments.items():
        command.extend([f"--logger-airflow-demo-{name}", str(value)])
    snapshot = _execution_snapshot(payload, batch, evidence, command)
    env = {
        **os.environ, "TZ": "Asia/Shanghai", "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": os.pathsep.join([str(logger_root), os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep),
        "WGS_ATTEMPT_ID": native_id,
    }
    with (evidence / "analysis.log").open("a", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=batch, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, check=False)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command)
    exit_path = batch / "log" / f"step1.{native_id}.exitcode"
    metadata_path = batch / "log" / f"step1.{native_id}.metadata.tsv"
    for path in (exit_path, metadata_path):
        if path.is_symlink() or not path.is_file() or batch.resolve() not in path.resolve().parents:
            raise RuntimeError("Native terminal exitcode/metadata is unavailable")
    exitcode = int(exit_path.read_text().strip())
    metadata = dict(line.split("\t", 1) for line in metadata_path.read_text().splitlines() if "\t" in line)
    if (exitcode != 0 or metadata.get("run_mode") != payload["prepare_execution"]["mode"]
            or not metadata.get("started_at") or not metadata.get("finished_at")):
        raise RuntimeError("Native terminal evidence does not confirm this execution succeeded")
    return {
        "native_execution_id": native_id, "native_exitcode": exitcode,
        "execution_snapshot": str(snapshot),
        "execution_target": target, "native_started_at": metadata["started_at"],
        "native_finished_at": metadata["finished_at"],
    }
