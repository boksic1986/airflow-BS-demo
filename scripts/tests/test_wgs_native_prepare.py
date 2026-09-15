"""Native prepare routing/binding, using only synthetic project artifacts."""
import json
from pathlib import Path

import pytest
import yaml

from test_wgs_420_handoff_gate import (
    load_gate, payload, safe_pending_row, write_all_pending_receipt, write_source,
)


def setup_native(tmp_path, monkeypatch, mode):
    gate = load_gate()
    repo = tmp_path / "wgs"
    (repo / "prepare").mkdir(parents=True)
    (repo / "prepare" / "prepare_wgs_batch.py").write_text("# synthetic")
    (repo / "prepare" / "config.yaml").write_text("{}")
    monkeypatch.setattr(gate, "WGS_REPO_ROOT", repo)
    monkeypatch.setattr(gate, "RUNTIME_RUN_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setattr(gate, "CCE_PIPELINE_BIN", "")
    data = payload(tmp_path, generation=1)
    data["prepare_execution"] = {
        "attempt": 1, "mode": mode,
        "target": {"cce": "cce", "local": "node-96", "sge": "sge-default"}[mode],
        "revision": 2,
    }
    write_source(tmp_path)
    return gate, data


@pytest.mark.parametrize("mode", ["cce", "local", "sge"])
def test_prepare_argv_uses_frozen_mode_without_cloud_flags_onprem(tmp_path, monkeypatch, mode):
    gate, data = setup_native(tmp_path, monkeypatch, mode)
    data.update(algo="Haplotyper", use_reference="ref")
    argv = gate.build_prepare_command(data)
    assert argv[argv.index("--run-mode") + 1] == mode
    assert argv[argv.index("--algo") + 1] == "Haplotyper"
    assert argv[argv.index("--use-reference") + 1] == "ref"
    assert "--handoff-request" in argv
    for flag in ("--cce-config", "--run-id"):
        assert (flag in argv) == (mode == "cce")
    assert "--cce-from-zero" not in argv
    assert "--cce-pipeline" not in argv


def publish_native(gate, data, argv):
    """Synthetic stand-in for external WGS; platform code handles real receipts."""
    root = Path(data["expected_batch_root"])
    mode = argv[argv.index("--run-mode") + 1]
    root.mkdir()
    profile = root / "pipeline" / "cfg" / "profiles" / mode
    profile.mkdir(parents=True)
    (profile / "config.yaml").write_text("executor: local\n" if mode == "local" else "executor: cluster-generic\n")
    (root / "config.yaml").write_text(yaml.safe_dump({"execution": {"executor": mode}}))
    (root / "Step1_run.sh").write_text("#!/bin/bash\n# synthetic native entry\n")
    source = root.parent / "sampleinfo" / f"{data['batch_no']}.sampleinfo.txt"
    final = root / f"{data['batch_no']}.sampleinfo.txt"
    final.write_bytes(source.read_bytes())
    request_path = Path(argv[argv.index("--handoff-request") + 1])
    private = write_all_pending_receipt(gate, request_path, source)
    private.write_text(private.read_text().splitlines()[0] + "\n")
    request = json.loads(request_path.read_text())
    receipt_path = request_path.parent / "prepare_analysis.receipt.json"
    receipt = json.loads(receipt_path.read_text())
    artifact = request_path.parent / request["artifact_keys"]["final_sampleinfo"]
    artifact.write_bytes(final.read_bytes())
    receipt["final_sampleinfo"].update(sha256=gate._sha256_file(final), row_count=1)
    receipt["private_pending_payload"].update(sha256=gate._sha256_file(private), row_count=0)
    receipt["selected"] = [{**safe_pending_row(), "decision": "selected", "reason_code": "selected", "reason_message": ""}]
    receipt["pending"] = []
    receipt_path.write_text(json.dumps(receipt))


@pytest.mark.parametrize("mode", ["local", "sge"])
def test_native_prepare_binds_receipt_without_rewriting_project_or_rerunning(tmp_path, monkeypatch, mode):
    gate, data = setup_native(tmp_path, monkeypatch, mode)
    # A catalog may describe CCE too; native preparation must not probe that CLI.
    data["cce_pipeline_version"] = "0.8.4"
    calls = []

    def external_prepare(argv, **kwargs):
        assert argv[2] == "analysis"
        calls.append(argv)
        publish_native(gate, data, argv)

    monkeypatch.setattr(gate.subprocess, "run", external_prepare)
    gate._run_prepare_analysis(data)
    root = Path(data["expected_batch_root"])
    original = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    binding = gate._load_binding(data)
    assert binding["prepare_execution"] == data["prepare_execution"]
    assert binding["resolved_runtime"]["execution_mode"] == mode
    assert "cce_bundle" not in binding
    assert [s["sample_id"] for s in data["prepare_handoff_receipt"]["selected"]] == ["SAMPLE-1"]
    assert not (root / "cce").exists()
    assert not (Path(data["control_workdir"]) / "release-runtime").exists()
    # Recover a lost platform binding from the exact native receipt, not prepare.
    gate._binding_path(data).unlink()
    retry = {k: v for k, v in data.items() if k != "prepare_handoff_receipt"}
    gate._run_prepare_analysis(retry)
    gate._run_prepare_analysis(retry)
    assert len(calls) == 1
    assert retry["prepare_handoff_receipt"]["selected"] == data["prepare_handoff_receipt"]["selected"]
    assert original == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    (root / "config.yaml").write_text("execution: {executor: cce}\n")
    with pytest.raises((ValueError, RuntimeError), match="changed|mismatch"):
        gate._load_binding(data)


@pytest.mark.parametrize("fault", ["attempt", "target", "test_project"])
def test_native_prepare_rejects_invalid_frozen_choice_before_external_work(tmp_path, monkeypatch, fault):
    gate, data = setup_native(tmp_path, monkeypatch, "local")
    if fault == "attempt":
        data["prepare_execution"]["attempt"] = 2
    elif fault == "target":
        data["prepare_execution"]["target"] = "sge-default"
    else:
        data["test_project"] = {"not": "a native test project"}
    with pytest.raises((ValueError, RuntimeError), match="execution|CCE"):
        gate.build_prepare_command(data)


def test_all_pending_receipt_is_reused_without_preparing_again(tmp_path, monkeypatch):
    gate, data = setup_native(tmp_path, monkeypatch, "local")
    source = Path(data["analysis_project_root"]) / "sampleinfo" / f"{data['batch_no']}.sampleinfo.txt"
    request = gate._prepare_handoff_request(data)
    write_all_pending_receipt(gate, request, source)

    def unexpected_prepare(*args, **kwargs):
        pytest.fail("A completed all-pending preparation must not run again")

    monkeypatch.setattr(gate.subprocess, "run", unexpected_prepare)
    gate._run_prepare_analysis(data)
    assert data["prepare_handoff_receipt"]["selected"] == []
    assert len(data["prepare_handoff_receipt"]["pending"]) == 1
    assert not gate._binding_path(data).exists()
