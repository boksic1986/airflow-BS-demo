from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import subprocess
import sys
from typing import Any

import yaml

from common.resource_monitor import ResourceMonitor


ANALYSIS_ID_RE = re.compile(r"^WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")
SUPPORTED_STAGES = {"prepare", "pre_calling", "variant_analysis", "collect_qc", "collect_artifacts"}
DEFAULT_RESULTS_ROOT = Path(
    os.getenv("WGS_RESULTS_ROOT", "/mnt/biodevrwbi/33.chenjiucheng/airflow-result/wgs")
)
DEFAULT_PIPELINE_ROOT = Path(
    os.getenv(
        "WGS_S9_PIPELINE_ROOT",
        "/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current/pipelines/wgs_s9",
    )
)
DEFAULT_SNAKEMAKE_BIN = Path(
    os.getenv(
        "WGS_SNAKEMAKE_BIN",
        "/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/envs/wgs-snakemake9/bin/snakemake",
    )
)
DEFAULT_ENV_SCRIPT = Path(
    os.getenv(
        "WGS_ENV_SCRIPT",
        "/sg2/biodevrwsg2/33.chenjiucheng/project/wgs/profiles/bs_direct/env.sh",
    )
)
DEFAULT_CONFIG_ROOTS = (
    "/sg2/biodevrwsg2/33.chenjiucheng/WGS_test",
    "/mnt/biodevrwsg2/33.chenjiucheng/WGS_test",
    "/mnt/biodevrwbi/33.chenjiucheng/airflow-intake-configs/wgs",
)
DEFAULT_FASTQ_ROOTS = (
    "/sg2/biodevrwsg2/33.chenjiucheng/WGS_test",
    "/mnt/biodevrwsg2/33.chenjiucheng/WGS_test",
)


def parse_forced_command(command: str) -> tuple[str, str]:
    parts = shlex.split(str(command or ""), posix=True)
    if len(parts) != 3 or parts[0] != "wgs-run":
        raise ValueError("Only 'wgs-run <analysis_id> <stage>' is accepted.")
    analysis_id, stage = parts[1], parts[2]
    if not ANALYSIS_ID_RE.fullmatch(analysis_id):
        raise ValueError("Invalid WGS analysis_id.")
    if stage not in SUPPORTED_STAGES:
        raise ValueError(f"Unsupported WGS stage: {stage}.")
    return analysis_id, stage


def resolve_request_path(analysis_id: str, *, results_root: Path = DEFAULT_RESULTS_ROOT) -> Path:
    if not ANALYSIS_ID_RE.fullmatch(analysis_id):
        raise ValueError("Invalid WGS analysis_id.")
    root = Path(results_root).resolve()
    request = (root / "runs" / analysis_id / "config" / "wgs_runner_request.json").resolve()
    if request != root and not request.is_relative_to(root):
        raise ValueError("WGS request path escapes results root.")
    return request


def load_request(analysis_id: str, *, results_root: Path = DEFAULT_RESULTS_ROOT) -> dict[str, Any]:
    request_path = resolve_request_path(analysis_id, results_root=results_root)
    if not request_path.is_file():
        raise FileNotFoundError(f"WGS runner request is not readable: {request_path}")
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("analysis_id") != analysis_id or payload.get("pipeline") != "wgs":
        raise ValueError("WGS runner request identity does not match the forced command.")
    expected_workdir = (Path(results_root).resolve() / "runs" / analysis_id).resolve()
    host_workdir = Path(str(payload.get("host_workdir") or "")).resolve()
    if host_workdir != expected_workdir:
        raise ValueError(f"WGS host_workdir must be {expected_workdir}.")
    return payload


