"""Trusted platform binding for the native CCE stage-execution protocol.

Only the already-registered WGS/GATK Step1–6 request supplies identity. Paths,
worker commands and handlers are selected here from the local gate, never from
request fields. Observation and resolution do not create evidence.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


_STAGES = (
    "step1_upload", "step2_master", "step3_monitor", "step4_publish",
    "step5_download", "step6_materialize",
)
_PIPELINES = frozenset({"wgs", "gatk"})
_CONTROL_SCHEMA = "airflow-demo.stage-terminal.v1"
_REGISTRATION_SCHEMA = "airflow-demo.stage-registration.v1"
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_TERMINAL = {"success": "succeeded", "failed": "failed", "canceled": "canceled"}


def _native():
    # No legacy fallback: a marked request requires the exact installed native
    # contract. Keep import lazy so old, unmarked requests retain their entry.
    from cce_pipeline import stage_execution

    if stage_execution.STAGE_EXECUTION_PROTOCOL != "cce.stage-execution.v1":
        raise RuntimeError("unsupported native stage-execution protocol")
    return stage_execution


def _paired():
    if __package__:
        from . import cce_paired_runtime
    else:
        import cce_paired_runtime
    return cce_paired_runtime


def _publish_module():
    if __package__:
        from . import cce_publish_recovery
    else:
        import cce_publish_recovery
    return cce_publish_recovery


def _request_path(gate, analysis_id: str, attempt: int, stage: str) -> Path:
    path = gate._request_path(analysis_id, attempt, stage)
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError("trusted stage request path is invalid")
    return path


def _registration_path(request_path: Path, stage: str, generation: int) -> Path:
    return (request_path.parent / "stage-execution-registration" / stage
            / f"generation-{generation}.json")


def _terminal_path(request_path: Path, stage: str, generation: int) -> Path:
    return (request_path.parent / "stage-execution-terminal" / stage
            / f"generation-{generation}.json")


def _read_json(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = _paired()._read_registered(path)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("registered stage evidence must be an object")
    return raw, value


def _read_private_bytes(path: Path) -> bytes:
    _check_private_dir(path.parent)
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise ValueError("stage private evidence file is unsafe")
    return _paired()._read_registered(path)


def _read_private_json(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = _read_private_bytes(path)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('registered stage evidence must be an object')
    return raw, value


def _registry(gate, pipeline: str):
    if pipeline not in _PIPELINES or not callable(getattr(gate, "_native_business_stage", None)):
        raise ValueError("native stage handler is unavailable")
    return {(pipeline, stage): gate._native_business_stage for stage in _STAGES}


def _identity(payload: dict[str, Any], *, pipeline: str, registry: dict):
    return _paired().execution_identity_from_registered_request(
        payload, pipeline=pipeline, handler_registry=registry)


def _trusted_ref(payload: dict[str, Any], raw: bytes, *, gate, pipeline: str,
                 registry: dict, frozen_binding: dict[str, Any] | None = None):
    native = _native()
    identity = _identity(payload, pipeline=pipeline, registry=registry)
    if frozen_binding is None:
        frozen_binding = gate._load_binding(payload)
    if not isinstance(frozen_binding, dict):
        raise ValueError("frozen batch binding is invalid")
    # The entire validated binding is hashed into the pathless ref. Neither
    # paths nor private configuration are returned over the public protocol.
    binding = {
        "request_sha256": hashlib.sha256(raw).hexdigest(),
        "frozen_batch_binding": frozen_binding,
    }
    return native.ExecutionRef.from_trusted_registration(identity, binding)


def _read_frozen(path: Path, *, gate, pipeline: str, registry: dict):
    _, record = _read_private_json(path)
    if set(record) != {"schema", "request_raw_b64", "frozen_batch_binding",
                       "execution_ref"} or record["schema"] != _REGISTRATION_SCHEMA:
        raise ValueError("frozen stage registration schema differs")
    encoded = record["request_raw_b64"]
    if not isinstance(encoded, str):
        raise ValueError("frozen stage request bytes are invalid")
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) > 16 * 1024 * 1024 or base64.b64encode(raw).decode("ascii") != encoded:
        raise ValueError("frozen stage request bytes are invalid")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or _paired()._request_digest(
            payload, pipeline) != payload.get("request_hash"):
        raise ValueError("frozen stage request hash differs")
    frozen_binding = record["frozen_batch_binding"]
    if not isinstance(frozen_binding, dict):
        raise ValueError("frozen batch binding is invalid")
    ref = _trusted_ref(payload, raw, gate=gate, pipeline=pipeline,
                       registry=registry, frozen_binding=frozen_binding)
    if record["execution_ref"] != ref.to_dict():
        raise ValueError("frozen stage registration identity differs")
    return raw, payload, frozen_binding, ref


def _current(payload: dict[str, Any], *, gate, pipeline: str, registry: dict):
    path, raw = _paired()._registered_request(payload, gate, pipeline)
    if path != _request_path(gate, payload["analysis_id"], payload["attempt"], payload["stage"]):
        raise ValueError("registered stage request path differs")
    ref = _trusted_ref(payload, raw, gate=gate, pipeline=pipeline, registry=registry)
    frozen = _registration_path(path, ref.stage, ref.stage_generation)
    if os.path.lexists(frozen):
        frozen_raw, _, _, frozen_ref = _read_frozen(
            frozen, gate=gate, pipeline=pipeline, registry=registry)
        if frozen_raw != raw or frozen_ref != ref:
            raise ValueError("frozen stage request changed")
    return path, raw, ref


def _old_payload(ref, *, gate, pipeline: str, registry: dict):
    path = _request_path(gate, ref.analysis_id, ref.attempt, ref.stage)
    frozen = _registration_path(path, ref.stage, ref.stage_generation)
    _, payload, _, frozen_ref = _read_frozen(
        frozen, gate=gate, pipeline=pipeline, registry=registry)
    if frozen_ref != ref:
        raise ValueError("frozen stage registration identity differs")
    shared_history = (path.parent / "request-history" / ref.stage
                      / f"generation-{ref.stage_generation}.json")
    if os.path.lexists(shared_history):
        _, history = _read_json(shared_history)
        if history != payload:
            raise ValueError("shared request history differs from frozen registration")
    return path, payload


def _stage_binding(ref, *, gate, pipeline: str, registry: dict):
    native = _native()
    if ref.pipeline != pipeline or ref.stage not in _STAGES:
        raise ValueError("native stage identity is outside this adapter")
    path = _request_path(gate, ref.analysis_id, ref.attempt, ref.stage)
    _, current_payload = _read_json(path)
    current_generation = current_payload.get("generation")
    if type(current_generation) is not int or current_generation < ref.stage_generation:
        raise ValueError("registered stage generation regressed")
    if current_generation == ref.stage_generation:
        _, _, current_ref = _current(current_payload, gate=gate, pipeline=pipeline,
                                     registry=registry)
        if current_ref != ref:
            raise ValueError("current stage registration differs")
    else:
        if (any(current_payload.get(key) != want for key, want in {
                "analysis_id": ref.analysis_id, "attempt": ref.attempt,
                "stage": ref.stage,
                }.items())
                or current_payload.get("stage_execution") != {
                    "protocol": "cce.stage-execution.v1"}
                or current_payload.get("orchestration_contract_version") != 2
                or current_payload.get("pipeline") not in (None, pipeline)
                or _paired()._request_digest(current_payload, pipeline)
                != current_payload.get("request_hash")):
            raise ValueError("newer stage registration is invalid")
        _old_payload(ref, gate=gate, pipeline=pipeline, registry=registry)

    dispatch = path.with_suffix(".stage-execution.dispatch.json")
    legacy_worker = path.with_suffix(
        ".worker.json" if pipeline == "wgs" else ".worker.state.json")
    if os.path.lexists(legacy_worker):
        raise ValueError("legacy stage worker evidence blocks native execution")
    if not os.path.lexists(dispatch) and os.path.lexists(path.with_suffix(".status.json")):
        raise ValueError("legacy stage status blocks native execution")
    worker_log = path.with_suffix(".worker.log")
    if os.path.lexists(worker_log):
        if not os.path.lexists(dispatch):
            raise ValueError("orphan legacy stage worker log blocks native execution")
        log_info = worker_log.lstat()
        if (not stat.S_ISREG(log_info.st_mode)
                or log_info.st_uid != os.geteuid()
                or stat.S_IMODE(log_info.st_mode) != 0o600):
            raise ValueError("native stage worker log is unsafe")
    return native.StageExecutionBinding(
        execution_ref=ref,
        request_path=path,
        dispatch_path=dispatch,
        status_path=_terminal_path(path, ref.stage, ref.stage_generation),
    )


def _business_terminal(raw: bytes, value: dict[str, Any], ref, *, pipeline: str):
    expected = {
        "analysis_id": ref.analysis_id, "attempt": ref.attempt,
        "stage": ref.stage, "generation": ref.stage_generation,
        "execution_id": ref.execution_id, "request_hash": ref.request_hash,
        "orchestration_contract_version": 2,
    }
    if any(type(value.get(key)) is not type(want) or value.get(key) != want
           for key, want in expected.items()):
        raise ValueError("business terminal identity differs")
    if value.get("schema_version") != (
        "gatk-runtime.status.v1" if pipeline == "gatk" else "wgs-runtime.stage-status.v1"
    ):
        raise ValueError("business terminal schema differs")
    state = _TERMINAL.get(value.get("status"))
    if state is None:
        return None
    receipt_hash = value.get("receipt_hash")
    if pipeline == "gatk" and receipt_hash is None:
        raise ValueError("GATK business terminal receipt hash is missing")
    if receipt_hash is not None:
        if not isinstance(receipt_hash, str) or not _DIGEST.fullmatch(receipt_hash):
            raise ValueError("business terminal receipt hash is invalid")
        digest = hashlib.sha256(json.dumps(
            {key: item for key, item in value.items() if key != "receipt_hash"},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        if digest != receipt_hash:
            raise ValueError("business terminal receipt hash differs")
    return state, hashlib.sha256(raw).hexdigest(), receipt_hash


def _check_private_component(component: Path) -> None:
    info = component.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_mode & 0o077):
        raise ValueError("stage private evidence directory is unsafe")


def _check_private_dir(path: Path) -> None:
    request_dir = path.parent.parent
    if not request_dir.is_dir() or request_dir.is_symlink():
        raise ValueError("stage request directory is unsafe")
    for component in (path.parent, path):
        _check_private_component(component)


def _private_dir(path: Path) -> None:
    # Only the two private components below the trusted request directory may
    # be created. Check each without following an intermediate symlink.
    request_dir = path.parent.parent
    if not request_dir.is_dir() or request_dir.is_symlink():
        raise ValueError("stage request directory is unsafe")
    for component in (path.parent, path):
        try:
            os.mkdir(component, 0o700)
            directory = os.open(component.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except FileExistsError:
            pass
        _check_private_component(component)


def _publish_once(path: Path, raw: bytes) -> None:
    _private_dir(path.parent)
    descriptor, name = tempfile.mkstemp(prefix=".stage-", suffix=".partial", dir=path.parent)
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            if _read_private_bytes(path) != raw:
                raise ValueError("frozen stage evidence conflicts") from None
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _freeze_registered_request(payload: dict[str, Any], *, gate, pipeline: str) -> Path:
    registry = _registry(gate, pipeline)
    path, raw, ref = _current(payload, gate=gate, pipeline=pipeline, registry=registry)
    frozen = _registration_path(path, ref.stage, ref.stage_generation)
    if not os.path.lexists(frozen):
        if os.path.lexists(_terminal_path(path, ref.stage, ref.stage_generation)):
            raise ValueError("native stage terminal lacks frozen registration")
        dispatch_path = path.with_suffix(".stage-execution.dispatch.json")
        if os.path.lexists(dispatch_path):
            _, dispatch = _read_json(dispatch_path)
            if (set(dispatch) != {"schema", "execution_ref", "state", "runtime_identity"}
                    or dispatch["schema"] != "cce.stage-execution.dispatch.v1"):
                raise ValueError("native stage dispatch evidence is invalid")
            prior = _native().ExecutionRef.from_dict(dispatch["execution_ref"])
            if (prior.pipeline != pipeline or prior.analysis_id != ref.analysis_id
                    or prior.attempt != ref.attempt or prior.stage != ref.stage
                    or prior.stage_generation >= ref.stage_generation):
                raise ValueError("native stage dispatch lacks frozen registration")
            # A real older generation may occupy the shared dispatch path.
            # Native submit still decides its terminal receipt and quiescence.
            _old_payload(prior, gate=gate, pipeline=pipeline, registry=registry)
    record = {
        "schema": _REGISTRATION_SCHEMA,
        "request_raw_b64": base64.b64encode(raw).decode("ascii"),
        "frozen_batch_binding": gate._load_binding(payload),
        "execution_ref": ref.to_dict(),
    }
    if _trusted_ref(payload, raw, gate=gate, pipeline=pipeline, registry=registry,
                    frozen_binding=record["frozen_batch_binding"]) != ref:
        raise ValueError("frozen batch binding changed before registration")
    _publish_once(frozen, _native().canonical_json_bytes(record) + b"\n")
    return frozen


def _publish_terminal(binding, *, gate, pipeline: str) -> None:
    ref = binding.execution_ref
    registry = _registry(gate, pipeline)
    current_path = _request_path(gate, ref.analysis_id, ref.attempt, ref.stage)
    _, current_payload = _read_json(current_path)
    _, _, current_ref = _current(current_payload, gate=gate, pipeline=pipeline,
                                 registry=registry)
    if current_ref != ref or binding.request_path != current_path:
        raise ValueError("business terminal belongs to another registration")
    business_path = current_path.with_suffix(".status.json")
    try:
        raw, value = _read_json(business_path)
    except FileNotFoundError:
        return  # A missing business result is not a terminal receipt.
    terminal = _business_terminal(raw, value, ref, pipeline=pipeline)
    if terminal is None:
        return
    state, business_sha, receipt_hash = terminal
    _, _, frozen_binding, frozen_ref = _read_frozen(
        _registration_path(current_path, ref.stage, ref.stage_generation),
        gate=gate, pipeline=pipeline, registry=registry)
    if frozen_ref != ref:
        raise ValueError("frozen stage registration differs from terminal")
    binding_sha = hashlib.sha256(_native().canonical_json_bytes(frozen_binding)).hexdigest()
    record = {
        "schema": _CONTROL_SCHEMA,
        "execution_ref": ref.to_dict(),
        "state": state,
        "business_sha256": business_sha,
        "business_receipt_hash": receipt_hash,
        "frozen_binding_sha256": binding_sha,
        "compute_identity": None,
    }
    _publish_once(binding.status_path, _native().canonical_json_bytes(record) + b"\n")


def _terminal_reader(binding, *, gate, pipeline: str):
    native = _native()
    try:
        _, record = _read_private_json(binding.status_path)
    except FileNotFoundError:
        return None
    expected = {"schema", "execution_ref", "state", "business_sha256",
                "business_receipt_hash", "frozen_binding_sha256", "compute_identity"}
    if set(record) != expected or record["schema"] != _CONTROL_SCHEMA:
        raise ValueError("stage terminal control schema differs")
    if record["execution_ref"] != binding.execution_ref.to_dict():
        raise ValueError("stage terminal control identity differs")
    for key in ("business_sha256", "frozen_binding_sha256"):
        if not isinstance(record[key], str) or not _DIGEST.fullmatch(record[key]):
            raise ValueError("stage terminal control digest is invalid")
    receipt_hash = record["business_receipt_hash"]
    if receipt_hash is not None and (not isinstance(receipt_hash, str)
                                     or not _DIGEST.fullmatch(receipt_hash)):
        raise ValueError("stage terminal business hash is invalid")
    if record["state"] not in _TERMINAL.values() or record["compute_identity"] is not None:
        raise ValueError("stage terminal control state is invalid")
    ref = binding.execution_ref
    path = _request_path(gate, ref.analysis_id, ref.attempt, ref.stage)
    registry = _registry(gate, pipeline)
    _, _, frozen_binding, frozen_ref = _read_frozen(
        _registration_path(path, ref.stage, ref.stage_generation),
        gate=gate, pipeline=pipeline, registry=registry)
    if (frozen_ref != ref or hashlib.sha256(
            native.canonical_json_bytes(frozen_binding)).hexdigest()
            != record["frozen_binding_sha256"]):
        raise ValueError("stage terminal frozen binding differs")
    _, current = _read_json(path)
    if current.get("generation") == ref.stage_generation:
        raw, value = _read_json(path.with_suffix(".status.json"))
        terminal = _business_terminal(raw, value, ref, pipeline=pipeline)
        if terminal is None or terminal != (
            record["state"], record["business_sha256"], receipt_hash
        ):
            raise ValueError("current business terminal differs from control")
    return native.StageReceipt(
        execution_ref=ref,
        state=record["state"],
        evidence_ref=receipt_hash or record["business_sha256"],
        compute_identity=None,
    )


def _initial_dispatch_root(request_path: Path, ref) -> Path:
    return (request_path.parent / 'stage-execution-terminal' / ref.stage
            / f'initial-dispatch-generation-{ref.stage_generation}')


def _freeze_initial_dispatch(candidate, *, gate, pipeline: str) -> None:
    """Keep old sender bytes before native submit replaces its shared sidecars.

    Called with the exact launch lock held by native submit. Acquire worker.lock
    nonblocking: the inverse worker->launch order must never block here. This
    snapshot grants no initial-abort, owner transition or CREATE authority.
    """
    if candidate.stage != 'step2_master' or candidate.stage_generation <= 1:
        return
    path = _request_path(gate, candidate.analysis_id, candidate.attempt, candidate.stage)
    _, current = _read_json(path)
    if not current.get('resume_action_id'):
        return
    dispatch_path = path.with_suffix('.stage-execution.dispatch.json')
    if not os.path.lexists(dispatch_path):
        return
    with _paired()._exclusive(path.with_suffix('.worker.lock')):
        dispatch_raw, dispatch = _read_json(dispatch_path)
        old = _native().ExecutionRef.from_dict(dispatch.get('execution_ref', {}))
        if old == candidate:
            return
        if (old.pipeline != pipeline or old.analysis_id != candidate.analysis_id
                or old.attempt != candidate.attempt or old.stage != candidate.stage
                or old.stage_generation >= candidate.stage_generation):
            raise ValueError('initial dispatch identity differs from recovery')
        if old.stage_generation != 1:
            return
        _, previous = _old_payload(old, gate=gate, pipeline=pipeline, registry=_registry(gate, pipeline))
        if previous.get('resume_action_id'):
            return
        executor, current_ref, _ = executor_for_registered(current, gate=gate, pipeline=pipeline)
        if current_ref != candidate:
            raise ValueError('initial dispatch successor changed')
        binding = _stage_binding(old, gate=gate, pipeline=pipeline, registry=_registry(gate, pipeline))
        receipt = _terminal_reader(binding, gate=gate, pipeline=pipeline)
        if receipt is None or receipt.state != 'failed':
            return  # Ordinary terminal compute recovery retains its existing path.
        if executor.writer_quiescent(old, locks_held=True) is not True:
            raise ValueError('initial sender is active or uncertain')
        business_path = path.with_suffix('.status.json')
        business_raw, business = _read_json(business_path)
        terminal = _business_terminal(business_raw, business, old, pipeline=pipeline)
        _, control = _read_private_json(binding.status_path)
        if terminal is None or terminal != (control['state'], control['business_sha256'],
                                             control['business_receipt_hash']):
            raise ValueError('initial business receipt differs from its terminal')
        log_path = path.with_suffix('.worker.log')
        log_raw = _paired()._read_registered(log_path)
        root = _initial_dispatch_root(path, old)
        snapshots = ((dispatch_path, root/'dispatch.json', dispatch_raw),
                     (business_path, root/'business-receipt.json', business_raw),
                     (log_path, root/'stderr.log', log_raw))
        for _, destination, raw in snapshots:
            _publish_once(destination, raw)
        # A concurrent append or replacement makes the snapshot unusable.
        if any(_paired()._read_registered(source) != raw for source, _, raw in snapshots):
            raise ValueError('initial sender evidence changed while freezing')


def initial_dispatch_proof(ref, *, gate, pipeline: str) -> dict[str, str]:
    """Derive native's fixed raw-evidence locators from trusted local scopes."""
    path, _ = _old_payload(ref, gate=gate, pipeline=pipeline, registry=_registry(gate, pipeline))
    root = _initial_dispatch_root(path, ref)
    values = {
        'registration_path': _registration_path(path, ref.stage, ref.stage_generation),
        'terminal_path': _terminal_path(path, ref.stage, ref.stage_generation),
        'dispatch_path': root/'dispatch.json',
        'business_receipt_path': root/'business-receipt.json',
        'stderr_path': root/'stderr.log',
    }
    for item in values.values():
        _read_private_bytes(item)
    paired = _paired()
    trust = paired._load_deployment_trust()
    if trust is None:
        raise ValueError('initial dispatch proof requires the paired deployment')
    sources = Path(paired.__file__).resolve().parent/'initial-abort-sources'
    for name in ('paired_source', 'native_source', 'executor_source'):
        item = sources/(name+'.py')
        paired._trusted_path({**trust['writers']['platform'], 'path': str(item)})
        paired._read_regular(item)
        values[name+'_path'] = item
    return {name: str(item) for name, item in values.items()}


