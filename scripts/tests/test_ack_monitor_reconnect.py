"""A failed START observer reconnects to its exact running producer only."""
import copy
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from test_p02_registered_recovery import registered
from test_p02_resume_final import adapter, mirrored_final, final_inputs, view_inputs, handoff, runtime
from scripts import cce_paired_runtime as paired, wgs_runtime_gate
from cce_pipeline.assets import cce_writer_guard as guard


@pytest.mark.parametrize('view_inputs', [
    {'pipeline': 'wgs', 'analysis_id': 'WGS_20261003_000000_AAAAAA'}], indirect=True)
@pytest.mark.parametrize('fault', [None, 'ack', 'owner', 'journal', 'producer', 'deadline'])
def test_created_start_ack_reconnect_is_observer_only(registered, monkeypatch, fault):
    state, _, gate, producer, old_path, policy, bundle, harness = registered
    producer.update(stage='step3_monitor', execution_id=producer['analysis_id'] + '-a1-step3-g8')
    producer['cce_recovery_deadline'] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    producer['request_hash'] = paired._request_digest(producer, 'wgs')
    path = gate._request_path(producer['analysis_id'], 1, producer['stage'])
    path.write_text(json.dumps(producer))
    binding = json.loads((bundle.parent / 'batch-binding.json').read_bytes())
    await_ack = runtime._await_master_confirmation
    finish = runtime._finish_master_handoff

    def fail_ack(*args, **kwargs):
        raise RuntimeError('Master confirmation identity mismatch')

    monkeypatch.setattr(runtime, '_await_master_confirmation', fail_ack)
    with pytest.raises(RuntimeError, match='Master confirmation identity mismatch'):
        paired.resume_registered(producer, binding=binding, gate=gate, pipeline='wgs')
    monkeypatch.setattr(runtime, '_await_master_confirmation', await_ack)
    journal_path = path.parent / 'recovery-new-action.json'
    journal_raw = journal_path.read_bytes()
    journal = json.loads(journal_raw)
    assert journal['recovery_state'] == 'created'
    selected = Path(journal['recovery_v2']['view'])
    record = runtime._read_master_handoff(selected, harness.contract)
    assert record['state'] == 'START_SENT'
    assert (state.creates, state.starts) == (1, 1)
    history = path.parent / 'request-history' / 'step3_monitor'
    history.mkdir(parents=True, exist_ok=True)
    original_path = history / 'generation-8.json'
    original_path.write_bytes(path.read_bytes())
    if fault is None:
        # Exercise the actual production guard's schema3/cloud branch, including
        # its START_CONFIRMED-only current-owner resolver. Only the directory
        # identity transport is synthetic; registration and resolver stay real.
        runtime._write_master_handoff(bundle, harness.contract, job_name=record['job_name'],
            job_uid=journal['recovery_v2']['expected_job_uid'], state='START_CONFIRMED')
        assert runtime._read_master_handoff(bundle, harness.contract)['state'] == 'START_CONFIRMED'
        approved = json.loads(policy.read_bytes())
        registration = copy.deepcopy(approved['bindings'][0])
        context = registration['context']
        context.update(generation=1, action=runtime.initial_owner_action(pipeline='wgs',
            analysis_id=producer['analysis_id'], attempt=1, run_id=harness.contract['identity']['run_id']), master_uid='')
        registration.update(schema_version=3, control_root=str(path.parent))
        registration_path = guard._registration_path(Path(approved['journal_root']),
            harness.contract['identity']['run_id'], 1)
        registration_path.write_text(json.dumps(registration))
        registration_path.chmod(0o660)
        approved['bindings'] = []
        approved['storage']['mode'] = 'cloud-reader'
        policy.write_text(json.dumps(approved))
        storage_identity = {'canonical_directory': context['canonical_directory']}
        monkeypatch.setattr(guard, 'cloud_storage_identity', lambda *a, **k: storage_identity)
        monkeypatch.setattr(guard, 'current_master_storage_identity', lambda *a, **k: storage_identity)
    old_terminal = path.parent / 'old-gen8-terminal.json'
    old_terminal.write_text(json.dumps({'status': 'failed', 'message': 'ACK identity mismatch'}))
    terminal_raw = old_terminal.read_bytes()
    observer = copy.deepcopy(producer)
    observer.update(generation=9, execution_id=producer['analysis_id'] + '-a1-step3-g9',
                    resume_action_id='observe-current-master', resume_previous_execution={
                        key: producer[key] for key in ('execution_id', 'generation', 'request_hash')})
    observer['request_hash'] = paired._request_digest(observer, 'wgs')
    path.write_text(json.dumps(observer))
    monkeypatch.setattr(paired, 'selected_runtime', lambda: (Path(runtime.__file__), '/operator/python'))

    def forbidden(*args, **kwargs):
        raise AssertionError('observer attempted replacement, CREATE, or START')

    monkeypatch.setattr(paired, 'resume_registered', forbidden)
    monkeypatch.setattr(runtime, '_advance_recovery_view', forbidden)
    monkeypatch.setattr(runtime, '_create_job_from_path', forbidden)
    confirmation = copy.deepcopy(record)
    confirmation.update(state='START_CONFIRMED', confirmed_epoch=record['deadline_epoch'] - 1)
    if fault == 'ack':
        confirmation['job_uid'] = 'foreign-uid'
    elif fault == 'owner':
        cm = next(iter(state.cms.values()))
        lock = json.loads(cm['data']['lock'])
        lock['owner']['master_uid'] = 'foreign-uid'
        cm['data']['lock'] = json.dumps(lock)
    elif fault == 'journal':
        journal['recovery_v2']['context']['execution_id'] = 'foreign-execution'
        journal_path.write_text(json.dumps(journal))
    elif fault == 'producer':
        changed = json.loads(original_path.read_bytes())
        changed['control_workdir'] += '-changed'
        original_path.write_text(json.dumps(changed))
    elif fault == 'deadline':
        observer['cce_recovery_deadline'] = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        observer['request_hash'] = paired._request_digest(observer, 'wgs')
        path.write_text(json.dumps(observer))
    transport = runtime._run

    def ack_transport(argv, *args, **kwargs):
        if 'cat' in argv and str(argv[-1]).endswith('/START_CONFIRMED.json'):
            return subprocess.CompletedProcess(argv, 0, json.dumps(confirmation).encode(), b'')
        if 'touch' in argv or 'apply' in argv or 'delete' in argv:
            forbidden()
        return transport(argv, *args, **kwargs)

    monkeypatch.setattr(runtime, '_run', ack_transport)
    def producer_finish(*args, **kwargs):
        writer = runtime.CURRENT_WRITER.get()
        assert 'execution_id' not in writer.context
        assert writer.context['generation'] == record['execution_generation']
        assert writer.context['action'] == producer['resume_action_id']
        return finish(*args, **kwargs)
    monkeypatch.setattr(runtime, '_finish_master_handoff', producer_finish)
    preserved_journal = journal_path.read_bytes()
    if fault:
        with pytest.raises((RuntimeError, ValueError)):
            paired.prepare_monitor_registered(observer, binding=binding, gate=gate, pipeline='wgs')
        assert '_cce_master_result' not in observer
    else:
        paired.prepare_monitor_registered(observer, binding=binding, gate=gate, pipeline='wgs')
        result = observer['_cce_master_result']
        assert runtime.writer_for_bundle(runtime, bundle, harness.contract, harness.config).registration_schema_version == 3
        assert result['master_uid'] == record['job_uid']
        assert result['cce_master_binding']['platform_execution']['execution_id'] == producer['execution_id']
        assert result['cce_master_binding']['native']['execution_generation'] == record['execution_generation']
        confirmed = runtime._read_master_handoff(selected, harness.contract)
        assert confirmed['state'] == 'START_CONFIRMED'
        assert all(confirmed[k] == v for k, v in record.items() if k not in {'state', 'updated_at'})
        # Durable recovery history is preserved, and a second observer prepare
        # must still select this producer without replacing it.
        paired.prepare_monitor_registered(observer, binding=binding, gate=gate, pipeline='wgs')
        paired._selected_registered(observer, binding=binding, gate=gate, pipeline='wgs',
            operation=lambda *args: {})
        contract, config, modules = runtime._load(bundle, None)
        writer = runtime.writer_for_bundle(runtime, bundle, contract, config)
        downstream = json.loads(path.read_bytes())
        downstream.update(stage='step4_publish', execution_id=producer['analysis_id'] + '-a1-step4-g1', generation=1)
        downstream['request_hash'] = paired._request_digest(downstream, 'wgs')
        gate._request_path(downstream['analysis_id'], 1, downstream['stage']).write_text(json.dumps(downstream))
        paired._observe_registered_source(downstream, binding, gate, 'wgs', runtime, bundle,
            contract, config, modules, writer, operation=lambda *args: {},
            expected=result['cce_master_binding'])
    assert journal_path.read_bytes() == preserved_journal
    assert old_terminal.read_bytes() == terminal_raw
    assert (state.creates, state.starts) == (1, 1)
