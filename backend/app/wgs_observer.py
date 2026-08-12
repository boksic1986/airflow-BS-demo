from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from sqlalchemy import select

from app.models import (
    AnalysisRun,
    EvidenceCursor,
    KubernetesWorkload,
    ObserverRunState,
    RuleEventRaw,
    RuleState,
    RunAttempt,
)
from app.wgs_evidence_binding import EvidenceBinding, load_evidence_bindings
from app.wgs_release_catalog import load_snapshot_catalog


RULE_EVENT_TYPES = {
    "rule_planned",
    "job_info",
    "job_started",
    "job_finished",
    "job_error",
}
TERMINAL_RULE_EVENTS = {"job_finished": "success", "job_error": "failed"}


def ingest_evidence_once(
    *,
    session_factory,
    evidence_root: Path,
    binding_root: Path,
    catalog_path: Path,
) -> dict[str, int]:
    catalog = load_snapshot_catalog(catalog_path)
    bindings, diagnostics = load_evidence_bindings(
        binding_root, evidence_root, catalog
    )
    result = {
        "bindings": 0,
        "files": 0,
        "events_ingested": 0,
        "errors": len(diagnostics),
    }
    for binding in bindings:
        validation_error = _validate_database_binding(session_factory, binding)
        if validation_error:
            result["errors"] += 1
            continue
        result["bindings"] += 1
        rule_paths = sorted(
            (binding.evidence_directory / "rule-status" / "raw").glob("*.jsonl")
        )
        raw_root = binding.evidence_directory / "raw"
        k8s_paths = [
            raw_root / name
            for name in ("pod-events.jsonl", "pod-metrics.jsonl", "job-events.jsonl")
            if (raw_root / name).is_file()
        ]
        binding_errors = 0
        for path in rule_paths:
            result["files"] += 1
            try:
                count, had_error = _ingest_rule_file(
                    session_factory, evidence_root.resolve(), binding, path
                )
                result["events_ingested"] += count
                if had_error:
                    result["errors"] += 1
                    binding_errors += 1
            except (OSError, UnicodeError, ValueError) as error:
                result["errors"] += 1
                binding_errors += 1
                _record_file_error(
                    session_factory, evidence_root.resolve(), binding, path, str(error)
                )
        for path in k8s_paths:
            result["files"] += 1
            try:
                count, had_error = _ingest_kubernetes_file(
                    session_factory, evidence_root.resolve(), binding, path
                )
                result["events_ingested"] += count
                if had_error:
                    result["errors"] += 1
                    binding_errors += 1
            except (OSError, UnicodeError, ValueError) as error:
                result["errors"] += 1
                binding_errors += 1
                _record_file_error(
                    session_factory, evidence_root.resolve(), binding, path, str(error)
                )
        _set_observer_status(
            session_factory,
            binding,
            status="degraded" if binding_errors else "healthy",
            error="one or more evidence files could not be consumed"
            if binding_errors
            else None,
        )
    return result


def _validate_database_binding(session_factory, binding: EvidenceBinding) -> str | None:
    with session_factory() as session:
        analysis = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == binding.analysis_id)
        )
        if analysis is None:
            return "unknown analysis"
        attempt = session.scalar(
            select(RunAttempt).where(
                RunAttempt.analysis_id == binding.analysis_id,
                RunAttempt.attempt == binding.attempt,
            )
        )
        if attempt is None:
            return "unknown analysis attempt"
        if analysis.attempt != binding.attempt:
            return "binding attempt is not the active analysis attempt"
        if attempt.run_label != binding.run_label:
            return "binding run_label does not match analysis attempt"
        if analysis.params_json.get("pipeline_snapshot_id") != binding.pipeline_snapshot_id:
            return "binding snapshot does not match analysis"
        state = session.scalar(
            select(ObserverRunState).where(
                ObserverRunState.analysis_id == binding.analysis_id,
                ObserverRunState.attempt == binding.attempt,
            )
        )
        if state is None:
            state = ObserverRunState(
                analysis_id=binding.analysis_id,
                attempt=binding.attempt,
                pipeline_snapshot_id=binding.pipeline_snapshot_id,
                run_label=binding.run_label,
                relative_evidence_path=binding.evidence_path,
                status="pending",
            )
            session.add(state)
        elif (
            state.pipeline_snapshot_id != binding.pipeline_snapshot_id
            or state.run_label != binding.run_label
            or state.relative_evidence_path != binding.evidence_path
        ):
            return "binding conflicts with persisted observer run state"
        session.commit()
    return None


