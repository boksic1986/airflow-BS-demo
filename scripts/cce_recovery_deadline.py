"""Consume the authenticated original Step3 deadline; never initialize it here."""
from datetime import datetime
import time


def deadline_epoch(payload):
    if 'cce_recovery_deadline' not in payload:
        return None  # Legacy/default-off requests retain their existing behavior.
    value = payload['cce_recovery_deadline']
    try:
        if not isinstance(value, str):
            raise ValueError()
        deadline = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if deadline.tzinfo is None or deadline.utcoffset() is None:
            raise ValueError()
        return deadline.timestamp()
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError('invalid original compute deadline') from exc


def monitor_wait(payload, interval):
    """Check at every poll and bound sleep by the same persisted absolute time."""
    deadline = deadline_epoch(payload)
    if deadline is None:
        return interval
    remaining = deadline - time.time()
    if remaining <= 0:
        raise TimeoutError('original compute deadline exhausted; manual reconciliation required')
    return min(interval, remaining)
