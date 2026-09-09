import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml


ROOT = Path(__file__).parents[1]


def load_gate():
    spec = importlib.util.spec_from_file_location(
        "gatk_runtime_gate_test", ROOT / "gatk_runtime_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_forced_command_loads_runtime_from_its_install_directory() -> None:
    source = (ROOT / "gatk_runtime_forced_command.sh").read_text(encoding="utf-8")

    assert 'script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"' in source
    assert 'config_dir="${GATK_HOST_CONFIG_DIR:-${script_dir}}"' in source
    assert "/home/ctapa" not in source


def test_cli_reports_a_missing_request_without_a_traceback(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "gatk_runtime_gate.py"),
            "gatk-runtime",
            "GATK_20260908_120000_A1B2C3",
            "1",
            "prepare",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "GATK_RUNTIME_REQUEST_ROOT": str(tmp_path)},
    )

    assert completed.returncode == 1
    assert "runtime request does not exist" in completed.stderr
    assert "Traceback" not in completed.stderr


def test_prepare_binding_exposes_only_frozen_cce_evidence_contract(tmp_path: Path) -> None:
    gate = load_gate()
    bundle = tmp_path / "run" / "cce"
    bundle.mkdir(parents=True)
    (bundle / "BATCH_RUNTIME.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 3,
                "identity": {
                    "project": "WES_Clinical",
                    "batch": "20260908A",
                    "run_id": "GATK_20260908_120000_A1B2C3-a1",
                },
                "kubernetes": {
                    "namespace": "snakemake-ns",
                    "master_job": "cce-master-0123456789abcdef0123",
                },
                "paths": {"run_dir": "/workspace/gatk-cloud/runs/WES_Clinical/20260908A"},
            }
        ),
        encoding="utf-8",
    )
    (bundle / "master-job.yaml").write_text(
        yaml.safe_dump(
            {
                "metadata": {"labels": {"cce.biosan.cn/run-id": "cce-run-0123456789abcdef"}},
                "spec": {"template": {"spec": {"containers": [{}], "volumes": []}}},
            }
        ),
        encoding="utf-8",
    )
    payload = {
        "kind": "gatk-airflow-prepare",
        "analysis_id": "GATK_20260908_120000_A1B2C3",
        "attempt": 1,
        "output_root": str(tmp_path / "run"),
        "profile_id": "gatk-scmc-v7.6.0",
        "profile_revision": "bd04f6d",
    }

    binding = gate._write_binding(payload)

    assert binding["run_label"] == "cce-run-0123456789abcdef"
    assert binding["rule_source_dir"].endswith(
        "/evidence/GATK_20260908_120000_A1B2C3-a1/rule-status/raw"
    )
    assert binding["evidence_output"].endswith(
        "/GATK_20260908_120000_A1B2C3/attempt-1"
    )


def test_evidence_bridge_uses_cce_label_and_terminal_mode(tmp_path: Path, monkeypatch) -> None:
    gate = load_gate()
    monkeypatch.setattr(gate, "EVIDENCE_BRIDGE", Path("/approved/wgs_evidence_bridge.py"))
    monkeypatch.setattr(gate, "GATK_EVIDENCE_ROOT", tmp_path / "evidence")
    binding = {
        "namespace": "snakemake-ns",
        "master_job": "cce-master-0123456789abcdef0123",
        "cce_bundle": "/runtime/gatk/run/cce",
        "rule_source_dir": "/workspace/run/evidence/id/rule-status/raw",
        "analysis_log_source": "/workspace/run/evidence/id/analysis.log",
        "run_label": "cce-run-0123456789abcdef",
        "evidence_output": str(tmp_path / "evidence" / "run"),
    }
    payload = {"analysis_id": "GATK_20260908_120000_A1B2C3", "attempt": 1}

    command = gate._bridge_command(payload, binding, terminal=True)

    assert "--run-label-key" in command
    assert command[command.index("--run-label-key") + 1] == "cce.biosan.cn/run-id"
    assert command[-1] == "--terminal"


