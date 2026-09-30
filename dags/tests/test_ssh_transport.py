"""UE-05 SSH connection delta; all commands and replies are synthetic."""

import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ssh_transport
from common.stage_execution import DispatchUncertain


COMMAND = [
    "ssh", "-tt", "-F", "/synthetic/ssh-config", "synthetic-node",
    "/synthetic/forced-command", "--native-submit", "SYNTHETIC", "1",
    "step5_download", "execution-1", "2", "a" * 64,
]
BANNER = (
    "Connection timed out during banner exchange\n"
    "Connection to 192.0.2.200 port 22 timed out\n"
)
IDENTITY = {
    "analysis_id": "SYNTHETIC", "attempt": 1, "stage": "step5_download",
    "execution_id": "execution-1", "stage_generation": 2,
    "request_hash": "a" * 64,
}
SUBMIT_TAIL = [
    "--native-submit", "SYNTHETIC", "1", "step5_download",
    "execution-1", "2", "a" * 64,
]


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def time(self):
        return 1000.0 + self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def reply(code=255, stderr=BANNER, stdout=""):
    return subprocess.CompletedProcess(COMMAND, code, stdout, stderr)


class SshTransportTests(unittest.TestCase):
    def clocked(self):
        clock = FakeClock()
        fake_time = SimpleNamespace(
            monotonic=clock.monotonic, time=clock.time, sleep=clock.sleep,
        )
        time_patch = patch.object(ssh_transport, "time", fake_time)
        time_patch.start()
        self.addCleanup(time_patch.stop)
        return clock

    def test_banner_reconnect_preserves_exact_command_and_single_budget(self):
        clock = self.clocked()
        calls = []
        responses = iter([reply(), reply(0, "", '{"state":"accepted"}')])

        def run(command, **kwargs):
            calls.append((list(command), kwargs["timeout"]))
            clock.now += 1
            return next(responses)

        with patch.object(ssh_transport.subprocess, "run", side_effect=run):
            result = ssh_transport.run_ssh(COMMAND, timeout_seconds=120)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], calls[1][0])
        self.assertEqual(calls[0][0][-len(COMMAND) + 1:], COMMAND[1:])
        self.assertEqual(calls[0][0][:5], [
            "ssh", "-o", "ConnectTimeout=30", "-o", "ConnectionAttempts=1",
        ])
        self.assertEqual(calls[0][1], 120)
        self.assertTrue(0 < calls[1][1] < calls[0][1])
        self.assertEqual(clock.sleeps, [5.0])

    def test_three_connections_and_visibility_chain_share_failure_count(self):
        clock = self.clocked()
        responses = iter([
            reply(), reply(1, "registered runtime request is missing"),
            reply(), reply(),
        ])
        calls = []

        def run(command, **kwargs):
            calls.append(kwargs["timeout"])
            return next(responses)

        with patch.object(ssh_transport.subprocess, "run", side_effect=run):
            budget = ssh_transport.SSHCallBudget.start(120)
            first = ssh_transport.run_ssh(COMMAND, timeout_seconds=120, budget=budget)
            second = ssh_transport.run_ssh(COMMAND, timeout_seconds=120, budget=budget)
            self.assertEqual(first.returncode, 1)
            self.assertEqual(second.returncode, 255)
            self.assertEqual(budget.pre_session_failures, 3)
            self.assertEqual(len(calls), 4)
            self.assertEqual(clock.sleeps, [5.0, 10.0])
            self.assertLess(calls[-1], calls[0])
            with self.assertRaisesRegex(subprocess.SubprocessError, "attempts exhausted"):
                ssh_transport.run_ssh(COMMAND, timeout_seconds=120, budget=budget)
            self.assertEqual(len(calls), 4)

    def test_single_invocation_stops_after_three_pre_session_failures(self):
        clock = self.clocked()
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            return reply()

        with patch.object(ssh_transport.subprocess, "run", side_effect=run):
            result = ssh_transport.run_ssh(COMMAND, timeout_seconds=120)
        self.assertEqual(result.returncode, 255)
        self.assertEqual(len(calls), 3)
        self.assertEqual(clock.sleeps, [5.0, 10.0])

    def test_original_deadline_and_backoff_cannot_reset_total_budget(self):
        clock = self.clocked()
        calls = []

        def run(command, **kwargs):
            calls.append(kwargs["timeout"])
            clock.now += 17
            return reply()

        with patch.object(ssh_transport.subprocess, "run", side_effect=run):
            result = ssh_transport.run_ssh(
                COMMAND, timeout_seconds=120, deadline_epoch=1020.0,
            )
        self.assertEqual(result.returncode, 255)
        self.assertEqual(calls, [20.0])
        self.assertEqual(clock.sleeps, [])

    def test_unproven_pre_session_failure_never_replays(self):
        clock = self.clocked()
        for result in [
            reply(stderr="Permission denied (publickey)."),
            reply(stderr="Host key verification failed."),
            reply(stderr=BANNER + "Traceback: remote command ran\n"),
            reply(stderr=BANNER, stdout="remote execution began"),
            reply(stderr=BANNER, stdout=" "),
            reply(stderr="Connection to 192.0.2.200 port 22 timed out"),
            reply(stderr="client_loop: send disconnect: Broken pipe"),
        ]:
            with self.subTest(stderr=result.stderr, stdout=result.stdout):
                calls = []

                def run(command, **kwargs):
                    calls.append(command)
                    return result

                with patch.object(ssh_transport.subprocess, "run", side_effect=run):
                    self.assertIs(ssh_transport.run_ssh(COMMAND, timeout_seconds=120), result)
                self.assertEqual(len(calls), 1)
        self.assertEqual(clock.sleeps, [])

    def test_command_timeout_is_not_replayed(self):
        self.clocked()
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        with patch.object(ssh_transport.subprocess, "run", side_effect=run):
            with self.assertRaises(subprocess.TimeoutExpired):
                ssh_transport.run_ssh(COMMAND, timeout_seconds=120)
        self.assertEqual(len(calls), 1)

    def test_wgs_marked_dispatch_reconnects_banner_before_session(self):
        module = importlib.import_module("bio_wgs")
        clock = self.clocked()
        commands = []
        responses = iter([
            reply(),
            reply(0, "", json.dumps({"schema": "cce.stage-execution.snapshot.v1"})),
        ])

        def ssh(command, **kwargs):
            commands.append(list(command))
            return next(responses)

        with patch.object(ssh_transport.subprocess, "run", side_effect=ssh):
            result = module._native_dispatch_stage(
                {"analysis_id": "SYNTHETIC", "attempt": 1}, "step5_download", IDENTITY,
            )
        self.assertEqual(result["schema"], "cce.stage-execution.snapshot.v1")
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0], commands[1])
        self.assertEqual(commands[0][-7:], SUBMIT_TAIL)
        self.assertEqual(clock.sleeps, [5.0])

    def test_marked_adapter_uses_shared_ssh_and_keeps_exact_identity(self):
        for pipeline in ("wgs", "gatk"):
            with self.subTest(pipeline=pipeline):
                module = importlib.import_module("bio_" + pipeline)
                calls = []

                def run(command, **kwargs):
                    calls.append((command, kwargs))
                    return reply(0, "", json.dumps({"schema": "cce.stage-execution.snapshot.v1"}))

                with patch.object(module, "run_ssh", side_effect=run):
                    result = module._native_dispatch_stage(
                        {"analysis_id": "SYNTHETIC", "attempt": 1},
                        "step5_download", IDENTITY,
                    )
                self.assertEqual(result["schema"], "cce.stage-execution.snapshot.v1")
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][1]["timeout_seconds"], 120)
                self.assertEqual(calls[0][0][-7:], SUBMIT_TAIL)

    def test_marked_adapter_timeout_remains_dispatch_uncertain(self):
        for pipeline in ("wgs", "gatk"):
            with self.subTest(pipeline=pipeline):
                module = importlib.import_module("bio_" + pipeline)
                sends = []

                def timeout(command, **kwargs):
                    sends.append(command)
                    raise subprocess.TimeoutExpired(command, kwargs["timeout_seconds"])

                with patch.object(module, "run_ssh", side_effect=timeout):
                    with self.assertRaises(DispatchUncertain):
                        module._native_dispatch_stage(
                            {"analysis_id": "SYNTHETIC", "attempt": 1},
                            "step5_download", IDENTITY,
                        )
                self.assertEqual(len(sends), 1)


if __name__ == "__main__":
    unittest.main()
