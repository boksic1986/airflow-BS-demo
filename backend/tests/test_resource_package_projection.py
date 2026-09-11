import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Base
from app.platform_resources_service import get_platform_resources
from app.bss_resource_snapshot import project, read_snapshot


def snapshot():
    return dict(schema_version='bss-resource-balances.v1', status='healthy', reason=None,
        updated_at='2026-09-12T00:00:00Z', checked_at='2026-09-12T00:00:00Z',
        account_id='must-not-leak', error_msg='raw-private',
        items=[dict(key='bss-'+'a'*32, category='cpu_hours', unit='core-hours',
            remaining='12.123456789012345678', total='100.25', period_start='2026-09-01T00:00:00Z',
            period_end='2026-10-01T00:00:00Z', expires_at='2027-01-01T00:00:00Z', cycle='month',
            cycle_type='calendar', order_id='must-not-leak')])


def test_api_spool_projection_is_safe_precise_and_stale(tmp_path):
    data = snapshot()
    (tmp_path/'bss-resources.json').write_text(json.dumps(data))
    (tmp_path/'heavy-slot-global.json').write_text(json.dumps(dict(schema_version='wgs-heavy-global.v2',
        complete=True, updated_at=datetime.now(timezone.utc).isoformat(), used=11, limit=25, waiting=None,
        mode='enforce', reasons={'waiting': 'waiting_snapshot_unavailable'})))
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        result = get_platform_resources(session=session, evidence_root=str(tmp_path),
            now=datetime(2026, 9, 12, 2, tzinfo=timezone.utc))
    package = result['resource_packages']
    assert package['status'] == 'stale'
    assert package['reason'] == 'cache_stale'
    assert package['items'][0]['remaining'] == '12.123456789012345678'
    assert 'must-not-leak' not in json.dumps(result)
    assert 'raw-private' not in json.dumps(result)
    assert result['heavy_slot']['used'] == 11
    assert result['heavy_slot']['waiting'] is None


def test_projection_rejects_malformed_unsafe_values_and_links(tmp_path):
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    for update in [dict(remaining='NaN'), dict(total='-1'), dict(remaining='101'),
                   dict(unit='https://credentials.example'), dict(key='private-order'),
                   dict(period_end='2028-01-01T00:00:00Z')]:
        data = snapshot()
        data['items'][0].update(update)
        assert project(data, now)['status'] == 'unavailable'
    target = tmp_path/'source.json'
    target.write_text(json.dumps(snapshot()))
    (tmp_path/'bss-resources.json').symlink_to(target)
    assert read_snapshot(tmp_path, now)['status'] == 'unavailable'


def test_missing_spool_does_not_claim_credential_configuration(tmp_path):
    assert read_snapshot(tmp_path)['status'] == 'unavailable'
    assert read_snapshot(tmp_path)['reason'] == 'spool_unavailable'
    assert read_snapshot(tmp_path)['items'] == []
