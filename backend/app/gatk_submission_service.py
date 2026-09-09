from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.airflow_idempotency import ensure_dag_run
from app.models import (
    AnalysisRun,
    PipelineSubmissionDraft,
    RunAttempt,
    Sample,
)


GATK_DAG_ID = "bio_gatk"
ANALYSIS_ID_PATTERN = re.compile(r"^GATK_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")
BATCH_PATTERN = re.compile(r"(?:^|_)([0-9]{8}[A-Z])(?:_|$)")
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class GatkInputChanged(ValueError):
    code = "GATK_INPUT_CHANGED"


class GatkDraftConflict(ValueError):
    code = "GATK_DRAFT_CONFLICT"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_scmc_sampleinfo(source: Path) -> tuple[Path, list[str]]:
    sampleinfo = source / f"{source.name.split('_V', 1)[0]}.sampleinfo.SCMC.txt"
    if not sampleinfo.is_file() or sampleinfo.is_symlink():
        raise ValueError(f"Required GATK input is missing: {sampleinfo.name}")
    try:
        with sampleinfo.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames is None or "\u6570\u636e\u7f16\u53f7" not in reader.fieldnames:
                raise ValueError("sampleinfo.SCMC.txt must contain the data ID column")
            samples = sorted(
                str(row.get("\u6570\u636e\u7f16\u53f7") or "").strip() for row in reader
            )
    except OSError as exc:
        raise ValueError(f"sampleinfo.SCMC.txt is not readable: {exc}") from exc
    if not samples or any(not item for item in samples) or len(samples) != len(set(samples)):
        raise ValueError("sampleinfo.SCMC.txt sample IDs must be non-empty and unique")
    return sampleinfo, samples


