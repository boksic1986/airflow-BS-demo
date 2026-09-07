from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from typing import Callable

import psycopg

from app.config import get_settings
from app.db import get_sessionmaker
from app.wgs_observer import ingest_observer_attempt_once
from app.wgs_observer_lifecycle import OBSERVER_CHANNEL, list_observer_work


ObserverKey = tuple[str, int]


class PostgresNotificationSource:
    def __init__(self, database_url: str):
        conninfo = database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        ).replace("postgresql+psycopg2://", "postgresql://", 1)
        self.connection = psycopg.connect(conninfo, autocommit=True)
        self.connection.execute(f"LISTEN {OBSERVER_CHANNEL}")

    def wait(self, timeout: float | None) -> list[ObserverKey]:
        found: list[ObserverKey] = []
        for notification in self.connection.notifies(timeout=timeout, stop_after=1):
            try:
                payload = json.loads(notification.payload)
                analysis_id = str(payload.get("analysis_id") or "")
                attempt = int(payload.get("attempt") or 0)
                if analysis_id and attempt > 0:
                    found.append((analysis_id, attempt))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return found

    def close(self) -> None:
        self.connection.close()


def run_observer_iteration(
    *,
    active: set[ObserverKey],
    notification_source,
    ingest_fn: Callable[[str, int], dict | None],
    interval_seconds: float,
    log_fn: Callable[[dict], None] | None = None,
) -> set[ObserverKey]:
    remaining = set(active)
    if remaining:
        for analysis_id, attempt in sorted(remaining):
            result = ingest_fn(analysis_id, attempt) or {}
            lifecycle = str(result.get("lifecycle_status") or "active")
            if lifecycle == "stopped":
                remaining.discard((analysis_id, attempt))
            if log_fn and (
                int(result.get("events_ingested") or 0)
                or int(result.get("errors") or 0)
                or lifecycle == "stopped"
            ):
                log_fn(
                    {
                        "observer": {
                            "analysis_id": analysis_id,
                            "attempt": attempt,
                            **result,
                        }
                    }
                )
    timeout = interval_seconds if remaining else None
    remaining.update(notification_source.wait(timeout))
    return remaining


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path(os.getenv("WGS_EVIDENCE_ROOT", "/data/wgs-evidence")),
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("WGS_OBSERVER_INTERVAL", "5")),
    )
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    session_factory = get_sessionmaker()

    if args.once:
        for analysis_id, attempt in list_observer_work(session_factory):
            result = ingest_observer_attempt_once(
                session_factory=session_factory,
                evidence_root=args.evidence_root,
                analysis_id=analysis_id,
                attempt=attempt,
                transfer_spool_root=Path(settings.wgs_transfer_spool_root),
            )
            if int(result.get("events_ingested") or 0) or int(
                result.get("errors") or 0
            ):
                _log(
                    {
                        "observer": {
                            "analysis_id": analysis_id,
                            "attempt": attempt,
                            **result,
                        }
                    }
                )
        return 0

    backoff = 1.0
    while True:
        source = None
        try:
            source = PostgresNotificationSource(settings.database_url)
            # LISTEN first, then restore persisted work.  This closes the race
            # where activation could commit between the initial query and
            # subscription and leave an idle observer blocked indefinitely.
            active = set(list_observer_work(session_factory))
            backoff = 1.0
            while True:
                active = run_observer_iteration(
                    active=active,
                    notification_source=source,
                    ingest_fn=lambda analysis_id, attempt: ingest_observer_attempt_once(
                        session_factory=session_factory,
                        evidence_root=args.evidence_root,
                        analysis_id=analysis_id,
                        attempt=attempt,
                        transfer_spool_root=Path(settings.wgs_transfer_spool_root),
                    ),
                    interval_seconds=max(1.0, args.interval),
                    log_fn=_log,
                )
        except (OSError, psycopg.Error, RuntimeError, ValueError) as exc:
            _log({"observer_error": str(exc)})
            if source is not None:
                source.close()
            time.sleep(backoff)
            backoff = min(60.0, backoff * 2)


def _log(payload: dict) -> None:
    print(json.dumps(payload, sort_keys=True), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
