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
    assert gate.parse_command(
        "wgs-runtime WGS_20260826_010203_A1B2C3 1 step4_repair_cram"
    ) == ("WGS_20260826_010203_A1B2C3", 1, "step4_repair_cram")
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
        "pipeline_release_id": "wgs-4.1.1-1656b5d",
        "wgs_version": "V4.1.1",
        "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
        "node200_workdir": str(tmp_path / "attempt-1"),
        "project_name": "clinical-wgs",
        "batch_no": "WGS_20260825A_T7Hg38V4.1.1",
        "fq_path": "/sg2/33.chenjiucheng/WGS_input/WGS_20260825A_T7Hg38V4.1.1",
    }

    command = gate.build_prepare_command(payload)

    assert command[1] == str(gate.WGS_REPO_ROOT / "prepare" / "prepare_wgs_batch.py")
    assert command[2] == "all"
    assert command[command.index("--batch") + 1] == "20260825A"
    assert (
        command[command.index("--analysis-batch") + 1]
        == "20260825A"
    )
    assert "--run-mode" in command and "cce" in command
    assert "--run-id" in command and "WGS_20260826_010203_A1B2C3-a1" in command
    assert command[command.index("--fastq-root") + 1] == "/sg2/33.chenjiucheng/WGS_input"
    assert gate.WGS_PREPARE_CONFIG == str(
        gate.WGS_REPO_ROOT / "prepare" / "config.yaml"
    )
    assert gate.WGS_PREPARE_CONFIG in command
    assert "/home/chenjc/.config/wgs/prepare.yaml" not in command
    assert gate.CCE_OPERATOR_CONFIG in command
    assert "--skip-samplelist-ready-check" in command
    assert not any("SECRET" in item for item in command)


def test_prepare_command_rejects_batch_without_sequencing_batch() -> None:
    gate = load_gate()
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "prepare",
        "pipeline_release_id": "wgs-4.1.1-2499749",
        "wgs_version": "V4.1.1",
        "wgs_source_commit": "2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68",
        "node200_workdir": "/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime/runs/WGS_20260826_010203_A1B2C3/attempt-1",
        "project_name": "WGS_Clinical",
        "batch_no": "WGS_BATCH_WITHOUT_DATE",
        "fq_path": "/bi/biodevrwbi/33.chenjiucheng/project/airflow-WGS/runtime/intake/BATCH-01",
    }

    with pytest.raises(ValueError, match="sequencing batch"):
        gate.build_prepare_command(payload)


def test_prepare_command_rejects_fastq_directory_for_another_batch(
    tmp_path: Path,
) -> None:
    gate = load_gate()
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "prepare",
        "pipeline_release_id": "wgs-4.1.1-2499749",
        "wgs_version": "V4.1.1",
        "wgs_source_commit": "2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68",
        "node200_workdir": str(tmp_path / "attempt-1"),
        "project_name": "WGS_Clinical",
        "batch_no": "WGS_20260825A_T7Hg38V4.1.1",
        "fq_path": "/bi/airflow-wgs/runtime/intake/WGS_20260826A_T7Hg38V4.1.1",
    }

    with pytest.raises(ValueError, match="FASTQ directory"):
        gate.build_prepare_command(payload)


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
                "pipeline_release_id": "wgs-4.1.1-1656b5d",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
            }
        )
    assert calls[0][-2:] == ["rev-parse", "HEAD"]


def test_release_repository_validation_allows_documentation_only_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    repo = tmp_path / "wgs-4.1.1"
    (repo / "prepare").mkdir(parents=True)
    (repo / "prepare" / "prepare_wgs_batch.py").write_text("# tracked\n")
    expected_commit = "2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68"

    def fake_run(command, **kwargs):
        if command[-2:] == ["rev-parse", "HEAD"]:
            return type("Result", (), {"stdout": expected_commit + "\n"})()
        if command[-2:] == ["status", "--porcelain"]:
            return type(
                "Result",
                (),
                {"stdout": " M README.md\n?? docs/runtime-contract.md\n"},
            )()
        raise AssertionError(f"unexpected git command: {command}")

    monkeypatch.setattr(gate, "WGS_REPO_ROOT", repo)
    monkeypatch.setattr(gate.subprocess, "run", fake_run)

    assert gate.validate_release_repository(
        {
            "pipeline_release_id": "wgs-4.1.1-2499749",
            "wgs_source_commit": expected_commit,
        }
    ) == repo.resolve()


