from types import SimpleNamespace as N
from app.wgs_dashboard_attention import _append_duplicate_families

def test_two_families_in_same_batches_have_distinct_actionable_alerts():
 runs=[N(analysis_id='r1',attempt=1,params_json={'analysis_batch':'B1'}),N(analysis_id='r2',attempt=2,params_json={'analysis_batch':'B2'})]
 samples=[N(analysis_id=r,family_id=f) for f in ('SYNTH-F1','SYNTH-F2') for r in ('r1','r2')]
 items=[];_append_duplicate_families(items,runs,samples)
 assert len({x['id'] for x in items})==2
 assert all('B1' in x['detail'] and 'B2' in x['detail'] for x in items)
 assert any('SYNTH-F1' in x['detail'] for x in items)
