from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisRun,
    RuleState,
    RunStageState,
    Sample,
    SnakemakeRuleEvent,
)
from app.rule_event_service import (
    cancel_incomplete_rule_events,
    finalize_dry_run_rule_events,
    import_snakemake_events_jsonl,
)
from app.wgs_run_projection import (
    load_wgs_runtime_binding,
    resolve_bound_wgs_batch_root,
)
from app.wgs_artifact_selection import select_batch_qcstat
from app.wgs_execution_dispatch_service import (
    mark_execution_needs_recovery,
    mark_execution_terminal,
)


class DiagnosticsError(Exception):
    pass


class InvalidRunPathError(DiagnosticsError):
    pass


class LogNotFoundError(DiagnosticsError):
    pass


class UnsupportedLogStreamError(DiagnosticsError):
    pass


class MissingDagRunError(DiagnosticsError):
    pass


LOG_TAIL_MAX_BYTES = 8 * 1024 * 1024
LOG_TAIL_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class ArtifactDefinition:
    key: str
    type: str
    label: str
    relative_path: Path
    url: str


LOG_STREAMS = {
    "stdout": Path("logs/snakemake.stdout.log"),
    "stderr": Path("logs/snakemake.stderr.log"),
    "metadata": Path("logs/run_metadata.tsv"),
}


ARTIFACTS: list[ArtifactDefinition] = []


def sync_wgs_airflow_status(*, session: Session, airflow_client, analysis_id: str, settings) -> dict[str, Any] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    if not run.dag_id or not run.dag_run_id:
        raise MissingDagRunError("Run has no dag_id or dag_run_id to sync.")

    previous_status = str(run.status or "").lower()
    has_stale_failed_stage = (
        session.scalar(
            select(RunStageState.id)
            .where(
                RunStageState.analysis_id == analysis_id,
                RunStageState.attempt == int(run.attempt or 1),
                RunStageState.stage_status == "failed",
            )
            .limit(1)
        )
        is not None
    )
    airflow_payload = airflow_client.get_dag_run(run.dag_id, run.dag_run_id)
    airflow_state = str(airflow_payload.get("state") or "").lower()
    authoritative_status = _map_airflow_state(airflow_state)
    if authoritative_status == "success":
        task_payload = airflow_client.list_task_instances(run.dag_id, run.dag_run_id)
        task_instances = task_payload.get("task_instances", [])
        if any(
            str(item.get("state") or "").lower() in {"failed", "upstream_failed"}
            for item in task_instances
        ):
            authoritative_status = "failed"
            airflow_payload = {**airflow_payload, "state": "failed"}
    run.status = authoritative_status
    run.started_at = _parse_airflow_datetime(airflow_payload.get("start_date")) or run.started_at
    dag_end_at = _parse_airflow_datetime(airflow_payload.get("end_date"))
    if run.status in {"success", "failed"}:
        run.ended_at = dag_end_at
    else:
        run.ended_at = None
        run.error_summary = None
    if run.status == "failed":
        run.error_summary = build_wgs_error_summary(run=run, airflow_payload=airflow_payload, settings=settings)
    elif run.status == "success":
        run.error_summary = None
        if (
            dag_end_at is not None
            and (
                run.pipeline_finished_at is None
                or previous_status in {"failed", "cancelled", "unknown_interrupted"}
                or has_stale_failed_stage
            )
        ):
            run.pipeline_finished_at = dag_end_at
        run.progress_percent = 100
        run.current_stage = "Workflow complete"
        run.progress_updated_at = run.ended_at or datetime.now(timezone.utc)
    if run.status in {"success", "failed"}:
        events_path = _safe_child_path(_safe_workdir(run, settings), Path("logs/events/snakemake_events.jsonl"), settings)
        import_snakemake_events_jsonl(session=session, analysis_id=analysis_id, events_path=events_path)
        cancel_incomplete_rule_events(
            session=session,
            analysis_id=analysis_id,
            parent_status=authoritative_status,
            timestamp=run.ended_at or datetime.now(timezone.utc),
        )
        params = run.params_json or {}
        if (
            authoritative_status == "success"
            and bool(params.get("wgs_dry_run", True))
        ):
            finalize_dry_run_rule_events(
                session=session,
                analysis_id=analysis_id,
                timestamp=run.ended_at or datetime.now(timezone.utc),
            )
        # A resumed run can retain an earlier failed JSONL event. Import the
        # complete audit trail, then let the terminal Airflow DAG state win.
        run.status = authoritative_status
        if authoritative_status == "success":
            mark_execution_terminal(
                session=session,
                analysis_id=analysis_id,
                attempt=int(run.attempt or 1),
            )
        else:
            mark_execution_needs_recovery(
                session=session,
                analysis_id=analysis_id,
                attempt=int(run.attempt or 1),
                reason=run.error_summary or "Committed WGS execution failed",
            )
    sync_sample_statuses(session=session, analysis_id=analysis_id, run_status=run.status)
    session.commit()
    session.refresh(run)
    return _run_payload(run)


