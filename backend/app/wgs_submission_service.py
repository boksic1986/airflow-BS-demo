from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets

from sqlalchemy import select

from app.models import AnalysisRun, RunAction, Sample, WgsInputSnapshot, WgsSubmissionDraft
from app.wgs_orchestration_service import build_fastq_snapshot, fastq_source_fingerprint
from app.wgs_platform_service import (
    action_wgs_run,
    create_wgs_platform_run,
    run_payload,
    submit_wgs_run,
)
from app.wgs_project_catalog import WgsProject, load_wgs_projects
from app.wgs_release_catalog import load_wgs_release_catalog


SAFE_BATCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
SAFE_SAMPLE_FIELDS = {
    "sample_id", "data_id", "family_id", "family_relation", "sample_type",
    "sex", "sequencing_batch", "r1_filename", "r2_filename", "status",
    "pending_source", "pending_reason", "fastq_pair_status",
}


@dataclass(frozen=True)
class CatalogRunSpec:
    project: WgsProject
    platform: str
    batch: str
    analysis_batch: str
    node_root: str
    batch_no: str
    use_reference: str


def create_draft(*, session, settings, owner_username: str, project_id: str, platform: str,
                 sequencing_batch: str, analysis_batch: str, fastq_root_id: str,
                 use_reference: bool) -> dict:
    project = _project(settings, project_id)
    project.platform(platform)
    root = project.fastq_root(fastq_root_id)
    for label, value in (("sequencing_batch", sequencing_batch), ("analysis_batch", analysis_batch)):
        if SAFE_BATCH.fullmatch(value.strip()) is None:
            raise ValueError(f"{label} contains unsupported characters")
    draft_id = f"WGSD_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{secrets.token_hex(3).upper()}"
    private_root = Path(settings.wgs_submission_draft_root).resolve()
    workdir = private_root / draft_id
    workdir.mkdir(parents=True, exist_ok=False)
    request = {
        "schema_version": "wgs-submission-draft.request.v1",
        "draft_id": draft_id,
        "project_id": project.project_id,
        "platform": platform,
        "sequencing_batch": sequencing_batch.strip(),
        "analysis_batch": analysis_batch.strip(),
        "fastq_root_id": fastq_root_id,
        "use_reference": bool(use_reference),
    }
    (workdir / "request.json").write_text(json.dumps(request, sort_keys=True) + "\n", encoding="utf-8")
    now = datetime.now(timezone.utc)
    row = WgsSubmissionDraft(
        draft_id=draft_id,
        owner_username=owner_username,
        project_id=project.project_id,
        platform=platform,
        sequencing_batch=sequencing_batch.strip(),
        analysis_batch=analysis_batch.strip(),
        fastq_root_id=fastq_root_id,
        fastq_path=str(root["node200_path"]),
        use_reference=bool(use_reference),
        status="queued",
        preview_json={},
        resolved_config_json={"use_reference": bool(use_reference)},
        private_workdir=str(workdir),
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=int(getattr(settings, "wgs_submission_draft_ttl_hours", 24))),
    )
    session.add(row)
    session.commit()
    return draft_payload(row)


def get_draft(*, session, draft_id: str, username: str, is_admin: bool = False) -> dict | None:
    row = session.scalar(select(WgsSubmissionDraft).where(WgsSubmissionDraft.draft_id == draft_id))
    if row is None or (not is_admin and row.owner_username != username):
        return None
    return draft_payload(row)


def complete_draft(*, session, settings, draft_id: str, prepared_fq_path: str,
                   samples: list[dict], families: list[dict], resolved_config: dict,
                   source_fingerprint: str) -> dict | None:
    row = session.scalar(select(WgsSubmissionDraft).where(WgsSubmissionDraft.draft_id == draft_id).with_for_update())
    if row is None:
        return None
    if row.status == "preview_ready":
        return draft_payload(row)
    if row.status not in {"queued", "preparing"}:
        raise ValueError(f"draft status {row.status} cannot accept a preview")
    if not re.fullmatch(r"[0-9a-f]{64}", source_fingerprint):
        raise ValueError("source_fingerprint must be a SHA256 hex digest")
    controlled = Path(prepared_fq_path).resolve()
    allowed = [Path(root).resolve() for root in getattr(settings, "wgs_config_roots", [])]
    if not any(controlled == root or root in controlled.parents for root in allowed):
        raise ValueError("prepared FASTQ directory is outside controlled WGS roots")
    safe_samples = [{key: value for key, value in sample.items() if key in SAFE_SAMPLE_FIELDS} for sample in samples]
    safe_families = [
        {key: value for key, value in family.items() if key in {"family_id", "sample_count", "status", "message"}}
        for family in families
    ]
    row.fastq_path = str(controlled)
    row.source_fingerprint = source_fingerprint
    row.preview_json = {"samples": safe_samples, "families": safe_families}
    row.resolved_config_json = {"use_reference": bool(row.use_reference), **{key: resolved_config[key] for key in ("profile_id", "resource_set") if key in resolved_config}}
    row.status = "preview_ready"
    row.error_message = None
    row.updated_at = datetime.now(timezone.utc)
    session.commit()
    return draft_payload(row)


