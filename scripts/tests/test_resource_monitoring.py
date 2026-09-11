"""Synthetic telemetry only: no cloud client or credential is used."""
import importlib.util
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_complete_lease_inventory_survives_missing_waiting(tmp_path):
    heavy = module('heavy', ROOT / 'backend/app/heavy_global_snapshot.py')
    leases = {'items': [{'metadata': {'name': f'wgs-heavy-io-{i:02d}'},
                        'spec': {'holderIdentity': 'old-reservation' if i < 11 else ''}}
                       for i in range(25)]}
    jobs = {'items': [{'metadata': {'labels': {'cce.biosan.cn/run-id': 'external'}},
                      'spec': {'template': {'spec': {'containers': [{'env': [
                          {'name': 'WGS_HEAVY_SLOT_MODE', 'value': 'enforce'},
                          {'name': 'WGS_HEAVY_SLOT_LIMIT', 'value': '25'}]}]}}}}]}
    class Result:
        def __init__(self, value): self.stdout = json.dumps(value)
        def check_returncode(self): pass
    with patch.object(heavy.subprocess, 'run', side_effect=[Result(leases), Result(jobs)]):
        result = heavy.project_snapshot(heavy.collect(['kubectl'], tmp_path))
    assert result['used'] == 11
    assert result['limit'] == 25
    assert result['waiting'] is None
    assert result['mode'] == 'enforce'
    assert result['available'] is False  # compatibility: all fields not available
    assert result['unit'] == 'heavy_work_job'
    assert result['fields']['used']['status'] == 'fresh'
    assert result['fields']['waiting']['reason'] == 'waiting_snapshot_unavailable'


def test_stale_heavy_retains_last_known_not_current_zero():
    heavy = module('heavy_stale', ROOT / 'backend/app/heavy_global_snapshot.py')
    result = heavy.project_snapshot(dict(schema_version='wgs-heavy-global.v1', complete=True,
        updated_at=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat(),
        used=11, limit=25, waiting=2, mode='enforce'))
    assert result['used'] == 11
    assert result['available'] is False
    assert result['fields']['used']['status'] == 'stale'


def billing():
    return module('billing', ROOT / 'scripts/collect_bss_resources.py')


def fixture_transport(count=2, mutate=None):
    calls = []
    def transport(method, path, body):
        calls.append((method, path, body))
        if path.endswith('/measurements'):
            return {'measure_units': [dict(measure_id=917, measure_name='core-hours', abbreviation='core-h', measure_type=27),
                                     dict(measure_id=918, measure_name='GiB-hours', abbreviation='GiB-h', measure_type=28)]}
        if path == '/v3/payments/free-resources/query':
            rows = [dict(order_instance_id=f'private-order-{i}', quota_reuse_mode=1,
                service_type_code='hws.service.type.cce', expire_time='2027-01-01T00:00:00Z',
                free_resources=[{'free_resource_id': f'private-resource-{i}'}])
                for i in range(body['offset'], min(count, body['offset'] + body['limit']))]
            return dict(total_count=count, free_resource_packages=rows)
        rows = [dict(free_resource_id=key, measure_id=917 if key.endswith('0') else 918,
            amount='12.123456789012345678', original_amount='100.25', quota_reuse_cycle=4,
            quota_reuse_cycle_type=1, start_time='2026-09-01T00:00:00Z', end_time='2026-10-01T00:00:00Z')
            for key in body['free_resource_ids']]
        if mutate: mutate(rows)
        return {'free_resources': rows}
    return transport, calls


def test_bss_batches_dictionary_decimal_and_private_ids():
    transport, calls = fixture_transport(count=102)
    rows = billing().collect(transport, page_size=40)
    assert len(rows) == 102
    assert rows[0]['remaining'] == '12.123456789012345678'
    assert rows[0]['total'] == '100.25'
    assert rows[0]['category'] == 'cpu_hours'
    assert rows[1]['category'] == 'memory_hours'
    assert rows[0]['unit'] == 'core-hours'
    assert rows[1]['unit'] == 'GiB-hours'
    assert rows[0]['cycle'] == 'month'
    assert rows[0]['cycle_type'] == 'calendar'
    assert 'private-' not in json.dumps(rows)
    assert [c[2]['offset'] for c in calls if c[1] == '/v3/payments/free-resources/query'] == [0, 40, 80]
    assert [len(c[2]['free_resource_ids']) for c in calls if 'usages/details' in c[1]] == [100, 2]


