"""Existing WGS/GATK Resume consumes native final bytes and Task2 lock CAS."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
import yaml

if not os.environ.get('CCE_PLUGIN_SOURCE'):
    pytest.skip('requires pinned producer sources',allow_module_level=True)
from cce_pipeline.assets import cce_batch_runtime as runtime
from test_recovery_final import mirrored_final,final_inputs,view_inputs,handoff
from scripts import wgs_resume,gatk_resume
from scripts.cce_recovery_inventory import RecoveryCapability

REAL_CLAIM=runtime._claim_batch_lock


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'}],indirect=True)
def test_wgs_resume_worker_retains_binding_when_monitor_disconnects(adapter,tmp_path,monkeypatch):
    from scripts import wgs_runtime_gate as gate
    state,invoke,bundle,cap,h=adapter
    platform={k:cap.context[k] for k in ('pipeline','analysis_id','execution_id')}
    platform.update(attempt=1,stage='step3_monitor',generation=8,request_hash='b'*64)
    cap.platform_execution=platform
    result=invoke()
    payload={**platform,'orchestration_contract_version':2,'resume_action_id':'new-action'}
    root=tmp_path/'worker-receipts';root.mkdir()
    monkeypatch.setattr(gate,'_sidecar_path',lambda p,s:root/(p['stage']+s))
    monkeypatch.setattr(gate,'_load_binding',lambda p:{'cce_bundle':str(bundle)})
    monkeypatch.setattr(wgs_resume,'resume_master',lambda **kw:result)
    def monitor(p):
        gate._write_status(p,'running','monitoring selected Master')
        raise RuntimeError('synthetic monitor disconnect')
    monkeypatch.setattr(gate,'_monitor_step3',monitor)
    monkeypatch.setattr(gate,'run_stage',lambda p:wgs_resume.run_resume_stage(p,gate=gate))
    with pytest.raises(RuntimeError,match='synthetic monitor disconnect'):
        gate._run_worker(payload)
    receipt=json.loads((root/'step3_monitor.status.json').read_bytes())
    assert receipt['status']=='failed'
    assert receipt['cce_master_binding']==result['cce_master_binding']
    assert receipt['cce_master_submit_execution_id']==platform['execution_id']


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
def test_verified_master_binding_survives_normal_stage_receipts(adapter,tmp_path,monkeypatch):
    from scripts import wgs_runtime_gate,gatk_runtime_gate
    state,invoke,bundle,cap,h=adapter
    pipeline=cap.context['pipeline']
    platform={k:cap.context[k] for k in ('pipeline','analysis_id','execution_id')}
    platform.update(attempt=1,stage='step3_monitor',generation=8,request_hash='b'*64)
    cap.platform_execution=platform
    result=invoke()
    expected=copy.deepcopy(result['cce_master_binding'])
    payload={**platform,'orchestration_contract_version':2,'_cce_master_result':result}
    root=tmp_path/'normal-receipts';root.mkdir()
    monkeypatch.setattr(wgs_runtime_gate,'_sidecar_path',lambda p,s:root/(p['stage']+s))
    def write(p,status,**details):
        if pipeline=='wgs':
            wgs_runtime_gate._write_status(p,status,'normal stage receipt',**details)
            return json.loads((root/(p['stage']+'.status.json')).read_bytes())
        path=root/(p['stage']+'.request.json')
        return gatk_runtime_gate._write_status(path,p,status,'normal stage receipt',**details)
    # Mutating the JSON-facing return must not alter the verified receipt copy.
    result['cce_master_binding']['native']['job_uid']='forged-uid'
    for number,stage in enumerate(('step3_monitor','step4_publish','step5_download','step6_materialize'),3):
        current={**payload,'stage':stage}
        if number>3:
            current.update(execution_id='downstream-'+str(number),generation=1,request_hash='c'*64)
        for status in ('running','success'):
            value=write(current,status)
            assert value['cce_master_binding']==expected
            assert value['cce_master_submit_execution_id']==platform['execution_id']
            assert value['request_hash']==current['request_hash']
            assert value['generation']==current['generation']
            if pipeline=='gatk':
                if status=='success':
                    unsigned={k:v for k,v in value.items() if k!='receipt_hash'}
                    assert value['receipt_hash']==hashlib.sha256(json.dumps(unsigned,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    # A JSON round trip loses authority; caller-provided receipt fields are not
    # enough to carry a binding, including through generic progress kwargs.
    forged={**payload,'_cce_master_result':json.loads(json.dumps(result))}
    with pytest.raises((ValueError,RuntimeError)):
        write(forged,'failed')
    with pytest.raises((ValueError,RuntimeError)):
        write({**payload,'attempt':2},'failed')
    with pytest.raises((ValueError,RuntimeError)):
        write({**payload,'request_hash':'d'*64},'failed')
    with pytest.raises((ValueError,RuntimeError)):
        write({k:v for k,v in payload.items() if k!='_cce_master_result'},'failed',
              cce_master_binding=expected)
    # A successful older Master keeps its original submit identity even when a
    # new authorized platform execution observes it. Test only receipt mapping
    # here; native-success validation remains in RecoveryCapability.export_result.
    from scripts.cce_recovery_inventory import VerifiedMasterResult,master_receipt_fields
    observing={**platform,'execution_id':'new-observer','generation':9,'request_hash':'e'*64}
    observed={**payload,**observing,'_cce_master_result':VerifiedMasterResult({},expected,observing)}
    assert master_receipt_fields(observed,pipeline=pipeline,details={})['cce_master_binding']==expected


@pytest.fixture
def adapter(mirrored_final,tmp_path,monkeypatch):
    h,view,record,evidence=mirrored_final
    pipeline=record['recovery_context']['pipeline']
    aid=record['recovery_context']['analysis_id']
    request_root=tmp_path/'requests'
    control=request_root/aid/'attempt-1';control.mkdir(parents=True)
    bundle=tmp_path/'runs'/aid/'attempt-1'/'cce'
    shutil.copytree(view,bundle)
    runtime._write_mirror_evidence(bundle,record['run_id'],evidence,project=record['project'],batch=record['batch'])
    manifest=yaml.safe_load((bundle/'master-job.yaml').read_bytes())
    master=copy.deepcopy(manifest)
    master['metadata'].update(uid=record['job_uid'],resourceVersion='10')
    master['status']={'conditions':[{'type':'Failed','status':'True'}]}
    worker_name=json.loads(evidence['recovery-final.json']['manifest'])['external_jobid']
    worker={'kind':'Job','metadata':{'name':worker_name,'namespace':'synthetic','uid':'worker-uid',
        'resourceVersion':'2','labels':{'cce.biosan.cn/run-id':'synthetic-run'}},'status':{'conditions':[{'type':'Complete','status':'True'}]}}
    state=SimpleNamespace(job=master,worker=worker,cms={},creates=0,deletes=0,starts=0,copies=0,
        lose=False,hide=False,unknown=False,page=False,surviving=False,allowed=True,confirmation=None,
        maintenance=False)
    def query(config,kind,*args):
        if kind=='job':
            if args[0]=='cleanup' and state.maintenance:return {'status':{'active':1}}
            return copy.deepcopy(state.job if args[0]=='master' else state.worker if args[0]==worker_name else None)
        if kind=='configmap':return copy.deepcopy(state.cms.get(args[0]))
        if kind=='jobs':
            items=[copy.deepcopy(v) for v in (state.job,state.worker) if v]
            if state.unknown:
                other=copy.deepcopy(worker);other['metadata']['name']='unknown';items.append(other)
            return {'kind':'JobList','metadata':{'remainingItemCount':1} if state.page else {},'items':items}
        if state.surviving:return {'kind':'PodList','metadata':{},'items':[{'kind':'Pod','metadata':{
            'name':'old-pod','uid':'pod-uid','namespace':'synthetic','ownerReferences':[
                {'controller':True,'kind':'Job','name':'master','uid':'master-uid'}]},'status':{'phase':'Running'}}]}
        return {'kind':'PodList','metadata':{},'items':[]}
    monkeypatch.setattr(runtime,'_recovery_query',query)
    monkeypatch.setattr(runtime,'_kubectl_json',lambda config,kind,*args,**kw:query(config,kind,*args))
    def transport(command,**kwargs):
        op=command[5]
        if op in {'create','replace'}:
            doc=json.loads(kwargs['input_bytes']);name=doc['metadata']['name'];old=state.cms.get(name)
            if old and any(doc['metadata'].get(k)!=old['metadata'][k] for k in ('uid','resourceVersion')):
                return SimpleNamespace(returncode=1)
            doc['metadata'].update(uid=old['metadata']['uid'] if old else 'lock-uid',
                resourceVersion=str(int(old['metadata']['resourceVersion'])+1) if old else '1')
            state.cms[name]=doc
        elif 'touch' in command:
            state.starts+=1
            new_view=Path(state.new_view)
            state.confirmation={**runtime._read_master_handoff(new_view,h.contract),
                'state':'START_CONFIRMED','pod_uid':'new-pod-uid','confirmed_epoch':h.now}
        elif 'cat' in command:
            return SimpleNamespace(returncode=0,stdout=json.dumps(state.confirmation).encode(),stderr=b'')
        elif 'input_bytes' in kwargs:state.copies+=1
        return SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
    monkeypatch.setattr(runtime,'_run',transport)
    monkeypatch.setattr(runtime,'_claim_batch_lock',REAL_CLAIM)
    monkeypatch.setattr(runtime,'_load',lambda *a:(h.contract,h.config,h.modules))
    def create(config,path):
        state.creates+=1;state.new_view=str(path.parent)
        new=yaml.safe_load(path.read_bytes());new['metadata'].update(uid='new-uid',resourceVersion='20');new['status']={'active':1}
        state.job=None if state.hide else new
        if state.lose:raise TimeoutError('synthetic lost CREATE')
        return new
    monkeypatch.setattr(runtime,'_create_job_from_path',create)
    # Existing producer confirmation queries need the new owned Pod.
    original_query=runtime._kubectl_json
    def native_query(config,kind,*args,**kwargs):
        if kind=='pods' and state.job and state.job['metadata']['uid']=='new-uid':
            return {'items':[{'metadata':{'name':'new-pod','uid':'new-pod-uid','ownerReferences':[
                {'controller':True,'kind':'Job','uid':'new-uid'}]},'status':{'phase':'Running'}}]}
        return original_query(config,kind,*args,**kwargs)
    monkeypatch.setattr(runtime,'_kubectl_json',native_query)
    monkeypatch.setattr(runtime,'_wait_pod',lambda *a,**kw:'new-pod')
    def remove(config,names,options):
        assert options['preconditions']=={'uid':'master-uid','resourceVersion':'10'}
        state.deletes+=1;state.job=None
    monkeypatch.setattr(runtime,'_delete_recovery_master',remove,raising=False)
    binding={'schema_version':'gatk-runtime.batch-binding.v1' if pipeline=='gatk' else 'wgs',
        'analysis_id':aid,'attempt':1,'run_id':record['run_id'],'cce_bundle':str(bundle),
        'namespace':'synthetic','master_job':'master','run_label':'synthetic-run'}
    binding_path=bundle.parent/'batch-binding.json';binding_path.write_text(json.dumps(binding))
    context={**record['recovery_context'],'generation':3,'action':'new-action','execution_id':'new-exec'}
    def authorize(facts):return {'writers_protocol':2,'dispatcher_inactive':state.allowed,'recovery_allowed':True,
        'native_directory':evidence['recovery-final.json']['canonical_directory'],'canonical_directory':'/storage/synthetic/project'}
    def mapper(current,operation,facts):
        old=json.loads(current['data']['lock'])
        return {'object_uid':current['metadata']['uid'],'resource_version':current['metadata']['resourceVersion'],
                'identity':old['identity'],'owner':old['owner']}
    platform=record.get('platform_execution')
    if platform is not None:
        platform=dict(platform,execution_id=context['execution_id'])
    cap=RecoveryCapability(bundle=bundle,expected_job_uid='master-uid',context=context,authorize=authorize,
        verify_lock=mapper,platform_execution=platform)
    cap.bind(runtime,h.contract,h.config,run_label='synthetic-run',pipeline=pipeline,
        analysis_id=aid,attempt=1,action='new-action')
    old_context={**cap.lock_context(),'generation':record['execution_generation'],
        'action':record['recovery_context']['action'],'master_uid':'master-uid'}
    REAL_CLAIM(h.contract,h.config,lock_context=old_context,journal={},save_journal=lambda v:None,verify=mapper)
    monkeypatch.setenv('GATK_RUNTIME_REQUEST_ROOT',str(request_root))
    def invoke():
        if pipeline=='wgs':
            return wgs_resume.resume_master(payload={**binding,'stage':'step3_monitor','resume_action_id':'new-action',
                'control_workdir':str(control)},binding=binding,runtime=runtime,recovery=cap)
        return gatk_resume.resume(analysis_id=aid,attempt=1,expected_job_uid='master-uid',
            expected_binding_sha256=hashlib.sha256(binding_path.read_bytes()).hexdigest(),
            expected_contract_sha256=hashlib.sha256((bundle/'BATCH_RUNTIME.yaml').read_bytes()).hexdigest(),
            runtime=runtime,execute=True,recovery=cap)
    state.record,state.evidence=record,evidence
    return state,invoke,bundle,cap,h


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
def test_resume_propagates_new_platform_execution_without_hash_substitution(adapter):
    state,invoke,bundle,cap,h=adapter
    platform={k:cap.context[k] for k in ('pipeline','analysis_id','execution_id')}
    platform.update(attempt=1,stage='step3_monitor',generation=8,request_hash='b'*64)
    cap.platform_execution=platform
    state.lose=True  # The existing journal reconciles uncertain CREATE.
    result=invoke()
    selected=Path(result['bundle'])
    binding=runtime._handoff_binding(selected,h.contract)
    assert binding['platform_execution']==platform
    exported=result['cce_master_binding']
    assert exported['schema_version']==2
    assert exported['platform_execution']==platform
    assert exported['selected_bundle']==str(selected)
    assert exported['source_bundle']==str(bundle)
    assert exported['native']['execution_generation']==3
    assert exported['native']['request_hash']==binding['request_hash']
    assert exported['native']['job_uid']=='new-uid'
    assert result['cce_master_submit_execution_id']==platform['execution_id']
    assert binding['request_hash']!=platform['request_hash']
    assert binding['execution_generation']==3
    invoke()
    assert (state.creates,state.starts)==(1,1)
    handoff_path=runtime._master_handoff_path(selected,h.contract)
    confirmed=handoff_path.read_bytes()
    changed=json.loads(confirmed);changed['state']='START_SENT'
    handoff_path.write_text(json.dumps(changed))
    with pytest.raises(ValueError):cap.export_result(result)
    handoff_path.write_bytes(confirmed)
    exported['platform_execution']['request_hash']='e'*64
    assert cap.platform_execution['request_hash']=='b'*64
    cap.platform_execution={**platform,'request_hash':'c'*64}
    with pytest.raises((RuntimeError,ValueError)):
        invoke()
    assert (state.creates,state.starts)==(1,1)


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
@pytest.mark.parametrize('scenario',['live_failed','reclaimed','lost_response','unknown_create','denied',
    'unknown_worker','page','surviving_pod','foreign_uid','missing_terminal','native_success',
    'handoff_lost','handoff_regressed','ambiguous_complete'])
def test_existing_resume_uses_final_evidence_new_view_and_one_create(adapter,scenario):
    state,invoke,bundle,cap,h=adapter
    if scenario=='reclaimed':state.job=None;state.worker=None
    if scenario in {'lost_response','unknown_create'}:state.lose=True
    if scenario=='unknown_create':state.hide=True
    if scenario=='denied':state.allowed=False
    if scenario=='unknown_worker':state.unknown=True
    if scenario=='page':state.page=True
    if scenario=='surviving_pod':state.job=None;state.surviving=True
    if scenario=='foreign_uid':state.job['metadata']['uid']='foreign'
    if scenario=='missing_terminal':
        (runtime._mirror_dir(bundle,state.record['run_id'])/'MIRROR_COMPLETE.json').unlink()
    if scenario=='native_success':
        terminal=state.evidence.pop('RUN_FAILED.json')
        terminal.update(state='SUCCEEDED',exit_code=0,exit_codes={'preflight':0,'analysis':0,'final_dryrun':0})
        terminal.pop('failed_stage',None)
        state.evidence['RUN_COMPLETE.json']=terminal
        state.evidence['workflow-completion.json']={'required':[{'path':'ANALYSIS_COMPLETE','content':json.dumps({
            'schema_version':1,'status':'PASS',**h.contract['identity']})}]}
        runtime._write_mirror_evidence(bundle,state.record['run_id'],state.evidence,
            project=state.record['project'],batch=state.record['batch'])
        state.job=None;state.worker=None
    before={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}
    if scenario=='native_success':
        assert invoke()['mode']=='succeeded'
        assert state.creates==state.deletes==state.starts==0
    elif scenario in {'unknown_create','denied','unknown_worker','page','surviving_pod','foreign_uid','missing_terminal'}:
        for _ in range(2):
            with pytest.raises((ValueError,RuntimeError)):invoke()
        assert state.creates==(1 if scenario=='unknown_create' else 0)
    else:
        result=invoke()
        assert result.get('master_uid',result.get('replacement_job_uid'))=='new-uid'
        assert runtime._read_master_handoff(Path(state.new_view),h.contract)['state']=='START_CONFIRMED'
        starts,copies=state.starts,state.copies
        if scenario=='handoff_lost':
            runtime._master_handoff_path(Path(state.new_view),h.contract).unlink()
            with pytest.raises(RuntimeError):invoke()
        elif scenario=='handoff_regressed':
            path=runtime._master_handoff_path(Path(state.new_view),h.contract)
            value=json.loads(path.read_bytes());value['state']='POD_READY'
            path.write_text(json.dumps(value))
            with pytest.raises(RuntimeError):invoke()
        elif scenario=='ambiguous_complete':
            state.job['status']={'active':1,'conditions':[{'type':'Complete','status':'True'}]}
            # A valid native success must not override an active live terminal.
            original_success=runtime._recovery_native_success
            runtime._recovery_native_success=lambda *a:{'state':'SUCCEEDED','job_uid':'new-uid'}
            try:
                with pytest.raises(RuntimeError):invoke()
            finally:runtime._recovery_native_success=original_success
        else:invoke()
        assert state.creates==1 and state.starts==starts==1
        assert state.copies==copies
        owner=json.loads(next(iter(state.cms.values()))['data']['lock'])['owner']
        assert owner=={'generation':3,'action':'new-action','master_uid':'new-uid'}
    assert before=={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}


@pytest.mark.parametrize('view_inputs',[{'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
def test_gatk_replay_rechecks_maintenance_before_start(adapter,monkeypatch):
    state,invoke,bundle,cap,h=adapter
    finish=runtime._finish_master_handoff
    monkeypatch.setattr(runtime,'_finish_master_handoff',lambda *a:(_ for _ in ()).throw(RuntimeError('interrupted before START')))
    with pytest.raises(RuntimeError):invoke()
    monkeypatch.setattr(runtime,'_finish_master_handoff',finish)
    state.maintenance=True
    with pytest.raises(RuntimeError):invoke()
    assert state.creates==1 and state.starts==0
