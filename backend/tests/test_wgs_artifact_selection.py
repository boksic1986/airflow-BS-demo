from pathlib import Path

from app.wgs_artifact_selection import select_batch_qcstat


def test_only_exact_batch_qcstat_is_authoritative(tmp_path: Path) -> None:
    batch = tmp_path / "WGS_20260909A_T7Hg38V4.2.0"
    qc = batch / "07_QC"
    qc.mkdir(parents=True)
    multi = qc / f"{batch.name}.multi.QCstat.tsv"
    multi.write_text("sample\tstatus\nS1\tYes\n", encoding="utf-8")

    assert select_batch_qcstat(batch) is None

    exact = qc / f"{batch.name}.QCstat.tsv"
    exact.write_text("sample\tstatus\nS1\tYes\n", encoding="utf-8")

    assert select_batch_qcstat(batch) == exact
