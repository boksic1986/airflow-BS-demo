from __future__ import annotations

import gzip
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from build_pgta_s9_validation_subset import build_subset


def _write_fastq(path: Path, records: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="ascii") as handle:
        for index in range(records):
            handle.write(f"@read-{index}\nACGT\n+\nIIII\n")


class PgtaS9ValidationSubsetTests(unittest.TestCase):
    def test_copies_paired_prefix_and_records_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source"
            sample_dir = source / "batch" / "Sample_S1"
            _write_fastq(sample_dir / "S1_combined_R1.fastq.gz", 5)
            _write_fastq(sample_dir / "S1_combined_R2.fastq.gz", 5)
            output = root / "subset"

            provenance = build_subset(
                source_batch=source,
                output_root=output,
                sample_ids=["S1"],
                read_pairs=3,
            )

            self.assertEqual(provenance["samples"][0]["read_pairs"], 3)
            self.assertEqual(len(provenance["samples"][0]["output_r1_sha256"]), 64)
            with gzip.open(
                output / "Sample_S1" / "S1_combined_R1.fastq.gz",
                "rt",
                encoding="ascii",
            ) as handle:
                self.assertEqual(sum(1 for _ in handle), 12)
            self.assertTrue((output / "validation_subset.provenance.json").is_file())


if __name__ == "__main__":
    unittest.main()
