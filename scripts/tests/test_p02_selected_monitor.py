"""A fresh monitor must reconstruct authority, not trust a deserialized receipt."""
import copy
import hashlib
import json
import os
import shutil
import traceback
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from test_p02_registered_recovery import registered
from test_p02_resume_final import adapter, mirrored_final, final_inputs, view_inputs, handoff as native_handoff, runtime
from scripts import cce_paired_runtime as paired, wgs_runtime_gate, wgs_resume
from cce_pipeline.assets import step3_status
from test_recovery_final import SubmissionManager, plugin_tests
REAL_RELEASE=runtime._release_batch_lock


@pytest.fixture
def handoff(tmp_path):
    # Declare downstream fields before the native producer freezes its inputs.
    for h in native_handoff.__wrapped__(tmp_path):
        h.contract.update(tools={'zstd_bin':'synthetic'},permissions={})
        (h.bundle/'BATCH_RUNTIME.yaml').write_text(yaml.safe_dump(h.contract))
        yield h


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
@pytest.mark.parametrize('outcome',['normal','lost_response','unknown','recover','bound_crash','reattach','interrupted','reattach_worker'])
def test_registered_initial_submission_selects_its_view(registered,monkeypatch,outcome):
    state,launch,gate,payload,request,policy,old_bundle,h=registered
    pipeline='wgs' if gate is wgs_runtime_gate else 'gatk'
    if outcome=='reattach_worker' and pipeline!='wgs':
        pytest.skip('Only WGS has a separate reattach worker entry')
    initial_root=h.bundle.parent/'initial-runtime'
    request_root=initial_root/'requests'
    bundle=initial_root/'runs'/payload['analysis_id']/'attempt-1'/'cce'
    shutil.copytree(h.bundle,bundle)
    monkeypatch.setattr(wgs_runtime_gate,'REQUEST_ROOT',request_root)
    monkeypatch.setenv('GATK_RUNTIME_REQUEST_ROOT',str(request_root))
    request_root.mkdir(parents=True,exist_ok=True)
    request=gate._request_path(payload['analysis_id'],1,'step2_master')
    request.parent.mkdir(parents=True,exist_ok=True)
    if pipeline=='wgs':payload['control_workdir']=str(request.parent)
    binding=json.loads((old_bundle.parent/'batch-binding.json').read_bytes())
    binding['cce_bundle']=str(bundle)
    (bundle.parent/'batch-binding.json').write_text(json.dumps(binding))
    monkeypatch.setattr(gate,'_load_binding',lambda p:binding)
    payload.pop('resume_action_id');payload.update(runtime_workdir=str(bundle.parent))
    if pipeline=='gatk':payload['cce_bundle']=str(bundle)
    excluded={'request_hash'} if pipeline=='gatk' else {'execution_id','generation','request_hash',
        'predecessor_execution_id','predecessor_generation','predecessor_receipt_hash'}
    def save(p,path):
        p['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in p.items() if k not in excluded},
            sort_keys=True,separators=(',',':')).encode()).hexdigest();path.write_text(json.dumps(p))
    save(payload,request)
    value=json.loads(policy.read_bytes());registration=value['bindings'][0]
    registration.update(bundle=str(bundle),files_sha256=runtime._handoff_binding(bundle,h.contract)['files_sha256'])
    registration['context'].update(generation=1,action=payload['execution_id'],master_uid='')
    policy.write_text(json.dumps(value))
    state.cms.clear();state.job=None;state.worker=None
    state.lose=outcome in ('lost_response','unknown');state.hide=outcome=='unknown'
    monkeypatch.setenv('WGS_EXECUTION_ENABLED','true');monkeypatch.setenv('WGS_RUNTIME_ADAPTER_ENABLED','true')
    before={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}
    if outcome=='interrupted':
        finish=runtime._finish_master_handoff
        def interrupted(*a,**kw):raise TimeoutError('synthetic handoff disconnect')
        monkeypatch.setattr(runtime,'_finish_master_handoff',interrupted)
        with pytest.raises(TimeoutError,match='synthetic'):
            paired.submit_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
        monkeypatch.setattr(runtime,'_finish_master_handoff',finish)
        archived=request.parent/'request-history'/'step2_master'/('generation-'+str(payload['generation'])+'.json')
        archived.parent.mkdir(parents=True);archived.write_bytes(request.read_bytes())
        payload.update(resume_action_id='resume-interrupted-initial',generation=9,execution_id='interrupted-step2')
        save(payload,request)
    if outcome=='bound_crash':
        atomic=runtime._atomic_write_text
        def crash_after_bind(path,text,*a,**kw):
            if Path(path).name.startswith('submission-') and '"state": "confirmed"' in text:
                raise RuntimeError('synthetic crash after lock bind')
            return atomic(path,text,*a,**kw)
        monkeypatch.setattr(runtime,'_atomic_write_text',crash_after_bind)
        with pytest.raises(RuntimeError,match='synthetic crash'):
            paired.submit_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
        monkeypatch.setattr(runtime,'_atomic_write_text',atomic)
    for _ in range(2):
        if outcome=='unknown':
            with pytest.raises(RuntimeError,match='outcome'):
                paired.submit_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
            continue
        if outcome=='interrupted':
            payload['_cce_master_result']=paired.resume_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
            if pipeline=='wgs':gate._write_status(payload,'success')
            else:gate._write_status(request,payload,'success','submitted')
            continue
        if pipeline=='wgs':
            gate.run_stage(payload);gate._write_status(payload,'success')
        else:gate._execute_stage(payload['analysis_id'],1,'step2_master',8)
    if outcome=='unknown':
        assert (state.creates,state.starts)==(1,0)
        return
    receipt=json.loads(request.with_suffix('.status.json').read_bytes())
    assert receipt['cce_master_binding']['native']['execution_generation']==1
    current={k:v for k,v in payload.items() if not k.startswith('_')}
    current.update(stage='step3_monitor',execution_id=payload['analysis_id']+'-a1-step3_monitor-g1',generation=1,
        predecessor_execution_id=payload['execution_id'],predecessor_receipt_hash=
        hashlib.sha256(request.with_suffix('.status.json').read_bytes()).hexdigest() if pipeline=='wgs' else receipt['receipt_hash'])
    path=gate._request_path(payload['analysis_id'],1,'step3_monitor');save(current,path)
    h.modules=(*h.modules[:3],step3_status)
    query=runtime._kubectl_json
    def ready(config,kind,*a,**k):
        result=query(config,kind,*a,**k)
        if kind=='pods':
            for pod in result.get('items',[]):pod['status']['conditions']=[{'type':'Ready','status':'True'}]
        return result
    monkeypatch.setattr(runtime,'_kubectl_json',ready)
    monkeypatch.setattr(runtime,'_read_pod_evidence',lambda *a,**k:({'START_CONFIRMED.json':state.confirmation},None))
    assert paired.monitor_registered(current,binding=binding,gate=gate,pipeline=pipeline)['master_state']=='RUNNING'
    assert (state.creates,state.starts)==(1,1)
    if outcome in ('reattach','reattach_worker'):
        archived=request.parent/'request-history'/'step2_master'/('generation-'+str(payload['generation'])+'.json')
        archived.parent.mkdir(parents=True);archived.write_bytes(request.read_bytes())
        old_execution={k:payload[k] for k in ('execution_id','generation','request_hash')}
        if outcome!='reattach_worker':request.with_suffix('.status.json').rename(archived.with_suffix('.status.json'))
        payload={k:v for k,v in payload.items() if not k.startswith('_')}
        payload.update(resume_action_id='observe-existing',generation=9,execution_id='observe-existing-step2')
        if outcome=='reattach_worker':payload['resume_previous_execution']=old_execution
        save(payload,request)
        if outcome=='reattach_worker':gate._finish_reattached_stage(payload)
        else:
            result=paired.resume_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
            payload['_cce_master_result']=result
            if pipeline=='wgs':gate._write_status(payload,'success')
            else:gate._write_status(request,payload,'success','submitted')
        receipt=json.loads(request.with_suffix('.status.json').read_bytes())
        current.pop('_cce_master_result',None)
        current.update(resume_action_id=payload['resume_action_id'],predecessor_execution_id=payload['execution_id'],
            predecessor_receipt_hash=hashlib.sha256(request.with_suffix('.status.json').read_bytes()).hexdigest()
                if pipeline=='wgs' else receipt['receipt_hash'])
        save(current,path)
        assert paired.monitor_registered(current,binding=binding,gate=gate,pipeline=pipeline)['master_state']=='RUNNING'
        assert current['_cce_master_result']['cce_master_binding']['platform_execution']['generation']==8
        assert (state.creates,state.starts)==(1,1)
    if outcome=='recover':
        selected=Path(state.new_view)
        record=runtime._read_master_handoff(selected,h.contract)
        monkeypatch.setattr(runtime,'_master_input_context',lambda:record)
        for phase in ('preflight','analysis'):
            env=runtime._recovery_phase_start(phase)
            root=Path(env['SNAKEMAKE_CCE_SUBMIT_EVIDENCE_DIR'])
            ctx=json.loads(Path(env['SNAKEMAKE_CCE_SUBMIT_CONTEXT_FILE']).read_bytes())
            SubmissionManager(ctx,root,plugin_tests.API(root,[])).claim_executor()
            runtime._recovery_phase_finished(phase,0)
        terminal=runtime._bind_master_terminal({'schema_version':1,'state':'FAILED',
            'exit_code':1,'failed_stage':'final_dryrun','finished_epoch':h.now+1,
            'exit_codes':{'preflight':0,'analysis':0,'final_dryrun':1}})
        final=json.loads((Path(h.contract['paths']['run_dir'])/'evidence'/record['run_id']/'recovery-final.json').read_bytes())
        runtime._write_mirror_evidence(selected,record['run_id'],{'RUN_FAILED.json':terminal,'recovery-final.json':final,
            'START_CONFIRMED.json':state.confirmation},
            project=record['project'],batch=record['batch'])
        # Ended initial dispatcher and reclaimed Master; no fabricated old bundle handoff.
        ended={k:payload[k] for k in ('analysis_id','attempt','stage','execution_id','generation','request_hash')}
        if pipeline=='wgs':ended.update(pid=999999999,boot_id='ended',process_start_time='0')
        else:ended.update(schema_version='gatk-runtime.dispatcher.v1',state='finished',process=None)
        request.with_suffix('.worker.json' if pipeline=='wgs' else '.worker.state.json').write_text(json.dumps(ended))
        state.job=None
        create=runtime._create_job_from_path
        def replacement(config,manifest):
            job=create(config,manifest);job['metadata']['uid']='replacement-uid';return job
        monkeypatch.setattr(runtime,'_create_job_from_path',replacement)
        previous_query=runtime._kubectl_json
        def replacement_pods(config,kind,*a,**kw):
            if kind=='pods' and state.job and state.job['metadata']['uid']=='replacement-uid':
                return {'items':[{'metadata':{'name':'new-pod','uid':'replacement-pod',
                    'ownerReferences':[{'controller':True,'kind':'Job','uid':'replacement-uid'}]},
                    'status':{'phase':'Running','conditions':[{'type':'Ready','status':'True'}]}}]}
            return previous_query(config,kind,*a,**kw)
        monkeypatch.setattr(runtime,'_kubectl_json',replacement_pods)
        transport=runtime._run
        def confirm_replacement(command,**kw):
            value=transport(command,**kw)
            if 'touch' in command:state.confirmation['pod_uid']='replacement-pod'
            return value
        monkeypatch.setattr(runtime,'_run',confirm_replacement)
        current.pop('_cce_master_result',None)
        current.update(resume_action_id='resume-initial',generation=2,execution_id='resume-initial-step3')
        save(current,path)
        result=paired.resume_registered(current,binding=binding,gate=gate,pipeline=pipeline)
        assert result['cce_master_binding']['native']['execution_generation']==2
        assert result['cce_master_binding']['source_bundle']==str(bundle)
        assert paired.resume_registered(current,binding=binding,gate=gate,pipeline=pipeline)['master_uid']==result['master_uid']
        assert paired.monitor_registered(current,binding=binding,gate=gate,pipeline=pipeline)['master_state']=='RUNNING'
        assert (state.creates,state.starts)==(2,2)
    assert before=={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
def test_direct_step3_replacement_and_observation(registered,monkeypatch):
    state,launch,gate,payload,request,policy,bundle,h=registered
    pipeline='wgs' if gate is wgs_runtime_gate else 'gatk'
    # The authenticated recovery starts at Step3, not an invented successful Step2.
    request.unlink()
    payload.update(stage='step3_monitor',execution_id=payload['analysis_id']+'-a1-step3_monitor-g8')
    excluded={'request_hash'} if pipeline=='gatk' else {'execution_id','generation','request_hash',
        'predecessor_execution_id','predecessor_generation','predecessor_receipt_hash'}
    payload['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in payload.items() if k not in excluded},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()
    path=gate._request_path(payload['analysis_id'],1,payload['stage']);path.write_text(json.dumps(payload))
    binding=json.loads((bundle.parent/'batch-binding.json').read_bytes())
    h.modules=(*h.modules[:3],step3_status)
    monkeypatch.setattr(runtime,'_read_pod_evidence',lambda *a,**k:({'START_CONFIRMED.json':state.confirmation},None))
    query=runtime._kubectl_json
    def ready(config,kind,*a,**k):
        value=query(config,kind,*a,**k)
        if kind=='pods':
            for pod in value.get('items',[]):pod['status']['conditions']=[{'type':'Ready','status':'True'}]
        return value
    monkeypatch.setattr(runtime,'_kubectl_json',ready)
    monkeypatch.setattr(paired,'selected_runtime',lambda:(Path(runtime.__file__),'/operator/python'))
    class Observed(BaseException):pass
    def stop(*a):raise Observed()
    monkeypatch.setattr(gate.time,'sleep',stop)
    monkeypatch.setattr(gate,'_sync_rule_evidence' if pipeline=='wgs' else '_sync_evidence',lambda *a,**k:None)
    if pipeline=='wgs':monkeypatch.setattr(gate,'_binding_run_label',lambda b:'cce-run-0123456789abcdef')
    with pytest.raises(Observed):
        if pipeline=='wgs':wgs_resume.run_resume_stage(payload,gate=gate)
        else:gate._execute_stage(payload['analysis_id'],1,payload['stage'],8)
    receipt=json.loads(path.with_suffix('.status.json').read_bytes())
    assert receipt['status']=='running'
    assert receipt['cce_master_binding']['native']['job_uid']=='new-uid'
    # Replay uses durable recovery state. Observation must not need a Step2 receipt.
    assert paired.resume_registered(json.loads(path.read_bytes()),binding=binding,gate=gate,pipeline=pipeline)['master_uid']=='new-uid'
    fresh=json.loads(path.read_bytes())
    assert paired.monitor_registered(fresh,binding=binding,gate=gate,pipeline=pipeline)['master_state']=='RUNNING'
    assert fresh['_cce_master_result']['cce_master_submit_execution_id']==payload['execution_id']
    assert (state.creates,state.starts)==(1,1)


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
@pytest.mark.parametrize('fault',[None,'receipt_uid','old_terminal','journal_view','lock_owner','gate',
    'old_marker','reclaimed_success','reclaimed_failure','recoverable_failure','downstream','reconnect','reconnect_downstream'])
def test_fresh_monitor_uses_selected_master_and_rejects_stale_authority(registered,monkeypatch,fault):
    state,launch,gate,submit,request,policy,bundle,h=registered
    original={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}
    receipt=launch()
    monkeypatch.setattr(paired,'selected_runtime',lambda:(Path(runtime.__file__),'/operator/python'))
    selected=Path(state.new_view)
    receipt_path=request.with_suffix('.status.json')
    pipeline='wgs' if gate is wgs_runtime_gate else 'gatk'
    if fault=='receipt_uid':
        receipt['cce_master_binding']['native']['job_uid']='foreign-uid'
        if pipeline=='gatk':
            receipt['receipt_hash']=hashlib.sha256(json.dumps({k:v for k,v in receipt.items() if k!='receipt_hash'},
                sort_keys=True,separators=(',',':')).encode()).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
    if fault=='journal_view':
        journal=(request.parent/('recovery-new-action.json' if pipeline=='wgs' else 'resume-master-uid.json'))
        value=json.loads(journal.read_bytes());value['recovery_v2']['view']=str(bundle)
        journal.write_text(json.dumps(value))
    if fault=='lock_owner':
        cm=next(iter(state.cms.values()));value=json.loads(cm['data']['lock'])
        value['owner']['master_uid']='foreign-uid';cm['data']['lock']=json.dumps(value)
    current={k:v for k,v in json.loads(request.read_bytes()).items() if k!='request_hash'}
    current.update(stage='step3_monitor',generation=1,
        execution_id=submit['analysis_id']+'-a1-step3_monitor-g1',
        predecessor_execution_id=submit['execution_id'],
        predecessor_receipt_hash=hashlib.sha256(receipt_path.read_bytes()).hexdigest() if pipeline=='wgs' else receipt['receipt_hash'])
    excluded=set() if pipeline=='gatk' else {'execution_id','generation','predecessor_execution_id',
        'predecessor_generation','predecessor_receipt_hash'}
    current['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in current.items() if k not in excluded},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()
    path=gate._request_path(submit['analysis_id'],1,'step3_monitor')
    if hasattr(h,'register_stage'):
        current=h.register_stage('step3_monitor')
    else:path.write_text(json.dumps(current))
    if fault in ('reconnect','reconnect_downstream'):
        current['resume_action_id']='observe-active-master'
        current.pop('request_hash')
        current['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in current.items() if k not in excluded},
            sort_keys=True,separators=(',',':')).encode()).hexdigest()
        path.write_text(json.dumps(current))
        ended={k:submit[k] for k in ('analysis_id','attempt','stage','execution_id','generation','request_hash')}
        if pipeline=='wgs':ended.update(pid=999999999,boot_id='ended',process_start_time='0')
        else:ended.update(schema_version='gatk-runtime.dispatcher.v1',state='finished',process=None)
        request.with_suffix('.worker.json' if pipeline=='wgs' else '.worker.state.json').write_text(json.dumps(ended))
    h.modules=(*h.modules[:3],step3_status)
    query=runtime._kubectl_json
    def ready_pods(config,kind,*args,**kwargs):
        result=query(config,kind,*args,**kwargs)
        if kind=='pods':
            for pod in result.get('items',[]):
                pod['status']['conditions']=[{'type':'Ready','status':'True'}]
        return result
    monkeypatch.setattr(runtime,'_kubectl_json',ready_pods)
    evidence={'analysis.log':'2 of 10 steps (20%) done\n','START_CONFIRMED.json':state.confirmation}
    if fault=='old_terminal':evidence['RUN_FAILED.json']=state.evidence['RUN_FAILED.json']
    if fault in ('old_marker','reclaimed_success','downstream','reconnect_downstream'):
        evidence['workflow-completion.json']={'required':[{'path':'ANALYSIS_COMPLETE',
            'content':json.dumps({'schema_version':1,'status':'PASS',**h.contract['identity']})}]}
    if fault in ('reclaimed_success','reclaimed_failure','recoverable_failure','downstream','reconnect_downstream'):
        record=runtime._read_master_handoff(selected,h.contract)
        monkeypatch.setattr(runtime,'_master_input_context',lambda:record)
        for phase in ('preflight','analysis'):
            env=runtime._recovery_phase_start(phase)
            root=Path(env['SNAKEMAKE_CCE_SUBMIT_EVIDENCE_DIR'])
            ctx=json.loads(Path(env['SNAKEMAKE_CCE_SUBMIT_CONTEXT_FILE']).read_bytes())
            clock=plugin_tests.Clock()
            manager=SubmissionManager(ctx,root,plugin_tests.API(root,[plugin_tests.admission()]*3),
                monotonic=clock.monotonic,sleep=clock.sleep)
            manager.claim_executor()
            if fault=='recoverable_failure':
                import logging
                from snakemake_logger_plugin_rule_status.failure_summary import FailureSummary
                from snakemake_interface_logger_plugins.common import LogEvent
                audit=FailureSummary(root/'submit-context.json',root)
                event=logging.LogRecord('synthetic',logging.INFO,'synthetic',1,'',(),None)
                event.event=LogEvent.WORKFLOW_STARTED;audit.emit(event)
                if phase=='analysis':
                    requested=plugin_tests.body();requested.metadata.name='snakejob-new-absent'
                    with pytest.raises(plugin_tests.module().SubmissionFailure):manager.submit(requested,1)
                    event=logging.LogRecord('synthetic',logging.ERROR,'synthetic',1,'',(),None)
                    event.event=LogEvent.ERROR;event.exception='SubmissionFailure';audit.emit(event)
                audit.close()
            runtime._recovery_phase_finished(phase,1 if fault=='recoverable_failure' and phase=='analysis' else 0)
        success=fault in ('reclaimed_success','downstream','reconnect_downstream')
        terminal=runtime._bind_master_terminal({'schema_version':1,'state':'SUCCEEDED' if success else 'FAILED',
            'exit_code':0 if success else 1,'failed_stage':'analysis' if fault=='recoverable_failure' else 'final_dryrun','finished_epoch':h.now+1,
            'exit_codes':{'preflight':0,'analysis':1 if fault=='recoverable_failure' else 0,
                'final_dryrun':None if fault=='recoverable_failure' else 0 if success else 1}})
        evidence['RUN_COMPLETE.json' if success else 'RUN_FAILED.json']=terminal
        evidence['recovery-final.json']=json.loads((Path(h.contract['paths']['run_dir'])/'evidence'/record['run_id']/'recovery-final.json').read_bytes())
        runtime._write_mirror_evidence(selected,record['run_id'],evidence,
            project=record['project'],batch=record['batch'])
        state.job=None
    monkeypatch.setattr(runtime,'_read_pod_evidence',lambda *a,**kw:(copy.deepcopy(evidence),None))
    class ObservedRunning(BaseException):pass
    def stop_after_observation(*args):raise ObservedRunning()
    def bridge(payload,binding,**kwargs):
        assert binding['cce_bundle']==str(selected), 'logger must follow selected Master'
        return None
    monkeypatch.setattr(gate,'_sync_rule_evidence' if pipeline=='wgs' else '_sync_evidence',bridge)
    monitor_binding=json.loads((bundle.parent/'batch-binding.json').read_bytes())
    # The native fixture uses synthetic-run. Keep that inventory identity;
    # normalize only the unrelated WGS display/bridge label boundary.
    if pipeline=='wgs':monkeypatch.setattr(gate,'_binding_run_label',lambda b:'cce-run-0123456789abcdef')
    monkeypatch.setattr(gate,'_load_binding',lambda payload:monitor_binding)
    # A genuine second process receives only registered JSON; no internal result.
    read_fd,write_fd=os.pipe()
    pid=os.fork()
    if pid==0:
        os.close(read_fd)
        try:
            payload=json.loads(path.read_bytes())
            if fault=='gate' or hasattr(h,'register_stage'):
                monkeypatch.setattr(gate.time,'sleep',stop_after_observation)
                try:
                    if pipeline=='wgs':wgs_resume.run_resume_stage(payload,gate=gate)
                    else:gate._execute_stage(submit['analysis_id'],1,'step3_monitor',1)
                except ObservedRunning:pass
                current_receipt=json.loads(path.with_suffix('.status.json').read_bytes())
                value=current_receipt['master'] if pipeline=='wgs' else {
                    'master_state':{'running':'RUNNING','success':'SUCCEEDED'}.get(current_receipt['status'],'FAILED'),
                    'completed':current_receipt['completed_units']}
            else:
                if fault=='reconnect':paired.prepare_monitor_registered(payload,binding=monitor_binding,gate=gate,pipeline=pipeline)
                value=paired.monitor_registered(payload,binding=json.loads((bundle.parent/'batch-binding.json').read_bytes()),
                    gate=gate,pipeline=pipeline)
                status={'SUCCEEDED':'success','FAILED':'failed'}.get(value['master_state'],'running')
                if pipeline=='wgs':gate._write_status(payload,status,master=value)
                else:gate._write_status(path,payload,status,'monitoring',master=value)
            answer={'status':value,'receipt':json.loads(path.with_suffix('.status.json').read_bytes()),'pid':os.getpid()}
        except Exception as error:
            answer={'error':type(error).__name__+': '+str(error)}
        with os.fdopen(write_fd,'w') as stream:json.dump(answer,stream)
        os._exit(0)
    os.close(write_fd)
    with os.fdopen(read_fd) as stream:answer=json.load(stream)
    assert os.waitpid(pid,0)[1]==0
    if fault not in (None,'gate','old_marker','reclaimed_success','reclaimed_failure','recoverable_failure','downstream','reconnect','reconnect_downstream'):
        assert 'error' in answer and not answer['error'].startswith('AttributeError'),answer
    else:
        assert 'error' not in answer,answer
        assert answer['pid']!=os.getpid()
        assert answer['status']['master_state']=={'reclaimed_success':'SUCCEEDED','downstream':'SUCCEEDED','reconnect_downstream':'SUCCEEDED','reclaimed_failure':'FAILED','recoverable_failure':'FAILED'}.get(fault,'RUNNING')
        assert answer['status']['completed']==(10 if fault in ('reclaimed_success','downstream','reconnect_downstream') else 2)
        assert answer['receipt']['cce_master_binding']['native']['job_uid']=='new-uid'
        assert answer['receipt']['cce_master_submit_execution_id']==submit['execution_id']
        assert answer['receipt']['execution_id']==current['execution_id']
        assert runtime._mirror_dir(selected,state.record['run_id']).is_dir()
        if fault=='recoverable_failure':
            proof=answer['receipt']['cce_recovery_evidence']
            assert proof['binding']==answer['receipt']['cce_master_binding']
            assert proof['terminal']['generation']==3
            assert proof['binding']['platform_execution']['generation']==8
            assert proof['terminal']['executor_failure_count']==1
            before_receipt=path.with_suffix('.status.json').read_bytes()
            before_mutations=(state.creates,state.deletes,state.starts,state.copies,copy.deepcopy(state.cms))
            observed=paired.worker_probe_command(['--recovery-probe',current['analysis_id'],str(current['attempt']),
                str(current['generation']),current['request_hash'],'a'*32],gate=gate,pipeline=pipeline)
            assert observed['cce_recovery_evidence']==proof
            assert path.with_suffix('.status.json').read_bytes()==before_receipt
            assert (state.creates,state.deletes,state.starts,state.copies,state.cms)==before_mutations
            with pytest.raises(ValueError):
                paired.probe_waiting_workers(json.loads(path.read_bytes()),binding=monitor_binding,
                    gate=gate,pipeline=pipeline,generation=current['generation']+1,request_hash=current['request_hash'],nonce='a'*32)
    if fault in ('downstream','reconnect_downstream'):
        monkeypatch.setattr(runtime,'_release_batch_lock',REAL_RELEASE)
        calls=[]
        def publish(**kw):calls.append(('publish',kw));return True
        def marker(name):
            root=bundle/'cloud_delivery';root.mkdir(exist_ok=True)
            values=dict(schema_version='1',status='PASS',**h.contract['identity'])
            (root/name).write_text('\n'.join(k+'='+str(v) for k,v in values.items()))
        def download(**kw):calls.append(('download',kw));marker('DOWNLOAD_VERIFIED')
        def materialize(*args,**kw):calls.append(('materialize',args));marker('MATERIALIZED')
        h.config['obs']={'obsutil_bin':'synthetic','config_file':'synthetic'}
        h.modules=(SimpleNamespace(reconcile_publish_status=publish,download_verify=download,
            materialize_results=materialize),*h.modules[1:])
        # Keep log transport at its existing tested boundary; exercise actual
        # native stage bodies, not a fake downstream stage or forged capability.
        monkeypatch.setattr(runtime,'download_snakemake_logs',lambda *a,**k:None)
        if pipeline=='gatk':
            monkeypatch.setattr(gate,'_materialize_to_approved_root',lambda p:materialize(bundle/'cloud_delivery','approved-root'))
        previous=current
        # Terminal worker sidecars model the real restricted dispatcher. A free
        # flock by itself must not count as proof that sibling writers ended.
        def finished_worker(request_path):
            p=json.loads(request_path.read_bytes())
            value={k:p[k] for k in ('analysis_id','attempt','stage','execution_id','generation','request_hash')}
            if pipeline=='wgs':value.update(pid=999999999,boot_id='synthetic-ended',process_start_time='0')
            else:value.update(schema_version='gatk-runtime.dispatcher.v1',state='finished',process=None)
            request_path.with_suffix('.worker.json' if pipeline=='wgs' else '.worker.state.json').write_text(json.dumps(value))
        finished_worker(request);finished_worker(path)
        # Keep the prior generation's verified terminal Worker: Task4 cannot
        # assume that the later TTL rollout has already removed it.
        for stage in ('step4_publish','step5_download','step6_materialize'):
            if hasattr(h,'ingest_stage'):h.ingest_stage(previous['stage'])
            previous_path=gate._request_path(submit['analysis_id'],1,previous['stage'])
            previous_receipt=json.loads(previous_path.with_suffix('.status.json').read_bytes())
            downstream={**previous,'stage':stage,'execution_id':submit['analysis_id']+'-a1-'+stage+'-g1',
                'predecessor_execution_id':previous['execution_id'],
                'predecessor_receipt_hash':hashlib.sha256(previous_path.with_suffix('.status.json').read_bytes()).hexdigest()
                    if pipeline=='wgs' else previous_receipt['receipt_hash']}
            downstream.pop('request_hash')
            downstream['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in downstream.items() if k not in excluded},
                sort_keys=True,separators=(',',':')).encode()).hexdigest()
            stage_path=gate._request_path(submit['analysis_id'],1,stage)
            if hasattr(h,'register_stage'):downstream=h.register_stage(stage)
            else:stage_path.write_text(json.dumps(downstream))
            if stage=='step6_materialize':
                # Current-generation journal projection must never hide an
                # unknown live workload from the final directory release.
                marker('MATERIALIZED');state.unknown=True
                def reject_unknown(rt,base,view,uid,contract,config,modules,writer):
                    paired._release_registered_writer(downstream,monitor_binding,gate,pipeline,
                        rt,base,view,uid,contract,config,writer)
                with pytest.raises(ValueError,match='inventory|unknown|unbound'):
                    paired._selected_registered(downstream,binding=monitor_binding,gate=gate,
                        pipeline=pipeline,operation=reject_unknown)
                assert json.loads(next(iter(state.cms.values()))['data']['lock'])['state']=='OWNED'
                state.unknown=False
            command=gate._step_command(downstream,stage) if pipeline=='wgs' else gate._step(downstream,stage)
            assert command[1:3]==[str(paired.PLATFORM_SOURCE),'--registered-stage']
            # The existing transfer process boundary gets only registered IDs.
            # No Python capability or caller-chosen view survives this handoff.
            read_fd,write_fd=os.pipe();pid=os.fork()
            if pid==0:
                os.close(read_fd)
                try:
                    paired.run_registered_stage(command[3:])
                    answer={'calls':calls,'locks':state.cms}
                except Exception as error:answer={'error':traceback.format_exc()}
                with os.fdopen(write_fd,'w') as stream:json.dump(answer,stream,default=str)
                os._exit(0)
            os.close(write_fd)
            with os.fdopen(read_fd) as stream:child=json.load(stream)
            assert os.waitpid(pid,0)[1]==0
            if 'error' in child:pytest.fail(child['error'])
            calls=child['calls']
            state.cms=child['locks']
            if pipeline=='wgs':gate._write_status(downstream,'success')
            else:gate._write_status(stage_path,downstream,'success','completed')
            result=json.loads(stage_path.with_suffix('.status.json').read_bytes())
            assert result['cce_master_submit_execution_id']==submit['execution_id']
            previous=json.loads(stage_path.read_bytes())
            finished_worker(stage_path)
        assert [c[0] for c in calls]==['publish','download','materialize']
        assert calls[0][1]['work_root']==str(bundle/'delivery-publish')
        assert calls[1][1]['download_root']==str(bundle/'cloud_delivery')
        assert calls[2][1][0]==str(bundle/'cloud_delivery')
        assert json.loads(next(iter(state.cms.values()))['data']['lock'])['state']=='RELEASED'
        before_calls=len(calls)
        paired.downstream_registered(downstream,binding=monitor_binding,gate=gate,pipeline=pipeline,
            materialize=lambda p:pytest.fail('released Step6 must not materialize again'))
        assert len(calls)==before_calls
    assert (state.creates,state.starts)==(1,1)
    assert original=={name:(bundle/name).read_bytes() for name in original}
