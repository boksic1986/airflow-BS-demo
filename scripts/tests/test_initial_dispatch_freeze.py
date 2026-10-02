"""Small synthetic checks for preserving an initial sender before relaunch."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cce_pipeline import stage_execution as native
from scripts import cce_paired_runtime as paired
from scripts import cce_stage_execution_adapter as adapter
from test_cce_stage_execution_adapter import _gate, _request, _terminal, _write_json


def _failed_initial(tmp_path, pipeline):
    gate, path = _gate(tmp_path, pipeline=pipeline)
    first = _request(1, pipeline=pipeline)
    first.update(stage='step2_master', execution_id='initial-step2')
    first['request_hash'] = paired._request_digest(first, pipeline)
    _write_json(path, first)
    adapter._freeze_registered_request(first, gate=gate, pipeline=pipeline)
    old_executor, old_ref, old_binding = adapter.executor_for_registered(
        first, gate=gate, pipeline=pipeline)
    _terminal(path, first, status='failed')
    adapter._publish_terminal(old_binding, gate=gate, pipeline=pipeline)
    identity = native.RuntimeIdentity(
        boot_id='00000000-0000-0000-0000-000000000001', pid=12345,
        starttime_ticks=999, process_group_id=12345)
    _write_json(old_binding.dispatch_path, {
        'schema':'cce.stage-execution.dispatch.v1', 'execution_ref':old_ref.to_dict(),
        'state':'finished', 'runtime_identity':identity.to_dict()})
    old_binding.dispatch_path.chmod(old_binding.file_mode)
    log = path.with_suffix('.worker.log')
    log.write_bytes(b'original synthetic pre-START traceback\n')
    log.chmod(0o600)
    old_raw = {name: p.read_bytes() for name, p in {
        'dispatch.json': old_binding.dispatch_path,
        'business-receipt.json': path.with_suffix('.status.json'),
        'stderr.log': log}.items()}
    second = dict(first, generation=2, execution_id='resume-step2',
                  resume_action_id='resume-initial-abort')
    second['request_hash'] = paired._request_digest(second, pipeline)
    _write_json(path, second)
    executor, ref, binding = adapter.executor_for_registered(
        second, gate=gate, pipeline=pipeline)
    adapter._freeze_registered_request(second, gate=gate, pipeline=pipeline)
    root = path.parent/'stage-execution-terminal'/'step2_master'/'initial-dispatch-generation-1'
    return gate, path, executor, ref, binding, root, old_raw, old_ref


@pytest.mark.parametrize('pipeline', ['wgs','gatk'])
def test_initial_sender_is_frozen_before_dispatch_overwrite(tmp_path, monkeypatch, pipeline):
    gate, path, executor, ref, binding, root, old_raw, old_ref = _failed_initial(tmp_path, pipeline)
    monkeypatch.setattr(native, '_group_quiescent', lambda identity: True)
    calls=[]
    def launch(command, **kwargs):
        assert root.is_dir(), 'old sender evidence was not frozen before launch'
        assert {name:(root/name).read_bytes() for name in old_raw} == old_raw
        calls.append(command)
        return SimpleNamespace(pid=54321)
    monkeypatch.setattr(native.subprocess, 'Popen', launch)
    monkeypatch.setattr(native, '_process_identity', lambda pid: native.RuntimeIdentity(
        boot_id='00000000-0000-0000-0000-000000000001',pid=pid,
        starttime_ticks=1000,process_group_id=pid))
    assert executor.submit(ref).state == 'accepted'
    assert len(calls)==1
    # Byte-preserving publication is idempotent for non-JSON stderr as well.
    adapter._publish_once(root/'stderr.log', old_raw['stderr.log'])
    adapter._publish_once(root/'stderr.log', old_raw['stderr.log'])
    assert json.loads((root/'dispatch.json').read_bytes())['execution_ref']==old_ref.to_dict()
    assert json.loads(binding.dispatch_path.read_bytes())['execution_ref']==ref.to_dict()
    # Relaunch appends to the original log; its frozen old bytes stay unchanged.
    with path.with_suffix('.worker.log').open('ab') as stream:
        stream.write(b'new generation output\n')
    assert (root/'stderr.log').read_bytes()==old_raw['stderr.log']


@pytest.mark.parametrize('pipeline', ['wgs','gatk'])
def test_initial_freeze_rejects_worker_lock_contention(tmp_path, monkeypatch, pipeline):
    gate, path, executor, ref, binding, root, old_raw, old_ref = _failed_initial(tmp_path, pipeline)
    monkeypatch.setattr(native, '_group_quiescent', lambda identity: True)
    with paired._exclusive(path.with_suffix('.worker.lock')):
        with pytest.raises(BlockingIOError):
            adapter._freeze_initial_dispatch(ref, gate=gate, pipeline=pipeline)
    assert not root.exists()
    assert binding.dispatch_path.read_bytes()==old_raw['dispatch.json']


def test_initial_freeze_rejects_conflicting_snapshot(tmp_path, monkeypatch):
    gate, path, executor, ref, binding, root, old_raw, old_ref = _failed_initial(tmp_path, 'wgs')
    monkeypatch.setattr(native, '_group_quiescent', lambda identity: True)
    root.mkdir(mode=0o700)
    (root/'dispatch.json').write_bytes(b'foreign previous evidence\n')
    (root/'dispatch.json').chmod(0o600)
    with pytest.raises(ValueError, match='conflicts'):
        adapter._freeze_initial_dispatch(ref, gate=gate, pipeline='wgs')
    assert (root/'dispatch.json').read_bytes()==b'foreign previous evidence\n'
    assert binding.dispatch_path.read_bytes()==old_raw['dispatch.json']
