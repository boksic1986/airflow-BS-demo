from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def get_system_resources() -> dict[str, Any]:
    payload = read_proc_resources()
    containers = _docker_stats()
    if containers:
        payload["source"] = "host_proc_docker_stats"
        payload["containers"] = containers
    return payload


def read_proc_resources() -> dict[str, Any]:
    source = "host_proc"
    try:
        cpu = _read_cpu()
        memory = _read_memory()
    except OSError:
        source = "host_proc_partial"
        cpu = {"cores": os.cpu_count() or 1, "load_average": []}
        memory = {"total_bytes": 0, "available_bytes": 0, "used_bytes": 0, "used_percent": 0}
    return {
        "source": source,
        "host": {
            "cpu": cpu,
            "memory": memory,
            "disks": _read_disks(),
        },
        "containers": [],
    }


def _read_cpu() -> dict[str, Any]:
    load_average = []
    if hasattr(os, "getloadavg"):
        load_average = [round(value, 2) for value in os.getloadavg()]
    return {
        "cores": os.cpu_count() or 1,
        "load_average": load_average,
    }


def _read_memory() -> dict[str, Any]:
    values: dict[str, int] = {}
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            key, raw_value = line.split(":", 1)
            values[key] = int(raw_value.strip().split()[0]) * 1024
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    used = max(total - available, 0)
    return {
        "total_bytes": total,
        "available_bytes": available,
        "used_bytes": used,
        "used_percent": round((used / total) * 100, 1) if total else 0,
    }


def _read_disks() -> list[dict[str, Any]]:
    disks = []
    for path in ["/", "/data"]:
        if not Path(path).exists():
            continue
        usage = shutil.disk_usage(path)
        disks.append(
            {
                "path": path,
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "used_percent": round((usage.used / usage.total) * 100, 1) if usage.total else 0,
            }
        )
    return disks


def _docker_stats() -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.BlockIO}}",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=4,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    containers = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        containers.append(
            {
                "name": parts[0],
                "cpu_percent": parts[1],
                "memory_usage": parts[2],
                "block_io": parts[3],
            }
        )
    return containers
