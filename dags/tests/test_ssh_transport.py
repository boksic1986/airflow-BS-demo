"""UE-05 SSH connection delta; all commands and replies are synthetic."""

import importlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

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


def clocked(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(
        ssh_transport, "time",
        SimpleNamespace(monotonic=clock.monotonic, time=clock.time, sleep=clock.sleep),
    )
    return clock


def reply(code=255, stderr=BANNER, stdout=""):
    return subprocess.CompletedProcess(COMMAND, code, stdout, stderr)


def test_banner_reconnect_preserves_exact_command_and_single_budget(monkeypatch):
    clock = clocked(monkeypatch)
    calls = []
    responses = iter([reply(), reply(0, "", '{"state":"accepted"}')])

    def run(command, **kwargs):
        calls.append((list(command), kwargs["timeout"]))
        clock.now += 1
        return next(responses)

    monkeypatch.setattr(ssh_transport.subprocess, "run", run)
    result = ssh_transport.run_ssh(COMMAND, timeout_seconds=120)
    assert result.returncode == 0
    assert len(calls) == 2 and calls[0][0] == calls[1][0]
    assert calls[0][0][-len(COMMAND) + 1:] == COMMAND[1:]
    assert calls[0][0][:5] == [
        "ssh", "-o", "ConnectTimeout=30", "-o", "ConnectionAttempts=1",
    ]
    assert calls[0][1] == 120 and 0 < calls[1][1] < calls[0][1]
    assert clock.sleeps == [5.0]


def test_three_connections_and_visibility_chain_share_failure_count(monkeypatch):
    clock = clocked(monkeypatch)
    responses = iter([
        reply(), reply(1, "registered runtime request is missing"),
        reply(), reply(),
    ])
    calls = []

    def run(command, **kwargs):
        calls.append(kwargs["timeout"])
        return next(responses)

    monkeypatch.setattr(ssh_transport.subprocess, "run", run)
    budget = ssh_transport.SSHCallBudget.start(120)
    first = ssh_transport.run_ssh(COMMAND, timeout_seconds=120, budget=budget)
    second = ssh_transport.run_ssh(COMMAND, timeout_seconds=120, budget=budget)
    assert first.returncode == 1 and second.returncode == 255
    assert budget.pre_session_failures == 3 and len(calls) == 4
    assert clock.sleeps == [5.0, 10.0]
    assert calls[-1] < calls[0]
    with pytest.raises(subprocess.SubprocessError, match="attempts exhausted"):
        ssh_transport.run_ssh(COMMAND, timeout_seconds=120, budget=budget)
    assert len(calls) == 4


def test_single_invocation_stops_after_three_pre_session_failures(monkeypatch):
    clock = clocked(monkeypatch)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return reply()

    monkeypatch.setattr(ssh_transport.subprocess, "run", run)
    assert ssh_transport.run_ssh(COMMAND, timeout_seconds=120).returncode == 255
    assert len(calls) == 3 and clock.sleeps == [5.0, 10.0]


def test_original_deadline_and_backoff_cannot_reset_total_budget(monkeypatch):
    clock = clocked(monkeypatch)
    calls = []

    def run(command, **kwargs):
        calls.append(kwargs["timeout"])
        clock.now += 17
        return reply()

    monkeypatch.setattr(ssh_transport.subprocess, "run", run)
    result = ssh_transport.run_ssh(
        COMMAND, timeout_seconds=120, deadline_epoch=1020.0,
    )
    assert result.returncode == 255
    assert calls == [20.0] and clock.sleeps == []


@pytest.mark.parametrize("result", [
    reply(stderr="Permission denied (publickey)."),
    reply(stderr="Host key verification failed."),
    reply(stderr=BANNER + "Traceback: remote command ran\n"),
    reply(stderr=BANNER, stdout="remote execution began"),
    reply(stderr=BANNER, stdout=" "),
    reply(stderr="Connection to 192.0.2.200 port 22 timed out"),
    reply(stderr="client_loop: send disconnect: Broken pipe"),
])
def test_unproven_pre_session_failure_never_replays(monkeypatch, result):
    clocked(monkeypatch)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return result

    monkeypatch.setattr(ssh_transport.subprocess, "run", run)
    assert ssh_transport.run_ssh(COMMAND, timeout_seconds=120) is result
    assert len(calls) == 1


def test_command_timeout_is_not_replayed(monkeypatch):
    clocked(monkeypatch)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(ssh_transport.subprocess, "run", run)
    with pytest.raises(subprocess.TimeoutExpired):
        ssh_transport.run_ssh(COMMAND, timeout_seconds=120)
    assert len(calls) == 1


@pytest.mark.parametrize("pipeline", ["wgs", "gatk"])
def test_marked_adapter_uses_shared_ssh_and_keeps_exact_identity(monkeypatch, pipeline):
    module = importlib.import_module("bio_" + pipeline)
    identity = {
        "analysis_id": "SYNTHETIC", "attempt": 1, "stage": "step5_download",
        "execution_id": "execution-1", "stage_generation": 2,
        "request_hash": "a" * 64,
    }
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return reply(0, "", json.dumps({"schema": "cce.stage-execution.snapshot.v1"}))

    monkeypatch.setattr(module, "run_ssh", run)
    result = module._native_dispatch_stage(
        {"analysis_id": "SYNTHETIC", "attempt": 1}, "step5_download", identity,
    )
    assert result["schema"] == "cce.stage-execution.snapshot.v1"
    assert len(calls) == 1 and calls[0][1]["timeout_seconds"] == 120
    assert calls[0][0][-7:] == [
        "--native-submit", "SYNTHETIC", "1", "step5_download",
        "execution-1", "2", "a" * 64,
    ]


@pytest.mark.parametrize("pipeline", ["wgs", "gatk"])
def test_marked_adapter_timeout_remains_dispatch_uncertain(monkeypatch, pipeline):
    module = importlib.import_module("bio_" + pipeline)
    identity = {
        "analysis_id": "SYNTHETIC", "attempt": 1, "stage": "step5_download",
        "execution_id": "execution-1", "stage_generation": 2,
        "request_hash": "a" * 64,
    }
    sends = []

    def timeout(command, **kwargs):
        sends.append(command)
        raise subprocess.TimeoutExpired(command, kwargs["timeout_seconds"])

    monkeypatch.setattr(module, "run_ssh", timeout)
    with pytest.raises(DispatchUncertain):
        module._native_dispatch_stage(
            {"analysis_id": "SYNTHETIC", "attempt": 1}, "step5_download", identity,
        )
    assert len(sends) == 1