def build_snakemake_command(
    request: dict[str, Any],
    *,
    stage: str,
    snakemake_bin: Path = DEFAULT_SNAKEMAKE_BIN,
    pipeline_root: Path = DEFAULT_PIPELINE_ROOT,
    cores: int = 96,
) -> list[str]:
    if stage not in {"pre_calling", "variant_analysis", "collect_qc"}:
        raise ValueError(f"Stage does not run Snakemake: {stage}")
    workdir = Path(str(request["host_workdir"])).resolve()
    analysis_id = str(request["analysis_id"])
    if stage == "pre_calling":
        snakefile = pipeline_root / "WGS_pipeline_fastq2vcf.Snakefile"
        config_path = workdir / "config" / "wgs.precalling.resolved.yaml"
        targets = _precalling_targets(config_path)
    else:
        snakefile = pipeline_root / "WGS_pipeline.Snakefile"
        config_path = workdir / "config" / "wgs.downstream.resolved.yaml"
        targets = _downstream_targets(workdir / "config" / "targets.resolved.txt", qc_only=stage == "collect_qc")
    command = [
        str(snakemake_bin),
        "--executor",
        "local",
        "--cores",
        str(int(cores)),
        "--resources",
        "qsub_vf=120000",
        "--rerun-incomplete",
        "--keep-going",
        "--printshellcmds",
        "--show-failed-logs",
        "--latency-wait",
        "60",
        "--logger",
        "airflow-demo",
        "--logger-airflow-demo-analysis-id",
        analysis_id,
        "--logger-airflow-demo-workdir",
        str(workdir),
        "--logger-airflow-demo-events-path",
        str(workdir / "logs" / "events" / "snakemake_events.jsonl"),
        "--snakefile",
        str(snakefile),
        "--configfile",
        str(config_path),
        "--directory",
        str(workdir),
    ]
    backend_event_url = str(request.get("backend_event_url") or "").strip()
    if backend_event_url:
        command.extend(["--logger-airflow-demo-backend-event-url", backend_event_url])
    command.extend(targets)
    return command


def run_forced_command(command: str) -> int:
    analysis_id, stage = parse_forced_command(command)
    request = load_request(analysis_id)
    workdir = Path(str(request["host_workdir"])).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    with (workdir / ".wgs-runner.lock").open("a+", encoding="utf-8") as lock_handle:
        _acquire_exclusive_lock(lock_handle)
        if stage == "prepare":
            prepare_run(request)
        elif stage in {"pre_calling", "variant_analysis", "collect_qc"}:
            run_snakemake_stage(request, stage=stage)
        else:
            collect_artifacts(request)
    return 0


