"""Thin initial-abort consumers; native proof and cluster transport are synthetic."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import cce_recovery_inventory as inventory, gatk_resume, wgs_resume


@pytest.fixture
def initial_capability(tmp_path, request, monkeypatch):
    pipeline = getattr(request, 'param', 'wgs')
    aid = pipeline.upper() + '_20261002_000000_AAAAAA'
    request_root = tmp_path / 'requests'
    control = request_root / aid / 'attempt-1'
    control.mkdir(parents=True)
    bundle = tmp_path / 'runs' / aid / 'attempt-1' / 'cce'
    bundle.mkdir(parents=True)
    context = dict(pipeline=pipeline, analysis_id=aid, execution_id='new-execution',
                   generation=2, action='new-action')
    old_context = dict(context, execution_id='old-execution', generation=1, action='initial-action')
    original = dict(attempt=1, execution_generation=1, request_hash='a' * 64,
                    config_sha256='b' * 64, files_sha256={'input': 'c' * 64},
                    recovery_context=old_context)
    run_dir = str(tmp_path / 'native-run')
    contract = dict(identity=dict(project='synthetic', batch='synthetic', run_id=aid + '-a1'),
                    paths=dict(run_dir=run_dir, fastq_upload_uri='obs://synthetic/input',
                               result_upload_uri='obs://synthetic/result'),
                    kubernetes=dict(namespace='test', master_job='master', cleanup_job='cleanup',
                                    reset_job='reset', repair_job='repair'))
    config = dict(kubernetes=dict(namespace='test'),
                  obs=dict(obsutil_bin='synthetic', config_file='synthetic'))
    manifest = dict(kind='Job', metadata=dict(name='master', namespace='test',
                    labels={'cce.biosan.cn/run-id': 'synthetic-run'}),
                    spec=dict(template=dict(spec=dict(containers=[dict(name='main')]))))
    (bundle / 'BATCH_RUNTIME.yaml').write_text(yaml.safe_dump(contract))
    (bundle / 'master-job.yaml').write_text(yaml.safe_dump(manifest))
    binding = dict(schema_version='gatk-runtime.batch-binding.v1' if pipeline == 'gatk' else 'wgs',
                   analysis_id=aid, attempt=1, run_id=aid + '-a1', cce_bundle=str(bundle),
                   namespace='test', master_job='master', run_label='synthetic-run')
    binding_path = bundle.parent / 'batch-binding.json'
    binding_path.write_text(json.dumps(binding))
    abort = dict(schema='cce-pipeline.initial-submission-abort.v1', bundle=str(bundle),
                 binding=original, run_id=aid + '-a1', job_name='master', job_uid='old-uid',
                 pending_owner=dict(generation=1, action='initial-action', master_uid=''),
                 intent_deadline_epoch=100.0, handoff_deadline_epoch=100.02,
                 submission_journal=dict(state='created', job_uid='old-uid'),
                 submission_journal_sha256='d' * 64, dispatch_proof=dict(stderr_path='synthetic'),
                 files_sha256=dict(stderr_path='e' * 64))
    evidence_path = tmp_path / 'verified-native-abort.json'
    evidence_path.write_text(json.dumps(abort))
    state = SimpleNamespace(job=None, pods=[], observations=[], proofs=[], native_reads=0,
                            authorizations=[], maintenance_reads=0, obs_reads=0, advanced=None)

    def query(cfg, kind, *args, **kwargs):
        if kind == 'job':
            if args[0] != 'master':
                state.maintenance_reads += 1
                return None
            return copy.deepcopy(state.job)
        assert kind in {'jobs', 'pods'}
        items = ([copy.deepcopy(state.job)] if state.job is not None else []) if kind == 'jobs' else copy.deepcopy(state.pods)
        if args and args[0] == '-l':
            items = [item for item in items if item['metadata'].get('labels', {}).get(
                'cce.biosan.cn/run-id') == 'synthetic-run']
        return dict(kind='JobList' if kind == 'jobs' else 'PodList', metadata={}, items=items)

    def native_abort(selected, bound, *, submission_journal, dispatch_proof):
        assert selected == bundle and bound == contract
        assert submission_journal == abort['submission_journal']
        assert dispatch_proof == abort['dispatch_proof']
        state.native_reads += 1
        # The producer boundary is deliberately read again, not caller boolean authority.
        return json.loads(evidence_path.read_bytes())

    def forbidden_final(*args, **kwargs):
        raise AssertionError('initial abort must not consume or manufacture compute FINAL')

    def authorize(facts):
        state.authorizations.append(copy.deepcopy(facts))
        assert facts['context'] == context and facts['old_job_uid'] == 'old-uid'
        assert facts['native_directory'] == run_dir and facts['config_digest'] == 'b' * 64
        return dict(writers_protocol=2, dispatcher_inactive=True, recovery_allowed=True,
                    native_directory=run_dir, canonical_directory='/storage/synthetic/project')

    def lock_identity(bound, lock_context):
        assert lock_context['canonical_directory'] == '/storage/synthetic/project'
        return 'synthetic-lock', {}, {}

    def verify_lock(current, operation, facts):
        expected = (abort['pending_owner'] if operation == 'takeover' else
                    dict(generation=2, action='new-action', master_uid=''))
        assert current['owner'] == expected
        assert 'terminal' not in facts and facts['initial_abort'] == abort
        return dict(object_uid='lock-uid', resource_version='1', identity={}, owner=expected)

    def claim(bound, cfg, *, lock_context, journal, save_journal, verify):
        operation = 'bind' if lock_context['master_uid'] else 'takeover'
        current = dict(owner=abort['pending_owner'] if operation == 'takeover' else
                       dict(generation=2, action='new-action', master_uid=''))
        state.proofs.append((operation, verify(current, operation)))

    def obs(**kwargs):
        state.obs_reads += 1
        return dict(result_count=0)

    runtime = SimpleNamespace(_handoff_binding=lambda *a: copy.deepcopy(original),
        _validate_recovery_context=lambda *a: None, _validate_platform_execution=lambda *a: None,
        _initial_submission_abort_evidence=native_abort, _recovery_final_evidence=forbidden_final,
        _directory_lock_identity=lock_identity, _claim_batch_lock=claim, _recovery_query=query,
        _recovery_encoded=lambda value: (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode(),
        _load=lambda *a: (contract, config, [SimpleNamespace(inspect_reset_obs=obs)]),
        _kubectl_json=query, _require_no_active_workers=lambda *a: None,
        _create_job_from_path=lambda *a: None, _wait_pod=lambda *a: None, _run=lambda *a: None,
        _kubectl=lambda *a: None, _write_master_handoff=lambda *a: None,
        _prepare_worker_manifest=lambda *a: None)
    cap = inventory.RecoveryCapability(bundle=bundle, expected_job_uid='old-uid', context=context,
        authorize=authorize, verify_lock=verify_lock, initial_abort=abort)
    cap.bind(runtime, contract, config, run_label='synthetic-run', pipeline=pipeline,
             analysis_id=aid, attempt=1, action='new-action')
    monkeypatch.setenv('GATK_RUNTIME_REQUEST_ROOT', str(request_root))
    return cap, runtime, state, abort, evidence_path, binding, binding_path, control


def test_initial_abort_inspect_claim_and_reread_never_invent_compute_final(initial_capability):
    cap, runtime, state, abort, evidence_path, *_ = initial_capability
    observed = cap.inspect()
    assert observed['initial_abort'] == abort and 'terminal' not in observed and 'snapshot' not in observed
    assert observed['observation']['master'] is None
    assert cap.lock_context()['generation'] == 2
    cap.claim({}, lambda value: None)
    takeover = state.proofs[-1][1]
    assert takeover['master_state'] == 'INITIAL_ABORTED' and takeover['initial_abort'] == abort
    assert takeover['evidence_sha256'] == hashlib.sha256(runtime._recovery_encoded(abort)).hexdigest()
    state.job = dict(kind='Job', metadata=dict(uid='new-uid', annotations={
        'cce-pipeline/recovery-context': json.dumps(cap.context, sort_keys=True),
        'cce-pipeline/execution-generation': '2'}), status=dict(active=1))
    cap.claim({}, lambda value: None, master_uid='new-uid')
    bound = state.proofs[-1][1]
    assert bound['master_state'] == 'ACTIVE' and bound['bound_master_uid'] == 'new-uid'
    assert 'initial_abort' not in bound
    assert state.native_reads > 3
    changed = copy.deepcopy(abort)
    changed['files_sha256']['stderr_path'] = 'f' * 64
    evidence_path.write_text(json.dumps(changed))
    with pytest.raises((ValueError, RuntimeError)):
        cap.lock_context()


@pytest.mark.parametrize('initial_capability', ['wgs', 'gatk'], indirect=True)
def test_existing_resume_forwards_initial_abort_and_keeps_independent_check(initial_capability):
    cap, runtime, state, abort, _, binding, binding_path, control = initial_capability

    def advance(bundle, contract, config, **kwargs):
        assert kwargs['initial_abort'] == abort and 'compute_deadline' not in kwargs
        checked = kwargs['check']()
        assert checked['initial_abort'] == abort and 'terminal' not in checked
        assert checked['observation']['master'] is None
        kwargs['claim']({}, lambda value: None)
        state.advanced = True
        return dict(mode='ready', master_uid='old-uid', bundle=str(bundle))

    runtime._advance_recovery_view = advance
    if cap.context['pipeline'] == 'wgs':
        result = wgs_resume.resume_master(payload=dict(binding, stage='step2_master',
            resume_action_id='new-action', control_workdir=str(control)), binding=binding,
            runtime=runtime, recovery=cap)
    else:
        result = gatk_resume.resume(analysis_id=binding['analysis_id'], attempt=1,
            expected_job_uid='old-uid', expected_binding_sha256=hashlib.sha256(binding_path.read_bytes()).hexdigest(),
            expected_contract_sha256=hashlib.sha256((cap.bundle / 'BATCH_RUNTIME.yaml').read_bytes()).hexdigest(),
            execute=False, runtime=runtime, recovery=cap)
        assert state.maintenance_reads == 3 and state.obs_reads == 1
    assert result['mode'] == 'ready' and state.advanced is True


def test_successful_child_releases_lineage_with_bound_initial_abort_not_parent_final(initial_capability):
    cap, runtime, _, abort, _, *_ = initial_capability
    child = cap.bundle.parent / 'successful-child'
    child.mkdir()
    original_binding = runtime._handoff_binding(cap.bundle, cap.contract)
    child_binding = dict(original_binding, execution_generation=2, recovery_context=cap.context)
    runtime._handoff_binding = lambda path, bound: copy.deepcopy(
        original_binding if path == cap.bundle else child_binding)
    record = dict(original_binding, job_uid='old-uid', state='JOB_CREATED',
                  run_id=abort['run_id'], job_name='master')
    runtime._read_master_handoff = lambda *a: copy.deepcopy(record)
    abort_path = cap.bundle / 'INITIAL_SUBMISSION_ABORT.json'
    abort_path.write_bytes(runtime._recovery_encoded(abort))
    runtime._master_handoff_path = lambda parent, bound: parent / 'MASTER_HANDOFF.json'
    runtime._validate_initial_submission_abort = lambda value: runtime._initial_submission_abort_evidence(
        cap.bundle, cap.contract, submission_journal=value['submission_journal'],
        dispatch_proof=value['dispatch_proof'])
    final = dict(terminal=dict(state='SUCCEEDED'), snapshot=dict(schema_version=1,
        canonical_directory='/storage/synthetic/project', manifest='',
        master=dict(recovery_context=cap.context),
        phases=dict(preflight=dict(started=False), analysis=dict(started=False))))
    digest = hashlib.sha256(runtime._recovery_encoded(abort)).hexdigest()
    ancestor = inventory.InitialAbortAncestor(bundle=cap.bundle, initial_abort_sha256=digest)
    assert inventory.lineage_workers(runtime, cap.contract, child, final, (ancestor,)) == []
    changed = inventory.InitialAbortAncestor(bundle=cap.bundle, initial_abort_sha256='f' * 64)
    with pytest.raises((ValueError, RuntimeError)):
        inventory.lineage_workers(runtime, cap.contract, child, final, (changed,))


def test_initial_replay_accepts_only_journal_bound_replacement_and_rejects_old_or_changed(initial_capability):
    cap, runtime, state, abort, _, _, _, control = initial_capability
    destination = control / 'recovery-new-action' / 'view'
    destination.mkdir(parents=True)
    manifest = yaml.safe_load((cap.bundle / 'master-job.yaml').read_bytes())
    manifest['metadata']['annotations'] = {
        'cce-pipeline/recovery-context': json.dumps(cap.context, sort_keys=True),
        'cce-pipeline/execution-generation': '2',
    }
    (destination / 'master-job.yaml').write_text(yaml.safe_dump(manifest))
    original = runtime._handoff_binding(cap.bundle, cap.contract)
    replacement_binding = dict(original, execution_generation=2, recovery_context=cap.context)
    runtime._handoff_binding = lambda path, bound: copy.deepcopy(
        original if path == cap.bundle else replacement_binding)

    def prepared(source, target, bound, *, context, platform_execution=None):
        assert source == cap.bundle and target == destination and target.is_dir()
        assert context == cap.context and platform_execution == cap.platform_execution
        return target

    runtime._prepare_recovery_view = prepared
    runtime._master_create_job_matches = lambda view, bound, job: wgs_resume._subset(
        yaml.safe_load((view / 'master-job.yaml').read_bytes()), job)
    state.job = copy.deepcopy(manifest)
    state.job['metadata'].update(uid='new-uid', resourceVersion='2')
    state.job['status'] = dict(active=1)
    identity = dict(expected_job_uid='old-uid', context=copy.deepcopy(cap.context),
                    original=original, view=str(destination), recovery_kind='initial_abort',
                    initial_abort_sha256=hashlib.sha256(runtime._recovery_encoded(abort)).hexdigest())
    journal = dict(recovery_v2=identity, recovery_state='created', replacement_uid='new-uid')
    observed = cap.inspect(journal=journal, destination=destination)
    assert observed['observation']['master'] == state.job and 'terminal' not in observed
    journal['recovery_state'] = 'submitting'
    del journal['replacement_uid']
    assert cap.inspect(journal=journal, destination=destination)['observation']['master'] == state.job
    state.pods = [dict(kind='Pod', metadata=dict(name='old-orphan', uid='old-pod-uid',
        namespace='test', labels={'job-name': 'master'}, ownerReferences=[dict(
            controller=True, kind='Job', name='master', uid='old-uid')]),
        spec=dict(containers=[dict(name='main')]), status=dict(phase='Running'))]
    with pytest.raises((ValueError, RuntimeError)):
        cap.inspect(journal=journal, destination=destination)
    state.pods = []
    journal['recovery_v2']['context']['action'] = 'changed-action'
    with pytest.raises((ValueError, RuntimeError)):
        cap.inspect(journal=journal, destination=destination)
