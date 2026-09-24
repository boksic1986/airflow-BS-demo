"""Restricted gates must not execute old frozen code after paired activation."""
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest


@pytest.fixture
def paired(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    import cce_paired_runtime as paired
    source=tmp_path/'cce_batch_runtime.py'
    source.write_text('COMPATIBLE = True\n')
    guard=tmp_path/'cce_writer_guard.py'; guard.write_text('# synthetic guard\n')
    gate=tmp_path/'platform.py';gate.write_text('# synthetic platform\n')
    def pin(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    policy=tmp_path/'writers.json'
    document={'schema_version':2,'namespace':'synthetic',
        'writers':{'cli':pin(source),'platform':pin(gate)},'runtime_guard':pin(guard),
        'operator_python':sys.executable}
    policy.write_text(json.dumps(document)); policy.chmod(0o600)
    monkeypatch.setattr(paired,'POLICY_PATH',policy)
    monkeypatch.setattr(paired,'TRUST_ROOT',tmp_path)
    monkeypatch.setattr(paired,'TRUSTED_UID',os.getuid())
    monkeypatch.setattr(paired,'PLATFORM_SOURCE',gate)
    # Executable provenance is substituted only; policy and source hash checks run.
    monkeypatch.setattr(paired,'_operator_python',lambda value:value)
    return paired,source,guard,policy


@pytest.mark.parametrize('adapter',['wgs','gatk'])
def test_real_gate_selects_compatible_source_preserving_bundle(paired,tmp_path,monkeypatch,adapter):
    import importlib
    module,source,guard,policy=paired
    gate=importlib.import_module(adapter+'_runtime_gate')
    bundle=tmp_path/'frozen';bundle.mkdir()
    if adapter=='wgs':
        monkeypatch.setattr(gate,'_load_binding',lambda payload:{'cce_bundle':str(bundle)})
        command=gate._step_command({},'step3_monitor','--output','json')
        assert command[-2:]==['--output','json']
    else:
        monkeypatch.setattr(gate,'_bundle',lambda payload:bundle)
        command=gate._step({},'step3_monitor')
    assert command[:5]==[sys.executable,str(source),'step3-status','--bundle',str(bundle)]
    assert list(bundle.iterdir())==[]


@pytest.mark.parametrize('adapter',['wgs','gatk'])
def test_resume_imports_pinned_external_runtime(paired,tmp_path,adapter):
    import importlib
    gate=importlib.import_module(adapter+'_resume')
    assert gate._runtime(tmp_path).COMPATIBLE is True


@pytest.mark.parametrize('fault',['guard_hash','policy_mode','source_symlink'])
def test_bad_activation_never_falls_back_to_frozen_runtime(paired,fault):
    module,source,guard,policy=paired
    if fault=='guard_hash':guard.write_text('changed\n')
    elif fault=='policy_mode':policy.chmod(0o666)
    else:
        other=source.with_name('other.py');source.rename(other);source.symlink_to(other)
    with pytest.raises(RuntimeError):module.selected_runtime()


@pytest.mark.parametrize('adapter',['wgs','gatk'])
def test_unactivated_entries_preserve_old_bundle(paired,tmp_path,monkeypatch,adapter):
    import importlib
    module,source,guard,policy=paired
    monkeypatch.setattr(module,'POLICY_PATH',tmp_path/'absent-policy.json')
    bundle=tmp_path/'old';bundle.mkdir()
    (bundle/'Step3_status.sh').write_text('# frozen step\n')
    (bundle/'cce_batch_runtime.py').write_text('LEGACY = True\n')
    gate=importlib.import_module(adapter+'_runtime_gate')
    if adapter=='wgs':
        monkeypatch.setattr(gate,'_load_binding',lambda payload:{'cce_bundle':str(bundle)})
        command=gate._step_command({},'step3_monitor')
    else:
        monkeypatch.setattr(gate,'_bundle',lambda payload:bundle)
        command=gate._step({},'step3_monitor')
    assert command==['bash',str(bundle/'Step3_status.sh')]
    assert importlib.import_module(adapter+'_resume')._runtime(bundle).LEGACY is True


def test_gatk_custom_materialization_cannot_bypass_paired_guard(paired,tmp_path,monkeypatch):
    import gatk_runtime_gate as gate
    from types import SimpleNamespace
    module,*_=paired
    class Denied:
        def validate_call(self,arguments):assert arguments['bundle']==tmp_path
        def enter(self,stage):
            assert stage==6
            raise RuntimeError('paired writer denied')
    selected=SimpleNamespace(_load=lambda *a:({}, {}, ()),
        writer_for_bundle=lambda *a:Denied())
    monkeypatch.setattr(module,'load_runtime',lambda:selected)
    monkeypatch.setattr(gate,'_bundle',lambda payload:tmp_path)
    with pytest.raises(RuntimeError,match='paired writer denied'):
        gate._materialize({})


@pytest.mark.parametrize('adapter',['wgs','gatk'])
def test_activated_resume_cannot_enter_legacy_unprotected_path(paired,tmp_path,monkeypatch,adapter):
    import importlib
    gate=importlib.import_module(adapter+'_resume')
    if adapter=='wgs':
        with pytest.raises(RuntimeError,match='verified recovery capability'):
            gate.resume_master(payload={'resume_action_id':'action-1'},binding={'cce_bundle':str(tmp_path)})
    else:
        analysis='GATK_20260924_120000_A1B2C3'
        root=tmp_path/'requests';(root/analysis/'attempt-1').mkdir(parents=True)
        bundle=tmp_path/'runs'/analysis/'attempt-1'/'cce';bundle.mkdir(parents=True)
        binding=bundle.parent/'batch-binding.json'
        binding.write_text(json.dumps({'schema_version':'gatk-runtime.batch-binding.v1',
            'analysis_id':analysis,'attempt':1,'run_id':analysis+'-a1','cce_bundle':str(bundle)}))
        contract=bundle/'BATCH_RUNTIME.yaml';contract.write_text('{}')
        (bundle/'master-job.yaml').write_text('{}')
        monkeypatch.setenv('GATK_RUNTIME_REQUEST_ROOT',str(root))
        digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        with pytest.raises(RuntimeError,match='verified recovery capability'):
            gate.resume(analysis_id=analysis,attempt=1,expected_job_uid='old-uid',
                expected_binding_sha256=digest(binding),expected_contract_sha256=digest(contract))
