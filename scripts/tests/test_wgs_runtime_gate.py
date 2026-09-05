import importlib.util
import json
from pathlib import Path
import sys
import threading
import types
from concurrent.futures import ThreadPoolExecutor

import pytest
import yaml


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


def test_hanjj_forced_command_uses_private_runtime_environment() -> None:
    source = (ROOT / "wgs_runtime_forced_command.sh").read_text(encoding="utf-8")

    assert 'config_dir="/home/hanjj/.config/airflow-wgs"' in source
    assert 'runtime_env="${config_dir}/runtime.env"' in source
    assert 'runtime_gate="${config_dir}/wgs_runtime_gate.py"' in source
    assert 'exec "${WGS_PYTHON}" "${runtime_gate}" "$@"' in source
    assert "/home/chenjc" not in source


def test_forced_command_accepts_only_registered_wgs_stages() -> None:
    gate = load_gate()

    assert gate.parse_command(
        "wgs-runtime WGS_20260826_010203_A1B2C3 1 step1_upload"
    ) == ("WGS_20260826_010203_A1B2C3", 1, "step1_upload")
    assert gate.parse_command(
        "wgs-runtime WGS_20260826_010203_A1B2C3 1 step4_repair_cram"
    ) == ("WGS_20260826_010203_A1B2C3", 1, "step4_repair_cram")
    assert gate.parse_command(
        "wgs-runtime WGS_20260826_010203_A1B2C3 1 step7_cleanup"
    ) == ("WGS_20260826_010203_A1B2C3", 1, "step7_cleanup")
    assert gate.parse_command(
        "wgs-runtime WGS_20260826_010203_A1B2C3 1 prepare_sampleinfo"
    ) == ("WGS_20260826_010203_A1B2C3", 1, "prepare_sampleinfo")
    assert gate.parse_command(
        "wgs-runtime WGS_20260826_010203_A1B2C3 1 prepare_analysis"
    ) == ("WGS_20260826_010203_A1B2C3", 1, "prepare_analysis")
    for command in (
        "bash -c id",
        "wgs-runtime WGS_20260826_010203_A1B2C3 1 step0_reset",
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
        "control_workdir": str(tmp_path / "control" / "attempt-1"),
        "analysis_project_root": str(tmp_path / "analysis"),
        "expected_batch_root": str(tmp_path / "analysis" / "WGS_20260825A_T7Hg38V4.1.1"),
        "project_name": "clinical-wgs",
        "batch_no": "WGS_20260825A_T7Hg38V4.1.1",
        "fq_path": "/sg2/33.chenjiucheng/WGS_input/WGS_20260825A_T7Hg38V4.1.1",
        "analysis_batch": "20260902A",
        "platform": "T7",
    }

    command = gate.build_prepare_command(payload)

    assert command[1] == str(gate.WGS_REPO_ROOT / "prepare" / "prepare_wgs_batch.py")
    assert command[2] == "all"
    assert command[command.index("--outpath") + 1] == str(tmp_path / "analysis")
    assert command[command.index("--batch") + 1] == "20260825A"
    assert (
        command[command.index("--analysis-batch") + 1]
        == "20260902A"
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
    assert command[command.index("--platform") + 1] == "T7"
    assert "--algo" not in command
    assert not any("SECRET" in item for item in command)


def test_split_prepare_commands_preserve_native_wgs_contract(tmp_path: Path) -> None:
    gate = load_gate()
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "pipeline_release_id": "wgs-4.1.1-6c98281",
        "wgs_version": "V4.1.1",
        "wgs_source_commit": "6c982817614db6a1157b6f287427ddf01ac91827",
        "control_workdir": str(tmp_path / "control" / "attempt-1"),
        "analysis_project_root": str(tmp_path / "WGS_Clinical"),
        "expected_batch_root": str(tmp_path / "WGS_Clinical" / "WGS_20260902A_T7Hg38V4.1.1"),
        "project_name": "WGS_Clinical",
        "batch_no": "WGS_20260902A_T7Hg38V4.1.1",
        "fq_path": "/bi/fastq/T7_Fastq",
        "fastq_root": "/bi/fastq/T7_Fastq",
        "sequencing_batch": "20260902A",
        "analysis_batch": "20260902A",
        "platform": "T7",
        "use_reference": "ref",
    }

    sampleinfo = gate.build_prepare_command({**payload, "stage": "prepare_sampleinfo"})
    analysis = gate.build_prepare_command({**payload, "stage": "prepare_analysis"})

    assert sampleinfo[2] == "sampleinfo"
    assert "--batch" in sampleinfo and "20260902A" in sampleinfo
    assert "--sampleinfo" not in sampleinfo
    assert analysis[2] == "analysis"
    assert analysis[analysis.index("--sampleinfo") + 1] == str(
        tmp_path / "WGS_Clinical" / "sampleinfo" / "WGS_20260902A_T7Hg38V4.1.1.sampleinfo.txt"
    )
    assert analysis[analysis.index("--use-reference") + 1] == "ref"


