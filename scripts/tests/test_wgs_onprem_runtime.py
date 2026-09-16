import importlib.util
import json
import os
import pwd
from pathlib import Path

import pytest
import yaml

from test_wgs_native_prepare import setup_native, publish_native
from test_wgs_local_runtime_gate import gate as local_gate


def native_project(tmp_path, monkeypatch, mode, target, *, missing_exit=False):
    prepare_gate, data = setup_native(tmp_path, monkeypatch, mode)
    data["prepare_execution"]["target"] = target
    argv = prepare_gate.build_prepare_command(data)
    publish_native(prepare_gate, data, argv)
    batch = Path(data["expected_batch_root"])
    (batch / "raw").mkdir()
    # A synthetic controller records the native contract, without running WGS.
    script = '''#!/bin/bash
set -eu
mkdir -p log
printf '%s\\n' "$@" > log/argv.txt
printf 'run_mode\\tMODE\\nstarted_at\\t2026-09-15T10:00:00+08:00\\nfinished_at\\t2026-09-15T10:00:01+08:00\\n' > "log/step1.${WGS_ATTEMPT_ID}.metadata.tsv"
EXIT
'''.replace("MODE", mode).replace("EXIT", "" if missing_exit else 'echo 0 > "log/step1.${WGS_ATTEMPT_ID}.exitcode"')
    (batch / "Step1_run.sh").write_text(script)
    sample = str(batch / f"{data['batch_no']}.sampleinfo.txt")
    (batch / "config.yaml").write_text(yaml.safe_dump({
        "execution": {"executor": mode}, "algo": "Haplotyper",
        "sample_info": sample, "new_sample_info": sample,
    }))
    prepare_gate._write_prepare_binding(data)
    data.update(stage="local_analysis" if mode == "local" else "sge_analysis",
                orchestration_contract_version=2, execution_id="wse-native-1", generation=1)
    return batch, data


@pytest.mark.parametrize("mode,target", [("local", "node-96"), ("local", "node-97"), ("sge", "sge-default")])
def test_native_launch_preserves_project_and_profiles_and_uses_execution_identity(tmp_path, monkeypatch, mode, target):
    batch, data = native_project(tmp_path, monkeypatch, mode, target)
    originals = {name: (batch / name).read_bytes() for name in ("config.yaml", "Step1_run.sh")}
    request_root = tmp_path / "runtime/runner-requests"
    evidence = tmp_path / "evidence"
    if mode == "local":
        monkeypatch.setattr(local_gate, "REQUEST_ROOT", request_root)
        monkeypatch.setattr(local_gate, "ANALYSIS_ROOT", batch.parent)
        monkeypatch.setattr(local_gate, "EVIDENCE_ROOT", evidence)
        monkeypatch.setattr(local_gate, "LOCAL_TARGET", target, raising=False)
        result = local_gate.run_local_analysis(data)
    else:
        spec = importlib.util.spec_from_file_location("onprem_test", Path(__file__).parents[1] / "wgs_onprem_runtime.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.run_analysis(data, request_root=request_root, analysis_root=batch.parent,
                                     evidence_root=evidence, logger_root=tmp_path, target=target)
    assert result["native_exitcode"] == 0
    assert result["execution_target"] == target
    assert "wse-native-1" in result["native_execution_id"]
    assert originals == {name: (batch / name).read_bytes() for name in originals}
    assert not (batch / "config.cce-prepared.yaml").exists()
    args = (batch / "log/argv.txt").read_text().splitlines()
    assert "--cores" not in args and "--jobs" not in args and "--forceall" not in args
    assert "--logger" in args
    stream = args[args.index("--logger-airflow-demo-stream-id") + 1]
    assert "wse-native-1" in stream


def test_native_launch_requires_exact_terminal_exitcode(tmp_path, monkeypatch):
    batch, data = native_project(tmp_path, monkeypatch, "local", "node-97", missing_exit=True)
    monkeypatch.setattr(local_gate, "REQUEST_ROOT", tmp_path / "runtime/runner-requests")
    monkeypatch.setattr(local_gate, "ANALYSIS_ROOT", batch.parent)
    monkeypatch.setattr(local_gate, "EVIDENCE_ROOT", tmp_path / "evidence")
    with pytest.raises((ValueError, RuntimeError), match="exitcode|terminal"):
        local_gate.run_local_analysis(data)


