from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from sqlalchemy import select

from app.models import (
    AnalysisRun,
    EvidenceCursor,
    KubernetesWorkload,
    ObserverRunState,
    RuleEventRaw,
    RuleState,
    RunAttempt,
    TransferJob,
    WgsMaintenanceAction,
)
from app.wgs_evidence_binding import EvidenceBinding, load_evidence_bindings
from app.wgs_release_catalog import load_wgs_release_catalog


RULE_EVENT_TYPES = {
    "rule_planned",
    "job_info",
    "job_started",
    "job_finished",
    "job_error",
    "group_error",
}
TERMINAL_RULE_EVENTS = {
    "job_finished": "success",
    "job_error": "failed",
    "group_error": "failed",
}


def ingest_evidence_once(
    *,
    session_factory,
    evidence_root: Path,
    binding_root: Path,
    catalog_path: Path,
    transfer_spool_root: Path | None = None,
    runtime_root: Path | None = None,
) -> dict[str, int]:
    catalog = load_wgs_release_catalog(catalog_path)
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
        degraded_marker = binding.evidence_directory / "LOGGER_DEGRADED.json"
        if not degraded_marker.is_file():
            degraded_marker = (
                binding.evidence_directory / "rule-status" / "LOGGER_DEGRADED.json"
            )
        monitoring_error = None
        if degraded_marker.is_file():
            try:
                marker = json.loads(degraded_marker.read_text(encoding="utf-8"))
                monitoring_error = str(
                    marker.get("message") or marker.get("error") or "Rule logger degraded"
                )
            except (OSError, UnicodeError, json.JSONDecodeError):
                monitoring_error = "Rule logger degraded (marker is unreadable)"
        _set_observer_status(
            session_factory,
            binding,
            status="degraded" if binding_errors or monitoring_error else "healthy",
            error=(
                "one or more evidence files could not be consumed"
                if binding_errors
                else monitoring_error
            ),
        )
    if transfer_spool_root is not None and transfer_spool_root.is_dir():
        for path in sorted(transfer_spool_root.glob("**/progress.json")):
            result["files"] += 1
            try:
                if _ingest_transfer_progress(session_factory, transfer_spool_root.resolve(), path):
                    result["events_ingested"] += 1
            except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
                result["errors"] += 1
    if runtime_root is not None and runtime_root.is_dir():
        for path in sorted(runtime_root.glob("runs/*/attempt-*/batch-binding.json")):
            result["files"] += 1
            try:
                if _ingest_runtime_binding(
                    session_factory, runtime_root.resolve(), path
                ):
                    result["events_ingested"] += 1
            except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
                result["errors"] += 1
        request_root = runtime_root / "runner-requests"
        for path in sorted(request_root.glob("**/*.status.json")):
            if path.name not in {
                "step1_upload.status.json",
                "step3_monitor.status.json",
                "step4_repair_cram.status.json",
                "step5_download.status.json",
            }:
                continue
            result["files"] += 1
            try:
                if _ingest_runtime_stage_status(
                    session_factory, request_root.resolve(), path
                ):
                    result["events_ingested"] += 1
            except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
                result["errors"] += 1
    return result