def _best_effort_fastq_inventory(source: Path, samples: list[str]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for sample in samples:
        for read in ("R1", "R2"):
            link = source / "a.raw" / f"{sample}.{read}.fq.gz"
            try:
                resolved = link.resolve(strict=True)
                if not resolved.is_file():
                    continue
                stat = resolved.stat()
            except OSError:
                continue
            files.append(
                {
                    "sample_id": sample,
                    "read": read,
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "resolved_path": str(resolved),
                }
            )
    return files


def _read_source(source: Path) -> dict[str, Any]:
    batch_match = BATCH_PATTERN.search(source.name)
    if batch_match is None:
        raise ValueError("WES project directory does not contain a YYYYMMDDX batch")
    batch = batch_match.group(1)
    sampleinfo, samples = _read_scmc_sampleinfo(source)
    files = _best_effort_fastq_inventory(source, samples)
    fingerprint_source = {
        "source": str(source),
        "batch": batch,
        "sampleinfo_sha256": _sha256(sampleinfo),
        "samples": samples,
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_source, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "batch": batch,
        "samples": samples,
        "sampleinfo_name": sampleinfo.name,
        "fastq_file_count": len(files),
        "fastq_total_bytes": sum(int(item["size"]) for item in files),
        "fingerprint": fingerprint,
        "file_evidence": files,
    }


def _public_preview(draft: PipelineSubmissionDraft) -> dict[str, Any]:
    preview = dict(draft.preview_json or {})
    return {
        "draft_id": draft.draft_id,
        "preview_hash": draft.input_fingerprint,
        "pipeline": "gatk",
        "profile_id": preview["profile_id"],
        "profile_revision": preview["profile_revision"],
        "batch": preview["batch"],
        "sampleinfo_name": preview["sampleinfo_name"],
        "sample_count": preview["sample_count"],
        "fastq_file_count": preview["fastq_file_count"],
        "fastq_total_bytes": preview["fastq_total_bytes"],
        "samples": list(preview["samples"]),
        "validation": dict(preview["validation"]),
        "expires_at": draft.expires_at.isoformat(),
    }


def _batch_lock_key(batch: str) -> int:
    digest = hashlib.sha256(f"gatk:{batch}".encode("ascii")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


def _lock_batch_submission(session: Session, batch: str) -> None:
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": _batch_lock_key(batch)},
        )


def create_gatk_submission_preview(
    *, session: Session, settings, source_project_dir: str, owner_username: str
) -> dict[str, Any]:
    requested_source = Path(source_project_dir)
    if not requested_source.is_absolute():
        raise ValueError("source_project_dir must be absolute")
    source = requested_source.resolve(strict=True)
    if not source.is_dir():
        raise ValueError("source_project_dir must be a real directory")
    evidence = _read_source(source)
    now = datetime.now(timezone.utc)
    draft = PipelineSubmissionDraft(
        draft_id=f"gatk-draft-{secrets.token_hex(12)}",
        pipeline_name="gatk",
        owner_username=owner_username,
        input_root=str(source),
        status="previewed",
        input_fingerprint=evidence["fingerprint"],
        preview_json={
            "profile_id": settings.gatk_runtime_profile_id,
            "profile_revision": settings.gatk_runtime_profile_revision,
            "batch": evidence["batch"],
            "sampleinfo_name": evidence["sampleinfo_name"],
            "sample_count": len(evidence["samples"]),
            "fastq_file_count": evidence["fastq_file_count"],
            "fastq_total_bytes": evidence["fastq_total_bytes"],
            "samples": evidence["samples"],
            "validation": {
                "source_directory_readable": True,
                "scmc_sampleinfo_present": True,
                "scmc_samples_present": True,
            },
        },
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(minutes=int(settings.gatk_submission_draft_ttl_minutes)),
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return _public_preview(draft)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _request_payload(*, settings, draft: PipelineSubmissionDraft, run: AnalysisRun) -> dict[str, Any]:
    preview = dict(draft.preview_json or {})
    node_root = Path(settings.gatk_runtime_node200_root)
    output_root = node_root / "runs" / run.analysis_id / "attempt-1"
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": "gatk-airflow-prepare",
        "analysis_id": run.analysis_id,
        "attempt": 1,
        "generation": 1,
        "source_project_dir": draft.input_root,
        "approved_source_roots": [draft.input_root],
        "approved_fastq_roots": list(settings.gatk_fastq_roots),
        "approved_output_roots": [str(node_root / "runs")],
        "output_root": str(output_root),
        "project_name": "WES_Clinical",
        "batch": preview["batch"],
        "run_id": f"{run.analysis_id}-a1",
        "operator_config": settings.gatk_operator_config,
        "profile_file": settings.gatk_profile_file,
        "runtime_file": settings.gatk_runtime_file,
        "pipeline_root": settings.gatk_pipeline_root,
        "cce_pipeline": settings.gatk_cce_pipeline,
        "result_root": str(Path(settings.gatk_result_root) / preview["batch"] / run.analysis_id),
        "profile_id": settings.gatk_runtime_profile_id,
        "profile_revision": settings.gatk_runtime_profile_revision,
    }
    payload["request_hash"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def confirm_gatk_submission(
    *,
    session: Session,
    settings,
    airflow_client,
    draft_id: str,
    preview_hash: str,
    project_name: str,
    submitted_by: str,
) -> dict[str, Any]:
    if not bool(settings.gatk_execution_enabled):
        raise GatkDraftConflict("GATK execution is disabled")
    draft = session.scalar(
        select(PipelineSubmissionDraft).where(
            PipelineSubmissionDraft.draft_id == draft_id,
            PipelineSubmissionDraft.pipeline_name == "gatk",
        ).with_for_update()
    )
    if draft is None or draft.owner_username != submitted_by:
        raise GatkDraftConflict("GATK submission draft is unavailable")
    now = datetime.now(timezone.utc)
    expires_at = draft.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now or draft.status != "previewed":
        raise GatkDraftConflict("GATK submission draft is expired or already consumed")
    if preview_hash != draft.input_fingerprint:
        raise GatkInputChanged("GATK preview hash does not match the draft")
    try:
        current = _read_source(Path(draft.input_root))
    except (OSError, ValueError) as exc:
        raise GatkInputChanged(f"GATK inputs changed after preview: {exc}") from exc
    if current["fingerprint"] != draft.input_fingerprint:
        raise GatkInputChanged("GATK inputs changed after preview")
    preview = dict(draft.preview_json or {})
    _lock_batch_submission(session, str(preview["batch"]))
    for existing in session.scalars(
        select(AnalysisRun).where(AnalysisRun.pipeline_name == "gatk")
    ).all():
        if str((existing.params_json or {}).get("batch") or "") == preview["batch"]:
            raise GatkDraftConflict("This GATK batch already has an analysis run")
    if SAFE_COMPONENT.fullmatch(project_name.strip()) is None:
        raise ValueError("project_name must be a safe component")
    analysis_id = f"GATK_{now:%Y%m%d_%H%M%S}_{secrets.token_hex(3).upper()}"
    pipeline_release_id = (
        f"{settings.gatk_runtime_profile_id}@{settings.gatk_runtime_profile_revision}"
    )
    runtime_workdir = Path(settings.gatk_runtime_node200_root) / "runs" / analysis_id
    run = AnalysisRun(
        analysis_id=analysis_id,
        pipeline_name="gatk",
        dag_id=GATK_DAG_ID,
        mode="new",
        execution_mode="cce",
        attempt=1,
        status="created",
        workdir=str(runtime_workdir),
        params_json={
            "project_name": project_name.strip(),
            "batch": preview["batch"],
            "source_project_name": Path(draft.input_root).name,
            "submission_draft_id": draft.draft_id,
            "submission_preview_hash": draft.input_fingerprint,
            "runtime_profile_id": settings.gatk_runtime_profile_id,
            "runtime_profile_revision": settings.gatk_runtime_profile_revision,
            "pipeline_release_id": pipeline_release_id,
            "target": "cloud_gatk_all",
            "orchestration_contract_version": 2,
        },
        submitted_by=submitted_by,
        current_stage="validate_request",
    )
    session.add(run)
    session.add(RunAttempt(analysis_id=analysis_id, attempt=1, execution_mode="cce", status="created"))
    for sample_id in preview["samples"]:
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id=sample_id,
                status="pending",
                qc_status="unknown",
                metadata_json={"source": "gatk_submission_draft"},
            )
        )
    session.flush()
    request = _request_payload(settings=settings, draft=draft, run=run)
    container_request = (
        Path(settings.gatk_runtime_request_root)
        / analysis_id
        / "attempt-1"
        / "prepare.request.json"
    )
    _atomic_json(container_request, request)
    node_request = (
        Path(settings.gatk_runtime_node200_root)
        / "requests"
        / analysis_id
        / "attempt-1"
        / "prepare.request.json"
    )
    conf = {
        "analysis_id": analysis_id,
        "pipeline": "gatk",
        "execution_mode": "cce",
        "attempt": 1,
        "params": {
            **dict(run.params_json or {}),
            "prepare_request_path": str(node_request),
        },
    }
    dag_run_id = f"{analysis_id}-a1"
    ensure_dag_run(
        airflow_client=airflow_client,
        dag_id=GATK_DAG_ID,
        dag_run_id=dag_run_id,
        conf=conf,
    )
    run.dag_run_id = dag_run_id
    run.status = "submitted"
    run.submitted_at = now
    run.current_stage = "queued"
    draft.status = "submitted"
    draft.analysis_id = analysis_id
    draft.updated_at = now
    for sample in session.scalars(select(Sample).where(Sample.analysis_id == analysis_id)).all():
        sample.status = "running"
    session.commit()
    return {
        "analysis_id": analysis_id,
        "pipeline": "gatk",
        "status": "submitted",
        "dag_id": GATK_DAG_ID,
        "dag_run_id": dag_run_id,
        "attempt": 1,
        "project_name": project_name.strip(),
        "batch_no": preview["batch"],
        "sample_count": len(preview["samples"]),
    }
