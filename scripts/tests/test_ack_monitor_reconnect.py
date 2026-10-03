"""A failed START observer reconnects to its exact running producer only."""
import copy
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from test_p02_registered_recovery import registered
from test_p02_resume_final import adapter, mirrored_final, final_inputs, view_inputs as native_view_inputs, handoff, runtime
from scripts import cce_paired_runtime as paired, wgs_runtime_gate
from cce_pipeline.assets import cce_writer_guard as guard

REAL_QUERY = runtime._recovery_query
REAL_LEGACY_QUERY = runtime._kubectl_json


@pytest.fixture
def view_inputs(handoff, request):
    harness, context = native_view_inputs.__wrapped__(handoff, request)
    if request.node.callspec.params.get('fault') == 'split_root_observer_chain':
        # Complete only this synthetic template before final_inputs/mirrored_final
        # freeze its native binding, recovery evidence, and registered hashes.
        from cce_pipeline.master_job import run_label
        manifest_path = harness.bundle / 'master-job.yaml'
        manifest = yaml.safe_load(manifest_path.read_bytes())
        label_key = 'cce.biosan.cn/run-id'
        label = run_label(harness.contract['identity']['run_id'])
        manifest['metadata']['labels'][label_key] = label
        template = manifest['spec']['template']['metadata']
        template.setdefault('labels', {})[label_key] = label
        selector = manifest['spec'].get('selector', {}).get('matchLabels', {})
        if label_key in selector:
            selector[label_key] = label
        manifest_path.write_text(yaml.safe_dump(manifest))
    return harness, context


@pytest.mark.parametrize('view_inputs', [
    {'pipeline': 'wgs', 'analysis_id': 'WGS_20261003_000000_AAAAAA'}], indirect=True)
@pytest.mark.parametrize('fault', [None, 'ack', 'owner', 'journal', 'producer', 'deadline',
                                 'retired_success', 'retired_failed', 'split_root_observer_chain'])
