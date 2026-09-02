import argparse
import json
import os
from pathlib import Path
import time
from typing import Callable

from app.db import get_sessionmaker
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
    scan = scan_fn or scan_wgs_t7_intake
    interval = max(60, intake_interval_seconds)
    while not stop_event.is_set():
        cycle_started = monotonic_fn()
        try:
            result = scan(
                session_factory=session_factory,
                root=intake_root,
                scan_interval_seconds=interval,
                scan_enabled=True,
                auto_dispatch_enabled=auto_dispatch_enabled,
            )
            payload = {"intake": result}
        except Exception as exc:
            payload = {"intake_error": str(exc)}
        print(json.dumps(payload, sort_keys=True), flush=True)
        elapsed = max(0.0, monotonic_fn() - cycle_started)
        if stop_event.wait(max(0.0, interval - elapsed)):
            return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--intake-root",
        type=Path,
        default=Path(os.getenv("WGS_T7_FASTQ_ROOT", "/bi/fastq/T7_Fastq")),
    )
    parser.add_argument(
        "--intake-interval",
        type=int,
        default=int(os.getenv("WGS_INTAKE_SCAN_INTERVAL_SECONDS", "600")),
    )
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if not _bool_env("WGS_INTAKE_SCAN_ENABLED", False):
        return 0
    interval = max(60, args.intake_interval)
    auto_dispatch = _bool_env("WGS_AUTO_DISPATCH_ENABLED", False)
    ignored_chip_ids = _csv_env("WGS_INTAKE_IGNORED_CHIP_IDS")
    session_factory = get_sessionmaker()
    while True:
        cycle_started = time.monotonic()
        try:
            result = scan_wgs_t7_intake(
                session_factory=session_factory,
                root=args.intake_root,
                scan_interval_seconds=interval,
                scan_enabled=True,
                auto_dispatch_enabled=auto_dispatch,
                ignored_chip_ids=ignored_chip_ids,
            )
            print(json.dumps({"intake": result}, sort_keys=True), flush=True)
        except Exception as exc:
            print(json.dumps({"intake_error": str(exc)}), flush=True)
        if args.once:
            return 0
        time.sleep(max(0.0, interval - (time.monotonic() - cycle_started)))


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str) -> set[str]:
    return {item.strip() for item in os.getenv(name, "").split(",") if item.strip()}


if __name__ == "__main__":
    raise SystemExit(main())
