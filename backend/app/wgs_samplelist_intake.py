"""Batch-only, read-only Samplelist discovery. Never persist TSV payloads."""
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat

from sqlalchemy import select

from .models import WgsIntakeBatch, WgsIntakeScannerState, WgsSamplelistSource, WgsSamplelistObservation
from .wgs_t7_intake import _acquire_scanner_lock, _apply_observation, inspect_chip_directory

MAX_FILES = 10000
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 50000
BATCH = re.compile(r"[0-9]{8}[A-Z]")
SAFE_NAME = re.compile(r"[A-Za-z0-9_.-]+")


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _safe_root(value):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("unsafe_source_root")
    if any(part.is_symlink() for part in (path, *path.parents)) or not path.is_dir():
        raise ValueError("unavailable_source_root")
    return path.resolve()


def _entries(root):
    result = []
    with os.scandir(root) as entries:
        for entry in entries:
            if len(result) >= MAX_FILES:
                raise ValueError("enumeration_limit")
            result.append(Path(entry.path))
    return sorted(result, key=lambda path: path.name)


def _stat_token(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _read_batches(path, platform_id):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
        raise ValueError("unsafe_samplelist_file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        opened = os.fstat(handle.fileno())
        if _stat_token(before) != _stat_token(opened):
            raise ValueError("samplelist_changed")
        data = handle.read(MAX_BYTES + 1)
        handle.seek(0)
        repeated = handle.read(MAX_BYTES + 1)
        after = os.fstat(handle.fileno())
    if (len(data) > MAX_BYTES or data != repeated or _stat_token(before) != _stat_token(after)
            or _stat_token(before) != _stat_token(path.lstat())):
        raise ValueError("samplelist_changed")
    if not data.endswith(b"\n"):
        raise ValueError("incomplete_samplelist")
    reader = csv.reader(io.StringIO(data.decode("utf-8-sig")), delimiter="\t", strict=True)
    header = next(reader, [])
    if len(set(header)) != len(header) or not {"batchNo", "sampleId"}.issubset(header):
        raise ValueError("invalid_samplelist")
    batches = set()
    for index, values in enumerate(reader):
        if index >= MAX_ROWS or len(values) != len(header):
            raise ValueError("invalid_samplelist")
        row = dict(zip(header, values))
        batch = row["batchNo"].strip()
        if not BATCH.fullmatch(batch) or not row["sampleId"].strip():
            raise ValueError("invalid_samplelist")
        if "techPlatformCode" in row and row["techPlatformCode"].strip() != platform_id:
            continue
        if "itemCode" in row and row["itemCode"].strip() != "WGS":
            continue
        batches.add(batch)
    version = _digest(data)
    token = _digest(json.dumps([_stat_token(before), version]).encode())
    return sorted(batches), version, token


def _review(row, reason):
    row.state = "needs_review"
    row.reason_code = reason
    row.last_error = reason


def _bind(row, directories, root, all_rows, now, ignored):
    row.last_scanned_at = now
    row.updated_at = now
    if row.source_path is None:
        matches = [path for path in directories if f"_{row.sequencing_batch}_" in path.name]
        if not matches:
            row.state, row.reason_code = "waiting_sequencing", "sequencing_directory_pending"
            return
        if len(matches) != 1:
            _review(row, "ambiguous_sequencing_directory")
            return
        path = matches[0]
    else:
        path = Path(row.source_path)
    try:
        value = path.lstat()
        if (path.parent != root or not SAFE_NAME.fullmatch(path.name) or not stat.S_ISDIR(value.st_mode)
                or path.name in ignored):
            raise ValueError("unsafe_directory")
        identity = f"{value.st_dev}:{value.st_ino}"
        if row.source_path and row.bound_directory_identity != identity:
            raise ValueError("bound_directory_changed")
        if any(other.id != row.id and (other.source_path == str(path) or other.chip_id == path.name) for other in all_rows):
            _review(row, "directory_owned_by_other_intake")
            return
        if row.source_path is None:
            row.source_path, row.chip_id = str(path), path.name
            row.bound_directory_identity = identity
        marker = path / "BarcodeStat.txt"
        if not marker.exists() and not marker.is_symlink():
            if row.eligible_fingerprint or row.analysis_id:
                _review(row, "bound_data_changed")
            else:
                row.state, row.reason_code = "waiting_data", "barcode_pending"
            return
        if marker.is_symlink() or not marker.is_file():
            _review(row, "unsafe_barcode_marker")
            return
        observation = inspect_chip_directory(path, sequencing_batch=row.sequencing_batch)
        if f"{path.lstat().st_dev}:{path.lstat().st_ino}" != identity:
            raise ValueError("bound_directory_changed")
        _apply_observation(row, observation, now=now)
        if row.state == "no_new_wgs" and not row.analysis_id:
            row.ready_at = None
        row.reason_code = "input_readiness_conflict" if row.state == "needs_review" else None
        row.last_error = row.reason_code
    except (OSError, ValueError):
        _review(row, "bound_directory_unavailable")


def scan_wgs_samplelist_intake(*, session_factory, root, samplelist_root, project_id,
        platform_id, root_id, now=None, scan_interval_seconds=600, scan_enabled=False,
        auto_dispatch_enabled=False, ignored_chip_ids=(), configured_source_identity=None):
    counts = dict.fromkeys(("scanned", "created", "updated", "ready", "needs_review", "no_new_wgs", "errors"), 0)
    if not scan_enabled:
        return counts
    if not project_id or platform_id != "T7" or not root_id:
        raise ValueError("invalid_samplelist_context")
    if configured_source_identity is not None and not re.fullmatch(r"[0-9a-f]{64}", configured_source_identity):
        raise ValueError("invalid_configured_source_identity")
    now = now or datetime.now(timezone.utc)
    with session_factory() as session:
        if not _acquire_scanner_lock(session):
            return counts
        scanner = session.get(WgsIntakeScannerState, 1)
        if scanner is None:
            scanner = WgsIntakeScannerState(id=1)
            session.add(scanner)
        try:
            source_root, fastq_root = _safe_root(samplelist_root), _safe_root(root)
            identity = [str(source_root), str(fastq_root), project_id, platform_id, root_id]
            if configured_source_identity is not None:
                identity.append(configured_source_identity)
            source_id = _digest(json.dumps(identity).encode())
            source = session.get(WgsSamplelistSource, source_id)
            if source is None:
                source = WgsSamplelistSource(source_identity=source_id, baseline_complete=False)
                session.add(source)
                session.flush()
            source.last_scan_at = now
            files = [path for path in _entries(source_root) if path.name.startswith("Samplelist_") and path.name.endswith(".txt")]
            directories = _entries(fastq_root)
            observations = {row.file_identity: row for row in session.scalars(select(WgsSamplelistObservation).where(WgsSamplelistObservation.source_identity == source_id))}
            all_rows = list(session.scalars(select(WgsIntakeBatch)))
            scoped = {row.sequencing_batch: row for row in all_rows if row.project_id == project_id and row.platform_id == platform_id}
            for path in files:
                counts["scanned"] += 1
                key = _digest(path.name.encode())
                observation = observations.get(key)
                if observation is None:
                    observation = WgsSamplelistObservation(source_identity=source_id, file_identity=key,
                        is_baseline=not source.baseline_complete, stable_count=0, last_seen_at=now)
                    session.add(observation)
                    observations[key] = observation
                observation.last_seen_at = now
                if observation.is_baseline:
                    continue
                try:
                    batches, version, token = _read_batches(path, platform_id)
                except (OSError, ValueError, UnicodeError, csv.Error):
                    observation.stable_count = 0
                    observation.reason_code = "samplelist_unreadable_or_invalid"
                    counts["errors"] += 1
                    continue
                observation.stable_count = observation.stable_count + 1 if observation.observation_token == token else 1
                observation.observed_version, observation.observation_token = version, token
                observation.reason_code = None
                if observation.stable_count < 2:
                    continue
                for batch in batches:
                    row = scoped.get(batch)
                    if row is None:
                        row = WgsIntakeBatch(discovery_mode="samplelist_batches", project_id=project_id,
                            platform_id=platform_id, root_id=root_id, source_identity=source_id,
                            source_version=version, sequencing_batch=batch, state="waiting_sequencing",
                            first_seen_at=now, created_at=now, last_scanned_at=now)
                        session.add(row)
                        scoped[batch] = row
                        all_rows.append(row)
                        counts["created"] += 1
                    elif row.root_id != root_id or row.source_identity != source_id:
                        _review(row, "source_context_conflict")
                    elif not row.analysis_id:
                        row.source_version = version
                        counts["updated"] += 1
            session.flush()
            for row in scoped.values():
                if row.source_identity != source_id or row.root_id != root_id or row.reason_code == "source_context_conflict":
                    continue
                _bind(row, directories, fastq_root, all_rows, now, frozenset(ignored_chip_ids))
                if row.state in counts:
                    counts[row.state] += 1
            source.baseline_complete = True
            source.first_scan_at = source.first_scan_at or now
            source.reason_code = None
            scanner.first_scan_at = scanner.first_scan_at or now
            scanner.last_error = None
        except (OSError, ValueError):
            counts["errors"] += 1
            scanner.last_error = "samplelist_scan_unavailable"
        scanner.last_scan_at = now
        scanner.last_scanned_directory_count = counts["scanned"]
        session.commit()
    return counts
