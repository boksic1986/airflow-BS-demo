"""Thin registered WGS routing; native abort/advance boundaries are synthetic.

The native no-START producer, capability inventory/CAS and replay primitive have
their own focused tests. Here the real paired entry must select the immutable
initial submission instead of requiring compute FINAL or reconciling START.
"""
from __future__ import annotations

import copy
import hashlib
import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

pytest.importorskip('cce_pipeline.stage_execution')

from scripts import cce_paired_runtime as paired, cce_stage_execution_adapter as stage
from scripts import wgs_resume
from test_cce_stage_execution_adapter import _request, _terminal, _write_json


LOCATORS = frozenset({'registration_path', 'terminal_path', 'dispatch_path',
    'business_receipt_path', 'stderr_path', 'paired_source_path',
    'native_source_path', 'executor_source_path'})


@pytest.fixture
def initial_entry(tmp_path, monkeypatch):
    pipeline = 'wgs'
    first = _request(1, pipeline=pipeline)
    first.update(stage='step2_master', execution_id='synthetic-initial-step2')
    aid = first['analysis_id']
    control = tmp_path/'requests'/aid/'attempt-1'
    control.mkdir(parents=True)
    bundle = tmp_path/'runs'/aid/'attempt-1'/'cce'
    bundle.mkdir(parents=True)
    first.update(control_workdir=str(control), runtime_workdir=str(bundle.parent))
    first['request_hash'] = paired._request_digest(first, pipeline)
    contract = dict(identity=dict(project='synthetic', batch='synthetic', run_id=aid+'-a1'),
        paths=dict(run_dir=str(tmp_path/'native-run')),
        kubernetes=dict(namespace='synthetic', master_job='master'))
    config = dict(kubernetes=dict(namespace='synthetic'))
    binding = dict(schema_version='wgs-runtime.batch-binding.v1', analysis_id=aid,
        attempt=1, run_id=aid+'-a1', cce_bundle=str(bundle), namespace='synthetic',
        master_job='master', run_label='synthetic-run')
    _write_json(bundle.parent/'batch-binding.json', binding)
    (bundle/'BATCH_RUNTIME.yaml').write_text(yaml.safe_dump(contract))
    gate = SimpleNamespace(_request_path=lambda a, n, s: control/(s+'.json'),
        _load_binding=lambda p: binding, _native_business_stage=lambda ref: None,
        RUNTIME_RUN_ROOT=str(tmp_path/'requests'), _workdir=lambda p: control)
    request = gate._request_path(aid, 1, 'step2_master')
    _write_json(request, first)
    stage._freeze_registered_request(first, gate=gate, pipeline=pipeline)
    _, _, _, old_ref = stage._read_frozen(stage._registration_path(request, 'step2_master', 1),
        gate=gate, pipeline=pipeline, registry=stage._registry(gate, pipeline))
    _, _, old_stage_binding = stage.executor_for_registered(first, gate=gate, pipeline=pipeline)
    # Native binding must precede business status, as in the real dispatcher.
    # Match the actual WGS receipt: no optional business receipt_hash field.
    _terminal(request, first, status='failed', receipt_hash=False)
    stage._publish_terminal(old_stage_binding, gate=gate, pipeline=pipeline)
    history = control/'request-history'/'step2_master'/'generation-1.json'
    history.parent.mkdir(parents=True)
    history.write_bytes(request.read_bytes())
    payload = dict(first, generation=2, execution_id='synthetic-recovery-step2',
        resume_action_id='synthetic-initial-abort-action')
    payload['request_hash'] = paired._request_digest(payload, pipeline)
    _write_json(request, payload)

    original = dict(attempt=1, execution_generation=1, config_sha256='b'*64,
        files_sha256={'synthetic-input': 'c'*64}, request_hash='d'*64)
    pending_owner = dict(generation=1, action='initial-synthetic-action', master_uid='')
    old_context = dict(pipeline=pipeline, analysis_id=aid, execution_id=first['execution_id'],
        generation=1, action=pending_owner['action'])
    platform = dict(pipeline=pipeline, **{k:first[k] for k in
        ('analysis_id', 'attempt', 'stage', 'execution_id', 'generation', 'request_hash')})
    journal_path = control/('submission-'+first['execution_id']+'.json')
    selected = journal_path.with_suffix('')/'view'
    selected.mkdir(parents=True)
    (selected/'BATCH_RUNTIME.yaml').write_text(yaml.safe_dump(contract))
    selected_binding = dict(original, recovery_context=old_context, platform_execution=platform)
    record = dict(selected_binding, **contract['identity'], schema_version=2,
        state='JOB_CREATED', job_name='master', job_uid='old-master-uid',
        deadline_epoch=100.02)
    journal = dict(identity=dict(platform_execution=platform, source_bundle=str(bundle),
        selected_bundle=str(selected)), state='created', job_uid='old-master-uid',
        deadline_epoch=100.02)
    _write_json(journal_path, journal)
    identity = dict(pipeline=pipeline, analysis_id=aid, attempt='1',
        config_digest=original['config_sha256'], run_id=contract['identity']['run_id'])
    cm = dict(metadata=dict(uid='lock-uid', resourceVersion='1'), data=dict(lock=json.dumps(
        dict(schema_version=2, identity=identity, state='OWNED', owner=pending_owner))))
    scope = dict(native_directory=contract['paths']['run_dir'],
        canonical_directory='/storage/synthetic/project')
    writer = SimpleNamespace(context=dict(identity, **pending_owner), config=config,
        serialize=nullcontext, validate=lambda: copy.deepcopy(scope), journal={},
        save_journal=lambda value: None)
    state = SimpleNamespace(cm=cm, job=None, abort_reads=0, creates=0, advances=[],
        selected_bindings={selected: selected_binding}, records={selected: record},
        original_bytes=journal_path.read_bytes())
    snapshots = control/'stage-execution-terminal'/'step2_master'/'initial-dispatch-generation-1'
    snapshots.mkdir(mode=0o700)
    locators = dict(registration_path=str(stage._registration_path(request, 'step2_master', 1)),
        terminal_path=str(stage._terminal_path(request, 'step2_master', 1)))
    for name in LOCATORS - locators.keys():
        target = snapshots/(name+'.synthetic')
        target.write_bytes(b'synthetic trusted snapshot\n')
        target.chmod(0o600)
        locators[name] = str(target)
    encoded = lambda value: (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()
    abort = dict(schema='cce-pipeline.initial-submission-abort.v1', bundle=str(selected),
        binding=selected_binding, run_id=record['run_id'], job_name='master',
        job_uid=record['job_uid'], pending_owner=pending_owner,
        intent_deadline_epoch=100.0, handoff_deadline_epoch=record['deadline_epoch'],
        submission_journal=journal, submission_journal_sha256=hashlib.sha256(encoded(journal)).hexdigest(),
        dispatch_proof=locators, files_sha256={k:hashlib.sha256(Path(v).read_bytes()).hexdigest()
            for k, v in locators.items()})

    def no_compute_final(*args, **kwargs):
        raise AssertionError('initial submitted source must never require compute FINAL')

    def native_abort(view, bound, *, submission_journal, dispatch_proof):
        assert view == selected and bound == contract
        assert submission_journal == journal and dispatch_proof == locators
        assert set(dispatch_proof) == LOCATORS
        assert all(Path(p).is_absolute() for p in dispatch_proof.values())
        state.abort_reads += 1
        return copy.deepcopy(abort)

    runtime = SimpleNamespace(_load=lambda *a: (contract, config, ()),
        writer_for_bundle=lambda *a, **k: writer,
        _handoff_binding=lambda view, bound: copy.deepcopy(original if Path(view)==bundle
            else state.selected_bindings[Path(view)]),
        _read_master_handoff=lambda view, bound: copy.deepcopy(state.records.get(Path(view))),
        _directory_lock_identity=lambda bound, ctx: ('synthetic-lock', copy.deepcopy(identity),
            {k:ctx[k] for k in ('generation', 'action', 'master_uid')}),
        _recovery_query=lambda cfg, kind, *a, **k: copy.deepcopy(state.cm if kind=='configmap' else state.job),
        _initial_submission_abort_evidence=native_abort,
        _recovery_encoded=encoded, _recovery_final_evidence=no_compute_final)
    monkeypatch.setattr(paired, 'load_runtime', lambda: runtime)

    def locator(ref, *, gate, pipeline):
        assert ref == old_ref and gate is not None and pipeline == 'wgs'
        return copy.deepcopy(locators)

    monkeypatch.setattr(stage, 'initial_dispatch_proof', locator)

    def advance(view, bound, cfg, **kwargs):
        assert Path(view) == selected and kwargs['initial_abort'] == abort
        assert kwargs['expected_job_uid'] == 'old-master-uid'
        assert kwargs['context'] == dict(pipeline='wgs', analysis_id=aid,
            execution_id=payload['execution_id'], generation=2, action=payload['resume_action_id'])
        assert 'compute_deadline' not in kwargs and 'canonical_directory' not in abort
        action_journal = copy.deepcopy(kwargs['journal'])
        if not action_journal:
            state.creates += 1
            destination = Path(kwargs['destination'])
            destination.mkdir(parents=True)
            action_journal.update(registered_source=str(selected), recovery_state='created',
                replacement_uid='new-master-uid', recovery_v2=dict(context=kwargs['context'],
                    original=selected_binding, expected_job_uid='old-master-uid', view=str(destination),
                    platform_execution=kwargs['platform_execution'], recovery_kind='initial_abort',
                    initial_abort_sha256=hashlib.sha256(encoded(abort)).hexdigest()))
            kwargs['save_journal'](action_journal)
            lock = json.loads(state.cm['data']['lock'])
            lock['owner'] = dict(generation=2, action=payload['resume_action_id'], master_uid='')
            state.cm['data']['lock'] = json.dumps(lock)
        else:
            assert action_journal['registered_source'] == str(selected)
            assert action_journal['recovery_state'] == 'created'
        state.advances.append(action_journal)
        return dict(mode='ready', bundle=str(view), master_uid='old-master-uid')

    runtime._advance_recovery_view = advance

    def resume(*, payload, binding, runtime, recovery):
        assert recovery.bundle == selected and recovery.origin_bundle == bundle
        assert recovery.initial_abort == abort
        action_path = control/('recovery-'+payload['resume_action_id']+'.json')
        current = json.loads(action_path.read_bytes()) if action_path.exists() else {}
        return runtime._advance_recovery_view(recovery.bundle, contract, config,
            context=recovery.context, expected_job_uid=recovery.expected_job_uid,
            destination=action_path.with_suffix('')/'view', journal=current,
            save_journal=lambda value: _write_json(action_path, value),
            initial_abort=recovery.initial_abort, platform_execution=recovery.platform_execution)

    monkeypatch.setattr(wgs_resume, 'resume_master', resume)
    return SimpleNamespace(state=state, payload=payload, binding=binding, gate=gate,
        runtime=runtime, contract=contract, source=selected, journal_path=journal_path,
        journal=journal, record=record, selected_binding=selected_binding, abort=abort,
        invoke=lambda: paired.resume_registered(payload, binding=binding, gate=gate, pipeline='wgs'))


def test_registered_initial_abort_enters_native_recovery_without_start_or_final(initial_entry, monkeypatch):
    case = initial_entry
    def forbidden(*args, **kwargs):
        raise AssertionError('proven initial abort must precede old START reconciliation')
    monkeypatch.setattr(paired, '_reconcile_initial_intent', forbidden)
    assert case.invoke()['mode'] == 'ready'
    assert case.state.abort_reads >= 1 and case.state.creates == 1
    assert case.journal_path.read_bytes() == case.state.original_bytes


@pytest.mark.parametrize('fault', ['ambiguous', 'changed_owner'])
def test_initial_abort_rejects_ambiguous_source_or_changed_pending_owner(initial_entry, fault):
    case = initial_entry
    if fault == 'ambiguous':
        duplicate = case.journal_path.with_name('submission-second-synthetic.json')
        selected = duplicate.with_suffix('')/'view'
        selected.mkdir(parents=True)
        value = copy.deepcopy(case.journal)
        value['identity']['selected_bundle'] = str(selected)
        _write_json(duplicate, value)
        case.state.selected_bindings[selected] = copy.deepcopy(case.selected_binding)
        case.state.records[selected] = copy.deepcopy(case.record)
    else:
        lock = json.loads(case.state.cm['data']['lock'])
        lock['owner']['action'] = 'foreign-owner'
        case.state.cm['data']['lock'] = json.dumps(lock)
    with pytest.raises((ValueError, RuntimeError)):
        case.invoke()
    assert case.state.creates == 0 and not case.state.advances
    assert case.journal_path.read_bytes() == case.state.original_bytes


def test_initial_abort_same_action_replay_uses_original_source_and_existing_native_journal(initial_entry, monkeypatch):
    case = initial_entry
    def forbidden(*args, **kwargs):
        raise AssertionError('initial abort replay must retain the old initial source')
    monkeypatch.setattr(paired, '_reconcile_initial_intent', forbidden)
    first = case.invoke()
    replay = case.invoke()
    assert first == replay and case.state.creates == 1
    assert len(case.state.advances) == 2
    assert all(j['registered_source'] == str(case.source) for j in case.state.advances)
    assert case.state.advances[1]['recovery_v2']['initial_abort_sha256'] == hashlib.sha256(
        case.runtime._recovery_encoded(case.abort)).hexdigest()
    assert case.journal_path.read_bytes() == case.state.original_bytes


def test_started_initial_abort_replay_observes_selected_master_and_binds_abort_ancestor(initial_entry, monkeypatch):
    from scripts.cce_recovery_inventory import InitialAbortAncestor

    case = initial_entry
    control = case.journal_path.parent
    action_path = control/('recovery-'+case.payload['resume_action_id']+'.json')
    selected = action_path.with_suffix('')/'view'
    selected.mkdir(parents=True)
    context = dict(pipeline='wgs', analysis_id=case.payload['analysis_id'],
        execution_id=case.payload['execution_id'], generation=2,
        action=case.payload['resume_action_id'])
    platform = dict(pipeline='wgs', **{k:case.payload[k] for k in
        ('analysis_id', 'attempt', 'stage', 'execution_id', 'generation', 'request_hash')})
    binding = dict(case.selected_binding, execution_generation=2,
        recovery_context=context, platform_execution=platform)
    record = dict(binding, **case.contract['identity'], schema_version=2,
        state='START_CONFIRMED', job_name='master', job_uid='new-master-uid',
        pod_uid='new-master-pod-uid', deadline_epoch=200.0, manifest_sha256='e'*64)
    digest = hashlib.sha256(case.runtime._recovery_encoded(case.abort)).hexdigest()
    journal = dict(registered_source=str(case.source), recovery_state='started',
        replacement_uid=record['job_uid'], recovery_v2=dict(context=context,
            original=case.selected_binding, expected_job_uid=case.record['job_uid'],
            view=str(selected), platform_execution=platform,
            recovery_kind='initial_abort', initial_abort_sha256=digest))
    _write_json(action_path, journal)
    case.state.selected_bindings[selected] = binding
    case.state.records[selected] = record
    lock = json.loads(case.state.cm['data']['lock'])
    lock['owner'] = dict(generation=2, action=context['action'], master_uid=record['job_uid'])
    case.state.cm['data']['lock'] = json.dumps(lock)
    case.state.job = dict(metadata=dict(name='master', uid=record['job_uid'],
        resourceVersion='2', annotations={
            'cce-pipeline/recovery-context': json.dumps(context, sort_keys=True),
            'cce-pipeline/execution-generation': '2'}), status=dict(active=1))
    writer = case.runtime.writer_for_bundle(case.runtime, Path(case.binding['cce_bundle']),
        case.contract, {})
    writer.registration_schema_version = 2
    case.runtime._job_flags = lambda job: (True, False, False)
    exports = []

    def monitor_transport(contract, config, modules, output, **kwargs):
        assert contract == case.contract and output == 'json'
        assert kwargs['bundle'] == Path(case.binding['cce_bundle'])
        assert kwargs['master_bundle'] == selected
        assert kwargs['expected_master_uid'] == record['job_uid']
        assert kwargs['read_only'] is True
        print(json.dumps(dict(master_state='RUNNING', master_uid=record['job_uid'])))

    case.runtime.step3 = monitor_transport

    def exported(runtime, origin, source, contract, producer):
        assert origin == Path(case.binding['cce_bundle']) and source == selected
        assert producer == platform
        value = dict(schema_version=2, platform_execution=producer,
            source_bundle=str(origin), selected_bundle=str(source),
            native={k:record[k] for k in ('project', 'batch', 'run_id', 'job_name',
                'job_uid', 'pod_uid', 'attempt', 'execution_generation', 'request_hash',
                'config_sha256', 'manifest_sha256', 'files_sha256', 'deadline_epoch',
                'recovery_context')})
        value['native']['namespace'] = case.contract['kubernetes']['namespace']
        exports.append(copy.deepcopy(value))
        return value

    def forbidden(*args, **kwargs):
        raise AssertionError('started action must only observe; no advance, CREATE or START')

    monkeypatch.setattr(paired, '_exported_master', exported)
    monkeypatch.setattr(case.runtime, '_advance_recovery_view', forbidden)
    monkeypatch.setattr(case.runtime, '_finish_master_handoff', forbidden, raising=False)
    monkeypatch.setattr(case.runtime, '_create_job_from_path', forbidden, raising=False)
    monkeypatch.setattr(wgs_resume, 'resume_master', forbidden)
    history = paired._source_history(control, 'wgs', case.runtime,
        Path(case.binding['cce_bundle']), case.contract, selected)
    assert len(history) == 1 and isinstance(history[0], InitialAbortAncestor)
    assert history[0].bundle == case.source and history[0].initial_abort_sha256 == digest
    result = case.invoke()
    assert result['mode'] == 'observed' and result['master_uid'] == record['job_uid']
    assert result['bundle'] == str(selected)
    assert result['cce_master_binding']['selected_bundle'] == str(selected)
    assert result['cce_master_binding']['platform_execution'] == platform
    assert exports and case.state.creates == 0 and not case.state.advances
    assert json.loads(action_path.read_bytes()) == journal
    assert case.journal_path.read_bytes() == case.state.original_bytes

    # A fresh Step3 must consume the same recovered Step2 through the real
    # selected-reader entry; observer reattachment alone does not cover it.
    keys = ('analysis_id', 'attempt', 'stage', 'execution_id', 'generation', 'request_hash')
    receipt = dict(schema_version='wgs-runtime.stage-status.v1',
        orchestration_contract_version=2, status='success',
        **{k:case.payload[k] for k in keys},
        cce_master_binding=result['cce_master_binding'],
        cce_master_submit_execution_id=result['cce_master_submit_execution_id'])
    status_path = case.gate._request_path(case.payload['analysis_id'], 1, 'step2_master').with_suffix('.status.json')
    _write_json(status_path, receipt)
    monitor = dict({k:v for k,v in case.payload.items() if not k.startswith('_')},
        stage='step3_monitor', generation=1, execution_id='synthetic-selected-step3',
        predecessor_execution_id=case.payload['execution_id'],
        predecessor_generation=case.payload['generation'],
        predecessor_receipt_hash=hashlib.sha256(status_path.read_bytes()).hexdigest())
    monitor['request_hash'] = paired._request_digest(monitor, 'wgs')
    _write_json(case.gate._request_path(monitor['analysis_id'], 1, monitor['stage']), monitor)
    case.runtime._master_handoff_path = lambda view, bound: Path(view)/'synthetic-master-handoff.json'
    abort_path = case.runtime._master_handoff_path(case.source, case.contract).with_name('INITIAL_SUBMISSION_ABORT.json')
    abort_path.write_bytes(case.runtime._recovery_encoded(case.abort))

    def validate_abort(value):
        assert value == case.abort
        return case.runtime._initial_submission_abort_evidence(Path(value['bundle']), case.contract,
            submission_journal=value['submission_journal'], dispatch_proof=value['dispatch_proof'])

    case.runtime._validate_initial_submission_abort = validate_abort
    value = paired._selected_registered(monitor, binding=case.binding, gate=case.gate, pipeline='wgs',
        operation=lambda *args: dict(master_state='RUNNING'))
    assert value['master_state'] == 'RUNNING'
    observed = monitor['_cce_master_result']
    assert observed['cce_master_binding'] == receipt['cce_master_binding']
    assert observed['cce_master_submit_execution_id'] == platform['execution_id']
    assert case.state.creates == 0 and not case.state.advances
    assert json.loads(action_path.read_bytes()) == journal
    assert case.journal_path.read_bytes() == case.state.original_bytes