def submit_draft(*, session, settings, airflow_client, draft_id: str, username: str,
                 idempotency_key: str) -> dict | None:
    row = session.scalar(select(WgsSubmissionDraft).where(WgsSubmissionDraft.draft_id == draft_id).with_for_update())
    if row is None or row.owner_username != username:
        return None
    if row.analysis_id:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == row.analysis_id))
        if run is None:
            raise RuntimeError("draft is bound to a missing AnalysisRun")
        if run.status == "created":
            payload = submit_wgs_run(
                session=session,
                airflow_client=airflow_client,
                analysis_id=run.analysis_id,
            )
        else:
            payload = run_payload(session, run)
        if run.status == "submitted" and row.status != "submitted":
            row.status = "submitted"
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
        return payload
    if row.status != "preview_ready":
        raise ValueError("sampleinfo preview is not ready")
    now = datetime.now(timezone.utc)
    expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise ValueError("submission draft has expired")
    if not idempotency_key or len(idempotency_key) > 128:
        raise ValueError("Idempotency-Key is required")
    verification = build_fastq_snapshot(
        fq_path=row.fastq_path,
        allowed_link_roots=list(getattr(settings, "wgs_config_roots", []) or []),
        allowed_fastq_roots=list(getattr(settings, "wgs_fastq_roots", []) or []),
        manifest_path=Path(row.private_workdir) / "submit-input-manifest.json",
    )
    if fastq_source_fingerprint(verification) != row.source_fingerprint:
        raise ValueError("submission draft source fingerprint changed")
    key_digest = hashlib.sha256(f"{username}:{idempotency_key}".encode()).hexdigest()
    prior = session.scalar(
        select(WgsSubmissionDraft).where(
            WgsSubmissionDraft.idempotency_key == key_digest,
            WgsSubmissionDraft.draft_id != row.draft_id,
        )
    )
    if prior is not None:
        if prior.owner_username != username or not prior.analysis_id:
            raise ValueError("Idempotency-Key is already in use")
        prior_run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == prior.analysis_id)
        )
        if prior_run is None:
            raise RuntimeError("idempotency record is bound to a missing AnalysisRun")
        return submit_wgs_run(
            session=session,
            airflow_client=airflow_client,
            analysis_id=prior_run.analysis_id,
        ) if prior_run.status == "created" else run_payload(session, prior_run)
    row.idempotency_key = key_digest
    session.flush()
    project = _project(settings, row.project_id)
    created = create_wgs_platform_run(
        session=session,
        settings=settings,
        project_name=project.project_name,
        execution_mode="cce",
        batch_no=row.analysis_batch,
        fq_path=row.fastq_path,
        submitted_by=username,
        commit=False,
    )
    row.analysis_id = str(created["analysis_id"])
    row.status = "ready_to_submit"
    row.updated_at = datetime.now(timezone.utc)
    session.commit()
    payload = submit_wgs_run(session=session, airflow_client=airflow_client, analysis_id=row.analysis_id)
    row = session.scalar(select(WgsSubmissionDraft).where(WgsSubmissionDraft.draft_id == draft_id).with_for_update())
    row.status = "submitted"
    row.updated_at = datetime.now(timezone.utc)
    session.commit()
    return payload


def draft_payload(row: WgsSubmissionDraft) -> dict:
    return {
        "draft_id": row.draft_id,
        "project_id": row.project_id,
        "platform": row.platform,
        "sequencing_batch": row.sequencing_batch,
        "analysis_batch": row.analysis_batch,
        "fastq_root_id": row.fastq_root_id,
        "use_reference": row.use_reference,
        "status": row.status,
        "preview": dict(row.preview_json or {}),
        "resolved_config": dict(row.resolved_config_json or {}),
        "error_message": row.error_message,
        "analysis_id": row.analysis_id,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "expires_at": row.expires_at.isoformat(),
    }


def _project(settings, project_id: str) -> WgsProject:
    projects = load_wgs_projects(settings.wgs_project_catalog_path)
    project = next((item for item in projects if item.project_id == project_id), None)
    if project is None:
        raise ValueError("unknown WGS project")
    return project


