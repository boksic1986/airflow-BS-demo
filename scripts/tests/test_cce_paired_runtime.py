"""Restricted gates must not execute old frozen code after paired activation."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace

import pytest


def test_deployment_trust_rejects_unapproved_owner_even_when_currently_read_only(monkeypatch):
    from scripts import cce_paired_runtime as module
    monkeypatch.setattr(module,'_acl_write_principals',lambda path:(set(),set()))
    info=SimpleNamespace(st_mode=stat.S_IFREG|0o440,st_uid=os.getuid()+100000,
        st_gid=os.getgid())
    with pytest.raises(RuntimeError,match='unapproved writer'):
        module._validate_writers('/synthetic',info,{os.getuid()},{os.getgid()})


def test_interpreter_target_ancestry_cannot_be_writable(tmp_path):
    from scripts import cce_paired_runtime as module
    mutable=tmp_path/'mutable';mutable.mkdir();mutable.chmod(0o777)
    target=mutable/'python-real';target.write_text('synthetic');target.chmod(0o555)
    link=tmp_path/'python';link.symlink_to(target)
    trust={'path':str(link),'trust_root':str(tmp_path),
        'maintainer_uids':[os.getuid()],'maintainer_gids':[os.getgid()],
        'canonical_path':str(target.resolve())}
    with pytest.raises(RuntimeError,match='unapproved writer'):
        module._trusted_path(trust,True)


@pytest.fixture
def paired(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    import cce_paired_runtime as paired
    source=tmp_path/'cce_batch_runtime.py'
    source.write_text('COMPATIBLE = True\n')
    guard=tmp_path/'cce_writer_guard.py'; guard.write_text('# synthetic guard\n')
    gate=tmp_path/'platform.py';gate.write_text('# synthetic platform\n')
    python_target=tmp_path/'python-real';python_target.write_text('synthetic');python_target.chmod(0o755)
    python_link=tmp_path/'python';python_link.symlink_to(python_target)
    def pin(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    policy=tmp_path/'writers.json'
    document={'schema_version':2,'namespace':'synthetic',
        'writers':{'cli':pin(source),'platform':pin(gate)},'runtime_guard':pin(guard),
        'operator_python':str(python_link)}
    policy.write_text(json.dumps(document)); policy.chmod(0o600)
    entry=lambda path:{'path':str(path),'trust_root':str(tmp_path),
        'maintainer_uids':[os.getuid()],'maintainer_gids':[os.getgid()]}
    bootstrap=tmp_path/'cce-paired-deployment-v1.json'
    bootstrap.write_text(json.dumps({'schema_version':1,'policy':entry(policy),
        'writers':{'cli':entry(source),'platform':entry(gate)},'runtime_guard':entry(guard),
        'operator_python':{**entry(python_link),'canonical_path':str(python_target.resolve())}}))
    bootstrap.chmod(0o600)
    monkeypatch.setattr(paired,'DEPLOYMENT_TRUST_ROOT',tmp_path,raising=False)
    monkeypatch.setattr(paired,'DEPLOYMENT_TRUST_PATH',bootstrap,raising=False)
    monkeypatch.setattr(paired,'PLATFORM_SOURCE',gate)
    return paired,source,guard,policy,bootstrap,python_link


@pytest.mark.parametrize('adapter',['wgs','gatk'])
def test_real_gate_selects_compatible_source_preserving_bundle(paired,tmp_path,monkeypatch,adapter):
    import importlib
    module,source,guard,policy,_,python_link=paired
    gate=importlib.import_module(adapter+'_runtime_gate')
    bundle=tmp_path/'frozen';bundle.mkdir()
    if adapter=='wgs':
        monkeypatch.setattr(gate,'_load_binding',lambda payload:{'cce_bundle':str(bundle)})
        command=gate._step_command({},'step3_monitor','--output','json')
        assert command[-2:]==['--output','json']
    else:
        monkeypatch.setattr(gate,'_bundle',lambda payload:bundle)
        command=gate._step({},'step3_monitor')
    assert command[:5]==[str(python_link.resolve()),str(source),'step3-status','--bundle',str(bundle)]
    assert list(bundle.iterdir())==[]


@pytest.mark.parametrize('adapter',['wgs','gatk'])
def test_resume_imports_pinned_external_runtime(paired,tmp_path,adapter):
    import importlib
    gate=importlib.import_module(adapter+'_resume')
    assert gate._runtime(tmp_path).COMPATIBLE is True


@pytest.mark.parametrize('fault',['guard_hash','policy_mode','source_symlink'])
def test_bad_activation_never_falls_back_to_frozen_runtime(paired,fault):
    module,source,guard,policy,*_=paired
    if fault=='guard_hash':guard.write_text('changed\n')
    elif fault=='policy_mode':policy.chmod(0o666)
    else:
        other=source.with_name('other.py');source.rename(other);source.symlink_to(other)
    with pytest.raises(RuntimeError):module.selected_runtime()


@pytest.mark.parametrize('adapter',['wgs','gatk'])
def test_unactivated_entries_preserve_old_bundle(paired,tmp_path,monkeypatch,adapter):
    import importlib
    module,source,guard,policy,*_=paired
    monkeypatch.setattr(module,'DEPLOYMENT_TRUST_PATH',tmp_path/'absent-bootstrap.json',raising=False)
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
    module,*_=paired
    def denied(payload,*,binding,gate: object,pipeline,materialize):
        assert binding=={'cce_bundle':str(tmp_path)}
        assert pipeline=='gatk' and materialize is gate._materialize_to_approved_root
        raise RuntimeError('paired writer denied')
    monkeypatch.setattr(module,'downstream_registered',denied)
    monkeypatch.setattr(gate,'_load_binding',lambda payload:{'cce_bundle':str(tmp_path)})
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


def test_real_interpreter_symlink_is_validated_without_substitution(paired):
    module,source,_,_,_,python_link=paired
    assert module.selected_runtime()==(source,str(python_link.resolve()))


def test_policy_cannot_choose_a_path_outside_deployment_bootstrap(paired,tmp_path):
    module,source,guard,policy,*_=paired
    document=json.loads(policy.read_text())
    foreign=tmp_path/'foreign.py';foreign.write_text('foreign')
    document['writers']['cli']={'path':str(foreign),
        'sha256':hashlib.sha256(foreign.read_bytes()).hexdigest()}
    policy.write_text(json.dumps(document))
    with pytest.raises(RuntimeError,match='deployment trust'):
        module.selected_runtime()


def test_shared_platform_lock_survives_private_umask(paired,tmp_path):
    module,*_=paired
    lock=tmp_path/'shared.lock'
    previous=os.umask(0o077)
    try:
        with module._exclusive(lock):pass
    finally:
        os.umask(previous)
    assert lock.stat().st_mode & 0o777 == 0o660