def _ingest_rule_file(
    session_factory,
    evidence_root: Path,
    binding: EvidenceBinding,
    path: Path,
) -> tuple[int, bool]:
    relative_path = _safe_relative(path, evidence_root)
    stat = path.stat()
    identity = f"{stat.st_dev}:{stat.st_ino}"
    with session_factory() as session:
        cursor = _get_or_create_cursor(session, binding, relative_path)
        if (
            cursor.file_identity not in {None, identity}
            or stat.st_size < cursor.byte_offset
        ):
            cursor.byte_offset = 0
            cursor.line_number = 0
            cursor.last_error = None
        offset = cursor.byte_offset
        line_number = cursor.line_number
        payloads: list[dict] = []
        bad_line: str | None = None
        with path.open("rb") as handle:
            handle.seek(offset)
            while True:
                start = handle.tell()
                raw = handle.readline()
                if not raw:
                    break
                if not raw.endswith(b"\n"):
                    handle.seek(start)
                    break
                try:
                    payload = json.loads(raw.decode("utf-8"))
                    _validate_rule_event(payload, binding)
                except (UnicodeError, ValueError, TypeError, json.JSONDecodeError) as error:
                    bad_line = f"invalid JSONL record at line {line_number + 1}: {error}"
                    handle.seek(start)
                    break
                payloads.append(payload)
                offset = handle.tell()
                line_number += 1

        inserted = 0
        for payload in payloads:
            event_id = _event_id(binding.pipeline_snapshot_id, payload)
            exists = session.scalar(
                select(RuleEventRaw.id).where(
                    RuleEventRaw.analysis_id == binding.analysis_id,
                    RuleEventRaw.attempt == binding.attempt,
                    RuleEventRaw.event_id == event_id,
                )
            )
            if exists is None:
                session.add(
                    RuleEventRaw(
                        analysis_id=binding.analysis_id,
                        attempt=binding.attempt,
                        event_id=event_id,
                        event_type=str(payload["event"]),
                        payload_json=payload,
                        observed_at=datetime.now(timezone.utc),
                    )
                )
                inserted += 1
        session.flush()
        _rebuild_rule_projection(session, binding.analysis_id, binding.attempt)
        cursor.file_identity = identity
        cursor.byte_offset = offset
        cursor.line_number = line_number
        cursor.observed_size = stat.st_size
        cursor.observed_mtime_ns = stat.st_mtime_ns
        cursor.last_error = bad_line
        cursor.last_success_at = datetime.now(timezone.utc) if bad_line is None else cursor.last_success_at
        cursor.updated_at = datetime.now(timezone.utc)
        session.commit()
        return inserted, bad_line is not None


def _validate_rule_event(payload: object, binding: EvidenceBinding) -> None:
    if not isinstance(payload, dict):
        raise ValueError("event must be a JSON object")
    if str(payload.get("schema_version")) != "1":
        raise ValueError("unsupported event schema_version")
    if payload.get("event") not in RULE_EVENT_TYPES:
        raise ValueError("unsupported Rule event")
    if str(payload.get("run_label")) != binding.run_label:
        raise ValueError("event run_label does not match binding")
    try:
        attempt = int(payload.get("attempt"))
        float(payload.get("timestamp"))
    except (TypeError, ValueError) as error:
        raise ValueError("event attempt and timestamp must be numeric") from error
    if attempt != binding.attempt:
        raise ValueError("event attempt does not match binding")
    if payload.get("role") not in {"master", "worker"}:
        raise ValueError("event role must be master or worker")
    if not str(payload.get("stream_id") or ""):
        raise ValueError("event stream_id is required")