def create_and_submit_run(*, session, settings, airflow_client, username: str,
                          project_id: str, platform: str, batch: str,
                          fastq_root_id: str,
                          use_reference: str | None = None,
                          validation_scope: str | None = None) -> dict:
    """Create one catalog-bound run; WGS prepare owns sampleinfo and selection."""
    if validation_scope not in {None, "step1_only"}:
        raise ValueError("unsupported WGS validation scope")
    spec = _catalog_run_spec(
        settings=settings,
        project_id=project_id,
        platform=platform,
        batch=batch,
        fastq_root_id=fastq_root_id,
        use_reference=use_reference,
        validation_scope=validation_scope,
    )
    run, existed = _create_catalog_run_record(
        session=session,
        settings=settings,
        username=username,
        spec=spec,
    )
    existing_scope = (run.params_json or {}).get("validation_scope")
    if existed and existing_scope != validation_scope:
        raise ValueError("existing WGS run uses a different validation scope")
    if run.status == "success":
        raise ValueError(
            f"batch {spec.batch} already completed as {run.analysis_id}"
        )
    if run.status not in {"created", "failed", "cancelled", "unknown_interrupted"}:
        return run_payload(session, run)
    restart_failed_attempt = run.status in {
        "failed",
        "cancelled",
        "unknown_interrupted",
    }
    params = dict(run.params_json or {})
    if validation_scope is not None:
        params["validation_scope"] = validation_scope
    params.update(
        {
            "submission_mode": "three_stage",
            "submission_phase": "preparing_sampleinfo",
            "config_approved_at": None,
            "execution_approved_at": None,
            "resource_set": "default",
        }
    )
    run.params_json = params
    session.commit()
    if restart_failed_attempt:
        return action_wgs_run(
            session=session,
            airflow_client=airflow_client,
            analysis_id=run.analysis_id,
            action="rerun_failed",
            requested_by=username,
        )
    return submit_wgs_run(
        session=session,
        airflow_client=airflow_client,
        analysis_id=run.analysis_id,
    )


def create_automatic_wgs_run(*, session, settings, airflow_client, username: str,
                             project_id: str, platform: str, batch: str,
                             fastq_root_id: str,
                             use_reference: str | None = None) -> dict:
    """Create one pre-approved intake run without reviving a terminal attempt."""
    spec = _catalog_run_spec(
        settings=settings,
        project_id=project_id,
        platform=platform,
        batch=batch,
        fastq_root_id=fastq_root_id,
        use_reference=use_reference,
    )
    run, existed = _create_catalog_run_record(
        session=session,
        settings=settings,
        username=username,
        spec=spec,
    )
    params = dict(run.params_json or {})
    if existed and params.get("submission_mode") != "auto_dispatch":
        return run_payload(session, run)
    if not existed:
        approved_at = datetime.now(timezone.utc).isoformat()
        params.update(
            {
                "submission_mode": "auto_dispatch",
                "submission_phase": "approved",
                "config_approved_at": approved_at,
                "execution_approved_at": approved_at,
                "resource_set": "default",
            }
        )
        run.params_json = params
        session.commit()
    if run.status == "created":
        return submit_wgs_run(
            session=session,
            airflow_client=airflow_client,
            analysis_id=run.analysis_id,
        )
    return run_payload(session, run)


def _catalog_run_spec(*, settings, project_id: str, platform: str, batch: str,
                      fastq_root_id: str,
                      use_reference: str | None,
                      validation_scope: str | None = None) -> CatalogRunSpec:
    project = _project(settings, project_id)
    project.platform(platform)
    root = project.fastq_root(fastq_root_id)
    normalized_batch = batch.strip()
    if (
        SAFE_BATCH.fullmatch(normalized_batch) is None
        or not re.fullmatch(r"[0-9]{8}[A-Z]", normalized_batch)
    ):
        raise ValueError("batch must use YYYYMMDDX format")
    normalized_reference = "all" if use_reference is None else use_reference
    if normalized_reference not in {"all", "ref", "no"}:
        raise ValueError("use_reference must be all, ref, or no")
    release = load_wgs_release_catalog(Path(settings.wgs_release_catalog_path)).release
    analysis_batch = (
        f"{normalized_batch}_STEP1_CANARY"
        if validation_scope == "step1_only"
        else normalized_batch
    )
    return CatalogRunSpec(
        project=project,
        platform=platform,
        batch=normalized_batch,
        analysis_batch=analysis_batch,
        node_root=str(root["node200_path"]),
        batch_no=f"WGS_{analysis_batch}_{platform}Hg38{release.version}",
        use_reference=normalized_reference,
    )


