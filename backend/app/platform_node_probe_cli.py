from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import time


logger = logging.getLogger(__name__)

NODE_TARGETS = (
    ("node-96", "172.17.61.96", "metrics-node-96"),
    ("node-97", "172.17.61.97", "metrics-node-97"),
)
NODE_DISPLAY_NAMES = {key: address for key, address, _alias in NODE_TARGETS}
NODE_METRIC_FIELDS = frozenset({
    "cpu_seconds_total",
    "cpu_seconds_idle",
    "node_memory_MemTotal_bytes",
    "node_memory_MemAvailable_bytes",
    "node_load1",
    "node_load5",
    "node_load15",
    "node_disk_read_bytes_total",
    "node_disk_written_bytes_total",
    "node_disk_reads_completed_total",
    "node_disk_writes_completed_total",
    "node_network_receive_bytes_total",
    "node_network_transmit_bytes_total",
    "node_filesystem_size_bytes",
    "node_filesystem_avail_bytes",
})

_REMOTE_PROBE = r'''
import glob
import json
import os

metrics = {}
hz = float(os.sysconf("SC_CLK_TCK"))
with open("/proc/stat", encoding="ascii") as handle:
    parts = handle.readline().split()[1:]
cpu = [float(value) for value in parts]
metrics["cpu_seconds_total"] = sum(cpu) / hz
metrics["cpu_seconds_idle"] = sum(cpu[3:5]) / hz

memory = {}
with open("/proc/meminfo", encoding="ascii") as handle:
    for line in handle:
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable"}:
            memory[key] = float(value.split()[0]) * 1024
metrics["node_memory_MemTotal_bytes"] = memory["MemTotal"]
metrics["node_memory_MemAvailable_bytes"] = memory["MemAvailable"]

with open("/proc/loadavg", encoding="ascii") as handle:
    load = [float(value) for value in handle.read().split()[:3]]
metrics["node_load1"], metrics["node_load5"], metrics["node_load15"] = load

disk = {"read_ios": 0.0, "write_ios": 0.0, "read_bytes": 0.0, "write_bytes": 0.0}
for stat_path in sorted(glob.glob("/sys/block/*/stat")):
    name = stat_path.split("/")[-2]
    if not name.startswith(("sd", "vd", "xvd", "nvme", "hd")):
        continue
    with open(stat_path, encoding="ascii") as handle:
        values = [float(value) for value in handle.read().split()]
    sector_path = "/sys/block/%s/queue/hw_sector_size" % name
    with open(sector_path, encoding="ascii") as handle:
        sector_size = float(handle.read().strip())
    disk["read_ios"] += values[0]
    disk["read_bytes"] += values[2] * sector_size
    disk["write_ios"] += values[4]
    disk["write_bytes"] += values[6] * sector_size
metrics["node_disk_reads_completed_total"] = disk["read_ios"]
metrics["node_disk_writes_completed_total"] = disk["write_ios"]
metrics["node_disk_read_bytes_total"] = disk["read_bytes"]
metrics["node_disk_written_bytes_total"] = disk["write_bytes"]

received = transmitted = 0.0
with open("/proc/net/dev", encoding="ascii") as handle:
    for line in handle:
        if ":" not in line:
            continue
        interface, values = line.split(":", 1)
        if interface.strip() == "lo":
            continue
        fields = values.split()
        received += float(fields[0])
        transmitted += float(fields[8])
metrics["node_network_receive_bytes_total"] = received
metrics["node_network_transmit_bytes_total"] = transmitted

filesystem = "/data" if os.path.isdir("/data") else "/"
stat = os.statvfs(filesystem)
metrics["node_filesystem_size_bytes"] = float(stat.f_blocks * stat.f_frsize)
metrics["node_filesystem_avail_bytes"] = float(stat.f_bavail * stat.f_frsize)
print(json.dumps(metrics, separators=(",", ":"), sort_keys=True))
'''.strip()
_REMOTE_PROBE_B64 = base64.b64encode(_REMOTE_PROBE.encode("utf-8")).decode("ascii")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    interval = max(30, int(os.getenv("PLATFORM_METRICS_INTERVAL_SECONDS", "60")))
    spool = Path(os.getenv(
        "PLATFORM_NODE_METRICS_SPOOL",
        "/data/wgs-runtime/platform-metrics/nodes.json",
    ))
    ssh_bin = os.getenv("PLATFORM_NODE_PROBE_SSH_BIN", "/usr/bin/ssh")
    ssh_config = Path(os.getenv(
        "PLATFORM_NODE_PROBE_SSH_CONFIG",
        "/opt/platform-metrics/ssh/metrics_config",
    ))
    previous: dict[str, str] = {}
    while True:
        collect_once(
            spool=spool,
            ssh_bin=ssh_bin,
            ssh_config=ssh_config,
            previous=previous,
        )
        time.sleep(interval)


def collect_once(*, spool: Path, ssh_bin: str, ssh_config: Path,
                 previous: dict[str, str] | None = None) -> dict:
    state = previous if previous is not None else {}
    items = []
    for resource_key, display_name, alias in NODE_TARGETS:
        try:
            completed = subprocess.run(
                _ssh_command(ssh_bin=ssh_bin, ssh_config=ssh_config, alias=alias),
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
            current = _validate_current(json.loads(completed.stdout))
            items.append({
                "resource_key": resource_key,
                "display_name": display_name,
                "source_updated_at": datetime.now(timezone.utc).isoformat(),
                "current": current,
            })
            _log_transition(state, resource_key, "healthy")
        except Exception as error:
            message = _safe_error(error)
            items.append({
                "resource_key": resource_key,
                "display_name": display_name,
                "error": message,
            })
            _log_transition(state, resource_key, "degraded", message)
    payload = {
        "schema_version": "platform-node-metrics.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    _write_spool(spool, payload)
    return payload


def _ssh_command(*, ssh_bin: str, ssh_config: Path, alias: str) -> list[str]:
    approved_aliases = {target[2] for target in NODE_TARGETS}
    if alias not in approved_aliases:
        raise ValueError("unsupported node metrics SSH alias")
    remote_command = (
        "python3 -c \"import base64;exec(base64.b64decode('"
        + _REMOTE_PROBE_B64
        + "'))\""
    )
    return [
        ssh_bin,
        "-F",
        str(ssh_config),
        "-o",
        "BatchMode=yes",
        alias,
        remote_command,
    ]


def _validate_current(payload: object) -> dict[str, float]:
    if not isinstance(payload, dict):
        raise ValueError("node probe did not return an object")
    result = {}
    for key in NODE_METRIC_FIELDS:
        value = payload.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"node probe metric is missing or invalid: {key}")
        result[key] = float(value)
    return result


def _write_spool(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".partial",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o640)
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _safe_error(error: Exception) -> str:
    if isinstance(error, subprocess.CalledProcessError):
        detail = (error.stderr or error.stdout or "SSH command failed").strip()
    else:
        detail = str(error).strip()
    return (detail or error.__class__.__name__)[-1000:]


def _log_transition(state: dict[str, str], key: str, status: str,
                    message: str | None = None) -> None:
    if state.get(key) == status:
        return
    state[key] = status
    if status == "healthy":
        logger.info("platform node probe %s is healthy", key)
    else:
        logger.error("platform node probe %s is %s: %s", key, status, message)


if __name__ == "__main__":
    raise SystemExit(main())
