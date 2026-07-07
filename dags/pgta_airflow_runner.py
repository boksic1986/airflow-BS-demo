from __future__ import annotations

from collections import Counter
import csv
import json
import logging
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any

from pgta_metadata_runner import (
    DEFAULT_PGTA_PIPELINE_ROOT,
    DEFAULT_SHARED_ROOT,
    build_pgta_config,
    collect_metadata_artifact,
    _snakemake_cores,
)


LOGGER = logging.getLogger(__name__)

DEFAULT_SNAKEMAKE9_BIN = Path(
    os.getenv("PGTA_SNAKEMAKE9_BIN", "/biosoftware/miniconda/envs/snakemake9_env/bin/snakemake")
)
DEFAULT_DAGS_ROOT = Path(os.getenv("AIRFLOW_DAGS_ROOT", "/opt/airflow/dags"))
EVENTS_RELATIVE_PATH = Path("logs/events/snakemake_events.jsonl")


def validate_pgta_airflow_conf(
    conf: dict[str, Any],
    *,
    shared_root: Path = DEFAULT_SHARED_ROOT,
) -> dict[str, Any]:
    analysis_id = str(conf.get("analysis_id") or "").strip()
    target = str(conf.get("target") or "").strip()
    sample_sheet_path = Path(str(conf.get("sample_sheet_path") or "")).resolve()
    workdir = Path(str(conf.get("workdir") or "")).resolve()

    if not analysis_id:
        raise ValueError("analysis_id is required.")
    if target != "metadata":
        raise ValueError("Only target=metadata is supported by bio_pgta_airflow v1.")
    if not sample_sheet_path.is_file():
        raise FileNotFoundError(f"sample_sheet_path is not readable: {sample_sheet_path}")

    shared_root = shared_root.resolve()
    if not _is_relative_to(workdir, shared_root):
        raise ValueError(f"workdir must be under shared root: {shared_root}")
    if not _is_relative_to(sample_sheet_path, workdir):
        raise ValueError("sample_sheet_path must be under workdir.")

    return {
        "analysis_id": analysis_id,
        "pipeline": "pgta",
        "mode": conf.get("mode") or "airflow_only",
        "sample_sheet_path": str(sample_sheet_path),
        "workdir": str(workdir),
        "email_to": conf.get("email_to"),
        "target": target,
        "params": {
            "target": target,
            "input_mode": "manifest_path",
            "airflow_only": True,
        },
        **_optional_logger_backend_settings(conf),
    }


def build_pgta_airflow_config(conf: dict[str, Any]) -> Path:
    return build_pgta_config(conf)


def run_snakemake9_with_logger(
    conf: dict[str, Any],
    *,
    snakemake_bin: Path = DEFAULT_SNAKEMAKE9_BIN,
    pgta_pipeline_root: Path = DEFAULT_PGTA_PIPELINE_ROOT,
    dags_root: Path = DEFAULT_DAGS_ROOT,
) -> Path:
    workdir = Path(conf["workdir"])
    logs_dir = workdir / "logs"
    events_path = workdir / EVENTS_RELATIVE_PATH
    logs_dir.mkdir(parents=True, exist_ok=True)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = workdir / "tmp" / "xdg-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = logs_dir / "snakemake.stdout.log"
    stderr_path = logs_dir / "snakemake.stderr.log"

    command = [
        str(snakemake_bin),
        "--snakefile",
        str(pgta_pipeline_root / "Snakefile"),
        "--cores",
        _snakemake_cores(),
        "--printshellcmds",
        "--show-failed-logs",
        "--logger",
        "airflow-demo",
        "--logger-airflow-demo-analysis-id",
        conf["analysis_id"],
        "--logger-airflow-demo-workdir",
        str(workdir),
        "--logger-airflow-demo-events-path",
        str(events_path),
    ]
    if conf.get("backend_event_url"):
        command.extend(["--logger-airflow-demo-backend-event-url", str(conf["backend_event_url"])])
    if conf.get("post_timeout_seconds") is not None:
        command.extend(["--logger-airflow-demo-post-timeout-seconds", str(conf["post_timeout_seconds"])])
    (logs_dir / "snakemake.command.txt").write_text(shlex.join(command) + "\n", encoding="utf-8")
    completed = subprocess.run(
        command,
        cwd=str(workdir),
        text=True,
        capture_output=True,
        check=False,
        env=_snakemake_env(dags_root, cache_dir),
    )
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"PGT-A Snakemake 9 failed with exit code {completed.returncode}. See {stderr_path}")
    return events_path