def test_prepare_command_rejects_batch_without_sequencing_batch() -> None:
    gate = load_gate()
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "prepare",
        "pipeline_release_id": "wgs-4.1.1-2499749",
        "wgs_version": "V4.1.1",
        "wgs_source_commit": "2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68",
        "control_workdir": "/sg2/14.hanjingjing/Cloud_WGS_Clinical/airflow-wgs/runtime/runs/WGS_20260826_010203_A1B2C3/attempt-1",
        "analysis_project_root": "/sg2/14.hanjingjing/Cloud_WGS_Clinical",
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
        "control_workdir": str(tmp_path / "control" / "attempt-1"),
        "analysis_project_root": str(tmp_path / "analysis"),
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
    (repo / ".git").mkdir()
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
    (repo / ".git").mkdir()
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


def test_release_repository_validation_maps_registered_mnt_worktree_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    repo = tmp_path / "bi" / "biodevrwbi" / "project" / "wgs-4.1.1"
    prepare = repo / "prepare" / "prepare_wgs_batch.py"
    prepare.parent.mkdir(parents=True)
    prepare.write_text("# tracked\n")
    repo.joinpath(".git").write_text(
        f"gitdir: {tmp_path / 'mnt' / 'biodevrwbi' / 'project' / 'wgs' / '.git' / 'worktrees' / 'wgs-4.1.1'}\n"
    )
    mapped = tmp_path / "bi" / "biodevrwbi" / "project" / "wgs" / ".git" / "worktrees" / "wgs-4.1.1"
    mapped.mkdir(parents=True)
    expected = "6c982817614db6a1157b6f287427ddf01ac91827"
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return type("Result", (), {"stdout": expected + "\n" if command[-2:] == ["rev-parse", "HEAD"] else ""})()

    monkeypatch.setattr(gate, "WGS_REPO_ROOT", repo)
    monkeypatch.setattr(gate, "WGS_GIT_MNT_PREFIX", str(tmp_path / "mnt" / "biodevrwbi"))
    monkeypatch.setattr(gate, "WGS_GIT_NODE_PREFIX", str(tmp_path / "bi" / "biodevrwbi"))
    monkeypatch.setattr(gate.subprocess, "run", fake_run)

    assert gate.validate_release_repository({"wgs_source_commit": expected}) == repo.resolve()
    assert f"--git-dir={mapped}" in calls[0]
    assert f"--work-tree={repo.resolve()}" in calls[0]


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
    (repo / ".git").mkdir()
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


def test_step7_cleanup_confirmation_is_derived_only_from_frozen_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    cce = tmp_path / "cce"
    cce.mkdir()
    script = cce / "Step7_cleanup_sfs.sh"
    script.write_text("#!/bin/bash\n", encoding="utf-8")
    monkeypatch.setattr(
        gate,
        "_load_binding",
        lambda _payload: {
            "cce_bundle": str(cce),
            "project": "WGS_Clinical",
            "batch": "WGS_20260901A_T7Hg38V4.1.1",
            "run_id": "WGS_20260901_010203_A1B2C3-a1",
        },
    )

    command = gate.build_step7_cleanup_command(
        {"analysis_id": "WGS_20260901_010203_A1B2C3", "attempt": 1}
    )

    assert command == [
        "bash",
        str(script),
        "--confirm",
        "DELETE-SFS:WGS_Clinical/WGS_20260901A_T7Hg38V4.1.1/WGS_20260901_010203_A1B2C3-a1",
    ]


def test_step4_wait_retries_short_master_completion_race_for_bound_successful_step3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    analysis_id = "WGS_20260826_010203_A1B2C3"
    request_root = tmp_path / "requests"
    request_dir = request_root / analysis_id / "attempt-1"
    request_dir.mkdir(parents=True)
    payload = {
        "analysis_id": analysis_id,
        "attempt": 1,
        "stage": "step4_publish",
    }
    (request_dir / "step3_monitor.status.json").write_text(
        json.dumps(
            {
                "schema_version": gate.STAGE_STATUS_SCHEMA,
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step3_monitor",
                "status": "success",
                "master_job": "cce-master-0123456789abcdef0123",
            }
        ),
        encoding="utf-8",
    )
    responses = iter(
        [
            type(
                "Result",
                (),
                {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "RuntimeError: Step4 requires a successful Master Job",
                },
            )(),
            type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
        ]
    )
    sleeps: list[int] = []
    statuses: list[tuple[str, str]] = []

    monkeypatch.setattr(gate, "REQUEST_ROOT", request_root)
    monkeypatch.setattr(
        gate,
        "_load_binding",
        lambda _payload: {"master_job": "cce-master-0123456789abcdef0123"},
    )
    monkeypatch.setattr(gate, "_step_command", lambda *_args: ["step4"])
    monkeypatch.setattr(gate.subprocess, "run", lambda *_args, **_kwargs: next(responses))
    monkeypatch.setattr(gate.time, "sleep", sleeps.append)
    monkeypatch.setattr(
        gate,
        "_write_status",
        lambda _payload, status, message="", **_details: statuses.append(
            (status, message)
        ),
    )

    gate._wait_step4(payload)

    assert sleeps == [gate.MONITOR_INTERVAL_SECONDS]
    assert statuses[0][0] == "running"
    assert "successful Master Job" in statuses[0][1]


