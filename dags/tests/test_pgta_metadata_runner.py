import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pgta_metadata_runner import (
    build_pgta_config,
    read_selected_manifest,
    run_pgta_metadata,
    validate_pgta_conf,
)


class PgtaMetadataRunnerTests(unittest.TestCase):
    def test_read_selected_manifest_returns_samples(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "samples.selected.tsv"
            manifest.write_text(
                "sample_id\tR1\tR2\tsource_dir\n"
                "G1\t/data/project/CNV/PGT-A/rawdata/run/G1_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run/G1_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run\n",
                encoding="utf-8",
            )

            samples = read_selected_manifest(manifest)

        self.assertEqual(samples, [{"sample_id": "G1", "R1": "/data/project/CNV/PGT-A/rawdata/run/G1_R1.fastq.gz", "R2": "/data/project/CNV/PGT-A/rawdata/run/G1_R2.fastq.gz", "source_dir": "/data/project/CNV/PGT-A/rawdata/run"}])

    def test_validate_pgta_conf_rejects_non_metadata_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            manifest = workdir / "config" / "samples.selected.tsv"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("sample_id\tR1\tR2\tsource_dir\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "target=metadata"):
                validate_pgta_conf(
                    {
                        "analysis_id": "PGTA_TEST",
                        "pipeline": "pgta",
                        "sample_sheet_path": str(manifest),
                        "workdir": str(workdir),
                        "params": {"target": "dryrun_cnv"},
                    },
                    shared_root=Path(tmpdir),
                )

    def test_build_config_writes_snakemake_compatible_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            manifest = workdir / "config" / "samples.selected.tsv"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                "sample_id\tR1\tR2\tsource_dir\n"
                "G1\t/data/project/CNV/PGT-A/rawdata/run/G1_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run/G1_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run\n",
                encoding="utf-8",
            )
            conf = validate_pgta_conf(
                {
                    "analysis_id": "PGTA_TEST",
                    "pipeline": "pgta",
                    "sample_sheet_path": str(manifest),
                    "workdir": str(workdir),
                    "params": {"target": "metadata"},
                    "email_to": "demo@example.com",
                },
                shared_root=Path(tmpdir),
            )

            config_path = build_pgta_config(conf, pgta_pipeline_root=Path("/opt/pipelines/PGT_A"))

            config = json.loads((workdir / "config" / "pgta_metadata_config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["analysis_id"], "PGTA_TEST")
            self.assertEqual(config["target"], "metadata")
            self.assertEqual(config["samples"]["G1"]["R1"], "/data/project/CNV/PGT-A/rawdata/run/G1_R1.fastq.gz")
            self.assertTrue((workdir / "config.yaml").exists())
            self.assertEqual(config_path, workdir / "config.yaml")

    def test_run_pgta_metadata_invokes_snakemake_and_writes_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            completed = Mock(returncode=0)
            completed.stdout = "snakemake stdout\n"
            completed.stderr = "snakemake stderr\n"
            with patch("pgta_metadata_runner.subprocess.run", return_value=completed) as run:
                metadata_path = run_pgta_metadata(
                    {
                        "analysis_id": "PGTA_TEST",
                        "workdir": str(workdir),
                        "config_path": str(config_path),
                    },
                    snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                    pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                )

            self.assertEqual(metadata_path, workdir / "logs" / "run_metadata.tsv")
            self.assertEqual((workdir / "logs" / "snakemake.stdout.log").read_text(encoding="utf-8"), "snakemake stdout\n")
            self.assertEqual((workdir / "logs" / "snakemake.stderr.log").read_text(encoding="utf-8"), "snakemake stderr\n")
            run.assert_called_once()
            command = run.call_args.args[0]
            self.assertEqual(command[:5], ["/biosoftware/miniconda/envs/snakemake_env/bin/snakemake", "--snakefile", "/opt/pipelines/PGT_A/Snakefile", "--cores", "1"])
            self.assertEqual(run.call_args.kwargs["cwd"], str(workdir))


if __name__ == "__main__":
    unittest.main()
