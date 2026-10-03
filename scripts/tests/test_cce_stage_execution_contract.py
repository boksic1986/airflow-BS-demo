"""The current platform producer/consumer mapping for stage execution v1."""

import hashlib
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))


def test_current_execution_contract():
    from app.stage_execution_contract import freeze_stage_execution_protocol
    from cce_pipeline.stage_execution import (
        ComputeIdentity,
        ExecutionRef,
        ExecutionSnapshot,
        canonical_json_bytes,
        platform_status_from_state,
        resolve_handler_key,
        state_from_platform_status,
    )
    from scripts import cce_paired_runtime as paired

    request = {
        "analysis_id": "synthetic-ue01-001",
        "attempt": 1,
        "stage": "step2_master",
        "execution_id": "wse-synthetic-001",
        "generation": 1,
        "orchestration_contract_version": 2,
    }
    handler_registry = {("wgs", "step2_master"): object()}

    before = hashlib.sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    freeze_stage_execution_protocol(request)
    assert request["stage_execution"] == {"protocol": "cce.stage-execution.v1"}
    after = hashlib.sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert before != after
    request["request_hash"] = paired._request_digest(request, "wgs")

    assert resolve_handler_key(handler_registry, "wgs", "step2_master") is handler_registry[("wgs", "step2_master")]
    with pytest.raises(ValueError):
        resolve_handler_key(handler_registry, "unregistered", "step2_master")

    identity = paired.execution_identity_from_registered_request(
        request, pipeline="wgs", handler_registry=handler_registry
    )
    runtime_binding = {"handler_key": ["wgs", "step2_master"]}
    ref = ExecutionRef.from_trusted_registration(identity, runtime_binding)
    ref_json = ref.to_dict()
    assert ref_json == {
        **identity,
        "registration_sha256": hashlib.sha256(
            canonical_json_bytes({**identity, "runtime_binding": runtime_binding})
        ).hexdigest(),
    }
    assert ref_json["stage_generation"] == request["generation"]
    assert ExecutionRef.from_dict(ref_json) == ref
    assert canonical_json_bytes({"label": "样本"}) == b'{"label":"\xe6\xa0\xb7\xe6\x9c\xac"}'
    for field in ("attempt", "stage_generation"):
        malformed = {**identity, field: True}
        with pytest.raises(ValueError):
            ExecutionRef.from_trusted_registration(malformed, runtime_binding)

    canceled = ExecutionSnapshot(
        execution_ref=ref,
        state="canceled",
        evidence_ref="evidence-synthetic-1",
        runtime_identity=None,
        compute_identity=ComputeIdentity(compute_generation=None, master_uid=None),
        observation_health="healthy",
    )
    canceled_json = json.loads(canceled.to_json_bytes())
    assert canceled_json["schema"] == "cce.stage-execution.snapshot.v1"
    assert canceled_json["execution_ref"] == ref_json
    assert paired.platform_status_from_snapshot(
        request,
        canceled_json,
        expected_ref=ref_json,
        pipeline="wgs",
        handler_registry=handler_registry,
    ) == "canceled"
    assert platform_status_from_state("canceled") == "canceled"
    assert state_from_platform_status("success") == "succeeded"

    malformed_evidence = {**canceled_json, "evidence_ref": "evidence ref"}
    with pytest.raises(RuntimeError, match="evidence"):
        paired.platform_status_from_snapshot(
            request,
            malformed_evidence,
            expected_ref=ref_json,
            pipeline="wgs",
            handler_registry=handler_registry,
        )
    malformed_runtime = {
        **canceled_json,
        "runtime_identity": {
            "boot_id": "boot id",
            "pid": 1,
            "starttime_ticks": 1,
            "process_group_id": 1,
        },
    }
    with pytest.raises(RuntimeError, match="runtime process"):
        paired.platform_status_from_snapshot(
            request,
            malformed_runtime,
            expected_ref=ref_json,
            pipeline="wgs",
            handler_registry=handler_registry,
        )

    # A matching stage identity with a different registration digest is not the
    # same execution and must not be accepted by the platform consumer.
    changed_digest = {
        **canceled_json,
        "execution_ref": {**ref_json, "registration_sha256": "b" * 64},
    }
    with pytest.raises(RuntimeError, match="identity"):
        paired.platform_status_from_snapshot(
            request,
            changed_digest,
            expected_ref=ref_json,
            pipeline="wgs",
            handler_registry=handler_registry,
        )

    unknown = ExecutionSnapshot(
        execution_ref=ref,
        state="unknown",
        evidence_ref=None,
        runtime_identity=None,
        compute_identity=None,
        observation_health="degraded",
    )
    assert paired.platform_status_from_snapshot(
        request,
        json.loads(unknown.to_json_bytes()),
        expected_ref=ref_json,
        pipeline="wgs",
        handler_registry=handler_registry,
    ) is None
    assert platform_status_from_state("unknown") is None

    unsupported = {**request, "stage_execution": {"protocol": "cce.stage-execution.v0"}}
    with pytest.raises(RuntimeError, match="protocol"):
        paired.execution_identity_from_registered_request(
            unsupported, pipeline="wgs", handler_registry=handler_registry
        )
    with pytest.raises(RuntimeError, match="registry"):
        paired.execution_identity_from_registered_request(
            request, pipeline="unknown-pipeline", handler_registry=handler_registry
        )
    for disabled in (None, False, ""):
        with pytest.raises(RuntimeError, match="registry"):
            paired.execution_identity_from_registered_request(
                request, pipeline="wgs", handler_registry={("wgs", "step2_master"): disabled}
            )
