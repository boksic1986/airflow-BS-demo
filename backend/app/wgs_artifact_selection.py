from __future__ import annotations

from pathlib import Path


def select_batch_qcstat(batch_root: Path) -> Path | None:
    """Select the controlled batch QC summary without guessing among sample files."""
    qc_dir = batch_root / "07_QC"
    if not qc_dir.is_dir() or qc_dir.is_symlink():
        return None
    expected = qc_dir / f"{batch_root.name}.QCstat.tsv"
    if expected.is_file() and not expected.is_symlink():
        return expected
    candidates = sorted(
        path
        for path in qc_dir.glob("*.QCstat.tsv")
        if path.is_file() and not path.is_symlink()
    )
    return candidates[0] if len(candidates) == 1 else None
