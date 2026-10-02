"""A Step1 recovery action does not imply an existing native Master.

Reuse the registered native fixture: Kubernetes and OBS transport are synthetic,
while registration, directory-owner fencing, CREATE intent, handoff and selected
producer reconstruction stay real. No production identity appears in fixtures.
"""
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from test_p02_registered_recovery import registered
from test_p02_selected_monitor import (
    adapter, mirrored_final, final_inputs, view_inputs, handoff, runtime,
)
from scripts import cce_paired_runtime as paired, wgs_resume


INITIAL_VIEW = {'pipeline': 'wgs', 'analysis_id': 'WGS_20261002_000000_SYNTHETIC'}
INITIAL_ADAPTER = {'initial': True}


@pytest.fixture
def continuation(registered, monkeypatch):
    state, _, gate, upload, upload_path, policy, bundle, native = registered
    binding = gate._load_binding(upload)
    monkeypatch.setattr(gate, 'RUNTIME_RUN_ROOT', str(upload_path.parent.parent.parent))

    def save(value):
        value = {k: v for k, v in value.items()
            if not k.startswith('_') and k != 'resume_master_uid'}
        value['request_hash'] = paired._request_digest(value, 'wgs')
        path = gate._request_path(value['analysis_id'], value['attempt'], value['stage'])
        path.write_text(json.dumps(value))
        return value, path

    def finish(value, path):
        gate._write_status(value, 'success')
        path.with_suffix('.worker.json').write_text(json.dumps({
            **{k: value[k] for k in ('analysis_id', 'attempt', 'stage',
                'execution_id', 'generation', 'request_hash')},
            'pid': 999999999, 'boot_id': 'synthetic-ended', 'process_start_time': '0',
        }))

    prepare, prepare_path = save({**upload, 'stage': 'prepare_analysis', 'generation': 2,
        'execution_id': 'synthetic-prepare-g2'})
    finish(prepare, prepare_path)
    upload, upload_path = save({**upload, 'generation': 2,
        'execution_id': 'synthetic-upload-g2', 'resume_action_id': 'synthetic-step1-resume',
        'predecessor_execution_id': prepare['execution_id'], 'predecessor_generation': 2,
        'predecessor_receipt_hash': hashlib.sha256(
            prepare_path.with_suffix('.status.json').read_bytes()).hexdigest()})
    # Obtain the real dynamic initial registration and pending owner through
    # the same protected Step1 boundary as the normal-path fixture.
    gate._step_command(upload, 'step1_upload')
    native.config['obs']['upload_parallelism'] = 1
    monkeypatch.setattr(runtime, '_obs_command', lambda *a, **k:
        subprocess.CompletedProcess([], 0, b'', b''))
    writer = runtime.writer_for_bundle(runtime, bundle, native.contract, native.config)
    runtime.step1(bundle, native.contract, native.config, native.modules, writer=writer)
    finish(upload, upload_path)
    initial_owner = json.loads(next(iter(state.cms.values()))['data']['lock'])['owner']
    assert initial_owner['generation'] == 1 and initial_owner['master_uid'] == ''
    assert state.job is None and (state.creates, state.starts) == (0, 0)

    submit, path = save({**upload, 'stage': 'step2_master', 'generation': 2,
        'execution_id': 'synthetic-first-step2-g2',
        'predecessor_execution_id': upload['execution_id'], 'predecessor_generation': 2,
        'predecessor_receipt_hash': hashlib.sha256(
            upload_path.with_suffix('.status.json').read_bytes()).hexdigest()})
    original_request = path.read_bytes()
    original_bundle = {str(p.relative_to(bundle)): p.read_bytes()
        for p in bundle.rglob('*') if p.is_file()}
    original_policy = policy.read_bytes()

    def invoke():
        # The real restricted worker already owns its current worker lock.
        with paired._exclusive(path.with_suffix('.worker.lock')):
            wgs_resume.run_resume_stage(submit, gate=gate)
            gate._write_status(submit, 'success')
        return json.loads(path.with_suffix('.status.json').read_bytes())

    return SimpleNamespace(state=state, gate=gate, binding=binding, bundle=bundle,
        native=native, policy=policy, upload=upload, upload_path=upload_path,
        submit=submit, path=path, save=save, finish=finish, invoke=invoke,
        initial_owner=initial_owner, original_request=original_request,
        original_bundle=original_bundle, original_policy=original_policy)