def collect_snakemake_events(conf: dict[str, Any]) -> dict[str, Any]:
    workdir = Path(conf["workdir"])
    events_path = workdir / EVENTS_RELATIVE_PATH
    summary_path = workdir / "logs" / "events" / "snakemake_rule_summary.tsv"
    if not events_path.is_file():
        raise FileNotFoundError(f"Snakemake logger events were not generated: {events_path}")

    events = _read_events(events_path)
    if not events:
        raise ValueError(f"Snakemake logger events file is empty: {events_path}")

    status_counts = Counter(str(event.get("status") or "unknown") for event in events)
    failed_jobs = [
        _event_for_summary(event)
        for event in events
        if str(event.get("status") or "").lower() in {"failed", "error"}
    ]
    _write_summary(summary_path, events)
    _log_airflow_summary(events, status_counts, failed_jobs, summary_path)

    return {
        "analysis_id": conf["analysis_id"],
        "events_path": str(events_path),
        "summary_path": str(summary_path),
        "event_count": len(events),
        "status_counts": dict(sorted(status_counts.items())),
        "failed_jobs": failed_jobs,
    }


def _snakemake_env(dags_root: Path, cache_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    paths = [str(dags_root)]
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    env["XDG_CACHE_HOME"] = str(cache_dir)
    return env


def _optional_logger_backend_settings(conf: dict[str, Any]) -> dict[str, Any]:
    settings: dict[str, Any] = {}
    backend_event_url = str(conf.get("backend_event_url") or "").strip()
    if backend_event_url:
        settings["backend_event_url"] = backend_event_url
    if conf.get("post_timeout_seconds") is not None:
        settings["post_timeout_seconds"] = float(conf["post_timeout_seconds"])
    return settings


def _read_events(events_path: Path) -> list[dict[str, Any]]:
    events = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def _write_summary(summary_path: Path, events: list[dict[str, Any]]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            delimiter="\t",
            fieldnames=["rule", "status", "sample_id", "snakemake_jobid", "event", "message"],
            extrasaction="ignore",
        )
        writer.writeheader()
        for event in events:
            writer.writerow(_event_for_summary(event))


def _event_for_summary(event: dict[str, Any]) -> dict[str, str]:
    return {
        "rule": str(event.get("rule") or ""),
        "status": str(event.get("status") or "unknown"),
        "sample_id": str(event.get("sample_id") or ""),
        "snakemake_jobid": str(event.get("snakemake_jobid") or ""),
        "event": str(event.get("event") or ""),
        "message": str(event.get("message") or ""),
    }


def _log_airflow_summary(
    events: list[dict[str, Any]],
    status_counts: Counter[str],
    failed_jobs: list[dict[str, str]],
    summary_path: Path,
) -> None:
    LOGGER.info("Snakemake event count: %s", len(events))
    LOGGER.info("Snakemake status counts: %s", dict(sorted(status_counts.items())))
    LOGGER.info("Snakemake rule summary path: %s", summary_path)
    for event in events:
        row = _event_for_summary(event)
        LOGGER.info(
            "snakemake rule=%s status=%s sample=%s jobid=%s event=%s message=%s",
            row["rule"],
            row["status"],
            row["sample_id"],
            row["snakemake_jobid"],
            row["event"],
            row["message"],
        )
    if failed_jobs:
        LOGGER.error("Snakemake failed jobs: %s", failed_jobs)


def _is_relative_to(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)
