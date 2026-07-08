from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any

import yaml

from common.progress_events import emit_progress_event, parse_snakemake_output_for_events


DEFAULT_SHARED_ROOT = Path(os.getenv("CONTAINER_SHARED_ROOT", "/data/airflow-demo"))
DEFAULT_PGTA_PIPELINE_ROOT = Path(os.getenv("PGTA_CONTAINER_ROOT", "/opt/pipelines/PGT_A"))
DEFAULT_PGTA_DATA_ROOT = Path(os.getenv("PGTA_CONTAINER_DATA_ROOT", "/data/project/CNV/PGT-A"))
DEFAULT_SNAKEMAKE_BIN = Path(os.getenv("PGTA_SNAKEMAKE_BIN", "/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"))
DEFAULT_PGTA_PYTHON_BIN = Path(os.getenv("PGTA_PYTHON_BIN", "/biosoftware/miniconda/envs/snakemake_env/bin/python"))
DEFAULT_PGTA_CONDA_LIB = Path(os.getenv("PGTA_CONDA_LIB", "/biosoftware/miniconda/envs/snakemake_env/lib"))
DEFAULT_PGTA_LIBSTDCXX = Path(
    os.getenv("PGTA_LIBSTDCXX", str(DEFAULT_PGTA_CONDA_LIB / "libstdc++.so.6"))
)
DEFAULT_SAMTOOLS_BIN = Path(os.getenv("PGTA_SAMTOOLS_BIN", "/biosoftware/miniconda/pkgs/samtools-1.7-1/bin/samtools"))
DEFAULT_SAMTOOLS_LIBRARY_PATH = os.getenv("PGTA_SAMTOOLS_LIBRARY_PATH", "/biosoftware/miniconda/pkgs/openssl-1.0.2u-h516909a_0/lib")
DEFAULT_REFERENCE_GENOME = Path(os.getenv("PGTA_REFERENCE_GENOME", "/data/Database/index/hg19/hg19.fa"))
DEFAULT_SNAKEMAKE_CORES = "64"
PGTA_BASELINE_PREFLIGHT_IMPORTS = ("matplotlib", "numpy", "pandas", "pysam", "scipy")
SUPPORTED_PGTA_TARGETS = {"metadata", "dryrun_cnv", "invalid_target", "baseline_qc"}
SUPPORTED_PGTA_MODES = {"new", "resume", "rerun_stage"}
SUPPORTED_PGTA_STAGES = {"mapping", "metadata", "baseline_qc"}
INVALID_SNAKEMAKE_TARGET = "__airflow_demo_invalid_target__"


def validate_pgta_conf(
    conf: dict[str, Any],
    *,
    shared_root: Path = DEFAULT_SHARED_ROOT,
) -> dict[str, Any]:
    analysis_id = str(conf.get("analysis_id") or "").strip()
    pipeline = str(conf.get("pipeline") or "").strip()
    sample_sheet_path = Path(str(conf.get("sample_sheet_path") or "")).resolve()
    workdir = Path(str(conf.get("workdir") or "")).resolve()
    params = dict(conf.get("params") or {})
    target = str(params.get("target") or "metadata").strip()
    mode = str(conf.get("mode") or "new").strip()

    if not analysis_id:
        raise ValueError("analysis_id is required.")
    if pipeline != "pgta":
        raise ValueError("pipeline must be pgta.")
    if target not in SUPPORTED_PGTA_TARGETS:
        supported = ", ".join(sorted(SUPPORTED_PGTA_TARGETS))
        raise ValueError(f"Unsupported PGT-A target: {target}. Supported targets: {supported}.")
    if mode not in SUPPORTED_PGTA_MODES:
        supported_modes = ", ".join(sorted(SUPPORTED_PGTA_MODES))
        raise ValueError(f"Unsupported PGT-A mode: {mode}. Supported modes: {supported_modes}.")
    if mode == "resume" and target != "baseline_qc":
        raise ValueError("PGT-A resume is only supported for baseline_qc.")
    rerun_stage = str(params.get("rerun_stage") or "").strip()
    if mode == "rerun_stage":
        if target != "baseline_qc":
            raise ValueError("PGT-A rerun_stage is only supported for baseline_qc.")
        if rerun_stage not in SUPPORTED_PGTA_STAGES:
            supported = ", ".join(sorted(SUPPORTED_PGTA_STAGES))
            raise ValueError(f"Unsupported PGT-A rerun stage: {rerun_stage}. Supported stages: {supported}.")
    if not sample_sheet_path.is_file():
        raise FileNotFoundError(f"sample_sheet_path is not readable: {sample_sheet_path}")

    shared_root = shared_root.resolve()
    if not _is_relative_to(workdir, shared_root):
        raise ValueError(f"workdir must be under shared root: {shared_root}")
    if not _is_relative_to(sample_sheet_path, workdir):
        raise ValueError("sample_sheet_path must be under workdir.")

    return {
        "analysis_id": analysis_id,
        "pipeline": pipeline,
        "mode": mode,
        "sample_sheet_path": str(sample_sheet_path),
        "workdir": str(workdir),
        "email_to": conf.get("email_to"),
        "backend_event_url": conf.get("backend_event_url"),
        "params": {**params, "target": target},
    }


