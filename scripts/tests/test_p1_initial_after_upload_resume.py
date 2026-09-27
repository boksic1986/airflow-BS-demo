"""Resumed upload still needs its first Master, not a replacement Master."""
import hashlib
import json
import subprocess

import pytest

from test_p02_registered_recovery import registered
from test_p02_resume_final import adapter, mirrored_final, final_inputs, view_inputs, handoff, runtime
from scripts import cce_paired_runtime as paired, wgs_resume


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260927_000000_AAAAAA'}],indirect=True)
@pytest.mark.parametrize('adapter',[{'initial':True}],indirect=True)
@pytest.mark.parametrize('scenario',['normal','upload_resume','unknown_create','foreign_owner','missing_upload','step3'])
def test_first_master_after_upload_resume(registered,monkeypatch,scenario):
    state,_,gate,upload,_,policy,bundle,h=registered
    binding=json.loads((bundle.parent/'batch-binding.json').read_bytes())
    def save(payload):
        payload['request_hash']=paired._request_digest(payload,'wgs')
        path=gate._request_path(payload['analysis_id'],1,payload['stage'])
        path.write_text(json.dumps(payload))
        return path
    prepare={**upload,'stage':'prepare','execution_id':upload['analysis_id']+'-prepare'}
    save(prepare);gate._write_status(prepare,'success')
    prepare_path=gate._request_path(upload['analysis_id'],1,'prepare')
    upload.update(resume_action_id='resume-upload',generation=2,
        execution_id=upload['analysis_id']+'-upload-g2',
        predecessor_execution_id=prepare['execution_id'],
        predecessor_receipt_hash=hashlib.sha256(prepare_path.with_suffix('.status.json').read_bytes()).hexdigest())
    upload_path=save(upload)
    gate._step_command(upload,'step1_upload')  # Real per-attempt writer registration.
    monkeypatch.setattr(runtime,'_obs_command',lambda *a,**k:subprocess.CompletedProcess([],0,b'',b''))
    h.config['obs']['upload_parallelism']=1
    writer=runtime.writer_for_bundle(runtime,bundle,h.contract,h.config)
    runtime.step1(bundle,h.contract,h.config,h.modules,writer=writer)
    gate._write_status(upload,'failed' if scenario=='missing_upload' else 'success')
    for payload,path in ((prepare,prepare_path),(upload,upload_path)):
        ended={k:payload[k] for k in ('analysis_id','attempt','stage','execution_id','generation','request_hash')}
        ended.update(pid=999999999,boot_id='synthetic-ended',process_start_time='0')
        path.with_suffix('.worker.json').write_text(json.dumps(ended))
    submit={**upload,'stage':'step3_monitor' if scenario=='step3' else 'step2_master',
        'execution_id':upload['analysis_id']+'-submit-g1','generation':1,
        'predecessor_execution_id':upload['execution_id'],
        'predecessor_receipt_hash':hashlib.sha256(upload_path.with_suffix('.status.json').read_bytes()).hexdigest()}
    if scenario=='normal':submit.pop('resume_action_id')
    save(submit)
    if scenario=='foreign_owner':
        current=next(iter(state.cms.values()))
        lock=json.loads(current['data']['lock']);lock['owner']['action']='another-writer'
        current['data']['lock']=json.dumps(lock)
    if scenario=='unknown_create':state.lose=True;state.hide=True
    def invoke():
        if scenario=='normal':
            return paired.submit_registered(submit,binding=binding,gate=gate,pipeline='wgs')
        wgs_resume.run_resume_stage(submit,gate=gate)
        return submit['_cce_master_result']
    if scenario in {'foreign_owner','missing_upload','step3','unknown_create'}:
        with pytest.raises(RuntimeError):invoke()
        if scenario=='unknown_create':
            assert state.creates==1
            with pytest.raises(RuntimeError):invoke()  # Unknown CREATE must not be resent.
        else:assert state.creates==0
    else:
        result=invoke()
        assert result['mode']=='submitted' and result['master_uid']=='new-uid'
        assert state.creates==state.starts==1
    assert state.deletes==0
