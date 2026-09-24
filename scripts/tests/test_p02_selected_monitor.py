"""A fresh monitor must reconstruct authority, not trust a deserialized receipt."""
import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

from test_p02_registered_recovery import registered
from test_p02_resume_final import adapter, mirrored_final, final_inputs, view_inputs, handoff, runtime
from scripts import cce_paired_runtime as paired, wgs_runtime_gate, wgs_resume
from cce_pipeline.assets import step3_status
from test_recovery_final import SubmissionManager, plugin_tests


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
@pytest.mark.parametrize('fault',[None,'receipt_uid','old_terminal','journal_view','lock_owner','gate',
    'old_marker','reclaimed_success','reclaimed_failure'])
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
    path=gate._request_path(submit['analysis_id'],1,'step3_monitor');path.write_text(json.dumps(current))
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
    if fault in ('old_marker','reclaimed_success'):
        evidence['workflow-completion.json']={'required':[{'path':'ANALYSIS_COMPLETE',
            'content':json.dumps({'schema_version':1,'status':'PASS',**h.contract['identity']})}]}
    if fault in ('reclaimed_success','reclaimed_failure'):
        record=runtime._read_master_handoff(selected,h.contract)
        monkeypatch.setattr(runtime,'_master_input_context',lambda:record)
        for phase in ('preflight','analysis'):
            env=runtime._recovery_phase_start(phase)
            root=Path(env['SNAKEMAKE_CCE_SUBMIT_EVIDENCE_DIR'])
            ctx=json.loads(Path(env['SNAKEMAKE_CCE_SUBMIT_CONTEXT_FILE']).read_bytes())
            SubmissionManager(ctx,root,plugin_tests.API(root,[])).claim_executor()
            runtime._recovery_phase_finished(phase,0)
        success=fault=='reclaimed_success'
        terminal=runtime._bind_master_terminal({'schema_version':1,'state':'SUCCEEDED' if success else 'FAILED',
            'exit_code':0 if success else 1,'failed_stage':'final_dryrun','finished_epoch':h.now+1,
            'exit_codes':{'preflight':0,'analysis':0,'final_dryrun':0 if success else 1}})
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
    monkeypatch.setattr(gate.time,'sleep',stop_after_observation)
    monkeypatch.setattr(gate,'_sync_rule_evidence' if pipeline=='wgs' else '_sync_evidence',bridge)
    monitor_binding=json.loads((bundle.parent/'batch-binding.json').read_bytes())
    monitor_binding['run_label']='cce-run-0123456789abcdef'
    monkeypatch.setattr(gate,'_load_binding',lambda payload:monitor_binding)
    # A genuine second process receives only registered JSON; no internal result.
    read_fd,write_fd=os.pipe()
    pid=os.fork()
    if pid==0:
        os.close(read_fd)
        try:
            payload=json.loads(path.read_bytes())
            if fault=='gate':
                try:
                    if pipeline=='wgs':wgs_resume.run_resume_stage(payload,gate=gate)
                    else:gate._execute_stage(submit['analysis_id'],1,'step3_monitor',1)
                except ObservedRunning:pass
                current_receipt=json.loads(path.with_suffix('.status.json').read_bytes())
                value=current_receipt['master'] if pipeline=='wgs' else {
                    'master_state':'RUNNING' if current_receipt['status']=='running' else 'FAILED',
                    'completed':current_receipt['completed_units']}
            else:
                value=paired.monitor_registered(payload,binding=json.loads((bundle.parent/'batch-binding.json').read_bytes()),
                    gate=gate,pipeline=pipeline)
                if pipeline=='wgs':gate._write_status(payload,'running',master=value)
                else:gate._write_status(path,payload,'running','monitoring',master=value)
            answer={'status':value,'receipt':json.loads(path.with_suffix('.status.json').read_bytes()),'pid':os.getpid()}
        except Exception as error:
            answer={'error':type(error).__name__+': '+str(error)}
        with os.fdopen(write_fd,'w') as stream:json.dump(answer,stream)
        os._exit(0)
    os.close(write_fd)
    with os.fdopen(read_fd) as stream:answer=json.load(stream)
    assert os.waitpid(pid,0)[1]==0
    if fault not in (None,'gate','old_marker','reclaimed_success','reclaimed_failure'):
        assert 'error' in answer and not answer['error'].startswith('AttributeError'),answer
    else:
        assert 'error' not in answer,answer
        assert answer['pid']!=os.getpid()
        assert answer['status']['master_state']=={'reclaimed_success':'SUCCEEDED','reclaimed_failure':'FAILED'}.get(fault,'RUNNING')
        assert answer['status']['completed']==(10 if fault=='reclaimed_success' else 2)
        assert answer['receipt']['cce_master_binding']['native']['job_uid']=='new-uid'
        assert answer['receipt']['cce_master_submit_execution_id']==submit['execution_id']
        assert answer['receipt']['execution_id']==current['execution_id']
        assert runtime._mirror_dir(selected,state.record['run_id']).is_dir()
    assert (state.creates,state.starts)==(1,1)
    assert original=={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}