def test_step4_wait_rejects_master_error_without_matching_step3_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    analysis_id = "WGS_20260826_010203_A1B2C3"
    request_root = tmp_path / "requests"
    request_dir = request_root / analysis_id / "attempt-1"
    request_dir.mkdir(parents=True)
    (request_dir / "step3_monitor.status.json").write_text(
        json.dumps(
            {
                "schema_version": gate.STAGE_STATUS_SCHEMA,
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step3_monitor",
                "status": "failed",
                "master_job": "cce-master-0123456789abcdef0123",
            }
        ),
        encoding="utf-8",
    )
    payload = {
        "analysis_id": analysis_id,
        "attempt": 1,
        "stage": "step4_publish",
    }

    monkeypatch.setattr(gate, "REQUEST_ROOT", request_root)
    monkeypatch.setattr(
        gate,
        "_load_binding",
        lambda _payload: {"master_job": "cce-master-0123456789abcdef0123"},
    )
    monkeypatch.setattr(gate, "_step_command", lambda *_args: ["step4"])
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result",
            (),
            {
                "returncode": 1,
                "stdout": "",
                "stderr": "RuntimeError: Step4 requires a successful Master Job",
            },
        )(),
    )

    with pytest.raises(RuntimeError, match="successful Master Job"):
        gate._wait_step4(payload)


def test_step4_wait_rejects_successful_step3_for_different_bound_master(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    analysis_id = "WGS_20260826_010203_A1B2C3"
    request_root = tmp_path / "requests"
    request_dir = request_root / analysis_id / "attempt-1"
    request_dir.mkdir(parents=True)
    (request_dir / "step3_monitor.status.json").write_text(
        json.dumps(
            {
                "schema_version": gate.STAGE_STATUS_SCHEMA,
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step3_monitor",
                "status": "success",
                "master_job": "cce-master-forged",
            }
        ),
        encoding="utf-8",
    )
    payload = {"analysis_id": analysis_id, "attempt": 1, "stage": "step4_publish"}

    monkeypatch.setattr(gate, "REQUEST_ROOT", request_root)
    monkeypatch.setattr(
        gate, "_load_binding", lambda _payload: {"master_job": "cce-master-bound"}
    )
    monkeypatch.setattr(gate, "_step_command", lambda *_args: ["step4"])
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result",
            (),
            {
                "returncode": 1,
                "stdout": "",
                "stderr": "RuntimeError: Step4 requires a successful Master Job",
            },
        )(),
    )

    with pytest.raises(RuntimeError, match="successful Master Job"):
        gate._wait_step4(payload)


def test_step4_wait_times_out_after_master_completion_grace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    analysis_id = "WGS_20260826_010203_A1B2C3"
    request_root = tmp_path / "requests"
    request_dir = request_root / analysis_id / "attempt-1"
    request_dir.mkdir(parents=True)
    master_job = "cce-master-bound"
    (request_dir / "step3_monitor.status.json").write_text(
        json.dumps(
            {
                "schema_version": gate.STAGE_STATUS_SCHEMA,
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step3_monitor",
                "status": "success",
                "master_job": master_job,
            }
        ),
        encoding="utf-8",
    )
    payload = {"analysis_id": analysis_id, "attempt": 1, "stage": "step4_publish"}
    clock = iter([0.0, 0.0, 0.0, 0.0, 601.0])

    monkeypatch.setattr(gate, "REQUEST_ROOT", request_root)
    monkeypatch.setattr(gate, "STEP4_MASTER_COMPLETION_GRACE_SECONDS", 600)
    monkeypatch.setattr(gate, "_load_binding", lambda _payload: {"master_job": master_job})
    monkeypatch.setattr(gate, "_step_command", lambda *_args: ["step4"])
    monkeypatch.setattr(gate.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(gate.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(gate, "_write_status", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result",
            (),
            {
                "returncode": 1,
                "stdout": "",
                "stderr": "RuntimeError: Step4 requires a successful Master Job",
            },
        )(),
    )

    with pytest.raises(TimeoutError, match="bound Master Job"):
        gate._wait_step4(payload)


def test_failed_step4_relaunch_archives_terminal_generation_before_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    analysis_id = "WGS_20260826_010203_A1B2C3"
    request_path = tmp_path / "step4_publish.json"
    request_path.write_text("{}\n", encoding="utf-8")
    payload = {
        "analysis_id": analysis_id,
        "attempt": 1,
        "stage": "step4_publish",
    }
    request_sha = gate.hashlib.sha256(request_path.read_bytes()).hexdigest()
    request_path.with_suffix(".status.json").write_text(
        json.dumps({"status": "failed", "message": "old failure"}),
        encoding="utf-8",
    )
    request_path.with_suffix(".worker.json").write_text(
        json.dumps({"pid": 1234, "request_sha256": request_sha}),
        encoding="utf-8",
    )
    request_path.with_suffix(".worker.log").write_text(
        "old worker evidence\n", encoding="utf-8"
    )

    monkeypatch.setattr(gate, "_request_path", lambda *_args: request_path)
    monkeypatch.setattr(gate, "_truthy", lambda _name: True)
    monkeypatch.setattr(gate, "_process_matches", lambda _state: False)
    monkeypatch.setattr(gate, "_boot_id", lambda: "boot-id")
    monkeypatch.setattr(gate, "_process_start_time", lambda _pid: "456")

    class FakeProcess:
        pid = 5678

    monkeypatch.setattr(gate.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())

    result = gate.start_async_stage(payload)

    assert result["status"] == "accepted"
    assert result["retry_no"] == 1
    status = json.loads(
        request_path.with_suffix(".status.json").read_text(encoding="utf-8")
    )
    assert status["status"] == "accepted"
    history = tmp_path / "history" / "step4_publish" / "retry-1"
    assert json.loads((history / "status.json").read_text(encoding="utf-8"))[
        "message"
    ] == "old failure"
    assert (history / "worker.log").read_text(encoding="utf-8") == (
        "old worker evidence\n"
    )


def test_failed_step5_relaunch_preserves_checkpoint_and_archives_worker_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    request_path = tmp_path / "step5_download.json"
    request_path.write_text("{}\n", encoding="utf-8")
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "step5_download",
    }
    request_sha = gate.hashlib.sha256(request_path.read_bytes()).hexdigest()
    request_path.with_suffix(".status.json").write_text(
        json.dumps({"status": "failed", "message": "no space left on device"}),
        encoding="utf-8",
    )
    request_path.with_suffix(".worker.json").write_text(
        json.dumps({"pid": 1234, "request_sha256": request_sha}),
        encoding="utf-8",
    )
    request_path.with_suffix(".worker.log").write_text(
        "obsutil checkpoint retained\n", encoding="utf-8"
    )
    checkpoint = tmp_path / "download-checkpoint"
    checkpoint.write_text("resume-me\n", encoding="utf-8")

    monkeypatch.setattr(gate, "_request_path", lambda *_args: request_path)
    monkeypatch.setattr(gate, "_truthy", lambda _name: True)
    monkeypatch.setattr(gate, "_process_matches", lambda _state: False)
    monkeypatch.setattr(gate, "_boot_id", lambda: "boot-id")
    monkeypatch.setattr(gate, "_process_start_time", lambda _pid: "456")

    class FakeProcess:
        pid = 5678

    monkeypatch.setattr(gate.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())

    result = gate.start_async_stage(payload)

    assert result == {"status": "accepted", "pid": 5678, "retry_no": 1}
    history = tmp_path / "history" / "step5_download" / "retry-1"
    assert json.loads((history / "status.json").read_text(encoding="utf-8"))[
        "message"
    ] == "no space left on device"
    assert (history / "worker.log").read_text(encoding="utf-8") == (
        "obsutil checkpoint retained\n"
    )
    assert checkpoint.read_text(encoding="utf-8") == "resume-me\n"


