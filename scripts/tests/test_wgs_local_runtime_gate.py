from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest
import yaml


MODULE_PATH = Path(__file__).resolve().parents[1] / "wgs_local_runtime_gate.py"
SPEC = importlib.util.spec_from_file_location("wgs_local_runtime_gate", MODULE_PATH)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def _payload(tmp_path: Path) -> dict:
    analysis_id = "WGS_20260907_123456_A1B2C3"
    request_root = tmp_path / "requests"
    analysis_root = tmp_path / "analysis"
    batch = "WGS_20260825A_T7Hg38V4.1.1"
    payload = {
        "schema_version": "wgs-runtime.request.v4",
        "analysis_id": analysis_id,
        "attempt": 1,
        "stage": "local_analysis",
        "pipeline_release_id": "wgs-4.1.1-1656b5d",
        "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
        "control_workdir": str(tmp_path / "runtime" / "runs" / analysis_id / "attempt-1"),
        "analysis_project_root": str(analysis_root),
        "expected_batch_root": str(analysis_root / batch),
        "project_name": "WGS_Clinical",
        "batch_no": batch,
        "fq_path": "/sg2/T7/result6/OutputFq/T7",
        "orchestration_contract_version": 2,
        "execution_id": "wse_test",
        "generation": 1,
        "request_hash": "a" * 64,
    }
    path = request_root / analysis_id / "attempt-1" / "local_analysis.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_parse_command_is_strict():
    assert gate.parse_command(
        "wgs-local-runtime WGS_20260907_123456_A1B2C3 1 local_analysis"
    ) == ("WGS_20260907_123456_A1B2C3", 1, "local_analysis")
    with pytest.raises(ValueError):
        gate.parse_command("bash -lc whoami")
    with pytest.raises(ValueError):
        gate.parse_command("wgs-local-runtime ../../escape 1 local_analysis")


def test_load_request_rejects_identity_and_symlink(tmp_path: Path, monkeypatch):
    payload = _payload(tmp_path)
    monkeypatch.setattr(gate, "REQUEST_ROOT", tmp_path / "requests")
    loaded = gate.load_request(payload["analysis_id"], 1, "local_analysis")
    assert loaded["execution_id"] == "wse_test"
    request = tmp_path / "requests" / payload["analysis_id"] / "attempt-1" / "local_analysis.json"
    request.unlink()
    (tmp_path / "outside.json").write_text("{}", encoding="utf-8")
    request.symlink_to(tmp_path / "outside.json")
    with pytest.raises(ValueError, match="escapes request root|missing or unsafe"):
        gate.load_request(payload["analysis_id"], 1, "local_analysis")


def test_validate_batch_root_is_exact_and_requires_frozen_snapshot(tmp_path: Path, monkeypatch):
    payload = _payload(tmp_path)
    monkeypatch.setattr(gate, "ANALYSIS_ROOT", tmp_path / "analysis")
    batch = Path(payload["expected_batch_root"])
    batch.mkdir(parents=True)
    (batch / "pipeline").mkdir()
    (batch / "raw").mkdir()
    (batch / "config.yaml").write_text("execution:\n  executor: cce\n", encoding="utf-8")
    assert gate.validate_batch_root(payload) == batch.resolve()
    payload["expected_batch_root"] = str(tmp_path / "outside")
    with pytest.raises(ValueError, match="approved analysis root"):
        gate.validate_batch_root(payload)


