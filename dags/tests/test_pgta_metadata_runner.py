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

            for target in ("metadata", "dryrun_cnv", "invalid_target", "baseline_qc"):
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
                        "params": {"target": "real_cnv"},
                    },
                    shared_root=Path(tmpdir),
                )

    def test_validate_pgta_conf_accepts_resume_only_for_baseline_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            manifest = workdir / "config" / "samples.selected.tsv"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                "sample_id\tR1\tR2\tsource_dir\n"
                "G1\t/data/project/CNV/PGT-A/rawdata/run/G1_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run/G1_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run\n"
                "G2\t/data/project/CNV/PGT-A/rawdata/run/G2_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run/G2_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run\n",
                encoding="utf-8",
            )

            conf = validate_pgta_conf(
                {
                    "analysis_id": "PGTA_TEST",
                    "pipeline": "pgta",
                    "mode": "resume",
                    "sample_sheet_path": str(manifest),
                    "workdir": str(workdir),
                    "params": {"target": "baseline_qc"},
                },
                shared_root=Path(tmpdir),
            )
            self.assertEqual(conf["mode"], "resume")

            with self.assertRaisesRegex(ValueError, "PGT-A resume is only supported for baseline_qc"):
                validate_pgta_conf(
                    {
                        "analysis_id": "PGTA_TEST",
                        "pipeline": "pgta",
                        "mode": "resume",
                        "sample_sheet_path": str(manifest),
                        "workdir": str(workdir),
                        "params": {"target": "metadata"},
                    },
                    shared_root=Path(tmpdir),
                )

            with self.assertRaisesRegex(ValueError, "Unsupported PGT-A mode"):
                validate_pgta_conf(
                    {
                        "analysis_id": "PGTA_TEST",
                        "pipeline": "pgta",
                        "mode": "forceall",
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

            config_path = build_pgta_config(
                conf,
                pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                pgta_data_root=Path("/data/project/CNV/PGT-A"),
            )

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
            wisecondorx = snakemake_config["core"]["wisecondorx"]
            self.assertEqual(snakemake_config["pipeline"]["targets"], ["cnv"])
            self.assertTrue(wisecondorx["cnv"]["enable"])
            self.assertEqual(
                wisecondorx["reference_output_by_sex"]["XX"],
                "/data/project/CNV/PGT-A/refactor_validation_20260419/results_build_ref_v2_mask_only/reference/XX/result/ref_xx_best.npz",
            )
            self.assertEqual(
                wisecondorx["reference_output_by_sex"]["XY"],
                "/data/project/CNV/PGT-A/refactor_validation_20260419/results_build_ref_v2_mask_only/reference/XY/result/ref_xy_best.npz",
            )
            self.assertEqual(
                wisecondorx["gender_reference_output"],
                "/data/project/CNV/PGT-A/refactor_validation_20260419/results_build_ref_v2_mask_only/reference/gender/result/ref_gender_best.npz",
            )
            self.assertEqual(
                wisecondorx["common_reference_binsize_output"],
                "/data/project/CNV/PGT-A/refactor_validation_20260419/results_build_ref_v2_mask_only/reference/gender/common_best_binsize.txt",
            )
            self.assertEqual(runner_config["target"], "dryrun_cnv")

    def test_build_config_sets_build_ref_target_for_baseline_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            manifest = workdir / "config" / "samples.selected.tsv"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                "sample_id\tR1\tR2\tsource_dir\n"
                "G1\t/data/project/CNV/PGT-A/rawdata/run/G1_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run/G1_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run\n"
                "G2\t/data/project/CNV/PGT-A/rawdata/run/G2_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run/G2_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run\n",
                encoding="utf-8",
            )
            conf = validate_pgta_conf(
                {
                    "analysis_id": "PGTA_TEST",
                    "pipeline": "pgta",
                    "sample_sheet_path": str(manifest),
                    "workdir": str(workdir),
                    "params": {"target": "baseline_qc"},
                },
                shared_root=Path(tmpdir),
            )

            config_path = build_pgta_config(conf, pgta_pipeline_root=Path("/opt/pipelines/PGT_A"))

            import yaml

            snakemake_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            runner_config = json.loads((workdir / "config" / "pgta_run_config.json").read_text(encoding="utf-8"))
            self.assertEqual(snakemake_config["pipeline"]["mode"], "build_ref")
            self.assertEqual(snakemake_config["pipeline"]["targets"], ["mapping", "metadata", "baseline_qc"])
            self.assertEqual(snakemake_config["build_reference"]["mode"], "selected_samples")
            self.assertEqual(snakemake_config["build_reference"]["groups"], {"demo": ["G1", "G2"]})
            self.assertFalse(snakemake_config["core"]["wisecondorx"]["tuning"]["enable"])
            self.assertFalse(snakemake_config["core"]["wisecondorx"]["cnv"]["enable"])
            self.assertEqual(runner_config["target"], "baseline_qc")

    def test_build_config_writes_run_local_samtools_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            manifest = workdir / "config" / "samples.selected.tsv"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                "sample_id\tR1\tR2\tsource_dir\n"
                "G1\t/data/project/CNV/PGT-A/rawdata/run/G1_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run/G1_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run\n"
                "G2\t/data/project/CNV/PGT-A/rawdata/run/G2_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run/G2_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/run\n",
                encoding="utf-8",
            )
            conf = validate_pgta_conf(
                {
                    "analysis_id": "PGTA_TEST",
                    "pipeline": "pgta",
                    "sample_sheet_path": str(manifest),
                    "workdir": str(workdir),
                    "params": {"target": "baseline_qc"},
                },
                shared_root=Path(tmpdir),
            )

            config_path = build_pgta_config(
                conf,
                pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                samtools_bin=Path("/opt/compatible/bin/samtools"),
                samtools_library_path="/opt/compatible/lib",
            )

            import yaml

            snakemake_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            wrapper = workdir / "bin" / "samtools"
            self.assertEqual(snakemake_config["biosoft"]["samtools"], str(wrapper))
            self.assertTrue(wrapper.is_file())
            self.assertTrue(wrapper.stat().st_mode & 0o111)
            wrapper_text = wrapper.read_text(encoding="utf-8")
            self.assertIn('export LD_LIBRARY_PATH="/opt/compatible/lib:${LD_LIBRARY_PATH:-}"', wrapper_text)
            self.assertIn('exec /opt/compatible/bin/samtools "$@"', wrapper_text)

    def test_build_config_uses_configured_reference_genome(self) -> None:
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
                },
                shared_root=Path(tmpdir),
            )

            config_path = build_pgta_config(
                conf,
                pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                reference_genome=Path("/refs/hg19/hg19.fa"),
            )

            import yaml

            snakemake_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            self.assertEqual(snakemake_config["core"]["reference_genome"], "/refs/hg19/hg19.fa")

    def test_build_config_rejects_baseline_qc_with_one_sample(self) -> None:
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
                    "params": {"target": "baseline_qc"},
                },
                shared_root=Path(tmpdir),
            )

            with self.assertRaisesRegex(ValueError, "baseline_qc requires at least 2 selected samples"):
                build_pgta_config(conf, pgta_pipeline_root=Path("/opt/pipelines/PGT_A"))

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
            self.assertEqual(command[0].replace("\\", "/"), "/biosoftware/miniconda/envs/snakemake_env/bin/snakemake")
            self.assertEqual(command[1], "--snakefile")
            self.assertEqual(command[2].replace("\\", "/"), "/opt/pipelines/PGT_A/Snakefile")
            self.assertEqual(command[3:5], ["--cores", "64"])
            self.assertNotIn("--dry-run", command)
            self.assertIn("--configfile", command)
            self.assertEqual(run.call_args.kwargs["cwd"], str(workdir))
            cache_dir = workdir / "tmp" / "xdg-cache"
            mpl_config_dir = workdir / "tmp" / "matplotlib"
            self.assertTrue(cache_dir.is_dir())
            self.assertTrue(mpl_config_dir.is_dir())
            self.assertEqual(run.call_args.kwargs["env"]["XDG_CACHE_HOME"], str(cache_dir))
            self.assertEqual(run.call_args.kwargs["env"]["MPLCONFIGDIR"], str(mpl_config_dir))
            self.assertTrue(
                run.call_args.kwargs["env"]["LD_LIBRARY_PATH"].startswith(
                    "/biosoftware/miniconda/envs/snakemake_env/lib"
                )
            )
            command_text = (workdir / "logs" / "snakemake.command.txt").read_text(encoding="utf-8")
            normalized_command_text = command_text.replace("\\", "/").replace("'", "")
            self.assertIn("--snakefile /opt/pipelines/PGT_A/Snakefile", normalized_command_text)
            self.assertIn("--cores 64", command_text)
            self.assertIn(f"--configfile {config_path}".replace("\\", "/"), normalized_command_text)

    def test_run_pgta_target_allows_core_count_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            completed = Mock(returncode=0)
            completed.stdout = ""
            completed.stderr = ""
            with patch.dict("pgta_metadata_runner.os.environ", {"PGTA_SNAKEMAKE_CORES": "8"}):
                with patch("pgta_metadata_runner.subprocess.run", return_value=completed) as run:
                    run_pgta_target(
                        {
                            "analysis_id": "PGTA_TEST",
                            "workdir": str(workdir),
                            "config_path": str(config_path),
                            "params": {"target": "metadata"},
                        },
                        snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                        pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                    )

            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--cores") + 1], "8")

    def test_run_pgta_target_drops_inherited_library_path_for_pgta_conda_lib(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            completed = Mock(returncode=0)
            completed.stdout = ""
            completed.stderr = ""
            with patch.dict("pgta_metadata_runner.os.environ", {"LD_LIBRARY_PATH": "/usr/local/lib"}):
                with patch("pgta_metadata_runner.subprocess.run", return_value=completed) as run:
                    run_pgta_target(
                        {
                            "analysis_id": "PGTA_TEST",
                            "workdir": str(workdir),
                            "config_path": str(config_path),
                            "params": {"target": "metadata"},
                        },
                        snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                        pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                    )

            self.assertEqual(
                run.call_args.kwargs["env"]["LD_LIBRARY_PATH"],
                "/biosoftware/miniconda/envs/snakemake_env/lib",
            )

    def test_run_pgta_target_preloads_pgta_conda_libstdcxx_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")
            libstdcxx = Path(tmpdir) / "libstdc++.so.6"
            libstdcxx.write_text("", encoding="utf-8")

            completed = Mock(returncode=0)
            completed.stdout = ""
            completed.stderr = ""
            with patch("pgta_metadata_runner.DEFAULT_PGTA_LIBSTDCXX", libstdcxx):
                with patch("pgta_metadata_runner.subprocess.run", return_value=completed) as run:
                    run_pgta_target(
                        {
                            "analysis_id": "PGTA_TEST",
                            "workdir": str(workdir),
                            "config_path": str(config_path),
                            "params": {"target": "metadata"},
                        },
                        snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                        pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                    )

            self.assertEqual(run.call_args.kwargs["env"]["LD_PRELOAD"], str(libstdcxx))

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
            self.assertIn("--ignore-incomplete", command)
            self.assertEqual(command[command.index("--rerun-triggers") + 1], "mtime")
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

    def test_run_pgta_target_baseline_qc_invokes_snakemake_without_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            completed = Mock(returncode=0)
            completed.stdout = "baseline stdout\n"
            completed.stderr = ""
            preflight_completed = Mock(returncode=0)
            preflight_completed.stdout = "pgta python preflight ok\n"
            preflight_completed.stderr = ""
            with patch("pgta_metadata_runner.subprocess.run", side_effect=[preflight_completed, completed]) as run:
                artifact_path = run_pgta_target(
                    {
                        "analysis_id": "PGTA_TEST",
                        "workdir": str(workdir),
                        "config_path": str(config_path),
                        "params": {"target": "baseline_qc"},
                    },
                    snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                    pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                )

            self.assertEqual(run.call_count, 2)
            preflight_command = run.call_args_list[0].args[0]
            command = run.call_args_list[1].args[0]
            self.assertEqual(artifact_path, workdir / "qc" / "baseline" / "baseline_qc_summary.tsv")
            self.assertEqual(preflight_command[0].replace("\\", "/"), "/biosoftware/miniconda/envs/snakemake_env/bin/python")
            self.assertIn("matplotlib", preflight_command[-1])
            self.assertIn("pysam", preflight_command[-1])
            preflight_log = (workdir / "logs" / "pgta.python_preflight.log").read_text(encoding="utf-8")
            self.assertIn("LD_LIBRARY_PATH\t/biosoftware/miniconda/envs/snakemake_env/lib", preflight_log)
            self.assertIn("--- output ---\npgta python preflight ok\n", preflight_log)
            self.assertNotIn("--dry-run", command)
            self.assertNotIn("__airflow_demo_invalid_target__", command)

    def test_run_pgta_target_baseline_qc_preflight_failure_stops_before_snakemake(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            preflight_completed = Mock(returncode=1)
            preflight_completed.stdout = ""
            preflight_completed.stderr = "ImportError: CXXABI_1.3.15 not found\n"
            with patch("pgta_metadata_runner.subprocess.run", return_value=preflight_completed) as run:
                with self.assertRaisesRegex(RuntimeError, "PGT-A Python preflight failed"):
                    run_pgta_target(
                        {
                            "analysis_id": "PGTA_TEST",
                            "workdir": str(workdir),
                            "config_path": str(config_path),
                            "params": {"target": "baseline_qc"},
                        },
                        snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                        pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                    )

            run.assert_called_once()
            self.assertIn(
                "ImportError: CXXABI_1.3.15 not found\n",
                (workdir / "logs" / "pgta.python_preflight.log").read_text(encoding="utf-8"),
            )

    def test_run_pgta_target_resume_unlocks_then_reruns_incomplete_without_forceall(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            unlock_completed = Mock(returncode=0)
            unlock_completed.stdout = "unlock stdout\n"
            unlock_completed.stderr = "unlock stderr\n"
            run_completed = Mock(returncode=0)
            run_completed.stdout = "resume stdout\n"
            run_completed.stderr = ""
            preflight_completed = Mock(returncode=0)
            preflight_completed.stdout = "pgta python preflight ok\n"
            preflight_completed.stderr = ""
            with patch("pgta_metadata_runner.subprocess.run", side_effect=[unlock_completed, preflight_completed, run_completed]) as run:
                artifact_path = run_pgta_target(
                    {
                        "analysis_id": "PGTA_TEST",
                        "mode": "resume",
                        "workdir": str(workdir),
                        "config_path": str(config_path),
                        "params": {"target": "baseline_qc"},
                    },
                    snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                    pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                )

            self.assertEqual(artifact_path, workdir / "qc" / "baseline" / "baseline_qc_summary.tsv")
            self.assertEqual(run.call_count, 3)
            unlock_command = run.call_args_list[0].args[0]
            preflight_command = run.call_args_list[1].args[0]
            resume_command = run.call_args_list[2].args[0]
            self.assertIn("--unlock", unlock_command)
            self.assertNotIn("--forceall", unlock_command)
            self.assertEqual(preflight_command[0].replace("\\", "/"), "/biosoftware/miniconda/envs/snakemake_env/bin/python")
            self.assertIn("--rerun-incomplete", resume_command)
            self.assertEqual(resume_command[resume_command.index("--cores") + 1], "64")
            self.assertNotIn("--forceall", resume_command)
            unlock_command_text = (workdir / "logs" / "snakemake.unlock.command.txt").read_text(encoding="utf-8")
            resume_command_text = (workdir / "logs" / "snakemake.command.txt").read_text(encoding="utf-8")
            self.assertIn("--unlock", unlock_command_text)
            self.assertIn("--rerun-incomplete", resume_command_text)
            self.assertIn("--cores 64", resume_command_text)
            self.assertNotIn("--forceall", resume_command_text)
            self.assertEqual((workdir / "logs" / "snakemake.stdout.log").read_text(encoding="utf-8"), "resume stdout\n")

    def test_run_pgta_target_resume_removes_only_samtools_sort_tmp_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            mapping_dir = workdir / "mapping"
            mapping_dir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")
            tmp_0000 = mapping_dir / "G11.sorted.bam.tmp.0000.bam"
            tmp_0001 = mapping_dir / "G11.sorted.bam.tmp.0001.bam"
            final_bam = mapping_dir / "G11.sorted.bam"
            final_bai = mapping_dir / "G11.sorted.bam.bai"
            non_matching_tmp = mapping_dir / "G11.sorted.bam.tmp.keep.txt"
            other_rule_tmp = mapping_dir / "G11.fastp.tmp.0000.bam"
            tmp_0000.write_bytes(b"tmp0000")
            tmp_0001.write_bytes(b"tmp0001")
            final_bam.write_bytes(b"final-bam")
            final_bai.write_bytes(b"final-bai")
            non_matching_tmp.write_bytes(b"keep")
            other_rule_tmp.write_bytes(b"keep2")

            unlock_completed = Mock(returncode=0)
            unlock_completed.stdout = ""
            unlock_completed.stderr = ""
            run_completed = Mock(returncode=0)
            run_completed.stdout = "resume stdout\n"
            run_completed.stderr = ""
            preflight_completed = Mock(returncode=0)
            preflight_completed.stdout = "pgta python preflight ok\n"
            preflight_completed.stderr = ""
            with patch("pgta_metadata_runner.subprocess.run", side_effect=[unlock_completed, preflight_completed, run_completed]):
                run_pgta_target(
                    {
                        "analysis_id": "PGTA_TEST",
                        "mode": "resume",
                        "workdir": str(workdir),
                        "config_path": str(config_path),
                        "params": {"target": "baseline_qc"},
                    },
                    snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake_env/bin/snakemake"),
                    pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                )

            self.assertFalse(tmp_0000.exists())
            self.assertFalse(tmp_0001.exists())
            self.assertTrue(final_bam.exists())
            self.assertTrue(final_bai.exists())
            self.assertTrue(non_matching_tmp.exists())
            self.assertTrue(other_rule_tmp.exists())
            cleanup_log = workdir / "logs" / "pgta.resume.cleanup.tsv"
            cleanup_lines = cleanup_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(cleanup_lines[0], "deleted_at\tpath\tsize_bytes")
            self.assertEqual(len(cleanup_lines), 3)
            self.assertIn("G11.sorted.bam.tmp.0000.bam\t7", cleanup_lines[1])
            self.assertIn("G11.sorted.bam.tmp.0001.bam\t7", cleanup_lines[2])

    def test_collect_pgta_artifact_branches_by_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            logs_dir = workdir / "logs"
            baseline_dir = workdir / "qc" / "baseline"
            logs_dir.mkdir(parents=True)
            baseline_dir.mkdir(parents=True)
            metadata = logs_dir / "run_metadata.tsv"
            stdout = logs_dir / "snakemake.stdout.log"
            baseline_summary = baseline_dir / "baseline_qc_summary.tsv"
            metadata.write_text("key\tvalue\n", encoding="utf-8")
            stdout.write_text("dry-run stdout\n", encoding="utf-8")
            baseline_summary.write_text("sample_id\tqc_decision\nG1\tPASS\n", encoding="utf-8")

            metadata_artifact = collect_pgta_artifact({"workdir": str(workdir), "params": {"target": "metadata"}})
            dryrun_artifact = collect_pgta_artifact({"workdir": str(workdir), "params": {"target": "dryrun_cnv"}})
            baseline_artifact = collect_pgta_artifact({"workdir": str(workdir), "params": {"target": "baseline_qc"}})

        self.assertEqual(metadata_artifact["type"], "pgta_metadata")
        self.assertTrue(metadata_artifact["path"].endswith("run_metadata.tsv"))
        self.assertEqual(dryrun_artifact["type"], "pgta_dryrun")
        self.assertTrue(dryrun_artifact["path"].endswith("snakemake.stdout.log"))
        self.assertEqual(baseline_artifact["type"], "pgta_baseline_qc")
        self.assertTrue(baseline_artifact["path"].endswith("baseline_qc_summary.tsv"))


if __name__ == "__main__":
    unittest.main()
