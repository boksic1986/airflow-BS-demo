from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.models import PlatformResourceSnapshot


RESOURCE_STALE_AFTER = {
    "node": timedelta(minutes=3),
    "sfs": timedelta(minutes=3),
    "obs": timedelta(minutes=90),
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
    row.history_json = history[-60:]
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


def get_platform_resources(*, session, now: datetime | None = None) -> dict[str, Any]:
    observed = now or datetime.now(timezone.utc)
    rows = session.scalars(select(PlatformResourceSnapshot).order_by(PlatformResourceSnapshot.resource_type, PlatformResourceSnapshot.resource_key)).all()
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
                "history": list(row.history_json or []),
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
    return {"status": overall, "items": items, "updated_at": observed.isoformat()}


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