def sync_airflow_status(*, session: Session, airflow_client, analysis_id: str, settings) -> dict[str, Any] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    if not run.dag_id or not run.dag_run_id:
        raise MissingDagRunError("Run has no dag_id or dag_run_id to sync.")
    airflow_payload = airflow_client.get_dag_run(run.dag_id, run.dag_run_id)
    authoritative_status = _map_airflow_state(str(airflow_payload.get("state") or "").lower())
    run.status = authoritative_status
    run.started_at = _parse_airflow_datetime(airflow_payload.get("start_date")) or run.started_at
    dag_end_at = _parse_airflow_datetime(airflow_payload.get("end_date"))
    if run.status in {"success", "failed"}:
        run.ended_at = dag_end_at or datetime.now(timezone.utc)
    else:
        run.ended_at = None
        run.error_summary = None
    if run.status == "failed":
        run.error_summary = build_error_summary(run=run, airflow_payload=airflow_payload, settings=settings)
    elif run.status == "success":
        run.error_summary = None
        run.progress_percent = 100
        run.current_stage = "Workflow complete"
        run.progress_updated_at = run.ended_at or datetime.now(timezone.utc)
    if run.status in {"success", "failed"}:
        events_path = _safe_child_path(
            _safe_workdir(run, settings),
            Path("logs/events/snakemake_events.jsonl"),
            settings,
        )
        import_snakemake_events_jsonl(
            session=session,
            analysis_id=analysis_id,
            events_path=events_path,
        )
        cancel_incomplete_rule_events(
            session=session,
            analysis_id=analysis_id,
            parent_status=authoritative_status,
            timestamp=run.ended_at or datetime.now(timezone.utc),
        )
        run.status = authoritative_status
    sync_sample_statuses(session=session, analysis_id=analysis_id, run_status=run.status)
    session.commit()
    session.refresh(run)
    return _run_payload(run)


def get_run_log(
    *, session: Session, analysis_id: str, stream: str, tail: int, settings, key: str | None = None
) -> dict[str, Any] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    log_path = _log_path_for_key(session=session, run=run, key=key, settings=settings) if key else _log_path(run, stream, settings)
    if not log_path.is_file():
        raise LogNotFoundError(f"Log file not found: {log_path}")
    lines, truncated, file_size = _tail_log_file(log_path, tail=tail)
    payload = {
        "stream": stream,
        "truncated": truncated,
        "file_size": file_size,
        "lines": lines,
    }
    payload["path"] = str(log_path)
    if key:
        payload["key"] = key
    return payload


def get_wgs_run_log(
    *, session: Session, analysis_id: str, stream: str, tail: int, settings, key: str | None = None
) -> dict[str, Any] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    if not key:
        raise LogNotFoundError("WGS logs require a registered opaque log key")
    log_item = next(
        (item for item in _wgs_run_log_items(run=run, settings=settings) if item["key"] == key),
        None,
    )
    if log_item is None:
        raise LogNotFoundError(f"Unknown or unavailable log key: {key}")
    log_path = Path(str(log_item["_path"]))
    if not log_path.is_file():
        raise LogNotFoundError(f"Log file not found for registered key: {key}")
    lines, truncated, file_size = _tail_log_file(log_path, tail=tail)
    return {
        "stream": stream,
        "truncated": truncated,
        "file_size": file_size,
        "lines": lines,
        "path": log_item.get("relative_path"),
        "key": key,
    }


