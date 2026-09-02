from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import Base, PlatformResourceSnapshot
from app.platform_resources_service import get_platform_resources, upsert_resource_snapshot
from app.platform_metrics_collector_cli import _collect_cloud_spool, _derive_node_rates, _parse_node_metrics


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
    previous = _parse_node_metrics("""
node_cpu_seconds_total{cpu="0",mode="idle"} 80
node_cpu_seconds_total{cpu="0",mode="user"} 20
node_disk_read_bytes_total{device="sda"} 1000
node_disk_written_bytes_total{device="sda"} 2000
node_disk_reads_completed_total{device="sda"} 10
node_disk_writes_completed_total{device="sda"} 20
node_network_receive_bytes_total{device="eth0"} 3000
node_network_transmit_bytes_total{device="eth0"} 4000
""")
    current = _parse_node_metrics("""
node_cpu_seconds_total{cpu="0",mode="idle"} 85
node_cpu_seconds_total{cpu="0",mode="user"} 25
node_disk_read_bytes_total{device="sda"} 7000
node_disk_written_bytes_total{device="sda"} 5000
node_disk_reads_completed_total{device="sda"} 70
node_disk_writes_completed_total{device="sda"} 50
node_network_receive_bytes_total{device="eth0"} 9000
node_network_transmit_bytes_total{device="eth0"} 10000
""")

    payload = _derive_node_rates(current=current, previous=previous, elapsed_seconds=60)

    assert payload["cpu_used_percent"] == 50.0
    assert payload["disk_read_bps"] == 100.0
    assert payload["disk_write_bps"] == 50.0
    assert payload["disk_read_iops"] == 1.0
    assert payload["disk_write_iops"] == 0.5
    assert payload["network_receive_bps"] == 100.0
    assert payload["network_transmit_bps"] == 100.0


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
