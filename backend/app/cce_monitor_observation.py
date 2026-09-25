"""UI-only snapshot, called after the existing current-execution identity gate.

This is not a terminal receipt or recovery authorization. It retains only the
current monitor's observation and started-Master identity for read-only views.
"""
from datetime import datetime, timezone
import math

KEY = 'cce_monitor_observation'


def query_observation(row, payload, *, pipeline):
    """Authenticated status identity is necessary; a foreign budget is not evidence."""
    value = payload.get('monitor_reconnect')
    if value is None or row.stage_code != 'step3_monitor':
        return None
    expected = dict(pipeline=pipeline, analysis_id=row.analysis_id, attempt=row.attempt,
        stage=row.stage_code, execution_id=row.execution_id, generation=row.generation, request_hash=row.request_hash)
    scope = value.get('scope') if isinstance(value, dict) else None
    if (not isinstance(scope, dict) or scope != expected
            or any(type(scope.get(k)) is not type(v) for k,v in expected.items())
            or type(value.get('version')) is not int or value['version'] != 1
            or value.get('phase') not in {'healthy','waiting','querying','observing','blocked','exhausted'}
            or type(value.get('retries_used')) is not int or not 0 <= value['retries_used'] <= 6
            or type(value.get('deadline')) not in {int,float} or not math.isfinite(value['deadline'])
            or any(value.get(k) is not None and (type(value[k]) not in {int,float}
                   or not math.isfinite(value[k])) for k in ('next_retry_at','last_success_at'))):
        raise ValueError('invalid current monitor reconnect observation')
    return {k:value.get(k) for k in ('version','scope','deadline','phase','retries_used','next_retry_at','last_success_at')}


def _date(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def retain_monitor_observation(row, payload, *, pipeline, previous=None):
    if row.stage_code != 'step3_monitor':
        return
    old = previous or (row.terminal_payload_json or {}).get(KEY) or {}
    stamp = _date(payload.get('updated_at'))
    before = _date(old.get('observed_at'))
    if stamp is None or before and stamp <= before:
        if old:
            row.terminal_payload_json = {**(row.terminal_payload_json or {}), KEY: old}
        return
    health = payload.get('monitoring_health')
    reconnect = query_observation(row, payload, pipeline=pipeline)
    expected = dict(pipeline=pipeline, analysis_id=row.analysis_id, attempt=row.attempt,
        stage=row.stage_code, execution_id=row.execution_id, generation=row.generation,
        request_hash=row.request_hash)
    binding = payload.get('cce_master_binding')
    bound = None
    if isinstance(binding, dict) and binding.get('schema_version') == 2:
        platform = binding.get('platform_execution')
        native = binding.get('native')
        if isinstance(platform, dict) and isinstance(native, dict) and all(
                type(platform.get(k)) is type(v) and platform[k] == v for k,v in expected.items()):
            bound = dict(schema_version=2, platform_execution=expected,
                native={k:native.get(k) for k in ('job_uid','pod_uid','recovery_context')})
    snapshot = dict(observed_at=stamp.isoformat(),
        monitoring_health=health if health in {'healthy','degraded','error'} else None,
        last_success_at=stamp.isoformat() if health == 'healthy' else old.get('last_success_at'),
        cce_master_binding=bound)
    if reconnect:
        snapshot['monitor_reconnect'] = reconnect
        if reconnect.get('last_success_at') is not None:
            snapshot['last_success_at'] = datetime.fromtimestamp(reconnect['last_success_at'], timezone.utc).isoformat()
    row.terminal_payload_json = {**(row.terminal_payload_json or {}), KEY: snapshot}


def query_unconfirmed(row):
    payload = (row.terminal_payload_json or {}).get(KEY, {})
    value = payload.get('monitor_reconnect') or {}
    return value.get('phase') in {'waiting','querying','observing','blocked','exhausted'}