def read_selected_manifest(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"sample_id", "R1", "R2", "source_dir"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("selected manifest missing columns: " + ",".join(sorted(missing)))
        samples = []
        seen = set()
        for row in reader:
            sample_id = (row.get("sample_id") or "").strip()
            if not sample_id:
                raise ValueError("selected manifest contains empty sample_id.")
            if sample_id in seen:
                raise ValueError(f"selected manifest contains duplicate sample_id: {sample_id}")
            seen.add(sample_id)
            samples.append(
                {
                    "sample_id": sample_id,
                    "R1": (row.get("R1") or "").strip(),
                    "R2": (row.get("R2") or "").strip(),
                    "source_dir": (row.get("source_dir") or "").strip(),
                }
            )
    if not samples:
        raise ValueError("selected manifest has no samples.")
    return samples


def build_pgta_config(
    conf: dict[str, Any],
    *,
    pgta_pipeline_root: Path = DEFAULT_PGTA_PIPELINE_ROOT,
    pgta_data_root: Path = DEFAULT_PGTA_DATA_ROOT,
    samtools_bin: Path = DEFAULT_SAMTOOLS_BIN,
    samtools_library_path: str | None = DEFAULT_SAMTOOLS_LIBRARY_PATH,
    reference_genome: Path = DEFAULT_REFERENCE_GENOME,
) -> Path:
    workdir = Path(conf["workdir"])
    config_dir = workdir / "config"
    logs_dir = workdir / "logs"
    config_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    target = _target_from_conf(conf)
    samples = read_selected_manifest(conf["sample_sheet_path"])
    for sample in samples:
        _validate_sample_paths(sample, pgta_data_root)
    if target == "baseline_qc" and len(samples) < 2:
        raise ValueError("baseline_qc requires at least 2 selected samples for reference-style baseline comparison.")

    samtools_wrapper = _write_samtools_wrapper(workdir, samtools_bin, samtools_library_path)
    snakemake_config = _snakemake_config(
        workdir,
        samples,
        target=target,
        pgta_data_root=pgta_data_root,
        samtools_path=samtools_wrapper,
        reference_genome=reference_genome,
    )
    config_path = workdir / "config.yaml"
    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(snakemake_config, handle, sort_keys=False)

    runner_config = {
        "analysis_id": conf["analysis_id"],
        "target": target,
        "workdir": str(workdir),
        "pgta_pipeline_root": str(pgta_pipeline_root),
        "config_path": str(config_path),
        "samples": snakemake_config["samples"],
    }
    (config_dir / "pgta_run_config.json").write_text(
        json.dumps(runner_config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (config_dir / "pgta_metadata_config.json").write_text(
        json.dumps(runner_config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return config_path


def run_pgta_target(
    conf: dict[str, Any],
    *,
    snakemake_bin: Path = DEFAULT_SNAKEMAKE_BIN,
    pgta_pipeline_root: Path = DEFAULT_PGTA_PIPELINE_ROOT,
) -> Path:
    workdir = Path(conf["workdir"])
    target = _target_from_conf(conf)
    logs_dir = workdir / "logs"
    metadata_path = logs_dir / "run_metadata.tsv"
    baseline_qc_summary = workdir / "qc" / "baseline" / "baseline_qc_summary.tsv"
    if target == "dryrun_cnv":
        output_path = logs_dir / "snakemake.stdout.log"
    elif target == "baseline_qc":
        output_path = baseline_qc_summary
    else:
        output_path = metadata_path
    return _run_pgta_snakemake(
        conf,
        snakemake_bin=snakemake_bin,
        pgta_pipeline_root=pgta_pipeline_root,
        config_path=Path(conf["config_path"]),
        event_rule=target,
        output_path=output_path,
        dry_run=target == "dryrun_cnv",
        invalid_target=target == "invalid_target",
        run_python_preflight=target == "baseline_qc",
        resume_prepare=True,
    )


def run_pgta_stage(
    conf: dict[str, Any],
    stage: str,
    *,
    snakemake_bin: Path = DEFAULT_SNAKEMAKE_BIN,
    pgta_pipeline_root: Path = DEFAULT_PGTA_PIPELINE_ROOT,
) -> Path:
    stage = stage.strip()
    if stage not in SUPPORTED_PGTA_STAGES:
        supported = ", ".join(sorted(SUPPORTED_PGTA_STAGES))
        raise ValueError(f"Unsupported PGT-A stage: {stage}. Supported stages: {supported}.")
    if _target_from_conf(conf) != "baseline_qc":
        raise ValueError("PGT-A staged execution is only supported for target=baseline_qc.")

    workdir = Path(conf["workdir"])
    stage_config_path = _write_pgta_stage_config(base_config_path=Path(conf["config_path"]), workdir=workdir, stage=stage)
    if stage == "metadata":
        output_path = workdir / "logs" / "run_metadata.tsv"
    elif stage == "baseline_qc":
        output_path = workdir / "qc" / "baseline" / "baseline_qc_summary.tsv"
    else:
        output_path = workdir / "logs" / f"snakemake.{stage}.stdout.log"

    return _run_pgta_snakemake(
        conf,
        snakemake_bin=snakemake_bin,
        pgta_pipeline_root=pgta_pipeline_root,
        config_path=stage_config_path,
        event_rule=stage,
        output_path=output_path,
        log_suffix=stage,
        run_python_preflight=stage == "mapping",
        resume_prepare=stage == "mapping",
    )


def _run_pgta_snakemake(
    conf: dict[str, Any],
    *,
    snakemake_bin: Path,
    pgta_pipeline_root: Path,
    config_path: Path,
    event_rule: str,
    output_path: Path,
    log_suffix: str | None = None,
    dry_run: bool = False,
    invalid_target: bool = False,
    run_python_preflight: bool = False,
    resume_prepare: bool = True,
) -> Path:
    workdir = Path(conf["workdir"])
    mode = _mode_from_conf(conf)
    logs_dir = workdir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = logs_dir / (f"snakemake.{log_suffix}.stdout.log" if log_suffix else "snakemake.stdout.log")
    stderr_path = logs_dir / (f"snakemake.{log_suffix}.stderr.log" if log_suffix else "snakemake.stderr.log")
    command_path = logs_dir / (f"snakemake.{log_suffix}.command.txt" if log_suffix else "snakemake.command.txt")

    command = [
        str(snakemake_bin),
        "--snakefile",
        str(pgta_pipeline_root / "Snakefile"),
        "--cores",
        _snakemake_cores(),
        "--printshellcmds",
        "--configfile",
        str(config_path),
    ]
    env = _pgta_subprocess_env(workdir)
    if mode == "resume" and resume_prepare:
        unlock_command = [*command, "--unlock"]
        (logs_dir / "snakemake.unlock.command.txt").write_text(shlex.join(unlock_command) + "\n", encoding="utf-8")
        unlock_completed = subprocess.run(
            unlock_command,
            cwd=str(workdir),
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        (logs_dir / "snakemake.unlock.stdout.log").write_text(unlock_completed.stdout or "", encoding="utf-8")
        (logs_dir / "snakemake.unlock.stderr.log").write_text(unlock_completed.stderr or "", encoding="utf-8")
        if unlock_completed.returncode != 0:
            unlock_stderr = logs_dir / "snakemake.unlock.stderr.log"
            raise RuntimeError(f"PGT-A Snakemake unlock failed with exit code {unlock_completed.returncode}. See {unlock_stderr}")
        _cleanup_pgta_resume_temp_files(
            workdir=workdir,
            analysis_id=str(conf.get("analysis_id") or workdir.name),
            logs_dir=logs_dir,
        )
    if mode in {"resume", "rerun_stage"}:
        command.append("--rerun-incomplete")
    if run_python_preflight:
        _run_pgta_python_preflight(workdir=workdir, logs_dir=logs_dir, env=env)
    if dry_run:
        command.extend(["--dry-run", "--ignore-incomplete", "--rerun-triggers", "mtime"])
    if invalid_target:
        command.append(INVALID_SNAKEMAKE_TARGET)
    command_path.write_text(shlex.join(command) + "\n", encoding="utf-8")
    backend_event_url = conf.get("backend_event_url")
    emit_progress_event(
        analysis_id=str(conf.get("analysis_id") or workdir.name),
        workdir=workdir,
        backend_event_url=str(backend_event_url) if backend_event_url else None,
        event="pipeline_step_started",
        rule=event_rule,
        status="running",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        message=f"PGT-A {event_rule} started.",
    )
    completed = subprocess.run(command, cwd=str(workdir), text=True, capture_output=True, check=False, env=env)
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    parse_snakemake_output_for_events(
        analysis_id=str(conf.get("analysis_id") or workdir.name),
        workdir=workdir,
        backend_event_url=str(backend_event_url) if backend_event_url else None,
        stdout_text=completed.stdout or "",
        stderr_text=completed.stderr or "",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    if completed.returncode != 0:
        emit_progress_event(
            analysis_id=str(conf.get("analysis_id") or workdir.name),
            workdir=workdir,
            backend_event_url=str(backend_event_url) if backend_event_url else None,
            event="pipeline_step_failed",
            rule=event_rule,
            status="failed",
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            message=f"PGT-A {event_rule} Snakemake failed with exit code {completed.returncode}.",
            return_code=completed.returncode,
        )
        raise RuntimeError(f"PGT-A {event_rule} Snakemake failed with exit code {completed.returncode}. See {stderr_path}")
    emit_progress_event(
        analysis_id=str(conf.get("analysis_id") or workdir.name),
        workdir=workdir,
        backend_event_url=str(backend_event_url) if backend_event_url else None,
        event="pipeline_step_finished",
        rule=event_rule,
        status="success",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        message=f"PGT-A {event_rule} completed.",
        return_code=0,
    )
    return output_path


def _write_pgta_stage_config(*, base_config_path: Path, workdir: Path, stage: str) -> Path:
    base_config = yaml.safe_load(base_config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(base_config, dict):
        raise ValueError(f"Invalid PGT-A config content: {base_config_path}")
    stage_config = dict(base_config)
    pipeline = dict(stage_config.get("pipeline") or {})
    pipeline["mode"] = "build_ref"
    pipeline["targets"] = [stage]
    stage_config["pipeline"] = pipeline
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    stage_config_path = config_dir / f"pgta_stage_{stage}.yaml"
    stage_config_path.write_text(yaml.safe_dump(stage_config, sort_keys=False), encoding="utf-8")
    return stage_config_path


def run_pgta_metadata(
    conf: dict[str, Any],
    *,
    snakemake_bin: Path = DEFAULT_SNAKEMAKE_BIN,
    pgta_pipeline_root: Path = DEFAULT_PGTA_PIPELINE_ROOT,
) -> Path:
    return run_pgta_target(conf, snakemake_bin=snakemake_bin, pgta_pipeline_root=pgta_pipeline_root)


def collect_pgta_artifact(conf: dict[str, Any]) -> dict[str, str]:
    target = _target_from_conf(conf)
    if target == "dryrun_cnv":
        stdout_path = Path(conf["workdir"]) / "logs" / "snakemake.stdout.log"
        if not stdout_path.is_file():
            raise FileNotFoundError(f"dry-run stdout artifact was not generated: {stdout_path}")
        return {"type": "pgta_dryrun", "path": str(stdout_path), "label": "PGT-A CNV dry-run stdout"}
    if target == "baseline_qc":
        summary_path = Path(conf["workdir"]) / "qc" / "baseline" / "baseline_qc_summary.tsv"
        if not summary_path.is_file():
            raise FileNotFoundError(f"baseline QC summary artifact was not generated: {summary_path}")
        return {"type": "pgta_baseline_qc", "path": str(summary_path), "label": "PGT-A baseline QC summary"}

    metadata_path = Path(conf["workdir"]) / "logs" / "run_metadata.tsv"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"run metadata artifact was not generated: {metadata_path}")
    return {"type": "pgta_metadata", "path": str(metadata_path), "label": "PGT-A run metadata"}


def collect_metadata_artifact(conf: dict[str, Any]) -> dict[str, str]:
    return collect_pgta_artifact(conf)


def _snakemake_config(
    workdir: Path,
    samples: list[dict[str, str]],
    *,
    target: str,
    pgta_data_root: Path,
    samtools_path: Path,
    reference_genome: Path,
) -> dict[str, Any]:
    pipeline_mode = "predict"
    pipeline_targets = ["metadata"]
    build_reference: dict[str, Any] | None = None
    if target == "dryrun_cnv":
        pipeline_targets = ["cnv"]
    elif target == "baseline_qc":
        pipeline_mode = "build_ref"
        pipeline_targets = ["mapping", "metadata", "baseline_qc"]
        build_reference = {
            "enabled": True,
            "mode": "selected_samples",
            "groups": {"demo": [sample["sample_id"] for sample in samples]},
        }
    reference_root = pgta_data_root / "refactor_validation_20260419" / "results_build_ref_v2_mask_only" / "reference"
    wisecondorx_config: dict[str, Any] = {
        "binsize": 100000,
        "reference_model_root": "reference",
        "reference_output": "",
        "gender_reference_output": "reference/gender/result/ref_gender_best.npz",
        "common_reference_binsize_output": "reference/gender/common_best_binsize.txt",
        "use_chr_prefix": True,
        "cnv": {"enable": target == "dryrun_cnv"},
        "tuning": {"enable": False},
        "reference_prefilter": {"binsize": 100000, "max_iterations": 3},
    }
    if target == "dryrun_cnv":
        wisecondorx_config.update(
            {
                "reference_output_by_sex": {
                    "XX": str(reference_root / "XX" / "result" / "ref_xx_best.npz"),
                    "XY": str(reference_root / "XY" / "result" / "ref_xy_best.npz"),
                },
                "gender_reference_output": str(reference_root / "gender" / "result" / "ref_gender_best.npz"),
                "common_reference_binsize_output": str(reference_root / "gender" / "common_best_binsize.txt"),
            }
        )
    config = {
        "core": {
            "project_path": str(workdir),
            "reference_genome": str(reference_genome),
            "chromosome_list": [
                "chr1",
                "chr2",
                "chr3",
                "chr4",
                "chr5",
                "chr6",
                "chr7",
                "chr8",
                "chr9",
                "chr10",
                "chr11",
                "chr12",
                "chr13",
                "chr14",
                "chr15",
                "chr16",
                "chr17",
                "chr18",
                "chr19",
                "chr20",
                "chr21",
                "chr22",
                "chrX",
                "chrY",
            ],
            "wisecondorx": wisecondorx_config,
        },
        "pipeline": {"mode": pipeline_mode, "targets": pipeline_targets},
        "biosoft": {
            "fastp": "/biosoftware/bin/fastp",
            "bwa": "/biosoftware/bin/bwa",
            "samtools": str(samtools_path),
            "WisecondorX": "/biosoftware/miniconda/envs/wise_env/bin/WisecondorX",
            "python": "/biosoftware/miniconda/envs/snakemake_env/bin/python",
        },
        "samples": {sample["sample_id"]: {"R1": sample["R1"], "R2": sample["R2"]} for sample in samples},
    }
    if build_reference is not None:
        config["build_reference"] = build_reference
    return config


def _write_samtools_wrapper(workdir: Path, samtools_bin: Path, samtools_library_path: str | None) -> Path:
    bin_dir = workdir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "samtools"
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
    ]
    if samtools_library_path:
        lines.append(f'export LD_LIBRARY_PATH="{samtools_library_path}:${{LD_LIBRARY_PATH:-}}"')
    lines.append(f'exec {shlex.quote(str(samtools_bin))} "$@"')
    wrapper.write_text("\n".join(lines) + "\n", encoding="utf-8")
    wrapper.chmod(0o755)
    return wrapper


def _pgta_subprocess_env(workdir: Path) -> dict[str, str]:
    cache_dir = workdir / "tmp" / "xdg-cache"
    matplotlib_dir = workdir / "tmp" / "matplotlib"
    cache_dir.mkdir(parents=True, exist_ok=True)
    matplotlib_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["XDG_CACHE_HOME"] = str(cache_dir)
    env["MPLCONFIGDIR"] = str(matplotlib_dir)

    env["LD_LIBRARY_PATH"] = str(DEFAULT_PGTA_CONDA_LIB)
    if DEFAULT_PGTA_LIBSTDCXX.exists():
        env["LD_PRELOAD"] = str(DEFAULT_PGTA_LIBSTDCXX)
    else:
        env.pop("LD_PRELOAD", None)
    return env


def _run_pgta_python_preflight(*, workdir: Path, logs_dir: Path, env: dict[str, str]) -> Path:
    preflight_log = logs_dir / "pgta.python_preflight.log"
    import_lines = "\n".join(
        [
            "import importlib",
            f"for name in {PGTA_BASELINE_PREFLIGHT_IMPORTS!r}:",
            "    module = importlib.import_module(name)",
            "    print(f'{name}\\t{getattr(module, \"__version__\", \"unknown\")}')",
        ]
    )
    command = [str(DEFAULT_PGTA_PYTHON_BIN), "-c", import_lines]
    completed = subprocess.run(
        command,
        cwd=str(workdir),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    header = "\n".join(
        [
            "PGT-A Python preflight",
            f"command\t{shlex.join(command)}",
            f"LD_LIBRARY_PATH\t{env.get('LD_LIBRARY_PATH', '')}",
            f"LD_PRELOAD\t{env.get('LD_PRELOAD', '')}",
            f"MPLCONFIGDIR\t{env.get('MPLCONFIGDIR', '')}",
            f"XDG_CACHE_HOME\t{env.get('XDG_CACHE_HOME', '')}",
            "--- output ---",
        ]
    )
    preflight_log.write_text(
        header + "\n" + (completed.stdout or "") + (completed.stderr or ""),
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"PGT-A Python preflight failed with exit code {completed.returncode}. See {preflight_log}")
    return preflight_log


def _cleanup_pgta_resume_temp_files(*, workdir: Path, analysis_id: str, logs_dir: Path) -> Path:
    _validate_resume_cleanup_workdir(workdir=workdir, analysis_id=analysis_id)
    cleanup_path = logs_dir / "pgta.resume.cleanup.tsv"
    lines = ["deleted_at\tpath\tsize_bytes"]
    mapping_dir = (workdir / "mapping").resolve()
    if mapping_dir.is_dir():
        for path in sorted(mapping_dir.glob("*.sorted.bam.tmp.*.bam")):
            resolved = path.resolve()
            if resolved.parent != mapping_dir or not _is_relative_to(resolved, mapping_dir):
                raise ValueError(f"Refusing to clean path outside PGT-A mapping dir: {resolved}")
            size_bytes = path.lstat().st_size
            path.unlink()
            deleted_at = datetime.now(timezone.utc).isoformat()
            lines.append(f"{deleted_at}\t{resolved}\t{size_bytes}")
    cleanup_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cleanup_path


def _validate_resume_cleanup_workdir(*, workdir: Path, analysis_id: str) -> None:
    resolved = workdir.resolve()
    normalized_analysis_id = analysis_id.strip()
    if not normalized_analysis_id:
        raise ValueError("analysis_id is required for PGT-A resume cleanup.")
    if resolved.name != normalized_analysis_id or resolved.parent.name != "runs":
        raise ValueError(f"Refusing PGT-A resume cleanup outside run-local workdir: {resolved}")


def _target_from_conf(conf: dict[str, Any]) -> str:
    params = conf.get("params") or {}
    target = str(params.get("target") or "metadata").strip()
    if target not in SUPPORTED_PGTA_TARGETS:
        supported = ", ".join(sorted(SUPPORTED_PGTA_TARGETS))
        raise ValueError(f"Unsupported PGT-A target: {target}. Supported targets: {supported}.")
    return target


def _mode_from_conf(conf: dict[str, Any]) -> str:
    mode = str(conf.get("mode") or "new").strip()
    if mode not in SUPPORTED_PGTA_MODES:
        supported = ", ".join(sorted(SUPPORTED_PGTA_MODES))
        raise ValueError(f"Unsupported PGT-A mode: {mode}. Supported modes: {supported}.")
    if mode == "resume" and _target_from_conf(conf) != "baseline_qc":
        raise ValueError("PGT-A resume is only supported for baseline_qc.")
    if mode == "rerun_stage":
        if _target_from_conf(conf) != "baseline_qc":
            raise ValueError("PGT-A rerun_stage is only supported for baseline_qc.")
        params = conf.get("params") or {}
        rerun_stage = str(params.get("rerun_stage") or "").strip()
        if rerun_stage not in SUPPORTED_PGTA_STAGES:
            supported = ", ".join(sorted(SUPPORTED_PGTA_STAGES))
            raise ValueError(f"Unsupported PGT-A rerun stage: {rerun_stage}. Supported stages: {supported}.")
    return mode


def _snakemake_cores() -> str:
    value = str(os.getenv("PGTA_SNAKEMAKE_CORES", DEFAULT_SNAKEMAKE_CORES)).strip()
    try:
        cores = int(value)
    except ValueError as exc:
        raise ValueError(f"PGTA_SNAKEMAKE_CORES must be a positive integer, got: {value}") from exc
    if cores < 1:
        raise ValueError(f"PGTA_SNAKEMAKE_CORES must be a positive integer, got: {value}")
    return str(cores)


def _validate_sample_paths(sample: dict[str, str], pgta_data_root: Path) -> None:
    data_root = pgta_data_root.resolve()
    for key in ("R1", "R2", "source_dir"):
        path = Path(sample[key]).resolve()
        if not _is_relative_to(path, data_root):
            raise ValueError(f"{key} for sample {sample['sample_id']} is outside PGT-A data root.")


def _is_relative_to(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)
