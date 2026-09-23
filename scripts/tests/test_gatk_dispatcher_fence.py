"""Restricted GATK dispatch must not double-launch or outlive its generation."""
import fcntl
import json
import os
import sys
from types import SimpleNamespace

import pytest

from test_gatk_runtime_gate import load_gate


@pytest.fixture
def dispatch_case(tmp_path, monkeypatch):
    gate = load_gate()
    monkeypatch.setenv('GATK_RUNTIME_REQUEST_ROOT', str(tmp_path))
    aid = 'GATK_20260924_000000_AAAAAA'
    path = tmp_path / aid / 'attempt-1/step2_master.request.json'
    path.parent.mkdir(parents=True)
    payload = dict(analysis_id=aid, attempt=1, stage='step2_master', generation=1,
        execution_id=aid+'-a1-step2_master-g1', request_hash='a'*64,
        orchestration_contract_version=2)
    path.write_text(json.dumps(payload))
    return gate, path, payload


def test_start_records_one_launch_and_rejects_live_previous_generation(dispatch_case, monkeypatch):
    gate, path, payload = dispatch_case
    launches = []
    def spawn(*args, **kwargs):
        launches.append(args[0])
        return SimpleNamespace(pid=os.getpid())
    monkeypatch.setattr(gate.subprocess, 'Popen', spawn)
    first = gate.start(payload['analysis_id'], 1, 'step2_master', 1)
    again = gate.start(payload['analysis_id'], 1, 'step2_master', 1)
    assert first['status'] == again['status'] == 'accepted'
    assert len(launches) == 1
    path.write_text(json.dumps({**payload, 'generation':2,
        'execution_id':payload['analysis_id']+'-a1-step2_master-g2', 'request_hash':'b'*64}))
    with pytest.raises(RuntimeError, match='dispatcher'):
        gate.start(payload['analysis_id'], 1, 'step2_master', 2)
    assert len(launches) == 1


def test_worker_lock_prevents_second_executor_before_any_stage_effect(dispatch_case, monkeypatch):
    gate, path, payload = dispatch_case
    effects = []
    monkeypatch.setattr(gate, '_step', lambda *args: effects.append('side effect'))
    with path.with_suffix('.worker.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match='dispatcher'):
            gate._execute(payload['analysis_id'], 1, 'step2_master', 1)
    assert effects == []
    assert not path.with_suffix('.status.json').exists()


def test_completed_worker_is_not_executed_twice(dispatch_case, monkeypatch):
    gate, path, payload = dispatch_case
    output = path.parent / 'effect'
    monkeypatch.setattr(gate, '_step', lambda *args: [sys.executable, '-c',
        f"from pathlib import Path; Path({str(output)!r}).open('a').write('once\\n')"])
    gate._execute(payload['analysis_id'], 1, 'step2_master', 1)
    gate._execute(payload['analysis_id'], 1, 'step2_master', 1)
    assert output.read_text() == 'once\n'
    assert json.loads(path.with_suffix('.status.json').read_text())['status'] == 'success'


def test_ambiguous_spawn_does_not_launch_again(dispatch_case, monkeypatch):
    gate, path, payload = dispatch_case
    launches = []
    def spawn(*args, **kwargs):
        launches.append(args[0])
        raise OSError('synthetic uncertain spawn')
    monkeypatch.setattr(gate.subprocess, 'Popen', spawn)
    with pytest.raises(OSError):
        gate.start(payload['analysis_id'], 1, 'step2_master', 1)
    with pytest.raises(RuntimeError, match='dispatcher'):
        gate.start(payload['analysis_id'], 1, 'step2_master', 1)
    assert len(launches) == 1


def test_superseded_worker_cannot_publish_a_late_terminal(dispatch_case, monkeypatch):
    gate, path, payload = dispatch_case
    newer = {**payload, 'generation':2, 'request_hash':'b'*64,
             'execution_id':payload['analysis_id']+'-a1-step2_master-g2'}
    def command(*args):
        path.write_text(json.dumps(newer))
        return [sys.executable, '-c', 'pass']
    monkeypatch.setattr(gate, '_step', command)
    with pytest.raises(RuntimeError, match='superseded'):
        gate._execute(payload['analysis_id'], 1, 'step2_master', 1)
    status = json.loads(path.with_suffix('.status.json').read_text())
    assert status['status'] == 'running'  # No old success/failure replaces current evidence.


def test_spawned_worker_waits_for_launch_record_and_next_generation_can_follow(dispatch_case, monkeypatch):
    gate, path, payload = dispatch_case
    output = path.parent / 'effect'
    monkeypatch.setattr(gate, '_step', lambda *args: [sys.executable, '-c',
        f"from pathlib import Path; Path({str(output)!r}).open('a').write('once\\n')"])
    original_spawn = gate.subprocess.Popen
    children = []
    def spawn(*args, **kwargs):
        pid = os.fork()
        if pid == 0:
            # Match the real Popen(close_fds=True), including the parent's lock.
            os.closerange(3, 1024)
            gate.subprocess.Popen = original_spawn
            try:
                gate._execute(payload['analysis_id'], 1, 'step2_master', int(args[0][-1]))
            except BaseException:
                os._exit(1)
            os._exit(0)
        children.append(pid)
        return SimpleNamespace(pid=pid)
    monkeypatch.setattr(gate.subprocess, 'Popen', spawn)
    for generation in (1, 2):
        path.write_text(json.dumps({**payload, 'generation':generation,
            'execution_id':payload['analysis_id']+f'-a1-step2_master-g{generation}',
            'request_hash':str(generation)*64}))
        assert gate.start(payload['analysis_id'], 1, 'step2_master', generation)['status'] == 'accepted'
        assert os.waitpid(children[-1], 0)[1] == 0
    assert output.read_text() == 'once\nonce\n'


def test_legacy_status_without_full_identity_does_not_authorize_launch(dispatch_case):
    gate, path, payload = dispatch_case
    path.with_suffix('.status.json').write_text(json.dumps({'status':'success', 'generation':1}))
    with pytest.raises(RuntimeError, match='legacy execution'):
        gate.start(payload['analysis_id'], 1, 'step2_master', 1)
