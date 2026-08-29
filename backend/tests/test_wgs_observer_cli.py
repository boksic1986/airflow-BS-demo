from pathlib import Path

from app.wgs_intake_scanner_cli import run_intake_worker
from app.wgs_observer_cli import run_observer_iteration


def test_intake_worker_runs_immediately_and_uses_an_independent_wait() -> None:
    calls: list[tuple[str, object]] = []

    class StopAfterFirstWait:
        def is_set(self) -> bool:
            return False

        def wait(self, seconds: float) -> bool:
            calls.append(("wait", seconds))
            return True

    run_intake_worker(
        session_factory=object(),
        intake_root=Path("/bi/fastq/T7_Fastq"),
        intake_interval_seconds=1800,
        auto_dispatch_enabled=False,
        stop_event=StopAfterFirstWait(),
        scan_fn=lambda **kwargs: calls.append(("scan", kwargs["root"])) or {"scanned": 1},
        monotonic_fn=iter((100.0, 400.0)).__next__,
    )

    assert calls == [
        ("scan", Path("/bi/fastq/T7_Fastq")),
        ("wait", 1500.0),
    ]


def test_active_observer_ingests_only_registered_keys_then_waits_five_seconds() -> None:
    calls: list[tuple[str, object]] = []

    class Source:
        def wait(self, timeout):
            calls.append(("wait", timeout))
            return []

    active = run_observer_iteration(
        active={
            ("WGS_20260830_010203_A1B2C3", 1),
            ("WGS_20260830_010204_D4E5F6", 2),
        },
        notification_source=Source(),
        ingest_fn=lambda analysis_id, attempt: calls.append(
            (analysis_id, attempt)
        )
        or {"lifecycle_status": "active", "events_ingested": 0, "errors": 0},
        interval_seconds=5,
    )

    assert active == {
        ("WGS_20260830_010203_A1B2C3", 1),
        ("WGS_20260830_010204_D4E5F6", 2),
    }
    assert calls == [
        ("WGS_20260830_010203_A1B2C3", 1),
        ("WGS_20260830_010204_D4E5F6", 2),
        ("wait", 5),
    ]
