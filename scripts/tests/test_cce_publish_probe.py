"""Step4 observes the original dispatcher, never infers absence from SSH failure."""
import hashlib
import json
import os
import fcntl
from types import SimpleNamespace

import pytest
from scripts import cce_paired_runtime as paired, wgs_runtime_gate, gatk_runtime_gate


@pytest.fixture(params=['wgs', 'gatk'])
def publish_case(request, tmp_path, monkeypatch):
    pipeline = request.param
    gate = wgs_runtime_gate if pipeline == 'wgs' else gatk_runtime_gate
    monkeypatch.setattr(wgs_runtime_gate, 'REQUEST_ROOT', tmp_path)
    monkeypatch.setenv('GATK_RUNTIME_REQUEST_ROOT', str(tmp_path))
    monkeypatch.setenv('WGS_EXECUTION_ENABLED', 'true')
    monkeypatch.setenv('WGS_RUNTIME_ADAPTER_ENABLED', 'true')
    aid = pipeline.upper()+'_20260925_000000_AAAAAA'
    path = gate._request_path(aid, 1, 'step4_publish')
    path.parent.mkdir(parents=True)
    payload = dict(schema_version='wgs-runtime.request.v4', analysis_id=aid, attempt=1,
        stage='step4_publish', generation=1, execution_id=aid+'-a1-step4_publish-g1',
        orchestration_contract_version=2, publish_dispatch_version=1,
        control_workdir=str(path.parent))
    payload['request_hash'] = paired._request_digest(payload, pipeline)
    path.write_text(json.dumps(payload))
    worker = path.with_suffix('.worker.json' if pipeline == 'wgs' else '.worker.state.json')
    return pipeline, gate, path, payload, worker


def write_state(case, status=None, *, live=False):
    pipeline, gate, path, payload, worker = case
    if pipeline == 'wgs':
        state = dict(payload, pid=os.getpid(), boot_id=gate._boot_id(),
            process_start_time=gate._process_start_time(os.getpid()),
            request_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        if not live: state['boot_id'] = 'old-boot'
    else:
        process = gate._process_identity(os.getpid())
        if not live: process['boot_id'] = 'old-boot'
        state = dict(payload, schema_version='gatk-runtime.dispatcher.v1',
            state='running' if live else 'finished', process=process)
    worker.write_text(json.dumps(state))
    if status:
        receipt = dict(payload, status=status)
        if pipeline == 'gatk':
            receipt['receipt_hash'] = hashlib.sha256(json.dumps(receipt,
                sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        path.with_suffix('.status.json').write_text(json.dumps(receipt))


def observe(case):
    from scripts.cce_publish_recovery import observe_publish
    pipeline, gate, _, payload, _ = case
    return observe_publish(payload, gate=gate, pipeline=pipeline, nonce='a'*32)


@pytest.mark.parametrize('state,want',[
    ('empty','not_started'), ('live','running'), ('success','success'),
    ('failed','failed'), ('dead','uncertain'), ('launching','uncertain')])
def test_original_publish_operation_is_reconciled_without_launch(publish_case, state, want, monkeypatch):
    _, gate, path, payload, _ = publish_case
    if state in {'live','success','failed','dead'}:
        write_state(publish_case, status=state if state in {'success','failed'} else None, live=state=='live')
    elif state == 'launching':
        path.with_suffix('.status.json').write_text(json.dumps(dict(payload,status='accepted')))
    before = {p.name:p.read_bytes() for p in path.parent.glob('*.json')}
    monkeypatch.setattr(gate.subprocess, 'Popen', lambda *a, **kw: pytest.fail('probe must not spawn'))
    answer = observe(publish_case)
    assert answer['status'] == want
    assert answer['execution_id'] == payload['execution_id'] and answer['generation'] == 1
    assert answer['request_hash'] == payload['request_hash'] and answer['nonce'] == 'a'*32
    assert {p.name:p.read_bytes() for p in path.parent.glob('*.json')} == before


@pytest.mark.parametrize('lock_name',['.launch.lock','.worker.lock'])
def test_in_flight_lock_is_not_negative_launch_evidence(publish_case, lock_name):
    path = publish_case[2]
    with path.with_suffix(lock_name).open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        answer = observe(publish_case)
    assert answer['status'] == 'uncertain'


@pytest.mark.parametrize('fault',['legacy','changed_request','foreign_receipt','malformed_worker'])
def test_absent_or_untrusted_evidence_cannot_authorize_retry(publish_case, fault):
    _, _, path, payload, worker = publish_case
    if fault == 'legacy':
        payload.pop('publish_dispatch_version')
    elif fault == 'changed_request':
        path.write_text(json.dumps(dict(payload, generation=2)))
    elif fault == 'foreign_receipt':
        path.with_suffix('.status.json').write_text(json.dumps(dict(payload,status='success',execution_id='foreign')))
    else: worker.write_text('{')
    with pytest.raises((ValueError, RuntimeError)):
        observe(publish_case)


@pytest.mark.parametrize('publish_case', ['wgs'], indirect=True)
def test_wgs_ambiguous_step4_cannot_spawn_again(publish_case, monkeypatch):
    pipeline, gate, path, payload, _ = publish_case
    launches = []
    def spawn(*a, **kw):
        launches.append(a)
        raise OSError('synthetic ambiguous spawn')
    monkeypatch.setattr(gate.subprocess, 'Popen', spawn)
    with pytest.raises(OSError): gate.start_async_stage(payload)
    with pytest.raises(RuntimeError): gate.start_async_stage(payload)
    assert len(launches) == 1


def test_duplicate_start_after_lost_reply_keeps_same_operation(publish_case, monkeypatch):
    pipeline, gate, _, payload, _ = publish_case
    launches = []
    def spawn(*a, **kw):
        launches.append(a)
        return SimpleNamespace(pid=os.getpid())
    monkeypatch.setattr(gate.subprocess, 'Popen', spawn)
    def start():
        if pipeline == 'wgs':return gate.start_async_stage(payload)
        return gate.start(payload['analysis_id'],1,'step4_publish',1)
    start(); start()
    assert len(launches) == 1
    assert observe(publish_case)['status'] == 'running'


@pytest.mark.parametrize('fault',[None, 'generation', 'hash', 'nonce', 'extra'])
def test_restricted_probe_binds_the_registered_operation(publish_case, fault):
    from scripts.cce_publish_recovery import publish_probe_command
    pipeline, gate, _, payload, _ = publish_case
    command = ['--publish-probe',payload['analysis_id'],'1','1',payload['request_hash'],'a'*32]
    if fault == 'generation':command[3] = '2'
    elif fault == 'hash':command[4] = 'b'*64
    elif fault == 'nonce':command[5] = '../foreign'
    elif fault == 'extra':command.append('foreign')
    if fault:
        with pytest.raises((ValueError, RuntimeError)):
            publish_probe_command(command,gate=gate,pipeline=pipeline)
    else:
        assert publish_probe_command(command,gate=gate,pipeline=pipeline)['status'] == 'not_started'
