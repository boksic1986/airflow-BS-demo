import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.progress_events import SnakemakeProgressParser, emit_progress_event


class ProgressEventsTests(unittest.TestCase):
    def test_emit_progress_event_writes_jsonl_and_posts_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            posted = []

            def fake_urlopen(request, timeout=0):  # type: ignore[no-untyped-def]
                posted.append(json.loads(request.data.decode("utf-8")))
                response = Mock()
                response.__enter__ = Mock(return_value=response)
                response.__exit__ = Mock(return_value=False)
                response.status = 200
                return response

            with patch("common.progress_events.urllib.request.urlopen", side_effect=fake_urlopen):
                event_path = emit_progress_event(
                    analysis_id="PGTA_TEST",
                    workdir=workdir,
                    backend_event_url="http://backend:8000/api/events/snakemake",
                    event="job_started",
                    rule="metadata",
                    status="running",
                    sample_id="G1",
                    snakemake_jobid="1",
                    stdout_path=workdir / "logs" / "snakemake.stdout.log",
                    stderr_path=workdir / "logs" / "snakemake.stderr.log",
                )

            events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(event_path.name, "snakemake_events.jsonl")
        self.assertEqual(events[0]["analysis_id"], "PGTA_TEST")
        self.assertEqual(events[0]["rule"], "metadata")
        self.assertEqual(events[0]["sample_id"], "G1")
        self.assertEqual(posted[0]["status"], "running")

    def test_emit_progress_event_records_backend_post_error_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"

            with patch("common.progress_events.urllib.request.urlopen", side_effect=OSError("network down")):
                event_path = emit_progress_event(
                    analysis_id="PGTA_TEST",
                    workdir=workdir,
                    backend_event_url="http://backend:8000/api/events/snakemake",
                    event="job_started",
                    rule="metadata",
                    status="running",
                )

            lines = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(lines[0]["event"], "job_started")
        self.assertEqual(lines[1]["event"], "backend_post_error")
        self.assertIn("network down", lines[1]["message"])

    def test_snakemake_progress_parser_tracks_running_success_and_failed_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            parser = SnakemakeProgressParser(
                analysis_id="PGTA_TEST",
                workdir=workdir,
                backend_event_url=None,
                stdout_path=workdir / "logs" / "snakemake.stdout.log",
                stderr_path=workdir / "logs" / "snakemake.stderr.log",
            )

            for line in [
                "rule fastp:\n",
                "    jobid: 1\n",
                "    wildcards: sample=G10\n",
                "\n",
                "Finished jobid: 1 (Rule: fastp)\n",
                "rule baseline_bam_uniformity_qc:\n",
                "    jobid: 2\n",
                "    wildcards: sample=G11\n",
                "\n",
                "Error in rule baseline_bam_uniformity_qc:\n",
            ]:
                parser.process_line(line)
            parser.finish()

            events = [
                json.loads(line)
                for line in (workdir / "logs" / "events" / "snakemake_events.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(
            [(event["rule"], event["sample_id"], event["status"]) for event in events],
            [
                ("fastp", "G10", "running"),
                ("fastp", "G10", "success"),
                ("baseline_bam_uniformity_qc", "G11", "running"),
                ("baseline_bam_uniformity_qc", "G11", "failed"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