def prepare_run(request: dict[str, Any]) -> None:
    workdir = Path(str(request["host_workdir"])).resolve()
    for relative in ("config", "logs", "logs/events", "logs/resources", "reports", "reports/resources"):
        (workdir / relative).mkdir(parents=True, exist_ok=True)
    roots = _configured_roots("WGS_CONFIG_ROOTS", DEFAULT_CONFIG_ROOTS)
    fastq_roots = _configured_roots("WGS_FASTQ_ROOTS", DEFAULT_FASTQ_ROOTS)
    input_root = (workdir / "config").resolve()
    source_pre = _approved_file(request.get("precalling_config_path"), (input_root,), "pre-calling config")
    source_down = _approved_file(request.get("downstream_config_path"), (input_root,), "downstream config")
    source_targets = _approved_file(request.get("targets_path"), (input_root,), "targets")
    _verify_input_hashes(
        request,
        precalling_config=source_pre,
        downstream_config=source_down,
        targets=source_targets,
    )
    if not DEFAULT_ENV_SCRIPT.is_file():
        raise FileNotFoundError(f"WGS environment script is not readable: {DEFAULT_ENV_SCRIPT}")
    if not DEFAULT_SNAKEMAKE_BIN.is_file():
        raise FileNotFoundError(f"WGS Snakemake 9 executable is not readable: {DEFAULT_SNAKEMAKE_BIN}")
    for filename in ("WGS_pipeline_fastq2vcf.Snakefile", "WGS_pipeline.Snakefile"):
        if not (DEFAULT_PIPELINE_ROOT / filename).is_file():
            raise FileNotFoundError(f"WGS S9 adapter is missing: {DEFAULT_PIPELINE_ROOT / filename}")
    pre_payload = _read_yaml_mapping(source_pre)
    down_payload = _read_yaml_mapping(source_down)
    _validate_wgs_config(pre_payload, roots=roots, fastq_roots=fastq_roots)
    _validate_wgs_config(down_payload, roots=roots, fastq_roots=fastq_roots)
    batch_context = _stage_historical_pre_calling_context(
        request,
        workdir=workdir,
        precalling_config=pre_payload,
        downstream_config=down_payload,
        approved_config_roots=roots,
    )
    targets = _read_target_lines(source_targets)
    config_dir = workdir / "config"
    shutil.copyfile(source_pre, config_dir / "wgs.precalling.resolved.yaml")
    shutil.copyfile(source_down, config_dir / "wgs.downstream.resolved.yaml")
    (config_dir / "targets.resolved.txt").write_text("\n".join(targets) + "\n", encoding="utf-8")
    provenance = {
        "analysis_id": request["analysis_id"],
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "environment_script": str(DEFAULT_ENV_SCRIPT),
        "snakemake_bin": str(DEFAULT_SNAKEMAKE_BIN),
        "pipeline_root": str(DEFAULT_PIPELINE_ROOT),
        "source_precalling_config": str(source_pre),
        "source_downstream_config": str(source_down),
        "source_targets": str(source_targets),
        "target_count": len(targets),
        "input_sha256": dict(request.get("input_sha256") or {}),
        "historical_pre_calling_context": batch_context,
    }
    (config_dir / "wgs_runtime_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_snakemake_stage(request: dict[str, Any], *, stage: str) -> dict[str, Any]:
    if request.get("wgs_stage") == "precalling" and stage != "pre_calling":
        print(f"WGS validation mode stops after pre-calling; {stage} is a no-op.", flush=True)
        return {"stage": stage, "status": "not_requested"}
    workdir = Path(str(request["host_workdir"])).resolve()
    command = build_snakemake_command(request, stage=stage)
    if stage == "collect_qc" and not _downstream_targets(
        workdir / "config" / "targets.resolved.txt",
        qc_only=True,
    ):
        print("No explicit QC targets were requested; validating existing QC outputs.", flush=True)
        return _write_qc_inventory(workdir)
    log_dir = workdir / "logs"
    stdout_path = log_dir / f"snakemake.{stage}.stdout.log"
    stderr_path = log_dir / f"snakemake.{stage}.stderr.log"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(DEFAULT_PIPELINE_ROOT.parents[1] / "dags"), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    env["INTERNAL_SERVICE_TOKEN"] = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    wrapped = [
        "/bin/bash",
        "-lc",
        f"source {shlex.quote(str(DEFAULT_ENV_SCRIPT))} >/dev/null && exec {shlex.join(command)}",
    ]
    return_code = _stream_process(
        wrapped,
        cwd=workdir,
        env=env,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        stage=stage,
    )
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, wrapped)
    return {"stage": stage, "status": "success", "return_code": 0}


