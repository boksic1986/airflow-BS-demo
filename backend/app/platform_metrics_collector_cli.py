from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.db import get_sessionmaker
from app.models import PlatformResourceSnapshot
from app.platform_resources_service import record_resource_error, upsert_resource_snapshot


logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    interval = max(30, int(os.getenv("PLATFORM_METRICS_INTERVAL_SECONDS", "60")))
    previous: dict[str, str] = {}
    while True:
        collect_once(previous)
        time.sleep(interval)


def collect_once(previous: dict[str, str] | None = None) -> None:
    state = previous if previous is not None else {}
    targets = _targets(os.getenv(
        "PLATFORM_NODE_EXPORTER_TARGETS",
        "node-96=http://172.17.61.96:9100/metrics,node-97=http://172.17.61.97:9100/metrics",
    ))
    for key, url in targets:
        try:
            response = httpx.get(url, timeout=10.0)
            response.raise_for_status()
            observed_at = datetime.now(timezone.utc)
            current = _parse_node_metrics(response.text)
            with get_sessionmaker()() as session:
                prior = session.scalar(select(PlatformResourceSnapshot).where(PlatformResourceSnapshot.resource_key == key))
                elapsed = (
                    (observed_at - _aware(prior.source_updated_at)).total_seconds()
                    if prior is not None and prior.source_updated_at is not None
                    else 0
                )
                current = _derive_node_rates(
                    current=current,
                    previous=dict(prior.current_json or {}) if prior is not None else {},
                    elapsed_seconds=elapsed,
                )
                upsert_resource_snapshot(
                    session=session,
                    resource_key=key,
                    resource_type="node",
                    display_name=key.replace("node-", "172.17.61."),
                    current=current,
                    source_updated_at=observed_at,
                )
            _log_transition(state, key, "healthy")
        except Exception as error:  # collector must not affect WGS execution
            with get_sessionmaker()() as session:
                record_resource_error(session=session, resource_key=key, resource_type="node", display_name=key, message=str(error))
            _log_transition(state, key, "degraded", str(error))
    _collect_cloud_spool(state)


def _collect_cloud_spool(state: dict[str, str]) -> None:
    path = Path(os.getenv("PLATFORM_CLOUD_METRICS_SPOOL", "/data/wgs-runtime/platform-metrics/cloud.json"))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("items") or []:
            resource_type = str(item["resource_type"])
            key = str(item["resource_key"])
            updated = datetime.fromisoformat(str(item["source_updated_at"]).replace("Z", "+00:00"))
            with get_sessionmaker()() as session:
                upsert_resource_snapshot(
                    session=session,
                    resource_key=key,
                    resource_type=resource_type,
                    display_name=str(item.get("display_name") or key),
                    current=dict(item.get("current") or {}),
                    source_updated_at=updated,
                )
            _log_transition(state, key, "healthy")
    except FileNotFoundError:
        _record_cloud_spool_error("cloud metrics spool is missing")
        _log_transition(state, "cloud-spool", "degraded", "cloud metrics spool is missing")
        return
    except Exception as error:
        _record_cloud_spool_error(f"cloud metrics spool is invalid: {error}")
        _log_transition(state, "cloud-spool", "degraded", str(error))


def _record_cloud_spool_error(message: str) -> None:
    # Keep the last good values for diagnosis, but make collection health
    # explicit. If no successful sample exists yet, create bounded placeholder
    # rows so healthy node metrics cannot make the overall response healthy.
    with get_sessionmaker()() as session:
        rows = session.scalars(
            select(PlatformResourceSnapshot).where(
                PlatformResourceSnapshot.resource_type.in_(("sfs", "obs"))
            )
        ).all()
        if rows:
            targets = [
                (row.resource_key, row.resource_type, row.display_name)
                for row in rows
            ]
        else:
            targets = [
                ("sfs-cloud-metrics", "sfs", "SFS Cloud Eye"),
                ("obs-cloud-metrics", "obs", "OBS Cloud Eye"),
            ]
        for resource_key, resource_type, display_name in targets:
            record_resource_error(
                session=session,
                resource_key=resource_key,
                resource_type=resource_type,
                display_name=display_name,
                message=message,
            )


def _parse_node_metrics(text: str) -> dict:
    totals: dict[str, float] = {}
    for raw in text.splitlines():
        if not raw or raw.startswith("#") or " " not in raw:
            continue
        name, value = raw.rsplit(" ", 1)
        try:
            number = float(value)
        except ValueError:
            continue
        metric = name.split("{", 1)[0]
        if metric in {
            "node_memory_MemTotal_bytes", "node_memory_MemAvailable_bytes",
            "node_load1", "node_load5", "node_load15",
            "node_disk_read_bytes_total", "node_disk_written_bytes_total",
            "node_disk_reads_completed_total", "node_disk_writes_completed_total",
            "node_network_receive_bytes_total", "node_network_transmit_bytes_total",
            "node_filesystem_size_bytes", "node_filesystem_avail_bytes",
        }:
            totals[metric] = totals.get(metric, 0.0) + number
        elif metric == "node_cpu_seconds_total":
            totals["cpu_seconds_total"] = totals.get("cpu_seconds_total", 0.0) + number
            if 'mode="idle"' in name or 'mode="iowait"' in name:
                totals["cpu_seconds_idle"] = totals.get("cpu_seconds_idle", 0.0) + number
    return totals


def _derive_node_rates(*, current: dict, previous: dict, elapsed_seconds: float) -> dict:
    result = dict(current)
    if elapsed_seconds <= 0:
        return result

    def rate(metric: str) -> float | None:
        if metric not in current or metric not in previous:
            return None
        delta = float(current[metric]) - float(previous[metric])
        return max(0.0, delta / elapsed_seconds)

    mappings = {
        "node_disk_read_bytes_total": "disk_read_bps",
        "node_disk_written_bytes_total": "disk_write_bps",
        "node_disk_reads_completed_total": "disk_read_iops",
        "node_disk_writes_completed_total": "disk_write_iops",
        "node_network_receive_bytes_total": "network_receive_bps",
        "node_network_transmit_bytes_total": "network_transmit_bps",
    }
    for source, target in mappings.items():
        value = rate(source)
        if value is not None:
            result[target] = round(value, 3)

    total_delta = float(current.get("cpu_seconds_total", 0)) - float(previous.get("cpu_seconds_total", 0))
    idle_delta = float(current.get("cpu_seconds_idle", 0)) - float(previous.get("cpu_seconds_idle", 0))
    if total_delta > 0:
        result["cpu_used_percent"] = round(max(0.0, min(100.0, (1 - idle_delta / total_delta) * 100)), 3)
    return result


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _targets(raw: str) -> list[tuple[str, str]]:
    result = []
    for item in raw.split(","):
        key, separator, url = item.partition("=")
        if separator and key.strip() and url.startswith("http://"):
            result.append((key.strip(), url.strip()))
    return result


def _log_transition(state: dict[str, str], key: str, status: str, message: str | None = None) -> None:
    if state.get(key) == status:
        return
    state[key] = status
    if status == "healthy":
        logger.info("platform resource %s is healthy", key)
    else:
        logger.error("platform resource %s is %s: %s", key, status, message or "unknown error")


if __name__ == "__main__":
    raise SystemExit(main())
