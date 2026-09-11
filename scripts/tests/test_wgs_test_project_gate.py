import hashlib
import json
from pathlib import Path
import pytest
from test_wgs_runtime_gate import load_gate


def freeze_fixture(gate,payload,tmp_path,monkeypatch):
    repo=tmp_path/'owner';(repo/'prepare').mkdir(parents=True);(repo/'cfg').mkdir()
    config=f'project_root: ..\nresource_root: {repo}\nconfig_template: ../cfg/config.template.yaml\ndefaults:\n  platform: T7\n'
    template='version: V4.2.1\nalgo: DNAscope\nuse_reference: all\ngenome:\n  fasta: /projectDir/genome.fa\n'
    (repo/'prepare/config.yaml').write_text(config);(repo/'cfg/config.template.yaml').write_text(template)
    monkeypatch.setattr(gate,'WGS_REPO_ROOT',repo)
    payload['wgs_source_commit']='synthetic-audited'
    payload['test_project']['effective_config']={'source_commit':'synthetic-audited','prepare_sha256':hashlib.sha256(config.encode()).hexdigest(),'template_sha256':hashlib.sha256(template.encode()).hexdigest()}
    return repo


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
    freeze_fixture(gate,payload,tmp_path,monkeypatch)
    gate._prepare_test_sampleinfo(payload)
    assert payload['prepare_handoff_receipt']['safe_candidates'][0]['sample_id']=='SYNTH1'
    assert not (output/'raw').exists()
    assert not (output/'results.vcf').exists()
    assert not (output/'prepare').exists()
    assert payload['prepare_handoff_receipt']['safe_candidates'][0]['analysis_batch']==analysis_batch
    assert (source/'sampleinfo.tsv').read_bytes()==frozen
    gate._prepare_test_sampleinfo(payload)
    # Every writable descendant must be real, not just the output root.
    outside=root/'outside';outside.mkdir()
    (output/'prepare').symlink_to(outside,target_is_directory=True)
    with pytest.raises(RuntimeError,match='symlink|unsafe'):
        gate._prepare_test_sampleinfo(payload)
    assert list(outside.iterdir())==[]
    (output/'prepare').unlink()
    sampleinfo=output/'sampleinfo';sampleinfo.rename(output/'saved-sampleinfo')
    sampleinfo.symlink_to(outside,target_is_directory=True)
    with pytest.raises(RuntimeError,match='symlink|unsafe'):
        gate._prepare_test_sampleinfo(payload)
    assert list(outside.iterdir())==[]
    sampleinfo.unlink();(output/'saved-sampleinfo').rename(sampleinfo)
    (source/'config.yaml').write_text('algo: changed')
    with pytest.raises(RuntimeError,match='changed'):gate._prepare_test_sampleinfo(payload)


def test_private_namespace_sticky_parent_concurrency_recovery_and_replacement(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    gate=load_gate();root=tmp_path/'shared';root.mkdir();root.chmod(0o2770)
    target=root/'project';output=target/'WGS_TEST_AAAAAAAAAAAAAAAA'
    payload={'analysis_id':'synthetic','test_project':{'target_root':str(target),'output_root':str(output),'fingerprint':'frozen'}}
    with pytest.raises(RuntimeError,match='sticky'):
        gate._test_secure_output(payload,create=True)
    root.chmod(0o3770)
    (root/'.wgs-test-orphan').mkdir(mode=0o700)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _:gate._test_secure_output(payload,create=True),range(4)))
    original=output.stat().st_ino
    gate._test_secure_output(payload,create=True)
    assert output.stat().st_ino==original
    assert output.stat().st_mode & 0o077==0
    assert len(list(target.iterdir()))==2
    # Copying marker text into a replacement inode does not confer ownership.
    record=(output/'.airflow-test-project.json').read_bytes()
    output.rename(target/'retained');output.mkdir(mode=0o700)
    (output/'.airflow-test-project.json').write_bytes(record)
    with pytest.raises(RuntimeError,match='inode'):
        gate._test_secure_output(payload,create=False)