def test_bss_rejects_incomplete_duplicate_and_invalid_numeric():
    import pytest
    for mutate in [lambda rows: rows.pop(), lambda rows: rows.append(rows[0]),
                   lambda rows: rows[0].update(amount='NaN'),
                   lambda rows: rows[0].update(amount='101'),
                   lambda rows: rows[0].update(measure_id=999),
                   lambda rows: rows[0].update(amount='-1')]:
        transport, _ = fixture_transport(mutate=mutate)
        with pytest.raises(ValueError): billing().collect(transport)


def test_hourly_cache_and_failed_refresh_keep_last_good(tmp_path):
    bss = billing()
    path = tmp_path / 'bss-resources.json'
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    transport, calls = fixture_transport()
    first = bss.refresh(path, transport=transport, now=now)
    assert first['status'] == 'healthy'
    count = len(calls)
    assert bss.refresh(path, transport=transport, now=now + timedelta(minutes=59)) == first
    assert len(calls) == count
    def denied(*args): raise bss.BssError('forbidden')
    failed = bss.refresh(path, transport=denied, now=now + timedelta(hours=1))
    assert failed['status'] == 'stale'
    assert failed['reason'] == 'forbidden'
    assert failed['items'] == first['items']
    assert failed['updated_at'] == first['updated_at']
    assert bss.refresh(path, transport=transport, now=now + timedelta(minutes=61)) == failed


def test_missing_billing_credentials_never_constructs_client(tmp_path):
    bss = billing()
    with patch.object(bss, 'signed_transport', side_effect=AssertionError('must not sign')):
        result = bss.refresh(tmp_path/'bss-resources.json', credentials_path=None)
    assert result['status'] == 'not_configured'
    assert result['reason'] == 'dedicated_billing_credentials_missing'
    assert result['items'] == []


def test_credentials_are_dedicated_owner_only_and_endpoint_not_configurable(tmp_path):
    import pytest
    bss = billing()
    tmp_path.chmod(0o700)
    path = tmp_path/'billing.json'
    value = dict(ak='synthetic', sk='synthetic', domain_id='synthetic', purpose='billing_readonly')
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    assert bss.load_credentials(path)['purpose'] == 'billing_readonly'
    path.chmod(0o644)
    with pytest.raises(bss.BssError, match='credential_permissions'): bss.load_credentials(path)
    path.chmod(0o600)
    path.write_text(json.dumps(dict(value, endpoint='https://foreign.example')))
    with pytest.raises(bss.BssError, match='credential_invalid'): bss.load_credentials(path)


def test_bss_stalled_pagination_and_changing_total_are_rejected():
    import pytest
    for kind in ('stalled', 'duplicate', 'changing', 'bounded'):
        original, calls = fixture_transport(count=4)
        def transport(method, path, body):
            result = original(method, path, body)
            if path == '/v3/payments/free-resources/query':
                if kind == 'bounded': result['total_count'] = 10001
                if body['offset']:
                    if kind == 'stalled': result['free_resource_packages'] = []
                    if kind == 'duplicate': result['free_resource_packages'][0]['order_instance_id'] = 'private-order-0'
                    if kind == 'changing': result['total_count'] = 5
            return result
        with pytest.raises(ValueError): billing().collect(transport, page_size=2)


def test_heavy_rejects_duplicate_lease_inventory(tmp_path):
    import pytest
    heavy = module('heavy_duplicates', ROOT / 'backend/app/heavy_global_snapshot.py')
    rows = [{'metadata': {'name': f'wgs-heavy-io-{i:02d}'}, 'spec': {}} for i in range(25)]
    class Result:
        stdout = json.dumps({'items': rows + [rows[0]]})
        def check_returncode(self): pass
    with patch.object(heavy.subprocess, 'run', return_value=Result()):
        with pytest.raises(ValueError): heavy.collect(['kubectl'], tmp_path)


def test_waiting_age_is_not_reset_by_lease_refresh():
    heavy = module('heavy_ages', ROOT / 'backend/app/heavy_global_snapshot.py')
    now = datetime.now(timezone.utc)
    result = heavy.project_snapshot(dict(schema_version='wgs-heavy-global.v2', complete=True,
        updated_at=now.isoformat(), waiting_updated_at=(now-timedelta(minutes=4)).isoformat(),
        used=11, limit=25, waiting=2, mode='enforce'), now=now)
    assert result['fields']['used']['status'] == 'fresh'
    assert result['fields']['waiting']['status'] == 'stale'