def get_gatk_run_log(
    *, session: Session, analysis_id: str, stream: str, tail: int, settings, key: str | None = None
) -> dict[str, Any] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    if not key:
        raise LogNotFoundError("GATK logs require a registered opaque log key")
    item = next(
        (candidate for candidate in _gatk_run_log_items(run=run, settings=settings) if candidate["key"] == key),
        None,
    )
    if item is None:
        raise LogNotFoundError(f"Unknown or unavailable log key: {key}")
    path = Path(str(item["_path"]))
    lines, truncated, file_size = _tail_log_file(path, tail=tail)
    return {
        "stream": str(item["stream"]),
        "truncated": truncated,
        "file_size": file_size,
        "lines": lines,
        "path": item["relative_path"],
        "key": key,
    }


def _tail_log_file(
    path: Path,
    *,
    tail: int,
    max_bytes: int = LOG_TAIL_MAX_BYTES,
    chunk_bytes: int = LOG_TAIL_CHUNK_BYTES,
) -> tuple[list[str], bool, int]:
    """Read only a bounded suffix while preserving the latest complete lines."""
    if tail < 1:
        raise ValueError("tail must be positive")
    if max_bytes < 1 or chunk_bytes < 1:
        raise ValueError("log byte limits must be positive")

    chunks: list[bytes] = []
    bytes_read = 0
    newline_count = 0
    with path.open("rb") as handle:
        handle.seek(0, 2)
        file_size = handle.tell()
        position = file_size
        while position > 0 and bytes_read < max_bytes and newline_count <= tail:
            read_size = min(chunk_bytes, position, max_bytes - bytes_read)
            position -= read_size
            handle.seek(position)
            chunk = handle.read(read_size)
            if not chunk:
                break
            chunks.append(chunk)
            bytes_read += len(chunk)
            newline_count += chunk.count(b"\n")

    text = b"".join(reversed(chunks)).decode("utf-8", errors="replace")
    available_lines = text.splitlines()
    truncated = position > 0 or len(available_lines) > tail
    return available_lines[-tail:], truncated, file_size


def list_run_logs(*, session: Session, analysis_id: str, settings) -> dict[str, list[dict[str, Any]]] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    workdir = _safe_workdir(run, settings)
    items: list[dict[str, Any]] = []
    for stream, relative_path in LOG_STREAMS.items():
        path = _safe_child_path(workdir, relative_path, settings)
        if path.is_file():
            items.append(_log_index_item(path=path, workdir=workdir, label=stream.title(), stream=stream))
    stage_labels = {
        "mapping": "Mapping stage",
        "metadata": "Metadata stage",
        "cnv_qc": "CNV QC stage",
        "cnv_predict": "CNV prediction stage",
        "baseline_qc": "Baseline QC stage",
    }
    for stage, label in stage_labels.items():
        for stream in ("stdout", "stderr"):
            path = _safe_child_path(workdir, Path(f"logs/snakemake.{stage}.{stream}.log"), settings)
            if path.is_file():
                items.append(_log_index_item(path=path, workdir=workdir, label=f"{label} {stream}", stream=stream))
    events = session.scalars(
        select(SnakemakeRuleEvent)
        .where(SnakemakeRuleEvent.analysis_id == analysis_id)
        .order_by(SnakemakeRuleEvent.updated_at.desc())
    ).all()
    seen = {item["key"] for item in items}
    for event in events:
        for stream, raw_path in (("stdout", event.stdout_path), ("stderr", event.stderr_path)):
            if not raw_path:
                continue
            try:
                candidate = Path(raw_path)
                if not candidate.is_absolute():
                    candidate = workdir / candidate
                relative_path = candidate.resolve().relative_to(workdir.resolve())
                path = _safe_child_path(workdir, relative_path, settings)
            except (ValueError, InvalidRunPathError):
                continue
            if not path.is_file():
                continue
            item = _log_index_item(
                path=path,
                workdir=workdir,
                label=f"{event.rule} - {event.sample_id or 'project'} - {stream}",
                stream=stream,
                rule=event.rule,
                sample_id=event.sample_id,
                status=event.status,
            )
            if item["key"] not in seen:
                items.append(item)
                seen.add(item["key"])
    return {"items": items}


