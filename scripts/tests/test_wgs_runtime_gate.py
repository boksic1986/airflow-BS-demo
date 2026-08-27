import importlib.util
from pathlib import Path
import sys
import types

import pytest


ROOT = Path(__file__).parents[1]


def load_gate():
    if sys.platform == "win32" and "fcntl" not in sys.modules:
        sys.modules["fcntl"] = types.SimpleNamespace(
            LOCK_EX=1,
            flock=lambda *_args, **_kwargs: None,
        )
    spec = importlib.util.spec_from_file_location(
        "wgs_runtime_gate_test", ROOT / "wgs_runtime_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_forced_command_accepts_only_registered_wgs_stages() -> None:
    gate = load_gate()

    assert gate.parse_command(
        "wgs-runtime WGS_20260826_010203_A1B2C3 1 step1_upload"
    ) == ("WGS_20260826_010203_A1B2C3", 1, "step1_upload")
    for command in (
        "bash -c id",
        "wgs-runtime WGS_20260826_010203_A1B2C3 1 step0_reset",
        "wgs-runtime WGS_20260826_010203_A1B2C3 1 step7_cleanup",
    ):
        with pytest.raises((ValueError, TypeError)):
            gate.parse_command(command)


def test_gate_uses_wgs_generated_steps_without_airflow_cce_version_gate() -> None:
    source = (ROOT / "wgs_runtime_gate.py").read_text(encoding="utf-8")

    for script in (
        "Step1_upload_fastq.sh",
        "Step2_run.sh",
        "Step3_status.sh",
        "Step4_publish_results.sh",
        "Step5_download_verify.sh",
        "Step6_materialize_results.sh",
    ):
        assert script in source
    assert "REQUIRED_CCE_PIPELINE_VERSION" not in source
    assert "REQUIRED_CCE_PIPELINE_WHEEL_SHA256" not in source
    assert "_assert_runtime_versions" not in source
    assert "cce-pipeline run" not in source
    assert "FASTQ_SOURCES.tsv" not in source
    assert "WGS_EXECUTION_ENABLED" in source
    assert "shell=True" not in source


def test_prepare_command_uses_fixed_shared_wgs_repository(tmp_path: Path) -> None:
    gate = load_gate()
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "prepare",
        "pipeline_release_id": "wgs-4.1.1-1778fca",
        "wgs_version": "V4.1.1",
        "wgs_source_commit": "1778fcabd99b5253aa90cd410112dc2f78e0c51a",
        "node200_workdir": str(tmp_path / "attempt-1"),
        "project_name": "clinical-wgs",
        "batch_no": "BATCH-01",
        "fq_path": "/sg2/33.chenjiucheng/WGS_input/BATCH-01",
    }

    command = gate.build_prepare_command(payload)

    assert command[1] == str(gate.WGS_REPO_ROOT / "prepare" / "prepare_wgs_batch.py")
    assert command[2] == "all"
    assert "--run-mode" in command and "cce" in command
    assert "--run-id" in command and "WGS_20260826_010203_A1B2C3-a1" in command
    assert "--fastq-root" in command
    assert gate.WGS_PREPARE_CONFIG in command
    assert gate.CCE_OPERATOR_CONFIG in command
    assert not any("SECRET" in item for item in command)


def test_release_repository_validation_rejects_commit_or_runtime_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    repo = tmp_path / "wgs-4.1.1"
    (repo / "prepare").mkdir(parents=True)
    (repo / "prepare" / "prepare_wgs_batch.py").write_text("# tracked\n")
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[-2:] == ["rev-parse", "HEAD"]:
            return type("Result", (), {"stdout": "wrong-commit\n"})()
        return type("Result", (), {"stdout": ""})()

    monkeypatch.setattr(gate, "WGS_REPO_ROOT", repo)
    monkeypatch.setattr(gate.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="release_unavailable"):
        gate.validate_release_repository(
            {
                "pipeline_release_id": "wgs-4.1.1-1778fca",
                "wgs_source_commit": "1778fcabd99b5253aa90cd410112dc2f78e0c51a",
            }
        )
    assert calls[0][-2:] == ["rev-parse", "HEAD"]


def test_prepare_retry_reuses_frozen_binding_without_repository_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    binding = tmp_path / "batch-binding.json"
    binding.write_text("{}\n", encoding="utf-8")
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "pipeline_release_id": "wgs-4.1.1-1778fca",
    }
    reused: list[dict] = []

    monkeypatch.setattr(gate, "_binding_path", lambda _payload: binding)
    monkeypatch.setattr(
        gate,
        "validate_release_repository",
        lambda _payload: (_ for _ in ()).throw(
            AssertionError("repository must not be consulted after bundle freeze")
        ),
    )
    monkeypatch.setattr(gate, "_load_binding", lambda value: reused.append(value))

    gate._run_prepare(payload)

    assert reused == [payload]


def test_step3_status_contract_is_strict_and_master_only() -> None:
    gate = load_gate()
    value = gate.validate_step3_status(
        {
            "master_state": "RUNNING",
            "normal": True,
            "current_rule": "align",
            "current_rules": ["align"],
            "last_completed_rule": "fastp",
            "completed": 3,
            "total": 20,
            "percent": 15.0,
            "message": "running",
        }
    )
    assert value["master_state"] == "RUNNING"
    assert "pods" not in value
    with pytest.raises(ValueError, match="master_state"):
        gate.validate_step3_status({"normal": True})


def test_step3_evidence_bridge_command_uses_frozen_binding_and_shared_spool(
    tmp_path: Path,
) -> None:
    gate = load_gate()
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
    }
    binding = {
        "cce_bundle": str(tmp_path / "cce"),
        "namespace": "snakemake-ns",
        "master_job": "wgs-master-abc",
        "run_id": "WGS_20260826_010203_A1B2C3-a1",
        "rule_source_dir": "/workspace/wgs/runs/project/batch/evidence/WGS_20260826_010203_A1B2C3-a1/rule-status/raw",
    }

    command = gate.build_evidence_bridge_command(payload, binding, terminal=True)

    assert command[0] == gate.WGS_PYTHON
    assert command[1].endswith("wgs_evidence_bridge.py")
    assert command[command.index("--master-job") + 1] == "wgs-master-abc"
    assert command[command.index("--rule-source-dir") + 1].endswith(
        "/rule-status/raw"
    )
    assert command[command.index("--output") + 1].endswith(
        "/WGS_20260826_010203_A1B2C3/attempt-1"
    )
    assert "--terminal" in command
    assert "/obs-data" not in " ".join(command)


def test_async_worker_is_nohup_setsid_flock_and_stage_status_is_versioned(
    tmp_path: Path,
) -> None:
    gate = load_gate()
    command = gate.build_async_worker_command(
        analysis_id="WGS_20260826_010203_A1B2C3",
        attempt=1,
        stage="step5_download",
        lock_path=tmp_path / "worker.lock",
    )
    assert command[:4] == ["nohup", "setsid", "flock", "-n"]
    assert "--worker" in command
    assert gate.STAGE_STATUS_SCHEMA == "wgs-runtime.stage-status.v1"
    assert all(";" not in item and "$(" not in item for item in command)


def test_node005_transfer_wrapper_remains_retired() -> None:
    assert not (ROOT / "node005_obs_transfer.py").exists()
