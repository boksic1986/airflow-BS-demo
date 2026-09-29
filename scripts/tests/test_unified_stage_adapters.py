"""Focused UE-04 gate evidence for the shared stage execution client."""

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


SCRIPTS = Path(__file__).parents[1]
ANALYSIS_WGS = "WGS_20260929_010203_A1B2C3"
ANALYSIS_GATK = "GATK_20260929_010203_A1B2C3"
PROTOCOL = {"protocol": "cce.stage-execution.v1"}


def _gate(name: str):
    spec = importlib.util.spec_from_file_location(f"ue04_{name}", SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _snapshot(pipeline: str, payload: dict, state: str) -> SimpleNamespace:
    wire = {
        "schema": "cce.stage-execution.snapshot.v1",
        "execution_ref": {
            "protocol": "cce.stage-execution.v1",
            "pipeline": pipeline,
            "analysis_id": payload["analysis_id"],
            "attempt": payload["attempt"],
            "stage": payload["stage"],
            "execution_id": payload["execution_id"],
            "stage_generation": payload["generation"],
            "request_hash": payload["request_hash"],
            "registration_sha256": "b" * 64,
        },
        "state": state,
        "evidence_ref": None,
        "runtime_identity": None,
        "compute_identity": {"compute_generation": None, "master_uid": None},
        "observation_health": "degraded" if state == "unknown" else "healthy",
    }
    return SimpleNamespace(state=state, to_dict=lambda: wire)


@pytest.mark.parametrize("stage", ["step2_master", "step6_materialize"])
def test_wgs_migrated_stages_use_shared_execution(stage, monkeypatch):
    gate = _gate("wgs_runtime_gate.py")
    payload = {
        "analysis_id": ANALYSIS_WGS,
        "attempt": 1,
        "stage": stage,
        "generation": 2,
        "execution_id": "wse_synthetic_ue04",
        "request_hash": "a" * 64,
        "stage_execution": PROTOCOL,
    }
    snapshot = _snapshot("wgs", payload, "accepted")
    submissions = []
    monkeypatch.setattr(gate, "_truthy", lambda _name: True)
    monkeypatch.setattr(gate, "_native_stage_adapter", lambda: SimpleNamespace(
        submit_registered_stage=lambda value, *, gate, pipeline: submissions.append(
            (value, pipeline)
        ) or snapshot,
    ))

    assert gate.start_native_stage(payload) == snapshot.to_dict()
    assert submissions == [(payload, "wgs")]


def test_gatk_thin_binding(monkeypatch, capsys):
    gate = _gate("gatk_runtime_gate.py")
    payload = {
        "pipeline": "gatk",
        "analysis_id": ANALYSIS_GATK,
        "attempt": 1,
        "stage": "step1_upload",
        "generation": 1,
        "execution_id": f"{ANALYSIS_GATK}-a1-step1_upload-g1",
        "request_hash": "a" * 64,
        "stage_execution": PROTOCOL,
    }
    snapshot = _snapshot("gatk", payload, "unknown")
    calls = []
    monkeypatch.setattr(gate, "_load", lambda *_args: (Path("synthetic.json"), payload))
    monkeypatch.setattr(gate, "_stage_execution_adapter", lambda: SimpleNamespace(
        submit_registered_stage=lambda value, *, gate, pipeline: calls.append(
            ("submit", value, pipeline)
        ) or snapshot,
        executor_for_registered=lambda value, *, gate, pipeline: (
            SimpleNamespace(observe=lambda ref: calls.append(("observe", ref, pipeline)) or snapshot),
            snapshot.to_dict()["execution_ref"],
            object(),
        ),
    ))

    assert gate.start(ANALYSIS_GATK, 1, "step1_upload", 1) == snapshot.to_dict()
    monkeypatch.setattr(sys, "argv", [
        "gatk_runtime_gate.py", "--native-observe", ANALYSIS_GATK, "1",
        "step1_upload", payload["execution_id"], "1", payload["request_hash"],
    ])
    gate.main()
    assert json.loads(capsys.readouterr().out) == snapshot.to_dict()
    assert [call[0] for call in calls] == ["submit", "observe"]

    monkeypatch.setattr(sys, "argv", [
        "gatk_runtime_gate.py", "--native-observe", ANALYSIS_GATK, "1",
        "step1_upload", payload["execution_id"], "1", "c" * 64,
    ])
    with pytest.raises((ValueError, SystemExit), match="superseded|identity"):
        gate.main()
    assert [call[0] for call in calls] == ["submit", "observe"]


@pytest.mark.parametrize("pipeline", ["wgs", "gatk"])
def test_marked_submit_fences_exact_identity_before_dispatch(pipeline, monkeypatch, capsys):
    gate = _gate(f"{pipeline}_runtime_gate.py")
    analysis_id = ANALYSIS_WGS if pipeline == "wgs" else ANALYSIS_GATK
    payload = {
        "analysis_id": analysis_id,
        "attempt": 1,
        "stage": "step1_upload",
        "generation": 2,
        "execution_id": f"{analysis_id}-a1-step1_upload-g2",
        "request_hash": "a" * 64,
        "stage_execution": PROTOCOL,
    }
    if pipeline == "wgs":
        monkeypatch.syspath_prepend(str(SCRIPTS))
        monkeypatch.delenv("SSH_ORIGINAL_COMMAND", raising=False)
        monkeypatch.setenv("WGS_RELEASE_RUNTIMES_JSON", "{}")
        monkeypatch.setattr(gate, "load_request", lambda *_args: payload)
    else:
        monkeypatch.setattr(gate, "_load", lambda *_args: (Path("synthetic.json"), payload))
    dispatched = []
    result = _snapshot(pipeline, payload, "accepted").to_dict()
    if pipeline == "wgs":
        monkeypatch.setattr(gate, "start_native_stage", lambda value: dispatched.append(value) or result)
    else:
        monkeypatch.setattr(gate, "start", lambda *_args, **_kwargs: dispatched.append(payload) or result)
    command = [
        f"{pipeline}_runtime_gate.py", "--native-submit", analysis_id, "1",
        "step1_upload", payload["execution_id"], "2", payload["request_hash"],
    ]
    monkeypatch.setattr(sys, "argv", command)
    gate.main()
    assert json.loads(capsys.readouterr().out) == result
    assert dispatched == [payload]

    monkeypatch.setattr(sys, "argv", [*command[:-2], "1", command[-1]])
    with pytest.raises((ValueError, SystemExit), match="superseded|identity|generation"):
        gate.main()
    monkeypatch.setattr(sys, "argv", [*command[:-1], "c" * 64])
    with pytest.raises((ValueError, SystemExit), match="superseded|identity"):
        gate.main()
    assert dispatched == [payload]

    legacy_shape = (
        [f"{pipeline}_runtime_gate.py", "wgs-runtime", analysis_id, "1", "step1_upload"]
        if pipeline == "wgs"
        else [f"{pipeline}_runtime_gate.py", "gatk-runtime", analysis_id, "1", "step1_upload", "2"]
    )
    monkeypatch.setattr(sys, "argv", legacy_shape)
    with pytest.raises((ValueError, SystemExit), match="exact --native-submit"):
        gate.main()
    assert dispatched == [payload]


def test_gatk_second_load_cannot_drop_native_marker(monkeypatch):
    gate = _gate("gatk_runtime_gate.py")
    payload = {
        "analysis_id": ANALYSIS_GATK,
        "attempt": 1,
        "stage": "step1_upload",
        "generation": 1,
        "execution_id": f"{ANALYSIS_GATK}-a1-step1_upload-g1",
        "request_hash": "a" * 64,
        "stage_execution": PROTOCOL,
    }
    changed = dict(payload)
    changed.pop("stage_execution")
    loads = iter((payload, changed))
    monkeypatch.setattr(gate, "_load", lambda *_args: (Path("synthetic.json"), next(loads)))
    monkeypatch.setattr(gate, "_dispatch_lock", lambda *_args: pytest.fail("legacy dispatcher selected"))
    monkeypatch.setattr(sys, "argv", [
        "gatk_runtime_gate.py", "--native-submit", ANALYSIS_GATK, "1",
        "step1_upload", payload["execution_id"], "1", payload["request_hash"],
    ])
    with pytest.raises(SystemExit, match="superseded"):
        gate.main()
