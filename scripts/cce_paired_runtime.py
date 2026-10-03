"""Operator-pinned runtime selection shared by restricted WGS/GATK entries.

Absence of activation keeps legacy behavior. Invalid activation never falls
back to a frozen copy, and no request/environment field selects executable code.
"""
import hashlib
import importlib.util
import json
import os
import errno
from pathlib import Path
import stat
import struct
import sys
import time
from contextlib import ExitStack, contextmanager, nullcontext, redirect_stdout
import io
import fcntl
import re
from types import SimpleNamespace

PLATFORM_SOURCE = Path(__file__).resolve()
STAGE_EXECUTION_PROTOCOL = 'cce.stage-execution.v1'
STAGE_EXECUTION_TOKEN_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}')
DEPLOYMENT_TRUST_ROOT = PLATFORM_SOURCE.parent
DEPLOYMENT_TRUST_PATH = DEPLOYMENT_TRUST_ROOT / 'cce-paired-deployment-v1.json'
COMMANDS = dict(step1_upload='step1-upload', step2_master='step2-run',
    step3_monitor='step3-status', step4_publish='step4-publish',
    step5_download='step5-download', step6_materialize='step6-materialize')


def _acl_write_principals(path):
    try:
        raw=os.getxattr(path,'system.posix_acl_access',follow_symlinks=False)
    except OSError as error:
        unsupported={errno.ENODATA,errno.ENOTSUP}
        if hasattr(errno,'EOPNOTSUPP'):unsupported.add(errno.EOPNOTSUPP)
        if error.errno in unsupported:return set(),set()
        raise RuntimeError('deployment trust ACL cannot be inspected') from error
    if len(raw)<4 or int.from_bytes(raw[:4],'little')!=2 or (len(raw)-4)%8:
        raise RuntimeError('deployment trust ACL is invalid')
    entries=[struct.unpack_from('<HHI',raw,offset) for offset in range(4,len(raw),8)]
    masks=[permissions for tag,permissions,_ in entries if tag==0x10]
    if len(masks)>1:raise RuntimeError('deployment trust ACL is invalid')
    mask=masks[0] if masks else 0o7
    return ({identity for tag,permissions,identity in entries if tag==0x02 and permissions&mask&0o2},
            {identity for tag,permissions,identity in entries if tag==0x08 and permissions&mask&0o2})


def _validate_writers(path,info,uids,gids):
    if (info.st_uid not in uids or info.st_mode&0o002 or (info.st_mode&0o200 and info.st_uid not in uids)
            or (info.st_mode&0o020 and info.st_gid not in gids)):
        raise RuntimeError('deployment trust path has an unapproved writer')
    users,groups=_acl_write_principals(path)
    if not users.issubset(uids) or not groups.issubset(gids):
        raise RuntimeError('deployment trust ACL has an unapproved writer')


def _trust_entry(value,interpreter=False):
    keys={'path','trust_root','maintainer_uids','maintainer_gids'}
    if interpreter:keys.add('canonical_path')
    if not isinstance(value,dict) or set(value)!=keys:
        raise RuntimeError('invalid deployment trust entry')
    uids=value['maintainer_uids'];gids=value['maintainer_gids']
    if (not isinstance(uids,list) or not uids or not isinstance(gids,list)
            or any(type(item) is not int or item<0 for item in [*uids,*gids])):
        raise RuntimeError('invalid deployment trust maintainers')
    return value,set(uids),set(gids)


def _trusted_path(value,interpreter=False):
    value,uids,gids=_trust_entry(value,interpreter)
    path,root=Path(value['path']),Path(value['trust_root'])
    if not path.is_absolute() or not root.is_absolute():
        raise RuntimeError('deployment trust paths must be absolute')
    try:
        root_info=root.lstat()
        if not stat.S_ISDIR(root_info.st_mode) or root.is_symlink() or root.resolve(strict=True)!=root:
            raise RuntimeError('deployment trust root is not canonical')
        path.relative_to(root)
    except (OSError,ValueError) as error:
        raise RuntimeError('deployment trust path escapes its root') from error
    _validate_writers(root,root_info,uids,gids)
    current=path.parent
    while True:
        info=current.lstat()
        if not stat.S_ISDIR(info.st_mode) or current.is_symlink():
            raise RuntimeError('deployment trust ancestry is not canonical')
        _validate_writers(current,info,uids,gids)
        if current==root:break
        if root not in current.parents:raise RuntimeError('deployment trust path escapes its root')
        current=current.parent
    info=path.lstat()
    if interpreter and stat.S_ISLNK(info.st_mode):
        if info.st_uid not in uids:raise RuntimeError('deployment interpreter link owner is unapproved')
        resolved=path.resolve(strict=True)
        if resolved!=Path(value['canonical_path']):raise RuntimeError('deployment interpreter target changed')
    else:
        if not stat.S_ISREG(info.st_mode) or path.resolve(strict=True)!=path:
            raise RuntimeError('deployment trust source must be a canonical file')
        resolved=path
    try:resolved.relative_to(root)
    except ValueError as error:raise RuntimeError('deployment trust target escapes its root') from error
    current=resolved.parent
    while True:
        info=current.lstat()
        if not stat.S_ISDIR(info.st_mode) or current.is_symlink():
            raise RuntimeError('deployment trust ancestry is not canonical')
        _validate_writers(current,info,uids,gids)
        if current==root:break
        if root not in current.parents:raise RuntimeError('deployment trust target escapes its root')
        current=current.parent
    target_info=resolved.lstat()
    if not stat.S_ISREG(target_info.st_mode):raise RuntimeError('deployment trust target must be a regular file')
    _validate_writers(resolved,target_info,uids,gids)
    return resolved if interpreter else path


def _read_regular(path,limit=16*1024*1024):
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info=os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size>limit:
            raise RuntimeError('deployment trust file is invalid')
        raw=os.read(descriptor,limit+1)
        if len(raw)>limit:raise RuntimeError('deployment trust file is too large')
        return raw
    finally:os.close(descriptor)


def _load_deployment_trust():
    try:DEPLOYMENT_TRUST_PATH.lstat()
    except FileNotFoundError:return None
    root,path=DEPLOYMENT_TRUST_ROOT,DEPLOYMENT_TRUST_PATH
    if path.parent!=root or not root.is_absolute():raise RuntimeError('deployment trust entry is not code-anchored')
    root_info,path_info=root.lstat(),path.lstat()
    if (not stat.S_ISDIR(root_info.st_mode) or root.is_symlink()
            or not stat.S_ISREG(path_info.st_mode) or path.is_symlink()
            or path_info.st_uid!=root_info.st_uid or root_info.st_mode&0o022 or path_info.st_mode&0o022):
        raise RuntimeError('deployment trust entry is not maintained by the code owner')
    if any(_acl_write_principals(item)[index] for item in (root,path) for index in (0,1)):
        raise RuntimeError('deployment trust entry has mutable ACL authority')
    try:value=json.loads(_read_regular(path))
    except (UnicodeDecodeError,json.JSONDecodeError) as error:raise RuntimeError('invalid deployment trust document') from error
    if (not isinstance(value,dict) or value.get('schema_version')!=1
            or set(value)!={'schema_version','policy','writers','runtime_guard','operator_python'}
            or set(value.get('writers',{}))!={'cli','platform'}):
        raise RuntimeError('invalid deployment trust document')
    _trusted_path(value['policy']);_trusted_path(value['writers']['cli'])
    _trusted_path(value['writers']['platform']);_trusted_path(value['runtime_guard'])
    _trusted_path(value['operator_python'],True)
    return value


def _pin(pin,trust):
    if not isinstance(pin, dict) or set(pin) != {'path','sha256'}:
        raise RuntimeError('invalid paired runtime pin')
    path = _trusted_path(trust)
    if Path(pin['path'])!=path:
        raise RuntimeError('paired runtime pin differs from deployment trust')
    if hashlib.sha256(_read_regular(path)).hexdigest() != pin['sha256']:
        raise RuntimeError('paired runtime source pin changed')
    return path


