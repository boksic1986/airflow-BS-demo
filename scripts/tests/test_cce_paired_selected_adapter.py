"""The registered child imports only its trusted, selected pipeline gate."""

import builtins
import importlib
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("pipeline", ["wgs", "gatk"])
@pytest.mark.parametrize("module_name", ["scripts.cce_paired_runtime", "cce_paired_runtime"])
def test_registered_stage_imports_only_selected_gate(
    tmp_path, monkeypatch, pipeline, module_name
):
    if module_name == "cce_paired_runtime":
        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    paired = importlib.import_module(module_name)

    gate_prefix = "scripts." if paired.__package__ else ""
    selected = importlib.import_module(f"{gate_prefix}{pipeline}_runtime_gate")
    forbidden = "gatk_runtime_gate" if pipeline == "wgs" else "wgs_runtime_gate"
    request_path = tmp_path / "step5_download.request.json"
    payload = {
        "analysis_id": "SYNTHETIC01",
        "attempt": 1,
        "stage": "step5_download",
        "execution_id": "synthetic-execution-1",
        "generation": 1,
        "request_hash": "a" * 64,
    }
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(selected, "_request_path", lambda *_: request_path)
    monkeypatch.setattr(selected, "_load_binding", lambda _: {"synthetic": True})

    calls = []

    def downstream(value, *, binding, gate, pipeline, materialize):
        calls.append((value, binding, gate, pipeline, materialize))
        return {}

    monkeypatch.setattr(paired, "downstream_registered", downstream)
    original_import = builtins.__import__

    def selected_import(name, globals=None, locals=None, fromlist=(), level=0):
        if forbidden in name or forbidden in (fromlist or ()):
            raise AssertionError("unselected pipeline gate was imported")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", selected_import)
    paired.run_registered_stage([
        pipeline, payload["analysis_id"], "1", payload["stage"],
        payload["execution_id"], "1", payload["request_hash"],
    ])

    assert len(calls) == 1
    assert calls[0][:4] == (payload, {"synthetic": True}, selected, pipeline)
