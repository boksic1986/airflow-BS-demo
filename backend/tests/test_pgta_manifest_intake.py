from __future__ import annotations

from pathlib import Path

import pytest

from app.pgta_manifest_intake import (
    ManifestIntakeError,
    scan_pgta_manifest_request_results,
    scan_pgta_manifest_requests,
)


def write_pair(batch: Path, sample_id: str) -> None:
    sample_dir = batch / f"Sample_{sample_id}"
    sample_dir.mkdir(parents=True, exist_ok=True)
    for read in ("R1", "R2"):
        (sample_dir / f"{sample_id}_combined_{read}.fastq.gz").write_bytes(b"fastq")


def write_request(inbox: Path, *, request_id: str = "request-001", rows: list[str] | None = None) -> Path:
    manifest = inbox / f"{request_id}.samples.tsv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "project_id\tsource_batch\tsample_id\toperator\n"
        + "\n".join(rows or ["PGTA-DEMO\t2026-06-08\tPGTA-DEMO-01\tdemo-operator"])
        + "\n",
        encoding="utf-8",
    )
    return manifest


def test_manifest_requires_ready_marker_and_resolves_exact_fastq_pair(tmp_path) -> None:
    data_root = tmp_path / "rawdata"
    inbox = data_root / "pgta_crontab"
    write_pair(data_root / "2026-06-08", "PGTA-DEMO-01")
    write_request(inbox)

    assert scan_pgta_manifest_requests(inbox_root=inbox, data_root=data_root) == []

    (inbox / "request-001.READY").write_text("", encoding="utf-8")
    requests = scan_pgta_manifest_requests(inbox_root=inbox, data_root=data_root)

    assert len(requests) == 1
    request = requests[0]
    assert request.request_id == "request-001"
    assert request.project_id == "PGTA-DEMO"
    assert request.operator == "demo-operator"
    assert request.source_batch == "2026-06-08"
    assert [sample.sample_id for sample in request.samples] == ["PGTA-DEMO-01"]
    assert request.samples[0].r1.endswith("PGTA-DEMO-01_combined_R1.fastq.gz")
    assert request.samples[0].r2.endswith("PGTA-DEMO-01_combined_R2.fastq.gz")


def test_manifest_rejects_duplicate_samples_and_path_escape(tmp_path) -> None:
    data_root = tmp_path / "rawdata"
    inbox = data_root / "pgta_crontab"
    write_request(
        inbox,
        rows=[
            "PGTA-DEMO\t../outside\tPGTA-DEMO-01\tdemo-operator",
            "PGTA-DEMO\t../outside\tPGTA-DEMO-01\tdemo-operator",
        ],
    )
    (inbox / "request-001.READY").write_text("", encoding="utf-8")

    with pytest.raises(ManifestIntakeError):
        scan_pgta_manifest_requests(inbox_root=inbox, data_root=data_root)


def test_safe_manifest_scan_keeps_valid_requests_and_reports_invalid_request(tmp_path) -> None:
    data_root = tmp_path / "rawdata"
    inbox = data_root / "pgta_crontab"
    write_pair(data_root / "2026-06-08", "PGTA-DEMO-01")
    write_request(inbox, request_id="valid-request")
    write_request(
        inbox,
        request_id="invalid-request",
        rows=[
            "PGTA-DEMO\t2026-06-08\tPGTA-DEMO-01\tdemo-operator",
            "PGTA-DEMO\t2026-06-08\tPGTA-DEMO-01\tdemo-operator",
        ],
    )
    (inbox / "valid-request.READY").write_text("", encoding="utf-8")
    (inbox / "invalid-request.READY").write_text("", encoding="utf-8")

    result = scan_pgta_manifest_request_results(inbox_root=inbox, data_root=data_root)

    assert [item.request_id for item in result.requests] == ["valid-request"]
    assert [item.request_id for item in result.errors] == ["invalid-request"]
    assert "duplicate sample_id" in result.errors[0].message
    assert len(result.errors[0].fingerprint) == 64
