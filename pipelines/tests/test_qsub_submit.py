from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipelines.common.qsub_submit import (
    build_submission_context,
    emit_event,
    run_mock_submission,
)


class QsubSubmitTests(unittest.TestCase):
    def test_build_submission_context_uses_job_properties_and_stable_mock_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "WES_20260704_000001"
            jobscript = Path(tmpdir) / "jobscript.sh"
            properties = {
                "rule": "bwa_mem",
                "jobid": 7,
                "threads": 2,
                "wildcards": {"sample": "S001"},
                "resources": {"mem_mb": 512, "runtime": 10},
                "params": {"analysis_id": "WES_20260704_000001", "workdir": str(workdir)},
            }
            jobscript.write_text("# properties = " + json.dumps(properties) + "\n", encoding="utf-8")

            context = build_submission_context(jobscript, environ={"AIRFLOW_DEMO_QSUB_MODE": "mock"})

        self.assertEqual(context.analysis_id, "WES_20260704_000001")
        self.assertEqual(context.rule, "bwa_mem")
        self.assertEqual(context.sample_id, "S001")
        self.assertEqual(context.snakemake_jobid, "7")
        self.assertEqual(context.qsub_jobid, "MOCK-WES_20260704_000001-7-bwa_mem-S001")
        self.assertEqual(context.stdout_path, workdir / "logs" / "qsub" / "bwa_mem.S001.o")
        self.assertEqual(context.stderr_path, workdir / "logs" / "qsub" / "bwa_mem.S001.e")
        self.assertEqual(context.resources["mem_mb"], 512)

    def test_run_mock_submission_executes_jobscript_and_records_final_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "WES_20260704_000001"
            output = workdir / "outputs" / "done.txt"
            jobscript = Path(tmpdir) / "jobscript.sh"
            properties = {
                "rule": "fastp",
                "jobid": 3,
                "threads": 1,
                "wildcards": {"sample": "S001"},
                "resources": {"mem_mb": 256},
                "params": {"analysis_id": "WES_20260704_000001", "workdir": str(workdir)},
            }
            jobscript.write_text(
                "#!/usr/bin/env bash\n"
                "# properties = " + json.dumps(properties) + "\n"
                "set -euo pipefail\n"
                f"mkdir -p {output.parent}\n"
                f"echo ok > {output}\n",
                encoding="utf-8",
            )

            context = build_submission_context(jobscript, environ={"AIRFLOW_DEMO_QSUB_MODE": "mock"})
            exit_code = run_mock_submission(context)

            events = [
                json.loads(line)
                for line in (workdir / "logs" / "events" / "snakemake_events.jsonl").read_text(encoding="utf-8").splitlines()
            ]

            self.assertEqual(exit_code, 0)
            self.assertTrue(output.is_file())
            self.assertTrue(context.stdout_path.is_file())
            self.assertTrue(context.stderr_path.is_file())
            self.assertEqual([event["status"] for event in events], ["submitted", "success"])
            self.assertEqual(events[-1]["qsub_jobid"], "MOCK-WES_20260704_000001-3-fastp-S001")

    def test_emit_event_posts_to_backend_and_keeps_jsonl_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "WES_20260704_000001"
            jobscript = Path(tmpdir) / "jobscript.sh"
            properties = {
                "rule": "markdup",
                "jobid": 9,
                "wildcards": {"sample": "S001"},
                "params": {"analysis_id": "WES_20260704_000001", "workdir": str(workdir)},
            }
            jobscript.write_text("# properties = " + json.dumps(properties) + "\n", encoding="utf-8")
            context = build_submission_context(
                jobscript,
                environ={
                    "AIRFLOW_DEMO_QSUB_MODE": "mock",
                    "AIRFLOW_DEMO_BACKEND_EVENT_URL": "http://backend:8000/api/events/snakemake",
                },
            )

            with patch("pipelines.common.qsub_submit.urlopen") as urlopen:
                emit_event(context, status="submitted")

            fallback = workdir / "logs" / "events" / "snakemake_events.jsonl"
            event = json.loads(fallback.read_text(encoding="utf-8").splitlines()[0])
            request = urlopen.call_args.args[0]

        self.assertEqual(request.full_url, "http://backend:8000/api/events/snakemake")
        self.assertEqual(event["rule"], "markdup")
        self.assertEqual(event["status"], "submitted")
        self.assertEqual(event["sample_id"], "S001")


if __name__ == "__main__":
    unittest.main()
