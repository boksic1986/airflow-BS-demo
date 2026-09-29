"""Focused WGS gate assertions for the UE-02 native executor handoff."""

import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest


SCRIPTS = Path(__file__).parents[1]


def _gate():
    if sys.platform == "win32" and "fcntl" not in sys.modules:
        sys.modules["fcntl"] = types.SimpleNamespace(
            LOCK_EX=1, flock=lambda *_args, **_kwargs: None
        )
    spec = importlib.util.spec_from_file_location(
        "wgs_native_stage_gate_test", SCRIPTS / "wgs_runtime_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("stage", ["step2_master", "step6_materialize"])
def test_new_marker_selects_native_submit_for_former_synchronous_stages(
    stage, monkeypatch, capsys
):
    gate = _gate()
    analysis_id = "WGS_20260929_010203_A1B2C3"
    payload = {
        "analysis_id": analysis_id,
        "attempt": 1,
        "stage": stage,
        "generation": 2,
        "execution_id": "registered-execution",
        "request_hash": "a" * 64,
        "stage_execution": {"protocol": "cce.stage-execution.v1"},
    }
    selected = []
    monkeypatch.syspath_prepend(str(SCRIPTS))
    monkeypatch.delenv("SSH_ORIGINAL_COMMAND", raising=False)
    monkeypatch.setenv("WGS_RELEASE_RUNTIMES_JSON", "{}")
    monkeypatch.setattr(sys, "argv", ["wgs_runtime_gate.py", "wgs-runtime", analysis_id, "1", stage])
    monkeypatch.setattr(gate, "load_request", lambda *_args: payload)
    monkeypatch.setattr(gate, "start_native_stage", lambda value: selected.append(value) or {
        "status": "accepted", "stage": stage, "generation": 2,
        "execution_id": "registered-execution",
    })
    monkeypatch.setattr(gate, "_run_synchronous_stage", lambda _value: pytest.fail("legacy worker selected"))

    assert gate.main() == 0
    assert selected == [payload]
    assert json.loads(capsys.readouterr().out)["status"] == "accepted"


def test_native_generation_archives_business_status_without_moving_open_worker_log(
    tmp_path, monkeypatch
):
    gate = _gate()
    request_path = tmp_path / "step1_upload.json"
    request_path.write_text("{}", encoding="utf-8")
    payload = {
        "analysis_id": "WGS_20260929_010203_A1B2C3",
        "attempt": 1,
        "stage": "step1_upload",
        "generation": 2,
        "execution_id": "new-execution",
        "request_hash": "b" * 64,
        "orchestration_contract_version": 2,
        "stage_execution": {"protocol": "cce.stage-execution.v1"},
    }
    request_path.with_suffix(".status.json").write_text(
        json.dumps({
            "orchestration_contract_version": 2,
            "generation": 1,
            "execution_id": "old-execution",
            "request_hash": "a" * 64,
            "status": "success",
        }),
        encoding="utf-8",
    )
    worker_log = request_path.with_suffix(".worker.log")
    worker_log.write_text("native worker already opened this log\n", encoding="utf-8")
    monkeypatch.setattr(gate, "_request_path", lambda *_args: request_path)
    monkeypatch.setattr(gate, "load_request", lambda *_args: payload)
    runs = []
    monkeypatch.setattr(gate, "_run_worker", lambda value: runs.append(value))
    ref = types.SimpleNamespace(
        pipeline="wgs", analysis_id=payload["analysis_id"], attempt=1,
        stage="step1_upload", execution_id="new-execution",
        stage_generation=2, request_hash="b" * 64,
    )

    gate._native_business_stage(ref)

    history = tmp_path / "history" / "step1_upload" / "generation-1"
    assert (history / "status.json").is_file()
    assert not (history / "worker.log").exists()
    assert worker_log.read_text(encoding="utf-8") == "native worker already opened this log\n"
    status = json.loads(request_path.with_suffix(".status.json").read_text(encoding="utf-8"))
    assert (status["execution_id"], status["generation"], status["status"], status["retry_no"]) == (
        "new-execution", 2, "accepted", 1,
    )
    assert runs == [payload]


def test_step4_expired_duplicate_reaches_native_submit_without_outer_deadline(
    monkeypatch,
):
    gate = _gate()
    payload = {
        "analysis_id": "WGS_20260929_010203_A1B2C3",
        "attempt": 1,
        "stage": "step4_publish",
        "generation": 1,
        "execution_id": "registered-execution",
        "request_hash": "a" * 64,
        "publish_dispatch_version": 1,
        "publish_deadline": "2020-01-01T00:00:00+00:00",
        "stage_execution": {"protocol": "cce.stage-execution.v1"},
    }
    registered = []
    submitted = []
    monkeypatch.setattr(gate, "_truthy", lambda _name: True)
    monkeypatch.setitem(sys.modules, "cce_publish_recovery", types.SimpleNamespace(
        registered_publish=lambda value, *, gate, pipeline: registered.append(
            (value, gate, pipeline)
        ),
        require_publish_deadline=lambda _value: pytest.fail(
            "deadline was checked before native launch fencing"
        ),
    ))
    monkeypatch.setattr(gate, "_native_stage_adapter", lambda: types.SimpleNamespace(
        submit_registered_stage=lambda value, *, gate, pipeline: submitted.append(
            (value, gate, pipeline)
        ) or types.SimpleNamespace(
            state="running",
            to_dict=lambda: {"schema": "cce.stage-execution.snapshot.v1", "state": "running"},
        ),
    ))

    result = gate.start_native_stage(payload)

    assert registered == [(payload, gate, "wgs")]
    assert submitted == [(payload, gate, "wgs")]
    assert result == {"schema": "cce.stage-execution.snapshot.v1", "state": "running"}


def test_explicit_null_marker_never_enters_legacy_launcher(monkeypatch):
    gate = _gate()
    analysis_id = "WGS_20260929_010203_A1B2C3"
    payload = {"analysis_id": analysis_id, "attempt": 1,
               "stage": "step1_upload", "stage_execution": None}
    monkeypatch.syspath_prepend(str(SCRIPTS))
    monkeypatch.delenv("SSH_ORIGINAL_COMMAND", raising=False)
    monkeypatch.setenv("WGS_RELEASE_RUNTIMES_JSON", "{}")
    monkeypatch.setattr(sys, "argv", ["wgs_runtime_gate.py", "wgs-runtime",
                                          analysis_id, "1", "step1_upload"])
    monkeypatch.setattr(gate, "load_request", lambda *_args: payload)
    monkeypatch.setattr(gate, "start_async_stage", lambda _value: pytest.fail(
        "legacy launcher was selected"))
    with pytest.raises(ValueError, match="unsupported WGS stage execution protocol"):
        gate.main()


def test_ordinary_step4_native_submit_does_not_require_publish_opt_in(monkeypatch):
    gate = _gate()
    payload = {"analysis_id": "WGS_20260929_010203_A1B2C3", "attempt": 1,
               "stage": "step4_publish", "generation": 1,
               "execution_id": "ordinary-step4", "request_hash": "a" * 64,
               "stage_execution": {"protocol": "cce.stage-execution.v1"}}
    monkeypatch.setattr(gate, "_truthy", lambda _name: True)
    monkeypatch.setattr(gate, "_native_stage_adapter", lambda: types.SimpleNamespace(
        submit_registered_stage=lambda *_args, **_kw: types.SimpleNamespace(
            state="accepted", to_dict=lambda: {"state": "accepted"})))
    assert gate.start_native_stage(payload)["state"] == "accepted"