def test_start_is_idempotent_for_same_generation(tmp_path: Path, monkeypatch) -> None:
    gate = load_gate()
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(tmp_path))
    analysis_id = "GATK_20260908_120000_A1B2C3"
    request = tmp_path / analysis_id / "attempt-1" / "step1_upload.request.json"
    request.parent.mkdir(parents=True)
    request.write_text(
        json.dumps(
            {
                "analysis_id": analysis_id,
                "attempt": 1,
                "generation": 1,
                "stage": "step1_upload",
                "orchestration_contract_version": 2,
                "execution_id": f"{analysis_id}-a1-step1_upload-g1",
                "request_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    request.with_suffix(".status.json").write_text(
        json.dumps({"status": "success", "generation": 1}), encoding="utf-8"
    )

    assert gate.start(analysis_id, 1, "step1_upload")["status"] == "success"


def test_prepare_retry_starts_worker_for_new_generation(
    tmp_path: Path, monkeypatch
) -> None:
    gate = load_gate()
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(tmp_path))
    analysis_id = "GATK_20260908_120000_A1B2C3"
    request = tmp_path / analysis_id / "attempt-1" / "prepare.request.json"
    request.parent.mkdir(parents=True)
    request.write_text(
        json.dumps(
            {
                "kind": "gatk-airflow-prepare",
                "analysis_id": analysis_id,
                "attempt": 1,
                "generation": 1,
                "request_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    request.with_suffix(".status.json").write_text(
        json.dumps({"status": "failed", "generation": 1}), encoding="utf-8"
    )
    commands: list[list[str]] = []
    monkeypatch.setattr(
        gate.subprocess,
        "Popen",
        lambda command, **_kwargs: commands.append(command),
    )

    result = gate.start(analysis_id, 1, "prepare", generation=2)

    assert result == {"status": "accepted", "stage": "prepare", "generation": 2}
    assert commands[0][-1] == "2"


def test_prepare_failure_persists_subprocess_stderr(tmp_path: Path, monkeypatch) -> None:
    gate = load_gate()
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(tmp_path))
    request = tmp_path / "prepare.request.json"
    payload = {
        "analysis_id": "GATK_20260908_120000_A1B2C3",
        "attempt": 1,
        "generation": 2,
        "request_hash": "a" * 64,
    }
    statuses = []
    monkeypatch.setattr(gate, "_load", lambda *_args: (request, payload))
    monkeypatch.setattr(gate, "_write_status", lambda *args, **_kwargs: statuses.append(args))
    monkeypatch.setattr(gate, "_prepare", lambda _payload: ["python", "handoff.py"])
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(
                1,
                ["python", "handoff.py"],
                output="",
                stderr="ModuleNotFoundError: missing handoff module\n",
            )
        ),
    )

    with pytest.raises(subprocess.CalledProcessError):
        gate._execute(payload["analysis_id"], 1, "prepare", 2)

    assert statuses[-1][2] == "failed"
    assert statuses[-1][3] == "ModuleNotFoundError: missing handoff module"


def test_step4_waits_for_backend_export_to_become_visible(monkeypatch) -> None:
    gate = load_gate()
    attempts = []

    def fake_run(*args, **kwargs):
        attempts.append((args, kwargs))
        if len(attempts) == 1:
            return SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="SFS backend export is not ready in OBS; retry Step4\n",
            )
        return SimpleNamespace(returncode=0, stdout="published\n", stderr="")

    sleeps = []
    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    monkeypatch.setattr(gate.time, "sleep", sleeps.append)
    monkeypatch.setenv("GATK_PUBLISH_WAIT_SECONDS", "120")
    monkeypatch.setenv("GATK_PUBLISH_POLL_SECONDS", "7")

    completed = gate._run_frozen_stage(
        ["bash", "/approved/Step4_publish_results.sh"],
        stage="step4_publish",
        environment={"PATH": "/usr/bin"},
    )

    assert completed.returncode == 0
    assert len(attempts) == 2
    assert sleeps == [7]


def test_parse_step3_accepts_cce_pipeline_083_text_status() -> None:
    gate = load_gate()
    output = """run_state=UNAVAILABLE attempt_start=2026-09-09T11:08:28Z
master_state=RUNNING normal=true
bioinformatics_stage=MarkDuplicates
progress=24/184 remaining=160 (13.0%)
current_rule_or_group=sentieon_mapping,gatk_mark_duplicates
last_completed_rule=sentieon_mapping
message=Master and Snakemake are running normally
"""

    state = gate._parse_step3(output)

    assert state == {
        "master_state": "RUNNING",
        "completed": 24,
        "total": 184,
        "percent": 13.0,
        "current_rule": "sentieon_mapping,gatk_mark_duplicates",
        "bioinformatics_stage": "MarkDuplicates",
        "message": "Master and Snakemake are running normally",
    }


