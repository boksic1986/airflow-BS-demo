from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Callable

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from .models import WgsIntakeBatch, WgsIntakeScannerState


CHIP_DIRECTORY_PATTERN = re.compile(
    r"^(?P<chip_number>\d+)th_(?P<sequencing_batch>\d{8}[A-Z])_[A-Za-z0-9.-]+$"
)
WGS_FASTQ_PATTERN = re.compile(r"^(?P<sample>.+)-WGS\.R(?P<read>[12])\.fq\.gz$")
ADDON_SAMPLE_PATTERN = re.compile(r"-S\d+$")
NON_CLINICAL_SAMPLE_PREFIX = "YF"
SCANNER_STATE_ID = 1
SCANNER_ADVISORY_LOCK_ID = 743_701_143_829
FINGERPRINT_FROZEN_STATES = {"ready"}
PERSISTED_STATES = {"ready", "needs_review", "no_new_wgs"}


@dataclass(frozen=True)
class FastqObservation:
    name: str


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
    legacy_fingerprint: str | None
    pre_yf_filter_fingerprint: str | None


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
    counts = {
        "scanned": 0,
        "created": 0,
        "updated": 0,
        "ready": 0,
        "needs_review": 0,
        "no_new_wgs": 0,
        "errors": 0,
    }

    with session_factory() as session:
        if not _acquire_scanner_lock(session):
            return counts

        scanner = session.get(WgsIntakeScannerState, SCANNER_STATE_ID)
        is_bootstrap = scanner is None or scanner.first_scan_at is None
        if scanner is None:
            scanner = WgsIntakeScannerState(id=SCANNER_STATE_ID)
            session.add(scanner)

        scanner.last_error = None

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
                if is_bootstrap:
                    continue
                source_path = str(directory.resolve())
                row = existing_by_path.get(source_path)
                if row is None:
                    barcode = directory / "BarcodeStat.txt"
                    if (
                        not barcode.is_file()
                        or barcode.is_symlink()
                        or barcode.stat().st_mtime_ns
                        <= int(scanner.first_scan_at.timestamp() * 1_000_000_000)
                    ):
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

                _apply_observation(row, observation, now=scan_now)
                if row.state in counts:
                    counts[row.state] += 1

            if is_bootstrap:
                scanner.first_scan_at = scan_now
        except Exception as exc:
            counts["errors"] += 1
            scanner.last_error = str(exc)
            raise
        finally:
            scanner.last_scan_at = scan_now
            scanner.last_scanned_directory_count = counts["scanned"]
            session.commit()

    return counts


def inspect_chip_directory(directory: Path, *, sequencing_batch: str) -> ChipObservation:
    barcode_path = directory / "BarcodeStat.txt"
    barcode_present = barcode_path.is_file() and not barcode_path.is_symlink()
    barcode_stat = barcode_path.stat() if barcode_present else None
    samples: dict[str, dict[int, FastqObservation]] = {}
    legacy_regular_files: list[dict[str, int | str]] = []

    for child in sorted(directory.iterdir(), key=lambda item: item.name):
        is_symlink = child.is_symlink()
        if not is_symlink and not child.is_file():
            continue
        match = WGS_FASTQ_PATTERN.fullmatch(child.name)
        if match is None:
            continue
        sample = match.group("sample")
        samples.setdefault(sample, {})[int(match.group("read"))] = FastqObservation(name=child.name)
        if not is_symlink:
            stat = child.stat()
            legacy_regular_files.append(
                {"name": child.name, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            )

    eligible_files: list[FastqObservation] = []
    pre_yf_filter_files: list[FastqObservation] = []
    eligible_pair_count = 0
    excluded_addon_pair_count = 0
    pair_issue_count = 0
    for sample, reads in samples.items():
        complete = set(reads) == {1, 2}
        is_addon = ADDON_SAMPLE_PATTERN.search(sample) is not None
        if complete and not is_addon:
            pre_yf_filter_files.extend((reads[1], reads[2]))
        if sample.startswith(NON_CLINICAL_SAMPLE_PREFIX):
            continue
        if is_addon:
            if complete:
                excluded_addon_pair_count += 1
            continue
        if complete:
            eligible_pair_count += 1
            eligible_files.extend((reads[1], reads[2]))
        else:
            pair_issue_count += 1

    fingerprint = None
    legacy_fingerprint = None
    pre_yf_filter_fingerprint = None
    if barcode_present:
        payload = {
            "schema_version": "wgs-t7-entry-fingerprint.v3",
            "chip_id": directory.name,
            "sequencing_batch": sequencing_batch,
            "barcode_stat": {
                "size": barcode_stat.st_size,
                "mtime_ns": barcode_stat.st_mtime_ns,
            },
            "eligible_file_names": sorted(item.name for item in eligible_files),
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        eligible_names = {item.name for item in eligible_files}
        legacy_payload = {
            "schema_version": "wgs-t7-eligible-fingerprint.v1",
            "chip_id": directory.name,
            "sequencing_batch": sequencing_batch,
            "barcode_stat": {
                "size": barcode_stat.st_size,
                "mtime_ns": barcode_stat.st_mtime_ns,
            },
            "eligible_files": sorted(
                (item for item in legacy_regular_files if item["name"] in eligible_names),
                key=lambda item: str(item["name"]),
            ),
        }
        legacy_fingerprint = hashlib.sha256(
            json.dumps(legacy_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        pre_yf_filter_payload = {
            "schema_version": "wgs-t7-entry-fingerprint.v2",
            "chip_id": directory.name,
            "sequencing_batch": sequencing_batch,
            "barcode_stat": {
                "size": barcode_stat.st_size,
                "mtime_ns": barcode_stat.st_mtime_ns,
            },
            "eligible_file_names": sorted(item.name for item in pre_yf_filter_files),
        }
        pre_yf_filter_fingerprint = hashlib.sha256(
            json.dumps(
                pre_yf_filter_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
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
        legacy_fingerprint=legacy_fingerprint,
        pre_yf_filter_fingerprint=pre_yf_filter_fingerprint,
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
    query = select(WgsIntakeBatch).where(WgsIntakeBatch.state.in_(PERSISTED_STATES))
    if state in PERSISTED_STATES:
        query = query.where(WgsIntakeBatch.state == state)
    elif view == "pending":
        query = query.where(WgsIntakeBatch.state.in_(("ready", "needs_review")))
    elif view == "history":
        query = query.where(WgsIntakeBatch.state == "no_new_wgs")
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


def get_wgs_t7_scanner_state(
    *,
    session: Session,
    root: str = "/bi/fastq/T7_Fastq",
    enabled: bool = False,
    schedule_seconds: int = 1800,
    auto_dispatch_enabled: bool = False,
) -> dict[str, object]:
    row = session.get(WgsIntakeScannerState, SCANNER_STATE_ID)
    return {
        "scanner": "wgs-intake-scanner",
        "root": root,
        "enabled": enabled,
        "schedule_seconds": schedule_seconds,
        "auto_dispatch_enabled": auto_dispatch_enabled,
        "first_scan_at": _iso_datetime(row.first_scan_at) if row else None,
        "last_scan_at": _iso_datetime(row.last_scan_at) if row else None,
        "last_scanned_directory_count": (
            row.last_scanned_directory_count if row else 0
        ),
        "last_error": row.last_error if row else None,
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

    if not observation.barcode_present:
        row.state = "needs_review"
        row.last_error = "eligible WGS input changed after ready"
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
        and previous_fingerprint
        not in {
            observation.fingerprint,
            observation.legacy_fingerprint,
            observation.pre_yf_filter_fingerprint,
        }
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
