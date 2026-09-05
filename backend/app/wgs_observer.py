from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Iterator
from sqlalchemy import select

from app.models import (
    AnalysisRun,
    EvidenceCursor,
    KubernetesWorkload,
    ObserverRunState,
    RuleEventRaw,
    RuleState,
    RunAttempt,
    RunStageState,
    Sample,
    TransferJob,
    TransferFileState,
    WgsMaintenanceAction,
)
from app.wgs_evidence_binding import (
    CCE_RUN_LABEL_PATTERN,
    EvidenceBinding,
    load_evidence_bindings,
)
from app.wgs_release_catalog import load_wgs_release_catalog
from app.wgs_stage_contract import wgs_stage_definition
from app.wgs_stage_execution_service import (
    transition_latest_stage_execution,
    transition_stage_execution,
    validate_current_stage_execution,
)
from app.workflow_phases import phase_for_rule


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
KUBERNETES_DNS_LABEL_RE = re.compile(
    r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$"
)


@dataclass
class _AnalysisLogIndex:
    file_identity: tuple[int, int] | None = None
    byte_offset: int = 0
    rule_name: str = ""
    job_id: str = ""
    sample_id: str = ""
    contexts: set[tuple[str, str, str]] = field(default_factory=set)


_ANALYSIS_LOG_INDEX: dict[str, _AnalysisLogIndex] = {}
_ANALYSIS_LOG_INDEX_LIMIT = 256


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
        _enrich_from_registered_analysis_log(
            session_factory=session_factory,
            binding=binding,
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
    transfer_spool_root: Path | None = None,
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

    if transfer_spool_root is not None:
        transfer_root = transfer_spool_root.resolve()
        attempt_root = (
            transfer_root / analysis_id / f"attempt-{attempt}"
        ).resolve()
        if transfer_root not in attempt_root.parents:
            raise ValueError("transfer spool attempt path escapes configured root")
        for path in sorted(attempt_root.glob("*/progress.json")):
            result["files"] = int(result["files"]) + 1
            try:
                if _ingest_transfer_progress(session_factory, transfer_root, path):
                    result["events_ingested"] = int(result["events_ingested"]) + 1
            except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
                result["errors"] = int(result["errors"]) + 1

    _enrich_from_registered_analysis_log(
        session_factory=session_factory,
        binding=binding,
    )

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
    if initial_lifecycle == "draining" and not any(
        path.is_file() and path.stat().st_size > 0 for path in rule_paths
    ):
        monitoring_error = monitoring_error or "Rule event JSONL was not produced"
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


def _enrich_from_registered_analysis_log(*, session_factory, binding: EvidenceBinding) -> None:
    analysis_log = binding.evidence_directory / "mirror" / "analysis.log"
    if not analysis_log.is_file() or analysis_log.is_symlink():
        return
    with session_factory() as session:
        enrich_rule_states_from_analysis_log(
            session,
            analysis_id=binding.analysis_id,
            attempt=binding.attempt,
            analysis_log=analysis_log,
        )
        session.commit()


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


PREPARE_STATUS_STAGES = frozenset(
    {"prepare", "prepare_sampleinfo", "prepare_analysis"}
)
RUNTIME_ARTIFACT_STAGES = frozenset(
    {
        "step1_upload",
        "step3_monitor",
        "step4_publish",
        "step4_repair_cram",
        "step5_download",
        "step6_materialize",
        "step7_cleanup",
    }
)
SUPPORTED_RUNTIME_SYNC_STAGES = PREPARE_STATUS_STAGES | RUNTIME_ARTIFACT_STAGES


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

    if stage not in SUPPORTED_RUNTIME_SYNC_STAGES:
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
    if status_path.is_file():
        result["files"] += 1
        if _ingest_runtime_stage_status(session_factory, request_root, status_path):
            result["events_ingested"] += 1
    if stage in {"step1_upload", "step5_download"}:
        kind = "input" if stage == "step1_upload" else "result"
        transfer_id = f"{analysis_id}-a{attempt}-{kind}"
        candidate_paths = (
            transfer_spool_root / analysis_id / f"attempt-{attempt}" / stage / "progress.json",
            transfer_spool_root / analysis_id / f"attempt-{attempt}" / transfer_id / "progress.json",
        )
        progress_path = next((path for path in candidate_paths if path.is_file()), None)
        if progress_path is not None:
            result["files"] += 1
            if _ingest_transfer_progress(session_factory, transfer_spool_root, progress_path):
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
    terminal_receipt_hash = (
        hashlib.sha256(resolved.read_bytes()).hexdigest()
        if status in {"success", "complete", "succeeded", "failed", "canceled", "cancelled"}
        else None
    )
    retry_no = payload.get("retry_no", 0)
    if type(retry_no) is not int or retry_no < 0:
        raise ValueError("runtime stage retry_no must be a nonnegative integer")
    heartbeat = datetime.fromisoformat(
        str(payload.get("updated_at") or "").replace("Z", "+00:00")
    )
    if stage not in SUPPORTED_RUNTIME_SYNC_STAGES:
        raise ValueError("unsupported runtime stage status")
    with session_factory() as session:
        analysis = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        if analysis is None or analysis.attempt != attempt:
            raise ValueError("runtime stage status references an unknown active attempt")
        contract_v2 = int((analysis.params_json or {}).get("orchestration_contract_version") or 1) == 2
        if contract_v2:
            execution = _current_execution_from_payload(
                session=session,
                analysis_id=analysis_id,
                attempt=attempt,
                stage_code=stage,
                payload=payload,
            )
            if execution is None:
                return False
            if not transition_stage_execution(
                session=session,
                execution_id=execution.execution_id,
                generation=execution.generation,
                status={
                    "complete": "success",
                    "completed": "success",
                    "succeeded": "success",
                    "cancelled": "canceled",
                }.get(status, status),
                observed_at=heartbeat,
                receipt_hash=terminal_receipt_hash,
                evidence_type="wgs-runtime.stage-status.v1",
                evidence_key=str(resolved.relative_to(request_root)),
                terminal_payload={"retry_no": retry_no},
                message=str(payload.get("message") or "") or None,
            ):
                return False
        if stage in PREPARE_STATUS_STAGES:
            upsert_stage_state(
                session,
                analysis_id=analysis_id,
                attempt=attempt,
                stage_code=stage,
                stage_status=status,
                updated_at=heartbeat,
                message=str(payload.get("message") or "") or None,
                evidence_key=str(resolved.relative_to(request_root)),
                receipt_hash=terminal_receipt_hash,
            )
        elif stage == "step4_publish":
            if status not in {"accepted", "running", "success", "failed"}:
                raise ValueError("Step4 publish status is invalid")
            analysis.current_stage = stage
            if status == "failed":
                analysis.status = "failed"
                analysis.error_summary = str(payload.get("message") or "") or None
                analysis.ended_at = heartbeat
                analysis.pipeline_finished_at = heartbeat
            elif str(analysis.status or "").lower() not in {
                "failed",
                "cancelled",
                "success",
                "unknown_interrupted",
            }:
                analysis.status = "publishing"
                analysis.error_summary = None
                analysis.ended_at = None
                analysis.pipeline_finished_at = None
            upsert_stage_state(
                session,
                analysis_id=analysis_id,
                attempt=attempt,
                stage_code=stage,
                stage_status=status,
                updated_at=heartbeat,
                message=str(payload.get("message") or "") or None,
                evidence_key=str(resolved.relative_to(request_root)),
                receipt_hash=terminal_receipt_hash,
                allow_terminal_retry=retry_no > 0,
            )
        elif stage == "step4_repair_cram":
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
            upsert_stage_state(
                session,
                analysis_id=analysis_id,
                attempt=attempt,
                stage_code=stage,
                stage_status=status,
                updated_at=heartbeat,
                message=action.error_message,
                evidence_key=action.evidence_path,
                receipt_hash=terminal_receipt_hash,
            )
        elif stage in {"step1_upload", "step5_download"}:
            kind = "input" if stage == "step1_upload" else "result"
            transfer_id = f"{analysis_id}-a{attempt}-{kind}"
            detail = payload.get("transfer")
            normalized_detail = _normalize_transfer_progress(detail) if isinstance(detail, dict) else None
            if normalized_detail is not None and (
                normalized_detail.get("analysis_id") != analysis_id
                or int(normalized_detail.get("attempt", 0)) != attempt
                or normalized_detail.get("transfer_id") != transfer_id
            ):
                raise ValueError("runtime transfer progress identity mismatch")
            row = session.scalar(
                select(TransferJob).where(TransferJob.transfer_id == transfer_id)
            )
            current_stage_row = session.scalar(
                select(RunStageState).where(
                    RunStageState.analysis_id == analysis_id,
                    RunStageState.attempt == attempt,
                    RunStageState.stage_code == stage,
                )
            )
            if row is not None and row.heartbeat_at is not None:
                previous = row.heartbeat_at
                if previous.tzinfo is None:
                    previous = previous.replace(tzinfo=timezone.utc)
                retry_projection_pending = (
                    heartbeat == previous
                    and retry_no > 0
                    and current_stage_row is not None
                    and _canonical_terminal_status(current_stage_row.stage_status)
                    == "failed"
                    and _canonical_terminal_status(status) != "failed"
                )
                if heartbeat < previous or (
                    heartbeat == previous and not retry_projection_pending
                ):
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
            has_exact_progress = normalized_detail is not None or bool(row.progress_detail_available)
            row.transfer_type = "input_upload" if kind == "input" else "result_download"
            row.status = status
            row.progress_detail_available = has_exact_progress
            if normalized_detail is not None:
                row.bytes_total = int(normalized_detail["bytes_total"])
                row.bytes_transferred = int(normalized_detail["bytes_transferred"])
                row.files_total = int(normalized_detail["files_total"])
                row.files_completed = int(normalized_detail["files_completed"])
                row.progress_percent = int(round(float(normalized_detail["progress_percent"])))
                row.speed_bps = int(normalized_detail["speed_bps"])
                row.eta_seconds = int(normalized_detail["eta_seconds"]) if normalized_detail.get("eta_seconds") is not None else None
                row.current_file = str(normalized_detail.get("current_file") or "") or None
                row.manifest_path = str(normalized_detail.get("plan_path") or "") or None
                _upsert_transfer_file_states(
                    session=session,
                    transfer=row,
                    files=(
                        normalized_detail["files"]
                        if isinstance(normalized_detail.get("files"), list)
                        else []
                    ),
                    heartbeat=heartbeat,
                )
            row.heartbeat_at = heartbeat
            row.message = str(payload.get("message") or "") or None
            row.error_message = row.message if status == "failed" else None
            row.updated_at = datetime.now(timezone.utc)
            progress_source = (
                str(detail.get("schema_version"))
                if isinstance(detail, dict)
                else (
                    current_stage_row.progress_source
                    if current_stage_row is not None and has_exact_progress
                    else "wgs-runtime.stage-status.v1"
                )
            )
            upsert_stage_state(
                session,
                analysis_id=analysis_id,
                attempt=attempt,
                stage_code=stage,
                stage_status=status,
                updated_at=heartbeat,
                progress_available=has_exact_progress,
                progress_percent=row.progress_percent if has_exact_progress else None,
                completed_units=row.bytes_transferred if has_exact_progress else None,
                total_units=row.bytes_total if has_exact_progress else None,
                unit="bytes" if has_exact_progress else None,
                current_item=row.current_file if has_exact_progress else None,
                speed_bps=row.speed_bps if has_exact_progress else None,
                eta_seconds=row.eta_seconds if has_exact_progress else None,
                message=row.message,
                evidence_key=str(resolved.relative_to(request_root)),
                receipt_hash=terminal_receipt_hash,
                progress_source=progress_source,
                allow_terminal_retry=retry_no > 0,
            )
        elif stage == "step7_cleanup":
            action = session.scalar(
                select(WgsMaintenanceAction).where(
                    WgsMaintenanceAction.analysis_id == analysis_id,
                    WgsMaintenanceAction.attempt == attempt,
                    WgsMaintenanceAction.action_type == "cleanup_step7_sfs",
                )
            )
            if action is None:
                raise ValueError("Step7 cleanup status has no registered maintenance action")
            normalized = {"accepted": "queued", "running": "running", "success": "success", "failed": "failed"}.get(status)
            if normalized is None:
                raise ValueError("Step7 cleanup status is invalid")
            action.status = normalized
            action.evidence_path = str(resolved.relative_to(request_root))
            action.error_message = (
                (str(payload.get("message") or "") or None)
                if normalized == "failed"
                else None
            )
            if normalized == "running" and action.started_at is None:
                action.started_at = heartbeat
            if normalized in {"success", "failed"}:
                action.ended_at = heartbeat
            action.updated_at = heartbeat
        elif stage == "step6_materialize":
            upsert_stage_state(
                session,
                analysis_id=analysis_id,
                attempt=attempt,
                stage_code=stage,
                stage_status=status,
                updated_at=heartbeat,
                message=str(payload.get("message") or "") or None,
                evidence_key=str(resolved.relative_to(request_root)),
                receipt_hash=terminal_receipt_hash,
            )
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
            master = payload.get("master") if isinstance(payload.get("master"), dict) else {}
            if not master_job or not master:
                if status in {"accepted", "running", "failed"}:
                    upsert_stage_state(
                        session,
                        analysis_id=analysis_id,
                        attempt=attempt,
                        stage_code=stage,
                        stage_status=status,
                        updated_at=heartbeat,
                        message=str(payload.get("message") or "") or None,
                        evidence_key=str(resolved.relative_to(request_root)),
                        receipt_hash=terminal_receipt_hash,
                    )
                    if monitoring_health == "degraded":
                        session.commit()
                    else:
                        session.commit()
                    return False
                raise ValueError("Step3 terminal success is missing Master evidence")
            if KUBERNETES_DNS_LABEL_RE.fullmatch(master_job) is None:
                raise ValueError("Step3 Master Job name is not a Kubernetes DNS label")
            binding_path = (
                request_root.parent
                / "runs"
                / analysis_id
                / f"attempt-{attempt}"
                / "batch-binding.json"
            )
            if not binding_path.is_file() or binding_path.is_symlink():
                raise ValueError("Step3 frozen binding is unavailable")
            binding = json.loads(binding_path.read_text(encoding="utf-8"))
            if (
                binding.get("schema_version") != "wgs-runtime.batch-binding.v2"
                or binding.get("analysis_id") != analysis_id
                or int(binding.get("attempt") or 0) != attempt
            ):
                raise ValueError("Step3 frozen binding identity is invalid")
            expected_master_job = str(binding.get("master_job") or "")
            expected_namespace = str(binding.get("namespace") or "")
            if master_job != expected_master_job:
                raise ValueError("Step3 Master Job does not match frozen binding")
            namespace = str(payload.get("namespace") or "")
            if namespace != expected_namespace:
                raise ValueError("Step3 namespace does not match frozen binding")
            run_label = str(payload.get("run_label") or "")
            if CCE_RUN_LABEL_PATTERN.fullmatch(run_label) is None:
                raise ValueError("Step3 CCE run label is invalid")
            observer = session.scalar(
                select(ObserverRunState).where(
                    ObserverRunState.analysis_id == analysis_id,
                    ObserverRunState.attempt == attempt,
                )
            )
            if observer is not None and observer.run_label != run_label:
                existing_runtime_label = (
                    CCE_RUN_LABEL_PATTERN.fullmatch(observer.run_label or "")
                    is not None
                )
                expected_airflow_label = f"{analysis_id}-a{attempt}"
                if existing_runtime_label or observer.run_label != expected_airflow_label:
                    raise ValueError("Step3 CCE run label conflicts with observer binding")
                observer.run_label = run_label
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
            completed = _nonnegative_int(master.get("completed"))
            total = _nonnegative_int(master.get("total"))
            percent = _bounded_percent(master.get("percent"))
            exact = total is not None and total > 0 and completed is not None
            upsert_stage_state(
                session,
                analysis_id=analysis_id,
                attempt=attempt,
                stage_code=stage,
                stage_status=status,
                updated_at=heartbeat,
                progress_available=exact,
                progress_percent=percent if exact else None,
                completed_units=completed if exact else None,
                total_units=total if exact else None,
                unit="rules" if exact else None,
                current_item=str(master.get("current_rule") or "") or None,
                message=str(master.get("message") or payload.get("message") or "") or None,
                evidence_key=str(resolved.relative_to(request_root)),
                receipt_hash=terminal_receipt_hash,
                progress_source="cce-pipeline.step3-status.v2",
            )
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
        if int((analysis.params_json or {}).get("orchestration_contract_version") or 1) == 2:
            if _current_execution_from_payload(
                session=session,
                analysis_id=analysis.analysis_id,
                attempt=analysis.attempt,
                stage_code=("step1_upload" if str(payload.get("direction")) == "upload" else "step5_download"),
                payload=payload,
            ) is None:
                return False
        row = session.scalar(select(TransferJob).where(TransferJob.transfer_id == str(payload["transfer_id"])))
        if row is not None and row.heartbeat_at is not None:
            previous = row.heartbeat_at if row.heartbeat_at.tzinfo else row.heartbeat_at.replace(tzinfo=timezone.utc)
            if heartbeat < previous:
                return False
            if heartbeat == previous:
                files = payload.get("files") if isinstance(payload.get("files"), list) else []
                if not _transfer_file_rows_need_sync(
                    session=session,
                    transfer_id=str(payload["transfer_id"]),
                    files=files,
                ):
                    return False
                _upsert_transfer_file_states(
                    session=session,
                    transfer=row,
                    files=files,
                    heartbeat=heartbeat,
                )
                session.commit()
                return True
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
        _upsert_transfer_file_states(
            session=session,
            transfer=row,
            files=payload.get("files") if isinstance(payload.get("files"), list) else [],
            heartbeat=heartbeat,
        )
        stage_code = (
            "step1_upload"
            if str(payload.get("direction")) == "upload"
            else "step5_download"
        )
        upsert_stage_state(
            session,
            analysis_id=analysis.analysis_id,
            attempt=analysis.attempt,
            stage_code=stage_code,
            stage_status=row.status,
            updated_at=heartbeat,
            progress_available=True,
            progress_percent=row.progress_percent,
            completed_units=row.bytes_transferred,
            total_units=row.bytes_total,
            unit="bytes",
            current_item=row.current_file,
            speed_bps=row.speed_bps,
            eta_seconds=row.eta_seconds,
            message=row.message,
            evidence_key=str(resolved.relative_to(spool_root)),
            progress_source=str(payload.get("schema_version")),
        )
        session.commit()
        return True


def _transfer_file_rows_need_sync(*, session, transfer_id: str, files: list[dict]) -> bool:
    if not files:
        return False
    rows = session.scalars(
        select(TransferFileState).where(TransferFileState.transfer_id == transfer_id)
    ).all()
    existing = {row.file_key: row for row in rows}
    if len(existing) != len(files):
        return True
    for item in files:
        row = existing.get(str(item.get("file_key") or ""))
        if row is None:
            return True
        expected_error = str(item.get("error_message") or "")[-2000:] or None
        expected_checksum = str(item.get("checksum_status") or "") or None
        if (
            row.display_name != Path(str(item.get("display_name") or "")).name
            or row.status != str(item.get("status") or "accepted").lower()
            or row.bytes_total != _strict_nonnegative_int(
                item.get("bytes_total"), "file.bytes_total"
            )
            or row.bytes_transferred != _strict_nonnegative_int(
                item.get("bytes_done"), "file.bytes_done"
            )
            or row.speed_bps
            != _strict_nonnegative_int(item.get("speed_bps", 0), "file.speed_bps")
            or row.checksum_status != expected_checksum
            or row.error_message != expected_error
        ):
            return True
    return False


def upsert_stage_state(
    session,
    *,
    analysis_id: str,
    attempt: int,
    stage_code: str,
    stage_status: str,
    updated_at: datetime,
    progress_available: bool = False,
    progress_percent: int | None = None,
    completed_units: int | None = None,
    total_units: int | None = None,
    unit: str | None = None,
    current_item: str | None = None,
    speed_bps: int | None = None,
    eta_seconds: int | None = None,
    message: str | None = None,
    evidence_key: str | None = None,
    progress_source: str = "wgs-runtime.stage-status.v1",
    allow_terminal_retry: bool = False,
    receipt_hash: str | None = None,
) -> RunStageState:
    definition = wgs_stage_definition(stage_code)
    row = session.scalar(
        select(RunStageState).where(
            RunStageState.analysis_id == analysis_id,
            RunStageState.attempt == attempt,
            RunStageState.stage_code == stage_code,
        )
    )
    if row is None:
        row = RunStageState(
            analysis_id=analysis_id,
            attempt=attempt,
            stage_code=stage_code,
            step_number=definition.step_number,
            stage_label=definition.label,
            stage_status=stage_status,
            progress_source=progress_source,
            updated_at=updated_at,
        )
        session.add(row)
    else:
        previous = row.updated_at
        if previous is not None:
            previous = previous if previous.tzinfo else previous.replace(tzinfo=timezone.utc)
            if updated_at < previous:
                return row
        terminal = {"success", "complete", "succeeded", "failed"}
        previous_terminal = _canonical_terminal_status(row.stage_status)
        incoming_terminal = _canonical_terminal_status(stage_status)
        retrying_failed_stage = (
            allow_terminal_retry
            and previous_terminal == "failed"
            and updated_at > previous
        )
        if row.stage_status in terminal and not retrying_failed_stage:
            # Terminal evidence is monotonic. A later file may refresh the same
            # terminal result, but it must never reverse success into failure
            # (or failure into success) or move the stage back to running.
            # A restricted runtime retry is the only exception: its archived
            # generation and positive retry_no prove this is newer execution.
            if incoming_terminal is None or incoming_terminal != previous_terminal:
                return row
    row.stage_status = stage_status
    row.progress_available = progress_available
    row.progress_percent = progress_percent if progress_available else None
    row.completed_units = completed_units if progress_available else None
    row.total_units = total_units if progress_available else None
    row.unit = unit if progress_available else None
    row.current_item = current_item
    row.speed_bps = speed_bps if progress_available else None
    row.eta_seconds = eta_seconds if progress_available else None
    row.message = message
    row.evidence_key = evidence_key
    row.progress_source = progress_source
    if stage_status in {"running", "accepted"} and row.started_at is None:
        row.started_at = updated_at
    if stage_status in {"success", "complete", "succeeded", "failed"}:
        row.ended_at = updated_at
    row.updated_at = updated_at
    normalized_execution_status = {
        "complete": "success",
        "completed": "success",
        "succeeded": "success",
        "cancelled": "canceled",
        "terminated": "canceled",
    }.get(str(stage_status).lower(), str(stage_status).lower())
    if normalized_execution_status in {"accepted", "running", "failed", "canceled"} or receipt_hash:
        transition_latest_stage_execution(
            session=session,
            analysis_id=analysis_id,
            attempt=attempt,
            stage_code=stage_code,
            status=normalized_execution_status,
            observed_at=updated_at,
            receipt_hash=receipt_hash,
            evidence_type=progress_source,
            evidence_key=evidence_key,
            terminal_payload={
                "progress_percent": progress_percent,
                "completed_units": completed_units,
                "total_units": total_units,
                "unit": unit,
            },
            message=message,
        )
    return row


def _nonnegative_int(value) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _bounded_percent(value) -> int | None:
    if value is None:
        return None
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return None


def _normalize_transfer_progress(payload: dict) -> dict:
    """Translate trusted runtime progress to the stable biodemo/API vocabulary."""
    schema = payload.get("schema_version")
    if schema not in {
        "wgs-runtime.transfer-progress.v1",
        "wgs-runtime.transfer-progress.v2",
        "cce-pipeline.transfer-progress.v1",  # legacy read compatibility
    }:
        raise ValueError("unsupported transfer progress schema")
    normalized = dict(payload)
    direction = str(payload.get("direction") or "")
    if direction not in {"upload", "download"}:
        raise ValueError("transfer progress direction must be upload or download")
    state = str(payload.get("state") or "")
    if not state:
        raise ValueError("transfer progress state is required")
    normalized["transfer_type"] = {
        "upload": "input_upload",
        "download": "result_download",
    }[direction]
    normalized["status"] = state
    total = _strict_nonnegative_int(payload.get("bytes_total"), "bytes_total")
    done = _strict_nonnegative_int(payload.get("bytes_done"), "bytes_done")
    files_total = _strict_nonnegative_int(payload.get("files_total"), "files_total")
    files_done = _strict_nonnegative_int(payload.get("files_done"), "files_done")
    if done > total or files_done > files_total:
        raise ValueError("transfer progress completed values exceed totals")
    normalized["bytes_transferred"] = done
    normalized["files_completed"] = files_done
    normalized["speed_bps"] = _strict_nonnegative_int(
        payload.get("speed_bytes_per_second", 0), "speed_bytes_per_second"
    )
    normalized["estimated_finish_at"] = payload.get("estimated_completion_at")
    normalized["checkpoint_ref"] = payload.get("checkpoint_path") if schema == "cce-pipeline.transfer-progress.v1" else None
    normalized["error_message"] = payload.get("error_summary")
    normalized["progress_percent"] = min(100, (done * 100 / total) if total else 0)
    return normalized


def _upsert_transfer_file_states(*, session, transfer: TransferJob, files: list[dict], heartbeat: datetime) -> None:
    if not files:
        return
    aggregate_total = 0
    aggregate_done = 0
    for item in files:
        file_key = str(item.get("file_key") or "")
        display_name = Path(str(item.get("display_name") or "")).name
        if not re.fullmatch(r"[0-9a-f]{64}", file_key) or not display_name:
            raise ValueError("transfer file event contains an invalid public identity")
        total = _strict_nonnegative_int(item.get("bytes_total"), "file.bytes_total")
        done = _strict_nonnegative_int(item.get("bytes_done"), "file.bytes_done")
        if done > total:
            raise ValueError("transfer file progress exceeds its frozen total")
        row = session.scalar(select(TransferFileState).where(TransferFileState.transfer_id == transfer.transfer_id, TransferFileState.file_key == file_key))
        if row is None:
            row = TransferFileState(
                transfer_id=str(transfer.transfer_id),
                analysis_id=transfer.analysis_id,
                attempt=transfer.attempt,
                file_key=file_key,
                display_name=display_name,
                bytes_total=total,
                bytes_transferred=0,
                speed_bps=0,
                status="accepted",
                updated_at=heartbeat,
            )
            session.add(row)
        elif row.bytes_total != total or row.display_name != display_name:
            raise ValueError("transfer file identity differs from frozen manifest")
        if done < row.bytes_transferred:
            continue
        status = str(item.get("status") or "accepted").lower()
        if status not in {"accepted", "running", "success", "failed", "canceled"}:
            raise ValueError("transfer file status is invalid")
        if row.status in {"success", "failed", "canceled"} and status != row.status:
            continue
        row.status = status
        row.bytes_transferred = done
        row.speed_bps = _strict_nonnegative_int(item.get("speed_bps", 0), "file.speed_bps")
        row.checksum_status = str(item.get("checksum_status") or "") or None
        row.error_message = str(item.get("error_message") or "")[-2000:] or None
        if status == "running" and row.started_at is None:
            row.started_at = heartbeat
        if status in {"success", "failed", "canceled"}:
            row.ended_at = heartbeat
        row.updated_at = heartbeat
        aggregate_total += total
        aggregate_done += done
    if aggregate_total != transfer.bytes_total or aggregate_done != transfer.bytes_transferred:
        raise ValueError("transfer file totals do not match frozen aggregate progress")


def _canonical_terminal_status(value: str | None) -> str | None:
    normalized = str(value or "").lower()
    if normalized in {"success", "complete", "succeeded"}:
        return "success"
    if normalized == "failed":
        return "failed"
    return None


def _current_execution_from_payload(*, session, analysis_id: str, attempt: int, stage_code: str, payload: dict):
    if int(payload.get("orchestration_contract_version") or 0) != 2:
        raise ValueError("contract v2 evidence is missing orchestration identity")
    try:
        generation = int(payload.get("generation"))
    except (TypeError, ValueError) as error:
        raise ValueError("contract v2 evidence generation is invalid") from error
    return validate_current_stage_execution(
        session=session,
        analysis_id=analysis_id,
        attempt=attempt,
        stage_code=stage_code,
        execution_id=str(payload.get("execution_id") or ""),
        generation=generation,
        request_hash=str(payload.get("request_hash") or ""),
    )


def _strict_nonnegative_int(value, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"transfer progress {field} must be an integer") from error
    if parsed < 0:
        raise ValueError(f"transfer progress {field} must be nonnegative")
    return parsed


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
        if attempt != binding.attempt:
            raise ValueError("event attempt does not match binding")
    else:
        if str(payload.get("run_label")) != binding.run_label:
            raise ValueError("event run_label does not match binding")
        try:
            float(payload.get("timestamp"))
        except (TypeError, ValueError) as error:
            raise ValueError("event timestamp must be numeric") from error
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
                    _validate_kubernetes_event(payload, path.name, binding)
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


def _validate_kubernetes_event(
    payload: object, filename: str, binding: EvidenceBinding
) -> None:
    if not isinstance(payload, dict):
        raise ValueError("event must be a JSON object")
    if not str(payload.get("event_key") or ""):
        raise ValueError("event_key is required")
    role = str(payload.get("workload_role") or "master")
    if role not in {"master", "work"}:
        raise ValueError("workload_role must be master or work")
    if role == "work" and str(payload.get("run_label") or "") != binding.run_label:
        raise ValueError("work workload run_label does not match evidence binding")
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
    labels = payload.get("workload_labels") if isinstance(payload.get("workload_labels"), dict) else {}
    if str(payload.get("workload_role") or "master") == "work":
        row.resources_json = {
            **dict(row.resources_json or {}),
            "workload_role": "work",
            "heavy_io": labels.get("wgs.biosan.cn/heavy-io") == "true",
            "heavy_slot": labels.get("wgs.biosan.cn/heavy-slot"),
        }
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
        row.resources_json = {
            **dict(row.resources_json or {}),
            **payload["metrics"],
        }
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
        ).order_by(RuleEventRaw.id)
    ).all()
    events = [(row.id, row.payload_json) for row in rows]
    job_map: dict[tuple[str, str], str] = {}
    for _, event in events:
        if event.get("event") == "job_info" and event.get("rule_instance_id"):
            job_map[(str(event.get("stream_id")), str(event.get("job_id")))] = str(
                event["rule_instance_id"]
            )

    grouped: dict[str, list[tuple[int, dict]]] = {}
    for event_row_id, event in events:
        instance = str(event.get("rule_instance_id") or "")
        if not instance and event.get("job_id") is not None:
            instance = job_map.get(
                (str(event.get("stream_id")), str(event.get("job_id"))), ""
            )
        if instance:
            grouped.setdefault(instance, []).append((event_row_id, event))

    stable_sequence = {
        instance: index
        for index, (instance, _) in enumerate(
            sorted(grouped.items(), key=lambda item: min(record[0] for record in item[1])),
            start=1,
        )
    }
    registered_samples = _registered_sample_aliases(session, analysis_id)

    for instance, instance_records in grouped.items():
        ordered = sorted((record[1] for record in instance_records), key=_event_order)
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
        state.sequence = _first_int(
            event.get("sequence") for event in ordered if event.get("sequence") is not None
        ) or stable_sequence[instance]
        state.phase = phase_for_rule(state.rule_name, pipeline_name="wgs")
        wildcards = next(
            (
                event.get("wildcards")
                for event in ordered
                if isinstance(event.get("wildcards"), dict)
            ),
            {},
        )
        explicit_sample = str(descriptive.get("sample_id") or "").strip()
        wildcard_sample = _sample_from_wildcards(wildcards)
        candidate_sample = explicit_sample or wildcard_sample
        registered = registered_samples.get(candidate_sample)
        if not candidate_sample and state.sample_id:
            # Keep a prior analysis.log enrichment only while it still resolves
            # to a sample registered for this analysis.
            registered = registered_samples.get(state.sample_id)
        state.sample_id = registered.sample_id if registered else None
        state.family_id = registered.family_id if registered else None
        state.wildcards_json = dict(wildcards)
        state.layer = descriptive.get("layer", state.layer)
        state.snakemake_jobid = _last_text(
            event.get("snakemake_jobid") or event.get("job_id")
            for event in ordered
        )
        state.message = _last_text(event.get("message") for event in ordered)
        state.log_paths_json = _opaque_log_keys(ordered)
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


