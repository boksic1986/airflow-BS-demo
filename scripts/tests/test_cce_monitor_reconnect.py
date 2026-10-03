"""Real registered status writers and native query transport, no cluster/service."""
import json
import subprocess
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from cce_pipeline.assets import cce_batch_runtime as native
from scripts import cce_paired_runtime as paired, wgs_runtime_gate, gatk_runtime_gate
from scripts.cce_query_reconnect import QueryReconnectStopped

REAL_QUERY = native._recovery_query
REAL_LEGACY_QUERY = native._kubectl_json
CONFIG = {"kubernetes": {"kubectl_bin": "kubectl", "kubeconfig": "synthetic", "namespace": "synthetic"}}


def monitor_fixture(tmp_path, monkeypatch, pipeline):
    root = tmp_path / "requests"
    monkeypatch.setattr(wgs_runtime_gate, "REQUEST_ROOT", root)
    monkeypatch.setattr(wgs_runtime_gate, "RUNTIME_RUN_ROOT", str(tmp_path / 'runs'))
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(root))
    gate = wgs_runtime_gate if pipeline == "wgs" else gatk_runtime_gate
    payload = dict(analysis_id=f"{pipeline.upper()}_20260925_000000_AAAAAA", attempt=1,
        stage="step3_monitor", orchestration_contract_version=2, execution_id="monitor-1",
        generation=1, cce_recovery_deadline=datetime.fromtimestamp(5000, timezone.utc).isoformat())
    path = gate._request_path(payload["analysis_id"], 1, "step3_monitor")
    path.parent.mkdir(parents=True, exist_ok=True)
    if pipeline == "wgs":
        payload['control_workdir'] = str(tmp_path / 'runs' / payload['analysis_id'] / 'attempt-1')
        (tmp_path / 'runs' / payload['analysis_id'] / 'attempt-1').mkdir(parents=True)
    payload["request_hash"] = paired._request_digest(payload, pipeline)
    path.write_text(json.dumps(payload))
    def write(status, **details):
        if pipeline == "wgs": gate._write_status(payload, status, "monitor", **details)
        else: gate._write_status(path, payload, status, "monitor", **details)
    write("running", monitoring_health="healthy", completed_units=4, total_units=100, progress_percent=4)
    clock = [1000.0]
    def owner():
        assert hasattr(paired, "_monitor_query_owner"), "registered monitor has no query retry owner"
        value = paired._monitor_query_owner(payload, gate, pipeline, native,
            observation=lambda: ({'master_state': 'RUNNING', 'completed': 4, 'total': 100,
                'percent': 4}, {'master_job': 'cce-master-synthetic', 'namespace': 'synthetic',
                               'run_label': 'cce-run-aaaaaaaaaaaaaaaa'}))
        value.now = lambda: clock[0]
        value.sleep = lambda seconds: clock.__setitem__(0, clock[0] + seconds)
        return value
    def read(): return json.loads(path.with_suffix(".status.json").read_bytes())
    return SimpleNamespace(payload=payload, gate=gate, path=path, owner=owner, read=read,
        write=write, clock=clock, root=root)


@pytest.mark.parametrize("pipeline", ["wgs", "gatk"])
def test_native_reads_retry_with_durable_status_and_outer_failure_keeps_marker(tmp_path, monkeypatch, pipeline):
    case = monitor_fixture(tmp_path, monkeypatch, pipeline)
    owner = case.owner()
    config = {**CONFIG, "_monitor_query_runner": owner.run}
    sent = []
    def transport(command, **kwargs):
        assert command[5] == "get"  # no CREATE, START, exec or logs can be repeated
        sent.append(kwargs["timeout"])
        if len(sent) > 1:
            assert case.read()["monitor_reconnect"]["retries_used"] == len(sent) - 1
        return subprocess.CompletedProcess(command, 1, b"", b"connection reset by peer")
    monkeypatch.setattr(native, "_run", transport)
    with pytest.raises(QueryReconnectStopped):
        REAL_LEGACY_QUERY(config, "job", "master")
    assert len(sent) == 7 and case.read()["monitor_reconnect"]["phase"] == "exhausted"
    assert case.read()["completed_units"] == 4
    case.write("failed")  # Existing generic outer worker failure handler.
    saved = case.read()
    assert saved["status"] == "failed" and saved["monitoring_health"] == "degraded"
    assert saved["monitor_reconnect"]["phase"] == "exhausted"
    assert saved["monitor_reconnect"]["scope"]["request_hash"] == case.payload["request_hash"]
    with pytest.raises((QueryReconnectStopped, RuntimeError)):
        case.owner().run(lambda timeout: pytest.fail("terminal monitor replay issued a query"))