@pytest.mark.parametrize('view_inputs', [INITIAL_VIEW], indirect=True)
@pytest.mark.parametrize('adapter', [INITIAL_ADAPTER], indirect=True)
def test_first_step2_after_resumed_step1_submits_once_without_changing_action(continuation):
    case = continuation
    receipt = case.invoke()
    assert receipt['status'] == 'success'
    assert receipt['cce_master_binding']['native']['execution_generation'] == 1
    assert receipt['cce_master_binding']['native']['job_uid'] == 'new-uid'
    assert receipt['cce_master_binding']['platform_execution']['execution_id'] == 'synthetic-first-step2-g2'
    assert receipt['cce_master_binding']['platform_execution']['generation'] == 2
    assert case.submit['resume_action_id'] == 'synthetic-step1-resume'
    assert case.path.read_bytes() == case.original_request
    journal = case.path.parent / 'submission-synthetic-first-step2-g2.json'
    assert json.loads(journal.read_bytes())['state'] == 'confirmed'
    # Re-entering the same registered producer reconciles its own durable
    # initial journal; it never becomes a replacement because it has an action.
    assert case.invoke()['cce_master_binding'] == receipt['cce_master_binding']
    assert not (case.path.parent / 'recovery-synthetic-step1-resume.json').exists()
    owner = json.loads(next(iter(case.state.cms.values()))['data']['lock'])['owner']
    assert owner == {**case.initial_owner, 'master_uid': 'new-uid'}
    assert (case.state.creates, case.state.starts, case.state.deletes) == (1, 1, 0)
    assert case.policy.read_bytes() == case.original_policy
    assert case.original_bundle == {name: (case.bundle / name).read_bytes()
        for name in case.original_bundle}


@pytest.mark.parametrize('view_inputs', [INITIAL_VIEW], indirect=True)
@pytest.mark.parametrize('adapter', [INITIAL_ADAPTER], indirect=True)
def test_first_step2_unknown_create_never_sends_a_second_create(continuation):
    case = continuation
    case.state.lose = case.state.hide = True
    for _ in range(2):
        with pytest.raises(RuntimeError, match='outcome|reconciliation'):
            case.invoke()
    assert (case.state.creates, case.state.starts, case.state.deletes) == (1, 0, 0)
    journal = json.loads((case.path.parent / 'submission-synthetic-first-step2-g2.json').read_bytes())
    assert journal['state'] == 'submitting'
    assert case.path.read_bytes() == case.original_request


@pytest.mark.parametrize('view_inputs', [INITIAL_VIEW], indirect=True)
@pytest.mark.parametrize('adapter', [INITIAL_ADAPTER], indirect=True)
def test_first_step2_late_exact_job_reconciles_original_create_intent(continuation):
    case = continuation
    case.state.lose = case.state.hide = True
    with pytest.raises(RuntimeError, match='outcome|reconciliation'):
        case.invoke()
    journal_path = case.path.parent / 'submission-synthetic-first-step2-g2.json'
    journal = json.loads(journal_path.read_bytes())
    selected = Path(journal['identity']['selected_bundle'])
    # The first transmitted CREATE becomes observable later. The only fake
    # here is the remote API response, with the exact submitted manifest.
    job = yaml.safe_load((selected / 'master-job.yaml').read_bytes())
    job['metadata'].update(uid='new-uid', resourceVersion='20')
    job['status'] = {'active': 1}
    case.state.job = job
    case.state.lose = case.state.hide = False
    assert case.invoke()['cce_master_binding']['native']['job_uid'] == 'new-uid'
    assert json.loads(journal_path.read_bytes())['state'] == 'confirmed'
    assert (case.state.creates, case.state.starts, case.state.deletes) == (1, 1, 0)
    assert case.path.read_bytes() == case.original_request


@pytest.mark.parametrize('view_inputs', [INITIAL_VIEW], indirect=True)
@pytest.mark.parametrize('adapter', [INITIAL_ADAPTER], indirect=True)
@pytest.mark.parametrize('fault', ['foreign_owner', 'failed_step1', 'changed_predecessor',
    'changed_predecessor_generation', 'foreign_journal', 'unknown_recovery_json'])
