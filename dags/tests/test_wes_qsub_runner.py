import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import wes_qsub_runner
from wes_qsub_runner import (
    build_snakemake_command,
    collect_wes_artifacts,
    prepare_wes_config,
    run_wes_qsub,
    validate_wes_conf,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class WesQsubRunnerTests(unittest.TestCase):
    def _valid_conf(self, workdir: Path) -> dict:
        return {
            "analysis_id": "WES_AIRFLOW_TEST",
            "pipeline": "wes_qsub",
            "mode": "new",
            "workdir": str(workdir),
            "backend_event_url": None,
            "params": {"target": "final_summary", "max_jobs": 2},
        }

    def test_validate_wes_conf_accepts_only_mock_final_summary_new_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            workdir = shared_root / "runs" / "WES_AIRFLOW_TEST"
            workdir.mkdir(parents=True)

            conf = validate_wes_conf(self._valid_conf(workdir), shared_root=shared_root)

        self.assertEqual(conf["analysis_id"], "WES_AIRFLOW_TEST")
        self.assertEqual(conf["pipeline"], "wes_qsub")
        self.assertEqual(conf["mode"], "new")
        self.assertEqual(conf["params"]["target"], "final_summary")
        self.assertEqual(conf["params"]["max_jobs"], 2)

    def test_validate_wes_conf_accepts_resume_and_rerun_rule_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            workdir = shared_root / "runs" / "WES_AIRFLOW_TEST"
            workdir.mkdir(parents=True)

            resume_conf = self._valid_conf(workdir)
            resume_conf["mode"] = "resume"
            resume = validate_wes_conf(resume_conf, shared_root=shared_root)

            rerun_conf = self._valid_conf(workdir)
            rerun_conf["mode"] = "rerun_rule"
            rerun_conf["params"]["rule"] = "fastp"
            rerun_conf["params"]["sample_id"] = "S001"
            rerun = validate_wes_conf(rerun_conf, shared_root=shared_root)

        self.assertEqual(resume["mode"], "resume")
        self.assertEqual(rerun["mode"], "rerun_rule")
        self.assertEqual(rerun["params"]["rule"], "fastp")
        self.assertEqual(rerun["params"]["sample_id"], "S001")

    def test_validate_wes_conf_rejects_forceall_and_bad_rerun_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            workdir = shared_root / "runs" / "WES_AIRFLOW_TEST"
            workdir.mkdir(parents=True)

            bad_mode = self._valid_conf(workdir)
            bad_mode["mode"] = "forceall"
            with self.assertRaisesRegex(ValueError, "Unsupported WES mode"):
                validate_wes_conf(bad_mode, shared_root=shared_root)

            bad_rule = self._valid_conf(workdir)
            bad_rule["mode"] = "rerun_rule"
            bad_rule["params"]["rule"] = "haplotypecaller"
            bad_rule["params"]["sample_id"] = "S001"
            with self.assertRaisesRegex(ValueError, "Unsupported WES rerun rule"):
                validate_wes_conf(bad_rule, shared_root=shared_root)

            missing_sample = self._valid_conf(workdir)
            missing_sample["mode"] = "rerun_rule"
            missing_sample["params"]["rule"] = "fastp"
            with self.assertRaisesRegex(ValueError, "sample_id is required"):
                validate_wes_conf(missing_sample, shared_root=shared_root)

    def test_validate_wes_conf_rejects_unknown_pipeline_or_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            workdir = shared_root / "runs" / "WES_AIRFLOW_TEST"
            workdir.mkdir(parents=True)

            bad_pipeline = self._valid_conf(workdir)
            bad_pipeline["pipeline"] = "pgta"
            with self.assertRaisesRegex(ValueError, "pipeline must be wes_qsub"):
                validate_wes_conf(bad_pipeline, shared_root=shared_root)

            bad_target = self._valid_conf(workdir)
            bad_target["params"]["target"] = "bam"
            with self.assertRaisesRegex(ValueError, "Unsupported WES target"):
                validate_wes_conf(bad_target, shared_root=shared_root)

    def test_prepare_wes_config_writes_run_local_absolute_container_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            workdir = shared_root / "runs" / "WES_AIRFLOW_TEST"
            workdir.mkdir(parents=True)
            conf = validate_wes_conf(self._valid_conf(workdir), shared_root=shared_root)

            config_path = prepare_wes_config(
                conf,
                repo_root=REPO_ROOT,
                pipelines_root=Path("/opt/airflow/pipelines"),
            )

            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            request = json.loads((workdir / "config" / "wes_airflow_request.json").read_text(encoding="utf-8"))

        self.assertEqual(config_path, workdir / "config" / "wes_mock_config.yaml")
        self.assertEqual(config["analysis_id"], "WES_AIRFLOW_TEST")
        self.assertEqual(config["workdir"], str(workdir))
        self.assertIsNone(config["backend_event_url"])
        self.assertEqual(
            config["samples"]["S001"]["input"],
            "/opt/airflow/pipelines/wes/mock_data/S001.input.txt",
        )
        self.assertEqual(
            config["samples"]["S002"]["input"],
            "/opt/airflow/pipelines/wes/mock_data/S002.input.txt",
        )
        self.assertEqual(request["analysis_id"], "WES_AIRFLOW_TEST")
        self.assertEqual(request["params"]["target"], "final_summary")

    def test_build_snakemake_command_uses_airflow_mounts_and_profile(self) -> None:
        command = build_snakemake_command(
            Path("/data/airflow-demo/runs/WES_TEST/config/wes_mock_config.yaml"),
            pipelines_root=Path("/opt/airflow/pipelines"),
            profiles_root=Path("/opt/airflow/profiles"),
        )

        self.assertEqual(command[0], "snakemake")
        self.assertIn("--snakefile", command)
        self.assertIn("/opt/airflow/pipelines/wes/workflow/Snakefile", command)
        self.assertIn("--profile", command)
        self.assertIn("/opt/airflow/profiles/qsub", command)
        self.assertIn("--configfile", command)
        self.assertNotIn("--forceall", command)

    def test_build_snakemake_command_adds_forcerun_for_selected_rule_only(self) -> None:
        command = build_snakemake_command(
            Path("/data/airflow-demo/runs/WES_TEST/config/wes_mock_config.yaml"),
            mode="rerun_rule",
            rule="fastp",
            sample_id="S001",
            workdir=Path("/data/airflow-demo/runs/WES_TEST"),
            pipelines_root=Path("/opt/airflow/pipelines"),
            profiles_root=Path("/opt/airflow/profiles"),
        )

        self.assertIn("--forcerun", command)
        self.assertIn("fastp", command)
        self.assertIn("/data/airflow-demo/runs/WES_TEST/fastp/S001.clean.txt", command)
        self.assertNotIn("--forceall", command)

    def test_run_wes_qsub_uses_run_local_snakemake_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "WES_AIRFLOW_TEST"
            (workdir / "config").mkdir(parents=True)
            config_path = workdir / "config" / "wes_mock_config.yaml"
            config_path.write_text("analysis_id: WES_AIRFLOW_TEST\n", encoding="utf-8")
            conf = {
                "analysis_id": "WES_AIRFLOW_TEST",
                "workdir": str(workdir),
                "config_path": str(config_path),
            }
            captured: dict[str, object] = {}

            original_runner = wes_qsub_runner.run_command_to_logs

            def fake_run_command_to_logs(command, cwd, stdout_path, stderr_path, env):  # type: ignore[no-untyped-def]
                captured["env"] = env
                captured["stdout_path"] = stdout_path
                captured["stderr_path"] = stderr_path
                return {"exit_code": 0}

            wes_qsub_runner.run_command_to_logs = fake_run_command_to_logs
            try:
                run_wes_qsub(
                    conf,
                    airflow_root=Path("/opt/airflow"),
                    pipelines_root=Path("/opt/airflow/pipelines"),
                    profiles_root=Path("/opt/airflow/profiles"),
                )
            finally:
                wes_qsub_runner.run_command_to_logs = original_runner

            env = captured["env"]
            self.assertEqual(env["XDG_CACHE_HOME"], str(workdir / "tmp" / "xdg-cache"))
            self.assertTrue((workdir / "tmp" / "xdg-cache").is_dir())
            self.assertEqual(captured["stdout_path"], workdir / "logs" / "snakemake.stdout.log")
            self.assertEqual(captured["stderr_path"], workdir / "logs" / "snakemake.stderr.log")
            self.assertIn("snakemake", (workdir / "logs" / "snakemake.command.txt").read_text(encoding="utf-8"))

    def test_collect_wes_artifacts_requires_summary_and_counts_events_and_qsub_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "WES_AIRFLOW_TEST"
            (workdir / "reports").mkdir(parents=True)
            (workdir / "logs" / "events").mkdir(parents=True)
            (workdir / "logs" / "qsub").mkdir(parents=True)
            (workdir / "reports" / "final_summary.tsv").write_text(
                "sample_id\tstatus\nS001\tmock_success\nS002\tmock_success\n",
                encoding="utf-8",
            )
            (workdir / "reports" / "qc_summary.tsv").write_text(
                "sample_id\tmetric_name\tmetric_value\tmetric_numeric\tthreshold\tstatus\n"
                "S001\tworkflow_status\tmock_success\t\tmock_success\tpass\n",
                encoding="utf-8",
            )
            (workdir / "logs" / "events" / "snakemake_events.jsonl").write_text(
                '{"event":"qsub_submitted"}\n{"event":"qsub_success"}\n',
                encoding="utf-8",
            )
            (workdir / "logs" / "qsub" / "fastp.S001.o").write_text("ok\n", encoding="utf-8")
            (workdir / "logs" / "qsub" / "fastp.S001.e").write_text("", encoding="utf-8")

            artifact = collect_wes_artifacts({"analysis_id": "WES_AIRFLOW_TEST", "workdir": str(workdir)})

        self.assertEqual(artifact["type"], "wes_mock_summary")
        self.assertEqual(artifact["event_count"], 2)
        self.assertEqual(artifact["qsub_log_count"], 2)
        self.assertEqual(artifact["qc_metric_count"], 1)
        self.assertTrue(artifact["path"].endswith("reports/final_summary.tsv"))
        self.assertTrue(artifact["qc_path"].endswith("reports/qc_summary.tsv"))


if __name__ == "__main__":
    unittest.main()
