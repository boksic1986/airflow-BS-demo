from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import AnalysisRun, Sample, WgsIntakeBatch
from app.wgs_samplelist_intake import scan_wgs_samplelist_intake
from app.wgs_t7_intake import list_wgs_t7_intake
from test_wgs_t7_intake import make_sessionmaker, chip


HEADER = "batchNo\tsampleId\ttechPlatformCode\titemCode\tprojectCode\n"
NOW = datetime(2099, 1, 1, tzinfo=timezone.utc)


def export(path, *batches):
    path.write_text(HEADER + "".join(f"{batch}\tSYN001\tT7\tWGS\tSYN-PROJECT\n" for batch in batches))


@pytest.fixture
def intake(tmp_path):
    root, source = tmp_path / "fastq", tmp_path / "samplelists"
    root.mkdir()
    source.mkdir()
    sessions = make_sessionmaker()
    def scan(**kwargs):
        return scan_wgs_samplelist_intake(session_factory=sessions, root=root,
            samplelist_root=source, project_id="SYN-PROJECT", platform_id="T7",
            root_id="SYN-ROOT", now=NOW, scan_enabled=True, **kwargs)
    return sessions, root, source, scan


def rows(sessions):
    with sessions() as session:
        return session.scalars(select(WgsIntakeBatch).order_by(WgsIntakeBatch.id)).all()


def test_baseline_files_and_later_mutations_never_register(intake):
    sessions, root, source, scan = intake
    old = source / "Samplelist_old.txt"
    export(old, "20990101A")
    scan()
    export(old, "20990102B")
    scan(); scan()
    assert rows(sessions) == []


def test_new_content_batch_needs_two_identical_observations_and_no_samples(intake):
    sessions, root, source, scan = intake
    scan()
    export(source / "Samplelist_19000101.txt", "20990101A")
    assert scan()["created"] == 0
    assert scan()["created"] == 1
    row, = rows(sessions)
    assert (row.sequencing_batch, row.chip_id, row.state) == ("20990101A", None, "waiting_sequencing")
    with sessions() as session:
        assert session.scalars(select(Sample)).all() == []
        assert session.scalars(select(AnalysisRun)).all() == []
        payload = list_wgs_t7_intake(session=session, state=None, view="pending", keyword=None, limit=20, offset=0)
    item, = payload["items"]
    assert item["batch_id"] == f"intake:{row.id}"
    assert item["intake_id"] == row.id
    assert item["project_id"] == "SYN-PROJECT"
    assert len(item["source_version"]) == 64
    assert "source_path" not in item


def test_reexports_dedupe_and_complete_file_registers_multiple_batches(intake):
    sessions, root, source, scan = intake
    scan()
    export(source / "Samplelist_new.txt", "20990101A", "20990102B")
    scan(); scan()
    export(source / "Samplelist_again.txt", "20990101A", "20990102B")
    scan(); scan()
    assert [row.sequencing_batch for row in rows(sessions)] == ["20990101A", "20990102B"]


@pytest.mark.parametrize("bad", ["20990102", "20990102BC", "20990102b", "", "../20990102B"])
def test_invalid_batch_makes_entire_file_atomic(intake, bad):
    sessions, root, source, scan = intake
    scan()
    export(source / "Samplelist_new.txt", "20990101A", bad)
    scan(); scan()
    assert rows(sessions) == []


@pytest.mark.parametrize("text", [
    HEADER + "20990101A\tSYN001\tT7\tWGS\tSYN-PROJECT\n20990102B\tSYN002",
    HEADER + "20990101A\t\tT7\tWGS\tSYN-PROJECT\n",
    "batchNo\tbatchNo\tsampleId\n20990101A\t20990101A\tSYN001\n",
])
def test_malformed_or_midwrite_file_never_partially_registers(intake, text):
    sessions, root, source, scan = intake
    scan()
    (source / "Samplelist_new.txt").write_text(text)
    scan(); scan()
    assert rows(sessions) == []


def test_changed_new_file_restarts_stability(intake):
    sessions, root, source, scan = intake
    scan()
    path = source / "Samplelist_new.txt"
    export(path, "20990101A"); scan()
    export(path, "20990102B"); scan()
    assert rows(sessions) == []
    scan()
    assert [row.sequencing_batch for row in rows(sessions)] == ["20990102B"]


def test_binding_exact_batch_waits_for_marker_then_preserves_row_identity(intake):
    sessions, root, source, scan = intake
    scan()
    export(source / "Samplelist_new.txt", "20990101A")
    scan(); scan()
    original, = rows(sessions)
    chip(root, "1th_20990101B_SYN")
    directory = chip(root, "2th_20990101A_SYN", files=("SYN001-WGS.R1.fq.gz", "SYN001-WGS.R2.fq.gz"))
    scan()
    row, = rows(sessions)
    assert row.state == "waiting_data"
    assert row.chip_id == directory.name
    (directory / "BarcodeStat.txt").write_text("complete\n")
    scan()
    row, = rows(sessions)
    assert (row.id, row.state, row.eligible_pair_count) == (original.id, "ready", 1)
    directory.rename(root / "gone")
    chip(root, "3th_20990101A_SYN", ready=True)
    scan()
    row, = rows(sessions)
    assert (row.state, row.chip_id) == ("needs_review", directory.name)


