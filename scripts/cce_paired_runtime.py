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


def stage_command(bundle, stage, *arguments):
    if stage not in COMMANDS:
        return None  # Prepare/Step7/maintenance remain outside this rollout.
    selected = selected_runtime()
    if selected is None:
        return None
    source, python = selected
    return [python, str(source), COMMANDS[stage], '--bundle', str(bundle), *arguments]


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
    excluded = {'request_hash'} if pipeline == 'gatk' else {
        'execution_id', 'generation', 'request_hash', 'predecessor_execution_id',
        'predecessor_generation', 'predecessor_receipt_hash'}
    digest = hashlib.sha256(json.dumps({k:v for k,v in registered.items() if k not in excluded},
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if registered != public or digest != registered.get('request_hash'):
        raise RuntimeError('registered recovery request changed or hash differs')
    if pipeline == 'wgs' and Path(registered['control_workdir']) != path.parent:
        raise RuntimeError('recovery journal must belong to registered request scope')
    return path, raw


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
            or payload.get('stage') != 'step2_master'
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(payload.get('resume_action_id') or ''))):
        raise RuntimeError('registered replacement requires Step2; selected Step3 continuation is not activated')
    path, raw = _registered_request(payload, gate, pipeline)
    bundle = Path(binding['cce_bundle'])
    contract, config, _ = runtime._load(bundle, None)
    writer = runtime.writer_for_bundle(runtime, bundle, contract, config)
    if writer is None:
        raise RuntimeError('trusted per-run writer registration required')
    if __package__:
        from .cce_recovery_inventory import RecoveryCapability
        from . import wgs_resume, gatk_resume
    else:
        from cce_recovery_inventory import RecoveryCapability
        import wgs_resume, gatk_resume
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
        record = runtime._read_master_handoff(bundle, contract)
        if not isinstance(record, dict) or record.get('schema_version') != 2:
            raise RuntimeError('native Master handoff identity required')
        old_uid = record['job_uid']
        terminal = runtime._recovery_final_evidence(bundle, contract, old_uid)['terminal']
        context = dict(pipeline=pipeline, analysis_id=payload['analysis_id'],
            execution_id=payload['execution_id'], generation=terminal['execution_generation']+1,
            action=payload['resume_action_id'])
        platform = {k:payload[k] for k in ('analysis_id', 'attempt', 'stage', 'execution_id', 'generation', 'request_hash')}
        platform['pipeline'] = pipeline
        name, identity, old_owner = runtime._directory_lock_identity(contract, writer.context)
        expected_owner = dict(generation=terminal['execution_generation'],
            action=terminal['recovery_context']['action'], master_uid=old_uid)
        if (old_owner != expected_owner or identity['pipeline'] != pipeline
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

        capability = RecoveryCapability(bundle=bundle, expected_job_uid=old_uid, context=context,
            authorize=authorize, verify_lock=verify_lock, platform_execution=platform)
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


def monitor_registered(payload, *, binding, gate, pipeline):
    """Reconstruct a selected Master in a new restricted monitor process.

    A receipt is a locator/checksum, not a capability. The registered producer,
    native journal, frozen input binding and current directory owner must agree.
    No replacement, takeover or missing-lock claim is performed by this reader.
    """
    runtime = load_runtime()
    if runtime is None:
        return None
    if (pipeline not in {'wgs', 'gatk'} or payload.get('orchestration_contract_version') != 2
            or payload.get('stage') != 'step3_monitor'):
        raise RuntimeError('selected monitor requires registered Step3')
    path, raw = _registered_request(payload, gate, pipeline)
    source_path = gate._request_path(payload['analysis_id'], payload['attempt'], 'step2_master')
    source = json.loads(_read_registered(source_path))
    _, source_raw = _registered_request(source, gate, pipeline)
    status_path = source_path.with_suffix('.status.json')
    status_raw = _read_registered(status_path)
    receipt = json.loads(status_raw)
    keys = ('analysis_id', 'attempt', 'stage', 'execution_id', 'generation', 'request_hash')
    digest = hashlib.sha256(status_raw).hexdigest() if pipeline == 'wgs' else hashlib.sha256(
        json.dumps({k:v for k,v in receipt.items() if k != 'receipt_hash'},
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    action = source.get('resume_action_id')
    if (source.get('orchestration_contract_version') != 2
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(action or ''))
            or any(receipt.get(k) != source[k] for k in keys)
            or any(source.get(k) != payload.get(k) for k in ('analysis_id', 'attempt'))
            or receipt.get('status') != 'success'
            or payload.get('predecessor_execution_id') != source['execution_id']
            or payload.get('predecessor_receipt_hash') != digest
            or (pipeline == 'gatk' and receipt.get('receipt_hash') != digest)):
        raise RuntimeError('selected monitor predecessor is not the registered successful submit')
    bundle = Path(binding['cce_bundle'])
    contract, config, modules = runtime._load(bundle, None)
    writer = runtime.writer_for_bundle(runtime, bundle, contract, config)
    if writer is None:
        raise RuntimeError('trusted per-run writer registration required')
    if __package__:
        from .cce_recovery_inventory import VerifiedMasterResult
    else:
        from cce_recovery_inventory import VerifiedMasterResult
    with writer.serialize():
        writer.validate()
        original = runtime._handoff_binding(bundle, contract)
        old = runtime._read_master_handoff(bundle, contract)
        if not old or any(old.get(k) != v for k,v in original.items()):
            raise RuntimeError('original Master handoff changed')
        journal_path = source_path.parent / (f'recovery-{action}.json' if pipeline == 'wgs'
            else f"resume-{old['job_uid']}.json")
        selected = journal_path.with_suffix('') / 'view' if pipeline == 'wgs' else (
            source_path.parent / f"resume-{old['job_uid']}-view")
        if selected.resolve(strict=True) != selected:
            raise RuntimeError('selected Master view is not canonical')
        journal_raw = _read_registered(journal_path)
        journal = json.loads(journal_raw)
        platform = dict(pipeline=pipeline, **{k:source[k] for k in keys})
        context = dict(pipeline=pipeline, analysis_id=source['analysis_id'],
            execution_id=source['execution_id'], generation=original['execution_generation']+1, action=action)
        expected = dict(expected_job_uid=old['job_uid'], context=context, original=original,
            view=str(selected), platform_execution=platform)
        selected_binding = runtime._handoff_binding(selected, contract)
        record = runtime._read_master_handoff(selected, contract)
        if (journal.get('recovery_state') != 'started' or journal.get('recovery_v2') != expected
                or not record or record.get('schema_version') != 2 or record.get('state') != 'START_CONFIRMED'
                or journal.get('replacement_uid') != record.get('job_uid') or not record.get('pod_uid')
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
        if (receipt.get('cce_master_binding') != exported
                or receipt.get('cce_master_submit_execution_id') != source['execution_id']):
            raise RuntimeError('selected Master receipt differs from native binding')
        writer.context.update(generation=context['generation'], action=action, master_uid=record['job_uid'])
        name, identity, owner = runtime._directory_lock_identity(contract, writer.context)
        current = runtime._recovery_query(config, 'configmap', name)
        lock = json.loads(current['data']['lock']) if current else {}
        if (lock.get('schema_version') != 2 or lock.get('state') != 'OWNED'
                or lock.get('identity') != identity or lock.get('owner') != owner):
            raise RuntimeError('selected Master directory owner changed or missing')
        # Already serialized; native protected_stage still validates and checks
        # the exact new owner. It cannot take over another generation.
        writer.serialize = nullcontext
        output = io.StringIO()
        with redirect_stdout(output):
            runtime.step3(contract, config, modules, 'json', bundle=bundle, writer=writer,
                master_bundle=selected, expected_master_uid=record['job_uid'])
        if any(_read_registered(p) != content for p,content in (
                (path,raw), (source_path,source_raw), (status_path,status_raw), (journal_path,journal_raw))):
            raise RuntimeError('selected monitor evidence superseded during observation')
        value = json.loads(output.getvalue())
        execution = dict(pipeline=pipeline, **{k:payload[k] for k in keys})
        payload['_cce_master_result'] = VerifiedMasterResult(
            dict(bundle=str(selected), master_uid=record['job_uid'], mode='observed'), exported, execution)
        return value
