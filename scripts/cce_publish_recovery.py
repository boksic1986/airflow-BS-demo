"""Identity-bound Step4 dispatcher observations; no publish, retry or cloud scan."""
import hashlib
import json
import re
from datetime import datetime,timezone

if __package__:
    from .cce_paired_runtime import _exclusive, _read_registered, _registered_request
else:
    from cce_paired_runtime import _exclusive, _read_registered, _registered_request

KEYS = ('analysis_id', 'attempt', 'stage', 'execution_id', 'generation', 'request_hash')
TERMINAL = {'success', 'complete', 'succeeded', 'failed', 'canceled'}


def registered_publish(payload, *, gate, pipeline):
    if (pipeline not in {'wgs', 'gatk'} or payload.get('stage') != 'step4_publish'
            or type(payload.get('publish_dispatch_version')) is not int
            or payload['publish_dispatch_version'] != 1
            or payload.get('orchestration_contract_version') != 2
            or any(not payload.get(k) for k in KEYS)):
        raise ValueError('Step4 requires the registered publish dispatch contract')
    return _registered_request(payload, gate, pipeline)


def require_publish_deadline(payload):
    try:
        deadline=datetime.fromisoformat(payload['publish_deadline'])
        if deadline.tzinfo is None or datetime.now(timezone.utc)>=deadline:
            raise ValueError('expired')
    except (KeyError,TypeError,ValueError):
        raise ValueError('Step4 original dispatch deadline is missing or exhausted') from None


def publish_dispatch_command(arguments, *, gate, pipeline):
    if (len(arguments)!=5 or arguments[0]!='--publish-dispatch'
            or not re.fullmatch('[A-Za-z0-9_-]{1,128}',arguments[1])
            or not re.fullmatch('[1-9][0-9]{0,8}',arguments[2])
            or not re.fullmatch('[1-9][0-9]{0,8}',arguments[3])
            or not re.fullmatch('[0-9a-f]{64}',arguments[4])):
        raise ValueError('invalid restricted Step4 dispatch command')
    _,aid,attempt,generation,digest=arguments
    if pipeline=='gatk':
        return gate.start(aid,int(attempt),'step4_publish',int(generation),expected_hash=digest)
    if pipeline!='wgs':raise ValueError('invalid Step4 pipeline')
    payload=gate.load_request(aid,int(attempt),'step4_publish')
    if payload.get('generation')!=int(generation) or payload.get('request_hash')!=digest:
        raise ValueError('Step4 dispatch was superseded')
    registered_publish(payload,gate=gate,pipeline=pipeline)
    if __package__:
        from .wgs_release_runtime import select_release_runtime
    else:
        from wgs_release_runtime import select_release_runtime
    gate.CCE_PIPELINE_BIN=select_release_runtime(payload,default_cli=gate.CCE_PIPELINE_BIN)
    # start_async_stage revalidates these exact bytes under the launch lock.
    return gate.start_async_stage(payload)


def _record(path, payload):
    try:
        value = json.loads(_read_registered(path))
    except FileNotFoundError:
        return None
    if (not isinstance(value, dict) or any(type(value.get(k)) is not type(payload[k])
            or value[k] != payload[k] for k in KEYS)):
        raise ValueError('Step4 evidence belongs to another operation')
    return value


def observe_locked(payload, *, gate, pipeline):
    """Caller holds the original launch lock. Absence alone never grants replay."""
    path, raw = registered_publish(payload, gate=gate, pipeline=pipeline)
    receipt = _record(path.with_suffix('.status.json'), payload)
    worker = _record(path.with_suffix('.worker.json' if pipeline == 'wgs' else '.worker.state.json'), payload)
    if worker:
        if pipeline == 'wgs':
            if worker.get('request_sha256') != hashlib.sha256(raw).hexdigest():
                raise ValueError('Step4 dispatcher request changed')
        elif worker.get('schema_version') != 'gatk-runtime.dispatcher.v1':
            raise ValueError('Step4 dispatcher evidence is invalid')
    if receipt and receipt.get('status') in TERMINAL:
        if pipeline == 'gatk':
            digest = hashlib.sha256(json.dumps({k:v for k,v in receipt.items() if k != 'receipt_hash'},
                sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            if receipt.get('receipt_hash') != digest:
                raise ValueError('Step4 receipt digest differs')
        return receipt['status']
    if worker:
        if pipeline == 'wgs':
            active = gate._process_matches(worker)
        else:
            process = worker.get('process')
            active = (isinstance(process, dict) and type(process.get('pid')) is int
                and process['pid'] > 0 and gate._process_identity(process['pid']) == process)
        if active:
            return 'running'
    # A dead parent, intent without PID, malformed legacy evidence or an occupied
    # executor lock is not proof that a publish child never started.
    if worker is not None or receipt is not None:
        return 'uncertain'
    try:
        with _exclusive(path.with_suffix('.worker.lock')):
            return 'not_started'
    except BlockingIOError:
        return 'uncertain'


def observe_publish(payload, *, gate, pipeline, nonce):
    if not isinstance(nonce, str) or not re.fullmatch('[0-9a-f]{32}', nonce):
        raise ValueError('invalid Step4 observation challenge')
    path, _ = registered_publish(payload, gate=gate, pipeline=pipeline)
    try:
        with _exclusive(path.with_suffix('.launch.lock')):
            status = observe_locked(payload, gate=gate, pipeline=pipeline)
    except BlockingIOError:
        status = 'uncertain'
    return dict(schema_version='cce.publish-observation.v1', pipeline=pipeline,
        **{k:payload[k] for k in KEYS}, nonce=nonce, status=status)


def publish_probe_command(arguments, *, gate, pipeline):
    if (len(arguments) != 6 or arguments[0] != '--publish-probe'
            or not re.fullmatch('[A-Za-z0-9_-]{1,128}', arguments[1])
            or not re.fullmatch('[1-9][0-9]{0,8}', arguments[2])
            or not re.fullmatch('[1-9][0-9]{0,8}', arguments[3])
            or not re.fullmatch('[0-9a-f]{64}', arguments[4])
            or not re.fullmatch('[0-9a-f]{32}', arguments[5])):
        raise ValueError('invalid restricted Step4 probe command')
    _, aid, attempt, generation, digest, nonce = arguments
    if pipeline == 'wgs':
        payload = gate.load_request(aid, int(attempt), 'step4_publish')
    elif pipeline == 'gatk':
        _, payload = gate._load(aid, int(attempt), 'step4_publish', int(generation))
    else:
        raise ValueError('invalid Step4 pipeline')
    if payload.get('generation') != int(generation) or payload.get('request_hash') != digest:
        raise ValueError('Step4 probe was superseded')
    return observe_publish(payload, gate=gate, pipeline=pipeline, nonce=nonce)
