from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import Base, PlatformResourceSnapshot
from app.platform_resources_service import get_platform_resources, upsert_resource_snapshot
from app.platform_metrics_collector_cli import (
    _collect_cloud_spool,
    _collect_node_spool,
    _derive_node_rates,
)
from app.platform_node_probe_cli import NODE_TARGETS, _ssh_command, _write_spool


def test_resource_snapshot_is_bounded_and_becomes_stale() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    with sessions() as session:
        for index in range(65):
            upsert_resource_snapshot(
                session=session,
                resource_key="node-96",
                resource_type="node",
                display_name="172.17.61.96",
                current={"load1": index},
                source_updated_at=start + timedelta(minutes=index),
            )
        row = session.scalar(select(PlatformResourceSnapshot))
        assert len(row.history_json) == 60
        payload = get_platform_resources(session=session, now=start + timedelta(minutes=70))
        assert payload["items"][0]["status"] == "stale"
        assert payload["items"][0]["current"] == {"load1": 64}


def test_node_metrics_report_cpu_io_and_network_rates() -> None:
    previous = {
        "cpu_seconds_total": 100,
        "cpu_seconds_idle": 80,
        "node_disk_read_bytes_total": 1000,
        "node_disk_written_bytes_total": 2000,
        "node_disk_reads_completed_total": 10,
        "node_disk_writes_completed_total": 20,
        "node_network_receive_bytes_total": 3000,
        "node_network_transmit_bytes_total": 4000,
    }
    current = {
        "cpu_seconds_total": 110,
        "cpu_seconds_idle": 85,
        "node_disk_read_bytes_total": 7000,
        "node_disk_written_bytes_total": 5000,
        "node_disk_reads_completed_total": 70,
        "node_disk_writes_completed_total": 50,
        "node_network_receive_bytes_total": 9000,
        "node_network_transmit_bytes_total": 10000,
    }

    payload = _derive_node_rates(current=current, previous=previous, elapsed_seconds=60)

    assert payload["cpu_used_percent"] == 50.0
    assert payload["disk_read_bps"] == 100.0
    assert payload["disk_write_bps"] == 50.0
    assert payload["disk_read_iops"] == 1.0
    assert payload["disk_write_iops"] == 0.5
    assert payload["network_receive_bps"] == 100.0
    assert payload["network_transmit_bps"] == 100.0


def test_node_probe_uses_only_fixed_ssh_aliases_and_atomic_spool(tmp_path) -> None:
    assert NODE_TARGETS == (
        ("node-96", "172.17.61.96", "metrics-node-96"),
        ("node-97", "172.17.61.97", "metrics-node-97"),
    )
    command = _ssh_command(
        ssh_bin="/usr/bin/ssh",
        ssh_config=tmp_path / "config",
        alias="metrics-node-96",
    )
    assert command[:5] == [
        "/usr/bin/ssh", "-F", str(tmp_path / "config"), "-o", "BatchMode=yes",
    ]
    assert command[5] == "metrics-node-96"
    assert "172.17.61.96" not in " ".join(command)

    spool = tmp_path / "nodes.json"
    _write_spool(spool, {"schema_version": "platform-node-metrics.v1", "items": []})
    assert spool.read_text(encoding="utf-8").endswith("\n")
    assert not list(tmp_path.glob("*.partial"))


def test_node_spool_upserts_fixed_nodes_and_derives_rates(tmp_path, monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    before = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    current_at = before + timedelta(seconds=60)
    with sessions() as session:
        upsert_resource_snapshot(
            session=session,
            resource_key="node-96",
            resource_type="node",
            display_name="172.17.61.96",
            current={
                "cpu_seconds_total": 100,
                "cpu_seconds_idle": 80,
                "node_disk_read_bytes_total": 1000,
            },
            source_updated_at=before,
        )
    spool = tmp_path / "nodes.json"
    base_current = {
        "cpu_seconds_total": 20,
        "cpu_seconds_idle": 10,
        "node_memory_MemTotal_bytes": 2000,
        "node_memory_MemAvailable_bytes": 1000,
        "node_load1": 1,
        "node_load5": 2,
        "node_load15": 3,
        "node_disk_read_bytes_total": 0,
        "node_disk_written_bytes_total": 0,
        "node_disk_reads_completed_total": 0,
        "node_disk_writes_completed_total": 0,
        "node_network_receive_bytes_total": 0,
        "node_network_transmit_bytes_total": 0,
        "node_filesystem_size_bytes": 10000,
        "node_filesystem_avail_bytes": 5000,
    }
    _write_spool(spool, {
        "schema_version": "platform-node-metrics.v1",
        "items": [
            {
                "resource_key": "node-96",
                "source_updated_at": current_at.isoformat(),
                "current": {**base_current,
                    "cpu_seconds_total": 110,
                    "cpu_seconds_idle": 85,
                    "node_disk_read_bytes_total": 7000,
                    "node_memory_MemTotal_bytes": 1000,
                    "node_memory_MemAvailable_bytes": 400,
                },
            },
            {
                "resource_key": "node-97",
                "source_updated_at": current_at.isoformat(),
                "current": base_current,
            },
        ],
    })
    monkeypatch.setenv("PLATFORM_NODE_METRICS_SPOOL", str(spool))
    monkeypatch.setattr("app.platform_metrics_collector_cli.get_sessionmaker", lambda: sessions)

    _collect_node_spool({})
    _collect_node_spool({})

    with sessions() as session:
        rows = {
            row.resource_key: row
            for row in session.scalars(select(PlatformResourceSnapshot)).all()
        }
        assert set(rows) == {"node-96", "node-97"}
        assert rows["node-96"].status == "healthy"
        assert rows["node-96"].current_json["cpu_used_percent"] == 50.0
        assert rows["node-96"].current_json["disk_read_bps"] == 100.0
        assert rows["node-97"].display_name == "172.17.61.97"


def test_invalid_cloud_spool_marks_existing_cloud_resources_degraded(tmp_path, monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc)
    with sessions() as session:
        for key, resource_type in (("sfs-main", "sfs"), ("obs-wgs", "obs")):
            upsert_resource_snapshot(
                session=session,
                resource_key=key,
                resource_type=resource_type,
                display_name=key,
                current={"used_bytes": 10},
                source_updated_at=now,
            )
    spool = tmp_path / "cloud.json"
    spool.write_text("{invalid", encoding="utf-8")
    monkeypatch.setenv("PLATFORM_CLOUD_METRICS_SPOOL", str(spool))
    monkeypatch.setattr(
        "app.platform_metrics_collector_cli.get_sessionmaker", lambda: sessions
    )

    _collect_cloud_spool({})

    with sessions() as session:
        rows = session.scalars(select(PlatformResourceSnapshot)).all()
        assert {row.status for row in rows} == {"degraded"}
        assert all("spool is invalid" in str(row.error_message) for row in rows)


def test_missing_cloud_spool_creates_degraded_placeholders(tmp_path, monkeypatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setenv("PLATFORM_CLOUD_METRICS_SPOOL", str(tmp_path / "missing.json"))
    monkeypatch.setattr(
        "app.platform_metrics_collector_cli.get_sessionmaker", lambda: sessions
    )

    _collect_cloud_spool({})

    with sessions() as session:
        payload = get_platform_resources(session=session)
        assert payload["status"] == "degraded"
        assert {item["resource_type"] for item in payload["items"]} == {"sfs", "obs"}
        assert all("spool is missing" in item["error_message"] for item in payload["items"])