def test_contract_v2_new_generation_archives_old_sidecars_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    request_path = tmp_path / "step1_upload.json"
    request_path.write_text('{"generation": 2}\n', encoding="utf-8")
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "step1_upload",
        "orchestration_contract_version": 2,
        "execution_id": "wse_new",
        "generation": 2,
        "request_hash": "b" * 64,
    }
    request_path.with_suffix(".status.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "orchestration_contract_version": 2,
                "execution_id": "wse_old",
                "generation": 1,
                "request_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    request_path.with_suffix(".worker.json").write_text(
        json.dumps(
            {
                "pid": 1234,
                "request_sha256": "old-request-sha",
                "orchestration_contract_version": 2,
                "execution_id": "wse_old",
                "generation": 1,
                "request_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    request_path.with_suffix(".worker.log").write_text(
        "generation one\n", encoding="utf-8"
    )
    monkeypatch.setattr(gate, "_request_path", lambda *_args: request_path)
    monkeypatch.setattr(gate, "_truthy", lambda _name: True)
    monkeypatch.setattr(gate, "_process_matches", lambda _state: False)
    monkeypatch.setattr(gate, "_boot_id", lambda: "boot-id")
    monkeypatch.setattr(gate, "_process_start_time", lambda _pid: "456")

    class FakeProcess:
        pid = 5678

    monkeypatch.setattr(
        gate.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess()
    )

    result = gate.start_async_stage(payload)

    assert result["status"] == "accepted"
    assert result["generation"] == 2
    history = tmp_path / "history" / "step1_upload" / "generation-1"
    assert json.loads((history / "status.json").read_text(encoding="utf-8"))[
        "execution_id"
    ] == "wse_old"
    worker = json.loads(
        request_path.with_suffix(".worker.json").read_text(encoding="utf-8")
    )
    assert worker["execution_id"] == "wse_new"
    assert worker["generation"] == 2


def test_contract_v2_new_generation_refuses_to_replace_live_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    request_path = tmp_path / "step1_upload.json"
    request_path.write_text('{"generation": 2}\n', encoding="utf-8")
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "step1_upload",
        "orchestration_contract_version": 2,
        "execution_id": "wse_new",
        "generation": 2,
        "request_hash": "b" * 64,
    }
    request_path.with_suffix(".worker.json").write_text(
        json.dumps(
            {
                "pid": 1234,
                "request_sha256": "old-request-sha",
                "orchestration_contract_version": 2,
                "execution_id": "wse_old",
                "generation": 1,
                "request_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "_request_path", lambda *_args: request_path)
    monkeypatch.setattr(gate, "_truthy", lambda _name: True)
    monkeypatch.setattr(gate, "_process_matches", lambda _state: True)

    with pytest.raises(RuntimeError, match="previous generation worker is still active"):
        gate.start_async_stage(payload)


def test_contract_v2_synchronous_retry_archives_old_terminal_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    request_path = tmp_path / "step6_materialize.json"
    request_path.write_text('{"generation": 2}\n', encoding="utf-8")
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "step6_materialize",
        "orchestration_contract_version": 2,
        "execution_id": "wse_new",
        "generation": 2,
        "request_hash": "b" * 64,
    }
    request_path.with_suffix(".status.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "orchestration_contract_version": 2,
                "execution_id": "wse_old",
                "generation": 1,
                "request_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "_request_path", lambda *_args: request_path)
    monkeypatch.setattr(gate, "run_stage", lambda _payload: None)

    assert gate._run_synchronous_stage(payload) == 0

    status = json.loads(
        request_path.with_suffix(".status.json").read_text(encoding="utf-8")
    )
    assert status["status"] == "success"
    assert status["execution_id"] == "wse_new"
    assert (
        tmp_path
        / "history"
        / "step6_materialize"
        / "generation-1"
        / "status.json"
    ).is_file()


def test_transfer_progress_stays_running_when_an_auxiliary_obsutil_call_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    payload = {
        "analysis_id": "WGS_20260903_111829_1D58E1",
        "attempt": 1,
        "stage": "step1_upload",
    }
    common = {
        "schema_version": "wgs-runtime.transfer-progress.v1",
        "analysis_id": payload["analysis_id"],
        "attempt": 1,
        "stage": "step1_upload",
        "bytes_total": 100,
        "bytes_done": 10,
        "files_total": 1,
        "files_done": 0,
        "speed_bytes_per_second": 5,
        "heartbeat_at": "2026-09-03T11:45:25+00:00",
    }
    (tmp_path / "auxiliary.json").write_text(
        json.dumps({**common, "state": "failed"}), encoding="utf-8"
    )
    (tmp_path / "upload.json").write_text(
        json.dumps({**common, "state": "running"}), encoding="utf-8"
    )
    monkeypatch.setattr(gate, "_transfer_progress_root", lambda _payload: tmp_path)

    progress = gate._aggregate_transfer_progress(payload)

    assert progress is not None
    assert progress["state"] == "running"


def test_sdk_transfer_progress_preserves_frozen_per_file_totals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    payload = {
        "analysis_id": "WGS_20260904_120000_A1B2C3",
        "attempt": 1,
        "stage": "step1_upload",
    }
    sdk = {
        "schema_version": "wgs-runtime.transfer-progress.v2",
        "transfer_id": f"{payload['analysis_id']}-a1-input",
        "analysis_id": payload["analysis_id"],
        "attempt": 1,
        "stage": "step1_upload",
        "direction": "upload",
        "state": "running",
        "bytes_total": 300,
        "bytes_done": 125,
        "files_total": 2,
        "files_done": 1,
        "speed_bytes_per_second": 50,
        "heartbeat_at": "2026-09-04T12:00:05+00:00",
        "files": [
            {"file_key": "a", "display_name": "S1_R1.fq.gz", "bytes_total": 100, "bytes_done": 100, "status": "success"},
            {"file_key": "b", "display_name": "S1_R2.fq.gz", "bytes_total": 200, "bytes_done": 25, "status": "running"},
        ],
    }
    (tmp_path / "progress.json").write_text(json.dumps(sdk), encoding="utf-8")
    monkeypatch.setattr(gate, "_transfer_progress_root", lambda _payload: tmp_path)

    progress = gate._aggregate_transfer_progress(payload)

    assert progress is not None
    assert progress["schema_version"] == "wgs-runtime.transfer-progress.v2"
    assert progress["bytes_total"] == 300
    assert progress["bytes_done"] == 125
    assert progress["files_done"] == 1
    assert len(progress["files"]) == 2


def test_step5_frozen_plan_does_not_claim_unobserved_files_are_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    payload = {
        "analysis_id": "WGS_20260903_200310_37E27D",
        "attempt": 1,
        "stage": "step5_download",
    }
    progress_root = tmp_path / "progress"
    progress_root.mkdir()
    batch_root = tmp_path / "batch"
    completed = batch_root / "cce" / "cloud_delivery" / "cram" / "S1.cram"
    completed.parent.mkdir(parents=True)
    completed.write_bytes(b"1" * 100)
    common = {
        "schema_version": "wgs-runtime.transfer-progress.v1",
        "analysis_id": payload["analysis_id"],
        "attempt": 1,
        "stage": "step5_download",
        "direction": "download",
        "eta_seconds": 0,
        "files_total": 1,
        "files_done": 1,
        "heartbeat_at": "2026-09-04T02:40:00+00:00",
        "monitoring_health": "healthy",
        "source": "obsutil-stream",
        "state": "success",
    }
    (progress_root / "payload.json").write_text(
        json.dumps(
            {
                **common,
                "transfer_id": "payload",
                "bytes_total": 100,
                "bytes_done": 100,
                "speed_bytes_per_second": 50,
            }
        ),
        encoding="utf-8",
    )
    (progress_root / "ready.json").write_text(
        json.dumps(
            {
                **common,
                "transfer_id": "ready",
                "bytes_total": 0,
                "bytes_done": 0,
                "speed_bytes_per_second": 0,
            }
        ),
        encoding="utf-8",
    )
    plan = {
        "files_total": 2,
        "bytes_total": 200,
        "manifest_sha256": "a" * 64,
        "entries": [
            {"relative_path": "cram/S1.cram", "size_bytes": 100},
            {"relative_path": "cram/S2.cram", "size_bytes": 100},
        ],
    }
    monkeypatch.setattr(gate, "_transfer_progress_root", lambda _payload: progress_root)
    monkeypatch.setattr(gate, "_load_binding", lambda _payload: {"batch_root": str(batch_root)})

    progress = gate._aggregate_transfer_progress(payload, plan)

    assert progress is not None
    assert progress["bytes_done"] == 100
    assert progress["bytes_total"] == 200
    assert progress["files_done"] == 1
    assert progress["files_total"] == 2
    assert progress["speed_bytes_per_second"] == 0
    assert progress["state"] == "running"


def test_transfer_plan_freezes_step1_total_before_obsutil_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    raw = tmp_path / "batch" / "raw"
    raw.mkdir(parents=True)
    (raw / "S1-WGS.R1.fq.gz").write_bytes(b"1" * 10)
    (raw / "S1-WGS.R2.fq.gz").write_bytes(b"2" * 20)
    progress_root = tmp_path / "progress"
    payload = {
        "analysis_id": "WGS_20260903_111829_1D58E1",
        "attempt": 1,
        "stage": "step1_upload",
    }
    monkeypatch.setattr(gate, "_transfer_progress_root", lambda _payload: progress_root)
    monkeypatch.setattr(gate, "_load_binding", lambda _payload: {"batch_root": str(tmp_path / "batch")})

    plan = gate._create_transfer_plan(payload)

    assert plan["files_total"] == 2
    assert plan["bytes_total"] == 30
    assert len(plan["manifest_sha256"]) == 64
    (raw / "late-WGS.R1.fq.gz").write_bytes(b"late")
    assert gate._create_transfer_plan(payload) == plan


def test_step5_starts_download_before_freezing_the_downloaded_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    batch_root = tmp_path / "batch"
    manifest = batch_root / "cce" / "cloud_delivery" / "payload-manifest.tsv"
    progress_root = tmp_path / "progress"
    payload = {
        "analysis_id": "WGS_20260903_200310_37E27D",
        "attempt": 1,
        "stage": "step5_download",
    }
    events: list[str] = []

    monkeypatch.setattr(gate, "_transfer_progress_root", lambda _payload: progress_root)
    monkeypatch.setattr(gate, "_load_binding", lambda _payload: {"batch_root": str(batch_root)})
    monkeypatch.setattr(gate, "_step_command", lambda *_args: ["step5-download"])
    monkeypatch.setattr(gate, "_write_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(gate.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(gate, "STEP5_TRANSFER_PLAN_GRACE_SECONDS", 0)

    class FakeProcess:
        returncode = 0

        def __init__(self) -> None:
            self.poll_count = 0

        def poll(self):
            self.poll_count += 1
            if self.poll_count == 1:
                manifest.parent.mkdir(parents=True)
                manifest.write_text(
                    "relative_path\tsize_bytes\n"
                    "07_QC/WGS_20260902B_T7Hg38V4.1.1.QCstat.tsv\t2048\n",
                    encoding="utf-8",
                )
                events.append("manifest")
                return None
            return 0

    def fake_popen(*_args, **_kwargs):
        assert not manifest.exists()
        assert not (progress_root / "transfer-plan.json").exists()
        events.append("spawn")
        return FakeProcess()

    monkeypatch.setattr(gate.subprocess, "Popen", fake_popen)

    gate._run_transfer_stage(payload)

    plan = json.loads(
        (progress_root / "transfer-plan.json").read_text(encoding="utf-8")
    )
    assert events == ["spawn", "manifest"]
    assert plan["stage"] == "step5_download"
    assert plan["files_total"] == 1
    assert plan["bytes_total"] == 2048


def test_step5_success_without_a_downloaded_manifest_is_a_contract_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    batch_root = tmp_path / "batch"
    progress_root = tmp_path / "progress"
    payload = {
        "analysis_id": "WGS_20260903_200310_37E27D",
        "attempt": 1,
        "stage": "step5_download",
    }
    events: list[str] = []

    monkeypatch.setattr(gate, "_transfer_progress_root", lambda _payload: progress_root)
    monkeypatch.setattr(gate, "_load_binding", lambda _payload: {"batch_root": str(batch_root)})
    monkeypatch.setattr(gate, "_step_command", lambda *_args: ["step5-download"])
    monkeypatch.setattr(gate, "_write_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(gate.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(gate, "STEP5_TRANSFER_PLAN_GRACE_SECONDS", 0)

    class FakeProcess:
        returncode = 0

        @staticmethod
        def poll():
            return 0

    def fake_popen(*_args, **_kwargs):
        events.append("spawn")
        return FakeProcess()

    monkeypatch.setattr(gate.subprocess, "Popen", fake_popen)

    with pytest.raises(RuntimeError, match="completed without a payload manifest"):
        gate._run_transfer_stage(payload)

    assert events == ["spawn"]


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
        "analysis_log_source": "/workspace/wgs/runs/project/batch/analysis.log",
    }

    command = gate.build_evidence_bridge_command(payload, binding, terminal=True)

    assert command[0] == gate.WGS_PYTHON
    assert command[1].endswith("wgs_evidence_bridge.py")
    assert command[command.index("--master-job") + 1] == "wgs-master-abc"
    assert command[command.index("--rule-source-dir") + 1].endswith(
        "/rule-status/raw"
    )
    assert command[command.index("--analysis-log-source") + 1].endswith(
        "/analysis.log"
    )
    assert command[command.index("--output") + 1].endswith(
        "/WGS_20260826_010203_A1B2C3/attempt-1"
    )
    assert "--terminal" in command
    assert "/obs-data" not in " ".join(command)


def test_prepare_binding_points_analysis_log_at_the_run_evidence_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    analysis_id = "WGS_20260826_010203_A1B2C3"
    run_id = f"{analysis_id}-a1"
    project_root = tmp_path / "WGS_Clinical"
    batch_root = project_root / "WGS_batch"
    cce = batch_root / "cce"
    cce.mkdir(parents=True)
    run_dir = "/workspace/wgs/runs/WGS_Clinical/WGS_batch"
    (cce / "BATCH_RUNTIME.yaml").write_text(
        yaml.safe_dump(
            {
                "identity": {
                    "project": "WGS_Clinical",
                    "batch": "WGS_batch",
                    "run_id": run_id,
                },
                "paths": {"run_dir": run_dir},
                "kubernetes": {
                    "master_job": "cce-master-0123456789abcdef0123",
                    "namespace": "snakemake-ns",
                },
            }
        ),
        encoding="utf-8",
    )
    (cce / "RESOLVED_PROFILE.yaml").write_text(
        yaml.safe_dump(
            {
                "run_label": "cce-run-0123456789abcdef",
                "platform": {
                    "version": "0.8.2",
                    "wheel_version": "0.8.2",
                    "source_commit": "e4c0f134bd397fb6113456b18cc148346808388e",
                },
                "pipeline": {"master_image": "registry/master@sha256:abc"},
                "transfer": {
                    "upload_file_parallelism": 4,
                    "download_file_parallelism": 8,
                    "obsutil_parts_per_file": 5,
                },
                "heavy_io": {
                    "limit": 25,
                    "mode": "monitor-only",
                    "unit": "work_pod",
                },
            }
        ),
        encoding="utf-8",
    )
    binding_path = tmp_path / "control" / "batch-binding.json"
    binding_path.parent.mkdir()
    monkeypatch.setattr(gate, "_binding_path", lambda _payload: binding_path)
    monkeypatch.setattr(gate, "_workdir", lambda _payload: binding_path.parent)
    payload = {
        "analysis_id": analysis_id,
        "attempt": 1,
        "pipeline_release_id": "wgs-4.1.1-test",
        "wgs_version": "V4.1.1",
        "wgs_source_commit": "a" * 40,
        "analysis_project_root": str(project_root),
        "expected_batch_root": str(batch_root),
        "batch_no": "WGS_batch",
    }

    gate._write_prepare_binding(payload)

    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    assert binding["analysis_log_source"] == (
        f"{run_dir}/evidence/{run_id}/analysis.log"
    )
    assert binding["resolved_runtime"]["cce_pipeline_version"] == "0.8.2"
    assert binding["resolved_runtime"]["cce_pipeline_source_commit"] == (
        "e4c0f134bd397fb6113456b18cc148346808388e"
    )
    assert binding["resolved_runtime"]["transfer"] == {
        "upload_file_parallelism": 4,
        "download_file_parallelism": 8,
        "obsutil_parts_per_file": 5,
    }
    assert binding["resolved_runtime"]["heavy_io"] == {
        "limit": 25,
        "mode": "monitor-only",
        "unit": "work_pod",
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("transfer", {"upload_file_parallelism": 4}, "transfer audit"),
        (
            "heavy_io",
            {"limit": 25, "mode": "enforce", "unit": "cpu"},
            "heavy_io.unit",
        ),
    ],
)
def test_resolved_runtime_controls_fail_closed(
    field: str, value: dict, message: str
) -> None:
    gate = load_gate()

    with pytest.raises(RuntimeError, match=message):
        gate._resolved_runtime_controls({field: value})


def test_terminal_evidence_sync_reports_missing_rule_jsonl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
    }
    binding = {
        "cce_bundle": str(tmp_path / "cce"),
        "namespace": "snakemake-ns",
        "master_job": "cce-master-0123456789abcdef0123",
        "rule_source_dir": "/workspace/wgs/runs/project/batch/evidence/run/rule-status/raw",
        "analysis_log_source": "/workspace/wgs/runs/project/batch/analysis.log",
    }
    monkeypatch.setattr(gate, "CCE_EVIDENCE_ROOT", tmp_path / "evidence")
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )(),
    )

    error = gate._sync_rule_evidence(payload, binding, terminal=True)

    assert error == "Rule event JSONL was not produced"


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


def test_atomic_json_uses_independent_temporary_files_for_concurrent_writers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    destination = tmp_path / "step3_monitor.status.json"
    barrier = threading.Barrier(2)
    original_replace = gate.os.replace

    def synchronized_replace(source, target):
        barrier.wait(timeout=5)
        original_replace(source, target)

    monkeypatch.setattr(gate.os, "replace", synchronized_replace)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(gate._atomic_json, destination, {"writer": writer})
            for writer in ("launcher", "worker")
        ]
        for future in futures:
            future.result(timeout=5)

    assert json.loads(destination.read_text(encoding="utf-8"))["writer"] in {
        "launcher",
        "worker",
    }


