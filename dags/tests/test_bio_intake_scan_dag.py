import json
import os
from datetime import datetime
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_intake_scan


class BioIntakeScanDagTests(unittest.TestCase):
    def test_dag_id_and_task(self) -> None:
        dag = bio_intake_scan.dag

        self.assertEqual(dag.dag_id, "bio_intake_scan")
        self.assertEqual(set(dag.task_ids), {"scan_and_submit", "prune_scanner_history", "propagate_scanner_result"})
        self.assertTrue(dag.is_paused_upon_creation)
        self.assertEqual(dag.get_task("propagate_scanner_result").upstream_task_ids, {"prune_scanner_history"})

    def test_run_intake_scan_posts_configured_payload(self) -> None:
        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"items":[]}'

        class DummyDagRun:
            conf = {"pipelines": ["nipt_docker"], "bootstrap": True, "max_samples": 12}

        with patch.dict(
            os.environ,
            {
                "BACKEND_BASE_URL": "http://backend:8000",
                "INTAKE_SCAN_TIMEOUT_SECONDS": "5",
                "INTERNAL_SERVICE_TOKEN": "service-secret",
            },
        ):
            with patch("bio_intake_scan.urlopen", return_value=DummyResponse()) as mocked_urlopen:
                result = bio_intake_scan.run_intake_scan(dag_run=DummyDagRun())

        self.assertEqual(result, {"items": []})
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://backend:8000/api/intake/scan-and-submit")
        self.assertEqual(request.get_header("X-airflow-demo-token"), "service-secret")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"pipelines": ["nipt_docker"], "bootstrap": True, "max_samples": 12})

    def test_default_scheduled_scan_requests_pgta_and_nipt_discovery(self) -> None:
        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"items":[]}'

        class DummyDagRun:
            conf = {}

        with patch.dict(
            os.environ,
            {
                "BACKEND_BASE_URL": "http://backend:8000",
                "INTAKE_SCAN_TIMEOUT_SECONDS": "5",
            },
            clear=True,
        ):
            with patch("bio_intake_scan.urlopen", return_value=DummyResponse()) as mocked_urlopen:
                bio_intake_scan.run_intake_scan(dag_run=DummyDagRun())

        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data.decode("utf-8"))["pipelines"], ["pgta", "nipt_docker"])

    def test_retention_calls_scanner_only_backend_endpoint(self) -> None:
        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"deleted":0,"protected":1}'

        class DummyDagRun:
            run_id = "scheduled__2026-07-13T03:00:00+08:00"

        with patch.dict(
            os.environ,
            {"BACKEND_BASE_URL": "http://backend:8000", "INTERNAL_SERVICE_TOKEN": "secret"},
            clear=True,
        ):
            with patch("bio_intake_scan.urlopen", return_value=DummyResponse()) as mocked_urlopen:
                result = bio_intake_scan.run_scanner_retention(dag_run=DummyDagRun())

        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://backend:8000/api/intake/retention")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"dag_id": "bio_intake_scan", "current_dag_run_id": DummyDagRun.run_id, "dry_run": False})
        self.assertEqual(result["deleted"], 0)

    def test_retention_runs_once_at_the_configured_minute(self) -> None:
        with patch.dict(os.environ, {"INTAKE_RETENTION_HOUR": "3", "INTAKE_RETENTION_MINUTE": "0"}, clear=True):
            with patch("bio_intake_scan.urlopen") as mocked_urlopen:
                result = bio_intake_scan.run_scanner_retention(logical_date=datetime(2026, 7, 13, 3, 10))

        self.assertTrue(result["skipped"])
        mocked_urlopen.assert_not_called()

    def test_terminal_task_propagates_scan_failure(self) -> None:
        class DummyTaskInstance:
            def __init__(self, state):
                self.state = state

        class DummyDagRun:
            states = {"scan_and_submit": "failed", "prune_scanner_history": "success"}

            def get_task_instance(self, *, task_id):
                return DummyTaskInstance(self.states[task_id])

        with self.assertRaisesRegex(RuntimeError, "scan_and_submit=failed"):
            bio_intake_scan.propagate_scanner_result(dag_run=DummyDagRun())


if __name__ == "__main__":
    unittest.main()
