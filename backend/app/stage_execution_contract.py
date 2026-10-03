"""Platform-side marker for newly frozen stage execution requests."""

import re

STAGE_EXECUTION_PROTOCOL = "cce.stage-execution.v1"
STAGE_EXECUTION_EXTENSION = {"protocol": STAGE_EXECUTION_PROTOCOL}
_NATIVE_STAGES = frozenset({
    "step1_upload", "step2_master", "step3_monitor",
    "step4_publish", "step5_download", "step6_materialize",
})
_SNAPSHOT_SCHEMA = "cce.stage-execution.snapshot.v1"
_SNAPSHOT_KEYS = frozenset({
    "schema", "execution_ref", "state", "evidence_ref", "runtime_identity",
    "compute_identity", "observation_health",
})
_REF_KEYS = frozenset({
    "protocol", "pipeline", "analysis_id", "attempt", "stage",
    "execution_id", "stage_generation", "request_hash", "registration_sha256",
})
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def freeze_stage_execution_protocol(request_payload: dict) -> None:
    """Freeze native Step1–Step6 before hashing; other stages stay legacy."""
    if not isinstance(request_payload, dict):
        raise ValueError("stage execution request must be an object")
    stage = request_payload.get("stage")
    native_stage = isinstance(stage, str) and stage in _NATIVE_STAGES
    if "stage_execution" in request_payload:
        if request_payload["stage_execution"] != STAGE_EXECUTION_EXTENSION or not native_stage:
            raise ValueError("unsupported stage execution protocol or stage")
        return
    if native_stage:
        request_payload["stage_execution"] = dict(STAGE_EXECUTION_EXTENSION)


def require_native_stage_terminal(
    observation: dict,
    *,
    pipeline: str,
    analysis_id: str,
    attempt: int,
    stage: str,
    execution_id: str,
    generation: int,
    request_hash: str,
    evidence_ref: str,
    expected_state: str,
) -> dict:
    """Require one exact native terminal for a current business receipt.

    The authenticated caller supplies a fresh read-only native observation. The
    registered platform row and business receipt provide the expected identity;
    the native-only registration digest has no platform copy to compare against.
    """
    if expected_state not in {"succeeded", "failed", "canceled"}:
        raise ValueError("unsupported native stage terminal state")
    label = "success" if expected_state == "succeeded" else "terminal"
    if (not isinstance(observation, dict) or set(observation) != _SNAPSHOT_KEYS
            or observation.get("schema") != _SNAPSHOT_SCHEMA):
        raise ValueError(f"native stage {label} snapshot schema differs")
    ref = observation.get("execution_ref")
    if not isinstance(ref, dict) or set(ref) != _REF_KEYS:
        raise ValueError(f"native stage {label} execution ref is incomplete")
    if ref.get("protocol") != STAGE_EXECUTION_PROTOCOL:
        raise ValueError(f"native stage {label} protocol differs")
    for key in ("pipeline", "analysis_id", "stage", "execution_id"):
        if not isinstance(ref[key], str) or _TOKEN.fullmatch(ref[key]) is None:
            raise ValueError(f"native stage {label} execution ref token is invalid")
    for key in ("attempt", "stage_generation"):
        if type(ref[key]) is not int or ref[key] < 1:
            raise ValueError(f"native stage {label} execution generation is invalid")
    for key in ("request_hash", "registration_sha256"):
        if not isinstance(ref[key], str) or _SHA256.fullmatch(ref[key]) is None:
            raise ValueError(f"native stage {label} execution digest is invalid")
    expected = {
        "pipeline": pipeline, "analysis_id": analysis_id, "attempt": attempt,
        "stage": stage, "execution_id": execution_id,
        "stage_generation": generation, "request_hash": request_hash,
    }
    if any(type(ref.get(key)) is not type(value) or ref[key] != value
           for key, value in expected.items()):
        raise ValueError(f"native stage {label} execution identity differs")
    if observation.get("state") != expected_state:
        raise ValueError("native stage terminal state differs")
    health = observation.get("observation_health")
    if not isinstance(health, str) or health not in {"healthy", "degraded"}:
        raise ValueError(f"native stage {label} observation health is invalid")
    if (not isinstance(evidence_ref, str) or _SHA256.fullmatch(evidence_ref) is None
            or observation.get("evidence_ref") != evidence_ref):
        raise ValueError(f"native stage {label} evidence does not match business receipt")
    runtime = observation.get("runtime_identity")
    if runtime is not None and (
        not isinstance(runtime, dict)
        or set(runtime) != {"boot_id", "pid", "starttime_ticks", "process_group_id"}
        or not isinstance(runtime.get("boot_id"), str)
        or _TOKEN.fullmatch(runtime["boot_id"]) is None
        or any(type(runtime.get(key)) is not int or runtime[key] < 1
               for key in ("pid", "starttime_ticks", "process_group_id"))
    ):
        raise ValueError(f"native stage {label} runtime identity is invalid")
    compute = observation.get("compute_identity")
    if compute is not None and (
        not isinstance(compute, dict)
        or set(compute) != {"compute_generation", "master_uid"}
        or (compute.get("compute_generation") is not None
            and (type(compute["compute_generation"]) is not int
                 or compute["compute_generation"] < 1))
        or (compute.get("master_uid") is not None
            and (not isinstance(compute["master_uid"], str)
                 or _TOKEN.fullmatch(compute["master_uid"]) is None))
    ):
        raise ValueError(f"native stage {label} compute identity is invalid")
    return observation


def require_native_stage_success(
    observation: dict,
    *,
    pipeline: str,
    analysis_id: str,
    attempt: int,
    stage: str,
    execution_id: str,
    generation: int,
    request_hash: str,
    evidence_ref: str,
) -> dict:
    """Preserve the UE-04 success-only finalization contract."""
    return require_native_stage_terminal(
        observation, pipeline=pipeline, analysis_id=analysis_id,
        attempt=attempt, stage=stage, execution_id=execution_id,
        generation=generation, request_hash=request_hash,
        evidence_ref=evidence_ref, expected_state="succeeded",
    )