def _operator_python(value,trust):
    path = _trusted_path(trust,True)
    if Path(value).resolve(strict=True)!=path:
        raise RuntimeError('paired runtime Python differs from deployment trust')
    if not os.access(path, os.X_OK):
        raise RuntimeError('paired runtime Python is unavailable')
    return str(path)


def selected_runtime():
    trust=_load_deployment_trust()
    if trust is None:
        return None
    path=_trusted_path(trust['policy'])
    try:policy=json.loads(_read_regular(path))
    except (UnicodeDecodeError,json.JSONDecodeError) as error:raise RuntimeError('invalid paired runtime activation') from error
    if (not isinstance(policy, dict) or policy.get('schema_version') != 2
            or set(policy.get('writers', {})) != {'cli','platform'}):
        raise RuntimeError('invalid paired runtime activation')
    source = _pin(policy['writers']['cli'],trust['writers']['cli'])
    platform = _pin(policy['writers']['platform'],trust['writers']['platform'])
    guard = _pin(policy.get('runtime_guard'),trust['runtime_guard'])
    if platform != PLATFORM_SOURCE or guard != source.with_name('cce_writer_guard.py'):
        raise RuntimeError('unpaired platform or guard entry')
    return source, _operator_python(policy['operator_python'],trust['operator_python'])


def stage_command(bundle, stage, *arguments, payload=None, gate=None, pipeline=None):
    if stage not in COMMANDS:
        return None  # Prepare/Step7/maintenance remain outside this rollout.
    selected = selected_runtime()
    if selected is None:
        return None
    source, python = selected
    if stage == 'step1_upload':
        register_initial(payload, bundle=bundle, gate=gate, pipeline=pipeline)
    if payload is not None and stage in {'step4_publish','step5_download','step6_materialize'}:
        if arguments:
            raise RuntimeError('registered downstream does not accept native command overrides')
        _selected_registered(payload, binding=gate._load_binding(payload), gate=gate, pipeline=pipeline,
            operation=lambda *args:None)
        return [python, str(PLATFORM_SOURCE), '--registered-stage', pipeline,
            payload['analysis_id'], str(payload['attempt']), stage, payload['execution_id'],
            str(payload['generation']), payload['request_hash']]
    return [python, str(source), COMMANDS[stage], '--bundle', str(bundle), *arguments]


def register_initial(payload, *, bundle, gate, pipeline):
    """Register prepared frozen inputs at the existing restricted Step1 entry."""
    if (not isinstance(payload, dict) or payload.get('stage') != 'step1_upload'
            or payload.get('orchestration_contract_version') != 2
            or gate is None or pipeline not in {'wgs', 'gatk'}):
        raise RuntimeError('initial registration requires a registered Step1 request')
    path, raw = _registered_request(payload, gate, pipeline)
    binding = gate._load_binding(payload)
    if Path(binding['cce_bundle']) != Path(bundle):
        raise RuntimeError('initial registration differs from prepared bundle')
    candidates = ('prepare', 'prepare_analysis') if pipeline == 'wgs' else ('prepare',)
    matched = []
    for stage in candidates:
        predecessor_path = gate._request_path(payload['analysis_id'], payload['attempt'], stage)
        if not predecessor_path.exists():
            continue
        receipt_path = predecessor_path.with_suffix('.status.json')
        if not receipt_path.exists():
            continue
        predecessor = json.loads(_read_registered(receipt_path))
        if predecessor.get('execution_id') == payload.get('predecessor_execution_id'):
            matched.append(stage)
    if len(matched) != 1:
        raise RuntimeError('initial registration requires its successful prepare predecessor')
    _, evidence = _predecessor(payload, gate, pipeline, previous=matched[0])
    runtime = load_runtime()
    if runtime is None:
        raise RuntimeError('paired runtime disappeared before initial registration')
    contract, config, _ = runtime._load(Path(bundle), None)
    runtime.register_bundle(runtime, Path(bundle), contract, config,
        identity=dict(pipeline=pipeline, analysis_id=payload['analysis_id'], attempt=payload['attempt']),
        control_root=path.parent)
    if _read_registered(path) != raw or any(_read_registered(p) != value for p, value in evidence):
        raise RuntimeError('initial registration request or prepare receipt superseded')


def run_registered_stage(arguments):
    """Child process resolves its own registered request; no view path is an arg."""
    if len(arguments) != 7:
        raise RuntimeError('registered downstream identity required')
    pipeline, analysis_id, attempt, stage, execution_id, generation, digest = arguments
    if (pipeline not in {'wgs','gatk'} or stage not in {'step4_publish','step5_download','step6_materialize'}
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', analysis_id)
            or not attempt.isdigit() or int(attempt) < 1 or not generation.isdigit() or int(generation) < 1):
        raise RuntimeError('invalid registered downstream identity')
    if pipeline == 'wgs':
        if __package__:
            from . import wgs_runtime_gate as gate
        else:
            import wgs_runtime_gate as gate
    else:
        if __package__:
            from . import gatk_runtime_gate as gate
        else:
            import gatk_runtime_gate as gate
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
    if pipeline == 'wgs':
        # Requests and runtime control files have separate approved roots.
        control = gate._workdir(registered)
        expected = (Path(gate.RUNTIME_RUN_ROOT).resolve() / registered['analysis_id']
                    / f"attempt-{registered['attempt']}")
        if control != expected:
            raise RuntimeError('recovery control directory must belong to registered attempt scope')
    return path, raw


def _registered_recovery_root(payload, gate, pipeline):
    if pipeline != 'wgs':
        return None
    path, raw = _registered_request(payload, gate, pipeline)
    frozen = json.loads(raw)
    root = gate._workdir(frozen)

    def resolve():
        current, current_raw = _registered_request(frozen, gate, pipeline)
        if current != path or current_raw != raw or gate._workdir(frozen) != root:
            raise RuntimeError('registered recovery root changed')
        return root

    return resolve


def _registered_journal_root(payload, gate, pipeline):
    path, _ = _registered_request(payload, gate, pipeline)
    callback = _registered_recovery_root(payload, gate, pipeline)
    return (path.parent, callback()) if callback is not None else path.parent


def _registered_writer(runtime, bundle, contract, config, payload, gate, pipeline, **kwargs):
    writer = runtime.writer_for_bundle(runtime, bundle, contract, config, **kwargs)
    callback = (_registered_recovery_root(payload, gate, pipeline)
                if writer is not None and writer.registration_schema_version == 3 else None)
    if callback is not None:
        writer = runtime.writer_for_bundle(runtime, bundle, contract, config,
            recovery_control_root=callback, **kwargs)
    if writer is not None:
        writer._registered_recovery_control_root = callback
    return writer


