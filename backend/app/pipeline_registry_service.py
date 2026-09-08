from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.pipeline_registry import (
    PipelineAdapter,
    PipelineCapabilityUnavailable,
    PipelineDefinition,
    PipelineRegistry,
    PipelineRegistryError,
    build_pipeline_registry,
    load_pipeline_registry,
)
from app.wgs_platform_service import create_wgs_platform_run
from app.wgs_platform_service import action_wgs_run, submit_wgs_run
from app.models import ObserverRunState, RunStageState, Sample
from app.wgs_execution_dispatch_service import project_execution_dispatch
from app.wgs_lifecycle_service import project_wgs_lifecycle, project_wgs_lifecycles
from app.wgs_sample_projection import get_wgs_sample_projection
from app.wgs_stage_contract import project_wgs_orchestration, terminal_wgs_progress
from app.wgs_step4_service import get_step4_repair_capability
from app.wgs_step7_service import get_step7_capability
from app.wgs_t7_intake import get_wgs_t7_scanner_state, list_wgs_t7_intake
from app.wgs_timing_service import enrich_progress
from app.wgs_run_projection import public_wgs_batch
from app.workflow_phases import wgs_phase_for_rule
from app.diagnostics_service import (
    get_gatk_run_log,
    get_wgs_run_log,
    list_gatk_run_artifacts,
    list_gatk_run_logs,
    list_wgs_run_artifacts,
    list_wgs_run_logs,
    sync_wgs_airflow_status,
)
from app.gatk_submission_service import confirm_gatk_submission
from app.gatk_stage_contract import project_gatk_orchestration
from app.workflow_phases import gatk_phase_for_rule


DEFAULT_REGISTRY_PAYLOAD: dict[str, Any] = {
    "version": 1,
    "pipelines": {
        "wgs": {
            "display_name": "WGS",
            "dag_id": "bio_wgs",
            "adapter": "wgs",
            "enabled": True,
            "submit_enabled": True,
            "capabilities": ["intake", "submit", "rules", "qc", "artifacts", "resume", "rerun"],
            "execution_targets": ["cce", "local", "sge"],
        }
    },
}


def _create_wgs_run(*, session, settings, request, user, **_) -> dict[str, Any]:
    if not str(request.batch_no or "").strip() or not str(request.fq_path or "").strip():
        raise ValueError("batch_no and fq_path are required for pipeline=wgs.")
    return create_wgs_platform_run(
        session=session,
        settings=settings,
        project_name=request.project_name,
        execution_mode=request.execution_mode,
        batch_no=str(request.batch_no or ""),
        fq_path=str(request.fq_path or ""),
        submitted_by=user.username,
    )


def _create_gatk_run(
    *, session, settings, request, user, airflow_client=None, **_
) -> dict[str, Any]:
    draft_id = str(getattr(request, "submission_draft_id", None) or "").strip()
    preview_hash = str(
        getattr(request, "submission_preview_hash", None) or ""
    ).strip()
    if not draft_id or not preview_hash:
        raise ValueError(
            "submission_draft_id and submission_preview_hash are required for pipeline=gatk."
        )
    if request.execution_mode != "cce":
        raise ValueError("execution_mode must be cce for pipeline=gatk.")
    if airflow_client is None:
        raise ValueError("Airflow client is required for GATK confirmation.")
    return confirm_gatk_submission(
        session=session,
        settings=settings,
        airflow_client=airflow_client,
        draft_id=draft_id,
        preview_hash=preview_hash,
        project_name=request.project_name,
        submitted_by=user.username,
    )


def _project_gatk_samples(*, session, run, **_) -> dict[str, Any]:
    rows = list(
        session.scalars(
            select(Sample)
            .where(Sample.analysis_id == run.analysis_id)
            .order_by(Sample.sample_id)
        ).all()
    )
    return {
        "items": [
            {
                "sample_id": row.sample_id,
                "family_id": row.family_id,
                "status": row.status,
                "qc_status": None,
                "metadata": {"source": "locked SCMC submission"},
            }
            for row in rows
        ]
    }


def _project_gatk_run_detail(*, run, **_) -> dict[str, Any]:
    params = dict(run.params_json or {})
    return {
        "pipeline_release_id": (
            f"{params.get('runtime_profile_id')}@{params.get('runtime_profile_revision')}"
        ),
        "gatk_version": "V7.6.0",
        "runtime_profile_id": params.get("runtime_profile_id"),
        "submission_preview_hash": params.get("submission_preview_hash"),
    }


