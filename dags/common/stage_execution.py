"""Small Airflow client for an already registered native stage execution.

The adapter supplies exact, trusted dispatch and observation operations. This
module does not create a generation or interpret a backend ``ready`` flag as
native completion.
"""

from __future__ import annotations

import re
import time
from typing import Callable


_REF_KEYS = frozenset({
    "protocol", "pipeline", "analysis_id", "attempt", "stage",
    "execution_id", "stage_generation", "request_hash", "registration_sha256",
})
_SNAPSHOT_KEYS = frozenset({
    "schema", "execution_ref", "state", "evidence_ref", "runtime_identity",
    "compute_identity", "observation_health",
})
_STATES = frozenset({"accepted", "running", "succeeded", "failed", "canceled", "unknown"})
_TERMINAL = frozenset({"succeeded", "failed", "canceled"})
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}\Z")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DispatchUncertain(RuntimeError):
    """The command may have run; callers may only observe this execution."""


class StageWaitExpired(RuntimeError):
    """The observation window ended without proving a business terminal."""


def _ref(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != _REF_KEYS:
        raise ValueError("native execution identity is incomplete")
    if value["protocol"] != "cce.stage-execution.v1":
        raise ValueError("native execution identity has an unsupported protocol")
    if any(not isinstance(value[key], str) or not _TOKEN.fullmatch(value[key])
           for key in ("pipeline", "analysis_id", "stage", "execution_id")):
        raise ValueError("native execution identity has an invalid token")
    if any(type(value[key]) is not int or value[key] < 1
           for key in ("attempt", "stage_generation")):
        raise ValueError("native execution identity has an invalid generation")
    if any(not isinstance(value[key], str) or not _SHA256.fullmatch(value[key])
           for key in ("request_hash", "registration_sha256")):
        raise ValueError("native execution identity has an invalid digest")
    return value


def require_snapshot(value: dict, *, execution_ref: dict) -> dict:
    """Accept only a full native snapshot for the exact registered execution."""
    expected = _ref(execution_ref)
    if (not isinstance(value, dict) or set(value) != _SNAPSHOT_KEYS
            or value.get("schema") != "cce.stage-execution.snapshot.v1"):
        raise ValueError("native execution snapshot schema differs")
    if _ref(value.get("execution_ref")) != expected:
        raise ValueError("native execution snapshot identity differs")
    state = value.get("state")
    health = value.get("observation_health")
    if not isinstance(state, str) or state not in _STATES or not isinstance(health, str) or health not in {"healthy", "degraded"}:
        raise ValueError("native execution snapshot state is invalid")
    if state == "unknown" and health != "degraded":
        raise ValueError("native execution unknown state requires degraded observation")
    evidence = value.get("evidence_ref")
    if evidence is not None and (not isinstance(evidence, str) or not _TOKEN.fullmatch(evidence)):
        raise ValueError("native execution evidence reference is invalid")
    runtime = value.get("runtime_identity")
    if runtime is not None and (
        not isinstance(runtime, dict)
        or set(runtime) != {"boot_id", "pid", "starttime_ticks", "process_group_id"}
        or not isinstance(runtime.get("boot_id"), str)
        or not _TOKEN.fullmatch(runtime["boot_id"])
        or any(type(runtime.get(key)) is not int or runtime[key] < 1
               for key in ("pid", "starttime_ticks", "process_group_id"))
    ):
        raise ValueError("native runtime process identity is invalid")
    compute = value.get("compute_identity")
    if compute is not None and (
        not isinstance(compute, dict)
        or set(compute) != {"compute_generation", "master_uid"}
        or (compute.get("compute_generation") is not None
            and (type(compute["compute_generation"]) is not int
                 or compute["compute_generation"] < 1))
        or (compute.get("master_uid") is not None
            and (not isinstance(compute["master_uid"], str)
                 or not _TOKEN.fullmatch(compute["master_uid"])))
    ):
        raise ValueError("native compute identity is invalid")
    return value


def execution_ref_from_registration(snapshot: dict, registration: dict, *,
                                    pipeline: str, stage: str) -> dict:
    """Bind the gate's full ref to the backend's frozen stage registration."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("execution_ref"), dict):
        raise ValueError("native execution registration has no full identity")
    ref = _ref(snapshot["execution_ref"])
    require_snapshot(snapshot, execution_ref=ref)
    expected = {
        "protocol": "cce.stage-execution.v1",
        "pipeline": pipeline,
        "analysis_id": registration.get("analysis_id"),
        "attempt": registration.get("attempt"),
        "stage": stage,
        "execution_id": registration.get("execution_id"),
        "stage_generation": registration.get("generation"),
        "request_hash": registration.get("request_hash"),
    }
    if any(ref.get(key) != value for key, value in expected.items()):
        raise ValueError("native execution registration identity differs")
    return ref


def observe_stage(*, execution_ref: dict, observe: Callable[[dict], dict]) -> dict:
    """Observe once; uncertainty remains a distinct, nonterminal snapshot."""
    ref = _ref(execution_ref)
    return require_snapshot(observe(ref), execution_ref=ref)


def submit_stage(*, execution_ref: dict, dispatch: Callable[[dict], dict],
                 observe: Callable[[dict], dict], deadline: float | None) -> dict:
    """Submit once; on an uncertain reply only observe the same identity."""
    ref = _ref(execution_ref)
    if deadline is not None and time.time() >= deadline:
        raise StageWaitExpired("registered stage observation deadline has elapsed")
    try:
        return require_snapshot(dispatch(ref), execution_ref=ref)
    except DispatchUncertain:
        return observe_stage(execution_ref=ref, observe=observe)


def submit_and_await(*, execution_ref: dict, dispatch: Callable[[dict], dict],
                     observe: Callable[[dict], dict], deadline: float | None,
                     poll_interval: float = 30) -> dict:
    """Hold the caller's existing task/pool until the same stage is terminal."""
    if poll_interval < 0:
        raise ValueError("stage observation poll interval must be nonnegative")
    result = submit_stage(execution_ref=execution_ref, dispatch=dispatch,
                          observe=observe, deadline=deadline)
    while result["state"] not in _TERMINAL:
        if deadline is not None and time.time() >= deadline:
            raise StageWaitExpired("registered stage observation deadline has elapsed")
        time.sleep(poll_interval)
        result = observe_stage(execution_ref=execution_ref, observe=observe)
    return result