def test_stage_status_never_moves_backward_from_running_to_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    request_path = tmp_path / "step3_monitor.json"
    request_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(gate, "_request_path", lambda *_args: request_path)
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "step3_monitor",
    }

    gate._write_status(payload, "running", master_job="cce-master-abc")
    gate._write_status(payload, "accepted")

    status = json.loads(
        request_path.with_suffix(".status.json").read_text(encoding="utf-8")
    )
    assert status["status"] == "running"
    assert status["master_job"] == "cce-master-abc"


def test_async_worker_preserves_retry_generation_in_terminal_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    monkeypatch.setattr(gate, "REQUEST_ROOT", tmp_path)
    payload = {
        "analysis_id": "WGS_20260830_010203_A1B2C3",
        "attempt": 1,
        "stage": "step4_publish",
    }
    request_dir = tmp_path / payload["analysis_id"] / "attempt-1"
    request_dir.mkdir(parents=True)
    gate._atomic_json(
        request_dir / "step4_publish.status.json",
        {
            "schema_version": gate.STAGE_STATUS_SCHEMA,
            **payload,
            "status": "accepted",
            "message": "",
            "updated_at": "2026-09-02T01:00:00+00:00",
            "retry_no": 3,
        },
    )
    monkeypatch.setattr(gate, "run_stage", lambda _payload: None)

    assert gate._run_worker(payload) == 0
    status = json.loads(
        (request_dir / "step4_publish.status.json").read_text(encoding="utf-8")
    )
    assert status["status"] == "success"
    assert status["retry_no"] == 3


