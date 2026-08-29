from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Callable

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from .models import WgsIntakeBatch, WgsIntakeScannerState


CHIP_DIRECTORY_PATTERN = re.compile(
    r"^(?P<chip_number>\d+)th_(?P<sequencing_batch>\d{8}[A-Z])_[A-Za-z0-9.-]+$"
)
WGS_FASTQ_PATTERN = re.compile(r"^(?P<sample>.+)-WGS\.R(?P<read>[12])\.fq\.gz$")
ADDON_SAMPLE_PATTERN = re.compile(r"-S\d+$")
SCANNER_STATE_ID = 1
SCANNER_ADVISORY_LOCK_ID = 743_701_143_829
FINGERPRINT_FROZEN_STATES = {"ready", "no_new_wgs"}


@dataclass(frozen=True)
class FastqObservation:
    name: str
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class ChipObservation:
    source_path: str
    chip_id: str
    sequencing_batch: str
    barcode_present: bool
    barcode_mtime_ns: int | None
    barcode_size: int | None
    eligible_pair_count: int
    excluded_addon_pair_count: int
    pair_issue_count: int
    fingerprint: str | None


def scan_wgs_t7_intake(
    *,
    session_factory: Callable[[], Session],
    root: str | Path,
    now: datetime | None = None,
    scan_interval_seconds: int = 1800,
    scan_enabled: bool = True,
    auto_dispatch_enabled: bool = False,
) -> dict[str, int]:
    """Register T7 discovery state without creating WGS runs or runtime artifacts."""

    scan_now = now or datetime.now(timezone.utc)
    root_path = Path(root)
    started = time.monotonic()
    counts = {
        "scanned": 0,
        "created": 0,
        "updated": 0,
        "ready": 0,
        "needs_review": 0,
        "bootstrap_ignored": 0,
        "errors": 0,
    }

    with session_factory() as session:
        if not _acquire_scanner_lock(session):
            return counts

        scanner = session.get(WgsIntakeScannerState, SCANNER_STATE_ID)
        is_bootstrap = scanner is None or scanner.bootstrap_completed_at is None
        if scanner is None:
            scanner = WgsIntakeScannerState(
                id=SCANNER_STATE_ID,
                root_path=str(root_path),
                scan_enabled=scan_enabled,
                scan_interval_seconds=scan_interval_seconds,
                auto_dispatch_enabled=auto_dispatch_enabled,
                bootstrap_started_at=scan_now,
            )
            session.add(scanner)

        scanner.root_path = str(root_path)
        scanner.scan_enabled = scan_enabled
        scanner.scan_interval_seconds = scan_interval_seconds
        scanner.auto_dispatch_enabled = auto_dispatch_enabled
        scanner.last_scan_started_at = scan_now
        scanner.last_status = "running"
        scanner.last_error = None
        scanner.updated_at = scan_now

        try:
            if not root_path.is_dir():
                raise RuntimeError(f"T7 scan root is unavailable: {root_path}")

            existing_by_path = {
                row.source_path: row
                for row in session.scalars(select(WgsIntakeBatch)).all()
            }
            for directory in sorted(root_path.iterdir(), key=lambda item: item.name):
                if not directory.is_dir() or directory.is_symlink():
                    continue
                match = CHIP_DIRECTORY_PATTERN.fullmatch(directory.name)
                if match is None:
                    continue

                counts["scanned"] += 1
                source_path = str(directory.resolve())
                row = existing_by_path.get(source_path)
                if row is not None and row.state == "bootstrap_ignored":
                    counts["updated"] += 1
                    counts["bootstrap_ignored"] += 1
                    row.last_scanned_at = scan_now
                    row.updated_at = scan_now
                    continue
                observation = inspect_chip_directory(
                    directory,
                    sequencing_batch=match.group("sequencing_batch"),
                )
                if row is None:
                    row = WgsIntakeBatch(
                        source_path=observation.source_path,
                        chip_id=observation.chip_id,
                        sequencing_batch=observation.sequencing_batch,
                        first_seen_at=scan_now,
                        created_at=scan_now,
                    )
                    session.add(row)
                    existing_by_path[observation.source_path] = row
                    counts["created"] += 1
                else:
                    counts["updated"] += 1

                _apply_observation(row, observation, now=scan_now, bootstrap=is_bootstrap)
                if row.state in counts:
                    counts[row.state] += 1

            if is_bootstrap:
                scanner.bootstrap_completed_at = scan_now
            scanner.last_status = "success"
        except Exception as exc:
            counts["errors"] += 1
            scanner.last_status = "failed"
            scanner.last_error = str(exc)
            raise
        finally:
            scanner.last_scan_completed_at = scan_now
            scanner.next_scan_at = scan_now + timedelta(seconds=scan_interval_seconds)
            scanner.last_scan_duration_ms = max(0, int((time.monotonic() - started) * 1000))
            scanner.last_counts_json = dict(counts)
            scanner.updated_at = scan_now
            session.commit()

    return counts