def test_ambiguous_batch_directory_fails_closed(intake):
    sessions, root, source, scan = intake
    scan()
    export(source / "Samplelist_new.txt", "20990101A")
    chip(root, "1th_20990101A_SYN", ready=True)
    chip(root, "2th_20990101A_SYN", ready=True)
    scan(); scan()
    row, = rows(sessions)
    assert (row.state, row.chip_id) == ("needs_review", None)


def test_switching_source_baselines_existing_files(intake, tmp_path):
    sessions, root, source, scan = intake
    scan()
    other = tmp_path / "other"
    other.mkdir()
    export(other / "Samplelist_existing.txt", "20990101A")
    for _ in range(3):
        scan_wgs_samplelist_intake(session_factory=sessions, root=root, samplelist_root=other,
            project_id="SYN-PROJECT", platform_id="T7", root_id="SYN-ROOT", scan_enabled=True)
    assert rows(sessions) == []


def test_symlink_source_and_directory_fail_closed(intake, tmp_path):
    sessions, root, source, scan = intake
    scan()
    outside = tmp_path / "outside.txt"
    export(outside, "20990101A")
    (source / "Samplelist_link.txt").symlink_to(outside)
    scan(); scan()
    assert rows(sessions) == []
    export(source / "Samplelist_real.txt", "20990101A")
    target = tmp_path / "external"
    target.mkdir()
    (root / "1th_20990101A_SYN").symlink_to(target, target_is_directory=True)
    scan(); scan()
    row, = rows(sessions)
    assert (row.state, row.chip_id) == ("needs_review", None)


def test_partial_baseline_enumeration_is_not_committed(intake, monkeypatch):
    from app import wgs_samplelist_intake as module
    from app.models import WgsSamplelistSource
    sessions, root, source, scan = intake
    export(source / "Samplelist_existing.txt", "20990101A")
    original = module._entries
    def failed(path):
        if path == source:
            raise OSError("synthetic enumeration failure")
        return original(path)
    monkeypatch.setattr(module, "_entries", failed)
    assert scan()["errors"] == 1
    with sessions() as session:
        assert session.scalar(select(WgsSamplelistSource)).baseline_complete is False
    monkeypatch.setattr(module, "_entries", original)
    scan(); scan(); scan()
    assert rows(sessions) == []


def test_ready_input_drift_never_resets_frozen_fingerprint(intake):
    sessions, root, source, scan = intake
    scan()
    export(source / "Samplelist_new.txt", "20990101A")
    directory = chip(root, "1th_20990101A_SYN", ready=True, files=("SYN001-WGS.R1.fq.gz", "SYN001-WGS.R2.fq.gz"))
    scan(); scan()
    original, = rows(sessions)
    (directory / "SYN002-WGS.R1.fq.gz").write_text("synthetic")
    (directory / "SYN002-WGS.R2.fq.gz").write_text("synthetic")
    scan(); scan()
    row, = rows(sessions)
    assert row.state == "needs_review"
    assert row.eligible_fingerprint == original.eligible_fingerprint


def test_platform_panel_filter_only_controls_batch_discovery(intake):
    sessions, root, source, scan = intake
    scan()
    (source / "Samplelist_new.txt").write_text(HEADER +
        "20990101A\tSYN001\tT7\tWGS\tSYN-PROJECT\n" +
        "20990102B\tSYN002\tOTHER\tWGS\tSYN-PROJECT\n" +
        "20990103C\tSYN003\tT7\tWES\tSYN-PROJECT\n")
    scan(); scan()
    assert [row.sequencing_batch for row in rows(sessions)] == ["20990101A"]


def test_missing_file_interrupts_consecutive_stability(intake):
    sessions, root, source, scan = intake
    scan()
    path = source / "Samplelist_new.txt"
    export(path, "20990101A")
    scan()
    hidden = source / "not-a-samplelist.txt"
    path.rename(hidden)
    scan()
    hidden.rename(path)
    scan()
    assert rows(sessions) == []
    scan()
    assert [row.sequencing_batch for row in rows(sessions)] == ["20990101A"]


def test_legacy_mode_does_not_mutate_samplelist_owned_rows(intake):
    from app.wgs_t7_intake import scan_wgs_t7_intake
    sessions, root, source, scan = intake
    scan()
    export(source / "Samplelist_new.txt", "20990101A")
    directory = chip(root, "1th_20990101A_SYN")
    scan(); scan()
    (directory / "BarcodeStat.txt").write_text("complete\n")
    (directory / "SYN001-WGS.R1.fq.gz").write_text("synthetic")
    (directory / "SYN001-WGS.R2.fq.gz").write_text("synthetic")
    scan_wgs_t7_intake(session_factory=sessions, root=root, now=NOW)
    row, = rows(sessions)
    assert row.state == "waiting_data"


def test_no_new_wgs_can_become_ready_without_false_frozen_conflict(intake):
    sessions, root, source, scan = intake
    scan()
    export(source / "Samplelist_new.txt", "20990101A")
    directory = chip(root, "1th_20990101A_SYN", ready=True)
    scan(); scan()
    assert rows(sessions)[0].state == "no_new_wgs"
    (directory / "SYN001-WGS.R1.fq.gz").write_text("synthetic")
    (directory / "SYN001-WGS.R2.fq.gz").write_text("synthetic")
    scan()
    assert rows(sessions)[0].state == "ready"
