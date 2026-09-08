from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.gatk_stage_contract import gatk_stage_definition
from app.models import AnalysisRun, PipelineStageExecution, RunStageState, Sample
from app.wgs_observer import ingest_bound_pipeline_evidence_once


STAGES = (
    "prepare",
    "step1_upload",
    "step2_master",
    "step3_monitor",
    "step4_publish",
    "step5_download",
    "step6_materialize",
)
PREDECESSOR = {
    "step1_upload": "prepare",
    "step2_master": "step1_upload",
    "step3_monitor": "step2_master",
    "step4_publish": "step3_monitor",
    "step5_download": "step4_publish",
    "step6_materialize": "step5_download",
}
STAGE_LABELS = {
    "prepare": "Prepare GATK contract",
    "step1_upload": "Upload FASTQ",
    "step2_master": "Create GATK Master",
    "step3_monitor": "Run GATK analysis",
    "step4_publish": "Publish results",
    "step5_download": "Download results",
    "step6_materialize": "Materialize delivery",
}


def _canonical_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _request_path(settings, analysis_id: str, attempt: int, stage: str) -> Path:
    return (
        Path(settings.gatk_runtime_request_root)
        / analysis_id
        / f"attempt-{attempt}"
        / f"{stage}.request.json"
    )


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    partial.replace(path)