def _ingest_kubernetes_file(
    session_factory,
    evidence_root: Path,
    binding: EvidenceBinding,
    path: Path,
) -> tuple[int, bool]:
    relative_path = _safe_relative(path, evidence_root)
    stat = path.stat()
    identity = f"{stat.st_dev}:{stat.st_ino}"
    with session_factory() as session:
        cursor = _get_or_create_cursor(session, binding, relative_path)
        if (
            cursor.file_identity not in {None, identity}
            or stat.st_size < cursor.byte_offset
        ):
            cursor.byte_offset = 0
            cursor.line_number = 0
            cursor.last_error = None
        offset = cursor.byte_offset
        line_number = cursor.line_number
        payloads: list[dict] = []
        bad_line: str | None = None
        with path.open("rb") as handle:
            handle.seek(offset)
            while True:
                start = handle.tell()
                raw = handle.readline()
                if not raw:
                    break
                if not raw.endswith(b"\n"):
                    handle.seek(start)
                    break
                try:
                    payload = json.loads(raw.decode("utf-8"))
                    _validate_kubernetes_event(payload, path.name)
                except (UnicodeError, ValueError, TypeError, json.JSONDecodeError) as error:
                    bad_line = f"invalid JSONL record at line {line_number + 1}: {error}"
                    handle.seek(start)
                    break
                payloads.append(payload)
                offset = handle.tell()
                line_number += 1

        for payload in payloads:
            if path.name == "pod-events.jsonl":
                _apply_pod_event(session, binding, relative_path, payload)
            elif path.name == "pod-metrics.jsonl":
                _apply_pod_metrics(session, binding, payload)
            else:
                _apply_job_event(session, binding, payload)
        cursor.file_identity = identity
        cursor.byte_offset = offset
        cursor.line_number = line_number
        cursor.observed_size = stat.st_size
        cursor.observed_mtime_ns = stat.st_mtime_ns
        cursor.last_error = bad_line
        cursor.last_success_at = datetime.now(timezone.utc) if bad_line is None else cursor.last_success_at
        cursor.updated_at = datetime.now(timezone.utc)
        session.commit()
        return len(payloads), bad_line is not None