def test_created_start_ack_reconnect_is_observer_only(registered, monkeypatch, fault):
    state, _, gate, producer, old_path, policy, bundle, harness = registered
    split = fault == 'split_root_observer_chain'
    producer_generation = 3 if split else 8
    producer.update(stage='step3_monitor', generation=producer_generation,
                    execution_id=producer['analysis_id'] + f'-a1-step3-g{producer_generation}')
    if split:
        # Production topology: immutable registrations/requests are in the
        # spool, while WGS recovery journals/views are in a distinct control.
        runtime_root = old_path.parents[3] / 'runtime-control'
        control = runtime_root / producer['analysis_id'] / 'attempt-1'
        control.mkdir(parents=True)
        for directory in (runtime_root, control.parent, control):
            directory.chmod(0o2770)
        monkeypatch.setattr(gate, 'RUNTIME_RUN_ROOT', str(runtime_root))
        producer['control_workdir'] = str(control)
    producer['cce_recovery_deadline'] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    producer['request_hash'] = paired._request_digest(producer, 'wgs')
    path = gate._request_path(producer['analysis_id'], 1, producer['stage'])
    path.write_text(json.dumps(producer))
    binding = json.loads((bundle.parent / 'batch-binding.json').read_bytes())
    if split:
        # Complete the synthetic platform binding before its producer starts.
        # The native template was normalized before evidence was frozen; the
        # external Kubernetes fixture and gate must use that same frozen label.
        label = yaml.safe_load((bundle / 'master-job.yaml').read_bytes())[
            'metadata']['labels']['cce.biosan.cn/run-id']
        binding.update(run_id=harness.contract['identity']['run_id'],
            namespace=harness.contract['kubernetes']['namespace'],
            master_job=harness.contract['kubernetes']['master_job'],
            run_label=label)
        if state.worker is not None:
            state.worker['metadata']['labels']['cce.biosan.cn/run-id'] = label
        gate._load_binding(producer).update(binding)
        (bundle.parent / 'batch-binding.json').write_text(json.dumps(binding))
        frozen_binding_raw = (bundle.parent / 'batch-binding.json').read_bytes()
    await_ack = runtime._await_master_confirmation
    finish = runtime._finish_master_handoff

    def fail_ack(*args, **kwargs):
        raise RuntimeError('Master confirmation identity mismatch')

    monkeypatch.setattr(runtime, '_await_master_confirmation', fail_ack)
    with pytest.raises(RuntimeError, match='Master confirmation identity mismatch'):
        paired.resume_registered(producer, binding=binding, gate=gate, pipeline='wgs')
    monkeypatch.setattr(runtime, '_await_master_confirmation', await_ack)
    journal_path = Path(producer['control_workdir']) / 'recovery-new-action.json'
    journal_raw = journal_path.read_bytes()
    journal = json.loads(journal_raw)
    assert journal['recovery_state'] == 'created'
    selected = Path(journal['recovery_v2']['view'])
    record = runtime._read_master_handoff(selected, harness.contract)
    assert record['state'] == 'START_SENT'
    assert (state.creates, state.starts) == (1, 1)
    history = path.parent / 'request-history' / 'step3_monitor'
    history.mkdir(parents=True, exist_ok=True)
    original_path = history / f'generation-{producer_generation}.json'
    original_path.write_bytes(path.read_bytes())
    producer_raw = original_path.read_bytes()
    if fault is None or fault in ('retired_success', 'retired_failed', 'split_root_observer_chain'):
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
        registration_raw = registration_path.read_bytes()
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
    observer_generation = 5 if split else 9
    observer.update(generation=observer_generation,
                    execution_id=producer['analysis_id'] + f'-a1-step3-g{observer_generation}',
                    resume_action_id='observe-current-master', resume_previous_execution={
                        key: producer[key] for key in ('execution_id', 'generation', 'request_hash')})
    archived_observer = None
    if split:
        archived_observer = copy.deepcopy(observer)
        archived_observer.update(generation=4,
            execution_id=producer['analysis_id'] + '-a1-step3-g4',
            resume_action_id='failed-observer-only')
        archived_observer['request_hash'] = paired._request_digest(archived_observer, 'wgs')
        path.write_text(json.dumps(archived_observer))
        gate._write_status(archived_observer, 'failed', 'observer did not resolve its original producer')
        failed_receipt_raw = path.with_suffix('.status.json').read_bytes()
        failed_observer_path = history / 'generation-4.json'
        failed_observer_path.write_bytes(path.read_bytes())
        failed_observer_raw = failed_observer_path.read_bytes()
        failed_observer_status = history / 'generation-4.status.json'
        failed_observer_status.write_bytes(failed_receipt_raw)
        path.with_suffix('.status.json').unlink()
        observer['resume_previous_execution'] = {
            key: archived_observer[key] for key in ('execution_id', 'generation', 'request_hash')}
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
    elif fault in ('retired_success', 'retired_failed', 'split_root_observer_chain'):
        from test_recovery_final import SubmissionManager, plugin_tests
        confirmation['confirmed_epoch'] = harness.now
        monkeypatch.setattr(runtime, '_master_input_context', lambda: record)
        monkeypatch.setenv('CCE_RUN_ROOT', harness.contract['paths']['run_dir'])
        monkeypatch.setenv('CCE_INPUT_ROOT', str(selected))
        for phase in ('preflight', 'analysis'):
            env = runtime._recovery_phase_start(phase)
            root = Path(env['SNAKEMAKE_CCE_SUBMIT_EVIDENCE_DIR'])
            context = json.loads(Path(env['SNAKEMAKE_CCE_SUBMIT_CONTEXT_FILE']).read_bytes())
            SubmissionManager(context, root, plugin_tests.API(root, [])).claim_executor()
            runtime._recovery_phase_finished(phase, 0)
        success = fault in ('retired_success', 'split_root_observer_chain')
        terminal = runtime._bind_master_terminal({'schema_version': 1,
            'state': 'SUCCEEDED' if success else 'FAILED', 'exit_code': 0 if success else 1,
            'finished_epoch': harness.now + 1, 'failed_stage': 'final_dryrun',
            'exit_codes': {'preflight': 0, 'analysis': 0, 'final_dryrun': 0 if success else 1}})
        assert terminal['submission_inventory_complete'] is True
        evidence = {'START_CONFIRMED.json': confirmation,
            'RUN_COMPLETE.json' if success else 'RUN_FAILED.json': terminal,
            'recovery-final.json': json.loads((Path(harness.contract['paths']['run_dir']) /
                'evidence' / record['run_id'] / 'recovery-final.json').read_bytes())}
        if success:
            evidence['workflow-completion.json'] = {'required': [{'path': 'ANALYSIS_COMPLETE',
                'content': json.dumps({'schema_version': 1, 'status': 'PASS', **harness.contract['identity']})}]}
        runtime._write_mirror_evidence(selected, record['run_id'], evidence,
            project=record['project'], batch=record['batch'])
        state.job = None
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
    frozen_inputs = {name: (bundle / name).read_bytes() for name in
        ('BATCH_RUNTIME.yaml', 'PAYLOAD.yaml', 'master-job.yaml', 'payload/config.yaml')}
    if fault and fault not in ('retired_success', 'split_root_observer_chain'):
        with pytest.raises((RuntimeError, ValueError)):
            paired.prepare_monitor_registered(observer, binding=binding, gate=gate, pipeline='wgs')
        assert '_cce_master_result' not in observer
    else:
        paired.prepare_monitor_registered(observer, binding=binding, gate=gate, pipeline='wgs')
        result = observer['_cce_master_result']
        if not split:
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
        if split:
            # Consume the native success in the normal monitor and write its
            # verified receipt. Step4 must use that receipt/hash and the actual
            # protected native stage, not a fake downstream operation.
            from cce_pipeline.assets import step3_status
            harness.modules = (*harness.modules[:3], step3_status)
            # The inherited fixture replaces both high-level query readers.
            # Restore their real implementations so this monitor's durable
            # QueryReconnect owner sees the actual native GET; emulate only
            # Kubernetes subprocess I/O below the classification/budget gate.
            synthetic_query = runtime._kubectl_json
            native_transport = runtime._run
            def monitor_transport(command, **kwargs):
                if command[5] != 'get':
                    return native_transport(command, **kwargs)
                arguments = [argument for argument in command[6:command.index('-o')]
                    if argument not in {'--ignore-not-found', '--chunk-size=0'}]
                value = synthetic_query(harness.config, *arguments)
                if value is not None and arguments[0] == 'pods':
                    value.update(kind='PodList', metadata={})
                return subprocess.CompletedProcess(command, 0,
                    json.dumps(value).encode() if value is not None else b'', b'')
            monkeypatch.setattr(runtime, '_run', monitor_transport)
            monkeypatch.setattr(runtime, '_recovery_query', REAL_QUERY)
            monkeypatch.setattr(runtime, '_kubectl_json', REAL_LEGACY_QUERY)
            assert gate._write_status(observer, 'running', 'observing original completed Master')
            observed = paired.monitor_registered(observer, binding=binding, gate=gate, pipeline='wgs')
            assert observed['master_state'] == 'SUCCEEDED'
            assert gate._write_status(observer, 'success', master=observed)
            receipt_path = path.with_suffix('.status.json')
            receipt = json.loads(receipt_path.read_bytes())
            assert receipt['generation'] == 5
            assert receipt['monitor_reconnect']['phase'] == 'healthy'
            assert receipt['monitor_reconnect']['last_success_at'] is not None
            assert receipt['cce_master_submit_execution_id'] == producer['execution_id']
            assert receipt['cce_master_binding']['platform_execution']['generation'] == 3
            assert receipt['cce_master_binding']['native']['job_uid'] == record['job_uid']
            published = []
            def publish(**arguments):
                published.append(arguments)
                return True  # Only the external OBS delivery transport is synthetic.
            harness.modules = (SimpleNamespace(reconcile_publish_status=publish), *harness.modules[1:])
            downstream = json.loads(path.read_bytes())
            downstream.update(stage='step4_publish', generation=1,
                execution_id=producer['analysis_id'] + '-a1-step4-g1',
                predecessor_execution_id=observer['execution_id'], predecessor_generation=5,
                predecessor_receipt_hash=hashlib.sha256(receipt_path.read_bytes()).hexdigest())
            downstream['request_hash'] = paired._request_digest(downstream, 'wgs')
            downstream_path = gate._request_path(downstream['analysis_id'], 1, downstream['stage'])
            changed = {**downstream, 'predecessor_receipt_hash': 'f' * 64}
            downstream_path.write_text(json.dumps(changed))
            with pytest.raises(RuntimeError, match='registered successful execution'):
                paired.downstream_registered(changed, binding=binding, gate=gate, pipeline='wgs')
            downstream_path.write_text(json.dumps(downstream))
            value = paired.downstream_registered(downstream, binding=binding, gate=gate, pipeline='wgs')
            assert value == {'stage': 'step4_publish', 'status': 'success'}
            assert gate._write_status(downstream, 'success')
            downstream_receipt = json.loads(downstream_path.with_suffix('.status.json').read_bytes())
            assert downstream_receipt['cce_master_binding'] == receipt['cce_master_binding']
            assert downstream_receipt['cce_master_submit_execution_id'] == producer['execution_id']
            assert len(published) == 1
            assert published[0]['obs_uri'] == 'obs://synthetic/out'
            assert published[0]['work_root'] == bundle / 'delivery-publish'
            assert registration_path.read_bytes() == registration_raw
            assert (bundle.parent / 'batch-binding.json').read_bytes() == frozen_binding_raw
            assert receipt['run_label'] == binding['run_label']
            assert receipt['namespace'] == harness.contract['kubernetes']['namespace']
            assert receipt['master_job'] == harness.contract['kubernetes']['master_job']
            assert json.loads(registration_raw)['control_root'] == str(path.parent)
            assert journal_path.parent != path.parent
            assert failed_observer_path.read_bytes() == failed_observer_raw
            assert failed_observer_status.read_bytes() == failed_receipt_raw
            assert original_path.read_bytes() == producer_raw
            assert observer['cce_recovery_deadline'] == producer['cce_recovery_deadline']
            assert downstream['cce_recovery_deadline'] == producer['cce_recovery_deadline']
        else:
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
    assert {name: (bundle / name).read_bytes() for name in frozen_inputs} == frozen_inputs
    assert (state.creates, state.starts) == (1, 1)
