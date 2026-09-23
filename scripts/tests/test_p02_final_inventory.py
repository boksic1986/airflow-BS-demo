"""Actual producer/plugin final inventory with synthetic Kubernetes transport."""
import copy
import json
import os
from types import SimpleNamespace

import pytest

if not os.environ.get('CCE_PLUGIN_SOURCE'):
    pytest.skip('requires pinned native and plugin sources',allow_module_level=True)
from test_recovery_final import mirrored_final, final_inputs, view_inputs, handoff
from cce_pipeline.assets import cce_batch_runtime as runtime
from scripts.cce_recovery_inventory import validate_final_submission_snapshot
from scripts import cce_recovery_workloads as workloads


@pytest.fixture
def final_cluster(mirrored_final,monkeypatch):
    h,view,record,evidence=mirrored_final
    snapshot=evidence['recovery-final.json']
    workers=validate_final_submission_snapshot(snapshot)
    namespace=h.contract['kubernetes']['namespace']
    label='synthetic-run'
    def job(name,uid,state):
        return {'kind':'Job','metadata':{'name':name,'uid':uid,'namespace':namespace,
            'resourceVersion':'1','labels':{'cce.biosan.cn/run-id':label}},
            'status':{'conditions':[{'type':state,'status':'True'}]}}
    master=job('master',record['job_uid'],'Failed')
    worker=job(workers[0]['name'],workers[0]['uid'],'Complete')
    objects={'master':master,workers[0]['name']:worker}
    lists={'jobs':{'kind':'JobList','metadata':{},'items':[master,worker]},
           'pods':{'kind':'PodList','metadata':{},'items':[]}}
    def query(config,*args):
        if args[0]=='job':return copy.deepcopy(objects.get(args[1]))
        if args[2].startswith('job-name='):return {'kind':'PodList','metadata':{},'items':[]}
        return copy.deepcopy(lists[args[0]])
    # Only external Kubernetes responses are substituted.
    monkeypatch.setattr(runtime,'_recovery_query',query)
    kwargs=dict(runtime=runtime,config={'kubernetes':{'namespace':namespace}},
        namespace=namespace,run_label=label,master_job='master',
        master_job_uid=record['job_uid'],master_state='FAILED',workers=workers)
    return kwargs,objects,lists,workers


@pytest.mark.parametrize('reclaimed',[False,True])
def test_final_inventory_reconciles_live_or_reclaimed_terminal_work(final_cluster,reclaimed):
    kwargs,objects,lists,workers=final_cluster
    if reclaimed:
        objects.clear();lists['jobs']['items']=[]
    result=workloads.probe_final_workloads(**kwargs)
    assert result['workers_inactive'] is True
    assert result['master_state']=='FAILED'


@pytest.mark.parametrize('change',['unknown_job','unknown_pod','page','active_worker','foreign_uid',
    'absent_worker_without_terminal','conflicting_terminal','foreign_namespace'])
def test_final_inventory_blocks_incomplete_or_unbound_cluster(final_cluster,change):
    kwargs,objects,lists,workers=final_cluster
    worker=objects[workers[0]['name']]
    if change=='unknown_job':lists['jobs']['items'].append(dict(kind='Job',metadata=dict(worker['metadata'],name='foreign')))
    elif change=='unknown_pod':lists['pods']['items']=[{'kind':'Pod','metadata':{'name':'foreign'}}]
    elif change=='page':lists['jobs']['metadata']['remainingItemCount']=1
    elif change=='active_worker':worker['status']['active']=1
    elif change=='foreign_uid':worker['metadata']['uid']='foreign'
    elif change=='absent_worker_without_terminal':
        del objects[workers[0]['name']];lists['jobs']['items']=[objects['master']];workers[0]['terminal_state']=None
    elif change=='conflicting_terminal':workers[0]['terminal_state']='FAILED'
    else:worker['metadata']['namespace']='foreign'
    with pytest.raises(ValueError):workloads.probe_final_workloads(**kwargs)
