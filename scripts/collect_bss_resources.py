"""Hourly read-only BSS balances, dedicated credentials, numeric public spool.

Only three fixed official API routes are reachable. Cloud SDK imports are lazy;
backend reads the validated spool without SDK bindings or a billing identity.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import time

_source = Path(__file__).with_name('bss_resource_snapshot.py')
if not _source.is_file():
    _source = Path(__file__).resolve().parents[1] / 'backend/app/bss_resource_snapshot.py'
_spec = importlib.util.spec_from_file_location('bss_resource_contract', _source)
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)

HOST = 'bss.myhuaweicloud.com'
LIST = '/v3/payments/free-resources/query'
USAGE = '/v2/payments/free-resources/usages/details/query'
UNITS = '/v2/bases/measurements'
ROUTES = {('POST', LIST), ('POST', USAGE), ('GET', UNITS)}


class BssError(ValueError):
    pass


def load_credentials(path):
    if not path: raise BssError('dedicated_billing_credentials_missing')
    path = Path(path)
    try:
        info, parent = path.lstat(), path.parent.lstat()
        if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
                or not stat.S_ISDIR(parent.st_mode) or stat.S_IMODE(parent.st_mode) != 0o700
                or info.st_uid != os.geteuid() or parent.st_uid != os.geteuid()):
            raise BssError('credential_permissions')
        if info.st_size > 8192: raise BssError('credential_invalid')
        value = json.loads(path.read_text())
        if (set(value) != {'ak', 'sk', 'domain_id', 'purpose'}
                or value['purpose'] != 'billing_readonly'
                or any(not isinstance(value[k], str) or not value[k].strip() for k in ('ak', 'sk', 'domain_id'))):
            raise BssError('credential_invalid')
        return value
    except FileNotFoundError: raise BssError('dedicated_billing_credentials_missing') from None
    except (OSError, json.JSONDecodeError, TypeError): raise BssError('credential_invalid') from None


def signed_transport(credentials, session=None):
    try:
        from huaweicloudsdkcore.auth.credentials import GlobalCredentials
        from huaweicloudsdkcore.sdk_request import SdkRequest
        import requests
    except ImportError: raise BssError('sdk_unavailable') from None
    signer = GlobalCredentials(credentials['ak'], credentials['sk'], credentials['domain_id'])
    http = session or requests.Session()
    http.trust_env = False  # no proxy/netrc credential forwarding
    def request(method, path, body):
        if (method, path) not in ROUTES: raise BssError('transport_error')
        data = json.dumps(body, separators=(',', ':')) if body is not None else ''
        req = SdkRequest(method=method, schema='https', host=HOST, resource_path=path,
            uri=path, query_params=[], header_params={'Content-Type': 'application/json', 'X-Language': 'en_US'}, body=data)
        signed = signer.sign_request(req)  # supplied domain; never IAM auto-discovery
        try:
            response = http.request(method, 'https://' + HOST + path, headers=signed.header_params,
                data=data, timeout=(10, 30), allow_redirects=False)
            if response.status_code == 403: raise BssError('forbidden')
            if response.status_code == 429: raise BssError('rate_limited')
            if response.status_code != 200: raise BssError('transport_error')
            if len(response.content) > 8_000_000: raise BssError('incomplete_response')
            return json.loads(response.content, parse_float=Decimal)
        except requests.Timeout: raise BssError('timeout') from None
        except requests.RequestException: raise BssError('transport_error') from None
    return request


def collect(transport, page_size=1000):
    if type(page_size) is not int or not 1 <= page_size <= 1000: raise ValueError('invalid page size')
    def query(method, path, body=None):
        value = transport(method, path, body)
        if not isinstance(value, dict) or value.get('error_code'): raise BssError('incomplete_response')
        return value
    dictionary = query('GET', UNITS).get('measure_units')
    if not isinstance(dictionary, list) or len(dictionary) > 10000: raise BssError('incomplete_response')
    units = {}
    for row in dictionary:
        key = row['measure_id']
        if type(key) is not int or key in units: raise BssError('incomplete_response')
        units[key] = row
    packages, seen, expected = [], set(), None
    for _ in range(100):
        value = query('POST', LIST, {'offset': len(packages), 'limit': page_size})
        total, rows = value.get('total_count'), value.get('free_resource_packages')
        if (type(total) is not int or not 0 <= total <= 10000
                or not isinstance(rows, list) or len(rows) > page_size
                or (expected is not None and total != expected)):
            raise BssError('incomplete_response')
        expected = total
        for row in rows:
            key = row['order_instance_id']
            if not isinstance(key, str) or not key or key in seen: raise BssError('incomplete_response')
            seen.add(key)
            packages.append(row)
        if len(packages) == total: break
        if not rows or len(packages) > total: raise BssError('incomplete_response')
    else: raise BssError('incomplete_response')
    resources = {}
    for package in packages:
        if not isinstance(package.get('free_resources'), list): raise BssError('incomplete_response')
        for row in package['free_resources']:
            key = row['free_resource_id']
            if not isinstance(key, str) or not 1 <= len(key) <= 64 or key in resources:
                raise BssError('incomplete_response')
            resources[key] = package
            if len(resources) > 10000: raise BssError('incomplete_response')
    output, keys = [], list(resources)
    for offset in range(0, len(keys), 100):
        batch = keys[offset:offset+100]
        rows = query('POST', USAGE, {'free_resource_ids': batch}).get('free_resources')
        if not isinstance(rows, list) or len(rows) != len(batch): raise BssError('incomplete_response')
        seen = set()
        for row in rows:
            key = row['free_resource_id']
            if key not in batch or key in seen: raise BssError('incomplete_response')
            seen.add(key)
            package = resources[key]
            unit = units.get(row['measure_id'])
            if not unit: raise BssError('incomplete_response')
            measure_type = unit.get('measure_type')
            category = {27: 'cpu_hours', 28: 'memory_hours'}.get(measure_type, 'other')
            if package.get('service_type_code', '').lower() == 'hws.service.type.obs':
                # GB can belong to the dictionary's flow dimension even for a
                # storage allowance. Quantity alone does not prove requests.
                usage = str(row.get('usage_type_name', '')).lower()
                if measure_type in (3, 7, 13, 15, 17) and any(word in usage for word in ('storage', '存储')):
                    category = 'obs_storage'
                elif measure_type in (4, 12) and any(word in usage for word in ('request', '请求')):
                    category = 'obs_requests'
                else:
                    category = 'other'
            reuse = package.get('quota_reuse_mode')
            cycle = {1: 'hour', 2: 'day', 3: 'week', 4: 'month', 5: 'year'}.get(row.get('quota_reuse_cycle')) if reuse == 1 else 'non_resetting' if reuse == 2 else None
            cycle_type = {1: 'calendar', 2: 'subscription'}.get(row.get('quota_reuse_cycle_type')) if reuse == 1 else 'non_resetting' if reuse == 2 else None
            output.append(dict(key='bss-'+hashlib.sha256(key.encode()).hexdigest()[:32], category=category,
                unit=unit.get('measure_name') or unit.get('abbreviation'), total=contract.decimal_value(row['original_amount']),
                remaining=contract.decimal_value(row['amount']), period_start=row['start_time'], period_end=row['end_time'],
                expires_at=package['expire_time'], cycle=cycle, cycle_type=cycle_type))
    return contract.validate_items(output)


def refresh(path, *, transport=None, credentials_path=None, now=None):
    now = now or datetime.now(timezone.utc)
    path = Path(path)
    previous = contract.read_snapshot(path.parent, now=now)
    checked = previous.get('checked_at')
    if checked and 0 <= (now-contract.timestamp(checked)).total_seconds() < 3600:
        return previous
    try:
        transport = transport or signed_transport(load_credentials(credentials_path))
        rows = collect(transport)
        result = dict(schema_version=contract.SCHEMA, status='healthy', reason=None, items=rows,
                      updated_at=now.isoformat(), checked_at=now.isoformat(), source='Huawei Cloud BSS', interval_seconds=3600)
    except Exception as error:
        reason = str(error) if isinstance(error, BssError) and str(error) in contract.REASONS else 'incomplete_response'
        result = dict(previous)
        result.update(status='stale' if previous['updated_at'] else 'not_configured' if reason == 'dedicated_billing_credentials_missing' else 'unavailable',
                      reason=reason, checked_at=now.isoformat())
    if path.is_symlink() or not path.parent.is_dir(): raise ValueError('invalid spool path')
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.bss-')
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(result, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, 0o644)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--credentials', default=os.environ.get('BSS_READONLY_CREDENTIALS'))
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    if root.is_symlink() or not root.is_dir(): raise ValueError('invalid evidence root')
    while True:
        result = refresh(root/'bss-resources.json', credentials_path=args.credentials)
        print(json.dumps({'status': result['status'], 'reason': result['reason']}), flush=True)
        if args.once: break
        time.sleep(3600)


if __name__ == '__main__': main()
