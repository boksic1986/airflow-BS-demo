import json
import logging
import sys
import tempfile
import unittest
from dataclasses import fields
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