@pytest.mark.parametrize("pipeline", ["wgs", "gatk"])
def test_reconnect_success_clears_only_after_complete_observation(tmp_path, monkeypatch, pipeline):
    case = monitor_fixture(tmp_path, monkeypatch, pipeline)
    owner = case.owner()
    config = {**CONFIG, "_monitor_query_runner": owner.run}
    values = iter([subprocess.CompletedProcess([], 1, b"", b"Error (ServiceUnavailable)"),
                   subprocess.CompletedProcess([], 0, b"", b"")])
    monkeypatch.setattr(native, "_run", lambda *a, **kw: next(values))
    assert REAL_QUERY(config, "job", "master") is None
    assert case.read()["monitor_reconnect"]["phase"] == "observing"
    owner.confirmed()
    case.write("running", monitoring_health="healthy")
    assert case.read()["monitor_reconnect"]["phase"] == "healthy"
    assert case.read()["monitor_reconnect"]["last_success_at"] == 1030


@pytest.mark.parametrize("pipeline", ["wgs", "gatk"])
def test_changed_registration_stops_before_retry(tmp_path, monkeypatch, pipeline):
    case = monitor_fixture(tmp_path, monkeypatch, pipeline)
    owner = case.owner()
    def change_during_wait(seconds):
        case.clock[0] += seconds
        current = dict(case.payload, generation=2)
        case.path.write_text(json.dumps(current))
    owner.sleep = change_during_wait
    count = [0]
    def query(timeout):
        count[0] += 1
        raise native.RecoveryQueryError("TRANSPORT")
    with pytest.raises(RuntimeError, match="registered"):
        owner.run(query)
    assert count[0] == 1


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
@pytest.mark.parametrize('damage', ['missing', 'foreign'])
def test_missing_or_foreign_status_does_not_reset_query_budget(tmp_path, monkeypatch, pipeline, damage):
    case = monitor_fixture(tmp_path, monkeypatch, pipeline)
    path = case.path.with_suffix('.status.json')
    if damage == 'missing':
        path.unlink()
    else:
        value = case.read(); value['generation'] += 1
        path.write_text(json.dumps(value))
    sent = []
    with pytest.raises((OSError, RuntimeError)):
        case.owner().run(lambda timeout: sent.append(timeout))
    assert not sent


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
def test_unconfirmed_selected_identity_is_blocked_not_retried(tmp_path, monkeypatch, pipeline):
    case = monitor_fixture(tmp_path, monkeypatch, pipeline)
    owner = case.owner()
    monkeypatch.setattr(paired, 'load_runtime', lambda: native)
    monkeypatch.setattr(paired, '_monitor_query_owner', lambda *a, **kw: owner)
    calls = []
    def invalid_observation(*a, **kw):
        calls.append(1)
        raise RuntimeError('selected Master directory owner changed or missing')
    monkeypatch.setattr(paired, '_selected_registered', invalid_observation)
    with pytest.raises(RuntimeError):
        paired.monitor_registered(case.payload, binding={}, gate=case.gate, pipeline=pipeline)
    case.write('failed')
    assert case.read()['monitor_reconnect']['phase'] == 'blocked'
    assert case.read()['monitor_reconnect']['retries_used'] == 0 and len(calls) == 1


