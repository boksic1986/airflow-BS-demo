from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import wgs_t7_intake
from app.models import AnalysisRun, Base, WgsIntakeBatch, WgsIntakeScannerState
from app.wgs_t7_intake import scan_wgs_t7_intake


def make_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def chip(root: Path, name: str, *, ready: bool = False, files: tuple[str, ...] = ()) -> Path:
    directory = root / name
    directory.mkdir()
    if ready:
        (directory / "BarcodeStat.txt").write_text("complete\n", encoding="utf-8")
    for filename in files:
        (directory / filename).write_bytes(filename.encode("utf-8"))
    return directory


def scan(sessions, root: Path, *, now: datetime):
    return scan_wgs_t7_intake(
        session_factory=sessions,
        root=root,
        now=now,
    )


def set_mtime(path: Path, when: datetime) -> None:
    timestamp = when.timestamp()
    os.utime(path, (timestamp, timestamp))


def complete_after(directory: Path, when: datetime) -> None:
    marker = directory / "BarcodeStat.txt"
    marker.write_text("complete\n", encoding="utf-8")
    set_mtime(marker, when)


def test_first_scan_bootstraps_completed_batches_without_creating_runs(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    completed = chip(
        root,
        "998th_20250409A_E250065164",
        ready=True,
        files=("NORMAL-WGS.R1.fq.gz", "NORMAL-WGS.R2.fq.gz"),
    )
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    set_mtime(completed / "BarcodeStat.txt", baseline - timedelta(minutes=1))
    chip(root, "999th_20250409B_E250065165", ready=False)
    chip(root, "invalid-directory", ready=True)
    sessions = make_sessionmaker()

    result = scan(sessions, root, now=baseline)

    assert result == {
        "scanned": 2,
        "created": 0,
        "updated": 0,
        "ready": 0,
        "needs_review": 0,
        "no_new_wgs": 0,
        "errors": 0,
    }
    with sessions() as session:
        assert session.scalars(select(WgsIntakeBatch)).all() == []
        assert session.scalars(select(AnalysisRun)).all() == []
        scanner = session.scalar(select(WgsIntakeScannerState))
        assert scanner is not None
        assert scanner.first_scan_at.replace(tzinfo=timezone.utc) == baseline
        assert scanner.last_scan_at.replace(tzinfo=timezone.utc) == baseline
        assert scanner.last_scanned_directory_count == 2
        assert scanner.last_error is None


def test_historical_completed_batch_skips_future_fastq_enumeration_without_a_row(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(
        root,
        "998th_20250409A_E250065164",
        ready=True,
        files=("NORMAL-WGS.R1.fq.gz", "NORMAL-WGS.R2.fq.gz"),
    )
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    set_mtime(directory / "BarcodeStat.txt", baseline - timedelta(minutes=1))
    scan(sessions, root, now=baseline)

    monkeypatch.setattr(
        wgs_t7_intake,
        "inspect_chip_directory",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("historical FASTQ files must not be enumerated")
        ),
    )
    result = scan(
        sessions, root, now=datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc)
    )

    assert result["errors"] == 0
    with sessions() as session:
        assert session.scalars(select(WgsIntakeBatch)).all() == []


def test_waiting_directory_is_not_persisted_until_barcode_stat_appears(
    tmp_path: Path,
) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    waiting = chip(root, "2200th_20260821A_E250208843")
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)

    scan(sessions, root, now=baseline)
    scan(sessions, root, now=baseline + timedelta(minutes=30))
    with sessions() as session:
        assert session.scalars(select(WgsIntakeBatch)).all() == []

    complete_after(waiting, baseline + timedelta(minutes=31))
    scan(sessions, root, now=baseline + timedelta(minutes=60))
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "no_new_wgs"


def test_post_bootstrap_ready_batch_classifies_normal_and_addon_pairs(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    waiting = chip(root, "2201th_20260821B_E250208844")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    complete_after(waiting, datetime(2026, 8, 29, 8, 1, tzinfo=timezone.utc))
    for filename in (
        "NEW1-WGS.R1.fq.gz",
        "NEW1-WGS.R2.fq.gz",
        "NEW2-WGS.R1.fq.gz",
        "NEW2-WGS.R2.fq.gz",
        "NEW1-S1-WGS.R1.fq.gz",
        "NEW1-S1-WGS.R2.fq.gz",
        "NEW2-S2-WGS.R1.fq.gz",
        "NEW2-S2-WGS.R2.fq.gz",
    ):
        (waiting / filename).write_bytes(b"fq")

    result = scan(sessions, root, now=datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc))

    assert result["ready"] == 1
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row.state == "ready"
        assert row.eligible_pair_count == 2
        assert row.excluded_addon_pair_count == 2
        assert row.pair_issue_count == 0
        assert row.analysis_id is None
        assert row.eligible_fingerprint


