"""Registered restricted entry -> real native recovery; no cloud connection."""
import copy
import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from test_p02_resume_final import adapter,mirrored_final,final_inputs,view_inputs,handoff,runtime
from scripts import cce_paired_runtime as paired,wgs_runtime_gate,gatk_runtime_gate,wgs_resume
from cce_pipeline.assets import cce_writer_guard as guard


@pytest.fixture
def registered(adapter,tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    monkeypatch.setitem(sys.modules,'cce_paired_runtime',paired)
    state,_,bundle,old_cap,h=adapter
    pipeline=old_cap.context['pipeline']
    gate=wgs_runtime_gate if pipeline=='wgs' else gatk_runtime_gate
    control=tmp_path/'requests'/old_cap.context['analysis_id']/'attempt-1'
    monkeypatch.setattr(wgs_runtime_gate,'REQUEST_ROOT',tmp_path/'requests')
    binding=json.loads((bundle.parent/'batch-binding.json').read_bytes())
    payload={'analysis_id':old_cap.context['analysis_id'],'attempt':1,'stage':'step2_master',
        'schema_version':'wgs-runtime.request.v4','orchestration_contract_version':2,
        'execution_id':old_cap.context['analysis_id']+'-a1-step2_master-g8','generation':8,
        'request_hash':'b'*64,'resume_action_id':'new-action',
        'control_workdir':str(control),'runtime_workdir':str(bundle.parent)}
    if pipeline=='gatk':
        payload.pop('control_workdir')
        payload.update(schema_version='gatk-runtime.request.v1',pipeline='gatk',cce_bundle=str(bundle))
    excluded={'request_hash'} if pipeline=='gatk' else {
        'execution_id','generation','request_hash','predecessor_execution_id',
        'predecessor_generation','predecessor_receipt_hash'}
    payload['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in payload.items()
        if k not in excluded},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    request=gate._request_path(payload['analysis_id'],1,payload['stage'])
    request.write_text(json.dumps(payload))
    storage=tmp_path/'storage';storage.mkdir();(storage/'project').mkdir()
    native_path=Path(h.contract['paths']['run_dir'])
    (storage/native_path.name).symlink_to(storage/'project',target_is_directory=True)
    journal=tmp_path/'writer-journal';journal.mkdir()
    python_target=tmp_path/'python-real';python_target.write_text('synthetic');python_target.chmod(0o755)
    python_link=tmp_path/'python';python_link.symlink_to(python_target)
    def pin(path):return {'path':str(path),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    context={**old_cap.lock_context(),'generation':2,'action':state.record['recovery_context']['action'],
        'master_uid':'master-uid'}
    policy=tmp_path/'writers-v2.json'
    policy.write_text(json.dumps({'schema_version':2,'namespace':'synthetic',
        'writers':{'cli':pin(runtime.__file__),'platform':pin(paired.__file__)},
        'runtime_guard':pin(guard.__file__),'operator_python':str(python_link),
        'storage':{'native_root':str(native_path.parent),'mounted_root':str(storage),
            'canonical_root':'/storage/synthetic','root_inode':storage.stat().st_ino,
            'filesystem_id':os.statvfs(storage).f_fsid},
        'journal_root':str(journal),'bindings':[{'bundle':str(bundle),
            'contract_sha256':hashlib.sha256((bundle/'BATCH_RUNTIME.yaml').read_bytes()).hexdigest(),
            'files_sha256':runtime._handoff_binding(bundle,h.contract)['files_sha256'],'context':context}]}))
    policy.chmod(0o600)
    def trust(path):
        path=Path(path)
        root=tmp_path if path.is_relative_to(tmp_path) else next(
            parent for parent in path.parents if parent.name in {'native','platform'})
        return {'path':str(path),'trust_root':str(root),
            'maintainer_uids':[os.getuid()],'maintainer_gids':[os.getgid()]}
    bootstrap=tmp_path/'cce-paired-deployment-v1.json'
    bootstrap.write_text(json.dumps({'schema_version':1,'policy':trust(policy),
        'writers':{'cli':trust(Path(runtime.__file__)),'platform':trust(Path(paired.__file__))},
        'runtime_guard':trust(Path(guard.__file__)),
        'operator_python':{**trust(python_link),'canonical_path':str(python_target.resolve())}}))
    bootstrap.chmod(0o600)
    monkeypatch.setattr(guard,'DEPLOYMENT_TRUST_ROOT',tmp_path)
    monkeypatch.setattr(guard,'DEPLOYMENT_TRUST_PATH',bootstrap)
    monkeypatch.setattr(paired,'load_runtime',lambda:runtime)
    monkeypatch.setattr(runtime,'_operator_paired_activation',True,raising=False)
    monkeypatch.setattr(gate,'_load_binding',lambda p:binding)
    def invoke():
        lock=request.with_suffix('.worker.lock')
        with lock.open('a+') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if pipeline=='wgs':
                wgs_resume.run_resume_stage(payload,gate=gate)
                gate._write_status(payload,'success')
            else:
                gate._execute_stage(payload['analysis_id'],1,payload['stage'],8)
        path=request.with_suffix('.status.json')
        return json.loads(path.read_bytes())
    return state,invoke,gate,payload,request,policy,bundle,h


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
@pytest.mark.parametrize('scenario',['success','request_changed','other_writer','uncertain_dispatcher',
    'foreign_lock','missing_lock','unregistered'])
def test_registered_entry_fences_before_master_replacement(registered,scenario):
    state,invoke,gate,payload,request,policy,bundle,h=registered
    before={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}
    locked=None
    if scenario=='request_changed':
        value=json.loads(request.read_bytes());value['resume_action_id']='different-action'
        request.write_text(json.dumps(value))
    elif scenario=='other_writer':
        path=gate._request_path(payload['analysis_id'],1,'step5_download').with_suffix('.worker.lock')
        locked=path.open('a+');fcntl.flock(locked,fcntl.LOCK_EX|fcntl.LOCK_NB)
    elif scenario=='foreign_lock':
        cm=next(iter(state.cms.values()));value=json.loads(cm['data']['lock'])
        value['owner']['master_uid']='foreign-uid';cm['data']['lock']=json.dumps(value)
    elif scenario=='missing_lock':
        state.cms.clear()
    elif scenario=='uncertain_dispatcher':
        path=gate._request_path(payload['analysis_id'],1,'step5_download')
        suffix='.worker.json' if gate is wgs_runtime_gate else '.worker.state.json'
        path.with_suffix(suffix).write_text(json.dumps({'pid':999999999,'state':'uncertain'}))
    elif scenario=='unregistered':
        value=json.loads(policy.read_bytes());value['bindings']=[];policy.write_text(json.dumps(value))
    try:
        if scenario=='success':
            receipt=invoke()
            assert receipt['status']=='success'
            assert receipt['cce_master_binding']['native']['job_uid']=='new-uid'
            assert receipt['cce_master_binding']['native']['execution_generation']==3
            assert receipt['cce_master_binding']['platform_execution']['generation']==8
            invoke()
            assert (state.creates,state.starts)==(1,1)
        else:
            with pytest.raises((ValueError,RuntimeError,BlockingIOError)):
                invoke()
            assert (state.creates,state.starts,state.deletes)==(0,0,0)
    finally:
        if locked:locked.close()
    assert before=={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}
