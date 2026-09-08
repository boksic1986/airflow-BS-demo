import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

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


def test_prepare_runs_as_module_from_frozen_release_root(
    tmp_path: Path, monkeypatch
) -> None:
    gate = load_gate()
    repository = tmp_path / "release"
    entrypoint = repository / "scripts" / "airflow_handoff.py"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.write_text("", encoding="utf-8")
    monkeypatch.setenv("GATK_REPOSITORY_ROOT", str(repository))
    monkeypatch.setenv("GATK_PYTHON", "/approved/python")
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(tmp_path / "requests"))
    payload = {
        "analysis_id": "GATK_20260908_120000_A1B2C3",
        "attempt": 1,
    }

    command, cwd = gate._prepare(payload)

    assert command[:3] == ["/approved/python", "-m", "scripts.airflow_handoff"]
    assert cwd == repository.resolve()


def test_retry_replaces_failed_sidecar_before_worker_starts(
    tmp_path: Path, monkeypatch
) -> None:
    gate = load_gate()
    analysis_id = "GATK_20260908_120000_A1B2C3"
    request = tmp_path / analysis_id / "attempt-1" / "prepare.request.json"
    request.parent.mkdir(parents=True)
    request.write_text(
        json.dumps(
            {
                "analysis_id": analysis_id,
                "attempt": 1,
                "generation": 1,
                "stage": "prepare",
                "request_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    status = request.with_suffix(".status.json")
    status.write_text(json.dumps({"status": "failed", "generation": 1}), encoding="utf-8")
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(tmp_path))
    monkeypatch.setattr(gate.subprocess, "Popen", lambda *_args, **_kwargs: object())

    result = gate.start(analysis_id, 1, "prepare")

    assert result["status"] == "accepted"
    assert json.loads(status.read_text(encoding="utf-8"))["status"] == "accepted"


def test_step1_progress_uses_frozen_manifest_totals(
    tmp_path: Path, monkeypatch
) -> None:
    gate = load_gate()
    analysis_id = "GATK_20260908_120000_A1B2C3"
    runtime = tmp_path / "runtime" / analysis_id / "attempt-1"
    bundle = runtime / "cce"
    bundle.mkdir(parents=True)
    first = tmp_path / "first.fq.gz"
    second = tmp_path / "second.fq.gz"
    first.write_bytes(b"a" * 10)
    second.write_bytes(b"b" * 30)
    (bundle / "BATCH_RUNTIME.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 3,
                "transfer_sources": [
                    {"source": str(first), "target": "S1.R1.fq.gz"},
                    {"source": str(second), "target": "S1.R2.fq.gz"},
                ],
            }
        ),
        encoding="utf-8",
    )
    spool = tmp_path / "spool"
    monkeypatch.setenv("GATK_TRANSFER_SPOOL_ROOT", str(spool))
    payload = {
        "analysis_id": analysis_id,
        "attempt": 1,
        "generation": 2,
        "stage": "step1_upload",
        "execution_id": f"{analysis_id}-a1-step1_upload-g2",
        "request_hash": "b" * 64,
        "runtime_workdir": str(runtime),
    }
    progress_root = gate._transfer_progress_root(payload)
    progress_root.mkdir(parents=True)
    (progress_root / "one.json").write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.transfer-progress.v1",
                "state": "running",
                "bytes_total": 10,
                "bytes_done": 4,
                "files_total": 1,
                "files_done": 0,
                "speed_bytes_per_second": 2,
                "heartbeat_at": "2026-09-08T12:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    progress = gate._aggregate_transfer_progress(payload)

    assert progress["bytes_total"] == 40
    assert progress["bytes_done"] == 4
    assert progress["files_total"] == 2
    assert progress["files_done"] == 0
    assert progress["generation"] == 2
    assert json.loads((progress_root / "progress.json").read_text())["bytes_total"] == 40


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
            }
        ),
        encoding="utf-8",
    )
    (bundle / "cce_delivery.py").write_text(
        "import json\n"
        "from pathlib import Path\n"
        "def materialize_results(download_root, batch_root, batch, **kwargs):\n"
        "    Path(batch_root).mkdir(parents=True)\n"
        "    (Path(batch_root) / 'call.json').write_text(json.dumps({\n"
        "        'download_root': str(download_root), 'batch': batch, **kwargs\n"
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