def _request_digest(registered,pipeline):
    excluded = {'request_hash'} if pipeline == 'gatk' else {
        'execution_id', 'generation', 'request_hash', 'predecessor_execution_id',
        'predecessor_generation', 'predecessor_receipt_hash'}
    # Initial WGS dispatch adds version2 after hashing. Recovery hashes a frozen
    # request that already contains it; retain that producer's digest contract.
    if pipeline == 'wgs' and not registered.get('resume_action_id'):
        excluded.add('orchestration_contract_version')
    return hashlib.sha256(json.dumps({k:v for k,v in registered.items() if k not in excluded},
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def execution_identity_from_registered_request(payload, *, pipeline, handler_registry):
    """Map a verified v2 request to the public, pathless execution identity."""
    if (not isinstance(payload, dict) or not isinstance(pipeline, str)
            or not STAGE_EXECUTION_TOKEN_RE.fullmatch(pipeline)):
        raise RuntimeError('registered stage execution identity is invalid')
    stage = payload.get('stage')
    if not isinstance(stage, str) or not STAGE_EXECUTION_TOKEN_RE.fullmatch(stage):
        raise RuntimeError('registered stage execution stage is invalid')
    if not isinstance(handler_registry, dict) or (pipeline, stage) not in handler_registry:
        raise RuntimeError('stage execution handler registry key is unsupported')
    handler = handler_registry[(pipeline, stage)]
    if handler is None or handler is False or handler == '':
        raise RuntimeError('stage execution handler registry key is unsupported')
    if payload.get('stage_execution') != {'protocol': STAGE_EXECUTION_PROTOCOL}:
        raise RuntimeError('unsupported stage execution protocol')
    if payload.get('orchestration_contract_version') != 2:
        raise RuntimeError('stage execution requires platform contract v2')
    if payload.get('pipeline') not in (None, pipeline):
        raise RuntimeError('registered stage execution pipeline differs')
    if (not isinstance(payload.get('analysis_id'), str)
            or not STAGE_EXECUTION_TOKEN_RE.fullmatch(payload['analysis_id'])
            or not isinstance(payload.get('execution_id'), str)
            or not STAGE_EXECUTION_TOKEN_RE.fullmatch(payload['execution_id'])
            or type(payload.get('attempt')) is not int or payload['attempt'] < 1
            or type(payload.get('generation')) is not int or payload['generation'] < 1
            or not isinstance(payload.get('request_hash'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', payload['request_hash'])):
        raise RuntimeError('registered stage execution identity is incomplete')
    return {
        'protocol': STAGE_EXECUTION_PROTOCOL,
        'pipeline': pipeline,
        'analysis_id': payload['analysis_id'],
        'attempt': payload['attempt'],
        'stage': stage,
        'execution_id': payload['execution_id'],
        'stage_generation': payload['generation'],
        'request_hash': payload['request_hash'],
    }


def platform_status_from_snapshot(payload, snapshot, *, expected_ref, pipeline, handler_registry):
    """Validate a native snapshot against its registration and project its state."""
    identity = execution_identity_from_registered_request(
        payload, pipeline=pipeline, handler_registry=handler_registry
    )
    expected = expected_ref.to_dict() if hasattr(expected_ref, 'to_dict') else expected_ref
    if (not isinstance(expected, dict)
            or set(expected) != set(identity) | {'registration_sha256'}
            or any(expected.get(key) != value for key, value in identity.items())
            or not isinstance(expected.get('registration_sha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', expected['registration_sha256'])):
        raise RuntimeError('expected execution identity is invalid')
    snapshot_keys = {
        'schema', 'execution_ref', 'state', 'evidence_ref', 'runtime_identity',
        'compute_identity', 'observation_health',
    }
    if (not isinstance(snapshot, dict) or set(snapshot) != snapshot_keys
            or snapshot.get('schema') != 'cce.stage-execution.snapshot.v1'
            or snapshot.get('execution_ref') != expected):
        raise RuntimeError('native execution snapshot identity differs')
    state = snapshot.get('state')
    health = snapshot.get('observation_health')
    if state not in {'accepted', 'running', 'succeeded', 'failed', 'canceled', 'unknown'}:
        raise RuntimeError('native execution snapshot state is unsupported')
    if health not in {'healthy', 'degraded'} or (state == 'unknown' and health != 'degraded'):
        raise RuntimeError('native execution observation health is invalid')
    runtime_identity = snapshot.get('runtime_identity')
    if runtime_identity is not None and (
        not isinstance(runtime_identity, dict)
        or set(runtime_identity) != {'boot_id', 'pid', 'starttime_ticks', 'process_group_id'}
        or not isinstance(runtime_identity.get('boot_id'), str)
        or not STAGE_EXECUTION_TOKEN_RE.fullmatch(runtime_identity['boot_id'])
        or any(type(runtime_identity.get(key)) is not int or runtime_identity[key] < 1
               for key in ('pid', 'starttime_ticks', 'process_group_id'))
    ):
        raise RuntimeError('native runtime process identity is invalid')
    compute_identity = snapshot.get('compute_identity')
    if compute_identity is not None and (
        not isinstance(compute_identity, dict)
        or set(compute_identity) != {'compute_generation', 'master_uid'}
        or (compute_identity.get('compute_generation') is not None
            and (type(compute_identity['compute_generation']) is not int
                 or compute_identity['compute_generation'] < 1))
        or (compute_identity.get('master_uid') is not None
            and (not isinstance(compute_identity['master_uid'], str)
                 or not STAGE_EXECUTION_TOKEN_RE.fullmatch(compute_identity['master_uid'])))
    ):
        raise RuntimeError('native compute identity is invalid')
    evidence_ref = snapshot.get('evidence_ref')
    if (evidence_ref is not None and (not isinstance(evidence_ref, str)
                                      or not STAGE_EXECUTION_TOKEN_RE.fullmatch(evidence_ref))):
        raise RuntimeError('native execution evidence reference is invalid')
    return {
        'accepted': 'accepted',
        'running': 'running',
        'succeeded': 'success',
        'failed': 'failed',
        'canceled': 'canceled',
        'unknown': None,
    }[state]


@contextmanager
def _exclusive(path):
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o660)
        os.fchmod(fd, 0o660)
    except FileExistsError:
        fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def _inactive_dispatcher(path, gate, pipeline):
    """A free lock/dead parent alone is not terminal dispatcher evidence."""
    worker = path.with_suffix('.worker.json' if pipeline == 'wgs' else '.worker.state.json')
    status = path.with_suffix('.status.json')
    native_dispatch = path.with_suffix('.stage-execution.dispatch.json')
    if os.path.lexists(path):
        request = json.loads(_read_registered(path))
        if not isinstance(request, dict):
            raise RuntimeError('other dispatcher request is invalid')
        marked = 'stage_execution' in request
        if not marked and os.path.lexists(native_dispatch):
            raise RuntimeError('native dispatcher belongs to a different protocol')
        if marked:
            if request['stage_execution'] != {'protocol': STAGE_EXECUTION_PROTOCOL}:
                raise RuntimeError('other dispatcher protocol is unsupported')
            if __package__:
                from .cce_stage_execution_adapter import executor_for_registered
            else:
                from cce_stage_execution_adapter import executor_for_registered
            executor, ref, binding = executor_for_registered(
                request, gate=gate, pipeline=pipeline)
            if (binding.request_path != path
                    or binding.dispatch_path != native_dispatch):
                raise RuntimeError('native dispatcher lock or dispatch path differs')
            # Callers hold both exact stage locks through their writer decision.
            quiet = executor.writer_quiescent(ref, locks_held=True)
            if quiet is False:
                raise RuntimeError('native dispatcher is active or uncertain')
            if quiet is True:
                if os.path.lexists(worker):
                    raise RuntimeError('legacy dispatcher evidence remains beside native terminal')
                return
            # No native dispatch: legacy evidence still has to be reconciled.
            if os.path.lexists(native_dispatch):
                raise RuntimeError('native dispatcher evidence became uncertain')
    else:
        suffix = '.request.json' if pipeline == 'gatk' else '.json'
        stage = path.name[:-len(suffix)] if path.name.endswith(suffix) else None
        if (os.path.lexists(native_dispatch)
                or (stage in COMMANDS and any(os.path.lexists(
                    path.parent / directory / stage)
                    for directory in ('stage-execution-registration',
                                      'stage-execution-terminal')))):
            raise RuntimeError('native dispatcher request is missing')
    if not worker.exists() and not status.exists():
        return  # Registered but never dispatched, or no request yet.
    if not worker.exists() or not status.exists() or not path.exists():
        raise RuntimeError('other dispatcher lacks terminal evidence')
    state, receipt, request = [json.loads(_read_registered(p)) for p in (worker, status, path)]
    immutable_prepare = pipeline == 'gatk' and request.get('kind') == 'gatk-airflow-prepare'
    if immutable_prepare:
        if (path != gate._request_path(request['analysis_id'], request['attempt'], 'prepare')
                or _request_digest(request, pipeline) != request.get('request_hash')):
            raise RuntimeError('immutable prepare dispatcher request changed')
        generation = state.get('generation')
        if type(generation) is not int or generation < 1:
            raise RuntimeError('immutable prepare dispatcher generation is invalid')
        request = {**request, **gate._dispatch_identity({**request, 'generation': generation}),
                   'orchestration_contract_version':2}
    keys = ('analysis_id', 'attempt', 'stage', 'generation', 'execution_id', 'request_hash')
    if (request.get('orchestration_contract_version') != 2
            or any(not request.get(k) or state.get(k) != request[k] or receipt.get(k) != request[k] for k in keys)
            or receipt.get('status') not in {'success', 'succeeded', 'complete', 'failed', 'canceled'}):
        raise RuntimeError('other dispatcher terminal identity is incomplete')
    if pipeline == 'gatk':
        process = state.get('process')
        if (state.get('schema_version') != 'gatk-runtime.dispatcher.v1'
                or state.get('state') != 'finished'
                or (immutable_prepare and (not isinstance(process, dict)
                    or not all(process.get(key) for key in ('pid', 'starttime', 'boot_id'))))
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


def _resolve_selected_owner(runtime, bundle, selected, contract, config, record, platform, writer):
    """Native and platform consumers must agree on one current confirmed owner."""
    expected = dict(generation=record['execution_generation'],
        action=record['recovery_context']['action'], master_uid=record['job_uid'])
    if writer.registration_schema_version == 2:
        # Explicit historical static registration keeps its already-validated
        # platform receipt/journal/ConfigMap path, not a dynamic fallback.
        return expected
    if writer.registration_schema_version != 3:
        raise RuntimeError('unsupported native writer registration protocol')
    callback = getattr(writer, '_registered_recovery_control_root', None)
    current = runtime.resolve_current_owner(runtime, bundle, contract, config,
        selected_bundle=selected, expected_master_uid=record['job_uid'], read_only=True,
        **({'recovery_control_root': callback} if callback is not None else {}))
    if (current['selected_bundle'] != selected
            or current['expected_master_uid'] != record['job_uid']
            or current['record'] != record or current['platform_execution'] != platform
            or any(current['context'].get(k) != v for k, v in expected.items())):
        raise RuntimeError('native current owner differs from registered selected Master')
    return expected


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
    writer = _registered_writer(runtime, bundle, contract, config, payload, gate, pipeline)
    if writer is None:
        raise RuntimeError('trusted per-run writer registration required')
    with writer.serialize():
        writer.validate()
        return _submit_registered_locked(payload, pipeline=pipeline, path=path, raw=raw,
            bundle=bundle, runtime=runtime, contract=contract, config=config, modules=modules, writer=writer)


def _submit_registered_locked(payload, *, pipeline, path, raw, bundle, runtime, contract, config, modules, writer):
    """Existing initial producer; its caller owns the registered writer scope."""
    platform = dict(pipeline=pipeline, **{k:payload[k] for k in
        ('analysis_id','attempt','stage','execution_id','generation','request_hash')})
    action = payload['execution_id']
    if (writer.context.get('generation') != 1
            or writer.context.get('analysis_id') != payload['analysis_id']
            or writer.context.get('attempt') != str(payload['attempt'])
            or writer.context.get('pipeline') != pipeline):
        raise RuntimeError('initial operator owner differs from registered submission')
    journal_path = path.parent / ('submission-'+action+'.json')
    selected = journal_path.with_suffix('') / 'view'
    journal = json.loads(_read_registered(journal_path)) if journal_path.exists() else {}
    identity = dict(platform_execution=platform, source_bundle=str(bundle), selected_bundle=str(selected))
    if journal and journal.get('identity') != identity:
        raise RuntimeError('initial submission journal changed')
    selected = runtime._prepare_submission_view(bundle, selected, contract,
        platform_execution=platform, owner_action=writer.context['action'])
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
        intent = runtime._master_create_intent(selected, contract)
        if intent is None:
            raise RuntimeError('initial CREATE requires a persisted native intent')
        journal.update(identity=identity,state='submitting',deadline_epoch=intent['deadline_epoch'])
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


def _initial_step2_continuation(path, payload, gate, pipeline, runtime, bundle, contract, config, writer):
    """A recovery action may precede the first Master, without being its producer."""
    if payload['stage'] != 'step2_master':
        return False
    context = writer.context
    expected_action = runtime.initial_owner_action(pipeline=pipeline,
        analysis_id=payload['analysis_id'], attempt=payload['attempt'], run_id=contract['identity']['run_id'])
    if (context.get('generation') != 1 or context.get('action') != expected_action
            or context.get('pipeline') != pipeline or context.get('analysis_id') != payload['analysis_id']
            or context.get('attempt') != str(payload['attempt'])):
        return False  # A real prior/replacement owner keeps the recovery path.
    platform = dict(pipeline=pipeline, **{k:payload[k] for k in
        ('analysis_id','attempt','stage','execution_id','generation','request_hash')})
    views = list(_journal_views(_registered_journal_root(payload, gate, pipeline), pipeline, runtime, bundle, contract))
    journal_path = path.parent / ('submission-'+payload['execution_id']+'.json')
    current = [v for v in views if v[0] == journal_path and v[1].get('identity',{}).get('platform_execution') == platform]
    if views and (len(current) != 1 or len(views) != 1):
        return False  # Existing/unknown producers must be reconciled, never CREATE again.
    allowed = {journal_path, journal_path.with_suffix('')} if current else set()
    artifacts = {p for pattern in ('submission-*', 'recovery-*', 'resume-*')
        for p in path.parent.glob(pattern)}
    if len(artifacts) > 4096:
        raise RuntimeError('initial continuation native artifact scope is too large')
    for artifact in artifacts:
        # _journal_views deliberately ignores legacy recovery records without
        # platform identity. Such bytes cannot establish a fresh CREATE scope.
        if (artifact not in allowed or artifact.is_symlink()
                or not (artifact.is_file() if artifact == journal_path else artifact.is_dir())):
            raise RuntimeError('initial continuation has an unregistered native intent')
    frozen = runtime._handoff_binding(bundle, contract)
    if (frozen['attempt'] != payload['attempt'] or frozen.get('execution_generation') != 1
            or frozen.get('recovery_context') or frozen.get('platform_execution')
            or runtime._read_master_handoff(bundle, contract)
            or runtime._master_create_intent(bundle, contract)):
        return False
    predecessor, evidence = _predecessor(payload, gate, pipeline, previous='step1_upload')
    if (type(payload.get('predecessor_generation')) is not int
            or payload['predecessor_generation'] != predecessor['generation']):
        raise RuntimeError('initial continuation predecessor generation changed')
    name, identity, owner = runtime._directory_lock_identity(contract, context)
    cm = runtime._recovery_query(config, 'configmap', name)
    lock = json.loads(cm['data']['lock']) if cm else {}
    owners = [owner]
    if current and current[0][1].get('job_uid'):
        owners.append({**owner, 'master_uid':current[0][1]['job_uid']})
    if (lock.get('schema_version') != 2 or lock.get('identity') != identity
            or lock.get('state') != 'OWNED' or lock.get('owner') not in owners):
        raise RuntimeError('initial continuation directory owner changed or missing')
    if not current:
        if owner['master_uid'] or runtime._recovery_query(config,'job',contract['kubernetes']['master_job']) is not None:
            raise RuntimeError('initial continuation cannot adopt an existing Master')
    elif owner['master_uid'] not in ('', current[0][1].get('job_uid')):
        raise RuntimeError('initial continuation differs from its submitted Master')
    _registered_request(payload, gate, pipeline)
    if any(_read_registered(p) != value for p,value in evidence):
        raise RuntimeError('initial continuation successful predecessor changed')
    return True


def _journal_views(root, pipeline, runtime, bundle, contract):
    """Locate native views by exact persisted identity, never by mtime/latest."""
    spool, recovery = root if isinstance(root, tuple) else (root, root)
    paths = sorted({p for directory, pattern in ((spool, 'submission-*.json'),
        (recovery, 'recovery-*.json' if pipeline == 'wgs' else 'resume-*.json'))
        for p in directory.glob(pattern)})
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
                or platform.get('analysis_id') != spool.parent.name or platform.get('attempt') != frozen['attempt']):
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
        recovery=journal.get('recovery_v2',{})
        if recovery.get('recovery_kind')=='initial_abort':
            if __package__:
                from .cce_recovery_inventory import InitialAbortAncestor
            else:
                from cce_recovery_inventory import InitialAbortAncestor
            original=runtime._handoff_binding(parent,contract)
            child=runtime._handoff_binding(source,contract)
            digest=recovery.get('initial_abort_sha256')
            if (recovery.get('original')!=original or recovery.get('expected_job_uid')!=record['job_uid']
                    or recovery.get('context')!=child.get('recovery_context')
                    or recovery.get('platform_execution')!=child.get('platform_execution')
                    or recovery.get('view')!=str(source) or original['execution_generation']!=1
                    or record.get('state')!='JOB_CREATED' or record.get('pod_uid')
                    or not re.fullmatch(r'[a-f0-9]{64}',str(digest))):
                raise RuntimeError('initial abort ancestor differs from its registered child')
            history.append(InitialAbortAncestor(parent,digest))
        else:
            history.append(parent)
        source=parent
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


def _initial_abort_source(root,payload,gate,pipeline,runtime,bundle,contract,config,writer):
    """Locate the original pre-START producer under existing sender/writer locks.

    Native owns abort validation. Journals and operator-derived raw locators
    only identify its immutable input; neither absence nor business failure
    grants replacement authority here.
    """
    if pipeline!='wgs' or payload['stage']!='step2_master':
        return None
    views=list(_journal_views(root,pipeline,runtime,bundle,contract))
    replays=[v for v in views if v[1].get('recovery_v2',{}).get('context',{}).get('action')==payload['resume_action_id']]
    if replays and (len(replays)!=1 or replays[0][1]['recovery_v2'].get('recovery_kind')!='initial_abort'):
        return None  # Ordinary compute recovery retains its existing path.
    name,identity,_=runtime._directory_lock_identity(contract,writer.context)
    current=runtime._recovery_query(config,'configmap',name)
    lock=json.loads(current['data']['lock']) if current else {}
    if lock.get('state')!='OWNED' or lock.get('identity')!=identity:
        raise RuntimeError('registered directory lock missing or foreign')
    candidates=[]
    for view in views:
        journal_path,journal,selected,platform=view
        if 'identity' not in journal or journal.get('state')!='created':
            continue
        native=runtime._handoff_binding(selected,contract)
        if native.get('execution_generation')!=1:
            continue
        pending=dict(generation=1,action=native.get('recovery_context',{}).get('action'),master_uid='')
        if replays:
            if str(selected)!=replays[0][1].get('registered_source'):
                continue
        elif lock.get('owner')!=pending:
            continue
        candidates.append(view)
    if not candidates:
        return None
    if len(candidates)!=1:
        raise RuntimeError('initial abort has no unique registered source')
    journal_path,journal,source,platform=candidates[0]
    frozen=runtime._handoff_binding(bundle,contract)
    native=runtime._handoff_binding(source,contract)
    if (source.resolve(strict=True)!=source or native.get('platform_execution')!=platform
            or any(native[k]!=frozen[k] for k in ('attempt','files_sha256','config_sha256'))):
        raise RuntimeError('initial source differs from registered frozen inputs')
    record=runtime._read_master_handoff(source,contract)
    if (not record or record.get('schema_version')!=2 or record.get('state')!='JOB_CREATED'
            or record.get('job_uid')!=journal.get('job_uid') or record.get('pod_uid')
            or any(record.get(k)!=v for k,v in native.items())):
        raise RuntimeError('initial source handoff differs from its journal')
    journal_raw=_read_registered(journal_path)
    if json.loads(journal_raw)!=journal:
        raise RuntimeError('initial submission journal changed')
    evidence=(*_producer_registration(platform,gate,pipeline,payload['analysis_id'],payload['attempt']),
        (journal_path,journal_raw))
    if __package__:
        from . import cce_stage_execution_adapter as adapter
    else:
        import cce_stage_execution_adapter as adapter
    producer=gate._request_path(payload['analysis_id'],payload['attempt'],platform['stage'])
    _,_,_,ref=adapter._read_frozen(adapter._registration_path(producer,platform['stage'],platform['generation']),
        gate=gate,pipeline=pipeline,registry=adapter._registry(gate,pipeline))
    locators=adapter.initial_dispatch_proof(ref,gate=gate,pipeline=pipeline)
    abort=runtime._initial_submission_abort_evidence(source,contract,
        submission_journal=journal,dispatch_proof=locators)
    if replays:
        _,replay,_,_=replays[0]
        identity=replay['recovery_v2']
        if (identity.get('original')!=native or identity.get('expected_job_uid')!=record['job_uid']
                or identity.get('initial_abort_sha256')!=hashlib.sha256(runtime._recovery_encoded(abort)).hexdigest()):
            raise RuntimeError('initial abort replay evidence changed')
    return source,record,abort,evidence


def _reconcile_initial_intent(root,payload,gate,pipeline,runtime,bundle,contract,config,writer):
    """Resume a failed initial handoff with its original CREATE and deadline."""
    name,identity,_=runtime._directory_lock_identity(contract,writer.context)
    current=runtime._recovery_query(config,'configmap',name)
    lock=json.loads(current['data']['lock']) if current else {}
    if lock.get('state')!='OWNED' or lock.get('identity')!=identity:return
    for path,journal,selected,platform in _journal_views(root,pipeline,runtime,bundle,contract):
        if 'identity' not in journal or journal.get('state')=='confirmed':continue
        pending=dict(generation=1,action=writer.context['action'],master_uid='')
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
        writer.context.update(generation=1,action=pending['action'],master_uid=uid)
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
        from .cce_recovery_deadline import deadline_epoch
    else:
        from cce_recovery_failure import collect_failure_evidence
        from cce_recovery_deadline import deadline_epoch
    try:
        return collect_failure_evidence(runtime=runtime,selected=selected,contract=contract,config=config,
            run_label=run_label,binding=exported,
            history_bundles=_source_history(request_root,pipeline,runtime,bundle,contract,selected),
            original_deadline_epoch=deadline_epoch(payload))
    except (ValueError, RuntimeError, OSError, KeyError, TypeError):
        # Missing/mixed/unknown evidence is ineligible, not a reason to erase the
        # ordinary failed status or change the existing manual recovery path.
        return None


def _created_monitor_journal(root, payload, pipeline, runtime, bundle, contract, expected=None, *, gate):
    """Follow registered observers to their exact original Step3 producer."""
    if pipeline != 'wgs':
        return None
    producer = (expected or {}).get('platform_execution')
    if producer is None:
        previous = payload.get('resume_previous_execution') or {}
        if payload.get('stage') != 'step3_monitor' or not previous:
            return None
        producer = dict(pipeline=pipeline, analysis_id=payload['analysis_id'], attempt=payload['attempt'],
            stage='step3_monitor', **previous)
    if expected is not None and producer.get('stage') != 'step3_monitor':
        return None
    if __package__:
        from .cce_recovery_deadline import deadline_epoch
    else:
        from cce_recovery_deadline import deadline_epoch
    views = list(_journal_views(root, pipeline, runtime, bundle, contract))
    evidence = []
    ceiling = payload['generation'] if expected is None else producer['generation'] + 1
    while True:
        generation = producer.get('generation')
        if producer.get('stage') != 'step3_monitor' or type(generation) is not int or not 0 < generation < ceiling:
            raise RuntimeError('monitor producer chain is cyclic or not decreasing')
        authenticated = _producer_registration(producer, gate, pipeline, payload['analysis_id'], payload['attempt'])
        registered = json.loads(authenticated[0][1])
        if (any(raw != authenticated[0][1] for _, raw in authenticated)
                or gate._workdir(registered) != gate._workdir(payload)
                or deadline_epoch(registered) != deadline_epoch(payload)):
            raise RuntimeError('monitor producer chain changed frozen scope')
        evidence.extend(authenticated)
        matches = [item for item in views if item[3].get('execution_id') == producer.get('execution_id')]
        if matches:
            if len(matches) != 1 or matches[0][3] != producer:
                raise RuntimeError('created monitor producer is ambiguous or changed')
            if matches[0][1].get('recovery_state') != 'created':
                if len(evidence) > 1:
                    raise RuntimeError('observer chain has no created producer')
                return None
            return (*matches[0], tuple(evidence))
        previous = registered.get('resume_previous_execution')
        if expected is not None or not previous:
            if len(evidence) > 1:
                raise RuntimeError('observer chain has no registered native producer')
            return None
        if not isinstance(previous, dict) or set(previous) != {'execution_id', 'generation', 'request_hash'}:
            raise RuntimeError('monitor producer predecessor identity changed')
        ceiling = generation
        producer = dict(pipeline=pipeline, analysis_id=payload['analysis_id'], attempt=payload['attempt'],
                        stage='step3_monitor', **previous)


def _confirmed_created_monitor_source(payload, gate, pipeline, runtime, bundle, contract, config, writer, expected=None,
        serialized=False):
    """Reconcile an existing START only; preserve its created journal and producer."""
    path, request_raw = _registered_request(payload, gate, pipeline)
    root = _registered_journal_root(payload, gate, pipeline)
    located = _created_monitor_journal(root, payload, pipeline, runtime, bundle, contract, expected, gate=gate)
    if located is None:
        return None
    journal_path, saved, selected, platform, chain_evidence = located
    journal_raw = _read_registered(journal_path)
    if json.loads(journal_raw) != saved:
        raise RuntimeError('created monitor journal changed')
    producer_evidence = _producer_registration(platform, gate, pipeline, payload['analysis_id'], payload['attempt'])
    evidence = (*chain_evidence, *producer_evidence)
    producer = json.loads(producer_evidence[0][1])
    parent = Path(saved.get('registered_source', str(bundle)))
    allowed = [bundle, *[v[2] for v in _journal_views(root, pipeline, runtime, bundle, contract)]]
    if parent not in allowed or parent.resolve(strict=True) != parent or selected.resolve(strict=True) != selected:
        raise RuntimeError('created monitor source is not registered or canonical')
    original = runtime._handoff_binding(parent, contract)
    old = runtime._read_master_handoff(parent, contract)
    native = runtime._handoff_binding(selected, contract)
    record = runtime._read_master_handoff(selected, contract)
    frozen = runtime._handoff_binding(bundle, contract)
    if not old or any(old.get(k) != v for k, v in original.items()):
        raise RuntimeError('created monitor parent handoff changed')
    context = dict(pipeline=pipeline, analysis_id=platform['analysis_id'], execution_id=platform['execution_id'],
        generation=original['execution_generation'] + 1, action=producer.get('resume_action_id'))
    if __package__:
        from .cce_recovery_deadline import deadline_epoch
    else:
        from cce_recovery_deadline import deadline_epoch
    deadline = deadline_epoch(producer)
    recovery = dict(expected_job_uid=old['job_uid'], context=context, original=original,
        view=str(selected), platform_execution=platform)
    if deadline is not None:
        recovery['compute_deadline'] = deadline
    if (journal_path.name != 'recovery-' + str(context['action']) + '.json'
            or saved.get('recovery_v2') != recovery or deadline_epoch(payload) != deadline
            or native.get('platform_execution') != platform or native.get('recovery_context') != context
            or any(original.get(k) != frozen[k] for k in ('attempt', 'config_sha256', 'files_sha256'))
            or any(native.get(k) != frozen[k] for k in ('attempt', 'config_sha256', 'files_sha256'))
            or not record or record.get('schema_version') != 2 or not record.get('pod_uid')
            or record.get('job_uid') != saved.get('replacement_uid')
            or record.get('deadline_epoch') != saved.get('recovery_handoff_deadline')
            or record.get('state') not in {'START_SENT', 'START_CONFIRMED'}
            or any(record.get(k) != v for k, v in native.items())):
        raise RuntimeError('created monitor differs from its frozen producer')
    owner = dict(generation=context['generation'], action=context['action'], master_uid=record['job_uid'])
    with (nullcontext() if serialized else writer.serialize()):
        # Validate the factory's authenticated registration/storage first. Its
        # dynamic cloud resolver cannot require the new ACK before accepting it.
        writer.validate()
        writer.context.update(owner)
        name, identity, _ = runtime._directory_lock_identity(contract, writer.context)
        def check_owner():
            current = runtime._recovery_query(config, 'configmap', name)
            lock = json.loads(current['data']['lock']) if current else {}
            if (lock.get('schema_version') != 2 or lock.get('state') != 'OWNED'
                    or lock.get('identity') != identity or lock.get('owner') != owner):
                raise RuntimeError('created monitor directory owner changed')
        check_owner()
        if record['state'] == 'START_SENT':
            live = runtime._recovery_query(config, 'job', record['job_name'])
            if live is None:
                final = runtime._recovery_final_evidence(selected, contract, record['job_uid'])
                if final['terminal']['state'] != 'SUCCEEDED':
                    raise RuntimeError('created monitor reclaimed Master has no verified success')
            elif (live.get('metadata', {}).get('uid') != record['job_uid']
                    or live['metadata'].get('deletionTimestamp')):
                raise RuntimeError('created monitor Master is missing or changed')
            # Native handles the real ACK and its original deadline. START_SENT
            # goes only to await; this never executes replacement or sends START.
            token = runtime.CURRENT_WRITER.set(writer)
            try:
                runtime._finish_master_handoff(selected, contract, config, record['job_uid'])
            finally:
                runtime.CURRENT_WRITER.reset(token)
        check_owner()
        record = runtime._read_master_handoff(selected, contract)
        exported = _exported_master(runtime, bundle, selected, contract, platform)
        if expected is not None and exported != expected:
            raise RuntimeError('created monitor receipt producer changed')
        if (_read_registered(path) != request_raw or _read_registered(journal_path) != journal_raw
                or any(_read_registered(p) != raw for p, raw in evidence)):
            raise RuntimeError('created monitor registration changed during confirmation')
    return selected, record, ((journal_path, journal_raw), *evidence)


def _observe_registered_source(payload, binding, gate, pipeline, runtime, bundle, contract, config, modules, writer, operation=None,
        expected=None, evidence=()):
    """Reattach a new observer without relabelling the original Master producer."""
    path, raw = _registered_request(payload,gate,pipeline)
    read_only = payload['stage'] == 'step3_monitor'
    with (nullcontext() if read_only else writer.serialize()):
        if not read_only:
            writer.validate()
        created = _confirmed_created_monitor_source(payload, gate, pipeline, runtime, bundle, contract,
            config, writer, expected, serialized=not read_only)
        if created is not None:
            source, record, confirmed_evidence = created
            evidence = (*evidence, *confirmed_evidence)
        elif expected is None:
            source, record = _recovery_source(_registered_journal_root(payload,gate,pipeline),payload,pipeline,runtime,bundle,contract,writer)
        else:
            matches=[v for v in _journal_views(_registered_journal_root(payload,gate,pipeline),pipeline,runtime,bundle,contract)
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
        writer.context.update(_resolve_selected_owner(runtime,bundle,source,contract,config,record,platform,writer))
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
                    master_bundle=source,expected_master_uid=record['job_uid'],read_only=True)
            result=json.loads(output.getvalue())
        else:result=operation(runtime,bundle,source,record['job_uid'],contract,config,modules,writer)
        proof = _automatic_failure_evidence(payload,result or {},runtime=runtime,bundle=bundle,selected=source,
            contract=contract,config=config,run_label=binding['run_label'],exported=exported,
            request_root=_registered_journal_root(payload,gate,pipeline),pipeline=pipeline)
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
    if __package__:
        from .cce_recovery_deadline import deadline_epoch, monitor_wait
    else:
        from cce_recovery_deadline import deadline_epoch, monitor_wait
    monitor_wait(payload, 0)
    original_deadline = deadline_epoch(payload)
    bundle = Path(binding['cce_bundle'])
    contract, config, modules = runtime._load(bundle, None)
    writer = _registered_writer(runtime, bundle, contract, config, payload, gate, pipeline,
        **({'probe_deadline_epoch':original_deadline} if original_deadline is not None else {}))
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
        if _initial_step2_continuation(path,payload,gate,pipeline,runtime,bundle,contract,config,writer):
            return _submit_registered_locked(payload, pipeline=pipeline, path=path, raw=raw,
                bundle=bundle, runtime=runtime, contract=contract, config=config, modules=modules, writer=writer)
        initial=_initial_abort_source(_registered_journal_root(payload,gate,pipeline),payload,gate,pipeline,runtime,bundle,contract,config,writer)
        abort=None; producer_evidence=()
        if initial is not None:
            if original_deadline is not None:
                raise RuntimeError('initial abort cannot change an initialized compute budget')
            source,record,abort,producer_evidence=initial
            started=[v for v in _journal_views(_registered_journal_root(payload,gate,pipeline),pipeline,runtime,bundle,contract)
                if v[1].get('recovery_state')=='started'
                and v[1].get('recovery_v2',{}).get('context',{}).get('action')==payload['resume_action_id']]
            if started:
                if len(started)!=1:
                    raise RuntimeError('initial abort has ambiguous started replay')
                _,_,selected,producer=started[0]
                expected=_exported_master(runtime,bundle,selected,contract,producer)
                writer.serialize=nullcontext
                _observe_registered_source(payload,binding,gate,pipeline,runtime,bundle,contract,config,modules,writer,
                    expected=expected,evidence=producer_evidence)
                return payload['_cce_master_result']
        else:
            _reconcile_initial_intent(_registered_journal_root(payload,gate,pipeline),payload,gate,pipeline,runtime,bundle,contract,config,writer)
            source, record = _recovery_source(_registered_journal_root(payload,gate,pipeline), payload, pipeline, runtime, bundle, contract, writer)
        if not isinstance(record, dict) or record.get('schema_version') != 2:
            raise RuntimeError('native Master handoff identity required')
        old_uid = record['job_uid']
        live = runtime._recovery_query(config,'job',contract['kubernetes']['master_job'])
        if abort is None and live is not None and live.get('metadata',{}).get('uid') == old_uid:
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
        terminal = abort['binding'] if abort is not None else runtime._recovery_final_evidence(source, contract, old_uid)['terminal']
        context = dict(pipeline=pipeline, analysis_id=payload['analysis_id'],
            execution_id=payload['execution_id'], generation=terminal['execution_generation']+1,
            action=payload['resume_action_id'])
        platform = {k:payload[k] for k in ('analysis_id', 'attempt', 'stage', 'execution_id', 'generation', 'request_hash')}
        platform['pipeline'] = pipeline
        name, identity, old_owner = runtime._directory_lock_identity(contract, writer.context)
        expected_owner = abort['pending_owner'] if abort is not None else dict(generation=terminal['execution_generation'],
            action=terminal['recovery_context']['action'], master_uid=old_uid)
        if (identity['pipeline'] != pipeline
                or identity['analysis_id'] != payload['analysis_id']
                or identity['attempt'] != str(payload['attempt'])):
            raise RuntimeError('operator registration differs from native old owner')

        def authorize(facts):
            if _read_registered(path) != raw or any(_read_registered(p)!=v for p,v in producer_evidence):
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
            compute_deadline=original_deadline,
            history_bundles=_source_history(_registered_journal_root(payload,gate,pipeline),pipeline,runtime,bundle,contract,source),
            **({'initial_abort':abort} if abort is not None else {}))
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
    runtime = load_runtime()
    bundle = Path(binding['cce_bundle'])
    contract, _, _ = runtime._load(bundle, None)
    if _created_monitor_journal(_registered_journal_root(payload,gate,pipeline), payload, pipeline, runtime, bundle, contract, gate=gate) is not None:
        # A failed START observer already has a producer. This branch can only
        # confirm that producer and observe it; errors never fall into Resume.
        _selected_registered(payload, binding=binding, gate=gate, pipeline=pipeline,
            runtime=runtime, operation=lambda *args: {})
        return
    if any(saved.get('recovery_state') == 'started'
            and saved.get('recovery_v2', {}).get('context', {}).get('action') == payload['resume_action_id']
            for _, saved, _, _ in _journal_views(_registered_journal_root(payload, gate, pipeline), pipeline, runtime, bundle, contract)):
        # A confirmed replacement is observed even if its Job has been reclaimed.
        # The journal is only a locator: revalidate registration, native handoff,
        # frozen inputs and current owner before the ordinary monitor reads FINAL.
        _selected_registered(payload, binding=binding, gate=gate, pipeline=pipeline,
            runtime=runtime, operation=lambda *args: {})
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
    writer=_registered_writer(runtime,bundle,contract,config,payload,gate,pipeline)
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
    writer = _registered_writer(runtime, bundle, contract, config, payload, gate, pipeline)
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


def _predecessor(payload, gate, pipeline, *, previous=None):
    if previous is None:
        stages = tuple(COMMANDS)
        previous = stages[stages.index(payload['stage']) - 1]
    path = gate._request_path(payload['analysis_id'], payload['attempt'], previous)
    raw = _read_registered(path)
    request = json.loads(raw)
    status_path = path.with_suffix('.status.json')
    status_raw = _read_registered(status_path)
    receipt = json.loads(status_raw)
    if pipeline == 'gatk' and previous == 'prepare':
        # Prepare's immutable request predates the stage-v2 envelope. Its
        # generation-scoped identity is produced by the existing gate receipt.
        generation = receipt.get('generation')
        if (request.get('kind') != 'gatk-airflow-prepare'
                or type(generation) is not int or generation < 1
                or request.get('request_hash') != _request_digest(request, pipeline)
                or any(request.get(k) != payload.get(k) for k in ('analysis_id', 'attempt'))):
            raise RuntimeError('GATK prepare predecessor request changed')
        request = {**request, 'stage':'prepare', 'generation':generation,
            'execution_id':f"{payload['analysis_id']}-a{payload['attempt']}-prepare-g{generation}",
            'orchestration_contract_version':2}
    else:
        _registered_request(request, gate, pipeline)
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
    runtime = load_runtime()
    if runtime is None:
        return None
    # This callback is consumed only after the entire selected-Master read
    # returns. A healthy control write must publish that read, never old counts.
    owner = _monitor_query_owner(payload, gate, pipeline, runtime,
        observation=lambda: (value, binding))
    try:
        value = _selected_registered(payload, binding=binding, gate=gate, pipeline=pipeline,
            runtime=runtime, query_owner=owner)
        if owner is not None:
            owner.confirmed()
    except Exception:
        # No whole-monitor replay. Only a returned, validated terminal result
        # proves analysis failure; query/control errors leave execution unknown.
        # The owner's save rechecks registration, so stale workers cannot write.
        if owner is not None:
            owner.unconfirmed()
        raise
    return value


def _monitor_query_owner(payload, gate, pipeline, runtime, *, observation=None):
    """Current worker owns the lock; reuse its registered status, never a new spool."""
    if __package__:
        from .cce_query_reconnect import QueryReconnect
        from .cce_recovery_deadline import deadline_epoch
    else:
        from cce_query_reconnect import QueryReconnect
        from cce_recovery_deadline import deadline_epoch
    deadline = deadline_epoch(payload)
    if deadline is None:
        return None  # Existing unmarked executions keep their original behavior.
    if payload.get('orchestration_contract_version') != 2 or payload.get('stage') != 'step3_monitor':
        raise RuntimeError('query reconnect requires registered v2 monitor')
    path, _ = _registered_request(payload, gate, pipeline)
    status_path = path.with_suffix('.status.json')
    keys = ('analysis_id', 'attempt', 'stage', 'execution_id', 'generation', 'request_hash')
    scope = dict(pipeline=pipeline, **{k:payload[k] for k in keys})

    def current():
        _registered_request(payload, gate, pipeline)
        value = json.loads(_read_registered(status_path))
        if (not isinstance(value, dict)
                or any(type(value.get(k)) is not type(payload[k]) or value[k] != payload[k] for k in keys)
                or value.get('status') not in {'accepted', 'running'}):
            raise RuntimeError('registered monitor status changed or terminal')
        return value

    def save(state):
        previous = current()
        payload['_monitor_reconnect'] = state
        progress = {k:previous[k] for k in ('progress_percent', 'completed_units', 'total_units', 'unit', 'current_item',
                    'master', 'master_job', 'namespace', 'run_label', 'monitoring_error')
                    if k in previous}
        if state['phase'] == 'healthy':
            if observation is None:
                raise RuntimeError('query confirmation requires the complete current Master observation')
            value, binding = observation()
            if not isinstance(value, dict) or not isinstance(binding, dict):
                raise RuntimeError('invalid confirmed Master observation')
            if pipeline == 'wgs':
                progress = dict(master=value, master_job=binding.get('master_job'),
                    namespace=binding.get('namespace'), run_label=gate._binding_run_label(binding))
            else:
                progress = dict(
                    progress_percent=int(float(value['percent'])) if value.get('percent') is not None else None,
                    completed_units=int(value['completed']) if value.get('completed') is not None else None,
                    total_units=int(value['total']) if value.get('total') is not None else None,
                    unit='rules', current_item=value.get('current_rule'))
            # Query recovery does not confirm that the rule-evidence bridge
            # recovered. The ordinary collector is the authority for that.
            if 'monitoring_error' in previous:
                progress['monitoring_error'] = previous['monitoring_error']
            if previous.get('monitoring_error'):
                progress['monitoring_health'] = 'degraded'
        # Non-healthy writes keep a new control timestamp. Existing consumers
        # retain the old business time while query_unconfirmed is true.
        # Receipt identity is still emitted only by the verified gate writer;
        # never copy cce_master_binding or receipt fields out of the old JSON.
        message = 'Monitor observation confirmed' if state['phase'] == 'healthy' else 'Monitor query unavailable; execution state unconfirmed'
        if pipeline == 'wgs':
            if not gate._write_status(payload, 'running', message, **progress):
                raise RuntimeError('registered monitor status refused query reservation')
        else:
            gate._write_status(path, payload, 'running', message, **progress)
            # GATK's ordinary atomic writer does not fsync; a retry reservation must.
            for target in (status_path, status_path.parent):
                fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
                try: os.fsync(fd)
                finally: os.close(fd)
    return QueryReconnect(scope=scope, deadline=deadline,
        load=lambda: current().get('monitor_reconnect'), save=save, error_type=runtime.RecoveryQueryError)


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
    # Step6 has no frozen final-release deadline. Step3's compute deadline and
    # Step4's publish deadline do not govern this later read-only finalization.
    release_query_deadline = time.monotonic() + 120
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
                _source_history(_registered_journal_root(payload,gate,pipeline),pipeline,runtime,bundle,contract,selected))
            probe_final_workloads(runtime=runtime, config=config,
                namespace=contract['kubernetes']['namespace'], run_label=binding['run_label'],
                master_job=contract['kubernetes']['master_job'], master_job_uid=uid,
                master_state='SUCCEEDED', workers=workers,
                query_deadline_monotonic=release_query_deadline, reconnect_transient=True)
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
            journal=writer.journal,save_journal=writer.save_journal,verify=proof,
            release_query_deadline=release_query_deadline)


def _selected_registered(payload, *, binding, gate, pipeline, operation=None, runtime=None, query_owner=None):
    """Reconstruct a selected Master in a new restricted monitor process.

    A receipt is a locator/checksum, not a capability. The registered producer,
    native journal, frozen input binding and current directory owner must agree.
    No replacement, takeover or missing-lock claim is performed by this reader.
    """
    runtime = runtime or load_runtime()
    if runtime is None:
        return None
    if (pipeline not in {'wgs', 'gatk'} or payload.get('orchestration_contract_version') != 2
            or payload.get('stage') not in {'step3_monitor','step4_publish','step5_download','step6_materialize'}):
        raise RuntimeError('selected stage requires registered Step3-Step6')
    path, raw = _registered_request(payload, gate, pipeline)
    bundle = Path(binding['cce_bundle'])
    contract, config, modules = runtime._load(bundle, None)
    if query_owner is not None:
        # ProtectedWriter snapshots config with deepcopy. A closure preserves
        # the one durable owner; copying a bound method would clone that owner.
        config = {**config, '_monitor_query_runner': lambda query: query_owner.run(query)}
    writer = _registered_writer(runtime, bundle, contract, config, payload, gate, pipeline)
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
    if (source.get('orchestration_contract_version') != 2
            or (action is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(action)))
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
            for v in _journal_views(_registered_journal_root(payload,gate,pipeline),pipeline,runtime,bundle,contract)):
        return _observe_registered_source(payload,binding,gate,pipeline,runtime,bundle,contract,config,modules,writer,operation)
    if __package__:
        from .cce_recovery_inventory import VerifiedMasterResult
    else:
        from cce_recovery_inventory import VerifiedMasterResult
    read_only = payload['stage'] == 'step3_monitor'
    with (nullcontext() if read_only else writer.serialize()):
        if not read_only:
            writer.validate()
        original = runtime._handoff_binding(bundle, contract)
        platform = dict(pipeline=pipeline, **{k:source[k] for k in keys})
        matches = [v for v in _journal_views(_registered_journal_root(payload,gate,pipeline),pipeline,runtime,bundle,contract)
            if v[3] == platform]
        if len(matches) != 1:
            raise RuntimeError('selected Master journal is missing or ambiguous')
        journal_path, selected_journal, selected, _ = matches[0]
        initial = 'identity' in selected_journal
        if initial:
            if journal_path.name != 'submission-'+source['execution_id']+'.json':
                raise RuntimeError('initial submit journal producer changed')
        else:
            if selected_journal.get('recovery_v2',{}).get('context',{}).get('action') != action:
                raise RuntimeError('recovery submit journal producer changed')
            parent = Path(selected_journal.get('registered_source',str(bundle)))
            allowed = [bundle, *[v[2] for v in _journal_views(_registered_journal_root(payload,gate,pipeline),pipeline,runtime,bundle,contract)]]
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
        if initial:
            action = writer.context['action']
        context = dict(pipeline=pipeline, analysis_id=source['analysis_id'],
            execution_id=source['execution_id'], generation=1 if initial else original['execution_generation']+1, action=action)
        if initial:
            journal_matches = (journal.get('state') == 'confirmed' and journal.get('identity') == dict(
                platform_execution=platform,source_bundle=str(bundle),selected_bundle=str(selected)))
            journal_uid = journal.get('job_uid')
        else:
            expected = dict(expected_job_uid=old['job_uid'], context=context, original=original,
                view=str(selected), platform_execution=platform)
            if journal.get('recovery_v2',{}).get('recovery_kind')=='initial_abort':
                abort_path=runtime._master_handoff_path(parent,contract).with_name('INITIAL_SUBMISSION_ABORT.json')
                abort_raw=_read_registered(abort_path)
                abort=runtime._validate_initial_submission_abort(json.loads(abort_raw))
                if (abort_raw!=runtime._recovery_encoded(abort) or abort['bundle']!=str(parent)
                        or abort['binding']!=original or abort['job_uid']!=old['job_uid']):
                    raise RuntimeError('selected Master initial abort changed')
                expected.update(recovery_kind='initial_abort',
                    initial_abort_sha256=hashlib.sha256(runtime._recovery_encoded(abort)).hexdigest())
            if __package__:
                from .cce_recovery_deadline import deadline_epoch
            else:
                from cce_recovery_deadline import deadline_epoch
            compute_deadline = deadline_epoch(source)
            if compute_deadline is not None:
                expected['compute_deadline'] = compute_deadline
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
        writer.context.update(_resolve_selected_owner(runtime,bundle,selected,contract,config,record,platform,writer))
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
                    master_bundle=selected, expected_master_uid=record['job_uid'],read_only=True)
            value = json.loads(output.getvalue())
        else:
            value = operation(runtime,bundle,selected,record['job_uid'],contract,config,modules,writer)
        proof = _automatic_failure_evidence(payload,value,runtime=runtime,bundle=bundle,selected=selected,
            contract=contract,config=config,run_label=binding['run_label'],exported=exported,
            request_root=_registered_journal_root(payload,gate,pipeline),pipeline=pipeline)
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