def test_stage_progress_updates_preserve_retry_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    request_path = tmp_path / "step5_download.json"
    request_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(gate, "_request_path", lambda *_args: request_path)
    payload = {
        "analysis_id": "WGS_20260830_010203_A1B2C3",
        "attempt": 1,
        "stage": "step5_download",
    }

    gate._write_status(payload, "accepted", retry_no=3)
    gate._write_status(payload, "running", transfer={"bytes_done": 10})
    gate._write_status(payload, "success")

    status = json.loads(
        request_path.with_suffix(".status.json").read_text(encoding="utf-8")
    )
    assert status["status"] == "success"
    assert status["retry_no"] == 3
    assert status["transfer"] == {"bytes_done": 10}


def test_async_stage_publishes_accepted_before_spawning_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = load_gate()
    request_path = tmp_path / "step3_monitor.json"
    request_path.write_text("{}\n", encoding="utf-8")
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "step3_monitor",
    }
    events: list[str] = []

    monkeypatch.setattr(gate, "_request_path", lambda *_args: request_path)
    monkeypatch.setattr(gate, "_truthy", lambda _name: True)
    monkeypatch.setattr(gate, "_boot_id", lambda: "boot-id")
    monkeypatch.setattr(gate, "_process_start_time", lambda _pid: "123")
    monkeypatch.setattr(
        gate,
        "_write_status",
        lambda _payload, status, *_args, **_kwargs: events.append(status),
    )

    class FakeProcess:
        pid = 4321

    def fake_popen(*_args, **_kwargs):
        events.append("spawn")
        return FakeProcess()

    monkeypatch.setattr(gate.subprocess, "Popen", fake_popen)

    gate.start_async_stage(payload)

    assert events[:2] == ["accepted", "spawn"]


