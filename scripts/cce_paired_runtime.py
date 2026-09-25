"""Operator-pinned runtime selection shared by restricted WGS/GATK entries.

Absence of activation keeps legacy behavior. Invalid activation never falls
back to a frozen copy, and no request/environment field selects executable code.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
from contextlib import ExitStack, contextmanager, nullcontext, redirect_stdout
import io
import fcntl
import re
from types import SimpleNamespace

POLICY_PATH = Path('/etc/cce-pipeline/writers-v2.json')
TRUST_ROOT = Path('/etc/cce-pipeline')
TRUSTED_UID = 0
PLATFORM_SOURCE = Path(__file__).resolve()
COMMANDS = dict(step1_upload='step1-upload', step2_master='step2-run',
    step3_monitor='step3-status', step4_publish='step4-publish',
    step5_download='step5-download', step6_materialize='step6-materialize')


def _operator_path(path):
    path = Path(path)
    if not path.is_absolute():
        raise RuntimeError('paired runtime path must be absolute')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != TRUSTED_UID or info.st_mode & 0o022:
        raise RuntimeError('paired runtime files must be operator-owned')
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != TRUSTED_UID or info.st_mode & 0o022:
            raise RuntimeError('paired runtime ancestry must be operator-owned')
        if parent == TRUST_ROOT:
            break
    return path


def _pin(pin):
    if not isinstance(pin, dict) or set(pin) != {'path','sha256'}:
        raise RuntimeError('invalid paired runtime pin')
    path = _operator_path(pin['path'])
    if path.stat().st_size > 16*1024*1024 or hashlib.sha256(path.read_bytes()).hexdigest() != pin['sha256']:
        raise RuntimeError('paired runtime source pin changed')
    return path


def _operator_python(value):
    path = _operator_path(value)
    if not os.access(path, os.X_OK):
        raise RuntimeError('paired runtime Python is unavailable')
    return str(path)


def selected_runtime():
    try:
        POLICY_PATH.lstat()
    except FileNotFoundError:
        return None
    path = _operator_path(POLICY_PATH)
    if path.stat().st_size > 16*1024*1024:
        raise RuntimeError('paired runtime policy is too large')
    policy = json.loads(path.read_bytes())
    if (not isinstance(policy, dict) or policy.get('schema_version') != 2
            or set(policy.get('writers', {})) != {'cli','platform'}):
        raise RuntimeError('invalid paired runtime activation')
    source = _pin(policy['writers']['cli'])
    platform = _pin(policy['writers']['platform'])
    guard = _pin(policy.get('runtime_guard'))
    if platform != PLATFORM_SOURCE or guard != source.with_name('cce_writer_guard.py'):
        raise RuntimeError('unpaired platform or guard entry')
    return source, _operator_python(policy['operator_python'])


def stage_command(bundle, stage, *arguments, payload=None, gate=None, pipeline=None):
    if stage not in COMMANDS:
        return None  # Prepare/Step7/maintenance remain outside this rollout.
    selected = selected_runtime()
    if selected is None:
        return None
    source, python = selected
    if payload is not None and stage in {'step4_publish','step5_download','step6_materialize'}:
        if arguments:
            raise RuntimeError('registered downstream does not accept native command overrides')
        _selected_registered(payload, binding=gate._load_binding(payload), gate=gate, pipeline=pipeline,
            operation=lambda *args:None)
        return [python, str(PLATFORM_SOURCE), '--registered-stage', pipeline,
            payload['analysis_id'], str(payload['attempt']), stage, payload['execution_id'],
            str(payload['generation']), payload['request_hash']]
    return [python, str(source), COMMANDS[stage], '--bundle', str(bundle), *arguments]


def run_registered_stage(arguments):
    """Child process resolves its own registered request; no view path is an arg."""
    if len(arguments) != 7:
        raise RuntimeError('registered downstream identity required')
    pipeline, analysis_id, attempt, stage, execution_id, generation, digest = arguments
    if (pipeline not in {'wgs','gatk'} or stage not in {'step4_publish','step5_download','step6_materialize'}
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', analysis_id)
            or not attempt.isdigit() or int(attempt) < 1 or not generation.isdigit() or int(generation) < 1):
        raise RuntimeError('invalid registered downstream identity')
    if __package__:
        from . import wgs_runtime_gate, gatk_runtime_gate
    else:
        import wgs_runtime_gate, gatk_runtime_gate
    gate = wgs_runtime_gate if pipeline == 'wgs' else gatk_runtime_gate
    path = gate._request_path(analysis_id, int(attempt), stage)
    payload = json.loads(_read_registered(path))
    expected = dict(analysis_id=analysis_id, attempt=int(attempt), stage=stage,
        execution_id=execution_id, generation=int(generation), request_hash=digest)
    if any(payload.get(k) != v for k,v in expected.items()):
        raise RuntimeError('registered downstream was superseded before execution')
    result = downstream_registered(payload, binding=gate._load_binding(payload), gate=gate, pipeline=pipeline,
        materialize=gate._materialize_to_approved_root if pipeline == 'gatk' else None)
    if result is None:
        raise RuntimeError('paired runtime activation disappeared before execution')


def load_runtime():
    selected = selected_runtime()
    if selected is None:
        return None
    source, _ = selected
    name = '_cce_operator_paired_runtime'
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    module._operator_paired_activation = True
    return module


def _read_registered(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise RuntimeError('registered evidence must be a regular file')
        raw = stream.read(16*1024*1024+1)
    if len(raw) > 16*1024*1024:
        raise RuntimeError('registered evidence is too large')
    return raw


def _registered_request(payload, gate, pipeline):
    path = gate._request_path(payload['analysis_id'], payload['attempt'], payload['stage'])
    raw = _read_registered(path)
    registered = json.loads(raw)
    public = {k:v for k,v in payload.items() if not k.startswith('_') and k != 'resume_master_uid'}
    digest = _request_digest(registered,pipeline)
    if registered != public or digest != registered.get('request_hash'):
        raise RuntimeError('registered recovery request changed or hash differs')
    if pipeline == 'wgs' and Path(registered['control_workdir']) != path.parent:
        raise RuntimeError('recovery journal must belong to registered request scope')
    return path, raw


def _request_digest(registered,pipeline):
    excluded = {'request_hash'} if pipeline == 'gatk' else {
        'execution_id', 'generation', 'request_hash', 'predecessor_execution_id',
        'predecessor_generation', 'predecessor_receipt_hash'}
    return hashlib.sha256(json.dumps({k:v for k,v in registered.items() if k not in excluded},
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@contextmanager
def _exclusive(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def _inactive_dispatcher(path, gate, pipeline):
    """A free lock/dead parent alone is not terminal dispatcher evidence."""
    worker = path.with_suffix('.worker.json' if pipeline == 'wgs' else '.worker.state.json')
    status = path.with_suffix('.status.json')
    if not worker.exists() and not status.exists():
        return  # Registered but never dispatched, or no request yet.
    if not worker.exists() or not status.exists() or not path.exists():
        raise RuntimeError('other dispatcher lacks terminal evidence')
    state, receipt, request = [json.loads(_read_registered(p)) for p in (worker, status, path)]
    keys = ('analysis_id', 'attempt', 'stage', 'generation', 'execution_id', 'request_hash')
    if (request.get('orchestration_contract_version') != 2
            or any(not request.get(k) or state.get(k) != request[k] or receipt.get(k) != request[k] for k in keys)
            or receipt.get('status') not in {'success', 'succeeded', 'complete', 'failed', 'canceled'}):
        raise RuntimeError('other dispatcher terminal identity is incomplete')
    if pipeline == 'gatk':
        process = state.get('process')
        if (state.get('schema_version') != 'gatk-runtime.dispatcher.v1'
                or state.get('state') != 'finished'
                or (process and gate._process_identity(process['pid']) == process)):
            raise RuntimeError('other dispatcher is active or uncertain')
    elif (not all(state.get(k) for k in ('pid', 'boot_id', 'process_start_time'))
            or gate._process_matches(state) or gate._process_matches(state.get('reattach') or {})):
        raise RuntimeError('other dispatcher is active or uncertain')


def _exported_master(runtime, bundle, selected, contract, platform):
    record = runtime._read_master_handoff(selected, contract)
    current = runtime._handoff_binding(selected, contract)
    original = runtime._handoff_binding(bundle, contract)
    if (not record or record.get('state') != 'START_CONFIRMED' or not record.get('pod_uid')
            or any(record.get(k) != v for k,v in current.items())
            or current.get('platform_execution') != platform
            or any(current[k] != original[k] for k in ('attempt','files_sha256','config_sha256'))):
        raise RuntimeError('selected Master confirmation differs from registered inputs')
    native = {k:record[k] for k in ('project','batch','run_id','job_name','job_uid','pod_uid',
        'attempt','execution_generation','request_hash','config_sha256','manifest_sha256',
        'files_sha256','deadline_epoch','recovery_context')}
    native['namespace'] = contract['kubernetes']['namespace']
    return dict(schema_version=2,platform_execution=platform,native=native,
        source_bundle=str(bundle),selected_bundle=str(selected))


def _initial_job_uid(selected,job,journal):
    if not job or not job.get('metadata',{}).get('uid') or job['metadata'].get('deletionTimestamp'):
        raise RuntimeError('initial CREATE outcome requires reconciliation')
    from yaml import safe_load
    expected=safe_load((selected/'master-job.yaml').read_bytes())
    def subset(a,b):
        if isinstance(a,dict):return isinstance(b,dict) and all(k in b and subset(v,b[k]) for k,v in a.items())
        if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(subset(x,y) for x,y in zip(a,b))
        return type(a) is type(b) and a==b
    if not subset(expected,job) or journal.get('job_uid') not in (None,job['metadata']['uid']):
        raise RuntimeError('initial Master differs from submitted manifest')
    return job['metadata']['uid']


def submit_registered(payload, *, binding, gate, pipeline):
    """Initial Step2, independently bound without editing the prepared bundle."""
    runtime = load_runtime()
    if runtime is None:
        return None
    if (pipeline not in {'wgs','gatk'} or payload.get('stage') != 'step2_master'
            or payload.get('orchestration_contract_version') != 2 or payload.get('resume_action_id')
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,192}', str(payload.get('execution_id') or ''))):
        raise RuntimeError('initial submission requires a registered Step2 execution')
    path, raw = _registered_request(payload, gate, pipeline)
    bundle = Path(binding['cce_bundle'])
    contract, config, modules = runtime._load(bundle, None)
    writer = runtime.writer_for_bundle(runtime, bundle, contract, config)
    if writer is None:
        raise RuntimeError('trusted per-run writer registration required')
    platform = dict(pipeline=pipeline, **{k:payload[k] for k in
        ('analysis_id','attempt','stage','execution_id','generation','request_hash')})
    action = payload['execution_id']
    if (writer.context.get('generation') != 1 or writer.context.get('action') != action
            or writer.context.get('analysis_id') != payload['analysis_id']
            or writer.context.get('pipeline') != pipeline):
        raise RuntimeError('initial operator owner differs from registered submission')
    journal_path = path.parent / ('submission-'+action+'.json')
    selected = journal_path.with_suffix('') / 'view'
    with writer.serialize():
        writer.validate()
        journal = json.loads(_read_registered(journal_path)) if journal_path.exists() else {}
        identity = dict(platform_execution=platform, source_bundle=str(bundle), selected_bundle=str(selected))
        if journal and journal.get('identity') != identity:
            raise RuntimeError('initial submission journal changed')
        selected = runtime._prepare_submission_view(bundle, selected, contract, platform_execution=platform)
        def require_job(job):
            return _initial_job_uid(selected,job,journal)
        def save():runtime._atomic_write_text(journal_path,json.dumps(journal,sort_keys=True)+'\n')
        if journal:
            job = runtime._recovery_query(config,'job',contract['kubernetes']['master_job'])
            uid = require_job(job)
            if not runtime._read_master_handoff(selected,contract):
                runtime._write_master_handoff(selected,contract,job_name=contract['kubernetes']['master_job'],
                    job_uid=uid,state='JOB_CREATED',deadline_epoch=journal['deadline_epoch'])
            # Binding the UID and persisting our receipt are separate writes.
            # Reconcile a crash between them against the exact CAS owner.
            name, lock_identity, pending = runtime._directory_lock_identity(contract,writer.context)
            current = runtime._recovery_query(config,'configmap',name)
            lock = json.loads(current['data']['lock']) if current else {}
            if (lock.get('state') == 'OWNED' and lock.get('identity') == lock_identity
                    and lock.get('owner') == {**pending,'master_uid':uid}):
                writer.context['master_uid'] = uid
        elif runtime._recovery_query(config,'job',contract['kubernetes']['master_job']) is not None:
            raise RuntimeError('unregistered existing Master cannot be adopted')
        create = runtime._create_job_from_path
        def submit(config_arg, manifest):
            if journal or Path(manifest) != selected/'master-job.yaml' or _read_registered(path) != raw:
                raise RuntimeError('initial CREATE is already transmitted or request changed')
            journal.update(identity=identity,state='submitting',deadline_epoch=runtime.time.time()+600)
            save()
            try:
                job = create(config_arg,manifest)
            except Exception as error:
                # Observe once; never send CREATE again on unknown outcome.
                job = runtime._recovery_query(config,'job',contract['kubernetes']['master_job'])
                if job is None:raise RuntimeError('initial CREATE outcome unknown; retain intent') from error
            uid = require_job(job)
            journal.update(state='created',job_uid=uid);save()
            runtime._write_master_handoff(selected,contract,job_name=contract['kubernetes']['master_job'],
                job_uid=uid,state='JOB_CREATED',deadline_epoch=journal['deadline_epoch'])
            return job
        writer.serialize = nullcontext
        runtime._create_job_from_path = submit
        try:
            runtime.step2(bundle,contract,config,modules,writer=writer,
                platform_execution=platform,submission_view=selected)
        finally:
            runtime._create_job_from_path = create
        exported = _exported_master(runtime,bundle,selected,contract,platform)
        uid = exported['native']['job_uid']
        writer.context['master_uid'] = uid
        _, identity_lock, owner = runtime._directory_lock_identity(contract,writer.context)
        def proof(current,operation):
            if operation != 'bind' or require_job(runtime._recovery_query(config,'job',contract['kubernetes']['master_job'])) != uid:
                raise RuntimeError('initial owner cannot be rebound')
            return dict(object_uid=current['metadata']['uid'],resource_version=current['metadata']['resourceVersion'],
                identity=identity_lock,owner={**owner,'master_uid':''},bound_master_uid=uid,master_state='ACTIVE',
                evidence_sha256=exported['native']['request_hash'])
        runtime._claim_batch_lock(contract,config,lock_context=writer.context,
            journal=writer.journal,save_journal=writer.save_journal,verify=proof)
        if _read_registered(path) != raw:raise RuntimeError('initial submission request superseded')
        journal.update(state='confirmed',job_uid=uid);save()
        if __package__:
            from .cce_recovery_inventory import VerifiedMasterResult
        else:
            from cce_recovery_inventory import VerifiedMasterResult
        return VerifiedMasterResult(dict(bundle=str(selected),master_uid=uid,mode='submitted'),exported,platform)


def _journal_views(root, pipeline, runtime, bundle, contract):
    """Locate native views by exact persisted identity, never by mtime/latest."""
    paths = sorted({p for pattern in ('submission-*.json', 'recovery-*.json' if pipeline == 'wgs' else 'resume-*.json')
                    for p in root.glob(pattern)})
    if len(paths) > 4096:
        raise RuntimeError('native journal inventory requires archival')
    frozen = runtime._handoff_binding(bundle, contract)
    for path in paths:
        value = json.loads(_read_registered(path))
        initial = path.name.startswith('submission-')
        if initial:
            platform = value.get('identity', {}).get('platform_execution', {})
            selected = path.with_suffix('')/'view'
            if value.get('state') not in {'submitting','created','confirmed'}:
                raise RuntimeError('invalid initial submission state')
            if value.get('identity') != dict(platform_execution=platform, source_bundle=str(bundle), selected_bundle=str(selected)):
                raise RuntimeError('initial view journal changed')
        else:
            platform = value.get('recovery_v2', {}).get('platform_execution', {})
            selected = path.with_suffix('')/'view' if pipeline == 'wgs' else path.with_name(path.stem+'-view')
            if not platform:
                continue
            if value['recovery_v2'].get('view') != str(selected):
                raise RuntimeError('recovery view journal changed')
        if (selected.resolve() != selected or platform.get('pipeline') != pipeline
                or platform.get('analysis_id') != root.parent.name or platform.get('attempt') != frozen['attempt']):
            raise RuntimeError('journal view outside registered attempt')
        yield path, value, selected, platform


def _recovery_source(root, payload, pipeline, runtime, bundle, contract, writer):
    views = list(_journal_views(root, pipeline, runtime, bundle, contract))
    replay = [v for v in views if v[1].get('recovery_v2', {}).get('context', {}).get('action') == payload['resume_action_id']]
    name, identity, _ = runtime._directory_lock_identity(contract, writer.context)
    current = runtime._recovery_query(writer.config, 'configmap', name)
    lock = json.loads(current['data']['lock']) if current else {}
    if lock.get('identity') != identity or lock.get('state') != 'OWNED':
        raise RuntimeError('registered directory lock missing or foreign')
    if replay:
        if len(replay) != 1:
            raise RuntimeError('ambiguous recovery journal')
        source = Path(replay[0][1].get('registered_source', str(bundle)))
        if source != bundle and source not in [v[2] for v in views]:
            raise RuntimeError('recovery source has no registered native journal')
    else:
        candidates = []
        for candidate in [bundle, *[v[2] for v in views if v[1].get('state') == 'confirmed' or v[1].get('recovery_state') == 'started']]:
            record = runtime._read_master_handoff(candidate, contract)
            if record and dict(generation=record['execution_generation'],action=record.get('recovery_context',{}).get('action'),
                    master_uid=record['job_uid']) == lock.get('owner'):
                candidates.append(candidate)
        if len(candidates) != 1:
            raise RuntimeError('current owner has no unique native submission')
        source = candidates[0]
    native = runtime._handoff_binding(source, contract)
    frozen = runtime._handoff_binding(bundle, contract)
    if source.resolve(strict=True) != source or any(native[k] != frozen[k] for k in ('attempt','files_sha256','config_sha256')):
        raise RuntimeError('recovery source differs from frozen inputs')
    record = runtime._read_master_handoff(source, contract)
    if not record or any(record.get(k) != v for k,v in native.items()):
        raise RuntimeError('native source handoff changed')
    if source != bundle:
        registered = [v for v in views if v[2] == source]
        if len(registered) != 1:
            raise RuntimeError('source native journal is ambiguous')
        _, saved, _, platform = registered[0]
        uid = saved.get('job_uid') if saved.get('state') == 'confirmed' else saved.get('replacement_uid')
        if native.get('platform_execution') != platform or record['job_uid'] != uid:
            raise RuntimeError('source differs from native journal binding')
    return source, record


def _source_history(root,pipeline,runtime,bundle,contract,source):
    views={v[2]:v[1] for v in _journal_views(root,pipeline,runtime,bundle,contract)}
    seen={source};history=[]
    while source!=bundle:
        if source not in views:
            raise RuntimeError('Master lineage is not registered')
        journal=views[source]
        parent=Path(journal.get('registered_source',str(bundle)))
        if parent in seen or (parent!=bundle and parent not in views):
            raise RuntimeError('Master lineage is cyclic or foreign')
        seen.add(parent)
        record=runtime._read_master_handoff(parent,contract)
        if not record:
            if parent==bundle and 'identity' in journal:break  # Initial prepared input, not a Master.
            raise RuntimeError('Master lineage lacks native evidence')
        history.append(parent);source=parent
    return tuple(history)


def _producer_registration(platform,gate,pipeline,analysis_id,attempt):
    if (platform.get('stage') not in {'step2_master','step3_monitor'} or platform.get('pipeline')!=pipeline
            or platform.get('analysis_id')!=analysis_id or platform.get('attempt')!=attempt):
        raise RuntimeError('foreign Master producer identity')
    producer=gate._request_path(analysis_id,attempt,platform['stage'])
    generation=platform['generation']
    if type(generation) is not int or generation<1:
        raise RuntimeError('invalid producer generation')
    registered=[]
    for candidate in (producer,producer.parent/'request-history'/platform['stage']/f'generation-{generation}.json'):
        if not candidate.exists():continue
        content=_read_registered(candidate);value=json.loads(content)
        if all(value.get(k)==v for k,v in platform.items() if k!='pipeline'):
            if _request_digest(value,pipeline)!=value.get('request_hash'):
                raise RuntimeError('producer registration hash changed')
            registered.append((candidate,content))
    if not registered:
        raise RuntimeError('selected producer has no authenticated registration')
    return tuple(registered)


def _reconcile_initial_intent(root,payload,gate,pipeline,runtime,bundle,contract,config,writer):
    """Resume a failed initial handoff with its original CREATE and deadline."""
    name,identity,_=runtime._directory_lock_identity(contract,writer.context)
    current=runtime._recovery_query(config,'configmap',name)
    lock=json.loads(current['data']['lock']) if current else {}
    if lock.get('state')!='OWNED' or lock.get('identity')!=identity:return
    for path,journal,selected,platform in _journal_views(root,pipeline,runtime,bundle,contract):
        if 'identity' not in journal or journal.get('state')=='confirmed':continue
        pending=dict(generation=1,action=platform['execution_id'],master_uid='')
        owner=lock.get('owner',{})
        if any(owner.get(k)!=pending[k] for k in ('generation','action')):continue
        evidence=_producer_registration(platform,gate,pipeline,payload['analysis_id'],payload['attempt'])
        _registered_request(payload,gate,pipeline)
        frozen=runtime._handoff_binding(bundle,contract)
        selected_binding=runtime._handoff_binding(selected,contract)
        if (selected_binding.get('platform_execution')!=platform
                or any(selected_binding[k]!=frozen[k] for k in ('attempt','files_sha256','config_sha256'))):
            raise RuntimeError('initial handoff differs from registered frozen inputs')
        uid=_initial_job_uid(selected,runtime._recovery_query(config,'job',contract['kubernetes']['master_job']),journal)
        if owner.get('master_uid') not in ('',uid):raise RuntimeError('initial directory owner changed')
        if not runtime._read_master_handoff(selected,contract):
            runtime._write_master_handoff(selected,contract,job_name=contract['kubernetes']['master_job'],
                job_uid=uid,state='JOB_CREATED',deadline_epoch=journal['deadline_epoch'])
        runtime._finish_master_handoff(selected,contract,config,uid)
        exported=_exported_master(runtime,bundle,selected,contract,platform)
        writer.context.update(generation=1,action=platform['execution_id'],master_uid=uid)
        def proof(current,operation):
            if operation!='bind':raise RuntimeError('initial reconciliation cannot replace an owner')
            _initial_job_uid(selected,runtime._recovery_query(config,'job',contract['kubernetes']['master_job']),journal)
            return dict(object_uid=current['metadata']['uid'],resource_version=current['metadata']['resourceVersion'],
                identity=identity,owner=pending,bound_master_uid=uid,master_state='ACTIVE',
                evidence_sha256=exported['native']['request_hash'])
        _registered_request(payload,gate,pipeline)
        if any(_read_registered(p)!=v for p,v in evidence):raise RuntimeError('initial producer registration changed')
        runtime._claim_batch_lock(contract,config,lock_context=writer.context,
            journal=writer.journal,save_journal=writer.save_journal,verify=proof)
        journal.update(state='confirmed',job_uid=uid)
        runtime._atomic_write_text(path,json.dumps(journal,sort_keys=True)+'\n')
        return


def _automatic_failure_evidence(payload, value, *, runtime, bundle, selected, contract, config,
        run_label, exported, request_root, pipeline):
    if payload['stage'] != 'step3_monitor' or value.get('master_state') != 'FAILED':
        return None
    if __package__:
        from .cce_recovery_failure import collect_failure_evidence
    else:
        from cce_recovery_failure import collect_failure_evidence
    try:
        return collect_failure_evidence(runtime=runtime,selected=selected,contract=contract,config=config,
            run_label=run_label,binding=exported,
            history_bundles=_source_history(request_root,pipeline,runtime,bundle,contract,selected))
    except (ValueError, RuntimeError, OSError, KeyError, TypeError):
        # Missing/mixed/unknown evidence is ineligible, not a reason to erase the
        # ordinary failed status or change the existing manual recovery path.
        return None


def _observe_registered_source(payload, binding, gate, pipeline, runtime, bundle, contract, config, modules, writer, operation=None,
        expected=None, evidence=()):
    """Reattach a new observer without relabelling the original Master producer."""
    path, raw = _registered_request(payload,gate,pipeline)
    with writer.serialize():
        writer.validate()
        if expected is None:
            source, record = _recovery_source(path.parent,payload,pipeline,runtime,bundle,contract,writer)
        else:
            matches=[v for v in _journal_views(path.parent,pipeline,runtime,bundle,contract)
                if str(v[2]) == expected.get('selected_bundle') and v[3] == expected.get('platform_execution')
                and (v[1].get('state') == 'confirmed' or v[1].get('recovery_state') == 'started')]
            if len(matches) != 1:
                raise RuntimeError('receipt has no unique confirmed native journal')
            journal_path,saved,source,_=matches[0]
            evidence=(*evidence,(journal_path,_read_registered(journal_path)))
            record=runtime._read_master_handoff(source,contract)
            if not record or record.get('job_uid') != (saved.get('job_uid') or saved.get('replacement_uid')):
                raise RuntimeError('receipt journal differs from native handoff')
        platform = runtime._handoff_binding(source,contract).get('platform_execution')
        if not platform:
            raise RuntimeError('unbound historical Master requires explicit migration')
        exported = _exported_master(runtime,bundle,source,contract,platform)
        if expected is not None and exported != expected:
            raise RuntimeError('receipt differs from selected native binding')
        # A reconnect is an observer, not a new producer. Its original request
        # may have been archived by the existing authenticated service.
        evidence=(*evidence,*_producer_registration(platform,gate,pipeline,payload['analysis_id'],payload['attempt']))
        writer.context.update(generation=record['execution_generation'],action=record['recovery_context']['action'],
            master_uid=record['job_uid'])
        name,identity,owner=runtime._directory_lock_identity(contract,writer.context)
        current=runtime._recovery_query(config,'configmap',name)
        lock=json.loads(current['data']['lock']) if current else {}
        released=lock.get('state')=='RELEASED' and payload['stage']=='step6_materialize'
        if (lock.get('schema_version')!=2 or (lock.get('state')!='OWNED' and not released)
                or lock.get('identity')!=identity or lock.get('owner')!=owner):
            raise RuntimeError('observed Master directory owner changed')
        writer.lifecycle_released=released
        writer.serialize = nullcontext
        if operation is None:
            output=io.StringIO()
            with redirect_stdout(output):
                runtime.step3(contract,config,modules,'json',bundle=bundle,writer=writer,
                    master_bundle=source,expected_master_uid=record['job_uid'])
            result=json.loads(output.getvalue())
        else:result=operation(runtime,bundle,source,record['job_uid'],contract,config,modules,writer)
        proof = _automatic_failure_evidence(payload,result or {},runtime=runtime,bundle=bundle,selected=source,
            contract=contract,config=config,run_label=binding['run_label'],exported=exported,
            request_root=path.parent,pipeline=pipeline)
        if _read_registered(path) != raw or any(_read_registered(p)!=v for p,v in evidence):
            raise RuntimeError('registered observer superseded')
        if __package__:
            from .cce_recovery_inventory import VerifiedMasterResult
        else:
            from cce_recovery_inventory import VerifiedMasterResult
        execution=dict(pipeline=pipeline,**{k:payload[k] for k in
            ('analysis_id','attempt','stage','execution_id','generation','request_hash')})
        payload['_cce_master_result']=VerifiedMasterResult(
            dict(bundle=str(source),master_uid=record['job_uid'],mode='observed'),exported,execution,failure_evidence=proof)
        return result


def resume_registered(payload, *, binding, gate, pipeline):
    """Internal restricted-worker entry; caller already holds its worker lock.

    The fixed operator policy and the authenticated spool are separate trust
    boundaries. Request flags cannot assert quiescence, choose code, or map an
    old lock. Locks remain held until the existing native recovery returns.
    """
    runtime = load_runtime()
    if runtime is None:
        return None
    if (pipeline not in {'wgs', 'gatk'} or payload.get('orchestration_contract_version') != 2
            or payload.get('stage') not in {'step2_master', 'step3_monitor'}
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(payload.get('resume_action_id') or ''))):
        raise RuntimeError('registered replacement requires Step2 or Step3 recovery')
    path, raw = _registered_request(payload, gate, pipeline)
    bundle = Path(binding['cce_bundle'])
    contract, config, modules = runtime._load(bundle, None)
    writer = runtime.writer_for_bundle(runtime, bundle, contract, config)
    if writer is None:
        raise RuntimeError('trusted per-run writer registration required')
    if __package__:
        from .cce_recovery_inventory import RecoveryCapability
        from .cce_recovery_deadline import deadline_epoch, monitor_wait
        from . import wgs_resume, gatk_resume
    else:
        from cce_recovery_inventory import RecoveryCapability
        from cce_recovery_deadline import deadline_epoch, monitor_wait
        import wgs_resume, gatk_resume
    monitor_wait(payload, 0)
    with ExitStack() as stack:
        # Exclude launches as well as execution. The current worker lock is
        # owned by the restricted gate, so it must not be acquired twice.
        paths = [gate._request_path(payload['analysis_id'], payload['attempt'], stage)
                 for stage in ('prepare', *COMMANDS, 'step7_cleanup')]
        for other in paths:
            stack.enter_context(_exclusive(other.with_suffix('.launch.lock')))
            if other != path:
                stack.enter_context(_exclusive(other.with_suffix('.worker.lock')))
                _inactive_dispatcher(other, gate, pipeline)
        stack.enter_context(writer.serialize())
        scope = writer.validate()
        _reconcile_initial_intent(path.parent,payload,gate,pipeline,runtime,bundle,contract,config,writer)
        source, record = _recovery_source(path.parent, payload, pipeline, runtime, bundle, contract, writer)
        if not isinstance(record, dict) or record.get('schema_version') != 2:
            raise RuntimeError('native Master handoff identity required')
        old_uid = record['job_uid']
        live = runtime._recovery_query(config,'job',contract['kubernetes']['master_job'])
        if live is not None and live.get('metadata',{}).get('uid') == old_uid:
            active, complete, failed = runtime._job_flags(live)
            if not failed and not live['metadata'].get('deletionTimestamp'):
                if not complete:
                    runtime._finish_master_handoff(source,contract,config,old_uid)
                else:
                    runtime._recovery_native_success(source,contract,old_uid)
                # Outer serialization is already held; observation revalidates ownership.
                writer.serialize = nullcontext
                _observe_registered_source(payload,binding,gate,pipeline,runtime,bundle,contract,config,modules,writer,
                    operation=lambda *args:None)
                return payload['_cce_master_result']
        terminal = runtime._recovery_final_evidence(source, contract, old_uid)['terminal']
        context = dict(pipeline=pipeline, analysis_id=payload['analysis_id'],
            execution_id=payload['execution_id'], generation=terminal['execution_generation']+1,
            action=payload['resume_action_id'])
        platform = {k:payload[k] for k in ('analysis_id', 'attempt', 'stage', 'execution_id', 'generation', 'request_hash')}
        platform['pipeline'] = pipeline
        name, identity, old_owner = runtime._directory_lock_identity(contract, writer.context)
        expected_owner = dict(generation=terminal['execution_generation'],
            action=terminal['recovery_context']['action'], master_uid=old_uid)
        if (identity['pipeline'] != pipeline
                or identity['analysis_id'] != payload['analysis_id']
                or identity['attempt'] != str(payload['attempt'])):
            raise RuntimeError('operator registration differs from native old owner')

        def authorize(facts):
            if _read_registered(path) != raw:
                raise RuntimeError('registered recovery request superseded')
            current_scope = writer.validate()
            if (current_scope != scope or facts['native_directory'] != scope['native_directory']
                    or facts['old_job_uid'] != old_uid or facts['config_digest'] != identity['config_digest']
                    or facts['run_id'] != identity['run_id'] or facts['context'] != context):
                raise RuntimeError('registered recovery identity changed')
            # A disappeared old lock cannot be treated as permission for a new claim.
            current = runtime._recovery_query(config, 'configmap', name)
            value = json.loads(current['data']['lock']) if current else {}
            if value.get('schema_version') != 2 or value.get('identity') != identity or value.get('state') != 'OWNED':
                raise RuntimeError('registered directory lock missing or foreign')
            owner = value.get('owner', {})
            if owner != expected_owner and (owner.get('generation') != context['generation']
                    or owner.get('action') != context['action']):
                raise RuntimeError('directory lock owner differs from recovery')
            if owner != expected_owner and owner.get('master_uid'):
                live = runtime._recovery_query(config, 'job', contract['kubernetes']['master_job'])
                metadata = (live or {}).get('metadata', {})
                if (metadata.get('uid') != owner['master_uid'] or metadata.get('deletionTimestamp')
                        or metadata.get('annotations', {}).get('cce-pipeline/recovery-context') != json.dumps(context, sort_keys=True)):
                    raise RuntimeError('replacement lock UID is not the registered Master')
            return dict(writers_protocol=2, dispatcher_inactive=True, recovery_allowed=True,
                native_directory=scope['native_directory'], canonical_directory=scope['canonical_directory'])

        def verify_lock(current, operation, facts):
            value = json.loads(current['data']['lock'])
            expected = expected_owner if operation == 'takeover' else dict(
                generation=context['generation'], action=context['action'], master_uid='')
            if (operation not in {'takeover', 'bind'} or value.get('identity') != identity
                    or value.get('owner') != expected):
                raise RuntimeError('lock transition does not match verified native owner')
            return dict(object_uid=current['metadata']['uid'], resource_version=current['metadata']['resourceVersion'],
                identity=identity, owner=expected)

        capability = RecoveryCapability(bundle=source, origin_bundle=bundle, expected_job_uid=old_uid, context=context,
            authorize=authorize, verify_lock=verify_lock, platform_execution=platform,
            compute_deadline=deadline_epoch(payload),
            history_bundles=_source_history(path.parent,pipeline,runtime,bundle,contract,source))
        if pipeline == 'wgs':
            result = wgs_resume.resume_master(payload=payload, binding=binding, runtime=runtime, recovery=capability)
        else:
            result = gatk_resume.resume(analysis_id=payload['analysis_id'], attempt=payload['attempt'],
                expected_job_uid=old_uid, expected_binding_sha256=hashlib.sha256(
                    _read_registered(bundle.parent/'batch-binding.json')).hexdigest(),
                expected_contract_sha256=hashlib.sha256(_read_registered(bundle/'BATCH_RUNTIME.yaml')).hexdigest(),
                execute=True, runtime=runtime, recovery=capability)
        if _read_registered(path) != raw:
            raise RuntimeError('registered recovery request superseded after native recovery')
        return result


def prepare_monitor_registered(payload, *, binding, gate, pipeline):
    """Only a new authenticated Step3 recovery action may replace a Master.

    Descendant Step3 of a Step2 action observes that submission; it cannot
    silently start a second replacement when the submitted Master fails.
    """
    if not payload.get('resume_action_id') or selected_runtime() is None:
        return
    _registered_request(payload, gate, pipeline)
    path = gate._request_path(payload['analysis_id'], payload['attempt'], 'step2_master')
    source = json.loads(_read_registered(path)) if path.exists() else {}
    if source.get('resume_action_id') == payload['resume_action_id']:
        _registered_request(source, gate, pipeline)
        return
    result = resume_registered(payload, binding=binding, gate=gate, pipeline=pipeline)
    payload['_cce_master_result'] = result


def reattach_registered(payload,previous,*,binding,gate,pipeline):
    """Revalidate a finished worker's selected producer before receipt archival."""
    runtime=load_runtime()
    if runtime is None:raise RuntimeError('paired reattachment requires its registered runtime')
    path,_=_registered_request(payload,gate,pipeline)
    status_path=path.with_suffix('.status.json');status_raw=_read_registered(status_path)
    if json.loads(status_raw)!=previous:raise RuntimeError('reattached status changed')
    expected=previous.get('cce_master_binding',{})
    if previous.get('cce_master_submit_execution_id')!=expected.get('platform_execution',{}).get('execution_id'):
        raise RuntimeError('reattached producer identity changed')
    bundle=Path(binding['cce_bundle']);contract,config,modules=runtime._load(bundle,None)
    writer=runtime.writer_for_bundle(runtime,bundle,contract,config)
    if writer is None:raise RuntimeError('reattached writer registration missing')
    _observe_registered_source(payload,binding,gate,pipeline,runtime,bundle,contract,config,modules,writer,
        operation=lambda *args:None,expected=expected,evidence=((status_path,status_raw),))


