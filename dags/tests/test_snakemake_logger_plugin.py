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


if __name__ == "__main__":
    unittest.main()