def list_wgs_run_logs(*, session: Session, analysis_id: str, settings) -> dict[str, list[dict[str, Any]]] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    return {
        "items": [
            {key: value for key, value in item.items() if key != "_path"}
            for item in _wgs_run_log_items(run=run, settings=settings)
        ]
    }


def list_gatk_run_logs(*, session: Session, analysis_id: str, settings) -> dict[str, list[dict[str, Any]]] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    return {
        "items": [
            {key: value for key, value in item.items() if key != "_path"}
            for item in _gatk_run_log_items(run=run, settings=settings)
        ]
    }


def _gatk_run_log_items(*, run: AnalysisRun, settings) -> list[dict[str, Any]]:
    attempt = int(run.attempt or 1)
    request_root = Path(settings.gatk_runtime_request_root).resolve()
    evidence_root = Path(settings.gatk_evidence_root).resolve()
    request_attempt = _contained_path(
        request_root, Path(run.analysis_id) / f"attempt-{attempt}"
    )
    evidence_attempt = _contained_path(
        evidence_root, Path(run.analysis_id) / f"attempt-{attempt}"
    )
    items: list[dict[str, Any]] = []
    analysis_log = _contained_path(evidence_attempt, Path("mirror/analysis.log"))
    if analysis_log.is_file() and not analysis_log.is_symlink():
        items.append(
            _wgs_log_item(
                path=analysis_log,
                token=f"gatk-analysis:{attempt}",
                label="GATK Snakemake analysis log",
                stream="stdout",
                source="master_analysis",
                stage="step3_monitor",
                relative_path="evidence/mirror/analysis.log",
            )
        )
    if request_attempt.is_dir() and not request_attempt.is_symlink():
        for path in sorted(request_attempt.glob("*.worker.log")):
            if path.is_symlink() or not path.is_file():
                continue
            stage = path.name.removesuffix(".worker.log")
            items.append(
                _wgs_log_item(
                    path=path,
                    token=f"gatk-worker:{attempt}:{stage}",
                    label=f"{stage.replace('_', ' ').title()} worker log",
                    stream="stdout",
                    source="stage_worker",
                    stage=stage,
                    relative_path=f"runtime/{path.name}",
                )
            )
    return items


def _log_index_item(*, path: Path, workdir: Path, label: str, stream: str, **extra) -> dict[str, Any]:
    relative = path.resolve().relative_to(workdir.resolve()).as_posix()
    key = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:20]
    return {"key": key, "label": label, "stream": stream, "relative_path": relative, **extra}


def _log_path_for_key(*, session: Session, run: AnalysisRun, key: str | None, settings) -> Path:
    index = list_run_logs(session=session, analysis_id=run.analysis_id, settings=settings) or {"items": []}
    item = next((candidate for candidate in index["items"] if candidate["key"] == key), None)
    if item is None:
        raise LogNotFoundError(f"Unknown or unavailable log key: {key}")
    return _safe_child_path(_safe_workdir(run, settings), Path(item["relative_path"]), settings)


