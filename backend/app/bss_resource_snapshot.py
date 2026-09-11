"""Pure validated public billing spool contract (no SDK/network dependencies)."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

SCHEMA = 'bss-resource-balances.v1'
REASONS = {'dedicated_billing_credentials_missing', 'credential_permissions',
           'credential_invalid', 'sdk_unavailable', 'forbidden', 'rate_limited',
           'timeout', 'transport_error', 'incomplete_response', 'cache_stale',
           'invalid_snapshot', 'spool_unavailable'}
CATEGORIES = {'cpu_hours', 'memory_hours', 'obs_storage', 'obs_requests', 'other'}


def timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('invalid timestamp')
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None: raise ValueError('naive timestamp')
    return stamp


def decimal_value(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError('invalid amount')
    text = str(value)
    if len(text) > 64: raise ValueError('invalid amount')
    try: number = Decimal(text)
    except InvalidOperation: raise ValueError('invalid amount') from None
    if not number.is_finite() or number < 0 or number > Decimal('1e30'):
        raise ValueError('invalid amount')
    if number.as_tuple().exponent < -30: raise ValueError('invalid precision')
    return format(number, 'f')


def validate_items(rows):
    if not isinstance(rows, list) or len(rows) > 10000: raise ValueError('invalid rows')
    result, keys = [], set()
    for row in rows:
        key = row['key']
        if not isinstance(key, str) or not re.fullmatch(r'bss-[a-f0-9]{32}', key) or key in keys:
            raise ValueError('invalid key')
        keys.add(key)
        if row['category'] not in CATEGORIES: raise ValueError('invalid category')
        unit = row['unit']
        if not isinstance(unit, str) or not re.fullmatch(r'[\w ./*()·%-]{1,64}', unit):
            raise ValueError('invalid unit')
        total, remaining = decimal_value(row['total']), decimal_value(row['remaining'])
        if Decimal(remaining) > Decimal(total): raise ValueError('invalid remaining')
        start, end, expiry = (timestamp(row[k]) for k in ('period_start', 'period_end', 'expires_at'))
        if start >= end or end > expiry: raise ValueError('invalid period')
        if row['cycle'] not in ('hour', 'day', 'week', 'month', 'year', 'non_resetting'):
            raise ValueError('invalid cycle')
        if row['cycle_type'] not in ('calendar', 'subscription', 'non_resetting'):
            raise ValueError('invalid cycle type')
        result.append(dict(key=key, category=row['category'], unit=unit,
            total=total, remaining=remaining, period_start=row['period_start'],
            period_end=row['period_end'], expires_at=row['expires_at'],
            cycle=row['cycle'], cycle_type=row['cycle_type']))
    return result


def unavailable(reason='dedicated_billing_credentials_missing', status='not_configured'):
    return dict(schema_version=SCHEMA, status=status, reason=reason, items=[],
                updated_at=None, checked_at=None, source='Huawei Cloud BSS', interval_seconds=3600)


def project(payload, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        if not isinstance(payload, dict) or payload.get('schema_version') != SCHEMA:
            raise ValueError('invalid schema')
        reason = payload.get('reason')
        if reason is not None and reason not in REASONS: raise ValueError('invalid reason')
        status = payload['status']
        if status not in ('healthy', 'stale', 'unavailable', 'not_configured'): raise ValueError('invalid status')
        checked = payload.get('checked_at')
        if checked is not None: timestamp(checked)
        result = unavailable(reason, status)
        result.update(items=validate_items(payload['items']), checked_at=checked)
        updated = payload.get('updated_at')
        if updated is not None:
            age = (now-timestamp(updated)).total_seconds()
            if age < -10: raise ValueError('future timestamp')
            result['updated_at'] = updated
            if age > 5400 and status == 'healthy':
                result.update(status='stale', reason='cache_stale')
        elif result['items'] or status == 'healthy':
            raise ValueError('missing timestamp')
        return result
    except (KeyError, TypeError, ValueError, OverflowError):
        return unavailable('invalid_snapshot', 'unavailable')


def read_snapshot(root, now=None):
    if not root: return unavailable('spool_unavailable', 'unavailable')
    path = Path(root) / 'bss-resources.json'
    try:
        if path.is_symlink() or path.stat().st_size > 8_000_000:
            return unavailable('invalid_snapshot', 'unavailable')
        return project(json.loads(path.read_text()), now=now)
    except FileNotFoundError: return unavailable('spool_unavailable', 'unavailable')
    except (OSError, ValueError): return unavailable('spool_unavailable', 'unavailable')
