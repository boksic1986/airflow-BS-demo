from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
from typing import Any

import yaml


DEFAULT_SHARED_ROOT = Path(os.getenv("CONTAINER_SHARED_ROOT", "/data/airflow-demo"))
DEFAULT_PGTA_PIPELINE_ROOT = Path(os.getenv("PGTA_CONTAINER_ROOT", "/opt/pipelines/PGT_A"))
DEFAULT_PGTA_DATA_ROOT = Path(os.getenv("PGTA_CONTAINER_DATA_ROOT", "/data/project/CNV/PGT-A"))
DEFAULT_SNAKEMAKE_BIN = Path(os.getenv("PGTA_SNAKEMAKE_BIN", "/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"))
SUPPORTED_PGTA_TARGETS = {"metadata", "dryrun_cnv", "invalid_target"}
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

    if not analysis_id:
        raise ValueError("analysis_id is required.")
    if pipeline != "pgta":
        raise ValueError("pipeline must be pgta.")
    if target not in SUPPORTED_PGTA_TARGETS:
        supported = ", ".join(sorted(SUPPORTED_PGTA_TARGETS))
        raise ValueError(f"Unsupported PGT-A target: {target}. Supported targets: {supported}.")
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
        "mode": conf.get("mode") or "new",
        "sample_sheet_path": str(sample_sheet_path),
        "workdir": str(workdir),
        "email_to": conf.get("email_to"),
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
) -> Path:
    workdir = Path(conf["workdir"])
    config_dir = workdir / "config"
    logs_dir = workdir / "logs"
    config_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    samples = read_selected_manifest(conf["sample_sheet_path"])
    for sample in samples:
        _validate_sample_paths(sample, pgta_data_root)

    target = _target_from_conf(conf)
    snakemake_config = _snakemake_config(workdir, samples, target=target, pgta_data_root=pgta_data_root)
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
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = logs_dir / "snakemake.stdout.log"
    stderr_path = logs_dir / "snakemake.stderr.log"
    metadata_path = logs_dir / "run_metadata.tsv"

    command = [
        str(snakemake_bin),
        "--snakefile",
        str(pgta_pipeline_root / "Snakefile"),
        "--cores",
        "1",
        "--printshellcmds",
        "--configfile",
        str(conf["config_path"]),
    ]
    if target == "dryrun_cnv":
        command.extend(["--dry-run", "--ignore-incomplete", "--rerun-triggers", "mtime"])
    if target == "invalid_target":
        command.append(INVALID_SNAKEMAKE_TARGET)
    completed = subprocess.run(command, cwd=str(workdir), text=True, capture_output=True, check=False)
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"PGT-A {target} Snakemake failed with exit code {completed.returncode}. See {stderr_path}")
    if target == "dryrun_cnv":
        return stdout_path
    return metadata_path


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
) -> dict[str, Any]:
    pipeline_target = "cnv" if target == "dryrun_cnv" else "metadata"
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
    return {
        "core": {
            "project_path": str(workdir),
            "reference_genome": "/data/Database/index/hg19/hg19.fa",
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
        "pipeline": {"mode": "predict", "targets": [pipeline_target]},
        "biosoft": {
            "fastp": "/biosoftware/bin/fastp",
            "bwa": "/biosoftware/bin/bwa",
            "samtools": "/biosoftware/bin/samtools",
            "WisecondorX": "/biosoftware/miniconda/envs/wise_env/bin/WisecondorX",
            "python": "/biosoftware/miniconda/envs/snakemake_env/bin/python",
        },
        "samples": {sample["sample_id"]: {"R1": sample["R1"], "R2": sample["R2"]} for sample in samples},
    }


def _target_from_conf(conf: dict[str, Any]) -> str:
    params = conf.get("params") or {}
    target = str(params.get("target") or "metadata").strip()
    if target not in SUPPORTED_PGTA_TARGETS:
        supported = ", ".join(sorted(SUPPORTED_PGTA_TARGETS))
        raise ValueError(f"Unsupported PGT-A target: {target}. Supported targets: {supported}.")
    return target


def _validate_sample_paths(sample: dict[str, str], pgta_data_root: Path) -> None:
    data_root = pgta_data_root.resolve()
    for key in ("R1", "R2", "source_dir"):
        path = Path(sample[key]).resolve()
        if not _is_relative_to(path, data_root):
            raise ValueError(f"{key} for sample {sample['sample_id']} is outside PGT-A data root.")


def _is_relative_to(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)
