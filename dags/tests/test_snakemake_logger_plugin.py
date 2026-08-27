import json
import logging
import sys
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from snakemake_interface_logger_plugins.common import LogEvent
except ModuleNotFoundError:  # Airflow's Python env does not provide Snakemake 9.
    LogEvent = None


@unittest.skipIf(LogEvent is None, "Snakemake 9 logger interface is not installed in this Python env")
class SnakemakeLoggerPluginTests(unittest.TestCase):
    def test_logger_settings_expose_runtime_argparse_types(self) -> None:
        from snakemake_logger_plugin_airflow_demo import LogHandlerSettings

        field_types = {item.name: item.type for item in fields(LogHandlerSettings)}

        self.assertIs(field_types["analysis_id"], str)
        self.assertIs(field_types["workdir"], Path)
        self.assertIs(field_types["events_path"], Path)
        self.assertIs(field_types["backend_event_url"], str)
        self.assertIs(field_types["post_timeout_seconds"], float)
        self.assertIs(field_types["dry_run"], bool)
        self.assertIs(field_types["attempt"], int)
        self.assertIs(field_types["pipeline_release_id"], str)
        self.assertIs(field_types["run_label"], str)
        self.assertIs(field_types["role"], str)
        self.assertIs(field_types["stream_id"], str)

    def test_cce_logger_writes_offline_observer_contract(self) -> None:
        from snakemake_logger_plugin_airflow_demo import LogHandler, LogHandlerSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "rule-status" / "raw" / "master.jsonl"
            handler = LogHandler(
                common_settings=None,
                settings=LogHandlerSettings(
                    analysis_id="WGS_20260813_010203_A1B2C3",
                    attempt=2,
                    pipeline_release_id="wgs-4.1.1-1778fca",
                    run_label="wgs401-0123456789abcdef",
                    role="master",
                    stream_id="master",
                    workdir=Path(tmpdir),
                    events_path=path,
                ),
            )
            record = logging.LogRecord("snakemake", logging.INFO, "Snakefile", 1, "started", (), None)
            record.event = LogEvent.JOB_STARTED
            record.rule = "pre_process_mapping"
            record.job_id = 7
            record.wildcards = {"sample": "S1"}
            handler.emit(record)
            payload = json.loads(path.read_text(encoding="utf-8").strip())

        self.assertEqual(payload["schema_version"], "1")
        self.assertEqual(payload["analysis_id"], "WGS_20260813_010203_A1B2C3")
        self.assertEqual(payload["attempt"], 2)
        self.assertEqual(payload["pipeline_release_id"], "wgs-4.1.1-1778fca")
        self.assertEqual(payload["run_label"], "wgs401-0123456789abcdef")
        self.assertEqual(payload["role"], "master")
        self.assertEqual(payload["stream_id"], "master")
        self.assertEqual(payload["rule_name"], "pre_process_mapping")
        self.assertTrue(payload["rule_instance_id"])
        self.assertIsInstance(payload["timestamp"], float)

    def test_dry_run_logger_marks_planned_jobs_as_skipped(self) -> None:
        from snakemake_logger_plugin_airflow_demo import LogHandler, LogHandlerSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            events_path = Path(tmpdir) / "events" / "snakemake_events.jsonl"
            handler = LogHandler(
                common_settings=None,
                settings=LogHandlerSettings(
                    analysis_id="WGS_DRY_RUN_TEST",
                    workdir=Path(tmpdir),
                    events_path=events_path,
                    dry_run=True,
                ),
            )
            record = logging.LogRecord(
                name="snakemake",
                level=logging.INFO,
                pathname="snakefile",
                lineno=1,
                msg="Rule: mapping, Jobid: 1",
                args=(),
                exc_info=None,
            )
            record.event = LogEvent.JOB_INFO
            record.rule = "mapping"
            record.job_id = 1
            record.wildcards = {"sample": "WGS-01"}

            handler.emit(record)

            payload = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(payload["status"], "skipped")
        self.assertEqual(payload["event"], "dry_run_planned")
        self.assertIn("not executed", payload["message"])

    def test_logger_writes_job_events_jsonl(self) -> None:
        from snakemake_logger_plugin_airflow_demo import LogHandler, LogHandlerSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            events_path = Path(tmpdir) / "events" / "snakemake_events.jsonl"
            handler = LogHandler(
                common_settings=None,
                settings=LogHandlerSettings(
                    analysis_id="PGTA_AIRFLOW_TEST",
                    workdir=Path(tmpdir),
                    events_path=events_path,
                ),
            )

            for event, extra in [
                (LogEvent.JOB_STARTED, {"rule": "metadata", "job_id": 1, "wildcards": {"sample": "G1"}}),
                (LogEvent.JOB_FINISHED, {"rule": "metadata", "job_id": 1, "wildcards": {"sample": "G1"}}),
                (LogEvent.JOB_ERROR, {"rule": "qc", "job_id": 2, "wildcards": {"sample": "G2"}}),
            ]:
                record = logging.LogRecord(
                    name="snakemake",
                    level=logging.INFO,
                    pathname="snakefile",
                    lineno=1,
                    msg=f"{event} message",
                    args=(),
                    exc_info=None,
                )
                record.event = event
                for key, value in extra.items():
                    setattr(record, key, value)
                handler.emit(record)

            lines = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual([line["status"] for line in lines], ["running", "success", "failed"])
        self.assertEqual(lines[0]["analysis_id"], "PGTA_AIRFLOW_TEST")
        self.assertEqual(lines[0]["rule"], "metadata")
        self.assertEqual(lines[0]["sample_id"], "G1")
        self.assertEqual(lines[0]["snakemake_jobid"], "1")

    def test_logger_posts_rule_events_when_backend_url_is_configured(self) -> None:
        from snakemake_logger_plugin_airflow_demo import LogHandler, LogHandlerSettings

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("urllib.request.urlopen") as urlopen,
            patch.dict("os.environ", {"INTERNAL_SERVICE_TOKEN": "service-secret"}),
        ):
            urlopen.return_value.__enter__.return_value.read.return_value = b'{"status":"ok"}'
            events_path = Path(tmpdir) / "events" / "snakemake_events.jsonl"
            handler = LogHandler(
                common_settings=None,
                settings=LogHandlerSettings(
                    analysis_id="PGTA_AIRFLOW_TEST",
                    workdir=Path(tmpdir),
                    events_path=events_path,
                    backend_event_url="http://backend:8000/api/events/snakemake",
                ),
            )
            record = logging.LogRecord(
                name="snakemake",
                level=logging.INFO,
                pathname="snakefile",
                lineno=1,
                msg="started",
                args=(),
                exc_info=None,
            )
            record.event = LogEvent.JOB_STARTED
            record.rule = "metadata"
            record.job_id = 1
            record.wildcards = {"sample": "G1"}

            handler.emit(record)

            request = urlopen.call_args.args[0]
            payload = json.loads(request.data.decode("utf-8"))

        self.assertEqual(request.full_url, "http://backend:8000/api/events/snakemake")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(request.get_header("X-airflow-demo-token"), "service-secret")
        self.assertEqual(payload["analysis_id"], "PGTA_AIRFLOW_TEST")
        self.assertEqual(payload["rule"], "metadata")
        self.assertEqual(payload["status"], "running")

    def test_logger_records_post_failure_without_failing_emit(self) -> None:
        from snakemake_logger_plugin_airflow_demo import LogHandler, LogHandlerSettings

        with tempfile.TemporaryDirectory() as tmpdir, patch("urllib.request.urlopen", side_effect=OSError("backend down")):
            events_path = Path(tmpdir) / "events" / "snakemake_events.jsonl"
            handler = LogHandler(
                common_settings=None,
                settings=LogHandlerSettings(
                    analysis_id="PGTA_AIRFLOW_TEST",
                    workdir=Path(tmpdir),
                    events_path=events_path,
                    backend_event_url="http://backend:8000/api/events/snakemake",
                ),
            )
            record = logging.LogRecord(
                name="snakemake",
                level=logging.INFO,
                pathname="snakefile",
                lineno=1,
                msg="started",
                args=(),
                exc_info=None,
            )
            record.event = LogEvent.JOB_STARTED
            record.rule = "metadata"
            record.job_id = 1
            record.wildcards = {"sample": "G1"}

            handler.emit(record)

            lines = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(lines[0]["event"], "job_started")
        self.assertEqual(lines[1]["event"], "backend_post_error")
        self.assertIn("backend down", lines[1]["message"])

    def test_logger_uses_job_info_context_for_finished_events_without_rule(self) -> None:
        from snakemake_logger_plugin_airflow_demo import LogHandler, LogHandlerSettings

        with tempfile.TemporaryDirectory() as tmpdir, patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b'{"status":"ok"}'
            events_path = Path(tmpdir) / "events" / "snakemake_events.jsonl"
            handler = LogHandler(
                common_settings=None,
                settings=LogHandlerSettings(
                    analysis_id="PGTA_AIRFLOW_TEST",
                    workdir=Path(tmpdir),
                    events_path=events_path,
                    backend_event_url="http://backend:8000/api/events/snakemake",
                ),
            )
            job_info = logging.LogRecord(
                name="snakemake",
                level=logging.INFO,
                pathname="snakefile",
                lineno=1,
                msg="Rule: metadata, Jobid: 1",
                args=(),
                exc_info=None,
            )
            job_info.event = "job_info"
            job_info.rule = "metadata"
            job_info.job_id = 1
            job_info.log = [str(Path(tmpdir) / "logs" / "metadata.log")]
            handler.emit(job_info)

            finished = logging.LogRecord(
                name="snakemake",
                level=logging.INFO,
                pathname="snakefile",
                lineno=1,
                msg="Finished jobid: 1 (Rule: metadata)",
                args=(),
                exc_info=None,
            )
            finished.event = LogEvent.JOB_FINISHED
            finished.job_id = 1
            handler.emit(finished)

            payloads = [json.loads(call.args[0].data.decode("utf-8")) for call in urlopen.call_args_list]

        self.assertEqual(payloads[0]["event"], "job_info")
        self.assertEqual(payloads[0]["rule"], "metadata")
        self.assertEqual(payloads[0]["status"], "running")
        self.assertTrue(payloads[0]["stdout_path"].endswith("logs/metadata.log"))
        self.assertEqual(payloads[1]["event"], "job_finished")
        self.assertEqual(payloads[1]["rule"], "metadata")
        self.assertEqual(payloads[1]["status"], "success")


if __name__ == "__main__":
    unittest.main()
