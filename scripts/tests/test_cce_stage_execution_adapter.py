"""Focused, data-free contract tests for the platform stage-execution adapter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("cce_pipeline.stage_execution")

from scripts import cce_stage_execution_adapter as adapter


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _request(generation: int, *, pipeline: str = "gatk") -> dict:
    analysis_id = ("GATK_20260929_010203_A1B2C3" if pipeline == "gatk"
                   else "WGS_20260929_010203_A1B2C3")
    value = {
        "schema_version": "gatk-runtime.request.v1" if pipeline == "gatk" else "wgs-runtime.request.v4",
        "stage_execution": {"protocol": "cce.stage-execution.v1"},
        "orchestration_contract_version": 2,
        "pipeline": pipeline,
        "analysis_id": analysis_id,
        "attempt": 1,
        "stage": "step1_upload",
        "generation": generation,
        "execution_id": f"{analysis_id}-a1-step1_upload-g{generation}",
        "runtime_workdir": f"/frozen/{analysis_id}/attempt-1",
    }
    from scripts import cce_paired_runtime
    value["request_hash"] = cce_paired_runtime._request_digest(value, pipeline)
    return value


def _gate(tmp_path: Path, *, pipeline: str = "gatk"):
    request_path = tmp_path / "requests" / _request(1, pipeline=pipeline)["analysis_id"] / "attempt-1" / "step1_upload.request.json"
    binding = {"schema_version": f"{pipeline}-runtime.batch-binding.v1", "release": "synthetic"}
    gate = SimpleNamespace(
        __file__=str(tmp_path / "gatk_runtime_gate.py"),
        _request_path=lambda aid, attempt, stage: request_path,
        _load_binding=lambda payload: binding,
        _native_business_stage=lambda ref: None,
    )
    if pipeline == "wgs":
        gate.RUNTIME_RUN_ROOT = str(tmp_path / "run-root")
        gate._workdir = lambda payload: (
            Path(gate.RUNTIME_RUN_ROOT).resolve() / payload["analysis_id"]
            / f"attempt-{payload['attempt']}")
    return gate, request_path


def _terminal(request_path: Path, payload: dict, *, status: str = "success",
              receipt_hash: bool = True) -> None:
    value = {
        "schema_version": ("gatk-runtime.status.v1" if payload["pipeline"] == "gatk"
                           else "wgs-runtime.stage-status.v1"),
        "analysis_id": payload["analysis_id"],
        "attempt": payload["attempt"],
        "stage": payload["stage"],
        "generation": payload["generation"],
        "execution_id": payload["execution_id"],
        "request_hash": payload["request_hash"],
        "orchestration_contract_version": 2,
        "status": status,
        "message": "synthetic private business detail",
    }
    if receipt_hash:
        value["receipt_hash"] = hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    _write_json(request_path.with_suffix(".status.json"), value)


def test_factory_is_read_only_and_separates_native_from_legacy_paths(tmp_path: Path) -> None:
    gate, path = _gate(tmp_path)
    payload = _request(1)
    _write_json(path, payload)

    executor, ref, binding = adapter.executor_for_registered(payload, gate=gate, pipeline="gatk")

    assert ref.stage_generation == 1
    assert binding.request_path == path
    assert binding.dispatch_path == path.with_suffix(".stage-execution.dispatch.json")
    assert binding.status_path == path.parent / "stage-execution-terminal" / "step1_upload" / "generation-1.json"
    assert not binding.dispatch_path.exists()
    assert not binding.status_path.exists()
    assert not (path.parent / "stage-execution-registration").exists()
    assert executor.observe(ref).state == "unknown"


def test_terminal_control_is_minimal_and_old_generation_resolves_from_frozen_request(
    tmp_path: Path, monkeypatch
) -> None:
    gate, path = _gate(tmp_path)
    first = _request(1)
    _write_json(path, first)
    executor, old_ref, old_binding = adapter.executor_for_registered(first, gate=gate, pipeline="gatk")
    adapter._freeze_registered_request(first, gate=gate, pipeline="gatk")
    _terminal(path, first)
    adapter._publish_terminal(old_binding, gate=gate, pipeline="gatk")
    control = json.loads(old_binding.status_path.read_text(encoding="utf-8"))
    assert control["state"] == "succeeded"
    assert control["execution_ref"] == old_ref.to_dict()
    assert len(control["business_sha256"]) == 64
    assert "synthetic private business detail" not in old_binding.status_path.read_text()

    # The fixed business status can move on; the exact older control remains.
    second = _request(2)
    _write_json(path, second)
    path.with_suffix(".status.json").unlink()
    newer, _, _ = adapter.executor_for_registered(second, gate=gate, pipeline="gatk")
    _write_json(old_binding.dispatch_path, {
        "schema": "cce.stage-execution.dispatch.v1",
        "execution_ref": old_ref.to_dict(),
        "state": "finished",
        "runtime_identity": None,
    })
    from cce_pipeline import stage_execution
    submitted = []
    monkeypatch.setattr(
        stage_execution.StageExecutor, "submit",
        lambda _executor, ref: submitted.append(ref) or SimpleNamespace(state="accepted"),
    )
    assert adapter.submit_registered_stage(second, gate=gate, pipeline="gatk").state == "accepted"
    assert len(submitted) == 1 and submitted[0].stage_generation == 2
    assert adapter._registration_path(path, "step1_upload", 2).is_file()
    assert newer.observe(old_ref).state == "succeeded"
    assert executor.observe(old_ref).state == "succeeded"


def test_unknown_or_foreign_business_terminal_cannot_be_published(tmp_path: Path) -> None:
    gate, path = _gate(tmp_path)
    payload = _request(1)
    _write_json(path, payload)
    _, _, binding = adapter.executor_for_registered(payload, gate=gate, pipeline="gatk")
    _terminal(path, {**payload, "execution_id": "foreign-execution"}, status="failed")

    with pytest.raises(ValueError, match="business terminal"):
        adapter._publish_terminal(binding, gate=gate, pipeline="gatk")
    assert not binding.status_path.exists()


def test_legacy_worker_evidence_blocks_native_takeover(tmp_path: Path) -> None:
    gate, path = _gate(tmp_path)
    payload = _request(1)
    _write_json(path, payload)
    _write_json(path.with_suffix(".worker.state.json"), {"state": "finished"})

    with pytest.raises(ValueError, match="legacy"):
        adapter.executor_for_registered(payload, gate=gate, pipeline="gatk")


def test_wgs_business_terminal_uses_real_stage_status_schema(tmp_path: Path) -> None:
    gate, path = _gate(tmp_path, pipeline="wgs")
    payload = _request(1, pipeline="wgs")
    _write_json(path, payload)
    _, _, binding = adapter.executor_for_registered(payload, gate=gate, pipeline="wgs")
    adapter._freeze_registered_request(payload, gate=gate, pipeline="wgs")
    _terminal(path, payload, receipt_hash=False)

    adapter._publish_terminal(binding, gate=gate, pipeline="wgs")
    assert adapter._terminal_reader(binding, gate=gate, pipeline="wgs").state == "succeeded"


def test_gatk_terminal_without_receipt_hash_is_not_published(tmp_path: Path) -> None:
    gate, path = _gate(tmp_path)
    payload = _request(1)
    _write_json(path, payload)
    _, _, binding = adapter.executor_for_registered(payload, gate=gate, pipeline="gatk")
    adapter._freeze_registered_request(payload, gate=gate, pipeline="gatk")
    _terminal(path, payload, receipt_hash=False)

    with pytest.raises(ValueError, match="receipt hash is missing"):
        adapter._publish_terminal(binding, gate=gate, pipeline="gatk")
    assert not binding.status_path.exists()


def test_orphan_legacy_worker_log_blocks_first_native_launch(tmp_path: Path) -> None:
    gate, path = _gate(tmp_path)
    payload = _request(1)
    _write_json(path, payload)
    path.with_suffix(".worker.log").write_text("old log", encoding="utf-8")

    with pytest.raises(ValueError, match="orphan legacy"):
        adapter.executor_for_registered(payload, gate=gate, pipeline="gatk")


def test_terminal_reader_rejects_changed_frozen_binding(tmp_path: Path) -> None:
    gate, path = _gate(tmp_path)
    payload = _request(1)
    _write_json(path, payload)
    _, _, binding = adapter.executor_for_registered(payload, gate=gate, pipeline="gatk")
    adapter._freeze_registered_request(payload, gate=gate, pipeline="gatk")
    _terminal(path, payload)
    adapter._publish_terminal(binding, gate=gate, pipeline="gatk")
    record = json.loads(binding.status_path.read_text(encoding="utf-8"))
    record["frozen_binding_sha256"] = "0" * 64
    _write_json(binding.status_path, record)

    with pytest.raises(ValueError, match="frozen binding differs"):
        adapter._terminal_reader(binding, gate=gate, pipeline="gatk")


def test_existing_native_dispatch_without_registration_is_not_backfilled(tmp_path: Path) -> None:
    gate, path = _gate(tmp_path)
    payload = _request(1)
    _write_json(path, payload)
    _, ref, _ = adapter.executor_for_registered(payload, gate=gate, pipeline="gatk")
    _write_json(path.with_suffix(".stage-execution.dispatch.json"), {
        "schema": "cce.stage-execution.dispatch.v1",
        "execution_ref": ref.to_dict(),
        "state": "finished",
        "runtime_identity": None,
    })

    with pytest.raises(ValueError, match="lacks frozen registration"):
        adapter._freeze_registered_request(payload, gate=gate, pipeline="gatk")
    assert not (path.parent / "stage-execution-registration").exists()


def test_symlinked_private_registration_parent_is_rejected(tmp_path: Path) -> None:
    gate, path = _gate(tmp_path)
    payload = _request(1)
    _write_json(path, payload)
    outside = tmp_path / "outside"
    outside.mkdir()
    (path.parent / "stage-execution-registration").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="private evidence directory is unsafe"):
        adapter._freeze_registered_request(payload, gate=gate, pipeline="gatk")
    assert list(outside.iterdir()) == []
