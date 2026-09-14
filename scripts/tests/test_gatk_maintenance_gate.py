import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('gatk_maintenance_gate', Path(__file__).parents[1]/'gatk_maintenance_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


@pytest.fixture
def frozen_request(tmp_path):
    aid='GATK_20260914_010203_A1B2C3'
    root=tmp_path/'requests'
    workdir=tmp_path/'runs'/aid/'attempt-1'
    bundle=workdir/'cce'
    bundle.mkdir(parents=True)
    binding={'analysis_id':aid,'attempt':1,'run_id':aid+'-a1','namespace':'test','master_job':'master'}
    raw=json.dumps(binding).encode()
    (workdir/'batch-binding.json').write_bytes(raw)
    (bundle/'BATCH_RUNTIME.yaml').write_text(json.dumps({'identity':{'project':'synthetic','batch':'B1','run_id':aid+'-a1'},
        'kubernetes':{'namespace':'test','master_job':'master'}}))
    (bundle/'Step7_cleanup_sfs.sh').write_text('# synthetic')
    for name in ('cleanup-job.yaml','cce_batch_runtime.py'):
        (bundle/name).write_text('# synthetic')
    receipt={'analysis_id':aid,'attempt':1,'stage':'step6_materialize','status':'success','generation':1,'execution_id':'step6-g1'}
    receipt_path=root/aid/'attempt-1'/'step6_materialize.request.status.json'
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(receipt))
    prepare=receipt_path.parent/'prepare.request.json'
    prepare.write_text(json.dumps({'analysis_id':aid,'attempt':1,'project_name':'synthetic','batch':'B1'}))
    value={'analysis_id':aid,'attempt':1,'maintenance_action_id':'gatk-step7-123456abcdef',
        'runtime_workdir':str(workdir),'cce_bundle':str(bundle),'binding_sha256':hashlib.sha256(raw).hexdigest(),
        'predecessor_execution_id':'step6-g1','predecessor_generation':1,'predecessor_receipt_hash':digest(receipt)}
    value['approved_project']='synthetic'
    value['approved_batch']='B1'
    value['prepare_sha256']=hashlib.sha256(prepare.read_bytes()).hexdigest()
    value['bundle_hashes']={name:hashlib.sha256((bundle/name).read_bytes()).hexdigest()
        for name in ('BATCH_RUNTIME.yaml','cleanup-job.yaml','Step7_cleanup_sfs.sh','cce_batch_runtime.py')}
    value['request_hash']=digest(value)
    return value, root


def test_frozen_confirmation_without_unverified_override(frozen_request):
    value, root=frozen_request
    command=gate.cleanup_command(value,root)
    assert command[-2:] == ['--confirm','DELETE-SFS:synthetic/B1/'+value['analysis_id']+'-a1']
    assert not any('unverified' in part for part in command)


@pytest.mark.parametrize('field,value', [('attempt',2),('binding_sha256','a'*64),
    ('predecessor_generation',2),('runtime_workdir','/'),('maintenance_action_id','forged')])
def test_rejects_changed_target_or_receipt(frozen_request,field,value):
    payload,root=frozen_request
    payload[field]=value
    payload.pop('request_hash')
    payload['request_hash']=digest(payload)
    with pytest.raises((ValueError,FileNotFoundError)):
        gate.cleanup_command(payload,root)


def test_concurrent_worker_does_not_overwrite_owner(frozen_request):
    import fcntl
    payload,root=frozen_request
    directory=root/payload['analysis_id']/'attempt-1'
    with (directory/'.maintenance.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        states=[]
        with pytest.raises(RuntimeError,match='lock is busy'):
            gate.execute_cleanup(payload,root,lambda *args:states.append(args))
        assert states == []


def test_unapproved_manifest_is_rejected_before_query(frozen_request):
    payload,_=frozen_request
    bundle=Path(payload['cce_bundle'])
    (bundle/'cleanup-job.yaml').write_text(json.dumps({'metadata':{'name':'foreign'}}))
    with pytest.raises(ValueError,match='manifest identity'):
        gate.verify_live_cleanup_target(payload)


@pytest.mark.parametrize('name',['BATCH_RUNTIME.yaml','cleanup-job.yaml','Step7_cleanup_sfs.sh','cce_batch_runtime.py'])
def test_changed_approved_bundle_is_rejected(frozen_request,name):
    payload,root=frozen_request
    path=Path(payload['cce_bundle'])/name
    path.write_text(path.read_text()+'\n# changed')
    with pytest.raises(ValueError,match='frozen cleanup bundle changed'):
        gate.cleanup_command(payload,root)


def test_symlink_lock_rejected_without_writing_target(frozen_request,monkeypatch):
    payload,root=frozen_request
    target=root/'unrelated'
    target.write_text('preserve')
    lock=root/payload['analysis_id']/'attempt-1'/'.maintenance.lock'
    lock.symlink_to(target)
    monkeypatch.setattr(gate,'cleanup_command',lambda *args:['/usr/bin/true'])
    monkeypatch.setattr(gate,'verify_live_cleanup_target',lambda *args:None)
    with pytest.raises((ValueError,OSError)):
        gate.execute_cleanup(payload,root,lambda *args:None)
    assert target.read_text()=='preserve'