def test_step4_does_not_retry_an_unrelated_failure(monkeypatch) -> None:
    gate = load_gate()
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="", stderr="permission denied\n"
        ),
    )

    with pytest.raises(RuntimeError, match="permission denied"):
        gate._run_frozen_stage(
            ["bash", "/approved/Step4_publish_results.sh"],
            stage="step4_publish",
            environment={"PATH": "/usr/bin"},
        )


def test_step6_materializes_to_approved_gatk_result_root(
    tmp_path: Path, monkeypatch
) -> None:
    gate = load_gate()
    analysis_id = "GATK_20260908_120000_A1B2C3"
    request_root = tmp_path / "requests"
    result_root = tmp_path / "results"
    runtime_workdir = tmp_path / "runtime" / analysis_id / "attempt-1"
    bundle = runtime_workdir / "cce"
    bundle.mkdir(parents=True)
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(request_root))
    monkeypatch.setenv("GATK_RESULT_ROOT", str(result_root))

    prepare = request_root / analysis_id / "attempt-1" / "prepare.request.json"
    prepare.parent.mkdir(parents=True)
    expected_result = result_root / "20260908A" / analysis_id
    prepare.write_text(
        json.dumps(
            {
                "analysis_id": analysis_id,
                "attempt": 1,
                "batch": "20260908A",
                "result_root": str(expected_result),
            }
        ),
        encoding="utf-8",
    )
    (bundle / "BATCH_RUNTIME.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 3,
                "identity": {
                    "project": "WES_Clinical",
                    "batch": "20260908A",
                    "run_id": f"{analysis_id}-a1",
                },
                "tools": {"zstd_bin": "/approved/zstd"},
                "permissions": {"directory_mode": "2770", "file_mode": "0660"},
            }
        ),
        encoding="utf-8",
    )
    (bundle / "cce_shared_permissions.py").write_text(
        "DELIVERY_SOURCE = 'frozen-bundle'\n",
        encoding="utf-8",
    )
    (bundle / "cce_delivery.py").write_text(
        "import json\n"
        "from cce_shared_permissions import DELIVERY_SOURCE\n"
        "from pathlib import Path\n"
        "def materialize_results(download_root, batch_root, batch, *, permissions, **kwargs):\n"
        "    Path(batch_root).mkdir(parents=True)\n"
        "    (Path(batch_root) / 'call.json').write_text(json.dumps({\n"
        "        'download_root': str(download_root), 'batch': batch,\n"
        "        'delivery_source': DELIVERY_SOURCE, 'permissions': permissions, **kwargs\n"
        "    }))\n",
        encoding="utf-8",
    )
    payload = {
        "analysis_id": analysis_id,
        "attempt": 1,
        "runtime_workdir": str(runtime_workdir),
    }

    assert gate._materialize(payload) == expected_result.resolve()
    call = json.loads((expected_result / "call.json").read_text(encoding="utf-8"))
    assert call["batch"] == "20260908A"
    assert call["run_id"] == f"{analysis_id}-a1"
    assert call["project_name"] == "WES_Clinical"
    assert call["delivery_source"] == "frozen-bundle"
    assert call["permissions"] == {"directory_mode": "2770", "file_mode": "0660"}


def test_step6_rejects_result_root_outside_configured_root(
    tmp_path: Path, monkeypatch
) -> None:
    gate = load_gate()
    analysis_id = "GATK_20260908_120000_A1B2C3"
    request_root = tmp_path / "requests"
    prepare = request_root / analysis_id / "attempt-1" / "prepare.request.json"
    prepare.parent.mkdir(parents=True)
    prepare.write_text(
        json.dumps(
            {
                "analysis_id": analysis_id,
                "attempt": 1,
                "batch": "20260908A",
                "result_root": str(tmp_path / "outside" / analysis_id),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(request_root))
    monkeypatch.setenv("GATK_RESULT_ROOT", str(tmp_path / "approved"))

    try:
        gate._materialize_result_root({"analysis_id": analysis_id, "attempt": 1})
    except ValueError as exc:
        assert "approved delivery location" in str(exc)
    else:
        raise AssertionError("unsafe GATK result root was accepted")
