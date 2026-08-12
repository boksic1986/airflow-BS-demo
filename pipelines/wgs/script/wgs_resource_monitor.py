#!/usr/bin/env python3
"""Monitor one local WGS Snakemake run and summarize Snakemake benchmarks."""

import argparse
import csv
import datetime as dt
import json
import os
import re
import signal
import sys
import time
from pathlib import Path

import psutil


BENCHMARK_COLUMNS = (
    "s",
    "h:m:s",
    "max_rss",
    "max_vms",
    "max_uss",
    "max_pss",
    "io_in",
    "io_out",
    "mean_load",
    "cpu_time",
)
PROCESS_COLUMNS = (
    "timestamp",
    "root_pid",
    "pid",
    "ppid",
    "process",
    "cpu_percent",
    "rss_bytes",
    "read_bytes",
    "write_bytes",
    "rule",
    "sample",
)
NODE_COLUMNS = (
    "timestamp",
    "root_pid",
    "cpu_percent",
    "load1",
    "load5",
    "load15",
    "memory_total_bytes",
    "memory_available_bytes",
    "memory_used_bytes",
    "swap_used_bytes",
    "disk_read_bytes",
    "disk_write_bytes",
    "process_count",
    "active_rules",
    "active_samples",
)
KNOWN_RULES = (
    "cleanFastq",
    "mapping",
    "Dedup",
    "QualCal",
    "Haplotyper",
    "Sam2Cram",
    "GVCFtyper",
)
SAMPLE_PATTERN = re.compile(r"(WGS\d{7,}(?:-WGS)?|[A-Za-z0-9_.-]+-WGS)")
STOP_REQUESTED = False


