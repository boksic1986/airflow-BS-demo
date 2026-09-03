from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import get_sessionmaker
from app.models import PlatformResourceSnapshot
from app.platform_node_probe_cli import NODE_DISPLAY_NAMES, NODE_METRIC_FIELDS
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
    _collect_node_spool(state)
    _collect_cloud_spool(state)


def _collect_node_spool(state: dict[str, str]) -> None:
    path = Path(os.getenv(
        "PLATFORM_NODE_METRICS_SPOOL",
        "/data/wgs-runtime/platform-metrics/nodes.json",
    ))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "platform-node-metrics.v1":
            raise ValueError("unsupported node metrics spool schema")
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise ValueError("node metrics spool items must be a list")
        items = {str(item.get("resource_key")): item for item in raw_items if isinstance(item, dict)}
        for key, display_name in NODE_DISPLAY_NAMES.items():
            item = items.get(key)
            if item is None:
                _record_node_error(key, display_name, "node metrics spool entry is missing")
                _log_transition(state, key, "degraded", "node metrics spool entry is missing")
                continue
            if item.get("error"):
                message = str(item["error"])[-1000:]
                _record_node_error(key, display_name, message)
                _log_transition(state, key, "degraded", message)
                continue
            observed_at = datetime.fromisoformat(
                str(item["source_updated_at"]).replace("Z", "+00:00")
            )
            current = _validated_node_metrics(item.get("current"))
            with get_sessionmaker()() as session:
                prior = session.scalar(
                    select(PlatformResourceSnapshot).where(
                        PlatformResourceSnapshot.resource_key == key
                    )
                )
                prior_source_at = (
                    _aware(prior.source_updated_at)
                    if prior is not None and prior.source_updated_at is not None
                    else None
                )
                if prior_source_at is not None and observed_at <= prior_source_at:
                    if observed_at == prior_source_at and prior.status != "healthy":
                        upsert_resource_snapshot(
                            session=session,
                            resource_key=key,
                            resource_type="node",
                            display_name=display_name,
                            current=dict(prior.current_json or {}),
                            source_updated_at=prior_source_at,
                        )
                        _log_transition(state, key, "healthy")
                    continue
                elapsed = (
                    (observed_at - prior_source_at).total_seconds()
                    if prior_source_at is not None
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
                    display_name=display_name,
                    current=current,
                    source_updated_at=observed_at,
                )
            _log_transition(state, key, "healthy")
    except FileNotFoundError:
        _record_all_node_errors("node metrics spool is missing")
        _log_transition(state, "node-spool", "degraded", "node metrics spool is missing")
    except Exception as error:
        message = f"node metrics spool is invalid: {error}"
        _record_all_node_errors(message)
        _log_transition(state, "node-spool", "degraded", message)


def _validated_node_metrics(payload: object) -> dict[str, float]:
    if not isinstance(payload, dict):
        raise ValueError("node metrics current payload must be an object")
    result = {}
    for key in NODE_METRIC_FIELDS:
        value = payload.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"node metric is missing or invalid: {key}")
        result[key] = float(value)
    return result


def _record_node_error(resource_key: str, display_name: str, message: str) -> None:
    with get_sessionmaker()() as session:
        record_resource_error(
            session=session,
            resource_key=resource_key,
            resource_type="node",
            display_name=display_name,
            message=message,
        )


def _record_all_node_errors(message: str) -> None:
    for resource_key, display_name in NODE_DISPLAY_NAMES.items():
        _record_node_error(resource_key, display_name, message)


def _collect_cloud_spool(state: dict[str, str]) -> None:
    path = Path(os.getenv("PLATFORM_CLOUD_METRICS_SPOOL", "/data/wgs-runtime/platform-metrics/cloud.json"))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "platform-cloud-metrics.v1":
            raise ValueError("unsupported cloud metrics spool schema")
        for item in payload.get("items") or []:
            resource_type = str(item["resource_type"])
            if resource_type != "sfs":
                continue
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
                PlatformResourceSnapshot.resource_type == "sfs"
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
            ]
        for resource_key, resource_type, display_name in targets:
            record_resource_error(
                session=session,
                resource_key=resource_key,
                resource_type=resource_type,
                display_name=display_name,
                message=message,
            )


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