def confirmed_monitor_result(case, monkeypatch, master):
    """Only the external selected-Master read is replaced; persistence is real."""
    monkeypatch.setattr(paired, 'load_runtime', lambda: native)
    def selected(payload, *, query_owner, **kwargs):
        query_owner.now = lambda: case.clock[0]
        query_owner.sleep = lambda seconds: case.clock.__setitem__(0, case.clock[0] + seconds)
        query_owner.run(lambda timeout: {'kind': 'Job'})
        return master
    monkeypatch.setattr(paired, '_selected_registered', selected)
    return paired.monitor_registered(case.payload,
        binding={'master_job': 'cce-master-synthetic', 'namespace': 'synthetic',
                 'run_label': 'cce-run-aaaaaaaaaaaaaaaa'}, gate=case.gate,
        pipeline=case.payload['analysis_id'].split('_', 1)[0].lower())


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
def test_healthy_confirmation_atomically_publishes_the_current_master_read(tmp_path, monkeypatch, pipeline):
    case = monitor_fixture(tmp_path, monkeypatch, pipeline)
    case.write('running', monitoring_health='degraded', monitoring_error='rule evidence unavailable',
        master={'master_state': 'RUNNING', 'completed': 6, 'total': 333, 'percent': 1.8})
    fresh = {'master_state': 'RUNNING', 'completed': 7, 'total': 333, 'percent': 2.1,
        'current_rule': 'synthetic-rule', 'current_rules': ['synthetic-rule'],
        'last_completed_rule': 'previous-rule', 'normal': True, 'message': 'workflow running',
        'master_uid': 'synthetic-master-uid', 'master_resource_version': '123'}
    writes = []
    atomic = case.gate._atomic_json
    def capture(path, value):
        writes.append(json.loads(json.dumps(value)))
        return atomic(path, value)
    monkeypatch.setattr(case.gate, '_atomic_json', capture)
    assert confirmed_monitor_result(case, monkeypatch, fresh) == fresh
    saved = case.read()
    assert saved['monitor_reconnect']['phase'] == 'healthy'
    assert saved['monitoring_error'] == 'rule evidence unavailable'
    assert saved['monitoring_health'] == 'degraded'  # Query recovery cannot repair the evidence bridge.
    healthy = [v for v in writes if v.get('monitor_reconnect', {}).get('phase') == 'healthy']
    assert healthy
    if pipeline == 'wgs':
        assert all(v['master'] == fresh for v in healthy)
        assert saved['master_job'] == 'cce-master-synthetic'
        assert saved['namespace'] == 'synthetic' and saved['run_label'] == 'cce-run-aaaaaaaaaaaaaaaa'
    else:
        assert all(v['completed_units'] == 7 and v['total_units'] == 333 for v in healthy)
        assert saved['progress_percent'] == 2 and saved['unit'] == 'rules'
        assert saved['current_item'] == 'synthetic-rule'


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
def test_unconfirmed_query_keeps_snapshot_but_does_not_claim_new_business(tmp_path, monkeypatch, pipeline):
    case = monitor_fixture(tmp_path, monkeypatch, pipeline)
    master = {'master_state': 'RUNNING', 'completed': 6, 'total': 333, 'percent': 1.8}
    case.write('running', master=master, master_job='cce-master-synthetic', namespace='synthetic',
        run_label='wgs-synthetic', monitoring_error='rule evidence unavailable')
    with pytest.raises(QueryReconnectStopped):
        case.owner().unconfirmed()
    saved = case.read()
    assert saved['monitor_reconnect']['phase'] == 'blocked'
    assert saved['monitoring_health'] == 'degraded'
    assert saved['master'] == master
    assert saved['master_job'] == 'cce-master-synthetic'
    assert saved['monitoring_error'] == 'rule evidence unavailable'


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
def test_complete_read_without_rule_counts_does_not_refresh_previous_numbers(tmp_path, monkeypatch, pipeline):
    case = monitor_fixture(tmp_path, monkeypatch, pipeline)
    confirmed_monitor_result(case, monkeypatch, {'master_state': 'RUNNING', 'message': 'counts unavailable'})
    saved = case.read()
    if pipeline == 'wgs':
        assert saved['master'] == {'master_state': 'RUNNING', 'message': 'counts unavailable'}
    for key in ('completed_units', 'total_units', 'progress_percent'):
        assert saved.get(key) is None