def probe_waiting_workers(payload, *, binding, gate, pipeline, generation, request_hash, nonce):
    """Read-only refresh of one failed observer; never rewrite its receipt."""
    if (payload.get('stage') != 'step3_monitor' or payload.get('generation') != generation
            or payload.get('request_hash') != request_hash
            or re.fullmatch('[0-9a-f]{32}', nonce) is None):
        raise ValueError('Worker probe identity differs')
    runtime = load_runtime()
    if runtime is None:
        raise RuntimeError('Worker probe requires registered paired runtime')
    path, _ = _registered_request(payload, gate, pipeline)
    status_path = path.with_suffix('.status.json')
    raw = _read_registered(status_path)
    previous = json.loads(raw)
    if (previous.get('status') != 'failed' or not previous.get('cce_recovery_evidence')
            or any(previous.get(k) != payload.get(k) for k in
                ('analysis_id','attempt','stage','execution_id','generation','request_hash'))):
        raise RuntimeError('Worker probe requires the exact failed receipt')
    expected = previous.get('cce_master_binding', {})
    if previous.get('cce_master_submit_execution_id') != expected.get('platform_execution', {}).get('execution_id'):
        raise RuntimeError('Worker probe producer differs')
    bundle = Path(binding['cce_bundle'])
    contract, config, modules = runtime._load(bundle, None)
    writer = runtime.writer_for_bundle(runtime, bundle, contract, config)
    if writer is None:
        raise RuntimeError('Worker probe writer registration missing')
    _observe_registered_source(payload,binding,gate,pipeline,runtime,bundle,contract,config,modules,writer,
        operation=lambda *args: {'master_state':'FAILED'}, expected=expected, evidence=((status_path,raw),))
    if __package__:
        from .cce_recovery_inventory import master_receipt_fields
    else:
        from cce_recovery_inventory import master_receipt_fields
    proof = master_receipt_fields(payload,pipeline=pipeline,details={}).get('cce_recovery_evidence')
    if proof is None:
        raise RuntimeError('Worker probe evidence is incomplete')
    return dict(nonce=nonce,execution_id=payload['execution_id'],generation=generation,
        request_hash=request_hash,cce_recovery_evidence=proof)


