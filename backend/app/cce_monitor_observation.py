"""UI-only snapshot, called after the existing current-execution identity gate.

This is not a terminal receipt or recovery authorization. It retains only the
current monitor's observation and started-Master identity for read-only views.
"""
from datetime import datetime, timezone

KEY = 'cce_monitor_observation'


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
    row.terminal_payload_json = {**(row.terminal_payload_json or {}), KEY: snapshot}