def _wgs_run_log_items(*, run: AnalysisRun, settings) -> list[dict[str, Any]]:
    """Index only deterministic files under the registered WGS runtime root."""
    request_root = Path(
        getattr(
            settings,
            "wgs_runtime_request_root",
            Path(settings.container_shared_root) / "wgs-runner-requests",
        )
    ).resolve()
    attempt = int(run.attempt or 1)
    attempt_name = f"attempt-{attempt}"
    items: list[dict[str, Any]] = []

    worker_root = _contained_path(
        request_root, Path(run.analysis_id) / attempt_name
    )
    if worker_root.is_dir():
        for path in sorted(worker_root.glob("*.worker.log")):
            if path.is_symlink() or not path.is_file():
                continue
            stage = path.name.removesuffix(".worker.log")
            items.append(
                _wgs_log_item(
                    path=path,
                    token=f"worker:{attempt}:{stage}",
                    label=f"{stage.replace('_', ' ').title()} worker log",
                    stream="stderr" if "failed" in stage else "stdout",
                    source="stage_worker",
                    stage=stage,
                    relative_path=(
                        Path("runner-requests") / run.analysis_id / attempt_name / path.name
                    ).as_posix(),
                )
            )

    try:
        binding = load_wgs_runtime_binding(
            run_root=settings.wgs_runtime_run_root,
            analysis_id=run.analysis_id,
            attempt=attempt,
        )
        local_batch = resolve_bound_wgs_batch_root(
            binding=binding,
            node_analysis_root=settings.wgs_results_host_root,
            local_analysis_root=settings.host_results_root,
        )
        run_id = str(binding["run_id"])
        if not run_id or "/" in run_id or "\\" in run_id:
            raise ValueError("invalid run id")
        analysis_log = _contained_path(
            local_batch,
            Path("cce") / "evidence" / run_id / "mirror" / "analysis.log",
        )
        if analysis_log.is_file() and not analysis_log.is_symlink():
            items.insert(
                0,
                _wgs_log_item(
                    path=analysis_log,
                    token=f"analysis:{attempt}:{run_id}",
                    label="WGS Snakemake analysis log",
                    stream="stdout",
                    source="master_analysis",
                    stage="step3_monitor",
                    relative_path=(
                        Path("cce") / "evidence" / run_id / "mirror" / "analysis.log"
                    ).as_posix(),
                ),
            )
    except (KeyError, TypeError, ValueError, InvalidRunPathError):
        pass
    return items


def wgs_rule_log_contexts(*, run: AnalysisRun, rules: list[RuleState], settings) -> dict[str, dict[str, str | None]]:
    """Bind Rules to the registered Master log and excerpt only failures."""
    return _rule_log_contexts(
        rules=rules,
        items=_wgs_run_log_items(run=run, settings=settings),
    )


def gatk_rule_log_contexts(*, run: AnalysisRun, rules: list[RuleState], settings) -> dict[str, dict[str, str | None]]:
    """Bind GATK Rule rows to its registered Master analysis log."""
    return _rule_log_contexts(
        rules=rules,
        items=_gatk_run_log_items(run=run, settings=settings),
    )


def _rule_log_contexts(*, rules: list[RuleState], items: list[dict[str, Any]]) -> dict[str, dict[str, str | None]]:
    item = next((row for row in items if row.get("source") == "master_analysis"), None)
    if item is None:
        return {}
    analysis_log_key = str(item["key"])
    output: dict[str, dict[str, str | None]] = {
        rule.rule_instance_id: {
            "stderr_excerpt": None,
            "analysis_log_key": analysis_log_key,
        }
        for rule in rules
    }
    failed_rules = [rule for rule in rules if rule.status == "failed"]
    if not failed_rules:
        return output
    path = Path(str(item["_path"]))
    try:
        with path.open("rb") as handle:
            size = path.stat().st_size
            handle.seek(max(0, size - 2 * 1024 * 1024))
            text = handle.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
    except OSError:
        return output
    lines = text.splitlines()
    for rule in failed_rules:
        anchors = []
        if rule.snakemake_jobid:
            anchors.extend([f"jobid: {rule.snakemake_jobid}", f"job {rule.snakemake_jobid}"])
        anchors.extend([f"Error in rule {rule.rule_name}", f"rule {rule.rule_name}:"])
        position = next((index for index in range(len(lines) - 1, -1, -1) if any(anchor in lines[index] for anchor in anchors)), None)
        if position is None:
            excerpt = str(rule.message or "").strip()
        else:
            excerpt = "\n".join(lines[max(0, position - 8):min(len(lines), position + 72)])
        excerpt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", excerpt)[-65536:]
        output[rule.rule_instance_id]["stderr_excerpt"] = excerpt or None
    return output