def ingest_observer_attempt_once(
    *,
    session_factory,
    evidence_root: Path,
    analysis_id: str,
    attempt: int,
) -> dict[str, int | str]:
    """Consume evidence for one explicitly activated WGS attempt only."""

    root = evidence_root.resolve()
    with session_factory() as session:
        state = session.scalar(
            select(ObserverRunState).where(
                ObserverRunState.analysis_id == analysis_id,
                ObserverRunState.attempt == attempt,
                ObserverRunState.lifecycle_status.in_(("active", "draining")),
            )
        )
        if state is None:
            return {
                "files": 0,
                "events_ingested": 0,
                "errors": 0,
                "lifecycle_status": "stopped",
            }
        relative = Path(state.relative_evidence_path)
        directory = (root / relative).resolve()
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or root not in directory.parents
        ):
            raise ValueError("observer evidence path escapes evidence root")
        binding = EvidenceBinding(
            analysis_id=state.analysis_id,
            attempt=state.attempt,
            pipeline_release_id=state.pipeline_release_id,
            run_label=state.run_label,
            evidence_path=relative.as_posix(),
            evidence_directory=directory,
            source_path=Path("<database-activation>"),
        )
        initial_lifecycle = state.lifecycle_status

    result: dict[str, int | str] = {
        "files": 0,
        "events_ingested": 0,
        "errors": 0,
        "lifecycle_status": initial_lifecycle,
    }
    rule_paths = sorted((directory / "rule-status" / "raw").glob("*.jsonl"))
    raw_root = directory / "raw"
    k8s_paths = [
        raw_root / name
        for name in ("pod-events.jsonl", "pod-metrics.jsonl", "job-events.jsonl")
        if (raw_root / name).is_file()
    ]
    binding_errors = 0
    for path, reader in [
        *((path, _ingest_rule_file) for path in rule_paths),
        *((path, _ingest_kubernetes_file) for path in k8s_paths),
    ]:
        result["files"] = int(result["files"]) + 1
        try:
            count, had_error = reader(session_factory, root, binding, path)
            result["events_ingested"] = int(result["events_ingested"]) + count
            if had_error:
                binding_errors += 1
                result["errors"] = int(result["errors"]) + 1
        except (OSError, UnicodeError, ValueError) as error:
            binding_errors += 1
            result["errors"] = int(result["errors"]) + 1
            _record_file_error(session_factory, root, binding, path, str(error))

    degraded = directory / "LOGGER_DEGRADED.json"
    if not degraded.is_file():
        degraded = directory / "rule-status" / "LOGGER_DEGRADED.json"
    monitoring_error = None
    if degraded.is_file():
        try:
            marker = json.loads(degraded.read_text(encoding="utf-8"))
            monitoring_error = str(
                marker.get("message") or marker.get("error") or "Rule logger degraded"
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            monitoring_error = "Rule logger degraded (marker is unreadable)"
    _set_observer_status(
        session_factory,
        binding,
        status="degraded" if binding_errors or monitoring_error else "healthy",
        error=(
            "one or more evidence files could not be consumed"
            if binding_errors
            else monitoring_error
        ),
    )

    with session_factory() as session:
        current = session.scalar(
            select(ObserverRunState).where(
                ObserverRunState.analysis_id == analysis_id,
                ObserverRunState.attempt == attempt,
            )
        )
        if current is None or current.lifecycle_status == "stopped":
            result["lifecycle_status"] = "stopped"
        elif current.lifecycle_status == "draining":
            current.lifecycle_status = "stopped"
            current.deactivated_at = datetime.now(timezone.utc)
            current.updated_at = current.deactivated_at
            session.commit()
            result["lifecycle_status"] = "stopped"
        else:
            result["lifecycle_status"] = "active"
    return result


def _ingest_runtime_binding(session_factory, runtime_root: Path, path: Path) -> bool:
    resolved = path.resolve()
    if runtime_root not in resolved.parents:
        raise ValueError("runtime binding escapes runtime root")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "wgs-runtime.batch-binding.v2":
        raise ValueError("unsupported runtime binding schema")
    analysis_id = str(payload.get("analysis_id") or "")
    attempt = int(payload.get("attempt") or 0)
    release_id = str(payload.get("pipeline_release_id") or "")
    source_commit = str(payload.get("wgs_source_commit") or "")
    source = payload.get("resolved_runtime")
    if not isinstance(source, dict):
        raise ValueError("runtime binding resolved_runtime is required")
    allowed = {
        "cce_pipeline_version",
        "cce_pipeline_source_commit",
        "profile_id",
        "profile_revision",
        "profile_sha256",
        "master_image_digest",
        "pipeline_build_sha256",
        "resource_manifest_sha256",
    }
    resolved_runtime = {key: str(source.get(key) or "") for key in sorted(allowed)}
    repair_groups = source.get("repair_groups")
    if isinstance(repair_groups, dict) and isinstance(repair_groups.get("cram"), dict):
        target = str(repair_groups["cram"].get("target") or "")
        target_path = PurePosixPath(target)
        if target and not target_path.is_absolute() and ".." not in target_path.parts:
            resolved_runtime["repair_groups"] = {"cram": {"target": target}}
    with session_factory() as session:
        analysis = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        if analysis is None or analysis.attempt != attempt:
            raise ValueError("runtime binding references an unknown active attempt")
        params = dict(analysis.params_json or {})
        if params.get("pipeline_release_id") != release_id:
            raise ValueError("runtime binding release does not match analysis")
        if params.get("wgs_source_commit") != source_commit:
            raise ValueError("runtime binding WGS commit does not match analysis")
        if params.get("resolved_runtime") == resolved_runtime:
            return False
        analysis.params_json = {**params, "resolved_runtime": resolved_runtime}
        session.commit()
    return True


def sync_runtime_stage_artifacts(
    *,
    session_factory,
    request_root: Path,
    transfer_spool_root: Path,
    analysis_id: str,
    attempt: int,
    stage: str,
) -> dict[str, int]:
    """Sync only the status/progress files registered for one sensor poke."""

    if stage not in {
        "step1_upload",
        "step3_monitor",
        "step4_publish",
        "step4_repair_cram",
        "step5_download",
        "step6_materialize",
    }:
        raise ValueError("unsupported runtime stage sync")
    result = {"files": 0, "events_ingested": 0}
    request_root = request_root.resolve()
    transfer_spool_root = transfer_spool_root.resolve()
    runtime_root = request_root.parent
    binding_path = (
        runtime_root
        / "runs"
        / analysis_id
        / f"attempt-{attempt}"
        / "batch-binding.json"
    )
    if binding_path.is_file():
        result["files"] += 1
        if _ingest_runtime_binding(session_factory, runtime_root, binding_path):
            result["events_ingested"] += 1
    status_path = (
        request_root
        / analysis_id
        / f"attempt-{attempt}"
        / f"{stage}.status.json"
    )
    if status_path.is_file() and stage in {
        "step1_upload",
        "step3_monitor",
        "step4_repair_cram",
        "step5_download",
    }:
        result["files"] += 1
        if _ingest_runtime_stage_status(session_factory, request_root, status_path):
            result["events_ingested"] += 1
    if stage in {"step1_upload", "step5_download"}:
        kind = "input" if stage == "step1_upload" else "result"
        transfer_id = f"{analysis_id}-a{attempt}-{kind}"
        progress_path = (
            transfer_spool_root
            / analysis_id
            / f"attempt-{attempt}"
            / transfer_id
            / "progress.json"
        )
        if progress_path.is_file():
            result["files"] += 1
            if _ingest_transfer_progress(
                session_factory, transfer_spool_root, progress_path
            ):
                result["events_ingested"] += 1
    return result


def _ingest_runtime_stage_status(session_factory, request_root: Path, path: Path) -> bool:
    resolved = path.resolve()
    if request_root not in resolved.parents:
        raise ValueError("runtime stage status escapes request root")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "wgs-runtime.stage-status.v1":
        raise ValueError("unsupported runtime stage status schema")
    analysis_id = str(payload.get("analysis_id") or "")
    attempt = int(payload.get("attempt") or 0)
    stage = str(payload.get("stage") or "")
    status = str(payload.get("status") or "")
    heartbeat = datetime.fromisoformat(
        str(payload.get("updated_at") or "").replace("Z", "+00:00")
    )
    if stage not in {
        "step1_upload",
        "step3_monitor",
        "step4_repair_cram",
        "step5_download",
    }:
        raise ValueError("unsupported runtime stage status")
    with session_factory() as session:
        analysis = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        if analysis is None or analysis.attempt != attempt:
            raise ValueError("runtime stage status references an unknown active attempt")
        if stage == "step4_repair_cram":
            action = session.scalar(
                select(WgsMaintenanceAction).where(
                    WgsMaintenanceAction.analysis_id == analysis_id,
                    WgsMaintenanceAction.attempt == attempt,
                    WgsMaintenanceAction.action_type == "repair_step4_cram",
                )
            )
            if action is None:
                raise ValueError("Step4 repair status has no registered maintenance action")
            previous = action.updated_at
            if previous is not None:
                if previous.tzinfo is None:
                    previous = previous.replace(tzinfo=timezone.utc)
                if action.evidence_path and heartbeat <= previous:
                    return False
            normalized = {
                "accepted": "queued",
                "running": "running",
                "success": "success",
                "failed": "failed",
            }.get(status)
            if normalized is None:
                raise ValueError("Step4 repair status is invalid")
            action.status = normalized
            action.evidence_path = str(resolved.relative_to(request_root))
            action.error_message = (
                str(payload.get("message") or "") or None
                if normalized == "failed"
                else None
            )
            if normalized == "running" and action.started_at is None:
                action.started_at = heartbeat
            if normalized in {"success", "failed"}:
                action.ended_at = heartbeat
            action.updated_at = heartbeat
        elif stage in {"step1_upload", "step5_download"}:
            kind = "input" if stage == "step1_upload" else "result"
            transfer_id = f"{analysis_id}-a{attempt}-{kind}"
            row = session.scalar(
                select(TransferJob).where(TransferJob.transfer_id == transfer_id)
            )
            if row is not None and row.heartbeat_at is not None:
                previous = row.heartbeat_at
                if previous.tzinfo is None:
                    previous = previous.replace(tzinfo=timezone.utc)
                if heartbeat <= previous:
                    return False
            if row is None:
                row = TransferJob(
                    analysis_id=analysis_id,
                    attempt=attempt,
                    transfer_id=transfer_id,
                    direction="upload" if kind == "input" else "download",
                    status=status,
                )
                session.add(row)
            row.transfer_type = "input_upload" if kind == "input" else "result_download"
            row.status = status
            row.progress_detail_available = False
            row.heartbeat_at = heartbeat
            row.message = str(payload.get("message") or "") or None
            row.error_message = row.message if status == "failed" else None
            row.updated_at = datetime.now(timezone.utc)
        else:
            monitoring_health = str(payload.get("monitoring_health") or "healthy")
            if monitoring_health not in {"healthy", "degraded"}:
                raise ValueError("Step3 monitoring health is invalid")
            if monitoring_health == "degraded":
                _mark_runtime_monitoring_degraded(
                    session,
                    analysis_id,
                    attempt,
                    str(
                        payload.get("monitoring_error")
                        or "Rule evidence bridge failed"
                    ),
                )
            master_job = str(payload.get("master_job") or "")
            if not master_job.startswith("wgs-master-"):
                raise ValueError("Step3 status is missing the opaque Master Job name")
            master = payload.get("master") if isinstance(payload.get("master"), dict) else {}
            master_state = str(master.get("master_state") or "PENDING")
            phase = {
                "PENDING": "Pending",
                "RUNNING": "Running",
                "SUCCEEDED": "Succeeded",
                "FAILED": "Failed",
            }.get(master_state)
            if phase is None:
                raise ValueError("Step3 Master state is invalid")
            pod_hash = hashlib.sha256(master_job.encode("utf-8")).hexdigest()[:32]
            row = session.scalar(
                select(KubernetesWorkload).where(
                    KubernetesWorkload.analysis_id == analysis_id,
                    KubernetesWorkload.attempt == attempt,
                    KubernetesWorkload.pod_hash == pod_hash,
                )
            )
            if row is not None and row.observed_at is not None:
                previous = row.observed_at
                if previous.tzinfo is None:
                    previous = previous.replace(tzinfo=timezone.utc)
                if heartbeat <= previous:
                    if monitoring_health == "degraded":
                        session.commit()
                    return False
            if row is None:
                row = KubernetesWorkload(
                    analysis_id=analysis_id,
                    attempt=attempt,
                    event_id=f"step3:{master_job}",
                    pod_hash=pod_hash,
                    job_name=master_job,
                    phase=phase,
                )
                session.add(row)
            row.phase = phase
            row.reason = "MasterFailed" if master_state == "FAILED" else None
            row.message = str(master.get("message") or payload.get("message") or "") or None
            row.job_status_json = master
            row.observed_at = heartbeat
            row.updated_at = datetime.now(timezone.utc)
        session.commit()
        return True


def _mark_runtime_monitoring_degraded(
    session, analysis_id: str, attempt: int, error: str
) -> None:
    observer = session.scalar(
        select(ObserverRunState).where(
            ObserverRunState.analysis_id == analysis_id,
            ObserverRunState.attempt == attempt,
        )
    )
    if observer is not None:
        observer.monitoring_health = "degraded"
        observer.last_error = error[-2000:]
        observer.updated_at = datetime.now(timezone.utc)


def _ingest_transfer_progress(session_factory, spool_root: Path, path: Path) -> bool:
    resolved = path.resolve()
    if spool_root not in resolved.parents:
        raise ValueError("transfer progress file escapes spool root")
    payload = _normalize_transfer_progress(
        json.loads(path.read_text(encoding="utf-8"))
    )
    required = ("analysis_id", "attempt", "transfer_id", "transfer_type", "direction", "status", "heartbeat_at")
    if any(payload.get(name) in {None, ""} for name in required):
        raise ValueError("transfer progress is missing required fields")
    heartbeat = datetime.fromisoformat(str(payload["heartbeat_at"]).replace("Z", "+00:00"))
    with session_factory() as session:
        analysis = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == str(payload["analysis_id"])))
        if analysis is None or analysis.attempt != int(payload["attempt"]):
            raise ValueError("transfer progress references an unknown active attempt")
        row = session.scalar(select(TransferJob).where(TransferJob.transfer_id == str(payload["transfer_id"])))
        if row is not None and row.heartbeat_at is not None:
            previous = row.heartbeat_at if row.heartbeat_at.tzinfo else row.heartbeat_at.replace(tzinfo=timezone.utc)
            if heartbeat <= previous:
                return False
        if row is None:
            row = TransferJob(analysis_id=analysis.analysis_id, attempt=analysis.attempt, transfer_id=str(payload["transfer_id"]), direction=str(payload["direction"]), status=str(payload["status"]))
            session.add(row)
        elif row.analysis_id != analysis.analysis_id or row.attempt != analysis.attempt:
            raise ValueError("transfer_id is already bound to another attempt")
        row.transfer_type = str(payload["transfer_type"])
        row.source = str(payload.get("source") or "") or None
        row.destination = str(payload.get("destination") or "") or None
        row.status = str(payload["status"])
        row.bytes_total = max(0, int(payload.get("bytes_total") or 0))
        row.bytes_transferred = max(0, int(payload.get("bytes_transferred") or 0))
        row.files_total = max(0, int(payload.get("files_total") or 0))
        row.files_completed = max(0, int(payload.get("files_completed") or 0))
        row.current_file = str(payload.get("current_file") or "") or None
        row.progress_percent = max(0, min(100, int(round(float(payload.get("progress_percent") or 0)))))
        row.speed_bps = max(0, int(payload.get("speed_bps") or 0))
        row.progress_detail_available = True
        row.eta_seconds = max(0, int(payload["eta_seconds"])) if payload.get("eta_seconds") is not None else None
        row.estimated_finish_at = datetime.fromisoformat(str(payload["estimated_finish_at"]).replace("Z", "+00:00")) if payload.get("estimated_finish_at") else None
        row.checkpoint_ref = str(payload.get("checkpoint_ref") or "") or None
        row.heartbeat_at = heartbeat
        row.verification_status = str(payload.get("verification_status") or "") or None
        row.message = str(payload.get("message") or "") or None
        row.error_message = str(payload.get("error_message") or "") or None
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        return True