@pytest.mark.parametrize(
    "porcelain_status",
    (
        " M prepare/prepare_wgs_batch.py\n",
        "?? README.md.bak\n",
    ),
)
def test_release_repository_validation_still_rejects_runtime_or_similar_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, porcelain_status: str
) -> None:
    gate = load_gate()
    repo = tmp_path / "wgs-4.1.1"
    (repo / "prepare").mkdir(parents=True)
    (repo / "prepare" / "prepare_wgs_batch.py").write_text("# tracked\n")
    expected_commit = "2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68"

    def fake_run(command, **kwargs):
        stdout = (
            expected_commit + "\n"
            if command[-2:] == ["rev-parse", "HEAD"]
            else porcelain_status
        )
        return type("Result", (), {"stdout": stdout})()

    monkeypatch.setattr(gate, "WGS_REPO_ROOT", repo)
    monkeypatch.setattr(gate.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="runtime changes"):
        gate.validate_release_repository(
            {
                "pipeline_release_id": "wgs-4.1.1-2499749",
                "wgs_source_commit": expected_commit,
            }
        )


def test_prepare_retry_reuses_frozen_binding_without_repository_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    binding = tmp_path / "batch-binding.json"
    binding.write_text("{}\n", encoding="utf-8")
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "pipeline_release_id": "wgs-4.1.1-1656b5d",
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


def test_step3_output_uses_last_json_record_after_kubectl_messages() -> None:
    gate = load_gate()
    parsed = gate.parse_step3_status_output(
        "pod/reader condition met\n"
        'job.batch "reader" deleted\n'
        '{"master_state":"FAILED","normal":false,"completed":0,'
        '"total":0,"percent":0,"message":"master failed"}\n'
    )

    assert parsed["master_state"] == "FAILED"
    assert parsed["message"] == "master failed"


def test_step3_output_rejects_missing_json_record() -> None:
    gate = load_gate()
    with pytest.raises(ValueError, match="valid JSON"):
        gate.parse_step3_status_output("pod/reader condition met\n")


def test_step4_repair_command_is_derived_only_from_frozen_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    cce = tmp_path / "cce"
    cce.mkdir()
    script = cce / "Step4_publish_results.sh"
    script.write_text("#!/bin/bash\n", encoding="utf-8")
    binding = {
        "cce_bundle": str(cce),
        "project": "WGS_Clinical",
        "batch": "20260821B",
        "run_id": "WGS_20260829_010203_A1B2C3-a1",
        "repair_groups": {"cram": {"target": "linkage/cram"}},
    }
    monkeypatch.setattr(gate, "_load_binding", lambda _payload: binding)

    command = gate.build_step4_repair_command({"analysis_id": "WGS_20260829_010203_A1B2C3", "attempt": 1})

    assert command == [
        "bash",
        str(script),
        "--repair-linkage-group",
        "cram",
        "--confirm",
        "REPAIR-LINKAGE:WGS_Clinical/20260821B/WGS_20260829_010203_A1B2C3-a1:cram",
    ]


def test_step4_repair_rejects_bundle_without_cram_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = load_gate()
    monkeypatch.setattr(
        gate,
        "_load_binding",
        lambda _payload: {
            "cce_bundle": "/frozen/cce",
            "project": "WGS_Clinical",
            "batch": "20260821B",
            "run_id": "run-1",
            "repair_groups": {},
        },
    )

    with pytest.raises(RuntimeError, match="cram"):
        gate.build_step4_repair_command({"analysis_id": "WGS_20260829_010203_A1B2C3", "attempt": 1})


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
