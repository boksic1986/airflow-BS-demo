from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from common.paths import count_nonempty_lines, ensure_directory, ensure_under_root
from common.subprocess_utils import run_command_to_logs


DEFAULT_SHARED_ROOT = Path(os.getenv("CONTAINER_SHARED_ROOT", "/data/airflow-demo"))
DEFAULT_AIRFLOW_ROOT = Path(os.getenv("AIRFLOW_HOME", "/opt/airflow"))
DEFAULT_PIPELINES_ROOT = Path(os.getenv("AIRFLOW_PIPELINES_ROOT", "/opt/airflow/pipelines"))
DEFAULT_PROFILES_ROOT = Path(os.getenv("AIRFLOW_PROFILES_ROOT", "/opt/airflow/profiles"))
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_WES_TARGETS = {"final_summary"}
SUPPORTED_WES_MODES = {"new", "resume", "rerun_rule"}
SUPPORTED_WES_RERUN_RULES = {"fastp", "bwa_mem", "markdup", "final_summary"}
WES_SAMPLE_RULES = {"fastp", "bwa_mem", "markdup"}
WES_MOCK_SAMPLES = {"S001", "S002"}
MAX_WES_MOCK_JOBS = 2


def validate_wes_conf(
    conf: dict[str, Any],
    *,
    shared_root: Path = DEFAULT_SHARED_ROOT,
) -> dict[str, Any]:
    analysis_id = str(conf.get("analysis_id") or "").strip()
    pipeline = str(conf.get("pipeline") or "").strip()
    mode = str(conf.get("mode") or "new").strip()
    workdir = Path(str(conf.get("workdir") or "")).resolve()
    params = dict(conf.get("params") or {})
    target = str(params.get("target") or "final_summary").strip()
    max_jobs = int(params.get("max_jobs") or MAX_WES_MOCK_JOBS)

    if not analysis_id:
        raise ValueError("analysis_id is required.")
    if pipeline != "wes_qsub":
        raise ValueError("pipeline must be wes_qsub.")
    if mode not in SUPPORTED_WES_MODES:
        supported_modes = ", ".join(sorted(SUPPORTED_WES_MODES))
        raise ValueError(f"Unsupported WES mode: {mode}. Supported modes: {supported_modes}.")
    if target not in SUPPORTED_WES_TARGETS:
        supported = ", ".join(sorted(SUPPORTED_WES_TARGETS))
        raise ValueError(f"Unsupported WES target: {target}. Supported targets: {supported}.")
    if max_jobs < 1 or max_jobs > MAX_WES_MOCK_JOBS:
        raise ValueError(f"max_jobs must be between 1 and {MAX_WES_MOCK_JOBS}.")
    if mode == "rerun_rule":
        _validate_rerun_rule_params(params)

    shared_root = shared_root.resolve()
    ensure_under_root(workdir, shared_root, label="workdir")

    return {
        "analysis_id": analysis_id,
        "pipeline": pipeline,
        "mode": mode,
        "workdir": str(workdir),
        "backend_event_url": conf.get("backend_event_url"),
        "params": {**params, "target": target, "max_jobs": max_jobs},
    }


