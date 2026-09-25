"""Bounded read-only retry owner; fake clock, real strict native GET and JSON state."""
import json
import subprocess

import pytest

from cce_pipeline.assets import cce_batch_runtime as native
from scripts.cce_query_reconnect import QueryReconnect, QueryReconnectStopped


SCOPE = dict(pipeline="wgs", analysis_id="synthetic", attempt=1, stage="step3_monitor",
             execution_id="execution-1", generation=1, request_hash="a" * 64)
CONFIG = {"kubernetes": {"kubectl_bin": "kubectl", "kubeconfig": "synthetic", "namespace": "synthetic"}}


@pytest.fixture
def owner(tmp_path):
    clock = [1000.0]
    waits = []
    path = tmp_path / "stage.status.json"
    def read():
        return json.loads(path.read_text())["monitor_reconnect"] if path.exists() else None
    def save(state):
        path.write_text(json.dumps({"monitor_reconnect": state}))
    def sleep(seconds):
        waits.append(seconds)
        clock[0] += seconds
    def new(**overrides):
        return QueryReconnect(scope=SCOPE, deadline=5000, load=read, save=save,
            error_type=native.RecoveryQueryError, now=lambda: clock[0], sleep=sleep, **overrides)
    return new, read, save, clock, waits


def test_real_get_exhausts_six_retries_and_restart_cannot_reset(owner, monkeypatch):
    new, read, _, _, waits = owner
    calls = []
    def transport(*args, **kwargs):
        calls.append(kwargs["timeout"])
        return subprocess.CompletedProcess([], 1, b"", b"connection reset by peer")
    monkeypatch.setattr(native, "_run", transport)
    query = lambda timeout: native._recovery_query(CONFIG, "job", "master", timeout=timeout)
    with pytest.raises(QueryReconnectStopped, match="exhausted"):
        new().run(query)
    assert calls == [30] * 7
    assert waits == [30, 60, 120, 240, 300, 300]
    assert read()["retries_used"] == 6
    assert read()["first_error_at"] == 1000
    with pytest.raises(QueryReconnectStopped):
        new().run(query)
    assert len(calls) == 7


def test_authoritative_monitor_confirmation_alone_clears_outage(owner):
    new, read, _, clock, waits = owner
    count = [0]
    def query(timeout):
        count[0] += 1
        if count[0] == 1:
            raise native.RecoveryQueryError("SERVICE")
        return {"kind": "Job"}
    client = new()
    assert client.run(query) == {"kind": "Job"}
    assert read()["phase"] == "observing" and read()["retries_used"] == 1
    assert new().run(lambda timeout: {"kind": "ConfigMap"})
    assert read()["retries_used"] == 1  # A partial read cannot reset the outage budget.
    client.confirmed()
    assert read()["phase"] == "healthy" and read()["last_success_at"] == clock[0]
    count[0] = 0
    assert new().run(query)
    assert read()["retries_used"] == 1 and waits == [30, 30]


@pytest.mark.parametrize("code", ["FORBIDDEN", "AUTHENTICATION", "INVALID_QUERY", "INVALID_RESPONSE", "QUERY_FAILED", "LOCAL_COMMAND"])
def test_control_or_unknown_failure_is_never_retried(owner, code):
    new, read, _, _, waits = owner
    calls = []
    def query(timeout):
        calls.append(timeout)
        raise native.RecoveryQueryError(code)
    with pytest.raises(QueryReconnectStopped, match="blocked"):
        new().run(query)
    assert len(calls) == 1 and not waits
    assert read()["reason"] == code and read()["phase"] == "blocked"


def test_crash_after_retry_reservation_consumes_slot(owner):
    new, read, _, clock, waits = owner
    calls = [0]
    def query(timeout):
        calls[0] += 1
        if calls[0] == 1:
            raise native.RecoveryQueryError("TRANSPORT")
        raise SystemExit("process lost")
    with pytest.raises(SystemExit):
        new().run(query)
    assert read()["phase"] == "querying" and read()["retries_used"] == 1
    assert new().run(lambda timeout: "observed") == "observed"
    assert read()["retries_used"] == 2 and waits == [30, 60]


def test_deadline_caps_wait_and_each_request_without_reset(owner):
    new, read, _, clock, waits = owner
    clock[0] = 4996
    calls = []
    def query(timeout):
        calls.append(timeout)
        raise native.RecoveryQueryError("TRANSPORT")
    with pytest.raises(QueryReconnectStopped, match="deadline"):
        new().run(query)
    assert calls == [4] and waits == [4]
    assert read()["phase"] == "exhausted" and read()["reason"] == "deadline"


def test_failed_persistence_or_foreign_state_prevents_query(owner):
    new, read, save, _, _ = owner
    def fail(timeout):
        raise native.RecoveryQueryError("TRANSPORT")
    with pytest.raises(QueryReconnectStopped):
        new().run(fail)
    state = read()
    state["scope"]["generation"] = 2
    save(state)
    with pytest.raises(ValueError, match="reconnect state"):
        new().run(lambda timeout: pytest.fail("foreign state authorized query"))
    save(None)
    client = new()
    client.save = lambda state: (_ for _ in ()).throw(OSError("disk full"))
    with pytest.raises(OSError, match="disk full"):
        client.run(fail)


def test_untyped_exception_is_not_retried(owner):
    new, read, _, _, waits = owner
    def query(timeout):
        raise RuntimeError("identity changed")
    with pytest.raises(RuntimeError, match="identity changed"):
        new().run(query)
    assert read() is None and not waits


@pytest.mark.parametrize("change", [
    {"phase": "waiting", "retries_used": 6, "next_retry_at": 1000},
    {"phase": "healthy", "retries_used": 2},
    {"scope": {**SCOPE, "attempt": True}},
    {"deadline": 6000},
])
def test_corrupt_or_reset_budget_cannot_authorize_a_query(owner, change):
    new, read, save, _, _ = owner
    def unavailable(timeout):
        raise native.RecoveryQueryError("TRANSPORT")
    with pytest.raises(QueryReconnectStopped):
        new().run(unavailable)
    state = read()
    state.update(change)
    save(state)
    with pytest.raises(ValueError, match="reconnect state"):
        new().run(lambda timeout: pytest.fail("corrupt budget authorized query"))


def test_response_after_deadline_cannot_confirm_success(owner):
    new, read, _, clock, _ = owner
    def late(timeout):
        clock[0] = 5001
        return {"kind": "Job"}
    client = new()
    with pytest.raises(QueryReconnectStopped, match="deadline"):
        client.run(late)
    with pytest.raises(ValueError, match="authoritative"):
        client.confirmed()
    assert read()["last_success_at"] is None
