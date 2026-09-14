import json
from types import SimpleNamespace
from app.heavy_global_snapshot import collect


def test_unrelated_gatk_master_does_not_invalidate_wgs_quota(monkeypatch,tmp_path):
    leases={'items':[{'metadata':{'name':f'wgs-heavy-io-{i:02d}'},'spec':{}} for i in range(25)]}
    jobs={'items':[{'metadata':{'labels':{'cce.biosan.cn/profile-id':'gatk-scmc-v7.6.0'}},
                   'spec':{'template':{'spec':{'containers':[{'env':[]}]}}}}]}
    def run(args,**kwargs):
        return SimpleNamespace(stdout=json.dumps(leases if 'leases' in args else jobs),check_returncode=lambda:None)
    monkeypatch.setattr('app.heavy_global_snapshot.subprocess.run',run)
    result=collect(['kubectl'],tmp_path)
    assert (result['used'],result['limit'],result['waiting'],result['mode'])==(0,25,0,'idle')