def prepare_wes_config(
    conf: dict[str, Any],
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    pipelines_root: Path = DEFAULT_PIPELINES_ROOT,
) -> Path:
    workdir = Path(conf["workdir"])
    config_dir = ensure_directory(workdir / "config")
    ensure_directory(workdir / "logs")
    ensure_directory(workdir / "reports")
    ensure_directory(workdir / "tmp")

    source_config = repo_root / "pipelines" / "wes" / "config" / "mock_config.yaml"
    config = yaml.safe_load(source_config.read_text(encoding="utf-8"))
    config["analysis_id"] = conf["analysis_id"]
    config["workdir"] = str(workdir)
    config["backend_event_url"] = conf.get("backend_event_url")
    config["samples"] = _containerized_samples(config.get("samples") or {}, pipelines_root=pipelines_root)

    config_path = config_dir / "wes_mock_config.yaml"
    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)

    request_path = config_dir / "wes_airflow_request.json"
    request_path.write_text(json.dumps(conf, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return config_path


def build_snakemake_command(
    config_path: Path,
    *,
    mode: str = "new",
    rule: str | None = None,
    sample_id: str | None = None,
    workdir: Path | None = None,
    pipelines_root: Path = DEFAULT_PIPELINES_ROOT,
    profiles_root: Path = DEFAULT_PROFILES_ROOT,
) -> list[str]:
    command = [
        "snakemake",
        "--snakefile",
        str(pipelines_root / "wes" / "workflow" / "Snakefile"),
        "--configfile",
        str(config_path),
        "--profile",
        str(profiles_root / "qsub"),
    ]
    if mode == "rerun_rule":
        if workdir is None:
            raise ValueError("workdir is required for rerun_rule command construction.")
        target = _rerun_target_path(workdir=workdir, rule=str(rule), sample_id=sample_id)
        command.extend(["--forcerun", str(rule), target])
    return command


def run_wes_qsub(
    conf: dict[str, Any],
    *,
    airflow_root: Path = DEFAULT_AIRFLOW_ROOT,
    pipelines_root: Path = DEFAULT_PIPELINES_ROOT,
    profiles_root: Path = DEFAULT_PROFILES_ROOT,
) -> dict[str, str | int]:
    workdir = Path(conf["workdir"])
    logs_dir = ensure_directory(workdir / "logs")
    snakemake_cache_dir = ensure_directory(workdir / "tmp" / "xdg-cache")
    config_path = Path(conf["config_path"])
    params = dict(conf.get("params") or {})
    command = build_snakemake_command(
        config_path,
        mode=str(conf.get("mode") or "new"),
        rule=params.get("rule"),
        sample_id=params.get("sample_id"),
        workdir=workdir,
        pipelines_root=pipelines_root,
        profiles_root=profiles_root,
    )
    env = os.environ.copy()
    env.setdefault("AIRFLOW_DEMO_QSUB_MODE", "mock")
    env.setdefault("AIRFLOW_DEMO_QSUB_PYTHON", "python")
    env["XDG_CACHE_HOME"] = str(snakemake_cache_dir)
    return run_command_to_logs(
        command,
        cwd=airflow_root,
        stdout_path=logs_dir / "snakemake.stdout.log",
        stderr_path=logs_dir / "snakemake.stderr.log",
        env=env,
    )


def collect_wes_artifacts(conf: dict[str, Any]) -> dict[str, str | int]:
    workdir = Path(conf["workdir"])
    summary_path = workdir / "reports" / "final_summary.tsv"
    events_path = workdir / "logs" / "events" / "snakemake_events.jsonl"
    qsub_log_count = len(list((workdir / "logs" / "qsub").glob("*.[oe]")))
    if not summary_path.is_file():
        raise FileNotFoundError(f"WES final summary artifact was not generated: {summary_path}")
    return {
        "type": "wes_mock_summary",
        "path": str(summary_path),
        "label": "WES mock final summary",
        "event_path": str(events_path),
        "event_count": count_nonempty_lines(events_path),
        "qsub_log_count": qsub_log_count,
    }


def _containerized_samples(samples: dict[str, Any], *, pipelines_root: Path) -> dict[str, dict[str, str]]:
    converted: dict[str, dict[str, str]] = {}
    for sample_id, sample in samples.items():
        input_path = Path(str(sample["input"]))
        if input_path.is_absolute():
            container_input = input_path
        elif input_path.parts and input_path.parts[0] == "pipelines":
            container_input = pipelines_root.joinpath(*input_path.parts[1:])
        else:
            container_input = pipelines_root / input_path
        converted[sample_id] = {"input": str(container_input)}
    return converted


def _validate_rerun_rule_params(params: dict[str, Any]) -> None:
    rule = str(params.get("rule") or "").strip()
    sample_id = str(params.get("sample_id") or "").strip() or None
    if rule not in SUPPORTED_WES_RERUN_RULES:
        supported = ", ".join(sorted(SUPPORTED_WES_RERUN_RULES))
        raise ValueError(f"Unsupported WES rerun rule: {rule}. Supported rules: {supported}.")
    if rule in WES_SAMPLE_RULES and sample_id not in WES_MOCK_SAMPLES:
        supported_samples = ", ".join(sorted(WES_MOCK_SAMPLES))
        raise ValueError(f"sample_id is required for rule {rule}; supported samples: {supported_samples}.")
    if rule == "final_summary" and sample_id:
        raise ValueError("sample_id is not supported for final_summary rerun.")


def _rerun_target_path(*, workdir: Path, rule: str, sample_id: str | None) -> str:
    if rule == "fastp":
        return str(workdir / "fastp" / f"{sample_id}.clean.txt")
    if rule == "bwa_mem":
        return str(workdir / "mapping" / f"{sample_id}.bam")
    if rule == "markdup":
        return str(workdir / "markdup" / f"{sample_id}.markdup.bam")
    if rule == "final_summary":
        return str(workdir / "reports" / "final_summary.tsv")
    raise ValueError(f"Unsupported WES rerun rule: {rule}.")
