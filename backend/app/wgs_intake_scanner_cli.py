import argparse
import json
import os
from pathlib import Path
import time
from typing import Callable

import httpx

from app.db import get_sessionmaker
from app.wgs_project_catalog import load_wgs_intake_policy
from app.wgs_t7_intake import scan_wgs_t7_intake


def run_intake_worker(
    *,
    session_factory,
    intake_root: Path,
    intake_interval_seconds: int,
    auto_dispatch_enabled: bool,
    stop_event,
    scan_fn: Callable | None = None,
    dispatch_fn: Callable[[], dict] | None = None,
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
            if auto_dispatch_enabled and dispatch_fn is not None:
                payload["dispatch"] = dispatch_fn()
        except Exception as exc:
            payload = {"intake_error": str(exc)}
        print(json.dumps(payload, sort_keys=True), flush=True)
        elapsed = max(0.0, monotonic_fn() - cycle_started)
        if stop_event.wait(max(0.0, interval - elapsed)):
            return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    policy = load_wgs_intake_policy(
        intake_path=_required_env("INTAKE_CONFIG_PATH"),
        project_catalog_path=_required_env("WGS_PROJECT_CATALOG_PATH"),
    )
    if not (
        _bool_env("WGS_INTAKE_SCAN_ENABLED", False)
        and policy.scheduled_scan_enabled
    ):
        return 0
    interval = policy.interval_seconds
    auto_dispatch = (
        policy.auto_dispatch_enabled
        and _bool_env("WGS_AUTO_DISPATCH_ENABLED", False)
    )
    ignored_chip_ids = _csv_env("WGS_INTAKE_IGNORED_CHIP_IDS")
    session_factory = get_sessionmaker()
    while True:
        cycle_started = time.monotonic()
        try:
            result = scan_wgs_t7_intake(
                session_factory=session_factory,
                root=Path(policy.control_plane_path),
                scan_interval_seconds=interval,
                scan_enabled=True,
                auto_dispatch_enabled=auto_dispatch,
                ignored_chip_ids=ignored_chip_ids,
            )
            payload = {"intake": result}
            if auto_dispatch:
                payload["dispatch"] = _request_auto_dispatch()
            print(json.dumps(payload, sort_keys=True), flush=True)
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


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _csv_env(name: str) -> set[str]:
    return {item.strip() for item in os.getenv(name, "").split(",") if item.strip()}


def _request_auto_dispatch() -> dict:
    backend_url = os.getenv("WGS_BACKEND_INTERNAL_URL", "http://backend:8000").rstrip("/")
    token = os.getenv("INTERNAL_SERVICE_TOKEN", "").strip()
    response = httpx.post(
        f"{backend_url}/api/internal/wgs/intake/dispatch-ready",
        headers={"X-Airflow-Demo-Token": token},
        timeout=60.0,
    )
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, dict):
        raise RuntimeError("automatic dispatch returned an invalid response")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
