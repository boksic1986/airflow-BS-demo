"""New GATK requests must enter one native dispatcher and fail closed on unknown."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

def load_gate():
    path = Path(__file__).parents[1] / "gatk_runtime_gate.py"
    spec = importlib.util.spec_from_file_location("gatk_runtime_gate_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_marked_stage_unknown_never_falls_back_to_legacy_worker(tmp_path, monkeypatch):
    gate = load_gate()
    monkeypatch.setitem(sys.modules, gate.__name__, gate)
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(tmp_path))
    analysis_id = "GATK_20260929_000000_AAAAAA"
    request = tmp_path / analysis_id / "attempt-1" / "step1_upload.request.json"
    request.parent.mkdir(parents=True)
    payload = {
        "pipeline": "gatk",
        "analysis_id": analysis_id,
        "attempt": 1,
        "stage": "step1_upload",
        "generation": 1,
        "execution_id": f"{analysis_id}-a1-step1_upload-g1",
        "request_hash": "a" * 64,
        "orchestration_contract_version": 2,
        "stage_execution": {"protocol": "cce.stage-execution.v1"},
    }
    request.write_text(json.dumps(payload), encoding="utf-8")

    submissions = []

    def submit(value, *, gate, pipeline):
        submissions.append((value, pipeline))
        return SimpleNamespace(state="unknown")

    monkeypatch.setattr(
        gate,
        "_stage_execution_adapter",
        lambda: SimpleNamespace(submit_registered_stage=submit),
    )
    monkeypatch.setattr(
        gate,
        "_dispatch_lock",
        lambda *args, **kwargs: pytest.fail("legacy dispatcher lock was entered"),
    )
    monkeypatch.setattr(
        gate.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("legacy worker was spawned"),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["gatk_runtime_gate.py", "gatk-runtime", analysis_id, "1", "step1_upload", "1"],
    )
    with pytest.raises(SystemExit, match="requires reconciliation: unknown"):
        gate.main()
    with pytest.raises(RuntimeError, match="requires its native worker"):
        gate._execute(analysis_id, 1, "step1_upload", 1)

    assert submissions == [(payload, "gatk")]
    assert not request.with_suffix(".worker.state.json").exists()
    assert not request.with_suffix(".status.json").exists()


def test_marked_step4_reattaches_after_original_deadline(tmp_path, monkeypatch):
    gate = load_gate()
    monkeypatch.setitem(sys.modules, gate.__name__, gate)
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(tmp_path))
    analysis_id = "GATK_20260929_000000_AAAAAA"
    request = tmp_path / analysis_id / "attempt-1" / "step4_publish.request.json"
    request.parent.mkdir(parents=True)
    payload = {
        "pipeline": "gatk",
        "analysis_id": analysis_id,
        "attempt": 1,
        "stage": "step4_publish",
        "generation": 1,
        "execution_id": f"{analysis_id}-a1-step4_publish-g1",
        "request_hash": "b" * 64,
        "orchestration_contract_version": 2,
        "publish_dispatch_version": 1,
        "publish_deadline": "2020-01-01T00:00:00+00:00",
        "stage_execution": {"protocol": "cce.stage-execution.v1"},
    }
    request.write_text(json.dumps(payload), encoding="utf-8")

    calls = []

    def registered_publish(value, *, gate, pipeline):
        calls.append(("registered", value, pipeline))

    def submit(value, *, gate, pipeline):
        calls.append(("submitted", value, pipeline))
        return SimpleNamespace(state="running")

    monkeypatch.setitem(
        sys.modules,
        "cce_publish_recovery",
        SimpleNamespace(
            registered_publish=registered_publish,
            require_publish_deadline=lambda value: pytest.fail(
                "outer Step4 deadline check blocked native reattachment"
            ),
        ),
    )
    monkeypatch.setattr(
        gate,
        "_stage_execution_adapter",
        lambda: SimpleNamespace(submit_registered_stage=submit),
    )

    assert gate.start(analysis_id, 1, "step4_publish", 1, expected_hash="b" * 64) == {
        "status": "running", "stage": "step4_publish", "generation": 1,
    }
    assert calls == [
        ("registered", payload, "gatk"),
        ("submitted", payload, "gatk"),
    ]
    with pytest.raises(ValueError, match="superseded"):
        gate.start(analysis_id, 1, "step4_publish", 1, expected_hash="c" * 64)
    assert len(calls) == 2


def test_ordinary_step4_native_submit_does_not_require_publish_opt_in(tmp_path, monkeypatch):
    gate = load_gate()
    monkeypatch.setitem(sys.modules, gate.__name__, gate)
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(tmp_path))
    analysis_id = "GATK_20260929_000000_AAAAAA"
    request = tmp_path / analysis_id / "attempt-1" / "step4_publish.request.json"
    request.parent.mkdir(parents=True)
    payload = {"pipeline": "gatk", "analysis_id": analysis_id, "attempt": 1,
               "stage": "step4_publish", "generation": 1,
               "execution_id": f"{analysis_id}-a1-step4_publish-g1",
               "request_hash": "a" * 64, "orchestration_contract_version": 2,
               "stage_execution": {"protocol": "cce.stage-execution.v1"}}
    request.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(gate, "_stage_execution_adapter", lambda: SimpleNamespace(
        submit_registered_stage=lambda *_args, **_kw: SimpleNamespace(state="accepted")))
    assert gate.start(analysis_id, 1, "step4_publish", 1) == {
        "status": "accepted", "stage": "step4_publish", "generation": 1,
    }