def _contained_path(root: Path, relative: Path) -> Path:
    if relative.is_absolute():
        raise InvalidRunPathError("absolute runtime child path is not allowed")
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as error:
        raise InvalidRunPathError("runtime log path escapes the registered root") from error
    return candidate


def _wgs_log_item(*, path: Path, token: str, label: str, stream: str, source: str,
                  stage: str, relative_path: str) -> dict[str, Any]:
    return {
        "key": hashlib.sha256(token.encode("utf-8")).hexdigest()[:20],
        "label": label,
        "stream": stream,
        "source": source,
        "stage": stage,
        "relative_path": relative_path,
        "_path": str(path),
    }


def list_run_artifacts(*, session: Session, analysis_id: str, settings) -> dict[str, list[dict[str, Any]]] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    return {"items": []}


def list_wgs_run_artifacts(*, session: Session, analysis_id: str, settings) -> dict[str, list[dict[str, Any]]] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    return {"items": _wgs_artifact_items(run=run, settings=settings)}


def list_gatk_run_artifacts(*, session: Session, analysis_id: str, settings) -> dict[str, list[dict[str, Any]]] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    attempt = int(run.attempt or 1)
    runtime_root = Path(settings.gatk_runtime_request_root).resolve().parent
    attempt_root = _contained_path(
        runtime_root, Path("runs") / run.analysis_id / f"attempt-{attempt}"
    )
    definitions = (
        ("gatk_prepare_receipt", "prepare_receipt", "GATK prepare receipt", "prepare.receipt.json"),
        ("gatk_batch_binding", "runtime_binding", "GATK runtime binding", "batch-binding.json"),
    )
    items = []
    for key, artifact_type, label, name in definitions:
        path = _contained_path(attempt_root, Path(name))
        if path.is_file() and not path.is_symlink():
            items.append(
                {
                    "key": key,
                    "type": artifact_type,
                    "label": label,
                    "path": f"runtime/{name}",
                    "size_bytes": path.stat().st_size,
                    "url": "",
                }
            )
    return {"items": items}


def _wgs_artifact_items(*, run: AnalysisRun, settings) -> list[dict[str, Any]]:
    try:
        binding = load_wgs_runtime_binding(
            run_root=settings.wgs_runtime_run_root,
            analysis_id=run.analysis_id,
            attempt=int(run.attempt or 1),
        )
        batch_root = resolve_bound_wgs_batch_root(
            binding=binding,
            node_analysis_root=settings.wgs_results_host_root,
            local_analysis_root=settings.host_results_root,
        )
    except (KeyError, OSError, TypeError, ValueError, InvalidRunPathError):
        return []
    definitions = [
        ("wgs_sampleinfo", "sample_manifest", "Selected sampleinfo", Path("sampleinfo.tsv")),
        ("wgs_config", "runtime_config", "WGS config", Path("config.yaml")),
        ("wgs_batch_runtime", "runtime_config", "Batch runtime", Path("cce/BATCH_RUNTIME.yaml")),
        ("wgs_resolved_profile", "runtime_config", "Resolved CCE profile", Path("cce/RESOLVED_PROFILE.yaml")),
    ]
    qc_path = select_batch_qcstat(batch_root)
    if qc_path is not None:
        definitions.append(
            ("wgs_qcstat", "qc_summary", "WGS QC statistics", qc_path.relative_to(batch_root))
        )
    items: list[dict[str, Any]] = []
    for key, artifact_type, label, relative in definitions:
        try:
            path = _contained_path(batch_root, relative)
        except InvalidRunPathError:
            continue
        if not path.is_file() or path.is_symlink():
            continue
        items.append(
            {
                "key": key,
                "type": artifact_type,
                "label": label,
                "path": relative.as_posix(),
                "size_bytes": path.stat().st_size,
                "url": "",
            }
        )
    return items


