import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pgta_airflow_runner import (
    collect_snakemake_events,
    run_snakemake9_with_logger,
    validate_pgta_airflow_conf,
)


class PgtaAirflowRunnerTests(unittest.TestCase):
    def test_validate_conf_accepts_manifest_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_AIRFLOW_TEST"
            manifest = workdir / "config" / "samples.selected.tsv"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("sample_id\tR1\tR2\tsource_dir\n", encoding="utf-8")

            conf = validate_pgta_airflow_conf(
                {
                    "analysis_id": "PGTA_AIRFLOW_TEST",
                    "workdir": str(workdir),
                    "sample_sheet_path": str(manifest),
                    "target": "metadata",
                    "email_to": None,
                },
                shared_root=Path(tmpdir),
            )

        self.assertEqual(conf["analysis_id"], "PGTA_AIRFLOW_TEST")
        self.assertEqual(conf["target"], "metadata")
        self.assertEqual(conf["sample_sheet_path"], str(manifest.resolve()))

    def test_validate_conf_preserves_optional_backend_event_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_AIRFLOW_TEST"
            manifest = workdir / "config" / "samples.selected.tsv"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("sample_id\tR1\tR2\tsource_dir\n", encoding="utf-8")

            conf = validate_pgta_airflow_conf(
                {
                    "analysis_id": "PGTA_AIRFLOW_TEST",
                    "workdir": str(workdir),
                    "sample_sheet_path": str(manifest),
                    "target": "metadata",
                    "backend_event_url": "http://backend:8000/api/events/snakemake",
                },
                shared_root=Path(tmpdir),
            )

        self.assertEqual(conf["backend_event_url"], "http://backend:8000/api/events/snakemake")

    def test_validate_conf_rejects_non_metadata_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_AIRFLOW_TEST"
            manifest = workdir / "config" / "samples.selected.tsv"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("sample_id\tR1\tR2\tsource_dir\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "target=metadata"):
                validate_pgta_airflow_conf(
                    {
                        "analysis_id": "PGTA_AIRFLOW_TEST",
                        "workdir": str(workdir),
                        "sample_sheet_path": str(manifest),
                        "target": "dryrun_cnv",
                    },
                    shared_root=Path(tmpdir),
                )

    def test_run_snakemake9_invokes_logger_plugin_and_writes_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_AIRFLOW_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            completed = Mock(returncode=0)
            completed.stdout = "snakemake stdout\n"
            completed.stderr = "snakemake stderr\n"
            with patch("pgta_airflow_runner.subprocess.run", return_value=completed) as run:
                events_path = run_snakemake9_with_logger(
                    {
                        "analysis_id": "PGTA_AIRFLOW_TEST",
                        "workdir": str(workdir),
                        "config_path": str(config_path),
                    },
                    snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake9_env/bin/snakemake"),
                    pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                    dags_root=Path("/opt/airflow/dags"),
                )

            self.assertEqual(events_path, workdir / "logs" / "events" / "snakemake_events.jsonl")
            self.assertEqual((workdir / "logs" / "snakemake.stdout.log").read_text(encoding="utf-8"), "snakemake stdout\n")
            self.assertEqual((workdir / "logs" / "snakemake.stderr.log").read_text(encoding="utf-8"), "snakemake stderr\n")
            command = run.call_args.args[0]
            self.assertEqual(command[:5], ["/biosoftware/miniconda/envs/snakemake9_env/bin/snakemake", "--snakefile", "/opt/pipelines/PGT_A/Snakefile", "--cores", "1"])
            self.assertIn("--show-failed-logs", command)
            self.assertIn("--logger", command)
            self.assertIn("airflow-demo", command)
            self.assertIn("--logger-airflow-demo-analysis-id", command)
            self.assertIn("--logger-airflow-demo-events-path", command)
            self.assertIn("/opt/airflow/dags", run.call_args.kwargs["env"]["PYTHONPATH"])
            cache_dir = workdir / "tmp" / "xdg-cache"
            self.assertTrue(cache_dir.is_dir())
            self.assertEqual(run.call_args.kwargs["env"]["XDG_CACHE_HOME"], str(cache_dir))
            command_text = (workdir / "logs" / "snakemake.command.txt").read_text(encoding="utf-8")
            self.assertIn("--logger airflow-demo", command_text)
            self.assertIn(f"--configfile {config_path}", command_text)

    def test_run_snakemake9_passes_optional_backend_event_url_to_logger(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_AIRFLOW_TEST"
            workdir.mkdir(parents=True)
            config_path = workdir / "config.yaml"
            config_path.write_text("samples: {}\n", encoding="utf-8")

            completed = Mock(returncode=0)
            completed.stdout = ""
            completed.stderr = ""
            with patch("pgta_airflow_runner.subprocess.run", return_value=completed) as run:
                run_snakemake9_with_logger(
                    {
                        "analysis_id": "PGTA_AIRFLOW_TEST",
                        "workdir": str(workdir),
                        "config_path": str(config_path),
                        "backend_event_url": "http://backend:8000/api/events/snakemake",
                    },
                    snakemake_bin=Path("/biosoftware/miniconda/envs/snakemake9_env/bin/snakemake"),
                    pgta_pipeline_root=Path("/opt/pipelines/PGT_A"),
                    dags_root=Path("/opt/airflow/dags"),
                )

            command = run.call_args.args[0]
            self.assertIn("--logger-airflow-demo-backend-event-url", command)
            self.assertIn("http://backend:8000/api/events/snakemake", command)

    def test_collect_snakemake_events_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_AIRFLOW_TEST"
            events_path = workdir / "logs" / "events" / "snakemake_events.jsonl"
            events_path.parent.mkdir(parents=True)
            events = [
                {"analysis_id": "PGTA_AIRFLOW_TEST", "event": "job_started", "status": "running", "rule": "metadata", "sample_id": "G1", "snakemake_jobid": "1", "message": "started"},
                {"analysis_id": "PGTA_AIRFLOW_TEST", "event": "job_finished", "status": "success", "rule": "metadata", "sample_id": "G1", "snakemake_jobid": "1", "message": "done"},
                {"analysis_id": "PGTA_AIRFLOW_TEST", "event": "job_error", "status": "failed", "rule": "qc", "sample_id": "G2", "snakemake_jobid": "2", "message": "boom"},
            ]
            events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            summary = collect_snakemake_events({"analysis_id": "PGTA_AIRFLOW_TEST", "workdir": str(workdir)})
            summary_path = Path(summary["summary_path"])
            summary_text = summary_path.read_text(encoding="utf-8")

            self.assertEqual(summary["event_count"], 3)
            self.assertEqual(summary["status_counts"], {"failed": 1, "running": 1, "success": 1})
            self.assertEqual(summary["failed_jobs"][0]["rule"], "qc")
            self.assertTrue(summary_path.exists())
            self.assertIn("rule\tstatus\tsample_id", summary_text)


if __name__ == "__main__":
    unittest.main()