def _sample_from_wildcards(wildcards: dict) -> str:
    for key in ("sample_id", "sample", "sample_name"):
        value = str(wildcards.get(key) or "").strip()
        if value:
            return value
    return ""


def _registered_sample_aliases(session, analysis_id: str) -> dict[str, Sample]:
    """Return exact, unambiguous sample and data identifiers for one run."""

    aliases: dict[str, Sample] = {}
    ambiguous: set[str] = set()
    rows = session.scalars(
        select(Sample).where(Sample.analysis_id == analysis_id)
    ).all()
    for row in rows:
        metadata = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        candidates = {
            str(row.sample_id or "").strip(),
            str(metadata.get("data_id") or "").strip(),
        }
        for candidate in candidates - {""}:
            current = aliases.get(candidate)
            if current is not None and current is not row:
                ambiguous.add(candidate)
                continue
            aliases[candidate] = row
    for candidate in ambiguous:
        aliases.pop(candidate, None)
    return aliases


def enrich_rule_states_from_analysis_log(
    session,
    *,
    analysis_id: str,
    attempt: int,
    analysis_log: Path,
) -> int:
    """Fill missing Rule sample context from an already registered log mirror.

    The caller owns path containment. This parser only accepts an exact sample
    identifier already registered for the run and never infers by row order.
    """

    if not analysis_log.is_file() or analysis_log.is_symlink():
        return 0
    samples = _registered_sample_aliases(session, analysis_id)
    if not samples:
        return 0
    states = session.scalars(
        select(RuleState).where(
            RuleState.analysis_id == analysis_id,
            RuleState.attempt == attempt,
        )
    ).all()
    if not any(not state.sample_id for state in states):
        return 0
    contexts = _analysis_log_rule_contexts(analysis_log)
    by_identity = {
        (state.rule_name, str(state.snakemake_jobid or "")): state for state in states
    }
    updated = 0
    for rule_name, job_id, candidate_sample in contexts:
        sample = samples.get(candidate_sample)
        state = by_identity.get((rule_name, job_id))
        if sample is None or state is None or state.sample_id:
            continue
        state.sample_id = sample.sample_id
        state.family_id = sample.family_id
        state.updated_at = datetime.now(timezone.utc)
        updated += 1
    return updated


