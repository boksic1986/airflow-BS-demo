"""Real Airflow DAG contract; synthetic HTTP responses, no database or cluster.

Run directly with python when pytest is not installed in the Airflow image.
"""
from datetime import timedelta
from http.client import IncompleteRead, RemoteDisconnected
from io import BytesIO
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from airflow.exceptions import AirflowException, AirflowFailException


class GatkNetworkRetryTests(unittest.TestCase):
    def setUp(self):
        self.ns = runpy.run_path(str(Path(__file__).parents[1] / "bio_gatk.py"))
        self.ready = self.ns["stage_ready"]
        self.context = {"dag_run": SimpleNamespace(conf={
            "analysis_id": "GATK_SYNTHETIC", "attempt": 2,
        })}

    def test_only_status_polling_has_bounded_backoff(self):
        dag = self.ns["dag"]
        polling = {task.task_id for task in dag.tasks
                   if task.python_callable.__name__ == "stage_ready"}
        self.assertIn("wait_step3_analysis", polling)
        for task in dag.tasks:
            if task.task_id in polling:
                self.assertGreater(task.retries, 0)
                self.assertLessEqual(task.retries, 6)
                self.assertTrue(task.retry_exponential_backoff)
                self.assertGreaterEqual(task.retry_delay, timedelta(seconds=30))
                self.assertLessEqual(task.max_retry_delay, timedelta(minutes=5))
                self.assertEqual(task.mode, "reschedule")
            else:
                # Re-running a stage registration or SSH may reopen a generation.
                self.assertEqual(task.retries, 0, task.task_id)

    def test_transport_and_retryable_http_failures_remain_retryable(self):
        failures = [URLError("connection refused"), TimeoutError("read timeout"),
                    ConnectionResetError("reset"), RemoteDisconnected("closed"),
                    IncompleteRead(b"partial", 100)]
        failures.extend(HTTPError("http://synthetic", code, "temporary", {},
                                  BytesIO(b"private upstream body"))
                        for code in (408, 429, 500, 502, 503, 504))
        for failure in failures:
            with self.subTest(failure=type(failure).__name__, code=getattr(failure, "code", None)):
                with patch.dict(self.ready.__globals__, {"urlopen": lambda *a, **kw: (_ for _ in ()).throw(failure)}):
                    with self.assertRaises(AirflowException) as raised:
                        self.ready("step3_monitor", **self.context)
                self.assertNotIsInstance(raised.exception, AirflowFailException)
                self.assertNotIn("private upstream body", str(raised.exception))

    def test_permanent_http_errors_bypass_remaining_retries(self):
        for code in (400, 401, 403, 404, 409, 422, 501):
            failure = HTTPError("http://synthetic", code, "permanent", {},
                                BytesIO(b"private upstream body"))
            with self.subTest(code=code):
                with patch.dict(self.ready.__globals__, {"urlopen": lambda *a, **kw: (_ for _ in ()).throw(failure)}):
                    with self.assertRaises(AirflowFailException) as raised:
                        self.ready("step3_monitor", **self.context)
                self.assertNotIn("private upstream body", str(raised.exception))

    def test_malformed_response_does_not_wait_out_network_retry_budget(self):
        for payload in (b"not json", b"[]", b"\xff"):
            with self.subTest(payload=payload):
                with patch.dict(self.ready.__globals__, {"urlopen": lambda *a, **kw: BytesIO(payload)}):
                    with self.assertRaises(AirflowFailException):
                        self.ready("step3_monitor", **self.context)

    def test_computation_failure_bypasses_remaining_retries(self):
        with patch.dict(self.ready.__globals__, {"urlopen": lambda *a, **kw: BytesIO(b'{"failed":true,"ready":false,"message":"Master failed"}')}):
            with self.assertRaises(AirflowFailException):
                self.ready("step3_monitor", **self.context)

    def test_recovered_poll_uses_same_attempt_without_stage_submission(self):
        requests = []
        def response(request, **kwargs):
            requests.append((request.method, request.full_url, request.data))
            return BytesIO(b'{"failed":false,"ready":true}')
        with patch.dict(self.ready.__globals__, {"urlopen": response}):
            self.assertTrue(self.ready("step3_monitor", **self.context))
        self.assertEqual(requests, [("GET", "http://backend:8000/api/internal/gatk/runs/GATK_SYNTHETIC/stage-status?attempt=2&stage=step3_monitor", None)])


if __name__ == "__main__":
    unittest.main()