def _project_gatk_dashboard_metadata(*, run, **_) -> dict[str, Any]:
    params = dict(run.params_json or {})
    return {
        "batch_no": params.get("batch"),
        "display_status": str(run.status or "").lower(),
        "qc_display_status": "not_applicable",
        "qc_display_note": "GATK v1 reports workflow and delivery integrity only.",
    }


def _project_gatk_sample_summary(*, run, sample, metadata, **_) -> dict[str, Any]:
    return {
        "batch_no": (run.params_json or {}).get("batch"),
        "qc_status": None,
        "family_relation": None,
        "sample_type": sample.sample_type,
        "sex": sample.sex,
        "sequencing_batch": None,
    }


def _enabled_env_flag(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def _submit_wgs_run(*, session, airflow_client, analysis_id: str, **_) -> dict[str, Any] | None:
    if not _enabled_env_flag("WGS_EXECUTION_ENABLED") or not _enabled_env_flag(
        "WGS_RUNTIME_ADAPTER_ENABLED"
    ):
        raise PipelineCapabilityUnavailable(
            "WGS execution is disabled by the active deployment configuration."
        )
    return submit_wgs_run(
        session=session,
        airflow_client=airflow_client,
        analysis_id=analysis_id,
    )


def _reanalyze_wgs_run(
    *, session, airflow_client, analysis_id: str, request, user, **_
) -> dict[str, Any] | None:
    if not _enabled_env_flag("WGS_EXECUTION_ENABLED") or not _enabled_env_flag(
        "WGS_RUNTIME_ADAPTER_ENABLED"
    ):
        raise PipelineCapabilityUnavailable(
            "WGS execution is disabled by the active deployment configuration."
        )
    return action_wgs_run(
        session=session,
        airflow_client=airflow_client,
        analysis_id=analysis_id,
        action=request.mode,
        requested_by=user.username,
    )


def _project_wgs_qc(*, session, settings, run, **_) -> dict[str, Any]:
    projection = get_wgs_sample_projection(
        session=session,
        settings=settings,
        run=run,
    )
    return {
        "analysis_id": run.analysis_id,
        "items": projection["items"],
        "source": "pipeline_adapter",
    }


def _project_wgs_samples(*, session, settings, run, **_) -> dict[str, Any]:
    return get_wgs_sample_projection(session=session, settings=settings, run=run)


def _project_wgs_run_detail(*, session, settings, run, **_) -> dict[str, Any]:
    observer = session.scalar(
        select(ObserverRunState).where(
            ObserverRunState.analysis_id == run.analysis_id,
            ObserverRunState.attempt == run.attempt,
        )
    )
    params = dict(run.params_json or {})
    return {
        "pipeline_release_id": params.get("pipeline_release_id"),
        "wgs_version": params.get("wgs_version"),
        "wgs_source_commit": params.get("wgs_source_commit"),
        "resolved_runtime": params.get("resolved_runtime"),
        "rule_event_schema_version": params.get("rule_event_schema_version"),
        "observer": _observer_payload(observer),
        "step4_repair": get_step4_repair_capability(
            session=session,
            run=run,
            execution_enabled=_enabled_env_flag("WGS_EXECUTION_ENABLED"),
            runtime_adapter_enabled=_enabled_env_flag("WGS_RUNTIME_ADAPTER_ENABLED"),
        ),
        "step7_cleanup": get_step7_capability(
            session=session,
            run=run,
            execution_enabled=_enabled_env_flag("WGS_EXECUTION_ENABLED"),
            runtime_adapter_enabled=_enabled_env_flag("WGS_RUNTIME_ADAPTER_ENABLED"),
        ),
        "execution_dispatch": project_execution_dispatch(
            session=session,
            settings=settings,
            run=run,
        ),
        "lifecycle": project_wgs_lifecycle(session=session, run=run),
    }


def _observer_payload(observer) -> dict[str, Any] | None:
    if observer is None:
        return None
    return {
        "lifecycle_status": observer.lifecycle_status,
        "monitoring_health": observer.monitoring_health,
        "activated_at": observer.activated_at.isoformat() if observer.activated_at else None,
        "deactivated_at": observer.deactivated_at.isoformat() if observer.deactivated_at else None,
        "last_success_at": observer.last_success_at.isoformat() if observer.last_success_at else None,
        "last_error": observer.last_error,
        "updated_at": observer.updated_at.isoformat(),
    }


def _project_wgs_workflows(*, session, runs, **_) -> dict[str, list[dict[str, Any]]]:
    if not runs:
        return {}
    attempts = {(run.analysis_id, run.attempt) for run in runs}
    stage_rows = list(
        session.scalars(
            select(RunStageState).where(
                RunStageState.analysis_id.in_([run.analysis_id for run in runs])
            )
        ).all()
    )
    rows_by_attempt: dict[tuple[str, int], list[RunStageState]] = {
        key: [] for key in attempts
    }
    for row in stage_rows:
        rows_by_attempt.setdefault((row.analysis_id, row.attempt), []).append(row)
    return {
        run.analysis_id: project_wgs_orchestration(
            run_status=run.status,
            current_stage=run.current_stage,
            stage_rows=rows_by_attempt.get((run.analysis_id, run.attempt), []),
        )
        for run in runs
    }
def _project_gatk_workflows(*, session, runs, **_) -> dict[str, list[dict[str, Any]]]:
    if not runs:
        return {}
    stage_rows = list(
        session.scalars(
            select(RunStageState).where(
                RunStageState.analysis_id.in_([run.analysis_id for run in runs])
            )
        ).all()
    )
    rows_by_attempt: dict[tuple[str, int], list[RunStageState]] = {}
    for row in stage_rows:
        rows_by_attempt.setdefault((row.analysis_id, row.attempt), []).append(row)
    return {
        run.analysis_id: project_gatk_orchestration(
            run_status=run.status,
            current_stage=run.current_stage,
            stage_rows=rows_by_attempt.get((run.analysis_id, run.attempt), []),
        )
        for run in runs
    }


def _project_gatk_rule_context(*, run, **_) -> dict[str, Any]:
    return {
        "pipeline_name": run.pipeline_name,
        "pipeline_stage": "full",
        "phase_projector": lambda rule, **_: gatk_phase_for_rule(rule),
    }


def _project_wgs_rule_context(*, run, **_) -> dict[str, Any]:
    params = run.params_json or {}
    return {
        "pipeline_name": run.pipeline_name,
        "pipeline_stage": str(params.get("wgs_stage") or params.get("stage") or "full"),
        "phase_projector": wgs_phase_for_rule,
    }


def _project_wgs_progress(*, session, run, payload, **_) -> dict[str, Any]:
    if str(run.status or "").lower() == "success":
        return {
            **payload,
            **terminal_wgs_progress(
                updated_at=(run.pipeline_finished_at or run.ended_at).isoformat()
                if run.pipeline_finished_at or run.ended_at
                else None,
                validation_scope=str((run.params_json or {}).get("validation_scope") or "") or None,
            ),
        }
    return enrich_progress(session=session, run=run, payload=payload)


def _project_wgs_dashboard_metadata(*, run, **_) -> dict[str, Any]:
    return {
        "batch_no": public_wgs_batch(run.params_json or {}),
        "display_status": str(run.status or "").lower(),
        "qc_display_status": "not_applicable",
        "qc_display_note": "WGS production status is workflow-only; QC is not shown in this interface.",
    }


def _project_wgs_sample_summary(*, run, sample, metadata, **_) -> dict[str, Any]:
    return {
        "batch_no": public_wgs_batch(run.params_json),
        "qc_status": None,
        "family_relation": metadata.get("family_relation") or metadata.get("relation"),
        "sample_type": sample.sample_type,
        "sex": sample.sex,
        "sequencing_batch": metadata.get("sequencing_batch")
        or (run.params_json or {}).get("sequencing_batch"),
    }


def _wgs_intake_status(*, session, **kwargs) -> dict[str, Any]:
    return list_wgs_t7_intake(
        session=session,
        state=kwargs.get("state"),
        view=kwargs.get("view", "all"),
        keyword=kwargs.get("keyword"),
        limit=kwargs.get("limit", 50),
        offset=kwargs.get("offset", 0),
    )


def _wgs_scanner_state(*, session, settings, **_) -> dict[str, Any]:
    return get_wgs_t7_scanner_state(
        session=session,
        root=settings.wgs_t7_fastq_root,
        enabled=settings.wgs_intake_scan_enabled,
        schedule_seconds=settings.wgs_intake_scan_interval_seconds,
        auto_dispatch_enabled=settings.wgs_auto_dispatch_enabled,
    )


ADAPTERS = {
    "generic": PipelineAdapter(adapter_id="generic"),
    "wgs": PipelineAdapter(
        adapter_id="wgs",
        sample_qc_failures=False,
        create_run=_create_wgs_run,
        submit_run=_submit_wgs_run,
        reanalyze_run=_reanalyze_wgs_run,
        project_qc=_project_wgs_qc,
        project_run_detail=_project_wgs_run_detail,
        project_samples=_project_wgs_samples,
        project_workflows=_project_wgs_workflows,
        project_rule_context=_project_wgs_rule_context,
        project_progress=_project_wgs_progress,
        project_dashboard_metadata=_project_wgs_dashboard_metadata,
        project_dashboard_lifecycles=project_wgs_lifecycles,
        project_sample_summary=_project_wgs_sample_summary,
        sync_airflow_status=sync_wgs_airflow_status,
        get_log=get_wgs_run_log,
        list_logs=list_wgs_run_logs,
        list_artifacts=list_wgs_run_artifacts,
        intake_status=_wgs_intake_status,
        scanner_state=_wgs_scanner_state,
    ),
    "gatk": PipelineAdapter(
        adapter_id="gatk",
        sample_qc_failures=False,
        create_run=_create_gatk_run,
        project_run_detail=_project_gatk_run_detail,
        project_samples=_project_gatk_samples,
        project_workflows=_project_gatk_workflows,
        project_rule_context=_project_gatk_rule_context,
        project_dashboard_metadata=_project_gatk_dashboard_metadata,
        project_sample_summary=_project_gatk_sample_summary,
        get_log=get_gatk_run_log,
        list_logs=list_gatk_run_logs,
        list_artifacts=list_gatk_run_artifacts,
    ),
}


@lru_cache(maxsize=16)
def _load_cached(path: str, deployed_pipeline_ids: tuple[str, ...]) -> PipelineRegistry:
    if path:
        return load_pipeline_registry(
            path,
            adapters=ADAPTERS,
            deployed_pipeline_ids=deployed_pipeline_ids,
        )
    return build_pipeline_registry(
        DEFAULT_REGISTRY_PAYLOAD,
        adapters=ADAPTERS,
        deployed_pipeline_ids=deployed_pipeline_ids,
    )


def get_pipeline_registry(settings) -> PipelineRegistry:
    path = str(getattr(settings, "pipeline_registry_path", "") or "").strip()
    if path and not Path(path).is_file():
        raise PipelineRegistryError(f"Pipeline registry not found: {path}")
    deployed = tuple(getattr(settings, "deployed_pipelines", ()) or ())
    return _load_cached(path, deployed)


def clear_pipeline_registry_cache() -> None:
    _load_cached.cache_clear()


def require_pipeline(
    settings,
    pipeline_id: str,
    *,
    capability: str | None = None,
) -> PipelineDefinition:
    return get_pipeline_registry(settings).require(
        pipeline_id,
        capability=capability,
    )


def workflow_projectors(settings) -> dict[str, Any]:
    registry = get_pipeline_registry(settings)
    return {
        pipeline_id: registry.require(pipeline_id).adapter.project_workflows
        for pipeline_id in registry.deployed_pipeline_ids
        if registry.require(pipeline_id).adapter.project_workflows is not None
    }


def lifecycle_projectors(settings) -> dict[str, Any]:
    registry = get_pipeline_registry(settings)
    return {
        pipeline_id: registry.require(pipeline_id).adapter.project_dashboard_lifecycles
        for pipeline_id in registry.deployed_pipeline_ids
        if registry.require(pipeline_id).adapter.project_dashboard_lifecycles is not None
    }


def deployed_adapters(settings) -> dict[str, PipelineAdapter]:
    registry = get_pipeline_registry(settings)
    return {
        pipeline_id: registry.require(pipeline_id).adapter
        for pipeline_id in registry.deployed_pipeline_ids
    }