def test_standalone_packaging_and_unconfigured_once_publish(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    for source, name in [('scripts/heavy_global_snapshot.py', 'heavy_global_snapshot.py'),
                         ('backend/app/heavy_global_snapshot.py', 'heavy_snapshot_core.py'),
                         ('scripts/collect_bss_resources.py', 'collect_bss_resources.py'),
                         ('backend/app/bss_resource_snapshot.py', 'bss_resource_snapshot.py')]:
        shutil.copyfile(ROOT/source, tmp_path/name)
    env = dict(os.environ)
    env.pop('BSS_READONLY_CREDENTIALS', None)
    for script in ('heavy_global_snapshot.py', 'collect_bss_resources.py'):
        result = subprocess.run([sys.executable, str(tmp_path/script), '--help'], env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    result = subprocess.run([sys.executable, str(tmp_path/'collect_bss_resources.py'), '--root', str(tmp_path), '--once'],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)['status'] == 'not_configured'
    assert json.loads((tmp_path/'bss-resources.json').read_text())['items'] == []


def test_launchers_fail_without_explicit_environment_without_starting_process(tmp_path):
    import subprocess
    for script in ('start_heavy_slot_collector.sh', 'start_bss_resource_collector.sh'):
        result = subprocess.run(['/bin/bash', str(ROOT/'scripts'/script)],
            env={'PATH': '/usr/bin:/bin'}, cwd=tmp_path, capture_output=True, text=True)
        assert result.returncode != 0
        assert 'CONFIG_ROOT' in result.stderr
        assert list(tmp_path.iterdir()) == []


def test_heavy_failed_refresh_preserves_old_reservations(tmp_path):
    heavy = module('heavy_refresh', ROOT/'backend/app/heavy_global_snapshot.py')
    stamp = datetime.now(timezone.utc).isoformat()
    path = tmp_path/'heavy-slot-global.json'
    path.write_text(json.dumps(dict(schema_version='wgs-heavy-global.v2', complete=True,
        updated_at=stamp, used=11, limit=25, waiting=None, mode='enforce')))
    config = tmp_path/'synthetic.yaml'
    config.write_text('kubernetes:\n  kubectl_bin: kubectl\n  kubeconfig: synthetic\n  namespace: synthetic\n')
    with patch('sys.argv', ['heavy', '--config', str(config), '--root', str(tmp_path), '--once']), \
         patch.object(heavy, 'collect', side_effect=TimeoutError('private-token must not escape')):
        heavy.main()
    result = heavy.read_snapshot(tmp_path)
    assert result['used'] == 11
    assert result['fields']['used']['status'] == 'stale'
    assert result['fields']['used']['reason'] == 'refresh_failed'
    assert 'private-token' not in path.read_text()


def test_heavy_public_projection_rejects_raw_timestamp_and_malformed_reasons():
    heavy = module('heavy_bad_payload', ROOT/'backend/app/heavy_global_snapshot.py')
    data = dict(schema_version='wgs-heavy-global.v2', complete=True, updated_at='private-secret-not-a-time',
                used=11, limit=25, waiting=None, mode='enforce', reasons=None)
    result = heavy.project_snapshot(data)
    assert result['used'] is None
    assert 'private-secret' not in json.dumps(result)


def test_obs_categories_use_usage_semantics_not_measure_id_or_quantity_alone():
    original, _ = fixture_transport(count=2)
    def transport(method, path, body):
        result = original(method, path, body)
        if path.endswith('/measurements'):
            result = {'measure_units': [dict(measure_id=917, measure_name='GB', measure_type=3),
                                       dict(measure_id=918, measure_name='requests', measure_type=4)]}
        elif path == '/v3/payments/free-resources/query':
            for package in result['free_resource_packages']: package['service_type_code'] = 'hws.service.type.obs'
        else:
            result['free_resources'][0]['usage_type_name'] = 'Standard storage'
            result['free_resources'][1]['usage_type_name'] = 'GET requests'
        return result
    rows = billing().collect(transport)
    assert [row['category'] for row in rows] == ['obs_storage', 'obs_requests']
    assert [row['unit'] for row in rows] == ['GB', 'requests']
