import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pgta_metadata_runner import (
    build_pgta_config,
    collect_pgta_artifact,
    read_selected_manifest,
    run_pgta_target,
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

    def test_validate_pgta_conf_accepts_controlled_pgta_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            manifest = workdir / "config" / "samples.selected.tsv"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                "sample_id\tR1\tR2\tsource_dir\n"
                "G1\t/data/project/CNV/PGT-A/rawdata/run/G1_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run/G1_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run\n",
                encoding="utf-8",
            )

            for target in ("metadata", "dryrun_cnv", "invalid_target"):
                conf = validate_pgta_conf(
                    {
                        "analysis_id": "PGTA_TEST",
                        "pipeline": "pgta",
                        "sample_sheet_path": str(manifest),
                        "workdir": str(workdir),
                        "params": {"target": target},
                    },
                    shared_root=Path(tmpdir),
                )
                self.assertEqual(conf["params"]["target"], target)

    def test_validate_pgta_conf_rejects_uncontrolled_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            manifest = workdir / "config" / "samples.selected.tsv"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("sample_id\tR1\tR2\tsource_dir\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported PGT-A target"):
                validate_pgta_conf(
                    {
                        "analysis_id": "PGTA_TEST",
                        "pipeline": "pgta",
                        "sample_sheet_path": str(manifest),
                        "workdir": str(workdir),
                        "params": {"target": "baseline_qc"},
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

    def test_build_config_sets_cnv_target_for_dryrun(self) -> None:
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
                    "params": {"target": "dryrun_cnv"},
                },
                shared_root=Path(tmpdir),
            )

            config_path = build_pgta_config(conf, pgta_pipeline_root=Path("/opt/pipelines/PGT_A"))

            import yaml

            snakemake_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            runner_config = json.loads((workdir / "config" / "pgta_run_config.json").read_text(encoding="utf-8"))
            self.assertEqual(snakemake_config["pipeline"]["targets"], ["cnv"])
            self.assertTrue(snakemake_config["core"]["wisecondorx"]["cnv"]["enable"])
            self.assertEqual(runner_config["target"], "dryrun_cnv")

    def test_run_pgta_target_metadata_invokes_snakemake_and_writes_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            completed = Mock(returncode=0)
            completed.stdout = "snakemake stdout\n"
            completed.stderr = "snakemake stderr\n"
            with patch("pgta_metadata_runner.subprocess.run", return_value=completed) as run:
                artifact_path = run_pgta_target(
                    {
                        "analysis_id": "PGTA_TEST",
                        "workdir": str(workdir),
                        "config_path": str(config_path),
                        "params": {"target": "metadata"},
                    },
                    snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                    pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                )

            self.assertEqual(artifact_path, workdir / "logs" / "run_metadata.tsv")
            self.assertEqual((workdir / "logs" / "snakemake.stdout.log").read_text(encoding="utf-8"), "snakemake stdout\n")
            self.assertEqual((workdir / "logs" / "snakemake.stderr.log").read_text(encoding="utf-8"), "snakemake stderr\n")
            run.assert_called_once()
            command = run.call_args.args[0]
            self.assertEqual(command[:5], ["/biosoftware/miniconda/envs/snakemake_env/bin/snakemake", "--snakefile", "/opt/pipelines/PGT_A/Snakefile", "--cores", "1"])
            self.assertNotIn("--dry-run", command)
            self.assertIn("--configfile", command)
            self.assertEqual(run.call_args.kwargs["cwd"], str(workdir))

    def test_run_pgta_target_dryrun_adds_dry_run_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            completed = Mock(returncode=0)
            completed.stdout = "dry-run stdout\n"
            completed.stderr = ""
            with patch("pgta_metadata_runner.subprocess.run", return_value=completed) as run:
                artifact_path = run_pgta_target(
                    {
                        "analysis_id": "PGTA_TEST",
                        "workdir": str(workdir),
                        "config_path": str(config_path),
                        "params": {"target": "dryrun_cnv"},
                    },
                    snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                    pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                )

            command = run.call_args.args[0]
            self.assertEqual(artifact_path, workdir / "logs" / "snakemake.stdout.log")
            self.assertIn("--dry-run", command)
            self.assertNotIn("__airflow_demo_invalid_target__", command)

    def test_run_pgta_target_invalid_target_writes_stderr_and_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            completed = Mock(returncode=1)
            completed.stdout = ""
            completed.stderr = "No rule to produce __airflow_demo_invalid_target__\n"
            with patch("pgta_metadata_runner.subprocess.run", return_value=completed) as run:
                with self.assertRaisesRegex(RuntimeError, "exit code 1"):
                    run_pgta_target(
                        {
                            "analysis_id": "PGTA_TEST",
                            "workdir": str(workdir),
                            "config_path": str(config_path),
                            "params": {"target": "invalid_target"},
                        },
                        snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                        pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                    )

            command = run.call_args.args[0]
            self.assertIn("__airflow_demo_invalid_target__", command)
            self.assertEqual(
                (workdir / "logs" / "snakemake.stderr.log").read_text(encoding="utf-8"),
                "No rule to produce __airflow_demo_invalid_target__\n",
            )

    def test_collect_pgta_artifact_branches_by_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            logs_dir = workdir / "logs"
            logs_dir.mkdir(parents=True)
            metadata = logs_dir / "run_metadata.tsv"
            stdout = logs_dir / "snakemake.stdout.log"
            metadata.write_text("key\tvalue\n", encoding="utf-8")
            stdout.write_text("dry-run stdout\n", encoding="utf-8")

            metadata_artifact = collect_pgta_artifact({"workdir": str(workdir), "params": {"target": "metadata"}})
            dryrun_artifact = collect_pgta_artifact({"workdir": str(workdir), "params": {"target": "dryrun_cnv"}})

        self.assertEqual(metadata_artifact["type"], "pgta_metadata")
        self.assertTrue(metadata_artifact["path"].endswith("run_metadata.tsv"))
        self.assertEqual(dryrun_artifact["type"], "pgta_dryrun")
        self.assertTrue(dryrun_artifact["path"].endswith("snakemake.stdout.log"))


if __name__ == "__main__":
    unittest.main()
