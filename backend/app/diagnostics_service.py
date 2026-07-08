from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Sample
from app.qc_service import import_run_qc_metrics
from app.rule_event_service import import_snakemake_events_jsonl


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


ARTIFACTS = [
    ArtifactDefinition(
        key="run_metadata",
        type="pgta_metadata",
        label="PGT-A run metadata",
        relative_path=Path("logs/run_metadata.tsv"),
        url="/api/runs/{analysis_id}/logs?stream=metadata",
    ),
    ArtifactDefinition(
        key="snakemake_stdout",
        type="snakemake_log",
        label="Snakemake stdout",
        relative_path=Path("logs/snakemake.stdout.log"),
        url="/api/runs/{analysis_id}/logs?stream=stdout",
    ),
    ArtifactDefinition(
        key="snakemake_stderr",
        type="snakemake_log",
        label="Snakemake stderr",
        relative_path=Path("logs/snakemake.stderr.log"),
        url="/api/runs/{analysis_id}/logs?stream=stderr",
    ),
    ArtifactDefinition(
        key="snakemake_command",
        type="snakemake_log",
        label="Snakemake command",
        relative_path=Path("logs/snakemake.command.txt"),
        url="/api/runs/{analysis_id}/artifacts/snakemake_command",
    ),
    ArtifactDefinition(
        key="pgta_resume_cleanup",
        type="snakemake_log",
        label="PGT-A resume cleanup log",
        relative_path=Path("logs/pgta.resume.cleanup.tsv"),
        url="/api/runs/{analysis_id}/artifacts/pgta_resume_cleanup",
    ),
    ArtifactDefinition(
        key="pgta_python_preflight",
        type="snakemake_log",
        label="PGT-A Python preflight log",
        relative_path=Path("logs/pgta.python_preflight.log"),
        url="/api/runs/{analysis_id}/artifacts/pgta_python_preflight",
    ),
    ArtifactDefinition(
        key="pgta_config_yaml",
        type="pgta_config",
        label="PGT-A Snakemake config",
        relative_path=Path("config.yaml"),
        url="/api/runs/{analysis_id}/artifacts/pgta_config_yaml",
    ),
    ArtifactDefinition(
        key="pgta_run_config",
        type="pgta_config",
        label="PGT-A runner config",
        relative_path=Path("config/pgta_run_config.json"),
        url="/api/runs/{analysis_id}/artifacts/pgta_run_config",
    ),
    ArtifactDefinition(
        key="pgta_metadata_config",
        type="pgta_config",
        label="PGT-A metadata runner config",
        relative_path=Path("config/pgta_metadata_config.json"),
        url="/api/runs/{analysis_id}/artifacts/pgta_metadata_config",
    ),
    ArtifactDefinition(
        key="pgta_baseline_qc_summary",
        type="qc_tsv",
        label="PGT-A baseline QC summary",
        relative_path=Path("qc/baseline/baseline_qc_summary.tsv"),
        url="/api/runs/{analysis_id}/qc",
    ),
    ArtifactDefinition(
        key="pgta_baseline_qc_pass_samples",
        type="qc_tsv",
        label="PGT-A baseline QC pass samples",
        relative_path=Path("qc/baseline/baseline_qc_pass_samples.txt"),
        url="/api/runs/{analysis_id}/artifacts/pgta_baseline_qc_pass_samples",
    ),
    ArtifactDefinition(
        key="pgta_baseline_qc_report",
        type="pgta_report",
        label="PGT-A baseline QC report",
        relative_path=Path("qc/baseline/baseline_qc_report.md"),
        url="/api/runs/{analysis_id}/artifacts/pgta_baseline_qc_report",
    ),
    ArtifactDefinition(
        key="wes_final_summary",
        type="wes_mock_summary",
        label="WES mock final summary",
        relative_path=Path("reports/final_summary.tsv"),
        url="/api/runs/{analysis_id}/artifacts/wes_final_summary",
    ),
    ArtifactDefinition(
        key="wes_qc_summary",
        type="qc_tsv",
        label="WES mock QC summary",
        relative_path=Path("reports/qc_summary.tsv"),
        url="/api/runs/{analysis_id}/qc",
    ),
    ArtifactDefinition(
        key="wes_mock_config",
        type="wes_config",
        label="WES mock Snakemake config",
        relative_path=Path("config/wes_mock_config.yaml"),
        url="/api/runs/{analysis_id}/artifacts/wes_mock_config",
    ),
    ArtifactDefinition(
        key="wes_events_jsonl",
        type="snakemake_events",
        label="WES Snakemake events JSONL",
        relative_path=Path("logs/events/snakemake_events.jsonl"),
        url="/api/runs/{analysis_id}/artifacts/wes_events_jsonl",
    ),
    ArtifactDefinition(
        key="nipt_qc_summary",
        type="qc_tsv",
        label="NIPT Docker QC summary",
        relative_path=Path("reports/qc_summary.tsv"),
        url="/api/runs/{analysis_id}/qc",
    ),
    ArtifactDefinition(
        key="nipt_docker_compose",
        type="nipt_config",
        label="NIPT Docker compose file",
        relative_path=Path("config/nipt_docker_compose.yml"),
        url="/api/runs/{analysis_id}/artifacts/nipt_docker_compose",
    ),
    ArtifactDefinition(
        key="nipt_run_config",
        type="nipt_config",
        label="NIPT run config",
        relative_path=Path("config/nipt_run_config.yaml"),
        url="/api/runs/{analysis_id}/artifacts/nipt_run_config",
    ),
    ArtifactDefinition(
        key="nipt_airflow_request",
        type="nipt_config",
        label="NIPT Airflow request",
        relative_path=Path("config/nipt_airflow_request.json"),
        url="/api/runs/{analysis_id}/artifacts/nipt_airflow_request",
    ),
    ArtifactDefinition(
        key="nipt_docker_command",
        type="docker_log",
        label="NIPT Docker command",
        relative_path=Path("logs/nipt_docker.command.txt"),
        url="/api/runs/{analysis_id}/artifacts/nipt_docker_command",
    ),
]