def build_error_summary(*, run: AnalysisRun, airflow_payload: dict[str, Any], settings) -> str:
    stderr_path = None
    log_key = None
    relative_path = None
    last_lines: list[str] = []
    try:
        stderr_path = _log_path(run, "stderr", settings)
        if stderr_path.is_file():
            last_lines = stderr_path.read_text(encoding="utf-8", errors="replace").splitlines()[-100:]
    except DiagnosticsError:
        stderr_path = None

    if not last_lines:
        last_lines = ["no stderr available"]

    payload = {
        "analysis_id": run.analysis_id,
        "dag_id": run.dag_id,
        "dag_run_id": run.dag_run_id,
        "status": str(airflow_payload.get("state") or run.status),
        "stderr_path": str(stderr_path) if stderr_path else None,
        "log_key": log_key,
        "last_100_lines": last_lines,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_wgs_error_summary(*, run: AnalysisRun, airflow_payload: dict[str, Any], settings) -> str:
    stderr_path = None
    log_key = None
    relative_path = None
    last_lines: list[str] = []
    registered = _wgs_run_log_items(run=run, settings=settings)
    item = next((value for value in registered if value.get("source") == "master_analysis"), None)
    item = item or (registered[-1] if registered else None)
    if item:
        stderr_path = Path(str(item["_path"]))
        log_key = item["key"]
        relative_path = item.get("relative_path")
        try:
            last_lines, _, _ = _tail_log_file(stderr_path, tail=100)
        except OSError:
            last_lines = []
    if not last_lines:
        last_lines = ["no stderr available"]
    return json.dumps(
        {
            "analysis_id": run.analysis_id,
            "dag_id": run.dag_id,
            "dag_run_id": run.dag_run_id,
            "status": str(airflow_payload.get("state") or run.status),
            "stderr_path": relative_path,
            "log_key": log_key,
            "last_100_lines": last_lines,
        },
        ensure_ascii=False,
        indent=2,
    )


def _get_run(session: Session, analysis_id: str) -> AnalysisRun | None:
    return session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))


def _log_path(run: AnalysisRun, stream: str, settings) -> Path:
    if stream not in LOG_STREAMS:
        raise UnsupportedLogStreamError(f"Unsupported log stream: {stream}")
    return _safe_child_path(_safe_workdir(run, settings), LOG_STREAMS[stream], settings)


def _safe_workdir(run: AnalysisRun, settings) -> Path:
    workdir = Path(run.workdir).resolve()
    if not any(_is_relative_to(workdir, root) for root in _allowed_run_roots(settings)):
        raise InvalidRunPathError(f"Run workdir is outside configured result roots: {workdir}")
    return workdir


def _safe_child_path(workdir: Path, relative_path: Path, settings) -> Path:
    path = (workdir / relative_path).resolve()
    if not _is_relative_to(path, workdir) or not any(
        _is_relative_to(path, root) for root in _allowed_run_roots(settings)
    ):
        raise InvalidRunPathError(f"Resolved path is outside run workdir: {path}")
    return path


def _allowed_run_roots(settings) -> tuple[Path, ...]:
    configured = [settings.container_shared_root, getattr(settings, "host_results_root", None)]
    return tuple(dict.fromkeys(Path(value).resolve() for value in configured if value))


def _is_relative_to(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def _map_airflow_state(state: str) -> str:
    if state == "success":
        return "success"
    if state == "failed":
        return "failed"
    if state == "running":
        return "running"
    if state in {"queued", "scheduled"}:
        return "submitted"
    return state or "unknown"


def sync_sample_statuses(*, session: Session, analysis_id: str, run_status: str) -> None:
    sample_status = _sample_status_for_run_status(run_status)
    if sample_status is None:
        return
    samples = session.scalars(select(Sample).where(Sample.analysis_id == analysis_id)).all()
    for sample in samples:
        sample.status = sample_status


def _sample_status_for_run_status(run_status: str) -> str | None:
    if run_status == "created":
        return "pending"
    if run_status in {"submitted", "running"}:
        return "running"
    if run_status in {"success", "failed"}:
        return run_status
    return None


def _parse_airflow_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _run_payload(run: AnalysisRun) -> dict[str, Any]:
    return {
        "analysis_id": run.analysis_id,
        "pipeline": run.pipeline_name,
        "dag_id": run.dag_id,
        "dag_run_id": run.dag_run_id,
        "status": run.status,
        "workdir": run.workdir,
        "mode": run.mode,
        "error_summary": run.error_summary,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
    }
