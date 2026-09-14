import hashlib
import json
from pathlib import Path
from test_gatk_runtime_gate import load_gate
import pytest


def setup(tmp_path, monkeypatch):
    gate = load_gate()
    payload = dict(analysis_id='GATK_20260908_120000_A1B2C3', attempt=1,
        stage='step5_download', generation=2, execution_id='download-g2',
        request_hash='b'*64, orchestration_contract_version=2)
    monkeypatch.setenv('GATK_TRANSFER_SPOOL_ROOT', str(tmp_path/'spool'))
    bundle=tmp_path/'bundle'; delivery=bundle/'cloud_delivery'; delivery.mkdir(parents=True)
    monkeypatch.setattr(gate, '_bundle', lambda value: bundle)
    request=tmp_path/'request.json'; request.write_text(json.dumps(payload))
    monkeypatch.setattr(gate, '_request_path', lambda *args: request)
    (bundle/'BATCH_RUNTIME.yaml').write_text('identity:\n  project: P\n  batch: B\n  run_id: '+payload['analysis_id']+'-a1\n')
    manifest='schema_version\tartifact_type\trelative_path\tsize_bytes\tmd5\tstatus\n1\tgatk_results\tresults/B.tar.zst\t100\t'+'a'*32+'\tsource_verified\n'
    (delivery/'payload-manifest.tsv').write_text(manifest)
    (delivery/'READY').write_text('project=P\nbatch=B\nrun_id='+payload['analysis_id']+'-a1\nstatus=READY\nmanifest_md5='+hashlib.md5(manifest.encode()).hexdigest()+'\n')
    return gate,payload,delivery,request


def test_download_plan_requires_ready_identity_and_manifest_hash(tmp_path,monkeypatch):
    gate,payload,delivery,request=setup(tmp_path,monkeypatch)
    plan=gate._create_step5_transfer_plan(payload)
    assert plan['entries'][0]['size_bytes']==100
    (delivery/'payload-manifest.tsv').write_text('invalid')
    assert gate._create_step5_transfer_plan(payload) is None


def test_download_progress_publishes_current_generation_without_early_success(tmp_path,monkeypatch):
    gate,payload,delivery,request=setup(tmp_path,monkeypatch)
    plan=gate._create_step5_transfer_plan(payload)
    root=gate._transfer_progress_root(payload)
    row=dict(schema_version='wgs-runtime.transfer-progress.v1',analysis_id=payload['analysis_id'],
        attempt=1,stage='step5_download',file_key=hashlib.sha256(b'results/B.tar.zst').hexdigest(),
        state='success',bytes_done=100,heartbeat_at='2026-09-14T01:00:00+00:00')
    (root/'part.json').write_text(json.dumps(row))
    progress=gate._aggregate_transfer_progress(payload,plan)
    assert progress['bytes_total']==100 and progress['bytes_done']==100
    assert progress['state']=='running'  # individual cp success is NOT stage verification
    assert progress['transfer_id'].endswith('-result')
    assert progress['generation']==2
    assert (root.parent/'progress.json').exists()
    row['request_hash']='c'*64
    (root/'part.json').write_text(json.dumps(row))
    assert gate._aggregate_transfer_progress(payload,plan)['bytes_done']==0
    # Old flat raw files are outside this generation and must not count.
    row.pop('request_hash'); (root.parent/'old.json').write_text(json.dumps(row))
    assert gate._aggregate_transfer_progress(payload,plan)['bytes_done']==0


def test_download_completion_requires_receipt_and_unchanged_verified_files(tmp_path, monkeypatch):
    gate,payload,delivery,request=setup(tmp_path,monkeypatch)
    plan=gate._create_step5_transfer_plan(payload)
    with pytest.raises(FileNotFoundError):
        gate._finalize_step5_transfer_progress(payload,plan)
    receipt=gate._write_status(request,payload,'success','verified download')
    target=delivery/'results/B.tar.zst'; target.parent.mkdir(); target.write_bytes(b'x'*100)
    stat=target.stat()
    identity=plan['delivery_identity']
    ledger=dict(identity,manifest_md5=plan['manifest_md5'],files=[dict(plan['entries'][0],
        st_dev=stat.st_dev,st_ino=stat.st_ino,st_mtime_ns=stat.st_mtime_ns)])
    (delivery/'DOWNLOAD_VERIFIED.json').write_text(json.dumps(ledger))
    (delivery/'DOWNLOAD_VERIFIED').write_text('\n'.join(f'{k}={v}' for k,v in
        dict(identity,manifest_md5=plan['manifest_md5'],file_count=1,total_bytes=100,status='PASS').items()))
    progress=gate._finalize_step5_transfer_progress(payload,plan)
    assert progress['state']=='success' and progress['bytes_done']==100
    assert progress['completed_at']==receipt['updated_at']
    assert progress['source']=='verified-download-receipt'
    target.write_bytes(b'x'*99)
    with pytest.raises(ValueError, match='changed since'):
        gate._finalize_step5_transfer_progress(payload,plan)


def test_download_old_receipt_cannot_complete_new_generation(tmp_path,monkeypatch):
    gate,payload,delivery,request=setup(tmp_path,monkeypatch)
    plan=gate._create_step5_transfer_plan(payload)
    gate._write_status(request,dict(payload,generation=1),'success','old execution')
    with pytest.raises(ValueError,match='matching successful'):
        gate._finalize_step5_transfer_progress(payload,plan)


def test_download_waits_for_manifest_without_interrupting_copy(tmp_path,monkeypatch):
    gate,payload,delivery,request=setup(tmp_path,monkeypatch)
    plan=gate._create_step5_transfer_plan(payload)
    observations=iter([None, plan])
    monkeypatch.setattr(gate, '_create_step5_transfer_plan', lambda value: next(observations))
    monkeypatch.setattr(gate, '_step', lambda *args: ['frozen-step5'])
    monkeypatch.setattr(gate.time, 'sleep', lambda _: None)
    class Process:
        returncode=0
        args=['frozen-step5']
        polls=0
        def poll(self):
            self.polls+=1
            return None if self.polls==1 else 0
    launched=[]
    def launch(args,env):
        launched.append(args)
        replacement=delivery/'READY.new'
        replacement.write_text((delivery/'READY').read_text())
        replacement.replace(delivery/'READY')
        return Process()
    monkeypatch.setattr(gate.subprocess, 'Popen', launch)
    gate._run_step5_with_progress(payload,{})
    assert launched==[['frozen-step5']]
    progress=json.loads((gate._transfer_stage_root(payload)/'progress.json').read_text())
    assert progress['state']=='running' and progress['bytes_total']==100