def worker_probe_command(arguments, *, gate, pipeline):
    """Fixed restricted command; all paths come from the registered request."""
    if (len(arguments) != 6 or arguments[0] != '--recovery-probe'
            or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', arguments[1]) is None
            or re.fullmatch(r'[1-9][0-9]{0,8}', arguments[2]) is None
            or re.fullmatch(r'[1-9][0-9]{0,8}', arguments[3]) is None
            or re.fullmatch(r'[0-9a-f]{64}', arguments[4]) is None
            or re.fullmatch(r'[0-9a-f]{32}', arguments[5]) is None):
        raise ValueError('invalid restricted Worker probe command')
    _, analysis_id, attempt, generation, request_hash, nonce = arguments
    if pipeline == 'wgs':
        payload = gate.load_request(analysis_id,int(attempt),'step3_monitor')
    else:
        _, payload = gate._load(analysis_id,int(attempt),'step3_monitor',int(generation))
    return probe_waiting_workers(payload,binding=gate._load_binding(payload),gate=gate,pipeline=pipeline,
        generation=int(generation),request_hash=request_hash,nonce=nonce)


def _predecessor(payload, gate, pipeline):
    stages = tuple(COMMANDS)
    previous = stages[stages.index(payload['stage']) - 1]
    path = gate._request_path(payload['analysis_id'], payload['attempt'], previous)
    raw = _read_registered(path)
    request = json.loads(raw)
    _registered_request(request, gate, pipeline)
    status_path = path.with_suffix('.status.json')
    status_raw = _read_registered(status_path)
    receipt = json.loads(status_raw)
    digest = hashlib.sha256(status_raw).hexdigest() if pipeline == 'wgs' else hashlib.sha256(
        json.dumps({k:v for k,v in receipt.items() if k != 'receipt_hash'},
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if (request.get('orchestration_contract_version') != 2
            or any(receipt.get(k) != request.get(k) for k in
                ('analysis_id','attempt','stage','execution_id','generation','request_hash'))
            or receipt.get('status') != 'success'
            or payload.get('predecessor_execution_id') != request.get('execution_id')
            or payload.get('predecessor_receipt_hash') != digest
            or (pipeline == 'gatk' and receipt.get('receipt_hash') != digest)):
        raise RuntimeError('selected stage predecessor is not the registered successful execution')
    return receipt, ((path,raw),(status_path,status_raw))


def monitor_registered(payload, *, binding, gate, pipeline):
    if payload.get('stage') != 'step3_monitor':
        raise RuntimeError('selected monitor requires Step3')
    return _selected_registered(payload, binding=binding, gate=gate, pipeline=pipeline)


def downstream_registered(payload, *, binding, gate, pipeline, materialize=None):
    if payload.get('stage') not in {'step4_publish','step5_download','step6_materialize'}:
        raise RuntimeError('selected downstream requires Step4-Step6')
    def execute(runtime, bundle, selected, uid, contract, config, modules, writer):
        args = SimpleNamespace(verify_existing=False, allow_unverified_manual=False)
        if payload['stage'] == 'step4_publish':
            runtime.step4(bundle, contract, config, modules, writer=writer,
                master_bundle=selected, expected_master_uid=uid)
        elif payload['stage'] == 'step5_download':
            runtime.step5(args, bundle, contract, config, modules, writer=writer,
                master_bundle=selected, expected_master_uid=uid)
        else:
            runtime._bound_downstream_master(bundle, selected, contract, config, uid)
            if not writer.lifecycle_released:
                if materialize is None:
                    runtime.step6(args, bundle, contract, modules, writer=writer)
                else:
                    with writer.enter(6):
                        materialize(payload)
            _release_registered_writer(payload, binding, gate, pipeline,
                runtime, bundle, selected, uid, contract, config, writer)
        return {'stage':payload['stage'], 'status':'success'}
    return _selected_registered(payload, binding=binding, gate=gate, pipeline=pipeline, operation=execute)


def _release_registered_writer(payload, binding, gate, pipeline,
        runtime, bundle, selected, uid, contract, config, writer):
    if __package__:
        from .cce_recovery_inventory import lineage_workers
        from .cce_recovery_workloads import probe_final_workloads
    else:
        from cce_recovery_inventory import lineage_workers
        from cce_recovery_workloads import probe_final_workloads
    with ExitStack() as locks:
        current_path, current_raw = _registered_request(payload, gate, pipeline)
        for stage in ('prepare', *COMMANDS, 'step7_cleanup'):
            path = gate._request_path(payload['analysis_id'], payload['attempt'], stage)
            locks.enter_context(_exclusive(path.with_suffix('.launch.lock')))
            if path != current_path:
                locks.enter_context(_exclusive(path.with_suffix('.worker.lock')))
                _inactive_dispatcher(path, gate, pipeline)

        def evidence():
            if _read_registered(current_path) != current_raw:
                raise RuntimeError('final writer request superseded')
            writer.validate()
            runtime._require_materialized(bundle, contract['identity'])
            value = runtime._recovery_final_evidence(selected, contract, uid)
            if value['terminal']['state'] != 'SUCCEEDED':
                raise RuntimeError('final writer requires native success')
            workers = lineage_workers(runtime,contract,selected,value,
                _source_history(current_path.parent,pipeline,runtime,bundle,contract,selected))
            probe_final_workloads(runtime=runtime, config=config,
                namespace=contract['kubernetes']['namespace'], run_label=binding['run_label'],
                master_job=contract['kubernetes']['master_job'], master_job_uid=uid,
                master_state='SUCCEEDED', workers=workers)
            return value['terminal']['submission_snapshot_sha256']

        evidence()  # Also required on an idempotent RELEASED replay.
        _, identity, owner = runtime._directory_lock_identity(contract, writer.context)
        def proof(current, operation):
            if operation != 'release':
                raise RuntimeError('final writer cannot acquire or take over a lock')
            return dict(object_uid=current['metadata']['uid'],resource_version=current['metadata']['resourceVersion'],
                identity=identity,owner=owner,evidence_sha256=evidence(),inventory_complete=True,
                workers_inactive=True,dispatcher_inactive=True,master_state='SUCCEEDED',protected_writes_complete=True)
        runtime._release_batch_lock(contract,config,lock_context=writer.context,
            journal=writer.journal,save_journal=writer.save_journal,verify=proof)


def _selected_registered(payload, *, binding, gate, pipeline, operation=None):
    """Reconstruct a selected Master in a new restricted monitor process.

    A receipt is a locator/checksum, not a capability. The registered producer,
    native journal, frozen input binding and current directory owner must agree.
    No replacement, takeover or missing-lock claim is performed by this reader.
    """
    runtime = load_runtime()
    if runtime is None:
        return None
    if (pipeline not in {'wgs', 'gatk'} or payload.get('orchestration_contract_version') != 2
            or payload.get('stage') not in {'step3_monitor','step4_publish','step5_download','step6_materialize'}):
        raise RuntimeError('selected stage requires registered Step3-Step6')
    path, raw = _registered_request(payload, gate, pipeline)
    bundle = Path(binding['cce_bundle'])
    contract, config, modules = runtime._load(bundle, None)
    writer = runtime.writer_for_bundle(runtime, bundle, contract, config)
    if writer is None:
        raise RuntimeError('trusted per-run writer registration required')
    source_path = gate._request_path(payload['analysis_id'], payload['attempt'], 'step2_master')
    source = json.loads(_read_registered(source_path)) if source_path.exists() else {}
    evidence = []
    direct = bool(payload['stage'] == 'step3_monitor' and payload.get('resume_action_id')
        and source.get('resume_action_id') != payload['resume_action_id'])
    downstream = payload['stage'] != 'step3_monitor'
    if downstream:
        previous, evidence = _predecessor(payload, gate, pipeline)
        submit = previous.get('cce_master_binding', {}).get('platform_execution', {})
        if submit.get('stage') not in {'step2_master','step3_monitor'}:
            raise RuntimeError('downstream has no verified Master submission identity')
        if previous.get('cce_master_submit_execution_id') != submit.get('execution_id'):
            raise RuntimeError('downstream producer identity changed')
        return _observe_registered_source(payload,binding,gate,pipeline,runtime,bundle,contract,config,modules,writer,
            operation,expected=previous['cce_master_binding'],evidence=evidence)
    if direct:
        source_path, source = path, json.loads(raw)
    _, source_raw = _registered_request(source, gate, pipeline)
    status_path = source_path.with_suffix('.status.json')
    status_raw = _read_registered(status_path) if not direct else None
    receipt = json.loads(status_raw) if status_raw is not None else {}
    keys = ('analysis_id', 'attempt', 'stage', 'execution_id', 'generation', 'request_hash')
    digest = hashlib.sha256(status_raw or b'').hexdigest() if pipeline == 'wgs' else hashlib.sha256(
        json.dumps({k:v for k,v in receipt.items() if k != 'receipt_hash'},
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    action = source.get('resume_action_id')
    initial = not action
    if (source.get('orchestration_contract_version') != 2
            or (not initial and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(action)))
            or any(source.get(k) != payload.get(k) for k in ('analysis_id', 'attempt'))
            or (not direct and (any(receipt.get(k) != source[k] for k in keys)
            or receipt.get('status') != 'success'
            or (not downstream and payload.get('predecessor_execution_id') != source['execution_id'])
            or (not downstream and payload.get('predecessor_receipt_hash') != digest)
            or (pipeline == 'gatk' and receipt.get('receipt_hash') != digest)))):
        raise RuntimeError('selected monitor predecessor is not the registered successful submit')
    if not direct and receipt.get('cce_master_submit_execution_id') != source['execution_id']:
        exported=receipt.get('cce_master_binding',{})
        if receipt.get('cce_master_submit_execution_id') != exported.get('platform_execution',{}).get('execution_id'):
            raise RuntimeError('observer receipt producer identity changed')
        return _observe_registered_source(payload,binding,gate,pipeline,runtime,bundle,contract,config,modules,writer,
            operation,expected=exported,evidence=((source_path,source_raw),(status_path,status_raw)))
    if direct and not any(v[1].get('recovery_v2',{}).get('context',{}).get('action') == action
            for v in _journal_views(path.parent,pipeline,runtime,bundle,contract)):
        return _observe_registered_source(payload,binding,gate,pipeline,runtime,bundle,contract,config,modules,writer,operation)
    if __package__:
        from .cce_recovery_inventory import VerifiedMasterResult
    else:
        from cce_recovery_inventory import VerifiedMasterResult
    with writer.serialize():
        writer.validate()
        original = runtime._handoff_binding(bundle, contract)
        if initial:
            action = source['execution_id']
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,192}', action):
                raise RuntimeError('invalid initial submit identity')
            journal_path = source_path.parent / ('submission-'+action+'.json')
            selected = journal_path.with_suffix('') / 'view'
        else:
            matches = [v for v in _journal_views(source_path.parent,pipeline,runtime,bundle,contract)
                if v[1].get('recovery_v2',{}).get('context',{}).get('action') == action]
            if len(matches) != 1:
                raise RuntimeError('selected Master journal is missing or ambiguous')
            journal_path, selected_journal, selected, _ = matches[0]
            parent = Path(selected_journal.get('registered_source',str(bundle)))
            allowed = [bundle, *[v[2] for v in _journal_views(source_path.parent,pipeline,runtime,bundle,contract)]]
            if parent not in allowed or parent.resolve(strict=True) != parent:
                raise RuntimeError('selected Master source is not registered')
            original = runtime._handoff_binding(parent,contract)
            old = runtime._read_master_handoff(parent,contract)
            if not old or any(old.get(k) != v for k,v in original.items()):
                raise RuntimeError('original Master handoff changed')
        if selected.resolve(strict=True) != selected:
            raise RuntimeError('selected Master view is not canonical')
        journal_raw = _read_registered(journal_path)
        journal = json.loads(journal_raw)
        platform = dict(pipeline=pipeline, **{k:source[k] for k in keys})
        context = dict(pipeline=pipeline, analysis_id=source['analysis_id'],
            execution_id=source['execution_id'], generation=1 if initial else original['execution_generation']+1, action=action)
        if initial:
            journal_matches = (journal.get('state') == 'confirmed' and journal.get('identity') == dict(
                platform_execution=platform,source_bundle=str(bundle),selected_bundle=str(selected)))
            journal_uid = journal.get('job_uid')
        else:
            expected = dict(expected_job_uid=old['job_uid'], context=context, original=original,
                view=str(selected), platform_execution=platform)
            journal_matches = journal.get('recovery_state') == 'started' and journal.get('recovery_v2') == expected
            journal_uid = journal.get('replacement_uid')
        selected_binding = runtime._handoff_binding(selected, contract)
        record = runtime._read_master_handoff(selected, contract)
        if (not journal_matches
                or not record or record.get('schema_version') != 2 or record.get('state') != 'START_CONFIRMED'
                or journal_uid != record.get('job_uid') or not record.get('pod_uid')
                or any(record.get(k) != v for k,v in selected_binding.items())
                or selected_binding.get('platform_execution') != platform
                or selected_binding.get('recovery_context') != context
                or any(selected_binding.get(k) != original[k] for k in ('attempt', 'files_sha256', 'config_sha256'))):
            raise RuntimeError('selected Master native journal/handoff changed')
        native = {k:record[k] for k in ('project', 'batch', 'run_id', 'job_name',
            'job_uid', 'pod_uid', 'attempt', 'execution_generation', 'request_hash',
            'config_sha256', 'manifest_sha256', 'files_sha256', 'deadline_epoch', 'recovery_context')}
        native['namespace'] = contract['kubernetes']['namespace']
        exported = dict(schema_version=2, platform_execution=platform, native=native,
            source_bundle=str(bundle), selected_bundle=str(selected))
        if not direct and (receipt.get('cce_master_binding') != exported
                or receipt.get('cce_master_submit_execution_id') != source['execution_id']):
            raise RuntimeError('selected Master receipt differs from native binding')
        if downstream and (previous.get('cce_master_binding') != exported
                or previous.get('cce_master_submit_execution_id') != source['execution_id']):
            raise RuntimeError('downstream predecessor changed selected Master')
        writer.context.update(generation=context['generation'], action=action, master_uid=record['job_uid'])
        name, identity, owner = runtime._directory_lock_identity(contract, writer.context)
        current = runtime._recovery_query(config, 'configmap', name)
        lock = json.loads(current['data']['lock']) if current else {}
        released = lock.get('state') == 'RELEASED' and payload['stage'] == 'step6_materialize'
        if (lock.get('schema_version') != 2 or (lock.get('state') != 'OWNED' and not released)
                or lock.get('identity') != identity or lock.get('owner') != owner):
            raise RuntimeError('selected Master directory owner changed or missing')
        writer.lifecycle_released = released
        # Already serialized; native protected_stage still validates and checks
        # the exact new owner. It cannot take over another generation.
        writer.serialize = nullcontext
        if operation is None:
            output = io.StringIO()
            with redirect_stdout(output):
                runtime.step3(contract, config, modules, 'json', bundle=bundle, writer=writer,
                    master_bundle=selected, expected_master_uid=record['job_uid'])
            value = json.loads(output.getvalue())
        else:
            value = operation(runtime,bundle,selected,record['job_uid'],contract,config,modules,writer)
        proof = _automatic_failure_evidence(payload,value,runtime=runtime,bundle=bundle,selected=selected,
            contract=contract,config=config,run_label=binding['run_label'],exported=exported,
            request_root=path.parent,pipeline=pipeline)
        if any(content is not None and _read_registered(p) != content for p,content in [
                (path,raw), (source_path,source_raw), (status_path,status_raw), (journal_path,journal_raw), *evidence]):
            raise RuntimeError('selected monitor evidence superseded during observation')
        execution = dict(pipeline=pipeline, **{k:payload[k] for k in keys})
        payload['_cce_master_result'] = VerifiedMasterResult(
            dict(bundle=str(selected), master_uid=record['job_uid'], mode='observed'), exported, execution,failure_evidence=proof)
        return value


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != '--registered-stage':
        raise SystemExit('registered stage entry only')
    run_registered_stage(sys.argv[2:])