def _executor_for_registered(payload: dict[str, Any], *, gate, pipeline: str):
    native = _native()
    registry = _registry(gate, pipeline)
    _, _, ref = _current(payload, gate=gate, pipeline=pipeline, registry=registry)

    def resolver(candidate):
        return _stage_binding(candidate, gate=gate, pipeline=pipeline,
                              registry=registry)

    def terminal_reader(binding):
        return _terminal_reader(binding, gate=gate, pipeline=pipeline)

    def worker_command(candidate):
        # Native calls this only for a new launch while holding launch.lock,
        # after its second resolver check. Recheck the original Step4 dispatch
        # deadline here; reattach and observation remain read-only after expiry.
        _freeze_initial_dispatch(candidate, gate=gate, pipeline=pipeline)
        if candidate.stage == "step4_publish":
            current_path = _request_path(
                gate, candidate.analysis_id, candidate.attempt, candidate.stage)
            _, current_payload = _read_json(current_path)
            _, _, current_ref = _current(current_payload, gate=gate,
                                         pipeline=pipeline, registry=registry)
            if current_ref != candidate:
                raise ValueError("Step4 dispatch registration changed")
            if any(key in current_payload for key in (
                    "publish_dispatch_version", "publish_deadline")):
                publish = _publish_module()
                publish.registered_publish(current_payload, gate=gate, pipeline=pipeline)
                publish.require_publish_deadline(current_payload)
        return [sys.executable, str(Path(gate.__file__).resolve()), "_native_worker",
                candidate.analysis_id, str(candidate.attempt), candidate.stage,
                str(candidate.stage_generation)]

    def handler(candidate):
        binding = resolver(candidate)
        try:
            gate._native_business_stage(candidate)
        finally:
            _publish_terminal(binding, gate=gate, pipeline=pipeline)

    handlers = {(pipeline, stage): handler for stage in _STAGES}
    executor = native.StageExecutor(
        resolver=resolver, terminal_reader=terminal_reader,
        worker_command=worker_command, handler_registry=handlers,
    )
    return executor, ref, resolver(ref)


def executor_for_registered(payload: dict[str, Any], *, gate, pipeline: str):
    """Return native executor, ref and binding without writing any file."""
    return _executor_for_registered(payload, gate=gate, pipeline=pipeline)


def submit_registered_stage(payload: dict[str, Any], *, gate, pipeline: str):
    """Freeze the exact registration, then submit through native launch fencing."""
    executor, ref, _ = _executor_for_registered(payload, gate=gate, pipeline=pipeline)
    _freeze_registered_request(payload, gate=gate, pipeline=pipeline)
    return executor.submit(ref)


def run_registered_worker(payload: dict[str, Any], *, gate, pipeline: str):
    """Worker entrypoint; the native launch identity must already exist."""
    executor, ref, binding = executor_for_registered(payload, gate=gate, pipeline=pipeline)
    frozen = _registration_path(binding.request_path, ref.stage, ref.stage_generation)
    frozen_raw, _, _, frozen_ref = _read_frozen(
        frozen, gate=gate, pipeline=pipeline, registry=_registry(gate, pipeline))
    if frozen_ref != ref or frozen_raw != _paired()._read_registered(binding.request_path):
        raise ValueError("worker frozen registration differs")
    return executor.run_worker(ref)