def inspect_chip_directory(directory: Path, *, sequencing_batch: str) -> ChipObservation:
    barcode_path = directory / "BarcodeStat.txt"
    barcode_present = barcode_path.is_file() and not barcode_path.is_symlink()
    barcode_stat = barcode_path.stat() if barcode_present else None
    samples: dict[str, dict[int, FastqObservation]] = {}

    for child in sorted(directory.iterdir(), key=lambda item: item.name):
        if not child.is_file() or child.is_symlink():
            continue
        match = WGS_FASTQ_PATTERN.fullmatch(child.name)
        if match is None:
            continue
        stat = child.stat()
        sample = match.group("sample")
        samples.setdefault(sample, {})[int(match.group("read"))] = FastqObservation(
            name=child.name,
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
        )

    eligible_files: list[FastqObservation] = []
    eligible_pair_count = 0
    excluded_addon_pair_count = 0
    pair_issue_count = 0
    for sample, reads in samples.items():
        complete = set(reads) == {1, 2}
        if ADDON_SAMPLE_PATTERN.search(sample):
            if complete:
                excluded_addon_pair_count += 1
            continue
        if complete:
            eligible_pair_count += 1
            eligible_files.extend((reads[1], reads[2]))
        else:
            pair_issue_count += 1

    fingerprint = None
    if barcode_present:
        payload = {
            "schema_version": "wgs-t7-eligible-fingerprint.v1",
            "chip_id": directory.name,
            "sequencing_batch": sequencing_batch,
            "barcode_stat": {
                "size": barcode_stat.st_size,
                "mtime_ns": barcode_stat.st_mtime_ns,
            },
            "eligible_files": [
                {"name": item.name, "size": item.size, "mtime_ns": item.mtime_ns}
                for item in sorted(eligible_files, key=lambda value: value.name)
            ],
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    return ChipObservation(
        source_path=str(directory.resolve()),
        chip_id=directory.name,
        sequencing_batch=sequencing_batch,
        barcode_present=barcode_present,
        barcode_mtime_ns=barcode_stat.st_mtime_ns if barcode_stat else None,
        barcode_size=barcode_stat.st_size if barcode_stat else None,
        eligible_pair_count=eligible_pair_count,
        excluded_addon_pair_count=excluded_addon_pair_count,
        pair_issue_count=pair_issue_count,
        fingerprint=fingerprint,
    )


def list_wgs_t7_intake(
    *,
    session: Session,
    state: str | None,
    view: str,
    keyword: str | None,
    limit: int,
    offset: int,
) -> dict[str, object]:
    query = select(WgsIntakeBatch)
    if state:
        query = query.where(WgsIntakeBatch.state == state)
    elif view == "pending":
        query = query.where(
            WgsIntakeBatch.state.in_(("waiting_barcode_stat", "ready", "needs_review"))
        )
    elif view == "history":
        query = query.where(
            WgsIntakeBatch.state.in_(("no_new_wgs", "bootstrap_ignored"))
        )
    if keyword:
        search = f"%{keyword.strip()}%"
        query = query.where(
            or_(
                WgsIntakeBatch.chip_id.ilike(search),
                WgsIntakeBatch.sequencing_batch.ilike(search),
            )
        )

    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rows = session.scalars(
        query.order_by(WgsIntakeBatch.last_scanned_at.desc(), WgsIntakeBatch.chip_id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "items": [_public_batch_payload(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_wgs_t7_scanner_state(*, session: Session) -> dict[str, object]:
    row = session.get(WgsIntakeScannerState, SCANNER_STATE_ID)
    if row is None:
        return {
            "scanner": "wgs-observer",
            "root": "/bi/fastq/T7_Fastq",
            "enabled": False,
            "schedule_seconds": 1800,
            "auto_dispatch_enabled": False,
            "bootstrap_completed_at": None,
            "last_scan_started_at": None,
            "last_scan_completed_at": None,
            "next_scan_at": None,
            "last_scan_duration_ms": None,
            "last_status": "never_run",
            "last_counts": {},
            "last_error": None,
        }
    return {
        "scanner": "wgs-observer",
        "root": row.root_path,
        "enabled": row.scan_enabled,
        "schedule_seconds": row.scan_interval_seconds,
        "auto_dispatch_enabled": row.auto_dispatch_enabled,
        "bootstrap_completed_at": _iso_datetime(row.bootstrap_completed_at),
        "last_scan_started_at": _iso_datetime(row.last_scan_started_at),
        "last_scan_completed_at": _iso_datetime(row.last_scan_completed_at),
        "next_scan_at": _iso_datetime(row.next_scan_at),
        "last_scan_duration_ms": row.last_scan_duration_ms,
        "last_status": row.last_status,
        "last_counts": dict(row.last_counts_json or {}),
        "last_error": row.last_error,
    }


def _public_batch_payload(row: WgsIntakeBatch) -> dict[str, object]:
    return {
        "pipeline": "wgs",
        "chip_id": row.chip_id,
        "batch_id": row.chip_id,
        "sequencing_batch": row.sequencing_batch,
        "ready_state": row.state,
        "submit_state": "disabled",
        "analysis_id": row.analysis_id,
        "eligible_pair_count": row.eligible_pair_count,
        "excluded_addon_pair_count": row.excluded_addon_pair_count,
        "pair_issue_count": row.pair_issue_count,
        "last_error": row.last_error,
        "last_seen_at": _iso_datetime(row.last_scanned_at),
    }


def _iso_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _apply_observation(
    row: WgsIntakeBatch,
    observation: ChipObservation,
    *,
    now: datetime,
    bootstrap: bool,
) -> None:
    previous_state = row.state
    previous_error = row.last_error
    previous_fingerprint = row.eligible_fingerprint
    row.chip_id = observation.chip_id
    row.sequencing_batch = observation.sequencing_batch
    row.barcode_stat_mtime_ns = observation.barcode_mtime_ns
    row.barcode_stat_size = observation.barcode_size
    row.eligible_pair_count = observation.eligible_pair_count
    row.excluded_addon_pair_count = observation.excluded_addon_pair_count
    row.pair_issue_count = observation.pair_issue_count
    row.observed_fingerprint = observation.fingerprint
    row.last_scanned_at = now
    row.updated_at = now

    if previous_state == "bootstrap_ignored":
        row.last_error = None
        return

    if not observation.barcode_present:
        if previous_fingerprint is not None and previous_state in {
            "ready",
            "no_new_wgs",
            "needs_review",
        }:
            row.state = "needs_review"
            row.last_error = "eligible WGS input changed after ready"
        else:
            row.state = "waiting_barcode_stat"
            row.last_error = None
        return

    if bootstrap and row.eligible_fingerprint is None:
        row.state = "bootstrap_ignored"
        row.eligible_fingerprint = observation.fingerprint
        row.ready_at = now
        row.last_error = None
        return

    if (
        (
            previous_state in FINGERPRINT_FROZEN_STATES
            or (
                previous_state == "needs_review"
                and previous_error == "eligible WGS input changed after ready"
            )
        )
        and previous_fingerprint is not None
        and observation.fingerprint != previous_fingerprint
    ):
        row.state = "needs_review"
        row.last_error = "eligible WGS input changed after ready"
        return

    if observation.pair_issue_count:
        row.state = "needs_review"
        row.last_error = "non-addon WGS FASTQ pairs are incomplete"
        if row.eligible_fingerprint is None:
            row.eligible_fingerprint = observation.fingerprint
        return

    row.state = "ready" if observation.eligible_pair_count else "no_new_wgs"
    row.eligible_fingerprint = observation.fingerprint
    row.ready_at = row.ready_at or now
    row.last_error = None


def _acquire_scanner_lock(session: Session) -> bool:
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return True
    return bool(
        session.scalar(
            text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
            {"lock_id": SCANNER_ADVISORY_LOCK_ID},
        )
    )
