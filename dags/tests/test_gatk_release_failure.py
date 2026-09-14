"""Real DAG callable: retained transfer capacity must not report success."""
import runpy
from pathlib import Path


def test_retained_lease_is_not_success():
    ns=runpy.run_path(str(Path(__file__).parents[1]/'bio_gatk.py'))
    release=ns['release_stage']
    release.__globals__['_backend_json']=lambda *a,**kw: {'released':False,'retained':True,'reason':'transfer_not_terminal'}
    context={'dag_run':type('Run',(),{'conf':{'analysis_id':'GATK_SYNTHETIC','attempt':1}})()}
    for stage in ('release_input_transfer_slot','release_result_transfer_slot','release_leases'):
        try:
            release(stage,**context)
        except RuntimeError:
            continue
        raise AssertionError('retained lease silently accepted as success')
    release.__globals__['_backend_json']=lambda *a,**kw: {'released':False,'retained':False}
    release('release_input_transfer_slot',**context)  # Already released is idempotent.


if __name__=='__main__':
    test_retained_lease_is_not_success()
    print('PASS: release retention is explicit, already-released is idempotent')
