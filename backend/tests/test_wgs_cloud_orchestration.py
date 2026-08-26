import json
from pathlib import Path

import pytest

from app.wgs_orchestration_service import (
    SnapshotChangedError,
    build_fastq_snapshot,
    parse_obsutil_progress,
    verify_fastq_snapshot,
)


def _linked_pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "source"
    intake = tmp_path / "intake" / "BATCH-001"
    source.mkdir()
    intake.mkdir(parents=True)
    r1 = source / "F01_S1_R1.fastq.gz"
    r2 = source / "F01_S1_R2.fastq.gz"
    r1.write_bytes(b"R1\n")
    r2.write_bytes(b"R2\n")
    (intake / r1.name).symlink_to(r1)
    (intake / r2.name).symlink_to(r2)
    return intake, r1, r2


def test_fastq_snapshot_requires_symlink_pairs_and_records_inode_identity(tmp_path: Path) -> None:
    intake, r1, r2 = _linked_pair(tmp_path)
    manifest = tmp_path / "run" / "input-manifest.json"

    snapshot = build_fastq_snapshot(
        fq_path=str(intake),
        allowed_link_roots=[str(tmp_path / "intake")],
        allowed_fastq_roots=[str(tmp_path / "source")],
        manifest_path=manifest,
    )

    assert snapshot["file_count"] == 2
    assert snapshot["sample_count"] == 1
    assert snapshot["total_bytes"] == r1.stat().st_size + r2.stat().st_size
    assert {item["read"] for item in snapshot["files"]} == {"R1", "R2"}
    assert all(item["device"] >= 0 and item["inode"] > 0 for item in snapshot["files"])
    assert json.loads(manifest.read_text(encoding="utf-8"))["manifest_sha256"] == snapshot["manifest_sha256"]
    verify_fastq_snapshot(manifest)


def test_snapshot_change_blocks_resume_and_mixed_upload(tmp_path: Path) -> None:
    intake, r1, _ = _linked_pair(tmp_path)
    manifest = tmp_path / "run" / "input-manifest.json"
    build_fastq_snapshot(
        fq_path=str(intake),
        allowed_link_roots=[str(tmp_path / "intake")],
        allowed_fastq_roots=[str(tmp_path / "source")],
        manifest_path=manifest,
    )
    r1.write_bytes(b"changed\n")

    with pytest.raises(SnapshotChangedError, match="source snapshot changed"):
        verify_fastq_snapshot(manifest)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            "[>>>>>>>>>>>>>>>>>>>>] 62.50% 115.89MB/s 2.50GB/4.00GB 13s",
            {"percent": 62.5, "speed_bps": 115_890_000, "bytes_transferred": 2_500_000_000, "bytes_total": 4_000_000_000, "eta_seconds": 13},
        ),
        (
            "[>>>>                ] 10.00% 8.00MiB/s 80.00MiB/800.00MiB 1m30s\r",
            {"percent": 10.0, "speed_bps": 8_388_608, "bytes_transferred": 83_886_080, "bytes_total": 838_860_800, "eta_seconds": 90},
        ),
    ],
)
def test_obsutil_carriage_return_progress_parser(line: str, expected: dict) -> None:
    assert parse_obsutil_progress(line) == expected
