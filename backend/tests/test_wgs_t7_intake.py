from __future__ import annotations

from datetime import datetime, timezone
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


def test_first_scan_bootstraps_completed_batches_without_creating_runs(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    chip(
        root,
        "998th_20250409A_E250065164",
        ready=True,
        files=("NORMAL-WGS.R1.fq.gz", "NORMAL-WGS.R2.fq.gz"),
    )
    chip(root, "999th_20250409B_E250065165", ready=False)
    chip(root, "invalid-directory", ready=True)
    sessions = make_sessionmaker()

    result = scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))

    assert result == {
        "scanned": 2,
        "created": 2,
        "updated": 0,
        "ready": 0,
        "needs_review": 0,
        "bootstrap_ignored": 1,
        "errors": 0,
    }
    with sessions() as session:
        rows = session.scalars(select(WgsIntakeBatch).order_by(WgsIntakeBatch.chip_id)).all()
        assert [(row.chip_id, row.sequencing_batch, row.state) for row in rows] == [
            ("998th_20250409A_E250065164", "20250409A", "bootstrap_ignored"),
            ("999th_20250409B_E250065165", "20250409B", "waiting_barcode_stat"),
        ]
        assert session.scalars(select(AnalysisRun)).all() == []
        scanner = session.scalar(select(WgsIntakeScannerState))
        assert scanner is not None
        assert scanner.bootstrap_completed_at is not None
        assert scanner.scan_interval_seconds == 1800
        assert scanner.auto_dispatch_enabled is False


def test_bootstrap_ignored_batch_skips_future_fastq_enumeration(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    chip(
        root,
        "998th_20250409A_E250065164",
        ready=True,
        files=("NORMAL-WGS.R1.fq.gz", "NORMAL-WGS.R2.fq.gz"),
    )
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))

    monkeypatch.setattr(
        wgs_t7_intake,
        "inspect_chip_directory",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("bootstrap-ignored FASTQ files must not be enumerated again")
        ),
    )
    result = scan(
        sessions, root, now=datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc)
    )

    assert result["bootstrap_ignored"] == 1
    assert result["errors"] == 0


def test_post_bootstrap_ready_batch_classifies_normal_and_addon_pairs(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    waiting = chip(root, "2201th_20260821B_E250208844")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    (waiting / "BarcodeStat.txt").write_text("complete\n", encoding="utf-8")
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


def test_no_wgs_or_only_addon_is_no_new_wgs_and_candidate_count_is_informational(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    empty = chip(root, "2202th_20260821C_E250208849")
    addon = chip(root, "2203th_20260822A_E250208832")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    for directory in (empty, addon):
        (directory / "BarcodeStat.txt").write_text("complete\n", encoding="utf-8")
    (addon / "SAMPLE-S1-WGS.R1.fq.gz").write_bytes(b"1")
    (addon / "SAMPLE-S1-WGS.R2.fq.gz").write_bytes(b"2")

    scan(sessions, root, now=datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc))

    with sessions() as session:
        rows = {row.chip_id: row for row in session.scalars(select(WgsIntakeBatch)).all()}
        assert rows[empty.name].state == "no_new_wgs"
        assert rows[empty.name].eligible_pair_count == 0
        assert rows[addon.name].state == "no_new_wgs"
        assert rows[addon.name].excluded_addon_pair_count == 1


def test_unpaired_normal_fastq_requires_review(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2204th_20260822B_E250208833")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    (directory / "BarcodeStat.txt").write_text("complete\n", encoding="utf-8")
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


def test_ready_input_drift_requires_review_but_addon_only_change_does_not(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2205th_20260823A_E250207440")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    (directory / "BarcodeStat.txt").write_text("complete\n", encoding="utf-8")
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

    r1.write_bytes(b"changed")
    scan(sessions, root, now=datetime(2026, 8, 29, 9, 30, tzinfo=timezone.utc))
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row.state == "needs_review"
        assert row.eligible_fingerprint == original_fingerprint
        assert row.last_error == "eligible WGS input changed after ready"


def test_repeated_scan_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "T7_Fastq"
    root.mkdir()
    directory = chip(root, "2206th_20260823B_E250208848")
    sessions = make_sessionmaker()
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc))
    (directory / "BarcodeStat.txt").write_text("complete\n", encoding="utf-8")
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
    (directory / "NORMAL-WGS.R1.fq.gz").write_bytes(b"1")
    (directory / "NORMAL-WGS.R2.fq.gz").write_bytes(b"2")
    scan(sessions, root, now=datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc))

    marker.unlink()
    scan(sessions, root, now=datetime(2026, 8, 29, 9, 0, tzinfo=timezone.utc))

    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        assert row.state == "needs_review"
        assert row.last_error == "eligible WGS input changed after ready"