def _handle_stop(_signum, _frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_command(process):
    try:
        return " ".join(process.cmdline())
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
        return ""


def _detect_rule_and_sample(command):
    rule = ""
    for candidate in KNOWN_RULES:
        if candidate.lower() in command.lower():
            rule = candidate
            break
    match = SAMPLE_PATTERN.search(command)
    return rule, match.group(1) if match else ""


def _benchmark_files(analysis_dir, attempt):
    root = Path(analysis_dir) / "logs" / "benchmarks" / attempt
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.tsv") if path.is_file())


def load_benchmark_records(analysis_dir, attempt, rule_threads):
    """Load Snakemake benchmark TSVs and calculate normalized CPU metrics."""
    records = []
    benchmark_root = Path(analysis_dir) / "logs" / "benchmarks" / attempt
    for path in _benchmark_files(analysis_dir, attempt):
        relative = path.relative_to(benchmark_root)
        if len(relative.parts) < 2:
            continue
        rule = relative.parts[0]
        sample = path.stem
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                wall_seconds = _number(row.get("s"))
                cpu_seconds = _number(row.get("cpu_time"))
                threads = int(rule_threads.get(rule, 1))
                requested_core_hours = threads * wall_seconds / 3600.0
                actual_cpu_hours = cpu_seconds / 3600.0
                efficiency = (
                    actual_cpu_hours / requested_core_hours
                    if requested_core_hours > 0
                    else 0.0
                )
                records.append(
                    {
                        "attempt": attempt,
                        "rule": rule,
                        "sample": sample,
                        "threads": threads,
                        "wall_seconds": wall_seconds,
                        "wall_hms": row.get("h:m:s", ""),
                        "cpu_seconds": cpu_seconds,
                        "requested_core_hours": requested_core_hours,
                        "actual_cpu_hours": actual_cpu_hours,
                        "cpu_efficiency": efficiency,
                        "mean_load": _number(row.get("mean_load")),
                        "max_rss_mb": _number(row.get("max_rss")),
                        "max_vms_mb": _number(row.get("max_vms")),
                        "max_uss_mb": _number(row.get("max_uss")),
                        "max_pss_mb": _number(row.get("max_pss")),
                        "io_read_mb": _number(row.get("io_in")),
                        "io_write_mb": _number(row.get("io_out")),
                        "benchmark_path": str(path),
                    }
                )
    return records


def _write_tsv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def _process_tree(root_pid):
    try:
        root = psutil.Process(root_pid)
        return [root] + root.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def monitor(args):
    output_dir = Path(args.analysis_dir) / "logs" / "performance" / args.attempt
    output_dir.mkdir(parents=True, exist_ok=True)
    node_path = output_dir / "node_resources.tsv"
    process_path = output_dir / "process_resources.tsv"
    metadata_path = output_dir / "monitor_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "analysis_dir": str(Path(args.analysis_dir).resolve()),
                "attempt": args.attempt,
                "performance_profile": args.profile,
                "root_pid": args.root_pid,
                "interval_seconds": args.interval,
                "monitor_pid": os.getpid(),
                "started_at": dt.datetime.now().astimezone().isoformat(),
                "hostname": os.uname().nodename,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    psutil.cpu_percent(interval=None)
    known_processes = {}
    with node_path.open("w", encoding="utf-8", newline="") as node_handle, process_path.open(
        "w", encoding="utf-8", newline=""
    ) as process_handle:
        node_writer = csv.DictWriter(node_handle, fieldnames=NODE_COLUMNS, delimiter="\t")
        process_writer = csv.DictWriter(
            process_handle, fieldnames=PROCESS_COLUMNS, delimiter="\t"
        )
        node_writer.writeheader()
        process_writer.writeheader()
        while not STOP_REQUESTED:
            timestamp = dt.datetime.now().astimezone().isoformat()
            processes = _process_tree(args.root_pid)
            active_rules = set()
            active_samples = set()
            for process in processes:
                if process.pid not in known_processes:
                    try:
                        process.cpu_percent(interval=None)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                    known_processes[process.pid] = process
                command = _safe_command(process)
                rule, sample = _detect_rule_and_sample(command)
                if rule:
                    active_rules.add(rule)
                if sample:
                    active_samples.add(sample)
                try:
                    memory = process.memory_info()
                    io_counters = process.io_counters()
                    process_writer.writerow(
                        {
                            "timestamp": timestamp,
                            "root_pid": args.root_pid,
                            "pid": process.pid,
                            "ppid": process.ppid(),
                            "process": process.name(),
                            "cpu_percent": process.cpu_percent(interval=None),
                            "rss_bytes": memory.rss,
                            "read_bytes": io_counters.read_bytes,
                            "write_bytes": io_counters.write_bytes,
                            "rule": rule,
                            "sample": sample,
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            disk = psutil.disk_io_counters()
            load1, load5, load15 = os.getloadavg()
            node_writer.writerow(
                {
                    "timestamp": timestamp,
                    "root_pid": args.root_pid,
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "load1": load1,
                    "load5": load5,
                    "load15": load15,
                    "memory_total_bytes": memory.total,
                    "memory_available_bytes": memory.available,
                    "memory_used_bytes": memory.used,
                    "swap_used_bytes": swap.used,
                    "disk_read_bytes": disk.read_bytes if disk else 0,
                    "disk_write_bytes": disk.write_bytes if disk else 0,
                    "process_count": len(processes),
                    "active_rules": ",".join(sorted(active_rules)),
                    "active_samples": ",".join(sorted(active_samples)),
                }
            )
            node_handle.flush()
            process_handle.flush()
            if not processes:
                break
            deadline = time.monotonic() + args.interval
            while not STOP_REQUESTED and time.monotonic() < deadline:
                time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
    return 0


def _load_yaml_config(config_path):
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML is required for benchmark summarization")
    with Path(config_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def summarize(args):
    config = _load_yaml_config(args.config)
    performance = config.get("performance", {})
    rule_threads = performance.get("rule_threads", {})
    records = load_benchmark_records(args.analysis_dir, args.attempt, rule_threads)
    output_dir = Path(args.analysis_dir) / "logs" / "performance" / args.attempt
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "benchmark_summary.tsv"
    fieldnames = [
        "attempt",
        "rule",
        "sample",
        "threads",
        "wall_seconds",
        "wall_hms",
        "cpu_seconds",
        "requested_core_hours",
        "actual_cpu_hours",
        "cpu_efficiency",
        "mean_load",
        "max_rss_mb",
        "max_vms_mb",
        "max_uss_mb",
        "max_pss_mb",
        "io_read_mb",
        "io_write_mb",
        "benchmark_path",
    ]
    _write_tsv(summary_path, fieldnames, records)
    totals = {
        "analysis_dir": str(Path(args.analysis_dir).resolve()),
        "attempt": args.attempt,
        "performance_profile": config.get("execution", {}).get(
            "performance_profile", "standard60"
        ),
        "benchmark_count": len(records),
        "requested_core_hours": sum(
            record["requested_core_hours"] for record in records
        ),
        "actual_cpu_hours": sum(record["actual_cpu_hours"] for record in records),
        "wall_hours_sum": sum(record["wall_seconds"] for record in records) / 3600.0,
        "io_read_mb": sum(record["io_read_mb"] for record in records),
        "io_write_mb": sum(record["io_write_mb"] for record in records),
        "max_rss_mb": max(
            (record["max_rss_mb"] for record in records), default=0.0
        ),
        "generated_at": dt.datetime.now().astimezone().isoformat(),
    }
    totals["cpu_efficiency"] = (
        totals["actual_cpu_hours"] / totals["requested_core_hours"]
        if totals["requested_core_hours"] > 0
        else 0.0
    )
    (output_dir / "performance_summary.json").write_text(
        json.dumps(totals, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(str(summary_path))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Monitor and summarize one direct Apptainer WGS attempt."
    )
    subparsers = parser.add_subparsers(dest="command")
    monitor_parser = subparsers.add_parser("monitor")
    monitor_parser.add_argument("--root-pid", type=int, required=True)
    monitor_parser.add_argument("--analysis-dir", required=True)
    monitor_parser.add_argument("--attempt", required=True)
    monitor_parser.add_argument("--profile", required=True)
    monitor_parser.add_argument("--interval", type=float, default=5.0)
    monitor_parser.set_defaults(handler=monitor)
    summarize_parser = subparsers.add_parser("summarize")
    summarize_parser.add_argument("--analysis-dir", required=True)
    summarize_parser.add_argument("--attempt", required=True)
    summarize_parser.add_argument("--config", required=True)
    summarize_parser.set_defaults(handler=summarize)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.error("a command is required")
    if getattr(args, "interval", 5.0) <= 0:
        parser.error("--interval must be greater than zero")
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
