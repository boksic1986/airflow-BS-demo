import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).parents[1]


def load_collector():
    spec = importlib.util.spec_from_file_location(
        "collect_sfs_cloud_eye_test", ROOT / "collect_sfs_cloud_eye.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_spool_projects_only_safe_sfs_metrics() -> None:
    collector = load_collector()
    payload = collector.build_spool(
        source_updated_at="2026-09-03T02:00:00+00:00",
        values={
            "used_capacity_percent": 13.86,
            "used_capacity": 123.0,
            "data_read_io_bytes": 1024.0,
            "data_write_io_bytes": 2048.0,
            "total_io_bytes": 3072.0,
            "iops": 12.0,
            "client_connections": 7.0,
        },
    )

    assert payload["schema_version"] == "platform-cloud-metrics.v1"
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["resource_type"] == "sfs"
    assert item["resource_key"] == "sfs-turbo-clinical"
    assert item["current"] == {
        "capacity_used_percent": 13.86,
        "capacity_used_bytes": 123.0,
        "read_bps": 1024.0,
        "write_bps": 2048.0,
        "total_bps": 3072.0,
        "iops": 12.0,
        "client_connections": 7.0,
    }
    assert "ak" not in json.dumps(payload).lower()
    assert "sk" not in json.dumps(payload).lower()


def test_write_spool_is_atomic(tmp_path: Path) -> None:
    collector = load_collector()
    target = tmp_path / "cloud.json"
    collector.write_spool(target, {"schema_version": "platform-cloud-metrics.v1", "items": []})
    assert json.loads(target.read_text(encoding="utf-8"))["items"] == []
    assert list(tmp_path.glob("*.partial")) == []


def test_periodic_collector_retries_transient_cloud_eye_failure(monkeypatch) -> None:
    collector = load_collector()
    attempts = 0

    def fail_then_stop(_args):
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise SystemExit(0)
        raise RuntimeError("temporary CES failure")

    monkeypatch.setattr(
        collector,
        "parse_args",
        lambda: SimpleNamespace(once=False, interval_seconds=30),
    )
    monkeypatch.setattr(collector, "collect_once", fail_then_stop)
    monkeypatch.setattr(collector.time, "sleep", lambda _seconds: None)

    with pytest.raises(SystemExit):
        collector.main()
    assert attempts == 2


def test_cloud_eye_runtime_configuration_fails_closed() -> None:
    collector = load_collector()
    args = SimpleNamespace(
        credentials=None,
        project_id=None,
        endpoint="ces.example.invalid",
        resource_id=None,
        output=None,
    )
    with pytest.raises(ValueError, match="configuration is incomplete"):
        collector.collect_once(args)


def test_collector_source_has_no_operator_or_resource_specific_defaults() -> None:
    source = (ROOT / "collect_sfs_cloud_eye.py").read_text(encoding="utf-8")
    assert "/home/hanjj" not in source
    assert "499af743d3b44edca53ac9fa70c3a98a" not in source
    assert "37cacd44-60ad-41ef-9df2-f93b3dca7095" not in source
