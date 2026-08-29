from pathlib import Path

from app.wgs_observer_cli import run_intake_worker, run_observer_cycle


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


def test_observer_keeps_five_second_evidence_cycle_and_runs_intake_only_when_due() -> None:
    calls: list[tuple[str, object]] = []

    def ingest(**kwargs):
        calls.append(("evidence", kwargs["evidence_root"]))
        return {"events": 2}

    def scan(**kwargs):
        calls.append(("intake", kwargs["root"]))
        assert kwargs["scan_interval_seconds"] == 1800
        assert kwargs["auto_dispatch_enabled"] is False
        return {"scanned": 3}

    common = {
        "session_factory": object(),
        "evidence_root": Path("/evidence"),
        "binding_root": Path("/bindings"),
        "catalog_path": Path("/catalog.yaml"),
        "transfer_spool_root": Path("/transfers"),
        "runtime_root": Path("/runtime"),
        "intake_enabled": True,
        "intake_root": Path("/bi/fastq/T7_Fastq"),
        "intake_interval_seconds": 1800,
        "auto_dispatch_enabled": False,
        "ingest_fn": ingest,
        "scan_fn": scan,
    }

    first, next_due = run_observer_cycle(**common, scanner_due=0.0, monotonic_now=100.0)
    second, next_due = run_observer_cycle(
        **common,
        scanner_due=next_due,
        monotonic_now=105.0,
    )

    assert calls == [
        ("evidence", Path("/evidence")),
        ("intake", Path("/bi/fastq/T7_Fastq")),
        ("evidence", Path("/evidence")),
    ]
    assert first == {"evidence": {"events": 2}, "intake": {"scanned": 3}}
    assert second == {"evidence": {"events": 2}}
    assert next_due == 1900.0


def test_disabled_intake_never_scans() -> None:
    calls: list[str] = []

    result, next_due = run_observer_cycle(
        session_factory=object(),
        evidence_root=Path("/evidence"),
        binding_root=Path("/bindings"),
        catalog_path=Path("/catalog.yaml"),
        transfer_spool_root=Path("/transfers"),
        runtime_root=Path("/runtime"),
        intake_enabled=False,
        intake_root=Path("/bi/fastq/T7_Fastq"),
        intake_interval_seconds=1800,
        auto_dispatch_enabled=False,
        scanner_due=0.0,
        monotonic_now=100.0,
        ingest_fn=lambda **kwargs: {"events": 0},
        scan_fn=lambda **kwargs: calls.append("scan"),
    )

    assert result == {"evidence": {"events": 0}}
    assert next_due == 0.0
    assert calls == []
