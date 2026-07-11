from __future__ import annotations

import csv
from pathlib import Path
import tempfile
import unittest

import yaml

from pgta_metadata_runner import build_pgta_config, run_pgta_stage, validate_pgta_conf


class PgtaS9PredictTests(unittest.TestCase):
    def _conf(self, root: Path) -> dict:
        workdir = root / "shared" / "runs" / "PGTA_S9_TEST"
        config_dir = workdir / "config"
        config_dir.mkdir(parents=True)
        sample_dir = root / "data" / "batch" / "Sample_PGTA-DEMO-01"
        sample_dir.mkdir(parents=True)
        r1 = sample_dir / "PGTA-DEMO-01_combined_R1.fastq.gz"
        r2 = sample_dir / "PGTA-DEMO-01_combined_R2.fastq.gz"
        r1.write_text("r1\n", encoding="utf-8")
        r2.write_text("r2\n", encoding="utf-8")
        manifest = config_dir / "samples.selected.tsv"
        with manifest.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(["sample_id", "R1", "R2", "source_dir"])
            writer.writerow(["PGTA-DEMO-01", r1, r2, sample_dir])
        return {
            "analysis_id": "PGTA_S9_TEST",
            "pipeline": "pgta",
            "mode": "new",
            "sample_sheet_path": str(manifest),
            "workdir": str(workdir),
            "backend_event_url": "http://backend:8000/api/events/snakemake",
            "params": {"target": "predict"},
        }

    def test_predict_config_uses_fixed_references_without_build_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            conf = self._conf(root)
            pipeline_root = root / "PGT_A_S9"
            pipeline_root.mkdir()
            config_path = build_pgta_config(
                conf,
                pgta_pipeline_root=pipeline_root,
                pgta_data_root=root / "data",
                reference_genome=root / "hg19.fa",
            )
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

            self.assertEqual(config["pipeline"], {"mode": "predict", "targets": ["mapping", "metadata", "cnv_qc", "cnv"]})
            self.assertNotIn("build_reference", config)
            self.assertTrue(config["core"]["wisecondorx"]["reference_output_by_sex"]["XX"])
            self.assertTrue(config["core"]["wisecondorx"]["reference_output_by_sex"]["XY"])

    def test_predict_is_validated_and_exposes_four_controlled_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            conf = self._conf(root)
            normalized = validate_pgta_conf(conf, shared_root=root / "shared")
            self.assertEqual(normalized["params"]["target"], "predict")
            for stage in ("mapping", "metadata", "cnv_qc", "cnv_predict"):
                with self.subTest(stage=stage):
                    self.assertTrue(callable(run_pgta_stage))


if __name__ == "__main__":
    unittest.main()
