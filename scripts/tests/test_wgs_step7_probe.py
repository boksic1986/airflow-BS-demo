import hashlib
import json
import os
import fcntl

import pytest
from test_wgs_runtime_gate import load_gate


@pytest.fixture
def probe_env(tmp_path, monkeypatch):
    gate = load_gate()
    monkeypatch.setattr(gate, 'REQUEST_ROOT', tmp_path)
    payload = {'schema_version': 'wgs-runtime.request.v4',
        'analysis_id': 'WGS_20260922_010203_A1B2C3', 'attempt': 1,
        'stage': 'step7_cleanup', 'maintenance_action_id': 'step7-sfs-123456abcdef', 'step7_generation': 1}
    path = gate._request_path(payload['analysis_id'], 1, 'step7_cleanup')
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload))
    def probe():
        return gate.step7_probe(payload['analysis_id'], 1, payload['maintenance_action_id'], 1)
    return gate, payload, path, probe


def test_not_started_probe_does_not_create_files(probe_env):
    _, _, path, probe = probe_env
    before = list(path.parent.iterdir())
    assert probe()['status'] == 'not_started'
    assert list(path.parent.iterdir()) == before


@pytest.mark.parametrize('status', ['success', 'failed'])
def test_terminal_receipt(probe_env, status):
    gate, payload, _, probe = probe_env
    gate._sidecar_path(payload, '.status.json').write_text(json.dumps({**payload, 'schema_version': 'wgs-runtime.stage-status.v1', 'status': status}))
    assert probe()['status'] == status


def test_live_process_is_reattached(probe_env):
    gate, payload, path, probe = probe_env
    gate._sidecar_path(payload, '.worker.json').write_text(json.dumps({
        'pid': os.getpid(), 'boot_id': gate._boot_id(),
        'process_start_time': gate._process_start_time(os.getpid()),
        'request_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))
    assert probe()['status'] == 'running'


def test_launch_in_flight_without_identity_is_unknown(probe_env):
    gate, payload, _, probe = probe_env
    with gate._sidecar_path(payload, '.launch.lock').open('w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        assert probe()['status'] == 'unknown'


def test_wrong_request_or_receipt_identity_is_rejected(probe_env):
    gate, payload, _, probe = probe_env
    with pytest.raises(ValueError, match='identity'):
        gate.step7_probe(payload['analysis_id'], 1, 'step7-sfs-abcdef123456', 1)
    gate._sidecar_path(payload, '.status.json').write_text(json.dumps({**payload, 'schema_version': 'wgs-runtime.stage-status.v1', 'attempt': 2, 'status': 'success'}))
    with pytest.raises(ValueError, match='identity'):
        probe()


def test_dead_process_without_receipt_is_unknown(probe_env):
    gate, payload, _, probe = probe_env
    gate._sidecar_path(payload, '.worker.json').write_text(json.dumps({
        'pid': 999999999, 'boot_id': gate._boot_id(), 'process_start_time': '0'}))
    assert probe()['status'] == 'unknown'


def test_orphan_cleanup_group_blocks_retry(probe_env, monkeypatch):
    gate, payload, _, probe = probe_env
    gate._sidecar_path(payload, '.worker.json').write_text(json.dumps({
        'pid': 999999999, 'boot_id': gate._boot_id(), 'process_start_time': '0'}))
    monkeypatch.setattr(gate.os, 'killpg', lambda *_: None)
    gate._sidecar_path(payload, '.status.json').write_text(json.dumps({**payload, 'status': 'failed'}))
    assert probe()['status'] == 'unknown'
