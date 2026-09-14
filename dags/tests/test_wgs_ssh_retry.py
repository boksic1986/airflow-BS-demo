"""No real SSH or workflow side effects; exercise the real dispatch boundary."""
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bio_wgs


class WgsSshRetryTests(unittest.TestCase):
    def dispatch(self, replies):
        calls, sleeps, registrations, queries = [], [], [], []
        conf = {"analysis_id": "WGS_20260915_010203_A1B2C3", "attempt": 1,
                "params": {"submission_mode": "three_stage"}}

        def backend(path, **kwargs):
            if kwargs.get("method") == "POST":
                registrations.append(kwargs["payload"])
                return {"generation": 2, "execution_id": "synthetic-execution"}
            queries.append(path)
            return {"status": "failed", "retry_no": 1}

        def run(command, **kwargs):
            calls.append(list(command))
            return replies.pop(0)

        with patch.object(bio_wgs, "_require_runtime_enabled"), \
             patch.object(bio_wgs, "_backend_json", side_effect=backend), \
             patch.object(bio_wgs.subprocess, "run", side_effect=run), \
             patch.object(bio_wgs.time, "sleep", side_effect=sleeps.append):
            try:
                result = bio_wgs.run_stage_on_200(
                    "prepare_analysis", dag_run=SimpleNamespace(conf=conf))
            except RuntimeError as exc:
                result = exc
        return result, calls, sleeps, registrations, queries

    @staticmethod
    def reply(code=255, error="Connection timed out during banner exchange", stdout=""):
        return subprocess.CompletedProcess(["ssh"], code, stdout, error)

    def test_banner_failure_reconnects_without_reregistering(self):
        result, calls, sleeps, registrations, queries = self.dispatch([
            self.reply(), self.reply(), self.reply(0, "", "{}")])
        self.assertIsInstance(result, dict)
        self.assertEqual(result["execution_id"], "synthetic-execution")
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(command == calls[0] for command in calls))
        self.assertEqual(sleeps, [5.0, 10.0])
        self.assertEqual(len(registrations), 1)
        self.assertNotIn("force_new_generation", registrations[0])
        self.assertEqual(queries, [])

    def test_connection_retry_is_bounded(self):
        result, calls, sleeps, registrations, _ = self.dispatch([self.reply()] * 3)
        self.assertIsInstance(result, RuntimeError)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [5.0, 10.0])
        self.assertEqual(len(registrations), 1)

    def test_known_connect_and_jump_handshake_failures_reconnect(self):
        for error in [
            "ssh: connect to host test-node port 22: Connection refused",
            "ssh: connect to host test-node port 22: Connection timed out",
            "kex_exchange_identification: read: Connection reset\n"
            "Connection reset by 192.0.2.1 port 22\n"
            "Connection closed by UNKNOWN port 65535",
        ]:
            with self.subTest(error=error):
                result, calls, sleeps, registrations, _ = self.dispatch([
                    self.reply(error=error), self.reply(0, "", "{}")])
                self.assertIsInstance(result, dict)
                self.assertEqual(len(calls), 2)
                self.assertEqual(sleeps, [5.0])
                self.assertEqual(len(registrations), 1)

    def test_auth_business_or_ambiguous_disconnect_never_replays(self):
        for reply in [self.reply(error="Permission denied (publickey)."),
                      self.reply(error="Host key verification failed."),
                      self.reply(error="client_loop: send disconnect: Broken pipe"),
                      self.reply(1, "project directory already exists"),
                      self.reply(stdout="remote execution started"),
                      self.reply(error="Connection timed out during banner exchange\nTraceback: remote error")]:
            with self.subTest(error=reply.stderr, stdout=reply.stdout):
                result, calls, sleeps, _, queries = self.dispatch([reply])
                self.assertIsInstance(result, RuntimeError)
                self.assertEqual(len(calls), 1)
                self.assertEqual(sleeps, [])
                self.assertEqual(len(queries), 1)

    def test_connection_budget_not_reset_by_request_visibility_retry(self):
        missing = self.reply(1, "registered runtime request is missing")
        result, calls, sleeps, registrations, _ = self.dispatch([
            self.reply(), missing, self.reply(), self.reply()])
        self.assertIsInstance(result, RuntimeError)
        self.assertEqual(len(calls), 4)
        self.assertEqual(sleeps, [5.0, 1.0, 10.0])
        self.assertEqual(len(registrations), 1)


if __name__ == "__main__":
    unittest.main()