def test_native_resume_snapshots_edited_config_and_actual_samples_without_overwriting_history(tmp_path, monkeypatch):
    batch, data = native_project(tmp_path, monkeypatch, "local", "node-97")
    monkeypatch.setattr(local_gate, "REQUEST_ROOT", tmp_path / "runtime/runner-requests")
    monkeypatch.setattr(local_gate, "ANALYSIS_ROOT", batch.parent)
    monkeypatch.setattr(local_gate, "EVIDENCE_ROOT", tmp_path / "evidence")
    monkeypatch.setenv("LOGNAME", "not-the-execution-user")
    config = yaml.safe_load((batch / "config.yaml").read_text())
    # Both edits happen AFTER prepare binding, including a new referenced file.
    edited = batch / "edited.sampleinfo.txt"
    edited.write_text("样本编号\t家系编号\nSYN_RENAMED\tFAMILY_EDITED\n")
    config.update(algo="DNAscope", sample_info=str(edited), new_sample_info=str(edited))
    (batch / "config.yaml").write_text(yaml.safe_dump(config))
    first = local_gate.run_local_analysis(data)
    first_path = Path(first["execution_snapshot"])
    first_bytes = {p.name: p.read_bytes() for p in first_path.iterdir()}
    assert yaml.safe_load((first_path / "config.yaml").read_text())["algo"] == "DNAscope"
    assert (first_path / "new_sample_info.tsv").read_text() == edited.read_text()
    assert first_path.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in first_path.iterdir())
    # A resume is a NEW execution under the same analysis, not a new project.
    config["algo"] = "Haplotyper"
    (batch / "config.yaml").write_text(yaml.safe_dump(config))
    edited.write_text("样本编号\t家系编号\nSYN_SECOND\tFAMILY_SECOND\n")
    resumed = {**data, "execution_id": "wse-native-2", "generation": 2}
    second = local_gate.run_local_analysis(resumed)
    second_path = Path(second["execution_snapshot"])
    assert first_path != second_path
    assert first_bytes == {p.name: p.read_bytes() for p in first_path.iterdir()}
    manifest = json.loads((second_path / "manifest.json").read_text())
    assert manifest["analysis_id"] == data["analysis_id"]
    assert manifest["execution_id"] == "wse-native-2"
    assert manifest["generation"] == 2
    assert manifest["execution_user"] == pwd.getpwuid(os.geteuid()).pw_name
    assert (second_path / "new_sample_info.tsv").read_text() == edited.read_text()
    # Replaying the same execution must not overwrite its input snapshot/start again.
    (batch / "log/argv.txt").unlink()
    with pytest.raises((ValueError, RuntimeError, FileExistsError)):
        local_gate.run_local_analysis(resumed)
    assert not (batch / "log/argv.txt").exists()


@pytest.mark.parametrize("fault", ["mode", "missing_samples", "entry"])
def test_native_edit_does_not_bypass_target_input_or_entry_checks(tmp_path, monkeypatch, fault):
    batch, data = native_project(tmp_path, monkeypatch, "local", "node-97")
    monkeypatch.setattr(local_gate, "REQUEST_ROOT", tmp_path / "runtime/runner-requests")
    monkeypatch.setattr(local_gate, "ANALYSIS_ROOT", batch.parent)
    monkeypatch.setattr(local_gate, "EVIDENCE_ROOT", tmp_path / "evidence")
    config = yaml.safe_load((batch / "config.yaml").read_text())
    if fault == "mode":
        config["execution"]["executor"] = "sge"
    elif fault == "missing_samples":
        config["new_sample_info"] = str(batch / "missing.tsv")
    else:
        (batch / "Step1_run.sh").write_text("exit 0\n")
    (batch / "config.yaml").write_text(yaml.safe_dump(config))
    with pytest.raises((ValueError, RuntimeError, FileNotFoundError)):
        local_gate.run_local_analysis(data)
    assert not (batch / "log/argv.txt").exists()
