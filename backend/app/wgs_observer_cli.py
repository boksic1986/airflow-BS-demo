import argparse
import json
import os
import threading
import time
from pathlib import Path
from typing import Callable

from app.db import get_sessionmaker
from app.wgs_observer import ingest_evidence_once
from app.wgs_t7_intake import scan_wgs_t7_intake


def run_intake_worker(
    *,
    session_factory,
    intake_root: Path,
    intake_interval_seconds: int,
    auto_dispatch_enabled: bool,
    stop_event,
    scan_fn: Callable | None = None,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> None:
    """Run the T7 scanner on its own clock, independent of evidence traversal."""
    scan = scan_fn or scan_wgs_t7_intake
    interval = max(60, intake_interval_seconds)
    while not stop_event.is_set():
        cycle_started = monotonic_fn()
        try:
            result = {
                "intake": scan(
                    session_factory=session_factory,
                    root=intake_root,
                    scan_interval_seconds=interval,
                    scan_enabled=True,
                    auto_dispatch_enabled=auto_dispatch_enabled,
                )
            }
        except Exception as exc:
            result = {"intake_error": str(exc)}
        print(json.dumps(result, sort_keys=True), flush=True)
        elapsed = max(0.0, monotonic_fn() - cycle_started)
        if stop_event.wait(max(0.0, interval - elapsed)):
            return


def run_observer_cycle(
    *,
    session_factory,
    evidence_root: Path,
    binding_root: Path,
    catalog_path: Path,
    transfer_spool_root: Path,
    runtime_root: Path,
    intake_enabled: bool,
    intake_root: Path,
    intake_interval_seconds: int,
    auto_dispatch_enabled: bool,
    scanner_due: float,
    monotonic_now: float,
    ingest_fn: Callable | None = None,
    scan_fn: Callable | None = None,
) -> tuple[dict[str, object], float]:
    ingest = ingest_fn or ingest_evidence_once
    scan = scan_fn or scan_wgs_t7_intake
    result: dict[str, object] = {
        "evidence": ingest(
            session_factory=session_factory,
            evidence_root=evidence_root,
            binding_root=binding_root,
            catalog_path=catalog_path,
            transfer_spool_root=transfer_spool_root,
            runtime_root=runtime_root,
        )
    }
    next_due = scanner_due
    if intake_enabled and monotonic_now >= scanner_due:
        try:
            result["intake"] = scan(
                session_factory=session_factory,
                root=intake_root,
                scan_interval_seconds=intake_interval_seconds,
                scan_enabled=True,
                auto_dispatch_enabled=auto_dispatch_enabled,
            )
        except Exception as exc:
            result["intake_error"] = str(exc)
        next_due = monotonic_now + intake_interval_seconds
    return result, next_due


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, default=Path(os.getenv("WGS_EVIDENCE_ROOT", "/data/wgs-evidence")))
    parser.add_argument("--binding-root", type=Path, default=Path(os.getenv("WGS_BINDING_ROOT", "/config/wgs-bindings")))
    parser.add_argument("--catalog", type=Path, default=Path(os.getenv("WGS_RELEASE_CATALOG_PATH", "/config/wgs_releases.yaml")))
    parser.add_argument("--transfer-spool-root", type=Path, default=Path(os.getenv("WGS_TRANSFER_SPOOL_ROOT", "/data/wgs-transfer-spool")))
    parser.add_argument("--runtime-root", type=Path, default=Path(os.getenv("WGS_RUNTIME_ROOT", "/data/wgs-runtime")))
    parser.add_argument("--interval", type=float, default=float(os.getenv("WGS_OBSERVER_INTERVAL", "5")))
    parser.add_argument(
        "--intake-root",
        type=Path,
        default=Path(os.getenv("WGS_T7_FASTQ_ROOT", "/bi/fastq/T7_Fastq")),
    )
    parser.add_argument(
        "--intake-interval",
        type=int,
        default=int(os.getenv("WGS_INTAKE_SCAN_INTERVAL_SECONDS", "1800")),
    )
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    intake_enabled = _bool_env("WGS_INTAKE_SCAN_ENABLED", False)
    auto_dispatch_enabled = _bool_env("WGS_AUTO_DISPATCH_ENABLED", False)
    session_factory = get_sessionmaker()
    if intake_enabled:
        intake_stop = threading.Event()
        threading.Thread(
            target=run_intake_worker,
            kwargs={
                "session_factory": session_factory,
                "intake_root": args.intake_root,
                "intake_interval_seconds": args.intake_interval,
                "auto_dispatch_enabled": auto_dispatch_enabled,
                "stop_event": intake_stop,
            },
            name="wgs-t7-intake",
            daemon=True,
        ).start()
    scanner_due = 0.0
    while True:
        now = time.monotonic()
        result, scanner_due = run_observer_cycle(
            session_factory=session_factory,
            evidence_root=args.evidence_root,
            binding_root=args.binding_root,
            catalog_path=args.catalog,
            transfer_spool_root=args.transfer_spool_root,
            runtime_root=args.runtime_root,
            intake_enabled=False,
            intake_root=args.intake_root,
            intake_interval_seconds=max(60, args.intake_interval),
            auto_dispatch_enabled=auto_dispatch_enabled,
            scanner_due=scanner_due,
            monotonic_now=now,
        )
        print(json.dumps(result, sort_keys=True), flush=True)
        if args.once:
            return 0
        time.sleep(max(1.0, args.interval))


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