def test_parent_replacement_before_publication_never_writes_external_files(tmp_path,monkeypatch):
    gate=load_gate();parent=tmp_path/'parent';parent.mkdir();moved=tmp_path/'moved'
    payload={'analysis_id':'synthetic','test_project':{'target_root':str(parent/'target'),'output_root':str(parent/'target'/'WGS_TEST_AAAAAAAAAAAAAAAA'),'fingerprint':'frozen'}}
    original=gate.os.mkdir;replaced=False
    def replace_after_mkdir(path,*args,**kwargs):
        nonlocal replaced
        result=original(path,*args,**kwargs)
        if str(path)=='target' and not replaced:
            replaced=True;parent.rename(moved);parent.mkdir()
        return result
    monkeypatch.setattr(gate.os,'mkdir',replace_after_mkdir)
    with pytest.raises(RuntimeError,match='replaced'):
        gate._test_secure_output(payload,create=True)
    assert not list(parent.iterdir())
    assert not list(moved.rglob('*.json'))


def test_unidentified_target_after_interrupted_mkdir_is_not_adopted(tmp_path):
    gate=load_gate();target=tmp_path/'target';target.mkdir(mode=0o700)
    payload={'analysis_id':'synthetic','test_project':{'target_root':str(target),'output_root':str(target/'WGS_TEST_AAAAAAAAAAAAAAAA'),'fingerprint':'frozen'}}
    with pytest.raises(RuntimeError,match='audit recovery'):
        gate._test_secure_output(payload,create=True)
    assert list(target.iterdir())==[]


def test_effective_defaults_reject_mutation_before_snapshot_and_use_frozen_bytes_after(tmp_path,monkeypatch):
    gate=load_gate();target=tmp_path/'project';output=target/'WGS_TEST_AAAAAAAAAAAAAAAA'
    payload={'analysis_id':'synthetic','test_project':{'target_root':str(target),'output_root':str(output),'fingerprint':'frozen'}}
    gate._test_secure_output(payload,create=True)
    repo=freeze_fixture(gate,payload,tmp_path,monkeypatch)
    original=(repo/'prepare/config.yaml').read_bytes()
    (repo/'prepare/config.yaml').write_text('changed: true\n')
    with pytest.raises(RuntimeError,match='configuration changed'):gate._test_effective_prepare(payload)
    (repo/'prepare/config.yaml').write_bytes(original)
    frozen,template,_=gate._test_effective_prepare(payload)
    first=frozen.read_bytes();first_template=template.read_bytes()
    (repo/'prepare/config.yaml').write_text('changed: true\n')
    (repo/'cfg/config.template.yaml').write_text('algo: mutated\n')
    assert gate._test_effective_prepare(payload)[0].read_bytes()==first
    assert template.read_bytes()==first_template
    payload.update(algo='Haplotyper',use_reference='no',batch_no='B',expected_batch_root=str(output/'B'))
    prepared={'version':'V4.2.1','algo':'Haplotyper','use_reference':'no','batch':'B','fastqDir':str(output/'B/raw'),'fastqPath':str(output/'B/raw'),'sample_info':str(output/'B/sampleinfo.tsv'),'src':{},'biosoft':{},'genome':{'fasta':str(repo/'genome.fa')},'bed':{},'database':{},'cnv_native':{}}
    prepared.update(new_sample_info=str(output/'B/sampleinfo.tsv'),workDir=str(output/'B'),execution={'executor':'cce'},workflow={'schema_version':3,'snakefile':'WGS_pipe.smk','target':'all'},delivery={'materialized_marker':'cce/cloud_delivery/MATERIALIZED'})
    gate._test_validate_prepared_config(payload,prepared)
    prepared['sample']=['foreign']
    with pytest.raises(RuntimeError,match='changed'):
        gate._test_validate_prepared_config(payload,prepared)
    prepared.pop('sample')
    prepared['genome']['fasta']='/foreign/reference.fa'
    with pytest.raises(RuntimeError,match='effective release'):
        gate._test_validate_prepared_config(payload,prepared)