def test_first_step2_requires_exact_predecessor_and_initial_owner(continuation, fault):
    case = continuation
    if fault == 'foreign_owner':
        cm = next(iter(case.state.cms.values()))
        value = json.loads(cm['data']['lock'])
        value['owner']['action'] = 'foreign-initial-owner'
        cm['data']['lock'] = json.dumps(value)
    elif fault == 'failed_step1':
        # The real status writer fences a successful terminal generation.
        # Set the synthetic predecessor input explicitly instead of asking
        # that writer to overwrite its completed receipt.
        receipt_path = case.upload_path.with_suffix('.status.json')
        receipt = json.loads(receipt_path.read_bytes())
        receipt['status'] = 'failed'
        receipt_path.write_text(json.dumps(receipt))
        case.submit['predecessor_receipt_hash'] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        updated, _ = case.save(case.submit)
        case.submit.update(updated)
    elif fault == 'changed_predecessor':
        case.submit['predecessor_receipt_hash'] = 'f' * 64
        updated, _ = case.save(case.submit)
        case.submit.update(updated)
    elif fault == 'changed_predecessor_generation':
        case.submit['predecessor_generation'] = 1
        updated, _ = case.save(case.submit)
        case.submit.update(updated)
    elif fault == 'unknown_recovery_json':
        # _journal_views intentionally ignores unregistered recovery JSON.
        # Such unknown CREATE evidence must still block the first Master;
        # a same-named directory cannot make the omitted producer trusted.
        orphan = case.path.parent / 'recovery-unregistered.json'
        orphan.write_text(json.dumps({'recovery_state': 'creating'}))
        orphan_view = orphan.with_suffix('') / 'view'
        orphan_view.mkdir(parents=True)
        (orphan_view / 'MASTER_CREATE_INTENT.json').write_text(json.dumps({
            'schema_version': 1, 'state': 'creating'}))
    else:
        (case.path.parent / 'submission-unknown-producer.json').write_text(json.dumps({
            'state': 'submitting', 'identity': {'platform_execution': {
                'pipeline': 'wgs', 'analysis_id': case.submit['analysis_id'],
                'attempt': 1, 'stage': 'step2_master', 'execution_id': 'unknown-producer',
                'generation': 1, 'request_hash': 'e' * 64},
                'source_bundle': str(case.bundle),
                'selected_bundle': str(case.path.parent / 'submission-unknown-producer' / 'view')}}))
    expected_error = RuntimeError if fault == 'unknown_recovery_json' else (RuntimeError, ValueError)
    with pytest.raises(expected_error):
        case.invoke()
    assert (case.state.creates, case.state.starts, case.state.deletes) == (0, 0, 0)


@pytest.mark.parametrize('view_inputs', [INITIAL_VIEW], indirect=True)
@pytest.mark.parametrize('adapter', [INITIAL_ADAPTER], indirect=True)
def test_carried_resume_action_reader_uses_authenticated_initial_producer(continuation):
    case = continuation
    # Keep the inherited action on producer and monitor. Native confirmation,
    # selected binding and submission journal come from the genuine initial
    # producer above; the reader must infer no replacement from that action.
    case.invoke()
    submit_receipt = case.path.with_suffix('.status.json')
    monitor, monitor_path = case.save({**case.submit, 'stage': 'step3_monitor',
        'execution_id': 'synthetic-monitor-g1', 'generation': 1,
        'predecessor_execution_id': case.submit['execution_id'], 'predecessor_generation': 2,
        'predecessor_receipt_hash': hashlib.sha256(submit_receipt.read_bytes()).hexdigest()})
    observed = paired._selected_registered(monitor, binding=case.binding, gate=case.gate,
        pipeline='wgs', operation=lambda *_: {'master_state': 'RUNNING', 'master_uid': 'new-uid'})
    assert observed['master_state'] == 'RUNNING' and observed['master_uid'] == 'new-uid'
    assert monitor['resume_action_id'] == 'synthetic-step1-resume'
    assert monitor_path.read_bytes() == json.dumps({k: v for k, v in monitor.items()
        if not k.startswith('_') and k != 'resume_master_uid'}).encode()
    assert case.path.read_bytes() == case.original_request
    assert (case.state.creates, case.state.starts, case.state.deletes) == (1, 1, 0)