def reconcile_rule_projection(
    session,
    *,
    analysis_id: str,
    attempt: int,
    evidence_directory: Path,
) -> dict[str, int]:
    """Rebuild a stored projection without rerunning WGS or altering evidence."""

    _rebuild_rule_projection(session, analysis_id, attempt)
    enriched = enrich_rule_states_from_analysis_log(
        session,
        analysis_id=analysis_id,
        attempt=attempt,
        analysis_log=evidence_directory / "mirror" / "analysis.log",
    )
    projected = len(
        session.scalars(
            select(RuleState).where(
                RuleState.analysis_id == analysis_id,
                RuleState.attempt == attempt,
            )
        ).all()
    )
    return {"rules_projected": projected, "rules_enriched": enriched}


def _analysis_log_rule_contexts(path: Path) -> Iterator[tuple[str, str, str]]:
    """Index only newly appended complete lines from an append-only log mirror."""

    cache_key = str(path)
    index = _ANALYSIS_LOG_INDEX.get(cache_key)
    stat = path.stat()
    file_identity = (stat.st_dev, stat.st_ino)
    if (
        index is None
        or index.file_identity != file_identity
        or stat.st_size < index.byte_offset
    ):
        index = _AnalysisLogIndex(file_identity=file_identity)
        if (
            cache_key not in _ANALYSIS_LOG_INDEX
            and len(_ANALYSIS_LOG_INDEX) >= _ANALYSIS_LOG_INDEX_LIMIT
        ):
            _ANALYSIS_LOG_INDEX.pop(next(iter(_ANALYSIS_LOG_INDEX)))
        _ANALYSIS_LOG_INDEX[cache_key] = index

    with path.open("rb") as handle:
        handle.seek(index.byte_offset)
        while True:
            start = handle.tell()
            raw = handle.readline()
            if not raw:
                break
            if not raw.endswith(b"\n"):
                handle.seek(start)
                break
            index.byte_offset = handle.tell()
            line = raw.decode("utf-8", errors="replace")
            match = re.match(r"^\s*(?:local)?rule\s+([^:]+):\s*$", line)
            if match:
                index.rule_name = match.group(1).strip()
                index.job_id = ""
                index.sample_id = ""
                continue
            if not index.rule_name:
                continue
            match = re.match(r"^\s*jobid:\s*(\S+)\s*$", line)
            if match:
                index.job_id = match.group(1)
                continue
            match = re.match(r"^\s*wildcards:\s*(.*)$", line)
            if match:
                values = {
                    key.strip(): value.strip()
                    for key, value in (
                        item.split("=", 1)
                        for item in match.group(1).split(",")
                        if "=" in item
                    )
                }
                index.sample_id = _sample_from_wildcards(values)
                if index.rule_name and index.job_id and index.sample_id:
                    index.contexts.add(
                        (index.rule_name, index.job_id, index.sample_id)
                    )
    yield from sorted(index.contexts)


def _first_int(values) -> int | None:
    for value in values:
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_text(values) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _last_text(values) -> str | None:
    result = None
    for value in values:
        text = str(value or "").strip()
        if text:
            result = text
    return result


def _opaque_log_keys(events: list[dict]) -> list[str]:
    keys: list[str] = []
    for event in events:
        values = event.get("log_keys")
        if not isinstance(values, list):
            continue
        for value in values:
            key = str(value or "")
            if re.fullmatch(r"[a-z][a-z0-9_-]{0,31}:[A-Za-z0-9_.-]{1,128}", key):
                if key not in keys:
                    keys.append(key)
    return keys


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
