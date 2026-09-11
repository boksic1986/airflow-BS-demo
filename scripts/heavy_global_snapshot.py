"""Read-only namespace Lease telemetry. Never acquire, renew or release slots."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def unavailable():
    return dict(pool='wgs-heavy-io', used=None, limit=None, waiting=None, mode=None, available=False)


def fresh(value, now):
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return -10 <= (now-stamp).total_seconds() <= 180
    except (ValueError, TypeError):
        return False


def project_snapshot(payload, *, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(payload, dict): return unavailable()
    used, limit, waiting = (payload.get(k) for k in ('used', 'limit', 'waiting'))
    if (payload.get('schema_version') != 'wgs-heavy-global.v1' or payload.get('complete') is not True
        or not fresh(payload.get('updated_at'), now)
        or any(type(x) is not int for x in (used, limit, waiting))
        or not 0 <= used <= limit or limit <= 0 or waiting < 0
        or payload.get('mode') not in ('enforce', 'observe', 'idle')):
        return unavailable()
    return dict(pool='wgs-heavy-io', used=used, limit=limit, waiting=waiting,
                mode=payload['mode'], available=True, updated_at=payload['updated_at'])


def read_snapshot(root):
    try:
        path = Path(root) / 'heavy-slot-global.json'
        if path.is_symlink(): return unavailable()
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
    if {x['metadata']['name'] for x in rows} != {'wgs-heavy-io-%02d' % i for i in range(limit)}:
        raise ValueError('incomplete quota inventory')
    # Count reservations including old holders: only the executor may reclaim them.
    used = sum(bool(x.get('spec', {}).get('holderIdentity')) for x in rows)
    jobs = get('jobs', '-l', 'app.kubernetes.io/component=snakemake-master')
    if jobs.get('metadata', {}).get('continue'): raise ValueError('incomplete Master list')
    active = []
    for job in jobs['items']:
        terminal = any(c.get('type') in ('Complete','Failed') and c.get('status')=='True'
                       for c in job.get('status', {}).get('conditions', []))
        if terminal or job.get('spec', {}).get('suspend'): continue
        active.append(job)
    snapshots = {}
    for p in Path(root).glob('*/attempt-*/heavy-slot-status.json'):
        try:
            if p.is_symlink(): continue
            d = json.loads(p.read_text())
            if d.get('schema_version') == 'wgs-heavy-slot-status.v1' and fresh(d.get('updated_at'), now):
                snapshots[d.get('run_label')] = d
        except (OSError, ValueError): pass
    modes, waiting = set(), 0
    for job in active:
        env = {e['name']: e.get('value') for c in job['spec']['template']['spec']['containers'] for e in c.get('env', [])}
        mode = env.get('WGS_HEAVY_SLOT_MODE')
        if mode not in ('enforce','observe') or env.get('WGS_HEAVY_SLOT_LIMIT') != str(limit):
            raise ValueError('Master quota configuration inconsistent')
        label = job['metadata'].get('labels', {}).get('cce.biosan.cn/run-id')
        d = snapshots.get(label, {})
        if d.get('mode') != mode or d.get('limit') != limit or type(d.get('waiting_jobs')) is not int:
            raise ValueError('Master waiting snapshot missing or stale')
        waiting += d['waiting_jobs']
        modes.add(mode)
    if len(modes)>1 or (not active and used): raise ValueError('unresolved quota owners')
    return dict(schema_version='wgs-heavy-global.v1', updated_at=now.isoformat(), complete=True,
                used=used, limit=limit, waiting=waiting, mode=next(iter(modes), 'idle'))


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
            write_snapshot(root/'heavy-slot-global.json', dict(schema_version='wgs-heavy-global.v1', complete=False,
                           updated_at=datetime.now(timezone.utc).isoformat(), error_type=type(e).__name__))
            print('Heavy snapshot unavailable:',type(e).__name__,flush=True)
        if a.once: break
        time.sleep(60)

if __name__=='__main__': main()
