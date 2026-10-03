"""Paired consumer of fixed native abort/advance bytes; cloud transport synthetic."""
import copy
import hashlib
import json

import pytest
import yaml

from test_initial_submission_abort import aborted, frozen_sources, recovery as native_recovery
from test_recovery_view import view_inputs
from test_master_handoff import handoff
from cce_pipeline.assets import cce_batch_runtime as runtime
from scripts.cce_recovery_inventory import RecoveryCapability, InitialAbortAncestor, lineage_workers
from scripts.cce_recovery_workloads import probe_final_workloads


def test_real_native_abort_advances_once_and_remains_noncompute_ancestor(native_recovery, monkeypatch):
    h, source, destination, state, abort, _ = native_recovery
    original = runtime._handoff_binding(source, h.contract)
    context = dict(pipeline='wgs', analysis_id='analysis', execution_id='exec-next',
                   generation=2, action='resume-next')
    platform = dict(original['platform_execution'], execution_id='exec-next',
                    generation=2, request_hash='b' * 64)
    label = yaml.safe_load((source/'master-job.yaml').read_bytes())['metadata']['labels']['cce.biosan.cn/run-id']
    canonical = '/storage/synthetic/project'
    native_directory = h.contract['paths']['run_dir']
    lock_context = dict(writers_protocol=2, canonical_directory=canonical,
        pipeline='wgs', analysis_id='analysis', attempt='1', run_id=abort['run_id'],
        config_digest=original['config_sha256'], **abort['pending_owner'])
    _, identity, _ = runtime._directory_lock_identity(h.contract, lock_context)
    cm = dict(metadata=dict(uid='synthetic-lock', resourceVersion='1'),
        data=dict(lock=json.dumps(dict(schema_version=2, identity=identity,
                                      state='OWNED', owner=abort['pending_owner']))))
    transport_query = runtime._recovery_query
    state['pods'] = []

    def query(config, kind, *args, **options):
        if kind == 'job':
            return transport_query(config, kind, *args, **options)
        if kind == 'configmap':
            return copy.deepcopy(cm)
        assert kind in {'jobs', 'pods'}
        items = ([state['job']] if state['job'] is not None else []) if kind == 'jobs' else state['pods']
        return dict(kind='JobList' if kind == 'jobs' else 'PodList', metadata={}, items=copy.deepcopy(items))

    def create(config, path):
        assert state['journal']['recovery_state']=='submitting'
        state['creates']+=1
        state['job']=yaml.safe_load(path.read_bytes())
        state['job']['metadata'].update(uid='master-new',resourceVersion='new-rv')
        h.pod['metadata']['ownerReferences'][0]['uid']='master-new'
        state['job']['status'] = dict(active=1, conditions=[])
        return copy.deepcopy(state['job'])

    def authorize(facts):
        owner = json.loads(cm['data']['lock'])['owner']
        assert owner == abort['pending_owner'] or (owner['generation'], owner['action']) == (2, 'resume-next')
        assert facts['native_directory'] == native_directory and facts['context'] == context
        return dict(writers_protocol=2, dispatcher_inactive=True, recovery_allowed=True,
                    native_directory=native_directory, canonical_directory=canonical)

    def verify_lock(current, operation, facts):
        expected = abort['pending_owner'] if operation == 'takeover' else dict(
            generation=2, action='resume-next', master_uid='')
        assert json.loads(current['data']['lock'])['owner'] == expected
        return dict(object_uid=current['metadata']['uid'],
                    resource_version=current['metadata']['resourceVersion'], identity=identity, owner=expected)

    def claim(contract, config, *, lock_context, journal, save_journal, verify):
        operation = 'bind' if lock_context['master_uid'] else 'takeover'
        desired={k:lock_context[k] for k in ('generation','action','master_uid')}
        value=json.loads(cm['data']['lock'])
        if value['owner']==desired:
            return  # Native claim also preserves an already identical owner.
        # The network CAS is synthetic; native owner/abort proof validation is real.
        runtime._lock_proof(cm, identity, operation, verify, bound_uid=lock_context['master_uid'] or None)
        value['owner']=desired
        cm['data']['lock'] = json.dumps(value)
        cm['metadata']['resourceVersion'] = str(int(cm['metadata']['resourceVersion']) + 1)

    monkeypatch.setattr(runtime, '_recovery_query', query)
    monkeypatch.setattr(runtime, '_create_job_from_path', create)
    monkeypatch.setattr(runtime, '_claim_batch_lock', claim)
    cap = RecoveryCapability(bundle=source, origin_bundle=h.bundle, expected_job_uid='master-old',
        context=context, authorize=authorize, verify_lock=verify_lock,
        platform_execution=platform, initial_abort=abort)
    cap.bind(runtime, h.contract, h.config, run_label=label, pipeline='wgs',
             analysis_id='analysis', attempt=1, action='resume-next')
    before = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
    journal = state['journal']
    result = runtime._advance_recovery_view(source, h.contract, h.config, context=context,
        expected_job_uid='master-old', destination=destination, journal=journal,
        save_journal=lambda value: None,
        check=lambda: cap.inspect(journal=journal, destination=destination),
        claim=cap.claim, authorize=cap._authorized, platform_execution=platform, initial_abort=abort)
    assert result['master_uid'] == 'master-new'
    assert runtime._read_master_handoff(destination, h.contract)['state'] == 'START_CONFIRMED'
    assert (state['creates'], state['starts']) == (1, 1)
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert journal['recovery_v2']['initial_abort_sha256'] == hashlib.sha256(runtime._recovery_encoded(abort)).hexdigest()

    # Reconstruct a created replay (START already confirmed) through the exact
    # live replacement. The real handoff checks must not send START again.
    journal['recovery_state'] = 'created'
    runtime._advance_recovery_view(source, h.contract, h.config, context=context,
        expected_job_uid='master-old', destination=destination, journal=journal,
        save_journal=lambda value: None,
        check=lambda: cap.inspect(journal=journal, destination=destination),
        claim=cap.claim, authorize=cap._authorized, platform_execution=platform, initial_abort=abort)
    assert (state['creates'], state['starts']) == (1, 1)

    # Synthetic completed-child snapshot exercises the Step6 ancestor reader;
    # old initial abort is native revalidated, never promoted to compute FINAL.
    final = dict(terminal=dict(state='SUCCEEDED'), snapshot=dict(schema_version=1,
        canonical_directory=canonical, manifest='', master=dict(recovery_context=context),
        phases=dict(preflight=dict(started=False), analysis=dict(started=False))))
    ancestor = InitialAbortAncestor(source, journal['recovery_v2']['initial_abort_sha256'])
    workers = lineage_workers(runtime, h.contract, destination, final, (ancestor,))
    assert workers == []
    state['job'] = None
    assert probe_final_workloads(runtime=runtime, config=h.config,
        namespace=h.contract['kubernetes']['namespace'], run_label=label,
        master_job=h.contract['kubernetes']['master_job'], master_job_uid='master-new',
        master_state='SUCCEEDED', workers=workers)['workers_inactive'] is True
    old_pod = copy.deepcopy(h.pod)
    old_pod['metadata']['ownerReferences'][0]['uid'] = 'master-old'
    state['pods'] = [old_pod]
    with pytest.raises(ValueError):
        probe_final_workloads(runtime=runtime, config=h.config,
            namespace=h.contract['kubernetes']['namespace'], run_label=label,
            master_job=h.contract['kubernetes']['master_job'], master_job_uid='master-new',
            master_state='SUCCEEDED', workers=workers)
