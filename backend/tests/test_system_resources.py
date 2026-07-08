from app.system_resources import read_proc_resources


def test_read_proc_resources_returns_host_metrics() -> None:
    payload = read_proc_resources()

    assert payload["source"] in {"host_proc", "host_proc_partial"}
    assert payload["host"]["cpu"]["cores"] >= 1
    assert payload["host"]["memory"]["total_bytes"] > 0
    assert isinstance(payload["host"]["disks"], list)
    assert "containers" in payload