def _create_catalog_run_record(*, session, settings, username: str,
                               spec: CatalogRunSpec) -> tuple[AnalysisRun, bool]:
    existed = session.scalar(
        select(WgsInputSnapshot).where(
            WgsInputSnapshot.batch_no == spec.batch_no,
            WgsInputSnapshot.fq_path == spec.node_root,
        )
    ) is not None
    created = create_wgs_platform_run(
        session=session,
        settings=settings,
        project_name=spec.project.project_name,
        execution_mode="cce",
        batch_no=spec.batch_no,
        fq_path=spec.node_root,
        submitted_by=username,
        commit=False,
        validate_input=False,
        platform=spec.platform,
        sequencing_batch=spec.batch,
        analysis_batch=spec.analysis_batch,
        fastq_root=spec.node_root,
        use_reference=spec.use_reference,
    )
    run = session.scalar(
        select(AnalysisRun).where(AnalysisRun.analysis_id == created["analysis_id"])
    )
    if run is None:
        raise RuntimeError("created WGS run is missing")
    return run, existed


def submission_state(*, session, analysis_id: str, attempt: int) -> dict:
    run = session.scalar(
        select(AnalysisRun).where(
            AnalysisRun.analysis_id == analysis_id,
            AnalysisRun.pipeline_name == "wgs",
        )
    )
    if run is None or run.attempt != attempt:
        raise ValueError("unknown active WGS attempt")
    params = dict(run.params_json or {})
    staged = params.get("submission_mode") == "three_stage"
    return {
        "analysis_id": analysis_id,
        "attempt": attempt,
        "submission_mode": "three_stage" if staged else "legacy",
        "submission_phase": params.get("submission_phase") if staged else "approved",
        "config_approved": (not staged) or bool(params.get("config_approved_at")),
        "execution_approved": (not staged) or bool(params.get("execution_approved_at")),
    }


def approve_wgs_config(*, session, analysis_id: str, requested_by: str,
                       use_reference: str, resource_set: str) -> dict:
    if use_reference not in {"all", "ref", "no"}:
        raise ValueError("use_reference must be all, ref, or no")
    if resource_set != "default":
        raise ValueError("resource_set is not in the current WGS catalog")
    run = session.scalar(
        select(AnalysisRun).where(
            AnalysisRun.analysis_id == analysis_id,
            AnalysisRun.pipeline_name == "wgs",
        ).with_for_update()
    )
    if run is None:
        raise ValueError("WGS run was not found")
    params = dict(run.params_json or {})
    if params.get("submission_mode") != "three_stage":
        raise ValueError("WGS run does not use staged submission")
    if params.get("config_approved_at"):
        if params.get("use_reference") != use_reference or params.get("resource_set") != resource_set:
            raise ValueError("WGS configuration was already approved with different values")
        return submission_state(session=session, analysis_id=analysis_id, attempt=run.attempt)
    if params.get("submission_phase") not in {"config_review", "preparing_analysis"}:
        raise ValueError("WGS sample information is not ready for configuration review")
    approved_at = datetime.now(timezone.utc).isoformat()
    params.update({
        "use_reference": use_reference,
        "resource_set": resource_set,
        "config_approved_at": approved_at,
        "submission_phase": "preparing_analysis",
    })
    run.params_json = params
    session.add(RunAction(
        analysis_id=analysis_id,
        action="approve_wgs_config",
        requested_by=requested_by,
        result_status="accepted",
        payload_json={"use_reference": use_reference, "resource_set": resource_set},
    ))
    session.commit()
    return submission_state(session=session, analysis_id=analysis_id, attempt=run.attempt)


def approve_wgs_execution(*, session, analysis_id: str, requested_by: str) -> dict:
    run = session.scalar(
        select(AnalysisRun).where(
            AnalysisRun.analysis_id == analysis_id,
            AnalysisRun.pipeline_name == "wgs",
        ).with_for_update()
    )
    if run is None:
        raise ValueError("WGS run was not found")
    params = dict(run.params_json or {})
    if params.get("submission_mode") != "three_stage":
        raise ValueError("WGS run does not use staged submission")
    if params.get("submission_phase") not in {"execution_review", "approved"}:
        raise ValueError("WGS analysis preparation is not ready for execution review")
    if session.scalar(
        select(Sample.id).where(Sample.analysis_id == analysis_id).limit(1)
    ) is None:
        raise ValueError("WGS analysis has no prepared samples")
    if not params.get("execution_approved_at"):
        params.update({
            "execution_approved_at": datetime.now(timezone.utc).isoformat(),
            "submission_phase": "approved",
        })
        run.params_json = params
        session.add(RunAction(
            analysis_id=analysis_id,
            action="approve_wgs_execution",
            requested_by=requested_by,
            result_status="accepted",
            payload_json={"attempt": run.attempt},
        ))
        session.commit()
    return submission_state(session=session, analysis_id=analysis_id, attempt=run.attempt)