def test_step3_worker_does_not_publish_generic_running_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = load_gate()
    statuses: list[str] = []
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "step3_monitor",
    }
    monkeypatch.setattr(gate, "run_stage", lambda _payload: None)
    monkeypatch.setattr(
        gate,
        "_write_status",
        lambda _payload, status, *_args, **_kwargs: statuses.append(status),
    )

    assert gate._run_worker(payload) == 0
    assert statuses == ["success"]


def test_step3_terminal_success_is_written_with_frozen_master_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = load_gate()
    cce_bundle = tmp_path / "cce"
    cce_bundle.mkdir()
    (cce_bundle / "Step3_status.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (cce_bundle / "RESOLVED_PROFILE.yaml").write_text(
        "run_label: cce-run-0123456789abcdef\n", encoding="utf-8"
    )
    payload = {
        "analysis_id": "WGS_20260826_010203_A1B2C3",
        "attempt": 1,
        "stage": "step3_monitor",
    }
    binding = {
        "cce_bundle": str(cce_bundle),
        "master_job": "cce-master-0123456789abcdef0123",
        "namespace": "snakemake-ns",
    }
    writes: list[tuple[str, dict]] = []

    monkeypatch.setattr(gate, "_load_binding", lambda _payload: binding)
    monkeypatch.setattr(
        gate,
        "_sync_rule_evidence",
        lambda _payload, _binding, *, terminal: None,
    )
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result",
            (),
            {
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "master_state": "SUCCEEDED",
                        "normal": True,
                        "completed": 209,
                        "total": 209,
                        "percent": 100.0,
                        "message": "complete",
                    }
                ),
                "stderr": "",
            },
        )(),
    )
    monkeypatch.setattr(
        gate,
        "_write_status",
        lambda _payload, status, _message="", **details: writes.append(
            (status, details)
        ),
    )

    gate._monitor_step3(payload)

    assert len(writes) == 1
    status, details = writes[0]
    assert status == "success"
    assert details["master_job"] == "cce-master-0123456789abcdef0123"
    assert details["namespace"] == "snakemake-ns"
    assert details["run_label"] == "cce-run-0123456789abcdef"
    assert details["master"]["master_state"] == "SUCCEEDED"
    assert details["monitoring_health"] == "healthy"


def test_node005_transfer_wrapper_remains_retired() -> None:
    assert not (ROOT / "node005_obs_transfer.py").exists()
