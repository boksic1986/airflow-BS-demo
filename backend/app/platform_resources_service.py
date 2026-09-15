from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Any

from sqlalchemy import select

from app.models import PlatformResourceSnapshot
from app.wgs_workspace_service import project_global_heavy_slot
from app.bss_resource_snapshot import read_snapshot as read_bss_snapshot


RESOURCE_STALE_AFTER = {
    "node": timedelta(minutes=3),
    "sfs": timedelta(minutes=3),
    "obs": timedelta(minutes=90),
}
RESOURCE_HISTORY_LIMIT = {
    "node": 60,
    # One point per minute for seven days.  The JSON contract and database
    # schema stay unchanged; only the bounded SFS ring is long enough for the
    # dashboard's time-window selector.
    "sfs": 7 * 24 * 60,
    "obs": 60,
}


def upsert_resource_snapshot(*, session, resource_key: str, resource_type: str,
                             display_name: str, current: dict[str, Any],
                             source_updated_at: datetime, status: str = "healthy",
                             error_message: str | None = None) -> PlatformResourceSnapshot:
    if resource_type not in RESOURCE_STALE_AFTER:
        raise ValueError("unsupported platform resource type")
    now = datetime.now(timezone.utc)
    row = session.scalar(
        select(PlatformResourceSnapshot).where(PlatformResourceSnapshot.resource_key == resource_key)
    )
    point = {"at": source_updated_at.isoformat(), **current}
    if row is None:
        row = PlatformResourceSnapshot(
            resource_key=resource_key,
            resource_type=resource_type,
            display_name=display_name,
            history_json=[],
        )
        session.add(row)
    history = list(row.history_json or [])
    if not history or history[-1].get("at") != point["at"]:
        history.append(point)
    row.resource_type = resource_type
    row.display_name = display_name
    row.status = status
    row.current_json = dict(current)
    row.history_json = history[-RESOURCE_HISTORY_LIMIT[resource_type]:]
    row.source_updated_at = source_updated_at
    row.collected_at = now
    row.error_message = error_message
    row.updated_at = now
    session.commit()
    return row


def record_resource_error(*, session, resource_key: str, resource_type: str,
                          display_name: str, message: str) -> PlatformResourceSnapshot:
    row = session.scalar(select(PlatformResourceSnapshot).where(PlatformResourceSnapshot.resource_key == resource_key))
    now = datetime.now(timezone.utc)
    if row is None:
        row = PlatformResourceSnapshot(
            resource_key=resource_key,
            resource_type=resource_type,
            display_name=display_name,
            status="degraded",
            current_json={},
            history_json=[],
        )
        session.add(row)
    row.status = "degraded"
    row.error_message = message[-2000:]
    row.collected_at = now
    row.updated_at = now
    session.commit()
    return row


def get_platform_resources(
    *,
    session,
    now: datetime | None = None,
    heavy_slot_limit: int | None = None,
    heavy_slot_mode: str | None = None,
    evidence_root: str | None = None,
    history_period: str | None = None,
) -> dict[str, Any]:
    observed = now or datetime.now(timezone.utc)
    rows = session.scalars(
        select(PlatformResourceSnapshot)
        .where(PlatformResourceSnapshot.resource_type.in_(("node", "sfs")))
        .order_by(PlatformResourceSnapshot.resource_type, PlatformResourceSnapshot.resource_key)
    ).all()
    has_named_sfs = any(
        row.resource_type == "sfs" and row.resource_key != "sfs-cloud-metrics"
        for row in rows
    )
    if has_named_sfs:
        rows = [row for row in rows if row.resource_key != "sfs-cloud-metrics"]
    items = []
    for row in rows:
        source_at = _aware(row.source_updated_at)
        stale = source_at is None or observed - source_at > RESOURCE_STALE_AFTER.get(row.resource_type, timedelta(minutes=5))
        status = "stale" if stale and row.status == "healthy" else row.status
        items.append(
            {
                "resource_key": row.resource_key,
                "resource_type": row.resource_type,
                "display_name": row.display_name,
                "status": status,
                "current": dict(row.current_json or {}),
                "history": (
                    _dashboard_history(row.history_json or [], history_period)
                    if row.resource_type == "sfs" else []
                ) if history_period else list(row.history_json or []),
                "source_updated_at": source_at.isoformat() if source_at else None,
                "collected_at": _aware(row.collected_at).isoformat() if row.collected_at else None,
                "error_message": row.error_message,
            }
        )
    overall = "healthy"
    if any(item["status"] == "degraded" for item in items):
        overall = "degraded"
    elif not items or any(item["status"] == "stale" for item in items):
        overall = "stale"
    return {
        "status": overall,
        "items": items,
        "updated_at": observed.isoformat(),
        **({"history_period": history_period} if history_period else {}),
        "resource_packages": read_bss_snapshot(evidence_root, now=observed),
        "heavy_slot": project_global_heavy_slot(
            session=session,
            limit=heavy_slot_limit,
            mode=heavy_slot_mode,
            evidence_root=evidence_root,
        ),
    }


def _dashboard_history(history: list[dict[str, Any]], period: str) -> list[dict[str, Any]]:
    # Response-only projection: never shorten the collector's seven-day ring.
    seconds, tick = {"1h": (3600, 900), "24h": (86400, 21600), "7d": (604800, 86400)}[period]
    dated = []
    for point in history:
        try:
            at = _aware(datetime.fromisoformat(str(point.get("at", "")).replace("Z", "+00:00")))
        except ValueError:
            continue
        dated.append((at.timestamp(), point))
    if not dated:
        return []
    dated.sort(key=lambda entry: entry[0])
    # Match the existing chart's tick-aligned window, anchored to its last sample.
    end = ceil(dated[-1][0] / tick) * tick
    points = [point for at, point in dated if end - seconds <= at <= end]
    if len(points) > 600:
        # Evenly spaced original observations, including both endpoints. No
        # invented averages/zeros; this trend view is not a peak-value report.
        points = [points[index * (len(points) - 1) // 599] for index in range(600)]
    return [{key: point.get(key) for key in ("at", "read_bps", "write_bps", "total_bps")} for point in points]


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
