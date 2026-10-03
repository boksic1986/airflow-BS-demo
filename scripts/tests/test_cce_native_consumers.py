"""Only the Step4 and paired-consumer branches added for native UE-02."""

import json
from types import SimpleNamespace

import pytest

from scripts import cce_paired_runtime as paired
from scripts import cce_publish_recovery as publish


def _payload(stage="step4_publish"):
    return {
        "analysis_id": "SYNTHETIC_UE02",
        "attempt": 1,
        "stage": stage,
        "execution_id": "SYNTHETIC_UE02-a1-" + stage + "-g1",
        "generation": 1,
        "request_hash": "a" * 64,
        "stage_execution": {"protocol": paired.STAGE_EXECUTION_PROTOCOL},
    }


def test_step4_new_protocol_dispatches_only_selected_native_gate(monkeypatch, tmp_path):
    from scripts import wgs_release_runtime

    payload = _payload()
    path = tmp_path / "step4_publish.request.json"
    calls = []
    gate = SimpleNamespace(
        CCE_PIPELINE_BIN="original",
        load_request=lambda *_: payload,
        start_native_stage=lambda value: calls.append(("native", value)) or {"status": "accepted"},
        start_async_stage=lambda _: pytest.fail("old worker launcher was selected"),
    )
    monkeypatch.setattr(publish, "registered_publish", lambda *_args, **_kw: (path, b"{}"))
    monkeypatch.setattr(
        publish, "require_publish_deadline",
        lambda _value: pytest.fail("native duplicate was rejected before submit"),
    )
    monkeypatch.setattr(wgs_release_runtime, "select_release_runtime", lambda *_args, **_kw: "selected")

    result = publish.publish_dispatch_command(
        ["--publish-dispatch", payload["analysis_id"], "1", "1", payload["request_hash"]],
        gate=gate, pipeline="wgs",
    )

    assert result == {"status": "accepted"}
    assert calls == [("native", payload)]
    assert gate.CCE_PIPELINE_BIN == "selected"


@pytest.mark.parametrize(
    ("native_state", "expected"),
    [("accepted", "running"), ("succeeded", "success"),
     ("failed", "failed"), ("unknown", "uncertain")],
)
def test_step4_observation_uses_native_evidence_when_present(
    monkeypatch, tmp_path, native_state, expected
):
    from scripts import cce_stage_execution_adapter as adapter

    payload = _payload()
    path = tmp_path / "step4_publish.request.json"
    dispatch = path.with_suffix(".stage-execution.dispatch.json")
    dispatch.write_text("{}", encoding="utf-8")
    binding = SimpleNamespace(
        request_path=path, dispatch_path=dispatch, status_path=tmp_path / "terminal.json"
    )
    executor = SimpleNamespace(observe=lambda _: SimpleNamespace(state=native_state))
    monkeypatch.setattr(publish, "registered_publish", lambda *_args, **_kw: (path, b"{}"))
    monkeypatch.setattr(adapter, "executor_for_registered", lambda *_args, **_kw: (executor, "ref", binding))

    assert publish.observe_locked(payload, gate=SimpleNamespace(), pipeline="wgs") == expected


@pytest.mark.parametrize("quiescent", [True, False])
def test_paired_writer_fence_uses_native_terminal_under_both_locks(
    monkeypatch, tmp_path, quiescent
):
    from scripts import cce_stage_execution_adapter as adapter

    payload = _payload("step2_master")
    path = tmp_path / "step2_master.request.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    binding = SimpleNamespace(
        request_path=path,
        dispatch_path=path.with_suffix(".stage-execution.dispatch.json"),
    )
    calls = []

    def writer_quiescent(_ref, *, locks_held):
        calls.append(locks_held)
        return quiescent

    executor = SimpleNamespace(writer_quiescent=writer_quiescent)
    monkeypatch.setattr(adapter, "executor_for_registered", lambda *_args, **_kw: (executor, "ref", binding))
    with paired._exclusive(path.with_suffix(".launch.lock")):
        with paired._exclusive(path.with_suffix(".worker.lock")):
            if quiescent:
                paired._inactive_dispatcher(path, SimpleNamespace(), "wgs")
            else:
                with pytest.raises(RuntimeError, match="native dispatcher is active or uncertain"):
                    paired._inactive_dispatcher(path, SimpleNamespace(), "wgs")
    assert calls == [True]


def test_native_consumers_reject_a_different_dispatch_path(monkeypatch, tmp_path):
    from scripts import cce_stage_execution_adapter as adapter

    payload = _payload()
    path = tmp_path / "step4_publish.request.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    other = tmp_path / "foreign.stage-execution.dispatch.json"
    executor = SimpleNamespace(writer_quiescent=lambda *_args, **_kw: True)
    binding = SimpleNamespace(
        request_path=path, dispatch_path=other, status_path=tmp_path / "terminal.json"
    )
    monkeypatch.setattr(adapter, "executor_for_registered", lambda *_args, **_kw: (executor, "ref", binding))
    monkeypatch.setattr(publish, "registered_publish", lambda *_args, **_kw: (path, b"{}"))

    with pytest.raises(ValueError, match="native dispatch path differs"):
        publish.observe_locked(payload, gate=SimpleNamespace(), pipeline="wgs")
    with paired._exclusive(path.with_suffix(".launch.lock")):
        with paired._exclusive(path.with_suffix(".worker.lock")):
            with pytest.raises(RuntimeError, match="native dispatcher lock or dispatch path differs"):
                paired._inactive_dispatcher(path, SimpleNamespace(), "wgs")


@pytest.mark.parametrize(
    ("pipeline", "name"),
    [("wgs", "step1_upload.json"), ("gatk", "step1_upload.request.json")],
)
def test_missing_request_with_private_native_evidence_blocks_writer(tmp_path, pipeline, name):
    path = tmp_path / name
    (tmp_path / "stage-execution-registration" / "step1_upload").mkdir(parents=True)
    with paired._exclusive(path.with_suffix(".launch.lock")):
        with paired._exclusive(path.with_suffix(".worker.lock")):
            with pytest.raises(RuntimeError, match="native dispatcher request is missing"):
                paired._inactive_dispatcher(path, SimpleNamespace(), pipeline)


def test_step4_observation_rejects_explicit_null_marker(monkeypatch, tmp_path):
    payload = _payload()
    payload["stage_execution"] = None
    path = tmp_path / "step4_publish.request.json"
    monkeypatch.setattr(publish, "registered_publish", lambda *_args, **_kw: (path, b"{}"))
    with pytest.raises(ValueError, match="unsupported Step4 stage execution protocol"):
        publish.observe_locked(payload, gate=SimpleNamespace(), pipeline="wgs")