def _validate_kubernetes_event(payload: object, filename: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError("event must be a JSON object")
    if not str(payload.get("event_key") or ""):
        raise ValueError("event_key is required")
    _iso_time(payload.get("observed_at_utc"))
    if filename in {"pod-events.jsonl", "pod-metrics.jsonl"} and not str(
        payload.get("pod_hash") or ""
    ):
        raise ValueError("pod_hash is required")
    if filename == "pod-events.jsonl":
        _resource_version(payload.get("resource_version"))
    if filename == "job-events.jsonl":
        if not str(payload.get("job") or ""):
            raise ValueError("job is required")
        _resource_version(payload.get("resource_version"))


def _apply_pod_event(
    session, binding: EvidenceBinding, relative_path: str, payload: dict
) -> None:
    pod_hash = str(payload["pod_hash"])
    row = session.scalar(
        select(KubernetesWorkload).where(
            KubernetesWorkload.analysis_id == binding.analysis_id,
            KubernetesWorkload.attempt == binding.attempt,
            KubernetesWorkload.pod_hash == pod_hash,
        )
    )
    incoming_version = str(payload.get("resource_version") or "0")
    if row is None:
        row = KubernetesWorkload(
            analysis_id=binding.analysis_id,
            attempt=binding.attempt,
            event_id=str(payload["event_key"]),
            pod_hash=pod_hash,
            phase=str(payload.get("phase") or "Unknown"),
            resources_json={},
        )
        session.add(row)
        session.flush()
    elif _resource_version(incoming_version) < _resource_version(row.resource_version):
        return
    row.event_id = str(payload["event_key"])
    row.resource_version = incoming_version
    row.job_name = str(payload.get("job") or row.job_name or "") or None
    row.phase = str(payload.get("phase") or row.phase or "Unknown")
    row.observed_at = _iso_time(payload.get("observed_at_utc"))
    row.node_name = str(payload.get("node_name") or row.node_name or "") or None
    container = payload.get("container") if isinstance(payload.get("container"), dict) else {}
    container_status = payload.get("container_status") if isinstance(payload.get("container_status"), dict) else {}
    state = container_status.get("state") if isinstance(container_status.get("state"), dict) else {}
    detail = next(
        (value for key in ("terminated", "waiting", "running") if isinstance((value := state.get(key)), dict)),
        {},
    )
    row.reason = str(detail.get("reason") or payload.get("reason") or row.reason or "") or None
    row.message = str(detail.get("message") or payload.get("message") or row.message or "") or None
    exit_code = detail.get("exitCode", payload.get("exit_code"))
    row.exit_code = int(exit_code) if exit_code is not None else row.exit_code
    row.image_id = str(container_status.get("imageID") or payload.get("image_id") or row.image_id or "") or None
    if isinstance(container.get("resources"), dict) and container["resources"]:
        row.resources_json = container["resources"]
    row.evidence_path = relative_path
    row.updated_at = datetime.now(timezone.utc)


def _apply_pod_metrics(session, binding: EvidenceBinding, payload: dict) -> None:
    row = session.scalar(
        select(KubernetesWorkload).where(
            KubernetesWorkload.analysis_id == binding.analysis_id,
            KubernetesWorkload.attempt == binding.attempt,
            KubernetesWorkload.pod_hash == str(payload["pod_hash"]),
        )
    )
    if row is not None and isinstance(payload.get("metrics"), dict):
        row.resources_json = payload["metrics"]
        row.updated_at = datetime.now(timezone.utc)


def _apply_job_event(session, binding: EvidenceBinding, payload: dict) -> None:
    rows = session.scalars(
        select(KubernetesWorkload).where(
            KubernetesWorkload.analysis_id == binding.analysis_id,
            KubernetesWorkload.attempt == binding.attempt,
            KubernetesWorkload.job_name == str(payload["job"]),
        )
    ).all()
    status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
    conditions = status.get("conditions") if isinstance(status.get("conditions"), list) else []
    condition = next(
        (item for item in reversed(conditions) if isinstance(item, dict)), {}
    )
    for row in rows:
        row.job_status_json = status
        if not row.reason:
            row.reason = str(condition.get("reason") or "") or None
        row.message = str(condition.get("message") or row.message or "") or None
        row.updated_at = datetime.now(timezone.utc)


def _resource_version(value: object) -> int:
    try:
        return int(str(value or "0"))
    except ValueError as error:
        raise ValueError("resource_version must be numeric") from error


def _iso_time(value: object) -> datetime:
    text = str(value or "")
    if not text:
        raise ValueError("observed_at_utc is required")
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("observed_at_utc must be ISO-8601") from error


def _rebuild_rule_projection(session, analysis_id: str, attempt: int) -> None:
    rows = session.scalars(
        select(RuleEventRaw).where(
            RuleEventRaw.analysis_id == analysis_id,
            RuleEventRaw.attempt == attempt,
        )
    ).all()
    events = [row.payload_json for row in rows]
    job_map: dict[tuple[str, str], str] = {}
    for event in events:
        if event.get("event") == "job_info" and event.get("rule_instance_id"):
            job_map[(str(event.get("stream_id")), str(event.get("job_id")))] = str(
                event["rule_instance_id"]
            )

    grouped: dict[str, list[dict]] = {}
    for event in events:
        instance = str(event.get("rule_instance_id") or "")
        if not instance and event.get("job_id") is not None:
            instance = job_map.get(
                (str(event.get("stream_id")), str(event.get("job_id"))), ""
            )
        if instance:
            grouped.setdefault(instance, []).append(event)

    for instance, instance_events in grouped.items():
        ordered = sorted(instance_events, key=lambda item: float(item.get("timestamp", 0)))
        descriptive = next(
            (
                event
                for event in ordered
                if event.get("rule_name") and event.get("event") in {"rule_planned", "job_info"}
            ),
            {},
        )
        state = session.scalar(
            select(RuleState).where(
                RuleState.analysis_id == analysis_id,
                RuleState.attempt == attempt,
                RuleState.rule_instance_id == instance,
            )
        )
        if state is None:
            state = RuleState(
                analysis_id=analysis_id,
                attempt=attempt,
                rule_instance_id=instance,
                rule_name=str(descriptive.get("rule_name") or "unknown"),
                layer=descriptive.get("layer"),
                status="planned",
            )
            session.add(state)
        state.rule_name = str(descriptive.get("rule_name") or state.rule_name)
        state.layer = descriptive.get("layer", state.layer)
        state.status = "planned"
        state.started_at = None
        state.ended_at = None
        worker_terminal = any(
            event.get("role") == "worker" and event.get("event") in TERMINAL_RULE_EVENTS
            for event in ordered
        )
        for event in ordered:
            event_type = str(event.get("event"))
            when = _event_time(event)
            if event_type == "job_started":
                state.status = "running"
                state.started_at = state.started_at or when
            elif event_type in TERMINAL_RULE_EVENTS:
                if worker_terminal and event.get("role") != "worker":
                    continue
                state.status = TERMINAL_RULE_EVENTS[event_type]
                state.ended_at = when
        state.updated_at = datetime.now(timezone.utc)


def _get_or_create_cursor(
    session, binding: EvidenceBinding, relative_path: str
) -> EvidenceCursor:
    cursor = session.scalar(
        select(EvidenceCursor).where(
            EvidenceCursor.analysis_id == binding.analysis_id,
            EvidenceCursor.attempt == binding.attempt,
            EvidenceCursor.relative_path == relative_path,
        )
    )
    if cursor is None:
        cursor = EvidenceCursor(
            analysis_id=binding.analysis_id,
            attempt=binding.attempt,
            relative_path=relative_path,
            byte_offset=0,
            line_number=0,
            observed_size=0,
            observed_mtime_ns=0,
        )
        session.add(cursor)
    return cursor


def _record_file_error(
    session_factory,
    evidence_root: Path,
    binding: EvidenceBinding,
    path: Path,
    message: str,
) -> None:
    with session_factory() as session:
        cursor = _get_or_create_cursor(
            session, binding, _safe_relative(path, evidence_root)
        )
        cursor.last_error = message
        cursor.updated_at = datetime.now(timezone.utc)
        session.commit()


def _set_observer_status(
    session_factory,
    binding: EvidenceBinding,
    *,
    status: str,
    error: str | None,
) -> None:
    with session_factory() as session:
        state = session.scalar(
            select(ObserverRunState).where(
                ObserverRunState.analysis_id == binding.analysis_id,
                ObserverRunState.attempt == binding.attempt,
            )
        )
        if state is None:
            return
        state.status = status
        state.last_error = error
        state.last_success_at = datetime.now(timezone.utc) if not error else state.last_success_at
        state.updated_at = datetime.now(timezone.utc)
        session.commit()


def _safe_relative(path: Path, evidence_root: Path) -> str:
    resolved = path.resolve()
    if evidence_root not in resolved.parents:
        raise ValueError("evidence file escapes evidence root")
    return resolved.relative_to(evidence_root).as_posix()


def _event_id(snapshot_id: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{snapshot_id}\0{canonical}".encode()).hexdigest()


def _event_time(payload: dict) -> datetime:
    return datetime.fromtimestamp(float(payload["timestamp"]), tz=timezone.utc)