def test_broken_symlink_pairs_are_classified_by_entry_name(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2210th_20260825A_E250208851")
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    scan(sessions, root, now=baseline)
    complete_after(directory, baseline + timedelta(minutes=1))
    r1_target = tmp_path / "missing-r1.fq.gz"
    r2_target = tmp_path / "missing-r2.fq.gz"
    (directory / "NORMAL-WGS.R1.fq.gz").symlink_to(r1_target)
    (directory / "NORMAL-WGS.R2.fq.gz").symlink_to(r2_target)

    result = scan(sessions, root, now=baseline + timedelta(minutes=30))

    assert result["ready"] == 1
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "ready"
        assert row.eligible_pair_count == 1
        assert row.pair_issue_count == 0
        fingerprint = row.eligible_fingerprint

    r1_target.write_bytes(b"target appeared after discovery")
    r2_target.write_bytes(b"target contents are validated later")
    scan(sessions, root, now=baseline + timedelta(minutes=60))
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "ready"
        assert row.eligible_fingerprint == fingerprint


def test_regular_hardlink_and_symlink_entries_share_pairing_rules(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2211th_20260825B_E250208852")
    source = tmp_path / "source.fq.gz"
    source.write_bytes(b"fq")
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    scan(sessions, root, now=baseline)
    complete_after(directory, baseline + timedelta(minutes=1))
    os.link(source, directory / "HARD-WGS.R1.fq.gz")
    (directory / "HARD-WGS.R2.fq.gz").write_bytes(b"fq")
    (directory / "SOFT-WGS.R1.fq.gz").symlink_to(tmp_path / "missing-soft-r1")
    (directory / "SOFT-WGS.R2.fq.gz").symlink_to(tmp_path / "missing-soft-r2")
    (directory / "ADDON-S1-WGS.R1.fq.gz").symlink_to(tmp_path / "missing-addon-r1")
    (directory / "ADDON-S1-WGS.R2.fq.gz").symlink_to(tmp_path / "missing-addon-r2")

    scan(sessions, root, now=baseline + timedelta(minutes=30))

    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "ready"
        assert row.eligible_pair_count == 2
        assert row.excluded_addon_pair_count == 1
        assert row.pair_issue_count == 0


def test_no_wgs_or_only_addon_is_no_new_wgs_and_candidate_count_is_informational(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    empty = chip(root, "2202th_20260821C_E250208849")
    addon = chip(root, "2203th_20260822A_E250208832")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    for directory in (empty, addon):
        complete_after(directory, datetime(2026, 8, 29, 8, 1, tzinfo=timezone.utc))
    (addon / "SAMPLE-S1-WGS.R1.fq.gz").write_bytes(b"1")
    (addon / "SAMPLE-S1-WGS.R2.fq.gz").write_bytes(b"2")

    scan(sessions, root, now=datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc))

    with sessions() as session:
        rows = {row.chip_id: row for row in session.scalars(select(WgsIntakeBatch)).all()}
        assert rows[empty.name].state == "no_new_wgs"
        assert rows[empty.name].eligible_pair_count == 0
        assert rows[addon.name].state == "no_new_wgs"
        assert rows[addon.name].excluded_addon_pair_count == 1


def test_yf_pairs_are_ignored_in_a_mixed_clinical_batch(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2215th_20260825F_E250208856")
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    scan(sessions, root, now=baseline)
    complete_after(directory, baseline + timedelta(minutes=1))
    for filename in (
        "WGS26080504-WGS.R1.fq.gz",
        "WGS26080504-WGS.R2.fq.gz",
        "YF26080504-WGS.R1.fq.gz",
        "YF26080504-WGS.R2.fq.gz",
    ):
        (directory / filename).write_bytes(b"fq")

    scan(sessions, root, now=baseline + timedelta(minutes=30))

    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "ready"
        assert row.eligible_pair_count == 1
        assert row.excluded_addon_pair_count == 0
        assert row.pair_issue_count == 0
        fingerprint = row.eligible_fingerprint

    (directory / "YF26080505-WGS.R1.fq.gz").write_bytes(b"fq")
    (directory / "YF26080505-WGS.R2.fq.gz").write_bytes(b"fq")
    scan(sessions, root, now=baseline + timedelta(minutes=60))
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "ready"
        assert row.eligible_fingerprint == fingerprint


def test_ready_v2_fingerprint_with_yf_pair_upgrades_without_false_drift(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2218th_20260825I_E250208859")
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    scan(sessions, root, now=baseline)
    complete_after(directory, baseline + timedelta(minutes=1))
    file_names = (
        "WGS26080504-WGS.R1.fq.gz",
        "WGS26080504-WGS.R2.fq.gz",
        "YF26080504-WGS.R1.fq.gz",
        "YF26080504-WGS.R2.fq.gz",
    )
    for filename in file_names:
        (directory / filename).write_bytes(b"fq")
    scan(sessions, root, now=baseline + timedelta(minutes=30))

    barcode_stat = (directory / "BarcodeStat.txt").stat()
    v2_payload = {
        "schema_version": "wgs-t7-entry-fingerprint.v2",
        "chip_id": directory.name,
        "sequencing_batch": "20260825I",
        "barcode_stat": {
            "size": barcode_stat.st_size,
            "mtime_ns": barcode_stat.st_mtime_ns,
        },
        "eligible_file_names": sorted(file_names),
    }
    old_v2_fingerprint = hashlib.sha256(
        json.dumps(v2_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    with sessions.begin() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        row.eligible_fingerprint = old_v2_fingerprint

    scan(sessions, root, now=baseline + timedelta(minutes=60))

    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "ready"
        assert row.eligible_pair_count == 1
        assert row.eligible_fingerprint != old_v2_fingerprint
        assert row.last_error is None


def test_yf_only_batch_is_no_new_wgs(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2216th_20260825G_E250208857")
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    scan(sessions, root, now=baseline)
    complete_after(directory, baseline + timedelta(minutes=1))
    (directory / "YF26080504-WGS.R1.fq.gz").write_bytes(b"1")
    (directory / "YF26080504-WGS.R2.fq.gz").write_bytes(b"2")

    result = scan(sessions, root, now=baseline + timedelta(minutes=30))

    assert result["no_new_wgs"] == 1
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "no_new_wgs"
        assert row.eligible_pair_count == 0
        assert row.excluded_addon_pair_count == 0
        assert row.pair_issue_count == 0


def test_incomplete_yf_sample_does_not_require_review(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2217th_20260825H_E250208858")
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    scan(sessions, root, now=baseline)
    complete_after(directory, baseline + timedelta(minutes=1))
    (directory / "YF26080504-WGS.R1.fq.gz").symlink_to(tmp_path / "missing-yf-r1")

    result = scan(sessions, root, now=baseline + timedelta(minutes=30))

    assert result["needs_review"] == 0
    assert result["no_new_wgs"] == 1
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "no_new_wgs"
        assert row.eligible_pair_count == 0
        assert row.pair_issue_count == 0


def test_historical_no_new_wgs_becomes_ready_when_named_pair_appears(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2212th_20260825C_E250208853")
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    scan(sessions, root, now=baseline)
    complete_after(directory, baseline + timedelta(minutes=1))
    scan(sessions, root, now=baseline + timedelta(minutes=30))

    (directory / "LATE-WGS.R1.fq.gz").write_bytes(b"1")
    (directory / "LATE-WGS.R2.fq.gz").write_bytes(b"2")
    result = scan(sessions, root, now=baseline + timedelta(minutes=60))

    assert result["ready"] == 1
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "ready"
        assert row.eligible_pair_count == 1
        assert row.last_error is None


def test_historical_no_new_wgs_requires_review_when_only_one_read_appears(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2213th_20260825D_E250208854")
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    scan(sessions, root, now=baseline)
    complete_after(directory, baseline + timedelta(minutes=1))
    scan(sessions, root, now=baseline + timedelta(minutes=30))

    (directory / "LATE-WGS.R1.fq.gz").symlink_to(tmp_path / "missing-late-r1")
    result = scan(sessions, root, now=baseline + timedelta(minutes=60))

    assert result["needs_review"] == 1
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "needs_review"
        assert row.pair_issue_count == 1


def test_unpaired_normal_fastq_requires_review(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2204th_20260822B_E250208833")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    complete_after(directory, datetime(2026, 8, 29, 8, 1, tzinfo=timezone.utc))
    (directory / "NORMAL-WGS.R1.fq.gz").write_bytes(b"1")

    result = scan(sessions, root, now=datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc))

    assert result["needs_review"] == 1
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row.state == "needs_review"
        assert row.pair_issue_count == 1
        assert row.last_error == "non-addon WGS FASTQ pairs are incomplete"

    (directory / "NORMAL-WGS.R2.fq.gz").write_bytes(b"2")
    scan(sessions, root, now=datetime(2026, 8, 29, 9, 0, tzinfo=timezone.utc))
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row.state == "ready"
        assert row.pair_issue_count == 0
        assert row.last_error is None


def test_ready_name_drift_requires_review_but_content_and_addon_changes_do_not(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2205th_20260823A_E250207440")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    complete_after(directory, datetime(2026, 8, 29, 8, 1, tzinfo=timezone.utc))
    r1 = directory / "NORMAL-WGS.R1.fq.gz"
    r2 = directory / "NORMAL-WGS.R2.fq.gz"
    r1.write_bytes(b"1")
    r2.write_bytes(b"2")
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc))

    (directory / "NORMAL-S1-WGS.R1.fq.gz").write_bytes(b"3")
    (directory / "NORMAL-S1-WGS.R2.fq.gz").write_bytes(b"4")
    scan(sessions, root, now=datetime(2026, 8, 29, 9, 0, tzinfo=timezone.utc))
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row.state == "ready"
        assert row.excluded_addon_pair_count == 1
        original_fingerprint = row.eligible_fingerprint

    r1.write_bytes(b"changed-content-is-validated-later")
    scan(sessions, root, now=datetime(2026, 8, 29, 9, 30, tzinfo=timezone.utc))
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row.state == "ready"
        assert row.eligible_fingerprint == original_fingerprint
        assert row.last_error is None

    r1.rename(directory / "RENAMED-WGS.R1.fq.gz")
    scan(sessions, root, now=datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc))
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row.state == "needs_review"
        assert row.eligible_fingerprint == original_fingerprint
        assert row.last_error == "eligible WGS input changed after ready"


def test_ready_v1_regular_file_fingerprint_upgrades_without_false_drift(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2214th_20260825E_E250208855")
    sessions = make_sessionmaker()
    baseline = datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    scan(sessions, root, now=baseline)
    complete_after(directory, baseline + timedelta(minutes=1))
    r1 = directory / "LEGACY-WGS.R1.fq.gz"
    r2 = directory / "LEGACY-WGS.R2.fq.gz"
    r1.write_bytes(b"r1")
    r2.write_bytes(b"r2")
    scan(sessions, root, now=baseline + timedelta(minutes=30))

    barcode_stat = (directory / "BarcodeStat.txt").stat()
    legacy_payload = {
        "schema_version": "wgs-t7-eligible-fingerprint.v1",
        "chip_id": directory.name,
        "sequencing_batch": "20260825E",
        "barcode_stat": {
            "size": barcode_stat.st_size,
            "mtime_ns": barcode_stat.st_mtime_ns,
        },
        "eligible_files": [
            {"name": path.name, "size": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns}
            for path in (r1, r2)
        ],
    }
    legacy_fingerprint = hashlib.sha256(
        json.dumps(legacy_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    with sessions.begin() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        row.eligible_fingerprint = legacy_fingerprint

    scan(sessions, root, now=baseline + timedelta(minutes=60))

    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row is not None
        assert row.state == "ready"
        assert row.eligible_fingerprint != legacy_fingerprint
        assert row.last_error is None


def test_repeated_scan_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2206th_20260823B_E250208848")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    complete_after(directory, datetime(2026, 8, 29, 8, 1, tzinfo=timezone.utc))
    (directory / "NORMAL-WGS.R1.fq.gz").write_bytes(b"1")
    (directory / "NORMAL-WGS.R2.fq.gz").write_bytes(b"2")
    first = scan(sessions, root, now=datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc))
    second = scan(sessions, root, now=datetime(2026, 8, 29, 9, 0, tzinfo=timezone.utc))

    assert first["ready"] == 1
    assert second["created"] == 0
    with sessions() as session:
        assert len(session.scalars(select(WgsIntakeBatch)).all()) == 1
        assert session.scalars(select(AnalysisRun)).all() == []


def test_ready_batch_losing_barcode_stat_requires_review(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2207th_20260824A_E250208850")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    marker = directory / "BarcodeStat.txt"
    marker.write_text("complete\n", encoding="utf-8")
    set_mtime(marker, datetime(2026, 8, 29, 8, 1, tzinfo=timezone.utc))
    (directory / "NORMAL-WGS.R1.fq.gz").write_bytes(b"1")
    (directory / "NORMAL-WGS.R2.fq.gz").write_bytes(b"2")
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc))

    marker.unlink()
    scan(sessions, root, now=datetime(2026, 8, 29, 9, 0, tzinfo=timezone.utc))

    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row.state == "needs_review"
        assert row.last_error == "eligible WGS input changed after ready"