def _normalize_transfer_progress(payload: dict) -> dict:
    """Translate cce-pipeline schema v1 to the stable biodemo/API vocabulary."""
    if payload.get("schema_version") != "cce-pipeline.transfer-progress.v1":
        return payload
    normalized = dict(payload)
    direction = str(payload.get("direction") or "")
    normalized["transfer_type"] = {
        "upload": "input_upload",
        "download": "result_download",
    }.get(direction, direction)
    normalized["status"] = payload.get("state")
    normalized["bytes_transferred"] = payload.get("bytes_done", 0)
    normalized["files_completed"] = payload.get("files_done", 0)
    normalized["speed_bps"] = payload.get("speed_bytes_per_second", 0)
    normalized["estimated_finish_at"] = payload.get("estimated_completion_at")
    normalized["checkpoint_ref"] = payload.get("checkpoint_path")
    normalized["error_message"] = payload.get("error_summary")
    total = max(0, int(payload.get("bytes_total") or 0))
    done = max(0, int(payload.get("bytes_done") or 0))
    normalized["progress_percent"] = min(100, (done * 100 / total) if total else 0)
    return normalized


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
        if attempt.run_label is None:
            attempt.run_label = binding.run_label
        elif attempt.run_label != binding.run_label:
            return "binding run_label does not match analysis attempt"
        if analysis.params_json.get("pipeline_release_id") != binding.pipeline_release_id:
            return "binding release does not match analysis"
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
                pipeline_release_id=binding.pipeline_release_id,
                run_label=binding.run_label,
                relative_evidence_path=binding.evidence_path,
                lifecycle_status="stopped",
                monitoring_health="healthy",
            )
            session.add(state)
        elif (
            state.pipeline_release_id != binding.pipeline_release_id
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
            event_id = str(
                payload.get("event_id") or _event_id(binding.pipeline_release_id, payload)
            )
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
    schema_version = str(payload.get("schema_version"))
    if schema_version not in {"1", "rule-event.v1"}:
        raise ValueError("unsupported event schema_version")
    if payload.get("event") not in RULE_EVENT_TYPES:
        raise ValueError("unsupported Rule event")
    attempt = _normalize_event_attempt(payload.get("attempt"))
    if schema_version == "rule-event.v1":
        if str(payload.get("analysis_id")) != binding.analysis_id:
            raise ValueError("event analysis_id does not match binding")
        if str(payload.get("run_id") or "") == "":
            raise ValueError("event run_id is required")
        if str(payload.get("pipeline_release_id")) != binding.pipeline_release_id:
            raise ValueError("event pipeline_release_id does not match binding")
        if not str(payload.get("event_id") or ""):
            raise ValueError("event_id is required")
        try:
            int(payload.get("sequence"))
            datetime.fromisoformat(str(payload.get("timestamp")).replace("Z", "+00:00"))
        except (TypeError, ValueError) as error:
            raise ValueError("event sequence and timestamp are invalid") from error
    else:
        if str(payload.get("run_label")) != binding.run_label:
            raise ValueError("event run_label does not match binding")
        try:
            float(payload.get("timestamp"))
        except (TypeError, ValueError) as error:
            raise ValueError("event timestamp must be numeric") from error
    if attempt != binding.attempt:
        raise ValueError("event attempt does not match binding")
    if schema_version == "1":
        if payload.get("role") not in {"master", "worker"}:
            raise ValueError("event role must be master or worker")
        if not str(payload.get("stream_id") or ""):
            raise ValueError("event stream_id is required")


def _normalize_event_attempt(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("event attempt must be a positive integer or attempt-N")
    if isinstance(value, int):
        attempt = value
    elif isinstance(value, str):
        match = re.fullmatch(r"(?:attempt-)?([1-9][0-9]*)", value.strip())
        if match is None:
            raise ValueError("event attempt must be a positive integer or attempt-N")
        attempt = int(match.group(1))
    else:
        raise ValueError("event attempt must be a positive integer or attempt-N")
    if attempt < 1:
        raise ValueError("event attempt must be a positive integer or attempt-N")
    return attempt


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
    if payload.get("workload_role", "master") != "master":
        raise ValueError("only Master workload evidence is accepted")
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
        ordered = sorted(instance_events, key=_event_order)
        descriptive = next(
            (
                event
                for event in ordered
                if event.get("rule_name") and event.get("event") in {"rule_planned", "job_info", "job_started"}
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
        state.sample_id = str(descriptive.get("sample_id") or "") or state.sample_id
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
                if worker_terminal and event.get("role") not in {None, "worker"}:
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
        state.monitoring_health = status
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
    value = payload["timestamp"]
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _event_order(payload: dict) -> tuple[int, datetime]:
    try:
        sequence = int(payload.get("sequence") or 0)
    except (TypeError, ValueError):
        sequence = 0
    return sequence, _event_time(payload)
