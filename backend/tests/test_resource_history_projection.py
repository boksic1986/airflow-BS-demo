from datetime import datetime, timedelta, timezone
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, PlatformResourceSnapshot
from app.platform_resources_service import get_platform_resources


@pytest.mark.parametrize("period,hours", [("1h", 1), ("24h", 24), ("7d", 168)])
def test_dashboard_history_is_windowed_bounded_and_does_not_change_storage(period, hours):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    end = datetime(2026, 9, 8, tzinfo=timezone.utc)
    history = [
        {"at": (end - timedelta(minutes=10079 - i)).isoformat(),
         "read_bps": i, "write_bps": None, "capacity_used_bytes": 123456789}
        for i in range(10080)
    ]
    with Session(engine) as session:
        sfs = PlatformResourceSnapshot(resource_key="sfs-test", resource_type="sfs",
            display_name="Synthetic SFS", current_json=history[-1], history_json=history,
            source_updated_at=end)
        node = PlatformResourceSnapshot(resource_key="node-test", resource_type="node",
            display_name="Synthetic node", current_json={"cpu_used_percent": 10},
            history_json=[{"at": end.isoformat(), "cpu_used_percent": 10}], source_updated_at=end)
        session.add_all([sfs, node])
        session.commit()
        full = get_platform_resources(session=session, now=end)
        result = get_platform_resources(session=session, now=end, history_period=period)
        items = {item["resource_type"]: item for item in result["items"]}
        points = items["sfs"]["history"]
        assert result["history_period"] == period
        assert 2 <= len(points) <= 600
        assert points[-1]["at"] == end.isoformat()
        assert all(end - timedelta(hours=hours) <= datetime.fromisoformat(p["at"]) <= end for p in points)
        assert all(set(p) == {"at", "read_bps", "write_bps", "total_bps"} for p in points)
        assert all(p["write_bps"] is None and p["total_bps"] is None for p in points)
        assert items["node"]["history"] == []
        assert items["node"]["current"] == {"cpu_used_percent": 10}
        assert len(sfs.history_json) == 10080
        assert len(next(i for i in full["items"] if i["resource_type"] == "sfs")["history"]) == 10080
        assert len(json.dumps(result)) < len(json.dumps(full)) / 10
