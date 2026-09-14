"""Read-only namespace Lease telemetry. Never acquire, renew or release slots."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def unavailable(reason='snapshot_unavailable'):
    return dict(pool='wgs-heavy-io', unit='heavy_work_job', used=None, limit=None,
                waiting=None, mode=None, available=False, updated_at=None,
                fields={key: dict(status='unavailable', reason=reason, updated_at=None)
                        for key in ('used', 'limit', 'waiting', 'mode')})


def fresh(value, now):
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return -10 <= (now-stamp).total_seconds() <= 180
    except (ValueError, TypeError):
        return False


def project_snapshot(payload, *, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(payload, dict): return unavailable()
    used, limit = (payload.get(k) for k in ('used', 'limit'))
    if (payload.get('schema_version') not in ('wgs-heavy-global.v1', 'wgs-heavy-global.v2')
        or payload.get('complete') is not True
        or any(type(x) is not int for x in (used, limit))
        or not 0 <= used <= limit or not 0 < limit <= 25):
        return unavailable()
    try:
        stamp = payload.get('updated_at')
        if not isinstance(stamp, str) or len(stamp) > 40: return unavailable()
        parsed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        if parsed.tzinfo is None or (now-parsed).total_seconds() < -10: return unavailable()
        reasons = payload.get('reasons') or {}
        if not isinstance(reasons, dict): return unavailable()
    except (ValueError, TypeError, OverflowError): return unavailable()
    result = unavailable()
    result['updated_at'] = payload.get('updated_at')
    reason_codes = {'waiting_snapshot_unavailable', 'master_inventory_unavailable',
                    'master_configuration_inconsistent', 'unresolved_quota_owners'}
    for key in ('used', 'limit', 'waiting', 'mode'):
        value = payload.get(key)
        valid = (value in ('enforce', 'observe', 'idle') if key == 'mode'
                 else type(value) is int and value >= 0)
        if valid:
            updated_at = payload.get('waiting_updated_at', payload.get('updated_at')) if key == 'waiting' else payload.get('updated_at')
            try:
                if not isinstance(updated_at, str) or len(updated_at) > 40: continue
                field_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                if field_time.tzinfo is None or (now-field_time).total_seconds() < -10: continue
            except (ValueError, TypeError, OverflowError): continue
            result[key] = value
            is_fresh = fresh(updated_at, now) and not payload.get('refresh_failed')
            result['fields'][key] = dict(status='fresh' if is_fresh else 'stale',
                reason=None if is_fresh else 'refresh_failed' if payload.get('refresh_failed') else 'snapshot_stale',
                updated_at=updated_at)
        else:
            reason = reasons.get(key)
            result['fields'][key]['reason'] = reason if reason in reason_codes else 'snapshot_unavailable'
    result['available'] = all(v['status'] == 'fresh' for v in result['fields'].values())
    return result


def read_snapshot(root):
    try:
        if not root or Path(root).is_symlink(): return unavailable()
        path = Path(root) / 'heavy-slot-global.json'
        if path.is_symlink() or path.stat().st_size > 65536: return unavailable()
        return project_snapshot(json.loads(path.read_text()))
    except (OSError, ValueError, TypeError):
        return unavailable()


def collect(kube, root, limit=25):
    def get(*args):
        r = subprocess.run(kube + ['get', *args, '-o', 'json'], capture_output=True, text=True, timeout=30)
        r.check_returncode()
        return json.loads(r.stdout)
    now = datetime.now(timezone.utc)
    leases = get('leases')
    if leases.get('metadata', {}).get('continue'): raise ValueError('incomplete lease list')
    rows = [x for x in leases['items'] if x['metadata']['name'].startswith('wgs-heavy-io-')]
    if len(rows) != limit or {x['metadata']['name'] for x in rows} != {'wgs-heavy-io-%02d' % i for i in range(limit)}:
        raise ValueError('incomplete quota inventory')
    # Count reservations including old holders: only the executor may reclaim them.
    used = sum(bool(x.get('spec', {}).get('holderIdentity')) for x in rows)
    result = dict(schema_version='wgs-heavy-global.v2', updated_at=now.isoformat(), complete=True,
                  used=used, limit=limit, waiting=None, mode=None, reasons={})
    try:
        jobs = get('jobs', '-l', 'app.kubernetes.io/component=snakemake-master')
        if jobs.get('metadata', {}).get('continue'): raise ValueError('incomplete Master list')
        if not isinstance(jobs.get('items'), list): raise ValueError('invalid Master list')
    except (OSError, ValueError, subprocess.SubprocessError):
        result['reasons'] = dict(waiting='master_inventory_unavailable', mode='master_inventory_unavailable')
        return result
    active = []
    for job in jobs['items']:
        terminal = any(c.get('type') in ('Complete','Failed') and c.get('status')=='True'
                       for c in job.get('status', {}).get('conditions', []))
        if terminal or job.get('spec', {}).get('suspend'): continue
        env = {e['name']: e.get('value') for c in job['spec']['template']['spec']['containers'] for e in c.get('env', [])}
        profile = job['metadata'].get('labels', {}).get('cce.biosan.cn/profile-id', '')
        # GATK Masters do not participate in WGS quota. Unknown Masters still
        # fail closed; a GATK Master advertising WGS quota must be validated.
        if profile.startswith('gatk-scmc-') and not any(k.startswith('WGS_HEAVY_SLOT_') for k in env):
            continue
        active.append(job)
    snapshots = {}
    for p in Path(root).glob('*/attempt-*/heavy-slot-status.json'):
        try:
            if p.is_symlink(): continue
            d = json.loads(p.read_text())
            if d.get('schema_version') == 'wgs-heavy-slot-status.v1' and fresh(d.get('updated_at'), now):
                snapshots[d.get('run_label')] = d
        except (OSError, ValueError): pass
    modes, waiting, waiting_known = set(), 0, True
    waiting_stamps = [now]
    for job in active:
        env = {e['name']: e.get('value') for c in job['spec']['template']['spec']['containers'] for e in c.get('env', [])}
        mode = env.get('WGS_HEAVY_SLOT_MODE')
        if mode not in ('enforce','observe') or env.get('WGS_HEAVY_SLOT_LIMIT') != str(limit):
            result['reasons'] = dict(waiting='master_configuration_inconsistent', mode='master_configuration_inconsistent')
            return result
        label = job['metadata'].get('labels', {}).get('cce.biosan.cn/run-id')
        d = snapshots.get(label, {})
        if (d.get('mode') != mode or d.get('limit') != limit
                or type(d.get('waiting_jobs')) is not int or d['waiting_jobs'] < 0):
            waiting_known = False
        else:
            waiting += d['waiting_jobs']
            waiting_stamps.append(datetime.fromisoformat(d['updated_at'].replace('Z', '+00:00')))
        modes.add(mode)
    if len(modes)>1 or (not active and used):
        result['reasons'] = dict(waiting='unresolved_quota_owners', mode='unresolved_quota_owners')
        return result
    result['mode'] = next(iter(modes), 'idle')
    result['waiting'] = waiting if waiting_known else None
    result['waiting_updated_at'] = min(waiting_stamps).isoformat() if waiting_known else None
    if not waiting_known: result['reasons']['waiting'] = 'waiting_snapshot_unavailable'
    return result


def write_snapshot(path, payload):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.heavy-slot-')
    try:
        with os.fdopen(fd,'w') as f: json.dump(payload,f)
        os.chmod(name,0o644)
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def main():
    import yaml
    p=argparse.ArgumentParser()
    p.add_argument('--config',required=True)
    p.add_argument('--root',required=True)
    p.add_argument('--once',action='store_true')
    a=p.parse_args()
    cfg=yaml.safe_load(Path(a.config).read_text())['kubernetes']
    kube=[cfg['kubectl_bin'],'--kubeconfig',cfg['kubeconfig'],'-n',cfg['namespace']]
    root=Path(a.root)
    if not root.is_dir() or root.is_symlink(): raise ValueError('invalid evidence root')
    while True:
        try:
            d=collect(kube,root)
            write_snapshot(root/'heavy-slot-global.json', d)
        except Exception as e:
            path = root/'heavy-slot-global.json'
            try:
                previous = json.loads(path.read_text()) if not path.is_symlink() else {}
            except (OSError, ValueError): previous = {}
            if project_snapshot(previous).get('used') is None:
                previous = dict(schema_version='wgs-heavy-global.v2', complete=False)
            previous.update(refresh_failed=True, checked_at=datetime.now(timezone.utc).isoformat())
            write_snapshot(path, previous)
            print('Heavy snapshot unavailable:',type(e).__name__,flush=True)
        if a.once: break
        time.sleep(60)

if __name__=='__main__': main()
