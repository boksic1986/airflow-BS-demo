from pathlib import Path

import pytest

from app.input_scanner import InputPathError, scan_fastq_candidates, scan_nipt_batch_candidates


def write_fastq_pair(sample_dir: Path, stem: str) -> tuple[Path, Path]:
    sample_dir.mkdir(parents=True, exist_ok=True)
    r1 = sample_dir / f"{stem}_R1.fastq.gz"
    r2 = sample_dir / f"{stem}_R2.fastq.gz"
    r1.write_text("r1\n", encoding="utf-8")
    r2.write_text("r2\n", encoding="utf-8")
    return r1, r2


def write_nipt_clean_pair(batch_dir: Path, sample_id: str) -> tuple[Path, Path]:
    batch_dir.mkdir(parents=True, exist_ok=True)
    r1 = batch_dir / f"{sample_id}.R1.clean.fastq.gz"
    r2 = batch_dir / f"{sample_id}.R2.clean.fastq.gz"
    r1.write_text("r1\n", encoding="utf-8")
    r2.write_text("r2\n", encoding="utf-8")
    return r1, r2


def test_scan_fastq_candidates_uses_repeated_token_from_sample_dir(tmp_path) -> None:
    allowed_root = tmp_path / "rawdata"
    sample_dir = allowed_root / "run1" / "Sample_JZ26083055-G1-G1"
    r1, r2 = write_fastq_pair(sample_dir, "JZ26083055-G1-G1_combined")

    result = scan_fastq_candidates(
        rawdata_root=allowed_root,
        allowed_roots=[allowed_root],
        max_samples=20,
    )

    assert result.truncated is False
    assert len(result.items) == 1
    assert result.items[0].sample_id == "G1"
    assert result.items[0].r1 == str(r1.resolve())
    assert result.items[0].r2 == str(r2.resolve())
    assert result.items[0].source_dir == str(sample_dir.resolve())
    assert result.items[0].discovery_method == "server_path_scan"


def test_scan_fastq_candidates_rejects_paths_outside_allowed_roots(tmp_path) -> None:
    allowed_root = tmp_path / "allowed"
    outside_root = tmp_path / "outside"
    write_fastq_pair(outside_root / "Sample_JZ26083055-G1-G1", "G1")

    with pytest.raises(InputPathError, match="outside allowed input roots"):
        scan_fastq_candidates(
            rawdata_root=outside_root,
            allowed_roots=[allowed_root],
            max_samples=20,
        )


def test_scan_fastq_candidates_reports_truncation(tmp_path) -> None:
    allowed_root = tmp_path / "rawdata"
    write_fastq_pair(allowed_root / "Sample_JZ26083055-G1-G1", "G1")
    write_fastq_pair(allowed_root / "Sample_JZ26083056-G2-G2", "G2")

    result = scan_fastq_candidates(
        rawdata_root=allowed_root,
        allowed_roots=[allowed_root],
        max_samples=1,
    )

    assert result.truncated is True
    assert len(result.items) == 1


def test_scan_nipt_batch_candidates_uses_chip_folder_and_clean_fastqs(tmp_path) -> None:
    allowed_root = tmp_path / "fastq"
    batch_dir = allowed_root / "FQ2026" / "260414_TPNB500380AR_1065_AH32CCBGY2"
    r1, r2 = write_nipt_clean_pair(batch_dir, "NIPT26040207.A06")
    adapter_dir = batch_dir / "002"
    write_nipt_clean_pair(adapter_dir, "NIPT26040207.A06.adapter")

    result = scan_nipt_batch_candidates(
        rawdata_root=allowed_root,
        allowed_roots=[allowed_root],
        max_samples=20,
    )

    assert result.pipeline == "nipt_docker"
    assert result.truncated is False
    assert len(result.items) == 1
    item = result.items[0]
    assert item.sample_id == "NIPT26040207.A06"
    assert item.r1 == str(r1.resolve())
    assert item.r2 == str(r2.resolve())
    assert item.source_dir == str(batch_dir.resolve())
    assert item.discovery_method == "nipt_docker_clean_scan"
