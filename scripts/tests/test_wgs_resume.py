"""Frozen synthetic native boundary; never contacts CCE/OBS."""
import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml


def module():
    path=Path(__file__).parents[1]/'wgs_resume.py'
    assert path.is_file(), 'explicit WGS frozen resume implementation is missing'
    spec=importlib.util.spec_from_file_location('wgs_resume_test',path)
    value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


@pytest.fixture
def frozen(tmp_path):
    bundle=tmp_path/'batch'/'cce'; bundle.mkdir(parents=True)
    aid='WGS_20260915_010203_A1B2C3'
    binding={'analysis_id':aid,'attempt':1,'run_id':aid+'-a1','pipeline_release_id':'wgs-4.2.1-34bfcbf',
        'cce_bundle':str(bundle),'namespace':'mock','master_job':'master-mock','run_label':'cce-run-0123456789abcdef'}
    manifest={'apiVersion':'batch/v1','kind':'Job','metadata':{'name':'master-mock','namespace':'mock',
        'labels':{'cce.biosan.cn/run-id':binding['run_label']}},
        'spec':{'template':{'spec':{'containers':[{'name':'master','image':'mock@sha256:'+'a'*64}]}}}}
    (bundle/'master-job.yaml').write_text(yaml.safe_dump(manifest))
    contract={'identity':{'run_id':aid+'-a1'},'kubernetes':{'namespace':'mock','master_job':'master-mock'}}
    (bundle/'BATCH_RUNTIME.yaml').write_text(yaml.safe_dump(contract))
    job=copy.deepcopy(manifest); job['metadata'].update(uid='old-uid',resourceVersion='10')
    job['status']={'conditions':[{'type':'Failed','status':'True'}]}
    state={'job':job,'deletes':[],'submits':[],'step2':0}
    def query(*args): return copy.deepcopy(state['job'])
    def replace(*args,**kwargs):
        state['submits'].append((args,kwargs))
        new=copy.deepcopy(manifest); new['metadata'].update(uid='new-uid',resourceVersion='20')
        new['status']={'active':1}; state['job']=new
    runtime=SimpleNamespace(_load=lambda *a:(contract,{},()),_kubectl_json=query,
        _claim_batch_lock=lambda *a:None,_require_no_active_workers=lambda *a,**k:None)
    for name in ('_create_job_from_path','_wait_pod','_run','_kubectl','_write_master_handoff','_prepare_worker_manifest'):
        setattr(runtime,name,lambda *a,**k:None)
    payload={**binding,'stage':'step3_monitor','generation':2,'resume_action_id':'resume-mock',
        'control_workdir':str(tmp_path/'control')}
    return bundle,binding,manifest,state,runtime,payload,replace


def test_failed_master_replaced_with_exact_frozen_manifest_and_uid_precondition(frozen,monkeypatch):
    m=module(); bundle,binding,manifest,state,runtime,payload,replace=frozen
    def delete(runtime,config,names,options):
        state['deletes'].append(options); state['job']=None
    monkeypatch.setattr(m,'_delete_master',delete)
    monkeypatch.setattr(m,'_submit_frozen_master',replace)
    monkeypatch.setattr(m,'_require_inactive_master_pods',lambda *a:None)
    monkeypatch.setattr(m,'_finish_handoff',lambda *a:None)
    result=m.resume_master(payload=payload,binding=binding,runtime=runtime)
    assert result['master_uid']=='new-uid'
    assert state['deletes'][0]['preconditions']=={'uid':'old-uid','resourceVersion':'10'}
    assert len(state['submits'])==1
    assert yaml.safe_load((bundle/'master-job.yaml').read_text())==manifest
    assert state['step2']==0
    assert m.resume_master(payload=payload,binding=binding,runtime=runtime)['master_uid']=='new-uid'
    assert len(state['deletes'])==len(state['submits'])==1


def test_active_master_is_reused_and_foreign_manifest_never_deleted(frozen,monkeypatch):
    m=module(); _,binding,_,state,runtime,payload,_=frozen
    monkeypatch.setattr(m,'_finish_handoff',lambda *a:None)
    state['job']['status']={'active':1}
    assert m.resume_master(payload=payload,binding=binding,runtime=runtime)['mode']=='reused'
    state['job']['spec']['template']['spec']['containers'][0]['image']='foreign'
    with pytest.raises(RuntimeError): m.resume_master(payload=payload,binding=binding,runtime=runtime)
    assert not state['deletes'] and not state['submits']


def test_stage_dispatch_reuses_transfer_and_materialization_without_prepare(frozen,monkeypatch):
    m=module(); _,binding,_,_,_,payload,_=frozen
    calls=[]
    spec=importlib.util.spec_from_file_location('wgs_runtime_gate_test',Path(__file__).parents[1]/'wgs_runtime_gate.py')
    gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
    monkeypatch.setitem(sys.modules,'wgs_runtime_gate_test',gate)
    monkeypatch.setitem(sys.modules,'wgs_resume',m)
    monkeypatch.setenv('WGS_EXECUTION_ENABLED','true')
    monkeypatch.setenv('WGS_RUNTIME_ADAPTER_ENABLED','true')
    monkeypatch.setattr(gate,'_load_binding',lambda p:binding)
    monkeypatch.setattr(gate,'_run_transfer_stage',lambda p:calls.append((p['stage'],p['attempt'],p['control_workdir'])))
    monkeypatch.setattr(gate,'_step_command',lambda p,s:['bash',s])
    monkeypatch.setattr(m.subprocess,'run',lambda command,**kw:calls.append(tuple(command)))
    for stage in ('step1_upload','step5_download','step6_materialize'):
        gate.run_stage({**payload,'stage':stage})
    assert calls==[('step1_upload',1,payload['control_workdir']),('step5_download',1,payload['control_workdir']),('bash','step6_materialize')]


def test_old_mirror_terminal_cannot_override_new_master_identity():
    m=module()
    stale={'master_state':'FAILED','master_uid':'old-uid','message':'old terminal'}
    live={'metadata':{'uid':'new-uid','resourceVersion':'20'},'status':{'active':1}}
    result=m.fence_master_status(stale,live,expected_uid='new-uid')
    assert result['master_state']=='RUNNING' and result['master_uid']=='new-uid'
