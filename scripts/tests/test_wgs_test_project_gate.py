import hashlib
import json
from pathlib import Path
import pytest
from test_wgs_runtime_gate import load_gate


def test_test_project_gate_rejects_production_and_scope_expansion(tmp_path, monkeypatch):
    gate=load_gate()
    assert hasattr(gate,'_validate_test_project'), 'test-project node gate is missing'
    with pytest.raises(RuntimeError,match='disabled'):
        gate._validate_test_project({'test_project':{}}, create=False)
    monkeypatch.setenv('WGS_TEST_PROJECT_ENABLED','true')
    monkeypatch.setenv('PLATFORM_ENVIRONMENT','production')
    with pytest.raises(RuntimeError,match='disabled'):
        gate._validate_test_project({'test_project':{}},create=False)


def test_exact_selection_fence_rejects_added_or_missing_samples():
    gate=load_gate()
    assert hasattr(gate,'_test_selection_fence'), 'exact selection fence is missing'
    payload={'test_project':{'samples':['SYNTH1']}}
    gate._test_selection_fence(payload, {'selected':[{'sample_id':'SYNTH1'}],'pending':[],'excluded':[]})
    for rows in [[],[{'sample_id':'SYNTH1'},{'sample_id':'EXTRA'}]]:
        with pytest.raises(RuntimeError,match='frozen'):
            gate._test_selection_fence(payload,{'selected':rows,'pending':[],'excluded':[]})


def test_node_copies_only_frozen_table_and_publishes_exact_receipt(tmp_path,monkeypatch):
    gate=load_gate();root=tmp_path/'test';root.mkdir();source=root/'source';source.mkdir();(source/'raw').mkdir()
    (source/'sampleinfo.tsv').write_text('样本编号\t数据编号\t分析批次\t上机批次\nSYNTH1\tDATA1\t20260912A\t20260912A\n')
    (source/'config.yaml').write_text('algo: DNAscope\n')
    (source/'results.vcf').write_text('must not be copied')
    files=[]
    for read in ['R1','R2']:
        path=source/'raw'/f'DATA1.{read}.fq.gz';path.write_bytes(b'synthetic');stat=path.stat()
        files.append({'data_id':'DATA1','sample_id':'SYNTH1','read':read,'path':str(path),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns})
    monkeypatch.setattr(gate,'TEST_PROJECT_ROOT',root)
    monkeypatch.setattr(gate,'RUNTIME_RUN_ROOT',str(tmp_path/'WGS_test'/'runtime'))
    monkeypatch.setenv('PLATFORM_ENVIRONMENT','test');monkeypatch.setenv('WGS_TEST_PROJECT_ENABLED','true')
    target=root/'independent'; namespace='WGS_TEST_'+('A'*16); output=target/namespace
    analysis_batch='20260912A'
    frozen=(source/'sampleinfo.tsv').read_bytes().replace(b'20260912A\t',analysis_batch.encode()+b'\t')
    data={'source':str(source),'target_root':str(target),'project_namespace':namespace,'batch':'20260912A','analysis_batch':analysis_batch,'frozen_sampleinfo_sha256':hashlib.sha256(frozen).hexdigest(),'output_root':str(output),'fingerprint':'a'*64,'samples':['SYNTH1'],'fastq':files,'sampleinfo_sha256':gate._sha256_file(source/'sampleinfo.tsv'),'config_sha256':gate._sha256_file(source/'config.yaml')}
    payload={'analysis_id':'WGS_20260912_000000_ABCDEF','attempt':1,'stage':'prepare_sampleinfo','generation':1,'execution_id':'synthetic-1','request_hash':'b'*64,'pipeline_release_id':'wgs-4.2.1-cc9bde3','wgs_version':'V4.2.1','control_workdir':str(tmp_path/'WGS_test'/'runtime'/'runs'/'SYNTHETIC'/'attempt-1'),'analysis_project_root':str(output),'expected_batch_root':str(output/'WGS_20260912A_T7Hg38V4.2.1'),'batch_no':'WGS_20260912A_T7Hg38V4.2.1','test_project':data}
    payload['analysis_batch']=analysis_batch
    payload['batch_no']=f'WGS_{analysis_batch}_T7Hg38V4.2.1'
    payload['expected_batch_root']=str(output/payload['batch_no'])
    gate._prepare_test_sampleinfo(payload)
    assert payload['prepare_handoff_receipt']['safe_candidates'][0]['sample_id']=='SYNTH1'
    assert not (output/'raw').exists()
    assert not (output/'results.vcf').exists()
    assert not (output/'prepare').exists()
    assert payload['prepare_handoff_receipt']['safe_candidates'][0]['analysis_batch']==analysis_batch
    assert (source/'sampleinfo.tsv').read_bytes()==frozen
    gate._prepare_test_sampleinfo(payload)
    (source/'config.yaml').write_text('algo: changed')
    with pytest.raises(RuntimeError,match='changed'):gate._prepare_test_sampleinfo(payload)
