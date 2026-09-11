import importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta
import unittest
import os

spec = importlib.util.spec_from_file_location('heavy_global_snapshot', os.environ.get('HEAVY_TEST_MODULE', str(Path(__file__).resolve().parents[1] / 'heavy_global_snapshot.py')))
m = importlib.util.module_from_spec(spec) if spec else None
if spec and spec.loader and Path(spec.origin).exists():
    spec.loader.exec_module(m)

class SnapshotTests(unittest.TestCase):
    def test_fresh_complete_snapshot(self):
        now = datetime.now(timezone.utc)
        payload = dict(schema_version='wgs-heavy-global.v1', updated_at=now.isoformat(), complete=True,
                       used=6, limit=25, waiting=2, mode='enforce')
        fn = getattr(m, 'project_snapshot', lambda *a, **kw: {'available': False})
        self.assertEqual(fn(payload, now=now).get('used'), 6)
        self.assertTrue(fn(payload, now=now)['available'])

    def test_stale_incomplete_invalid_unavailable(self):
        now = datetime.now(timezone.utc)
        fn = getattr(m, 'project_snapshot', lambda *a, **kw: {'available': False})
        base = dict(schema_version='wgs-heavy-global.v1', updated_at=now.isoformat(), complete=True,
                    used=6, limit=25, waiting=0, mode='enforce')
        for change in [dict(complete=False), dict(used=26), dict(waiting=None), dict(mode=''),
                       dict(updated_at=(now-timedelta(seconds=181)).isoformat()),
                       dict(updated_at=(now+timedelta(seconds=60)).isoformat())]:
            self.assertFalse(fn(dict(base, **change), now=now)['available'])

    def test_collection_counts_actual_holders_and_waiting(self):
        from unittest.mock import patch
        import json,tempfile
        now=datetime.now(timezone.utc).isoformat()
        leases={'items':[{'metadata':{'name':'wgs-heavy-io-%02d'%i},'spec':{'holderIdentity':'owner' if i<6 else ''}} for i in range(25)]}
        jobs={'items':[{'metadata':{'labels':{'cce.biosan.cn/run-id':'run1'}},'spec':{'template':{'spec':{'containers':[{'env':[{'name':'WGS_HEAVY_SLOT_MODE','value':'enforce'},{'name':'WGS_HEAVY_SLOT_LIMIT','value':'25'}]}]}}}}]}
        class Result:
            def __init__(self,d): self.stdout=json.dumps(d)
            def check_returncode(self): pass
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'run'/'attempt-1';p.mkdir(parents=True)
            (p/'heavy-slot-status.json').write_text(json.dumps(dict(schema_version='wgs-heavy-slot-status.v1',run_label='run1',updated_at=now,mode='enforce',limit=25,waiting_jobs=3)))
            with patch.object(m.subprocess,'run',side_effect=[Result(leases),Result(jobs)]):
                result=m.collect(['kubectl'],tmp)
            self.assertEqual((result['used'],result['limit'],result['waiting']),(6,25,3))
            with patch.object(m.subprocess,'run',return_value=Result({'items':leases['items'][:-1]})):
                with self.assertRaises(ValueError):m.collect(['kubectl'],tmp)

if __name__ == '__main__': unittest.main()
