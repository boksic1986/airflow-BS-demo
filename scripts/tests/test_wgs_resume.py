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


def test_lost_create_then_absent_master_never_posts_a_second_create(frozen, monkeypatch):
    m=module(); _,binding,_,state,runtime,payload,_=frozen
    state['job']=None
    payload['stage']='step2_master'
    def uncertain_create(*args):
        state['submits'].append(args)
        raise m.subprocess.TimeoutExpired('synthetic-create', 1)
    monkeypatch.setattr(m,'_submit_frozen_master',uncertain_create)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            m.resume_master(payload=payload,binding=binding,runtime=runtime)
    # A later 404 cannot distinguish never-created from already-created/reclaimed.
    assert len(state['submits'])==1
    assert not state['deletes']


def test_missing_started_replacement_never_reopens_create_permission(frozen, monkeypatch):
    m=module(); _,binding,_,state,runtime,payload,replace=frozen
    state['job']=None
    payload['stage']='step2_master'
    journal=Path(payload['control_workdir'])/('recovery-'+payload['resume_action_id']+'.json')
    journal.parent.mkdir()
    journal.write_text(json.dumps({'state':'started','replacement_uid':'gone-uid'}))
    monkeypatch.setattr(m,'_submit_frozen_master',replace)
    monkeypatch.setattr(m,'_finish_handoff',lambda *a:None)
    with pytest.raises(RuntimeError):
        m.resume_master(payload=payload,binding=binding,runtime=runtime)
    assert not state['submits'] and not state['deletes']


def test_master_resource_version_change_during_worker_check_prevents_delete(frozen, monkeypatch):
    m=module(); _,binding,_,state,runtime,payload,replace=frozen
    def changed_after_inventory(*args,**kwargs):
        state['job']['metadata']['resourceVersion']='11'
    def delete(*args):
        state['deletes'].append(args)
        state['job']=None
    runtime._require_no_active_workers=changed_after_inventory
    monkeypatch.setattr(m,'_require_inactive_master_pods',lambda *a:None)
    monkeypatch.setattr(m,'_delete_master',delete)
    monkeypatch.setattr(m,'_submit_frozen_master',replace)
    monkeypatch.setattr(m,'_finish_handoff',lambda *a:None)
    with pytest.raises(RuntimeError):
        m.resume_master(payload=payload,binding=binding,runtime=runtime)
    assert not state['deletes'] and not state['submits']


def test_paginated_empty_master_pods_do_not_prove_quiescence(frozen):
    m=module(); _,_,_,_,runtime,_,_=frozen
    runtime._kubectl_json=lambda *a: {
        'kind':'PodList','metadata':{'continue':'next-page'},'items':[]}
    with pytest.raises(RuntimeError):
        m._require_inactive_master_pods(runtime,{},
            {'namespace':'mock','master_job':'master-mock'},'old-uid')


def test_lost_create_delayed_failed_replacement_does_not_reopen_same_action(frozen, monkeypatch):
    m=module(); _,binding,manifest,state,runtime,payload,replace=frozen
    state['job']=None
    payload['stage']='step2_master'
    def uncertain_create(*args):
        state['submits'].append(args)
        raise m.subprocess.TimeoutExpired('synthetic-create',1)
    monkeypatch.setattr(m,'_submit_frozen_master',uncertain_create)
    with pytest.raises(RuntimeError):
        m.resume_master(payload=payload,binding=binding,runtime=runtime)
    # The first exact GET was absent; the same submitted Job becomes visible
    # only after it failed, before its UID could be journalled locally.
    delayed=copy.deepcopy(manifest)
    delayed['metadata'].update(uid='delayed-uid',resourceVersion='30')
    delayed['status']={'conditions':[{'type':'Failed','status':'True'}]}
    state['job']=delayed
    def delete(*args):
        state['deletes'].append(args)
        state['job']=None
    monkeypatch.setattr(m,'_delete_master',delete)
    monkeypatch.setattr(m,'_submit_frozen_master',replace)
    monkeypatch.setattr(m,'_require_inactive_master_pods',lambda *a:None)
    monkeypatch.setattr(m,'_finish_handoff',lambda *a:None)
    with pytest.raises(RuntimeError):
        m.resume_master(payload=payload,binding=binding,runtime=runtime)
    assert len(state['submits'])==1 and not state['deletes']


@pytest.mark.parametrize('verified', [True, False])
def test_complete_job_requires_native_success_before_resume_advances(frozen, verified):
    m=module(); _,binding,_,state,runtime,payload,_=frozen
    state['job']['status']={'conditions':[{'type':'Complete','status':'True'}]}
    calls=[]
    def success(*args):
        calls.append(args[-1])
        if not verified:
            raise RuntimeError('native success unavailable')
        return {'state':'SUCCEEDED','job_uid':'old-uid'}
    runtime._recovery_native_success=success
    if verified:
        assert m.resume_master(payload=payload,binding=binding,runtime=runtime)['mode']=='reused'
    else:
        with pytest.raises(RuntimeError):
            m.resume_master(payload=payload,binding=binding,runtime=runtime)
    assert calls==['old-uid'] and not state['submits'] and not state['deletes']


@pytest.mark.parametrize('change', ['active', 'contradictory'])
def test_ambiguous_master_terminal_never_advances_or_replaces(frozen, change):
    m=module(); _,binding,_,state,runtime,payload,_=frozen
    state['job']['status']={'conditions':[{'type':'Complete','status':'True'}]}
    if change=='active':state['job']['status']['active']=1
    else:state['job']['status']['conditions'].append({'type':'Failed','status':'True'})
    runtime._recovery_native_success=lambda *a:{'state':'SUCCEEDED','job_uid':'old-uid'}
    with pytest.raises(RuntimeError):m.resume_master(payload=payload,binding=binding,runtime=runtime)
    assert not state['submits'] and not state['deletes']


def test_v2_missing_master_with_old_deletion_journal_cannot_create(frozen, monkeypatch):
    m=module(); bundle,binding,manifest,state,runtime,payload,replace=frozen
    manifest['metadata']['annotations']={'cce-pipeline/handoff-version':'2'}
    (bundle/'master-job.yaml').write_text(yaml.safe_dump(manifest))
    state['job']=None
    path=Path(payload['control_workdir'])/('recovery-'+payload['resume_action_id']+'.json')
    path.parent.mkdir(); path.write_text(json.dumps({'state':'deleted','old_uid':'old-uid'}))
    before=path.read_bytes()
    monkeypatch.setattr(m,'_submit_frozen_master',replace)
    monkeypatch.setattr(m,'_finish_handoff',lambda *a:None)
    with pytest.raises(RuntimeError,match='recovery view'):
        m.resume_master(payload=payload,binding=binding,runtime=runtime)
    assert not state['submits'] and not state['deletes'] and path.read_bytes()==before