def register_gatk_stage(
    *, session: Session, settings, analysis_id: str, attempt: int, stage: str
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError("unsupported GATK runtime stage")
    run = session.scalar(
        select(AnalysisRun).where(
            AnalysisRun.analysis_id == analysis_id,
            AnalysisRun.pipeline_name == "gatk",
        )
    )
    if run is None or run.attempt != attempt:
        raise ValueError("unknown active GATK attempt")
    predecessor = None
    predecessor_stage = PREDECESSOR.get(stage)
    if predecessor_stage:
        predecessor = session.scalar(
            select(PipelineStageExecution)
            .where(
                PipelineStageExecution.pipeline_name == "gatk",
                PipelineStageExecution.analysis_id == analysis_id,
                PipelineStageExecution.attempt == attempt,
                PipelineStageExecution.stage_code == predecessor_stage,
                PipelineStageExecution.status == "success",
            )
            .order_by(PipelineStageExecution.generation.desc())
            .limit(1)
        )
        if predecessor is None or not predecessor.receipt_hash:
            raise ValueError(f"GATK predecessor {predecessor_stage} has no successful receipt")
    latest = session.scalar(
        select(PipelineStageExecution)
        .where(
            PipelineStageExecution.pipeline_name == "gatk",
            PipelineStageExecution.analysis_id == analysis_id,
            PipelineStageExecution.attempt == attempt,
            PipelineStageExecution.stage_code == stage,
        )
        .order_by(PipelineStageExecution.generation.desc())
        .limit(1)
    )
    if latest is not None and latest.status in {"accepted", "running", "success"}:
        _upsert_gatk_stage_state(
            session,
            analysis_id=analysis_id,
            attempt=attempt,
            stage_code=stage,
            stage_status=latest.status,
            updated_at=datetime.now(timezone.utc),
            progress_source="gatk-runtime",
            allow_terminal_reset=latest.status in {"accepted", "running"},
        )
        session.commit()
        return _execution_payload(latest)
    generation = (latest.generation + 1) if latest is not None else 1
    execution_id = f"{analysis_id}-a{attempt}-{stage}-g{generation}"
    node_root = Path(settings.gatk_runtime_node200_root)
    runtime_workdir = node_root / "runs" / analysis_id / f"attempt-{attempt}"
    request_path = _request_path(settings, analysis_id, attempt, stage)
    if stage == "prepare":
        if not request_path.is_file():
            raise ValueError("immutable GATK prepare request is missing")
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request_hash = str(request.get("request_hash") or "")
        if len(request_hash) != 64:
            raise ValueError("immutable GATK prepare request has no request hash")
    else:
        request = {
            "schema_version": "gatk-runtime.request.v1",
            "pipeline": "gatk",
            "analysis_id": analysis_id,
            "attempt": attempt,
            "generation": generation,
            "stage": stage,
            "orchestration_contract_version": 2,
            "execution_id": execution_id,
            "runtime_workdir": str(runtime_workdir),
            "cce_bundle": str(runtime_workdir / "cce"),
            "profile_id": (run.params_json or {}).get("runtime_profile_id"),
            "profile_revision": (run.params_json or {}).get("runtime_profile_revision"),
            "predecessor_execution_id": predecessor.execution_id if predecessor else None,
            "predecessor_receipt_hash": predecessor.receipt_hash if predecessor else None,
        }
        request_hash = _canonical_hash(request)
        request["request_hash"] = request_hash
    execution = PipelineStageExecution(
        execution_id=execution_id,
        pipeline_name="gatk",
        analysis_id=analysis_id,
        attempt=attempt,
        stage_code=stage,
        generation=generation,
        status="accepted",
        request_hash=request_hash,
        release_id=(
            f"{(run.params_json or {}).get('runtime_profile_id')}@"
            f"{(run.params_json or {}).get('runtime_profile_revision')}"
        ),
        predecessor_execution_id=predecessor.execution_id if predecessor else None,
        predecessor_generation=predecessor.generation if predecessor else None,
        predecessor_receipt_hash=predecessor.receipt_hash if predecessor else None,
    )
    session.add(execution)
    run.status = "running"
    run.current_stage = stage
    run.started_at = run.started_at or datetime.now(timezone.utc)
    if stage != "prepare":
        _atomic_json(request_path, request)
    _upsert_gatk_stage_state(
        session,
        analysis_id=analysis_id,
        attempt=attempt,
        stage_code=stage,
        stage_status="accepted",
        updated_at=datetime.now(timezone.utc),
        progress_available=False,
        progress_percent=None,
        completed_units=None,
        total_units=None,
        unit=None,
        progress_source="gatk-runtime",
        allow_terminal_reset=True,
    )
    session.commit()
    return _execution_payload(execution)


def _execution_payload(row: PipelineStageExecution) -> dict[str, Any]:
    return {
        "analysis_id": row.analysis_id,
        "attempt": row.attempt,
        "stage": row.stage_code,
        "generation": row.generation,
        "execution_id": row.execution_id,
        "status": row.status,
        "request_hash": row.request_hash,
    }


def sync_gatk_stage_status(
    *, session: Session, settings, analysis_id: str, attempt: int, stage: str
) -> dict[str, Any]:
    if stage in {"step1_upload", "step3_monitor", "step5_download"}:
        _ingest_gatk_evidence(session=session, settings=settings, analysis_id=analysis_id, attempt=attempt)
    row = session.scalar(
        select(PipelineStageExecution)
        .where(
            PipelineStageExecution.pipeline_name == "gatk",
            PipelineStageExecution.analysis_id == analysis_id,
            PipelineStageExecution.attempt == attempt,
            PipelineStageExecution.stage_code == stage,
        )
        .order_by(PipelineStageExecution.generation.desc())
        .limit(1)
    )
    if row is None:
        return {"status": "pending", "ready": False, "failed": False}
    path = _request_path(settings, analysis_id, attempt, stage)
    sidecar = path.with_suffix(".status.json")
    if sidecar.is_file():
        try:
            value = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid GATK stage sidecar: {exc}") from exc
        if (
            value.get("analysis_id") != analysis_id
            or value.get("attempt") != attempt
            or value.get("stage") != stage
            or value.get("generation") != row.generation
            or value.get("request_hash") != row.request_hash
            or (
                stage != "prepare"
                and value.get("execution_id") != row.execution_id
            )
        ):
            raise ValueError("GATK stage sidecar identity mismatch")
        state = str(value.get("status") or "running").lower()
        if state in {"running", "success", "failed", "canceled"}:
            row.status = state
            row.message = str(value.get("message") or "") or None
            row.heartbeat_at = datetime.now(timezone.utc)
            row.started_at = row.started_at or datetime.now(timezone.utc)
            if state in {"success", "failed", "canceled"}:
                row.ended_at = datetime.now(timezone.utc)
                row.receipt_hash = str(value.get("receipt_hash") or _canonical_hash(value))
                row.terminal_payload_json = value
            _upsert_gatk_stage_state(
                session,
                analysis_id=analysis_id,
                attempt=attempt,
                stage_code=stage,
                stage_status=state,
                updated_at=datetime.now(timezone.utc),
                progress_available=isinstance(value.get("progress_percent"), (int, float)),
                progress_percent=value.get("progress_percent"),
                completed_units=value.get("completed_units"),
                total_units=value.get("total_units"),
                unit=value.get("unit"),
                current_item=value.get("current_item"),
                progress_source="gatk-runtime",
            )
            session.commit()
    failed = row.status in {"failed", "canceled"}
    return {
        **_execution_payload(row),
        "ready": row.status == "success",
        "failed": failed,
        "message": row.message,
    }


def _ingest_gatk_evidence(
    *, session: Session, settings, analysis_id: str, attempt: int
) -> None:
    request_root = Path(settings.gatk_runtime_request_root).resolve()
    runtime_root = request_root.parent
    binding_path = runtime_root / "runs" / analysis_id / f"attempt-{attempt}" / "batch-binding.json"
    if not binding_path.is_file() or binding_path.is_symlink():
        return
    try:
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if (
        binding.get("schema_version") != "gatk-runtime.batch-binding.v1"
        or binding.get("analysis_id") != analysis_id
        or int(binding.get("attempt") or 0) != attempt
    ):
        raise ValueError("GATK evidence binding identity mismatch")
    evidence_root = Path(
        getattr(settings, "gatk_evidence_root", "/data/gatk-evidence")
    ).resolve()
    evidence_directory = evidence_root / analysis_id / f"attempt-{attempt}"
    ingest_bound_pipeline_evidence_once(
        session_factory=sessionmaker(bind=session.get_bind()),
        analysis_id=analysis_id,
        attempt=attempt,
        pipeline_release_id=str(binding.get("pipeline_release_id") or ""),
        run_label=str(binding.get("run_label") or ""),
        evidence_root=evidence_root,
        evidence_directory=evidence_directory,
        transfer_spool_root=Path(settings.gatk_transfer_spool_root),
    )


def finalize_gatk_run(
    *, session: Session, settings, analysis_id: str, attempt: int
) -> dict[str, Any]:
    status = sync_gatk_stage_status(
        session=session,
        settings=settings,
        analysis_id=analysis_id,
        attempt=attempt,
        stage="step6_materialize",
    )
    if not status.get("ready"):
        raise ValueError("GATK Step6 materialization is not complete")
    run = session.scalar(
        select(AnalysisRun).where(
            AnalysisRun.analysis_id == analysis_id,
            AnalysisRun.pipeline_name == "gatk",
        )
    )
    if run is None or run.attempt != attempt:
        raise ValueError("unknown active GATK attempt")
    now = datetime.now(timezone.utc)
    run.status = "success"
    run.current_stage = "finalize_run"
    run.progress_percent = 100
    run.progress_updated_at = now
    run.pipeline_finished_at = run.pipeline_finished_at or now
    run.ended_at = run.ended_at or now
    for sample in session.scalars(select(Sample).where(Sample.analysis_id == analysis_id)).all():
        sample.status = "success"
    session.commit()
    return {"analysis_id": analysis_id, "attempt": attempt, "status": "success"}


def _upsert_gatk_stage_state(
    session: Session,
    *,
    analysis_id: str,
    attempt: int,
    stage_code: str,
    stage_status: str,
    updated_at: datetime,
    progress_available: bool = False,
    progress_percent: int | float | None = None,
    completed_units: int | None = None,
    total_units: int | None = None,
    unit: str | None = None,
    current_item: str | None = None,
    progress_source: str = "gatk-runtime",
    allow_terminal_reset: bool = False,
) -> RunStageState:
    definition = gatk_stage_definition(stage_code)
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
    elif row.ended_at is not None and row.stage_status in {"success", "failed", "canceled"}:
        if not allow_terminal_reset:
            return row
        row.started_at = None
        row.ended_at = None
    row.stage_status = stage_status
    row.progress_available = progress_available
    row.progress_percent = int(progress_percent) if progress_available and progress_percent is not None else None
    row.completed_units = completed_units if progress_available else None
    row.total_units = total_units if progress_available else None
    row.unit = unit if progress_available else None
    row.current_item = current_item
    row.progress_source = progress_source
    if stage_status in {"accepted", "running"} and row.started_at is None:
        row.started_at = updated_at
    if stage_status in {"success", "failed", "canceled"}:
        row.ended_at = updated_at
    row.updated_at = updated_at
    return row