def test_build_local_command_uses_96_cores_and_logger(tmp_path: Path, monkeypatch):
    payload = _payload(tmp_path)
    batch = Path(payload["expected_batch_root"])
    batch.mkdir(parents=True)
    (batch / "Step1_run.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    evidence = tmp_path / "evidence"
    monkeypatch.setattr(gate, "EVIDENCE_ROOT", evidence)
    monkeypatch.setattr(gate, "LOCAL_CORES", 96)
    command = gate.build_local_command(payload, batch)
    assert command[:2] == ["bash", str(batch / "Step1_run.sh")]
    assert command[command.index("--cores") + 1] == "96"
    assert command[command.index("--logger") + 1] == "airflow-demo"
    assert command[command.index("--logger-airflow-demo-run-label") + 1] == (
        f"{payload['analysis_id']}-a1"
    )
    events = evidence / payload["analysis_id"] / "attempt-1" / "rule-status" / "raw" / "node97.jsonl"
    assert str(events) in command
    assert "--forceall" not in command


def test_terminal_status_contains_contract_identity(tmp_path: Path, monkeypatch):
    payload = _payload(tmp_path)
    monkeypatch.setattr(gate, "REQUEST_ROOT", tmp_path / "requests")
    assert gate.write_status(payload, "success", "done") is True
    marker = tmp_path / "requests" / payload["analysis_id"] / "attempt-1" / "local_analysis.status.json"
    value = json.loads(marker.read_text(encoding="utf-8"))
    assert value["execution_id"] == "wse_test"
    assert value["generation"] == 1
    assert value["request_hash"] == "a" * 64
    assert value["status"] == "success"


def test_run_local_analysis_surfaces_process_failure(tmp_path: Path, monkeypatch):
    payload = _payload(tmp_path)
    batch = Path(payload["expected_batch_root"])
    batch.mkdir(parents=True)
    monkeypatch.setattr(gate, "prepare_local_snapshot", lambda *_: batch)
    monkeypatch.setattr(gate, "build_local_command", lambda *_: ["false"])
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 17),
    )
    with pytest.raises(subprocess.CalledProcessError) as caught:
        gate.run_local_analysis(payload)
    assert caught.value.returncode == 17


def test_node97_smoke_builds_a_synthetic_sample_workflow(tmp_path: Path, monkeypatch):
    payload = _payload(tmp_path)
    payload["validation_scope"] = "node97_smoke"
    monkeypatch.setattr(gate, "EVIDENCE_ROOT", tmp_path / "evidence")
    monkeypatch.setattr(gate, "LOCAL_SNAKEMAKE_BIN", tmp_path / "snakemake")

    workdir, command = gate.build_smoke_command(payload)

    snakefile = workdir / "Snakefile"
    assert snakefile.is_file()
    assert "SMOKE001" in snakefile.read_text(encoding="utf-8")
    assert command[0] == str(tmp_path / "snakemake")
    assert command[command.index("--cores") + 1] == "1"
    assert command[command.index("--logger") + 1] == "airflow-demo"
    assert "--forceall" not in command


def test_node97_smoke_never_prepares_a_real_batch(tmp_path: Path, monkeypatch):
    payload = _payload(tmp_path)
    payload["validation_scope"] = "node97_smoke"
    called = []
    monkeypatch.setattr(
        gate,
        "prepare_local_snapshot",
        lambda *_: pytest.fail("synthetic smoke must not inspect a WGS batch"),
    )
    monkeypatch.setattr(gate, "run_node97_smoke", lambda value: called.append(value))

    gate.run_local_analysis(payload)

    assert called == [payload]


def test_convert_config_switches_only_executor(tmp_path: Path):
    source = {"execution": {"executor": "cce", "other": "keep"}, "value": 3}
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(source), encoding="utf-8")
    converted = gate.local_source_config(path)
    assert converted["execution"] == {"executor": "local", "other": "keep"}
    assert converted["value"] == 3


def test_normalize_local_fastq_links_flattens_an_intermediate_symlink(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source" / "sample.R1.fq.gz"
    source.parent.mkdir()
    source.write_bytes(b"fastq")
    intake = tmp_path / "intake"
    intake.mkdir()
    intermediate = intake / source.name
    intermediate.symlink_to(source)
    raw = tmp_path / "batch" / "raw"
    raw.mkdir(parents=True)
    link = raw / source.name
    link.symlink_to(intermediate)

    sources = gate.normalize_local_fastq_links(raw)

    assert sources == [str(source.resolve())]
    assert link.is_symlink()
    assert link.readlink() == source.resolve()