def sync_airflow_status(*, session: Session, airflow_client, analysis_id: str, settings) -> dict[str, Any] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    if not run.dag_id or not run.dag_run_id:
        raise MissingDagRunError("Run has no dag_id or dag_run_id to sync.")

    airflow_payload = airflow_client.get_dag_run(run.dag_id, run.dag_run_id)
    airflow_state = str(airflow_payload.get("state") or "").lower()
    run.status = _map_airflow_state(airflow_state)
    _sync_sample_statuses(session=session, analysis_id=analysis_id, run_status=run.status)
    run.started_at = _parse_airflow_datetime(airflow_payload.get("start_date")) or run.started_at
    if run.status in {"success", "failed"}:
        run.ended_at = _parse_airflow_datetime(airflow_payload.get("end_date")) or datetime.now(timezone.utc)
    if run.status == "failed":
        run.error_summary = build_error_summary(run=run, airflow_payload=airflow_payload, settings=settings)
    elif run.status == "success":
        run.error_summary = None
        import_run_qc_metrics(session=session, run=run, settings=settings)
    if run.status in {"success", "failed"}:
        events_path = _safe_child_path(_safe_workdir(run, settings), Path("logs/events/snakemake_events.jsonl"), settings)
        import_snakemake_events_jsonl(session=session, analysis_id=analysis_id, events_path=events_path)

    session.commit()
    session.refresh(run)
    return _run_payload(run)


def get_run_log(*, session: Session, analysis_id: str, stream: str, tail: int, settings) -> dict[str, Any] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    log_path = _log_path(run, stream, settings)
    if not log_path.is_file():
        raise LogNotFoundError(f"Log file not found: {log_path}")
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return {
        "path": str(log_path),
        "stream": stream,
        "truncated": len(lines) > tail,
        "lines": lines[-tail:],
    }


def list_run_artifacts(*, session: Session, analysis_id: str, settings) -> dict[str, list[dict[str, Any]]] | None:
    run = _get_run(session, analysis_id)
    if run is None:
        return None
    workdir = _safe_workdir(run, settings)
    items = []
    for definition in ARTIFACTS:
        if not _artifact_applies_to_pipeline(definition, run.pipeline_name):
            continue
        path = _safe_child_path(workdir, definition.relative_path, settings)
        if not path.is_file():
            continue
        items.append(
            {
                "key": definition.key,
                "type": definition.type,
                "label": definition.label,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "url": definition.url.format(analysis_id=analysis_id),
            }
        )
    return {"items": items}


def _artifact_applies_to_pipeline(definition: ArtifactDefinition, pipeline_name: str) -> bool:
    if definition.key.startswith("pgta_") or definition.type.startswith("pgta_"):
        return pipeline_name == "pgta"
    if definition.key.startswith("wes_") or definition.type.startswith("wes_"):
        return pipeline_name == "wes_qsub"
    if definition.key.startswith("nipt_") or definition.type.startswith("nipt_"):
        return pipeline_name == "nipt_docker"
    return True


def build_error_summary(*, run: AnalysisRun, airflow_payload: dict[str, Any], settings) -> str:
    stderr_path = None
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
        "last_100_lines": last_lines,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _get_run(session: Session, analysis_id: str) -> AnalysisRun | None:
    return session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))


def _log_path(run: AnalysisRun, stream: str, settings) -> Path:
    if stream not in LOG_STREAMS:
        raise UnsupportedLogStreamError(f"Unsupported log stream: {stream}")
    return _safe_child_path(_safe_workdir(run, settings), LOG_STREAMS[stream], settings)


def _safe_workdir(run: AnalysisRun, settings) -> Path:
    shared_root = Path(settings.container_shared_root).resolve()
    workdir = Path(run.workdir).resolve()
    if not _is_relative_to(workdir, shared_root):
        raise InvalidRunPathError(f"Run workdir is outside shared root: {workdir}")
    return workdir


def _safe_child_path(workdir: Path, relative_path: Path, settings) -> Path:
    shared_root = Path(settings.container_shared_root).resolve()
    path = (workdir / relative_path).resolve()
    if not _is_relative_to(path, shared_root) or not _is_relative_to(path, workdir):
        raise InvalidRunPathError(f"Resolved path is outside run workdir: {path}")
    return path


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


def _sync_sample_statuses(*, session: Session, analysis_id: str, run_status: str) -> None:
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
