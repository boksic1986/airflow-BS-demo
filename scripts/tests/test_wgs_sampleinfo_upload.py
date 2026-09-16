import hashlib
from pathlib import Path

import pytest
from test_wgs_runtime_gate import load_gate


def test_import_uses_uploaded_bytes_without_sampleinfo_subprocess(tmp_path, monkeypatch):
    gate = load_gate()
    original_build = gate.build_prepare_command
    monkeypatch.setattr(gate, 'REQUEST_ROOT', tmp_path / 'requests')
    monkeypatch.setattr(gate, 'RUNTIME_RUN_ROOT', str(tmp_path))
    monkeypatch.setattr(gate, 'WGS_REPO_ROOT', tmp_path / 'owner-repository')
    monkeypatch.setattr(gate, 'validate_release_repository', lambda payload: None)
    monkeypatch.setattr(gate, 'validate_prepare_config', lambda payload: None)
    monkeypatch.setattr(gate, 'build_prepare_command', lambda payload: ['must-not-run'])
    monkeypatch.setattr(gate.subprocess, 'run', lambda *a, **kw: pytest.fail('must not regenerate sampleinfo'))
    text = '上机批次\t分析批次\t样本编号\t数据编号\n20260910A\t20260910A_CCE_TEST\tSYNTH1\tDATA1\n'
    sha = hashlib.sha256(text.encode()).hexdigest()
    source = gate.REQUEST_ROOT / 'WGS_20260916_010203_A1B2C3' / 'sampleinfo-upload.tsv'
    source.parent.mkdir(parents=True)
    source.write_text(text)
    output = tmp_path / 'WGS_Clinical'
    output.mkdir()
    payload = dict(analysis_id=source.parent.name, attempt=1, stage='prepare_sampleinfo',
                   generation=1, execution_id='wse_synthetic', request_hash='a'*64,
                   pipeline_release_id='wgs-4.2.1-34bfcbf', wgs_version='V4.2.1',
                   control_workdir=str(tmp_path / 'runtime'), batch_no='WGS_20260910A_CCE_TEST_T7Hg38V4.2.1',
                   analysis_project_root=str(output), project_name=output.name,
                   sampleinfo_upload={'sha256':sha, 'row_count':1})
    destination = output / 'sampleinfo' / (payload['batch_no'] + '.sampleinfo.txt')
    with monkeypatch.context() as patch:
        def interrupted(_fd):
            raise OSError('synthetic interrupted write')
        patch.setattr(gate.os, 'fsync', interrupted)
        with pytest.raises(OSError, match='interrupted'):
            gate._run_prepare_sampleinfo(payload)
        assert not destination.exists()
    gate._run_prepare_sampleinfo(payload)
    gate._run_prepare_sampleinfo(payload)
    destination = output / 'sampleinfo' / (payload['batch_no'] + '.sampleinfo.txt')
    assert destination.read_text() == text
    assert payload['prepare_handoff_receipt']['safe_candidates'][0]['sample_id'] == 'SYNTH1'
    assert not (output / 'prepare').exists()  # importing must not touch pending
    payload.update(stage='prepare_analysis', sequencing_batch='20260910A', analysis_batch='20260910A_CCE_TEST',
                   fq_path='/fastq', fastq_root='/fastq', platform='T7')
    request = gate._prepare_handoff_request(payload)
    assert sha in request.read_text()
    assert destination.read_text() == text
    destination.write_text(text.replace('DATA1', 'DATA2'))
    with pytest.raises(RuntimeError, match='Imported sampleinfo changed'):
        gate._prepare_handoff_request(payload)
    destination.write_text(text)
    command = original_build(payload)
    assert command[2] == 'analysis'
    assert command[command.index('--sampleinfo') + 1] == str(destination)
    assert command[command.index('--outpath') + 1] == str(output)
    assert '--forceall' not in command
    payload['stage'] = 'prepare_sampleinfo'
    batch_root = output / payload['batch_no']
    batch_root.mkdir()
    with pytest.raises(RuntimeError, match='already exists'):
        gate._run_prepare_sampleinfo(payload)
    batch_root.rmdir()
    source.write_text(text.replace('DATA1', 'DATA2'))
    with pytest.raises(RuntimeError, match='changed'):
        gate._run_prepare_sampleinfo(payload)