def collect_artifacts(request: dict[str, Any]) -> dict[str, Any]:
    workdir = Path(str(request["host_workdir"])).resolve()
    resource_summaries = []
    for path in sorted((workdir / "reports" / "resources").glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            resource_summaries.append(payload)
    summary = {
        "analysis_id": request["analysis_id"],
        "wall_seconds": sum(float(item.get("wall_seconds") or 0) for item in resource_summaries),
        "peak_pss_bytes": _max_nullable(item.get("peak_pss_bytes") for item in resource_summaries),
        "peak_rss_bytes": max((int(item.get("peak_rss_bytes") or 0) for item in resource_summaries), default=0),
        "read_bytes": sum(int(item.get("read_bytes") or 0) for item in resource_summaries),
        "write_bytes": sum(int(item.get("write_bytes") or 0) for item in resource_summaries),
        "cpu_seconds": sum(float(item.get("cpu_seconds") or 0) for item in resource_summaries),
        "sample_count": sum(int(item.get("sample_count") or 0) for item in resource_summaries),
        "complete": bool(resource_summaries) and all(bool(item.get("complete")) for item in resource_summaries),
        "source": "host_procfs_process_tree",
        "stages": resource_summaries,
        "raw_samples_paths": [
            _relative_artifact_path(workdir, item.get("samples_path"))
            for item in resource_summaries
            if item.get("samples_path")
        ],
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    (workdir / "reports" / "resource_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_qc_inventory(workdir)
    return summary


def _stream_process(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    stage: str,
) -> int:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    monitor = ResourceMonitor(
        root_pid=process.pid,
        samples_path=cwd / "logs" / "resources" / f"{stage}.jsonl",
        summary_path=cwd / "reports" / "resources" / f"{stage}.json",
        interval_seconds=float(os.getenv("WGS_RESOURCE_INTERVAL_SECONDS", "5")),
    )
    monitor.start()
    selector = selectors.DefaultSelector()
    assert process.stdout is not None and process.stderr is not None
    selector.register(process.stdout, selectors.EVENT_READ, (stdout_path, sys.stdout))
    selector.register(process.stderr, selectors.EVENT_READ, (stderr_path, sys.stderr))
    handles = {stdout_path: stdout_path.open("a", encoding="utf-8"), stderr_path: stderr_path.open("a", encoding="utf-8")}
    try:
        while selector.get_map():
            for key, _ in selector.select(timeout=1):
                line = key.fileobj.readline()
                if not line:
                    selector.unregister(key.fileobj)
                    continue
                path, terminal = key.data
                handles[path].write(line)
                handles[path].flush()
                terminal.write(line)
                terminal.flush()
        return_code = process.wait()
    finally:
        for handle in handles.values():
            handle.close()
    monitor.stop(return_code=return_code)
    return return_code


def _precalling_targets(config_path: Path) -> list[str]:
    payload = _read_yaml_mapping(config_path)
    configured_samples = payload.get("sample")
    if configured_samples is None:
        sample_info = Path(str(payload.get("sample_info") or ""))
        if not sample_info.is_file():
            raise FileNotFoundError(f"WGS sample_info is not readable: {sample_info}")
        sample_ids = _sample_ids(sample_info)
    else:
        if not isinstance(configured_samples, list):
            raise ValueError("WGS pre-calling config sample must be a list.")
        sample_ids = list(
            dict.fromkeys(str(sample_id).strip() for sample_id in configured_samples if str(sample_id).strip())
        )
        if not sample_ids:
            raise ValueError("WGS pre-calling config sample contains no samples.")
    targets = []
    for sample_id in sample_ids:
        targets.extend(
            [
                f"00_PreCalling/{sample_id}.g.vcf.gz",
                f"00_PreCalling/{sample_id}.deduped.cram",
                f"00_PreCalling/{sample_id}.deduped.cram.crai",
                f"00_PreCalling/{sample_id}.blk",
            ]
        )
    return targets


def _stage_historical_pre_calling_context(
    request: dict[str, Any],
    *,
    workdir: Path,
    precalling_config: dict[str, Any],
    downstream_config: dict[str, Any],
    approved_config_roots: tuple[Path, ...],
) -> dict[str, Any]:
    if str(request.get("wgs_stage") or "") != "full":
        return {"sample_count": 0, "file_count": 0, "status": "not_required"}
    new_samples = set(_configured_sample_names(precalling_config, label="pre-calling"))
    downstream_samples = set(_configured_sample_names(downstream_config, label="downstream"))
    historical_samples = sorted(downstream_samples - new_samples)
    if not historical_samples:
        return {"sample_count": 0, "file_count": 0, "status": "not_required"}
    source_root = _approved_directory(
        request.get("source_analysis_root"),
        approved_config_roots,
        "source analysis root",
    )
    source_precalling = source_root / "00_PreCalling"
    if not source_precalling.is_dir():
        raise FileNotFoundError(f"WGS historical pre-calling directory is not readable: {source_precalling}")
    allowed_targets = _configured_roots(
        "WGS_PRECALLING_SOURCE_ROOTS",
        (str(source_root),),
    )
    destination_root = workdir / "00_PreCalling"
    destination_root.mkdir(parents=True, exist_ok=True)
    qc_destination_root = workdir / "07_QC"
    qc_destination_root.mkdir(parents=True, exist_ok=True)
    linked_files = 0
    missing_samples = []
    missing_blocks = []
    missing_qc = []
    for sample_id in historical_samples:
        matched = 0
        resolved_sources: list[Path] = []
        for source in source_precalling.iterdir():
            if not _belongs_to_sample(source.name, sample_id):
                continue
            resolved = source.resolve(strict=True)
            destination = destination_root / source.name
            if _link_historical_context_file(
                source=resolved,
                destination=destination,
                allowed_targets=allowed_targets,
            ):
                linked_files += 1
            matched += 1
            resolved_sources.append(resolved)
        if matched == 0:
            missing_samples.append(sample_id)
            continue
        block_destination = destination_root / f"{sample_id}.blk"
        if not block_destination.exists():
            for resolved_source in resolved_sources:
                block_source = resolved_source.parent / f"{sample_id}.blk"
                if not block_source.is_file():
                    continue
                if _link_historical_context_file(
                    source=block_source.resolve(strict=True),
                    destination=block_destination,
                    allowed_targets=allowed_targets,
                ):
                    linked_files += 1
                break
        if not block_destination.is_file():
            missing_blocks.append(sample_id)
        qc_destination = qc_destination_root / f"{sample_id}.template.json"
        if not qc_destination.exists():
            qc_sources = [source_root / "07_QC" / qc_destination.name]
            qc_sources.extend(
                resolved_source.parent.parent / "07_QC" / qc_destination.name
                for resolved_source in resolved_sources
            )
            for qc_source in dict.fromkeys(qc_sources):
                if not qc_source.is_file():
                    continue
                if _link_historical_context_file(
                    source=qc_source.resolve(strict=True),
                    destination=qc_destination,
                    allowed_targets=allowed_targets,
                ):
                    linked_files += 1
                break
        if not qc_destination.is_file():
            missing_qc.append(sample_id)
    if missing_samples:
        raise FileNotFoundError(
            "WGS historical pre-calling context is missing samples: " + ", ".join(missing_samples)
        )
    if missing_blocks:
        raise FileNotFoundError(
            "WGS historical pre-calling context is missing .blk files for samples: "
            + ", ".join(missing_blocks)
        )
    if missing_qc:
        raise FileNotFoundError(
            "WGS historical pre-calling context is missing fastp QC JSON for samples: "
            + ", ".join(missing_qc)
        )
    return {
        "sample_count": len(historical_samples),
        "file_count": linked_files,
        "status": "linked_read_only",
    }


def _link_historical_context_file(
    *,
    source: Path,
    destination: Path,
    allowed_targets: tuple[Path, ...],
) -> bool:
    resolved = source.resolve(strict=True)
    if not resolved.is_file() or not any(
        resolved == root or resolved.is_relative_to(root) for root in allowed_targets
    ):
        raise ValueError(f"WGS historical context target is outside approved roots: {source}")
    if destination.exists() or destination.is_symlink():
        try:
            existing = destination.resolve(strict=True)
        except FileNotFoundError as exc:
            raise FileExistsError(
                f"WGS historical context destination is a broken link: {destination}"
            ) from exc
        if destination.is_symlink() and existing == resolved:
            return False
        raise FileExistsError(f"WGS historical context destination already exists: {destination}")
    destination.symlink_to(resolved)
    return True


def _configured_sample_names(payload: dict[str, Any], *, label: str) -> list[str]:
    configured = payload.get("sample")
    if not isinstance(configured, list):
        raise ValueError(f"WGS {label} config sample must be a list.")
    samples = list(dict.fromkeys(str(item).strip() for item in configured if str(item).strip()))
    if not samples:
        raise ValueError(f"WGS {label} config sample contains no samples.")
    return samples


def _approved_directory(value: object, roots: tuple[Path, ...], label: str) -> Path:
    path = Path(str(value or "")).resolve()
    if not any(path == root or path.is_relative_to(root) for root in roots):
        raise ValueError(f"WGS {label} is outside approved roots: {path}")
    if not path.is_dir():
        raise FileNotFoundError(f"WGS {label} is not readable: {path}")
    return path


def _belongs_to_sample(filename: str, sample_id: str) -> bool:
    return filename == sample_id or filename.startswith(f"{sample_id}.") or filename.startswith(f"{sample_id}-")


def _downstream_targets(path: Path, *, qc_only: bool) -> list[str]:
    targets = _read_target_lines(path)
    qc_targets = [item for item in targets if item.startswith("07_QC/")]
    return qc_targets if qc_only else [item for item in targets if item not in qc_targets]


def _sample_ids(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError("WGS sample_info has no header.")
        key = next((candidate for candidate in ("sample_id", "sample", "样本编号", "样本ID") if candidate in reader.fieldnames), reader.fieldnames[0])
        values = [str(row.get(key) or "").strip() for row in reader]
    samples = list(dict.fromkeys(item for item in values if item))
    if not samples:
        raise ValueError("WGS sample_info contains no samples.")
    return samples


def _validate_wgs_config(
    payload: dict[str, Any],
    *,
    roots: tuple[Path, ...],
    fastq_roots: tuple[Path, ...] | None = None,
) -> None:
    sample_info = _approved_file(payload.get("sample_info"), roots, "sample_info")
    _sample_ids(sample_info)
    fastq_dir = Path(str(payload.get("fastqDir") or "")).resolve()
    approved_fastq_roots = fastq_roots or roots
    if not any(fastq_dir == root or fastq_dir.is_relative_to(root) for root in approved_fastq_roots):
        raise ValueError(f"WGS fastqDir is outside approved roots: {fastq_dir}")
    if not fastq_dir.is_dir():
        raise FileNotFoundError(f"WGS fastqDir is not readable: {fastq_dir}")


def _acquire_exclusive_lock(handle) -> None:
    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError("This WGS analysis already has an active host runner stage.") from exc


def _approved_file(value: object, roots: tuple[Path, ...], label: str) -> Path:
    path = Path(str(value or "")).resolve()
    if not any(path == root or path.is_relative_to(root) for root in roots):
        raise ValueError(f"WGS {label} is outside approved roots: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"WGS {label} is not readable: {path}")
    return path


def _configured_roots(name: str, defaults: tuple[str, ...]) -> tuple[Path, ...]:
    raw = os.getenv(name, ",".join(defaults))
    roots = tuple(Path(item.strip()).resolve() for item in raw.split(",") if item.strip())
    if not roots:
        raise ValueError(f"{name} must contain at least one approved root.")
    return roots


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"WGS config must be a YAML mapping: {path}")
    return payload


def _read_target_lines(path: Path) -> list[str]:
    targets = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(item.startswith("/") or ".." in Path(item).parts for item in targets):
        raise ValueError("WGS targets must be relative paths without traversal.")
    return targets


def _verify_input_hashes(request: dict[str, Any], **paths: Path) -> None:
    expected = dict(request.get("input_sha256") or {})
    for label, path in paths.items():
        wanted = str(expected.get(label) or "").lower()
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if not re.fullmatch(r"[0-9a-f]{64}", wanted) or actual != wanted:
            raise ValueError(f"WGS run-local input SHA256 mismatch for {label}.")


def _write_qc_inventory(workdir: Path) -> dict[str, Any]:
    qc_dir = workdir / "07_QC"
    files = [path.relative_to(workdir).as_posix() for path in qc_dir.rglob("*") if path.is_file()] if qc_dir.is_dir() else []
    payload = {"status": "available" if files else "not_captured", "file_count": len(files), "files": files[:500]}
    (workdir / "reports" / "wgs_qc_inventory.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _max_nullable(values) -> int | None:
    present = [int(value) for value in values if value is not None]
    return max(present) if present else None


def _relative_artifact_path(workdir: Path, value: object) -> str:
    path = Path(str(value or "")).resolve()
    root = workdir.resolve()
    if path != root and not path.is_relative_to(root):
        raise ValueError(f"Resource artifact is outside WGS workdir: {path}")
    return path.relative_to(root).as_posix()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = os.getenv("SSH_ORIGINAL_COMMAND", "").strip() or " ".join(shlex.quote(item) for item in argv)
    if not command:
        raise ValueError("SSH_ORIGINAL_COMMAND is required.")
    return run_forced_command(command)


if __name__ == "__main__":
    raise SystemExit(main())
