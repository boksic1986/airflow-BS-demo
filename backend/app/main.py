import logging
import json
import os
from pathlib import Path
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import case

from app.airflow_client import AirflowClient
from app.config import get_cors_origins, get_internal_service_token, get_settings
from app.dashboard_service import get_dashboard_overview, get_dashboard_runs
from app.db import check_database, get_sessionmaker
from app.diagnostics_service import (
    InvalidRunPathError,
    LogNotFoundError,
    MissingDagRunError,
    UnsupportedLogStreamError,
    get_run_log,
    list_run_logs,
    list_run_artifacts,
    sync_sample_statuses,
    sync_airflow_status,
)
from app.input_scanner import InputPathError
from app.gatk_submission_service import (
    GatkDraftConflict,
    GatkInputChanged,
    create_gatk_submission_preview,
)
from app.gatk_runtime_service import (
    finalize_gatk_run,
    register_gatk_stage,
    sync_gatk_stage_status,
)
from app.gatk_workspace_service import build_gatk_workspace
from app.intake_retention_service import prune_scanner_history
from app.operator_resources_service import list_failures_resource, list_samples_resource
from app.progress_service import get_run_progress
from app.pipeline_registry import (
    PipelineCapabilityUnavailable,
    PipelineNotAvailable,
    PipelineNotRegistered,
    PipelineRegistryError,
)
from app.pipeline_registry_service import (
    attention_projectors,
    clear_pipeline_registry_cache,
    deployed_adapters,
    get_pipeline_registry,
    lifecycle_projectors,
    qc_status_projectors,
    require_pipeline,
    workflow_projectors,
)
from app.rule_event_service import get_snakemake_rule_events_page, record_snakemake_event
from app.run_service import (
    get_run_detail,
    list_runs,
)
from app.run_resources_service import get_run_resource_summary
from app.system_resources import get_system_resources
from app.auth_service import (
    AuthenticatedUser,
    audit,
    authenticate_session,
    create_session,
    create_user,
    list_users,
    require_role,
    revoke_session,
)
from app.wgs_platform_service import WgsPreparedArtifactPending, action_wgs_run, acquire_obs_transfer_slot, create_wgs_platform_run, release_obs_transfer_slot, revalidate_wgs_run, submit_wgs_run, sync_prepared_samples, sync_prepare_handoff_decisions, sync_sampleinfo_preview
from app.wgs_release_catalog import load_wgs_release_catalog
from app.models import AnalysisRun, KubernetesWorkload, RuleState, RunValidationIssue, Sample, TransferFileState, TransferJob, UserAccount, WgsExecutionDispatch, WgsStageExecution
from app.wgs_timing_service import serialize_rule_states
from app.wgs_workspace_service import build_wgs_workspace
from app.workflow_phases import gatk_phase_definitions, phase_for_rule, phase_order, wgs_phase_definitions
from app.wgs_runtime_adapter import build_stage_request, container_workdir_to_host, write_stage_request
from app.wgs_observer import (
    SUPPORTED_RUNTIME_SYNC_STAGES,
    sync_runtime_stage_artifacts,
    upsert_stage_state,
)
from app.wgs_observer_lifecycle import activate_observer, request_observer_drain
from app.wgs_t7_intake import get_wgs_t7_scanner_state, list_wgs_t7_intake
from app.wgs_auto_dispatch import dispatch_ready_wgs_intake
from app.wgs_step4_service import request_step4_repair
from app.wgs_step7_service import authorize_step7_runtime, request_step7_cleanup
from app.wgs_stage_catalog import load_wgs_stage_contract
from app.wgs_stage_execution_service import (
    WgsStagePredecessorPending,
    register_stage_execution,
    validate_step3_dryrun_fencing,
)
from app.wgs_project_catalog import load_wgs_projects, public_project_catalog
from app.wgs_submission_service import (
    approve_wgs_config,
    approve_wgs_execution,
    complete_draft,
    create_and_submit_run,
    create_draft,
    get_draft,
    mark_submission_dag_failed,
    submission_state,
    submit_draft,
)
from app.wgs_execution_dispatch_service import (
    ExecutionDispatchConflict,
    change_execution_choice,
    commit_execution_choice,
    mark_execution_running,
    mark_execution_needs_recovery,
    mark_execution_terminal,
)
from app.wgs_lifecycle_service import (
    LifecycleConflict,
    update_wgs_lifecycle_status,
)
from app.platform_resources_service import get_platform_resources
from sqlalchemy import func, or_, select


logger = logging.getLogger(__name__)
app = FastAPI(title="airflow-demo backend")
INTAKE_SCANNER_DAG_ID = "bio_intake_scan"
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_COOKIE = "wgs_session"
STEP4_MASTER_NOT_SUCCESSFUL = "Step4 requires a successful Master Job"


@app.middleware("http")
async def enforce_platform_auth(request: Request, call_next):
    if request.url.path in {"/api/health", "/api/health/db", "/api/auth/login"}:
        return await call_next(request)
    try:
        settings = get_settings()
    except RuntimeError:
        # Older isolated unit tests intentionally construct the app without
        # runtime environment. Production Compose always supplies DATABASE_URL
        # and AUTH_REQUIRED=true, so this branch cannot disable deployed auth.
        if os.getenv("AUTH_REQUIRED", "").strip().lower() in {"1", "true", "yes", "on"}:
            return Response(content='{"detail":{"code":"PLATFORM_MISCONFIGURED","message":"Authentication storage unavailable."}}', status_code=503, media_type="application/json")
        request.state.user = AuthenticatedUser(0, "test-legacy", "admin", "")
        return await call_next(request)
    if not bool(getattr(settings, "auth_required", False)):
        request.state.user = AuthenticatedUser(0, "legacy", "admin", "")
        return await call_next(request)
    internal_token = request.headers.get("X-Airflow-Demo-Token")
    expected_internal = str(getattr(settings, "internal_service_token", "") or "")
    if expected_internal and internal_token and secrets.compare_digest(internal_token, expected_internal):
        request.state.user = AuthenticatedUser(0, "internal-service", "admin", "")
        return await call_next(request)
    with get_sessionmaker()() as session:
        user = authenticate_session(session=session, raw_token=request.cookies.get(SESSION_COOKIE))
    if user is None:
        return Response(content='{"detail":{"code":"AUTH_REQUIRED","message":"Login required."}}', status_code=401, media_type="application/json")
    request.state.user = user
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        supplied = request.headers.get("X-CSRF-Token", "")
        if not supplied or not secrets.compare_digest(supplied, user.csrf_token):
            return Response(content='{"detail":{"code":"CSRF_REQUIRED","message":"Valid CSRF token required."}}', status_code=403, media_type="application/json")
    return await call_next(request)


def current_user(request: Request) -> AuthenticatedUser:
    return getattr(request.state, "user", AuthenticatedUser(0, "legacy", "admin", ""))


def operator_user(user: AuthenticatedUser = Depends(current_user)) -> AuthenticatedUser:
    try:
        require_role(user, "operator")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": str(exc)}) from exc
    return user


def admin_user(user: AuthenticatedUser = Depends(current_user)) -> AuthenticatedUser:
    try:
        require_role(user, "admin")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": str(exc)}) from exc
    return user


def _is_known_step4_master_completion_race(
    *, request_root: str, analysis_id: str, attempt: int
) -> bool:
    marker = (
        Path(request_root)
        / analysis_id
        / f"attempt-{attempt}"
        / "step4_publish.status.json"
    )
    if not marker.is_file() or marker.is_symlink():
        return False
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
        marker_attempt = int(value.get("attempt", 0))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return False
    return (
        value.get("schema_version") == "wgs-runtime.stage-status.v1"
        and value.get("analysis_id") == analysis_id
        and marker_attempt == attempt
        and value.get("stage") == "step4_publish"
        and value.get("status") == "failed"
        and STEP4_MASTER_NOT_SUCCESSFUL in str(value.get("message") or "")
    )


def _is_successful_runtime_stage(
    *, request_root: str, analysis_id: str, attempt: int, stage: str
) -> bool:
    marker = Path(request_root) / analysis_id / f"attempt-{attempt}" / f"{stage}.status.json"
    if not marker.is_file() or marker.is_symlink():
        return False
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
        marker_attempt = int(value.get("attempt", 0))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return False
    return (
        value.get("schema_version") == "wgs-runtime.stage-status.v1"
        and value.get("analysis_id") == analysis_id
        and marker_attempt == attempt
        and value.get("stage") == stage
        and value.get("status") in {"success", "complete", "succeeded"}
    )


def require_internal_service_token(
    x_airflow_demo_token: str | None = Header(default=None, alias="X-Airflow-Demo-Token"),
) -> None:
    expected = get_internal_service_token()
    if not expected:
        return
    if not x_airflow_demo_token or not secrets.compare_digest(x_airflow_demo_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INTERNAL_SERVICE_AUTH_REQUIRED", "message": "Valid internal service token required."},
        )


class InputScanRequest(BaseModel):
    pipeline: str
    rawdata_root: str
    max_samples: int = Field(default=200, ge=1, le=1000)


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline: str
    project_name: str
    execution_mode: str = Field(default="cce", max_length=32)
    batch_no: str | None = Field(default=None, min_length=1, max_length=128)
    fq_path: str | None = None
    options: dict[str, object] = Field(default_factory=dict)
    submission_draft_id: str | None = Field(default=None, max_length=128)
    submission_preview_hash: str | None = Field(
        default=None, pattern="^[0-9a-f]{64}$"
    )

    @model_validator(mode="after")
    def validate_pipeline_inputs(self):
        self.pipeline = self.pipeline.strip()
        if not self.pipeline:
            raise ValueError("pipeline is required.")
        return self


class PipelineConfigValidationRequest(BaseModel):
    pipeline: str
    runtime_profile_id: str
    config_template_hash: str
    snakemake_config_yaml: str = Field(max_length=65536)
    options: dict[str, object] = Field(default_factory=dict)


class IntakeScanRequest(BaseModel):
    pipelines: list[str] = Field(default_factory=lambda: ["wgs"])
    bootstrap: bool = False
    max_samples: int = Field(default=200, ge=1, le=1000)


class IntakeRetentionRequest(BaseModel):
    dag_id: str = INTAKE_SCANNER_DAG_ID
    current_dag_run_id: str | None = None
    dry_run: bool = False


class WgsRuntimeStageRequest(BaseModel):
    attempt: int = Field(ge=1)
    adapter: str
    command: str | None = None
    maintenance_action_id: str | None = Field(default=None, max_length=128)
    force_new_generation: bool = False


class GatkRuntimeStageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attempt: int = Field(ge=1)
    adapter: str = Field(pattern="^gatk-runtime-200$")


class WgsObserverLifecycleRequest(BaseModel):
    attempt: int = Field(ge=1)


class WgsDagTerminalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attempt: int = Field(ge=1)
    status: str = Field(pattern="^failed$")
    failed_task_ids: list[str] = Field(default_factory=list, max_length=64)


class WgsExecutionChoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    desired_mode: str = Field(pattern="^(cce|local|sge)$")
    desired_target: str = Field(pattern="^(cce|node-97|node-96|sge-default)$")
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class WgsLifecycleStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attempt: int = Field(ge=1)
    status: str = Field(pattern="^(not_started|pending|running|success|failed)$")
    expected_revision: int = Field(ge=1)
    message: str | None = Field(default=None, max_length=500)


class WgsSubmissionDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1, max_length=128)
    platform: str = Field(min_length=1, max_length=64)
    sequencing_batch: str = Field(min_length=1, max_length=64)
    analysis_batch: str = Field(min_length=1, max_length=128)
    fastq_root_id: str = Field(min_length=1, max_length=128)
    use_reference: bool = False


class GatkSubmissionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_project_dir: str = Field(min_length=1, max_length=2048)


class WgsCatalogRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1, max_length=128)
    platform: str = Field(min_length=1, max_length=64)
    batch: str = Field(pattern="^[0-9]{8}[A-Z]$")
    fastq_root_id: str = Field(min_length=1, max_length=128)
    validation_scope: str | None = Field(
        default=None, pattern="^(step1_only|step3_dryrun|node97_full)$"
    )


class WgsConfigApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use_reference: str = Field(pattern="^(all|ref|no)$")
    resource_set: str = Field(default="default", pattern="^default$")


class WgsSubmissionDraftResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prepared_fq_path: str = Field(min_length=1)
    samples: list[dict[str, object]] = Field(default_factory=list)
    families: list[dict[str, object]] = Field(default_factory=list)
    resolved_config: dict[str, object] = Field(default_factory=dict)
    source_fingerprint: str = Field(pattern="^[0-9a-f]{64}$")


class WgsStep7CleanupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_confirmation: str = Field(min_length=1, max_length=128)
    retry_failed: bool = False
    expected_action_id: str | None = Field(default=None, min_length=1, max_length=128)


class ReanalysisRequest(BaseModel):
    mode: str
    rule: str | None = None
    sample_id: str | None = None
    stage: str | None = None
    reason: str | None = None


class SnakemakeEventRequest(BaseModel):
    analysis_id: str = Field(min_length=1)
    event: str = Field(min_length=1)
    rule: str = Field(min_length=1)
    sample_id: str | None = None
    wildcards: dict[str, object] = Field(default_factory=dict)
    snakemake_jobid: str | None = None
    qsub_jobid: str | None = None
    status: str = Field(min_length=1)
    stdout_path: str | None = None
    stderr_path: str | None = None
    message: str | None = None
    return_code: int | None = None
    resources: dict[str, object] | None = None
    timestamp: datetime | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=512)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=512)
    role: str = Field(pattern="^(viewer|operator|admin)$")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/wgs/release")
def current_wgs_release() -> dict[str, object]:
    release = load_wgs_release_catalog(
        Path(get_settings().wgs_release_catalog_path)
    ).release
    return {
        "release_id": release.release_id,
        "version": release.version,
        "source_commit": release.source_commit,
        "profile_id": release.profile_id,
        "profile_revision": release.profile_revision,
        "profile_sha256": release.profile_sha256,
        "cce_pipeline_version": release.cce_pipeline_version,
        "execution_enabled": _wgs_platform_execution_enabled(),
        "runtime_adapter_enabled": _wgs_runtime_adapter_enabled(),
        "submission_preview_enabled": _wgs_submission_preview_enabled(),
    }


@app.post("/api/auth/login")
def login(request: LoginRequest, response: Response) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            user, raw_token = create_session(
                session=session,
                username=request.username,
                password=request.password,
                ttl_hours=int(getattr(get_settings(), "session_ttl_hours", 8)),
            )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": str(exc)}) from exc
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        httponly=True,
        secure=bool(getattr(get_settings(), "session_cookie_secure", True)),
        samesite="strict",
        max_age=int(getattr(get_settings(), "session_ttl_hours", 8)) * 3600,
        path="/",
    )
    return {"username": user.username, "role": user.role, "csrf_token": user.csrf_token}


@app.post("/api/auth/logout")
def logout(response: Response, raw_token: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict[str, str]:
    with get_sessionmaker()() as session:
        revoke_session(session=session, raw_token=raw_token)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "ok"}


@app.get("/api/auth/me")
def me(user: AuthenticatedUser = Depends(current_user)) -> dict[str, str]:
    return {"username": user.username, "role": user.role, "csrf_token": user.csrf_token}


@app.get("/api/users")
def users(user: AuthenticatedUser = Depends(admin_user)) -> dict[str, object]:
    with get_sessionmaker()() as session:
        return {"items": list_users(session=session)}


@app.post("/api/users", status_code=201)
def add_user(request: UserCreateRequest, user: AuthenticatedUser = Depends(admin_user)) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            account = create_user(session=session, username=request.username, password=request.password, role=request.role)
            audit(session=session, username=user.username, action="user.create", payload={"target": account.username, "role": account.role})
            return {"id": account.id, "username": account.username, "role": account.role, "enabled": account.enabled}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(exc)}) from exc


@app.get("/api/platform/capabilities")
def platform_capabilities() -> dict[str, object]:
    settings = get_settings()
    registry = get_pipeline_registry(settings)
    return {
        "environment": getattr(settings, "platform_environment", "Demo"),
        **registry.public_payload(),
        "airflow_url": getattr(settings, "public_airflow_url", "") or None,
    }


@app.get("/api/pipelines/gatk/release")
def gatk_release() -> dict[str, object]:
    settings = get_settings()
    definition = require_pipeline(settings, "gatk", capability="submit")
    return {
        "pipeline": definition.pipeline_id,
        "profile_id": settings.gatk_runtime_profile_id,
        "profile_revision": settings.gatk_runtime_profile_revision,
        "execution_target": "cce",
        "execution_enabled": bool(settings.gatk_execution_enabled),
    }


def _pipeline_http_exception(exc: PipelineRegistryError) -> HTTPException:
    status_code = (
        status.HTTP_404_NOT_FOUND
        if isinstance(exc, PipelineNotRegistered)
        else status.HTTP_409_CONFLICT
    )
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


def get_airflow_client() -> AirflowClient:
    settings = get_settings()
    return AirflowClient(
        base_url=settings.airflow_base_url,
        username=settings.airflow_api_username,
        password=settings.airflow_api_password,
    )


@app.post("/api/input/scan")
def scan_input(request: InputScanRequest) -> dict[str, object]:
    try:
        settings = get_settings()
        definition = require_pipeline(settings, request.pipeline, capability="input_scan")
        if definition.adapter.scan_inputs is None:
            raise PipelineCapabilityUnavailable(
                f"Pipeline {request.pipeline!r} has no input scan adapter."
            )
        return definition.adapter.scan_inputs(
            settings=settings,
            rawdata_root=request.rawdata_root,
            max_samples=request.max_samples,
        )
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    except InputPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT_PATH", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": str(exc)},
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("intake Airflow submit failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "AIRFLOW_TRIGGER_FAILED", "message": str(exc)},
        ) from exc

@app.get("/api/input/roots")
def input_roots(pipeline: str) -> dict[str, object]:
    try:
        settings = get_settings()
        definition = require_pipeline(settings, pipeline, capability="input_scan")
        if definition.adapter.input_roots is None:
            raise PipelineCapabilityUnavailable(
                f"Pipeline {pipeline!r} has no input-root adapter."
            )
        return {"pipeline": pipeline, "roots": definition.adapter.input_roots(settings=settings)}
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc


@app.get("/api/intake/config")
def intake_config() -> dict[str, object]:
    return get_pipeline_registry(get_settings()).public_payload()


@app.get("/api/intake/scanner-state")
def intake_scanner_state() -> dict[str, object]:
    settings = get_settings()
    registry = get_pipeline_registry(settings)
    states: dict[str, object] = {}
    with get_sessionmaker()() as session:
        for pipeline_id in registry.deployed_pipeline_ids:
            definition = registry.require(pipeline_id)
            if "intake" not in definition.capabilities:
                continue
            if definition.adapter.scanner_state is None:
                states[pipeline_id] = {
                    "available": False,
                    "message": "Scanner state is not provided by this pipeline adapter.",
                }
                continue
            states[pipeline_id] = definition.adapter.scanner_state(
                session=session,
                settings=settings,
            )
    if len(states) == 1:
        return next(iter(states.values()))
    return {"pipelines": states}


@app.post("/api/intake/retention", dependencies=[Depends(require_internal_service_token)])
def intake_retention(request: IntakeRetentionRequest) -> dict[str, object]:
    try:
        return prune_scanner_history(
            airflow_client=get_airflow_client(),
            dag_id=request.dag_id,
            cutoff=datetime.now(timezone.utc) - timedelta(days=30),
            current_dag_run_id=request.current_dag_run_id,
            dry_run=request.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RETENTION_SCOPE", "message": str(exc)},
        ) from exc


@app.get("/api/pipeline-config/template")
def pipeline_config_template(
    pipeline: str,
    target: str | None = None,
    run_mode: str | None = None,
    profile_id: str | None = None,
) -> dict[str, object]:
    try:
        definition = require_pipeline(get_settings(), pipeline, capability="profile")
        if definition.adapter.config_template is None:
            raise PipelineCapabilityUnavailable(
                f"Pipeline {pipeline!r} has no profile template adapter."
            )
        return definition.adapter.config_template(
            settings=get_settings(),
            pipeline=pipeline,
            profile_id=profile_id,
            options={"target": target, "run_mode": run_mode},
        )
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc


@app.post("/api/pipeline-config/validate")
def pipeline_config_validate(request: PipelineConfigValidationRequest) -> dict[str, object]:
    try:
        definition = require_pipeline(get_settings(), request.pipeline, capability="profile")
        if definition.adapter.validate_config is None:
            raise PipelineCapabilityUnavailable(
                f"Pipeline {request.pipeline!r} has no profile validation adapter."
            )
        return definition.adapter.validate_config(
            settings=get_settings(),
            pipeline=request.pipeline,
            profile_id=request.runtime_profile_id,
            template_hash=request.config_template_hash,
            config_yaml=request.snakemake_config_yaml,
            options=request.options,
        )
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc


@app.post("/api/runs", status_code=status.HTTP_201_CREATED)
def create_run(request: CreateRunRequest, user: AuthenticatedUser = Depends(operator_user)) -> dict[str, object]:
    settings = get_settings()
    session_factory = get_sessionmaker()
    try:
        definition = require_pipeline(settings, request.pipeline, capability="submit")
        if not definition.submit_enabled or definition.adapter.create_run is None:
            raise PipelineCapabilityUnavailable(
                f"Pipeline {request.pipeline!r} has no enabled submit adapter."
            )
        with session_factory() as session:
            payload = definition.adapter.create_run(
                session=session,
                settings=settings,
                request=request,
                user=user,
                airflow_client=get_airflow_client(),
            )
            audit(
                session=session,
                username=user.username,
                action="run.create",
                analysis_id=str(payload["analysis_id"]),
                payload={"pipeline": request.pipeline, "execution_mode": request.execution_mode},
            )
            return payload
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    except InputPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT_PATH", "message": str(exc)},
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT_PATH", "message": str(exc)},
        ) from exc
    except GatkInputChanged as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except GatkDraftConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": str(exc)},
        ) from exc


@app.post("/api/pipelines/gatk/submission-preview", status_code=status.HTTP_201_CREATED)
def gatk_submission_preview(
    request: GatkSubmissionPreviewRequest,
    user: AuthenticatedUser = Depends(operator_user),
) -> dict[str, object]:
    try:
        require_pipeline(get_settings(), "gatk", capability="submit")
        with get_sessionmaker()() as session:
            return create_gatk_submission_preview(
                session=session,
                settings=get_settings(),
                source_project_dir=request.source_project_dir,
                owner_username=user.username,
            )
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "GATK_INPUT_INVALID", "message": str(exc)},
        ) from exc


@app.get("/api/wgs/projects")
def wgs_projects() -> dict[str, object]:
    settings = get_settings()
    return public_project_catalog(load_wgs_projects(settings.wgs_project_catalog_path))


@app.get("/api/platform/resources")
def platform_resources() -> dict[str, object]:
    settings = get_settings()
    with get_sessionmaker()() as session:
        return get_platform_resources(
            session=session,
            heavy_slot_limit=int(settings.wgs_heavy_slot_limit),
            heavy_slot_mode=str(settings.wgs_heavy_slot_mode),
            evidence_root=str(settings.wgs_evidence_root or ""),
        )


@app.post("/api/wgs/runs", status_code=status.HTTP_201_CREATED)
def create_catalog_wgs_run(
    request: WgsCatalogRunRequest,
    user: AuthenticatedUser = Depends(operator_user),
) -> dict[str, object]:
    if not _wgs_platform_execution_enabled() or not _wgs_runtime_adapter_enabled():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "WGS_EXECUTION_DISABLED", "message": "WGS execution remains disabled."},
        )
    if request.validation_scope is not None:
        try:
            require_role(user, "admin")
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": str(exc)},
            ) from exc
        gate_enabled = {
            "step1_only": _wgs_step1_canary_enabled,
            "step3_dryrun": _wgs_step3_dryrun_canary_enabled,
            "node97_full": _wgs_node97_full_canary_enabled,
        }[request.validation_scope]()
        if not gate_enabled:
            gate_code = {
                "step1_only": "WGS_STEP1_CANARY_DISABLED",
                "step3_dryrun": "WGS_STEP3_DRYRUN_CANARY_DISABLED",
                "node97_full": "WGS_NODE97_FULL_CANARY_DISABLED",
            }[request.validation_scope]
            gate_message = {
                "step1_only": "The Step1-only validation gate is disabled.",
                "step3_dryrun": "The Step3 dry-run validation gate is disabled.",
                "node97_full": "The node97 full-run validation gate is disabled.",
            }[request.validation_scope]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": gate_code,
                    "message": gate_message,
                },
            )
        if not _wgs_contract_v2_enabled():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "WGS_CONTRACT_V2_DISABLED",
                    "message": "The validation canary requires contract v2.",
                },
            )
    try:
        with get_sessionmaker()() as session:
            payload = create_and_submit_run(
                session=session,
                settings=get_settings(),
                airflow_client=get_airflow_client(),
                username=user.username,
                **request.model_dump(),
            )
            audit(
                session=session,
                username=user.username,
                action="wgs.run.submit",
                analysis_id=str(payload["analysis_id"]),
                payload={"project_id": request.project_id, "batch": request.batch},
            )
            return payload
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail={"code": "WGS_RUN_INVALID", "message": str(exc)}) from exc


@app.post("/api/runs/{analysis_id}/actions/approve-wgs-config")
def approve_wgs_run_config(
    analysis_id: str,
    request: WgsConfigApprovalRequest,
    user: AuthenticatedUser = Depends(operator_user),
) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            return approve_wgs_config(
                session=session,
                analysis_id=analysis_id,
                requested_by=user.username,
                **request.model_dump(),
            )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "WGS_CONFIG_NOT_READY", "message": str(exc)}) from exc


@app.post("/api/runs/{analysis_id}/actions/start-wgs-execution")
def start_wgs_run_execution(
    analysis_id: str,
    user: AuthenticatedUser = Depends(operator_user),
) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            return approve_wgs_execution(
                session=session,
                analysis_id=analysis_id,
                requested_by=user.username,
            )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "WGS_EXECUTION_NOT_READY", "message": str(exc)}) from exc


@app.post("/api/wgs/runs/{analysis_id}/execution-choice")
def update_wgs_execution_choice(
    analysis_id: str,
    request: WgsExecutionChoiceRequest,
    user: AuthenticatedUser = Depends(operator_user),
) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            return change_execution_choice(
                session=session,
                settings=get_settings(),
                analysis_id=analysis_id,
                requested_by=user.username,
                **request.model_dump(),
            )
    except ExecutionDispatchConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WGS_EXECUTION_CHOICE_INVALID", "message": str(exc)},
        ) from exc


def _update_wgs_lifecycle(
    *,
    analysis_id: str,
    kind: str,
    request: WgsLifecycleStatusRequest,
    user: AuthenticatedUser,
) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(
                select(AnalysisRun).where(
                    AnalysisRun.analysis_id == analysis_id,
                    AnalysisRun.pipeline_name == "wgs",
                )
            )
            if run is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
                )
            return update_wgs_lifecycle_status(
                session=session,
                run=run,
                kind=kind,
                updated_by=user.username,
                **request.model_dump(),
            )
    except LifecycleConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WGS_LIFECYCLE_STATUS_INVALID", "message": str(exc)},
        ) from exc


@app.patch("/api/wgs/runs/{analysis_id}/lifecycle/raw-fastq-backup")
def update_raw_fastq_backup_status(
    analysis_id: str,
    request: WgsLifecycleStatusRequest,
    user: AuthenticatedUser = Depends(admin_user),
) -> dict[str, object]:
    return _update_wgs_lifecycle(
        analysis_id=analysis_id,
        kind="raw_fastq_backup",
        request=request,
        user=user,
    )


@app.patch("/api/wgs/runs/{analysis_id}/lifecycle/downstream-release")
def update_downstream_release_status(
    analysis_id: str,
    request: WgsLifecycleStatusRequest,
    user: AuthenticatedUser = Depends(admin_user),
) -> dict[str, object]:
    return _update_wgs_lifecycle(
        analysis_id=analysis_id,
        kind="downstream_release",
        request=request,
        user=user,
    )


@app.post("/api/wgs/submission-drafts", status_code=status.HTTP_202_ACCEPTED)
def create_wgs_submission_draft(
    request: WgsSubmissionDraftRequest,
    user: AuthenticatedUser = Depends(operator_user),
) -> dict[str, object]:
    if not _wgs_submission_preview_enabled():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "WGS_DRAFT_PREVIEW_DISABLED",
                "message": "WGS has not published the read-only FASTQ and pending-sample preview contract; no draft was created.",
            },
        )
    try:
        with get_sessionmaker()() as session:
            payload = create_draft(
                session=session,
                settings=get_settings(),
                owner_username=user.username,
                **request.model_dump(),
            )
            audit(session=session, username=user.username, action="wgs.draft.create", payload={"draft_id": payload["draft_id"]})
            return payload
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail={"code": "WGS_DRAFT_INVALID", "message": str(exc)}) from exc


@app.get("/api/wgs/submission-drafts/{draft_id}")
def read_wgs_submission_draft(
    draft_id: str,
    user: AuthenticatedUser = Depends(operator_user),
) -> dict[str, object]:
    with get_sessionmaker()() as session:
        payload = get_draft(session=session, draft_id=draft_id, username=user.username, is_admin=user.role == "admin")
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "WGS_DRAFT_NOT_FOUND", "message": "WGS submission draft was not found"})
    return payload


@app.post("/api/internal/wgs/submission-drafts/{draft_id}/complete", dependencies=[Depends(require_internal_service_token)])
def complete_wgs_submission_draft(draft_id: str, request: WgsSubmissionDraftResultRequest) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            payload = complete_draft(session=session, settings=get_settings(), draft_id=draft_id, **request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "WGS_DRAFT_RESULT_INVALID", "message": str(exc)}) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "WGS_DRAFT_NOT_FOUND", "message": "WGS submission draft was not found"})
    return payload


@app.post("/api/wgs/submission-drafts/{draft_id}/submit")
def submit_wgs_submission_draft(
    draft_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: AuthenticatedUser = Depends(operator_user),
) -> dict[str, object]:
    if not _wgs_platform_execution_enabled() or not _wgs_runtime_adapter_enabled():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "WGS_EXECUTION_DISABLED", "message": "WGS execution remains disabled; the draft preview is read-only."},
        )
    try:
        with get_sessionmaker()() as session:
            payload = submit_draft(
                session=session,
                settings=get_settings(),
                airflow_client=get_airflow_client(),
                draft_id=draft_id,
                username=user.username,
                idempotency_key=str(idempotency_key or ""),
            )
            if payload is not None:
                audit(session=session, username=user.username, action="wgs.draft.submit", analysis_id=str(payload["analysis_id"]), payload={"draft_id": draft_id})
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail={"code": "WGS_DRAFT_SUBMIT_INVALID", "message": str(exc)}) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "WGS_DRAFT_NOT_FOUND", "message": "WGS submission draft was not found"})
    return payload


@app.get("/api/runs")
def runs_list(
    pipeline: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = None,
    sort: str = Query(default="created_desc", pattern="^(created_desc|duration_desc|status)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    deployed_pipelines = _active_deployed_pipelines()
    if pipeline and pipeline not in {"all", "deployed"}:
        _guard_pipeline_deployed(pipeline)
    with get_sessionmaker()() as session:
        return list_runs(
            session=session,
            pipeline="deployed" if pipeline in {None, "all", "deployed"} else pipeline,
            deployed_pipelines=deployed_pipelines,
            status=status_filter,
            keyword=keyword,
            sort=sort,
            limit=limit,
            offset=offset,
            workflow_projectors=workflow_projectors(get_settings()),
            lifecycle_projectors=lifecycle_projectors(get_settings()),
            qc_status_projectors=qc_status_projectors(get_settings()),
        )


@app.get("/api/samples")
def samples_list(
    pipeline: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    qc_status: str | None = None,
    keyword: str | None = None,
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    deployed_pipelines = _active_deployed_pipelines()
    if pipeline and pipeline not in {"all", "deployed"}:
        _guard_pipeline_deployed(pipeline)
    with get_sessionmaker()() as session:
        return list_samples_resource(
            session=session,
            pipeline="deployed" if pipeline in {None, "all", "deployed"} else pipeline,
            deployed_pipelines=deployed_pipelines,
            status=status_filter,
            qc_status=qc_status,
            keyword=keyword,
            limit=limit,
            offset=offset,
            pipeline_adapters=deployed_adapters(get_settings()),
        )


@app.get("/api/failures")
def failures_list(
    pipeline: str = Query(default="all"),
    kind: str = Query(default="all", pattern="^(all|workflow|qc)$"),
    layer: str | None = Query(default=None, pattern="^(airflow|runner|pipeline_rule|qc|unknown)$"),
    period: str = Query(default="7d", pattern="^(24h|7d|30d)$"),
    keyword: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    deployed_pipelines = _active_deployed_pipelines()
    if pipeline not in {"all", "deployed"}:
        _guard_pipeline_deployed(pipeline)
    with get_sessionmaker()() as session:
        return list_failures_resource(
            session=session,
            pipeline="deployed" if pipeline in {"all", "deployed"} else pipeline,
            kind=kind,
            layer=layer,
            period=period,
            keyword=keyword,
            limit=limit,
            offset=offset,
            deployed_pipelines=deployed_pipelines,
            pipeline_adapters=deployed_adapters(get_settings()),
        )


@app.get("/api/dashboard/overview")
def dashboard_overview(
    pipeline: str = Query(default="all"),
    period: str = Query(default="7d", pattern="^(24h|7d|30d)$"),
) -> dict[str, object]:
    deployed_pipelines = _active_deployed_pipelines()
    if pipeline not in {"all", "deployed"}:
        _guard_pipeline_deployed(pipeline)
    with get_sessionmaker()() as session:
        return get_dashboard_overview(
            session=session,
            pipeline=pipeline,
            period=period,
            deployed_pipelines=deployed_pipelines,
            attention_projectors=attention_projectors(get_settings()),
        )


@app.get("/api/dashboard/runs")
def dashboard_runs(
    pipeline: str = Query(default="all"),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    deployed_pipelines = _active_deployed_pipelines()
    if pipeline not in {"all", "deployed"}:
        _guard_pipeline_deployed(pipeline)
    with get_sessionmaker()() as session:
        return get_dashboard_runs(
            session=session,
            airflow_client=get_airflow_client(),
            pipeline=pipeline,
            deployed_pipelines=deployed_pipelines,
            status=status_filter,
            keyword=keyword,
            limit=limit,
            offset=offset,
            pipeline_adapters=deployed_adapters(get_settings()),
        )


@app.post("/api/runs/{analysis_id}/actions/submit")
def submit_run(analysis_id: str, user: AuthenticatedUser = Depends(operator_user)) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            detail = get_run_detail(session=session, analysis_id=analysis_id)
            if detail is None:
                payload = None
            else:
                definition = require_pipeline(
                    get_settings(), str(detail.get("pipeline") or ""), capability="submit"
                )
                if not definition.submit_enabled or definition.adapter.submit_run is None:
                    raise PipelineCapabilityUnavailable(
                        f"Pipeline {definition.pipeline_id!r} has no enabled submit adapter."
                    )
                payload = definition.adapter.submit_run(
                    session=session,
                    settings=get_settings(),
                    airflow_client=get_airflow_client(),
                    analysis_id=analysis_id,
                    user=user,
                )
            if payload is not None:
                audit(session=session, username=user.username, action="run.submit", analysis_id=analysis_id)
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": str(exc)},
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("airflow dag trigger failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "AIRFLOW_TRIGGER_FAILED", "message": str(exc)},
        ) from exc

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.post("/api/intake/scan-and-submit", dependencies=[Depends(require_internal_service_token)])
def intake_scan_and_submit(request: IntakeScanRequest) -> dict[str, object]:
    try:
        settings = get_settings()
        for pipeline_id in request.pipelines:
            definition = require_pipeline(settings, pipeline_id, capability="intake")
            raise PipelineCapabilityUnavailable(
                f"Pipeline {definition.pipeline_id!r} does not expose generic scan-and-submit; use its registered intake adapter."
            )
        return {"items": []}
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc


@app.post(
    "/api/internal/wgs/intake/dispatch-ready",
    dependencies=[Depends(require_internal_service_token)],
)
def dispatch_ready_wgs_batches() -> dict[str, object]:
    if not _wgs_platform_execution_enabled() or not _wgs_runtime_adapter_enabled():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "WGS_EXECUTION_DISABLED",
                "message": "WGS execution/runtime gates must be enabled for automatic dispatch.",
            },
        )
    try:
        with get_sessionmaker()() as session:
            return dispatch_ready_wgs_intake(
                session=session,
                settings=get_settings(),
                airflow_client=get_airflow_client(),
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "WGS_AUTO_DISPATCH_BLOCKED", "message": str(exc)},
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("automatic WGS Airflow dispatch failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "AIRFLOW_TRIGGER_FAILED", "message": str(exc)},
        ) from exc


@app.post("/api/intake/scan-preview")
def intake_scan_preview(request: IntakeScanRequest) -> dict[str, object]:
    try:
        settings = get_settings()
        for pipeline_id in request.pipelines:
            definition = require_pipeline(settings, pipeline_id, capability="intake")
            raise PipelineCapabilityUnavailable(
                f"Pipeline {definition.pipeline_id!r} does not expose generic intake preview; use its registered intake adapter."
            )
        return {"items": []}
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc


@app.get("/api/intake/status")
def intake_status(
    pipeline: str | None = Query(default=None),
    state_filter: str | None = Query(
        default=None,
        alias="state",
        pattern="^(bootstrap|observed|ready|submitted|error|disabled|waiting_barcode_stat|no_new_wgs|needs_review|bootstrap_ignored)$",
    ),
    lifecycle: str = Query(default="active", pattern="^(active|archived|all)$"),
    view_filter: str = Query(default="all", alias="view", pattern="^(attention|pending|history|all)$"),
    keyword: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    deployed_pipelines = _active_deployed_pipelines()
    aggregate_scope = pipeline in {None, "all", "deployed"}
    with get_sessionmaker()() as session:
        registry = get_pipeline_registry(get_settings())
        selected = (
            tuple(
                pipeline_id
                for pipeline_id in deployed_pipelines
                if "intake" in registry.require(pipeline_id).capabilities
            )
            if aggregate_scope
            else (str(pipeline),)
        )
        payloads = []
        for pipeline_id in selected:
            try:
                definition = registry.require(pipeline_id, capability="intake")
                if definition.adapter.intake_status is None:
                    continue
                payloads.append(
                    definition.adapter.intake_status(
                        session=session,
                        settings=get_settings(),
                        state=state_filter,
                        lifecycle=lifecycle,
                        view=view_filter,
                        keyword=keyword,
                        limit=limit,
                        offset=offset,
                    )
                )
            except PipelineRegistryError as exc:
                raise _pipeline_http_exception(exc) from exc
        if len(payloads) == 1:
            return payloads[0]
        items = [item for payload in payloads for item in payload.get("items", [])]
        return {
            "items": items[:limit],
            "total": sum(int(item.get("total", 0)) for item in payloads),
            "limit": limit,
            "offset": offset,
        }


@app.get("/api/workflows")
def workflows() -> dict[str, object]:
    registry = get_pipeline_registry(get_settings())
    return {
        "items": [
            registry.require(pipeline_id).public_payload()
            for pipeline_id in registry.deployed_pipeline_ids
        ]
    }


@app.get("/api/system/resources")
def system_resources() -> dict[str, object]:
    return get_system_resources()


@app.post("/api/runs/{analysis_id}/actions/reanalyze")
def reanalyze_run(
    analysis_id: str,
    request: ReanalysisRequest,
    user: AuthenticatedUser = Depends(operator_user),
) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            detail = get_run_detail(session=session, analysis_id=analysis_id)
            if detail is None:
                payload = None
            else:
                capability = "resume" if request.mode == "resume" else "rerun"
                definition = require_pipeline(
                    get_settings(), str(detail.get("pipeline") or ""), capability=capability
                )
                if definition.adapter.reanalyze_run is None:
                    raise PipelineCapabilityUnavailable(
                        f"Pipeline {definition.pipeline_id!r} has no reanalysis adapter."
                    )
                payload = definition.adapter.reanalyze_run(
                    session=session,
                    settings=get_settings(),
                    airflow_client=get_airflow_client(),
                    analysis_id=analysis_id,
                    request=request,
                    user=user,
                )
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": str(exc)},
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("airflow dag trigger failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "AIRFLOW_TRIGGER_FAILED", "message": str(exc)},
        ) from exc

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.post("/api/runs/{analysis_id}/actions/sync-airflow")
def sync_run_airflow(analysis_id: str) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(
                select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
            )
            adapter = (
                require_pipeline(get_settings(), run.pipeline_name).adapter
                if run is not None
                else None
            )
            handler = (
                adapter.sync_airflow_status
                if adapter is not None and adapter.sync_airflow_status is not None
                else sync_airflow_status
            )
            payload = handler(
                session=session,
                airflow_client=get_airflow_client(),
                analysis_id=analysis_id,
                settings=get_settings(),
            )
    except MissingDagRunError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MISSING_DAG_RUN", "message": str(exc)},
        ) from exc
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    except InvalidRunPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RUN_PATH", "message": str(exc)},
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("airflow dag run sync failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "AIRFLOW_SYNC_FAILED", "message": str(exc)},
        ) from exc

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.get("/api/runs/{analysis_id}")
def run_detail(analysis_id: str) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            payload = get_run_detail(session=session, analysis_id=analysis_id)
            run = session.scalar(
                select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
            )
            if run is not None:
                definition = require_pipeline(get_settings(), run.pipeline_name)
                if definition.adapter.project_run_detail is not None:
                    payload.update(
                        definition.adapter.project_run_detail(
                            session=session,
                            settings=get_settings(),
                            run=run,
                        )
                        or {}
                    )
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.get("/api/runs/{analysis_id}/samples")
def run_samples(analysis_id: str) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(
                select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
            )
            if run is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
                )
            definition = require_pipeline(get_settings(), run.pipeline_name)
            if definition.adapter.project_samples is None:
                raise PipelineCapabilityUnavailable(
                    f"Pipeline {definition.pipeline_id!r} has no sample projection adapter."
                )
            return definition.adapter.project_samples(
                session=session,
                settings=get_settings(),
                run=run,
            )
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc


@app.get("/api/runs/{analysis_id}/workspace")
def run_workspace(analysis_id: str) -> dict[str, object]:
    # Reuse the public run-detail projection while keeping the browser's first
    # paint to one HTTP resource. All progress in this endpoint is DB-backed.
    detail = run_detail(analysis_id)
    with get_sessionmaker()() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
            )
        settings = get_settings()
        require_pipeline(settings, run.pipeline_name, capability="rules")
        if run.pipeline_name == "gatk":
            return build_gatk_workspace(
                session=session,
                run=run,
                run_payload=detail,
            )
        return build_wgs_workspace(
            session=session,
            run=run,
            run_payload=detail,
            heavy_slot_limit=int(getattr(settings, "wgs_heavy_slot_limit", 25)),
            heavy_slot_mode=str(getattr(settings, "wgs_heavy_slot_mode", "monitor-only")),
            evidence_root=str(getattr(settings, "wgs_evidence_root", "") or ""),
            settings=settings,
        )


@app.get("/api/runs/{analysis_id}/families")
def run_families(analysis_id: str) -> dict[str, object]:
    with get_sessionmaker()() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs"))
        if run is None:
            raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"})
        samples = session.scalars(select(Sample).where(Sample.analysis_id == analysis_id).order_by(Sample.family_id, Sample.sample_id)).all()
    families: dict[str, list[str]] = {}
    for sample in samples:
        families.setdefault(sample.family_id or "unassigned", []).append(sample.sample_id)
    return {"items": [{"family_id": family_id, "sample_ids": sample_ids, "sample_count": len(sample_ids)} for family_id, sample_ids in families.items()]}


@app.get("/api/runs/{analysis_id}/pods")
def run_pods(analysis_id: str) -> dict[str, object]:
    with get_sessionmaker()() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        if run is None:
            raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"})
        definition = require_pipeline(get_settings(), run.pipeline_name)
        if "cce" not in definition.execution_targets:
            raise PipelineCapabilityUnavailable(
                f"Pipeline {run.pipeline_name!r} does not expose Kubernetes workloads."
            )
        query = select(KubernetesWorkload).where(
            KubernetesWorkload.analysis_id == analysis_id,
            KubernetesWorkload.attempt == run.attempt,
        )
        if run.pipeline_name == "wgs":
            query = query.where(KubernetesWorkload.event_id.like("step3:%"))
        items = session.scalars(
            query.order_by(KubernetesWorkload.attempt, KubernetesWorkload.job_name)
        ).all()
    return {"items": [{"attempt": item.attempt, "pod_hash": item.pod_hash, "job_name": item.job_name, "phase": item.phase, "reason": item.reason, "exit_code": item.exit_code, "image_id": item.image_id, "node_name": item.node_name, "message": item.message, "resources": item.resources_json, "observed_at": item.observed_at.isoformat() if item.observed_at else None, "updated_at": item.updated_at.isoformat()} for item in items]}


@app.get("/api/runs/{analysis_id}/transfers")
def run_transfers(analysis_id: str) -> dict[str, object]:
    from app.wgs_transfer_projection import serialize_transfer_job

    with get_sessionmaker()() as session:
        items = session.scalars(select(TransferJob).where(TransferJob.analysis_id == analysis_id).order_by(TransferJob.id)).all()
    return {"items": [serialize_transfer_job(item) for item in items]}


@app.get("/api/transfers/{transfer_id}/files")
def transfer_files(transfer_id: str, status_filter: str | None = Query(default=None, alias="status"), limit: int = Query(default=50, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> dict[str, object]:
    from app.wgs_transfer_projection import transfer_file_order_by

    with get_sessionmaker()() as session:
        transfer = session.scalar(select(TransferJob).where(TransferJob.transfer_id == transfer_id))
        if transfer is None:
            raise HTTPException(status_code=404, detail={"code": "TRANSFER_NOT_FOUND", "message": "Transfer not found"})
        query = select(TransferFileState).where(TransferFileState.transfer_id == transfer_id)
        if status_filter:
            query = query.where(TransferFileState.status == status_filter)
        total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
        rows = session.scalars(
            query.order_by(*transfer_file_order_by()).limit(limit).offset(offset)
        ).all()
        return {
            "items": [
                {
                    "file_key": row.file_key,
                    "display_name": row.display_name,
                    "status": row.status,
                    "bytes_total": row.bytes_total,
                    "bytes_transferred": row.bytes_transferred,
                    "progress_percent": round(row.bytes_transferred * 100 / row.bytes_total, 1) if row.bytes_total else 0.0,
                    "speed_bps": row.speed_bps,
                    "checksum_status": row.checksum_status,
                    "error_message": row.error_message,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "ended_at": row.ended_at.isoformat() if row.ended_at else None,
                }
                for row in rows
            ],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }


@app.get("/api/runs/{analysis_id}/rules")
def run_rules(
    analysis_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    rule: str | None = None,
    sample_id: str | None = None,
    family_id: str | None = None,
    phase: str | None = None,
    sort: str = Query(default="execution_order", pattern="^(execution_order|active_first)$"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    with get_sessionmaker()() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        if run is None:
            raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"})
        require_pipeline(get_settings(), run.pipeline_name, capability="rules")
        query = select(RuleState).where(RuleState.analysis_id == analysis_id)
        if status_filter:
            query = query.where(RuleState.status == status_filter)
        if rule:
            query = query.where(RuleState.rule_name == rule)
        if sample_id:
            query = query.where(RuleState.sample_id == sample_id)
        if family_id:
            query = query.where(RuleState.family_id == family_id)
        if phase:
            query = query.where(RuleState.phase == phase)
        total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
        ordering = []
        if sort == "active_first":
            ordering.append(
                case(
                    (RuleState.status.in_(("running", "started")), 0),
                    (RuleState.status.in_(("accepted", "submitted", "queued", "pending")), 1),
                    else_=2,
                )
            )
        page = list(session.scalars(
            query.order_by(
                *ordering,
                RuleState.attempt,
                RuleState.sequence.is_(None),
                RuleState.sequence,
                RuleState.sample_id,
                RuleState.rule_name,
                RuleState.rule_instance_id,
            ).limit(limit).offset(offset)
        ).all())
        return {
            "items": serialize_rule_states(session=session, run=run, rows=page, settings=get_settings()),
            "phases": (
                gatk_phase_definitions()
                if run.pipeline_name == "gatk"
                else wgs_phase_definitions()
            ),
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }


@app.get("/api/runs/{analysis_id}/validation-issues")
def validation_issues(analysis_id: str) -> dict[str, object]:
    with get_sessionmaker()() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs"))
        if run is None:
            raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"})
        rows = session.scalars(select(RunValidationIssue).where(RunValidationIssue.analysis_id == analysis_id).order_by(RunValidationIssue.id)).all()
        return {"items": [{"id": row.id, "attempt": row.attempt, "code": row.code, "severity": row.severity, "scope_type": row.scope_type, "sample_id": row.sample_id, "family_id": row.family_id, "file_path": row.file_path, "message": row.message, "status": row.status, "created_at": row.created_at.isoformat(), "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None} for row in rows]}


@app.post("/api/runs/{analysis_id}/actions/revalidate")
def revalidate_run(analysis_id: str, user: AuthenticatedUser = Depends(operator_user)) -> dict[str, object]:
    with get_sessionmaker()() as session:
        payload = revalidate_wgs_run(session=session, settings=get_settings(), analysis_id=analysis_id)
        if payload is not None:
            audit(session=session, username=user.username, action="run.revalidate", analysis_id=analysis_id)
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"})
    return payload


@app.post("/api/internal/wgs/runs/{analysis_id}/stages/{stage_name}", dependencies=[Depends(require_internal_service_token)])
def internal_wgs_runtime_stage(analysis_id: str, stage_name: str, request: WgsRuntimeStageRequest) -> dict[str, object]:
    local_stage = stage_name in {"local_analysis", "finalize_local_run"}
    expected_adapter = "wgs-runtime-node97" if local_stage else "wgs-runtime-200"
    if request.adapter != expected_adapter or not _wgs_runtime_adapter_enabled():
        raise HTTPException(status_code=409, detail={"code": "WGS_RUNTIME_DISABLED", "message": "WGS runtime adapter is disabled."})
    if stage_name == "step7_cleanup" and not _wgs_platform_execution_enabled():
        raise HTTPException(status_code=409, detail={"code": "WGS_RUNTIME_DISABLED", "message": "WGS execution is disabled; Step7 was not registered."})
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs"))
            if run is None or run.attempt != request.attempt:
                raise ValueError("unknown active WGS attempt")
            dispatch = session.scalar(
                select(WgsExecutionDispatch).where(
                    WgsExecutionDispatch.analysis_id == analysis_id
                )
            )
            if local_stage and (
                dispatch is None
                or dispatch.dispatch_state not in {"committed", "running"}
                or dispatch.committed_attempt != request.attempt
                or dispatch.desired_target != "node-97"
            ):
                raise ValueError("node97 local stage does not match the committed execution target")
            step7_action = None
            if stage_name == "step7_cleanup":
                step7_action = authorize_step7_runtime(
                    session=session,
                    run=run,
                    action_id=str(request.maintenance_action_id or ""),
                )
            params = dict(run.params_json or {})
            release_id = str(params["pipeline_release_id"])
            catalog = load_wgs_release_catalog(
                Path(get_settings().wgs_release_catalog_path)
            )
            try:
                release = catalog.by_id(release_id)
            except ValueError as exc:
                raise ValueError(
                    "release_unavailable: run WGS release is not cataloged"
                ) from exc
            if stage_name in {"prepare", "prepare_sampleinfo", "prepare_analysis"}:
                if str(params.get("wgs_source_commit") or "") != release.source_commit:
                    raise ValueError("release_unavailable: run WGS commit does not match its catalog release")
            if stage_name in {"acquire_input_transfer_slot", "acquire_result_transfer_slot"}:
                transfer_kind = "input" if stage_name == "acquire_input_transfer_slot" else "result"
                transfer_id = f"{analysis_id}-a{request.attempt}-{transfer_kind}"
                slot = acquire_obs_transfer_slot(
                    session=session,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    transfer_id=transfer_id,
                    transfer_kind=transfer_kind,
                )
                if slot is None:
                    return {"analysis_id": analysis_id, "attempt": request.attempt, "stage": stage_name, "status": "waiting", "acquired": False}
                run.current_stage = stage_name
                session.commit()
                return {"analysis_id": analysis_id, "attempt": request.attempt, "stage": stage_name, "status": "acquired", "acquired": True, "slot": slot}
            if stage_name in {"release_input_transfer_slot", "release_result_transfer_slot", "release_leases"}:
                transfer_kind = None
                if stage_name == "release_input_transfer_slot":
                    transfer_kind = "input"
                elif stage_name == "release_result_transfer_slot":
                    transfer_kind = "result"
                transfer_id = f"{analysis_id}-a{request.attempt}-{transfer_kind}" if transfer_kind else None
                release_result = release_obs_transfer_slot(
                    session=session,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    transfer_id=transfer_id,
                    transfer_kind=transfer_kind,
                )
                if release_result["retained"]:
                    mark_execution_needs_recovery(
                        session=session,
                        analysis_id=analysis_id,
                        attempt=request.attempt,
                        reason=(
                            f"{stage_name} retained OBS lease: "
                            f"{release_result['reason']}"
                        ),
                    )
                    run.current_stage = stage_name
                    session.commit()
                return {
                    "analysis_id": analysis_id,
                    "attempt": request.attempt,
                    "stage": stage_name,
                    "status": (
                        "retained" if release_result["retained"] else "released"
                    ),
                    **release_result,
                }
            if stage_name == "finalize_run":
                if not _is_successful_runtime_stage(
                    request_root=get_settings().wgs_runtime_request_root,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    stage="step6_materialize",
                ):
                    raise ValueError("Step6 materialization is not complete")
                already_successful = str(run.status or "").lower() == "success"
                finished_at = (
                    (run.pipeline_finished_at or run.ended_at)
                    if already_successful
                    else None
                ) or datetime.now(timezone.utc)
                if finished_at.tzinfo is None:
                    finished_at = finished_at.replace(tzinfo=timezone.utc)
                run.status = "success"
                run.current_stage = "finalize_run"
                run.pipeline_finished_at = finished_at
                run.ended_at = finished_at
                run.progress_percent = 100
                run.progress_updated_at = finished_at
                run.error_summary = None
                sync_sample_statuses(
                    session=session,
                    analysis_id=analysis_id,
                    run_status="success",
                )
                upsert_stage_state(
                    session,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    stage_code="final",
                    stage_status="success",
                    updated_at=finished_at,
                    progress_available=True,
                    progress_percent=100,
                    completed_units=1,
                    total_units=1,
                    unit="workflow",
                    progress_source="airflow-finalize",
                )
                mark_execution_terminal(
                    session=session, analysis_id=analysis_id, attempt=request.attempt
                )
                session.commit()
                return {"analysis_id": analysis_id, "attempt": request.attempt, "stage": stage_name, "status": "success"}
            if stage_name == "finalize_local_run":
                if not _is_successful_runtime_stage(
                    request_root=get_settings().wgs_runtime_request_root,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    stage="local_analysis",
                ):
                    raise ValueError("node97 local analysis has no successful terminal receipt")
                finished_at = run.pipeline_finished_at or datetime.now(timezone.utc)
                if finished_at.tzinfo is None:
                    finished_at = finished_at.replace(tzinfo=timezone.utc)
                run.status = "success"
                run.current_stage = "finalize_local_run"
                run.pipeline_finished_at = finished_at
                run.ended_at = finished_at
                run.progress_percent = 100
                run.progress_updated_at = finished_at
                run.error_summary = None
                sync_sample_statuses(
                    session=session,
                    analysis_id=analysis_id,
                    run_status="success",
                )
                upsert_stage_state(
                    session,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    stage_code="final",
                    stage_status="success",
                    updated_at=finished_at,
                    progress_available=True,
                    progress_percent=100,
                    completed_units=1,
                    total_units=1,
                    unit="workflow",
                    progress_source="node97-local-finalize",
                )
                mark_execution_terminal(
                    session=session, analysis_id=analysis_id, attempt=request.attempt
                )
                session.commit()
                return {
                    "analysis_id": analysis_id,
                    "attempt": request.attempt,
                    "stage": stage_name,
                    "status": "success",
                }
            if stage_name == "finalize_step1_canary":
                if not _wgs_step1_canary_enabled():
                    raise ValueError("Step1 canary is disabled")
                if params.get("validation_scope") != "step1_only":
                    raise ValueError("run is not a Step1-only canary")
                step1 = session.scalar(
                    select(WgsStageExecution)
                    .where(
                        WgsStageExecution.analysis_id == analysis_id,
                        WgsStageExecution.attempt == request.attempt,
                        WgsStageExecution.stage_code == "step1_upload",
                    )
                    .order_by(WgsStageExecution.generation.desc())
                    .limit(1)
                )
                if step1 is None or step1.status != "success" or not step1.receipt_hash:
                    raise ValueError("Step1 upload has no exact successful receipt")
                finished_at = run.pipeline_finished_at or datetime.now(timezone.utc)
                if finished_at.tzinfo is None:
                    finished_at = finished_at.replace(tzinfo=timezone.utc)
                params.update(
                    {
                        "validation_result": "step1_upload_complete",
                        "validation_completed_at": finished_at.isoformat(),
                        "step1_receipt_hash": step1.receipt_hash,
                    }
                )
                run.params_json = params
                run.status = "success"
                run.current_stage = "finalize_step1_canary"
                run.pipeline_finished_at = finished_at
                run.ended_at = finished_at
                run.progress_percent = 100
                run.progress_updated_at = finished_at
                run.error_summary = None
                for sample in session.scalars(
                    select(Sample).where(Sample.analysis_id == analysis_id)
                ).all():
                    sample.status = "skipped"
                upsert_stage_state(
                    session,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    stage_code="step1_canary_complete",
                    stage_status="success",
                    updated_at=finished_at,
                    progress_available=True,
                    progress_percent=100,
                    completed_units=1,
                    total_units=1,
                    unit="validation",
                    progress_source="step1-transfer-receipt",
                )
                mark_execution_terminal(
                    session=session, analysis_id=analysis_id, attempt=request.attempt
                )
                session.commit()
                return {
                    "analysis_id": analysis_id,
                    "attempt": request.attempt,
                    "stage": stage_name,
                    "status": "success",
                    "validation_result": "step1_upload_complete",
                }
            if stage_name == "finalize_step3_dryrun":
                if not _wgs_step3_dryrun_canary_enabled():
                    raise ValueError("Step3 dry-run canary is disabled")
                if params.get("validation_scope") != "step3_dryrun":
                    raise ValueError("run is not a Step3 dry-run canary")
                step3 = session.scalar(
                    select(WgsStageExecution)
                    .where(
                        WgsStageExecution.analysis_id == analysis_id,
                        WgsStageExecution.attempt == request.attempt,
                        WgsStageExecution.stage_code == "step3_monitor",
                    )
                    .order_by(WgsStageExecution.generation.desc())
                    .limit(1)
                )
                evidence = dict(step3.terminal_payload_json or {}) if step3 else {}
                master = evidence.get("master") if isinstance(evidence.get("master"), dict) else {}
                if (
                    step3 is None
                    or step3.status != "success"
                    or not step3.receipt_hash
                    or evidence.get("master_job") in {None, ""}
                    or evidence.get("namespace") in {None, ""}
                    or master.get("execution_mode") != "dry_run"
                    or master.get("master_state") != "SUCCEEDED"
                    or master.get("master_uid") in {None, ""}
                    or master.get("master_resource_version") in {None, ""}
                ):
                    raise ValueError(
                        "Step3 dry-run has no exact successful Master identity evidence"
                    )
                validate_step3_dryrun_fencing(
                    session=session,
                    run=run,
                    step3=step3,
                    runtime_run_root=get_settings().wgs_runtime_run_root,
                )
                finished_at = run.pipeline_finished_at or datetime.now(timezone.utc)
                if finished_at.tzinfo is None:
                    finished_at = finished_at.replace(tzinfo=timezone.utc)
                params.update(
                    {
                        "validation_result": "step3_dryrun_complete",
                        "validation_completed_at": finished_at.isoformat(),
                        "step3_receipt_hash": step3.receipt_hash,
                        "step3_master_uid": master["master_uid"],
                        "step3_master_resource_version": master[
                            "master_resource_version"
                        ],
                    }
                )
                run.params_json = params
                run.status = "success"
                run.current_stage = "finalize_step3_dryrun"
                run.pipeline_finished_at = finished_at
                run.ended_at = finished_at
                run.progress_percent = 100
                run.progress_updated_at = finished_at
                run.error_summary = None
                for sample in session.scalars(
                    select(Sample).where(Sample.analysis_id == analysis_id)
                ).all():
                    sample.status = "skipped"
                upsert_stage_state(
                    session,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    stage_code="step3_dryrun_complete",
                    stage_status="success",
                    updated_at=finished_at,
                    progress_available=True,
                    progress_percent=100,
                    completed_units=1,
                    total_units=1,
                    unit="validation",
                    progress_source="step3-master-terminal-evidence",
                )
                mark_execution_terminal(
                    session=session, analysis_id=analysis_id, attempt=request.attempt
                )
                session.commit()
                return {
                    "analysis_id": analysis_id,
                    "attempt": request.attempt,
                    "stage": stage_name,
                    "status": "success",
                    "validation_result": "step3_dryrun_complete",
                }
            command_prefix = (
                "wgs-local-runtime" if stage_name == "local_analysis" else "wgs-runtime"
            )
            expected_command = f"{command_prefix} {analysis_id} {request.attempt} {stage_name}"
            if request.command != expected_command:
                raise ValueError("runtime command does not match the registered stage")
            settings = get_settings()
            if params.get("fastq_root"):
                fq_node200 = str(params["fastq_root"])
            else:
                fq_host = container_workdir_to_host(
                    str(params["fq_path"]),
                    container_root=settings.wgs_intake_container_root,
                    host_root=settings.wgs_intake_host_root,
                )
                fq_node200 = container_workdir_to_host(
                    fq_host,
                    container_root=settings.wgs_intake_host_root,
                    host_root=settings.wgs_intake_node200_root,
                )
            payload = build_stage_request(
                analysis_id=analysis_id, attempt=request.attempt, stage=stage_name,
                pipeline_release_id=release_id,
                wgs_version=str(params["wgs_version"]),
                wgs_source_commit=str(params["wgs_source_commit"]),
                control_runtime_root=settings.wgs_runtime_node200_root,
                analysis_project_root=getattr(
                    settings,
                    "wgs_analysis_project_node200_root",
                    settings.wgs_results_host_root,
                ),
                project_name=str(params["project_name"]),
                batch_no=str(params["batch_no"]),
                fq_path=fq_node200,
                platform=str(params.get("platform") or "") or None,
                sequencing_batch=str(params.get("sequencing_batch") or "") or None,
                fastq_root=str(params.get("fastq_root") or "") or None,
                use_reference=str(params.get("use_reference") or "") or None,
                analysis_batch=str(params.get("analysis_batch") or "") or None,
                validation_scope=str(params.get("validation_scope") or "") or None,
                maintenance_action_id=request.maintenance_action_id,
            )
            if step7_action is not None:
                snapshot = dict(step7_action.target_snapshot_json or {})
                snapshot.update(
                    {
                        "control_workdir": payload["control_workdir"],
                        "analysis_project_root": payload["analysis_project_root"],
                        "expected_batch_root": payload["expected_batch_root"],
                        "cce_bundle": f"{payload['expected_batch_root']}/cce",
                    }
                )
                step7_action.target_snapshot_json = snapshot
                session.flush()
                payload["step7_target_snapshot"] = snapshot
                payload["step7_generation"] = step7_action.generation
            contract_v2 = bool(getattr(settings, "wgs_contract_v2_enabled", False)) and int(
                params.get("orchestration_contract_version") or 1
            ) == 2
            if contract_v2:
                contract = load_wgs_stage_contract(
                    Path(settings.wgs_stage_contract_path)
                )
                payload["heavy_io_contract"] = {
                    "limit": contract.heavy_io.limit,
                    "mode": contract.heavy_io.mode,
                    "unit": "work_pod",
                }
                if (
                    request.force_new_generation
                    and stage_name in SUPPORTED_RUNTIME_SYNC_STAGES
                ):
                    sync_runtime_stage_artifacts(
                        session_factory=get_sessionmaker(),
                        request_root=Path(settings.wgs_runtime_request_root),
                        transfer_spool_root=Path(settings.wgs_transfer_spool_root),
                        analysis_id=analysis_id,
                        attempt=request.attempt,
                        stage=stage_name,
                    )
                if stage_name == "step3_monitor":
                    sync_runtime_stage_artifacts(
                        session_factory=get_sessionmaker(),
                        request_root=Path(settings.wgs_runtime_request_root),
                        transfer_spool_root=Path(settings.wgs_transfer_spool_root),
                        analysis_id=analysis_id,
                        attempt=request.attempt,
                        stage="step2_master",
                    )
                execution = register_stage_execution(
                    session=session,
                    run=run,
                    contract=contract,
                    stage_code=stage_name,
                    request_payload=payload,
                    force_new_generation=request.force_new_generation,
                )
                payload.update(
                    {
                        "orchestration_contract_version": 2,
                        "execution_id": execution.execution_id,
                        "generation": execution.generation,
                        "request_hash": execution.request_hash,
                        "predecessor_execution_id": execution.predecessor_execution_id,
                        "predecessor_generation": execution.predecessor_generation,
                        "predecessor_receipt_hash": execution.predecessor_receipt_hash,
                    }
                )
            path = write_stage_request(
                settings.wgs_runtime_request_root,
                payload,
                shared_gid=getattr(settings, "wgs_runtime_shared_gid", None),
            )
            upsert_stage_state(
                session,
                analysis_id=analysis_id,
                attempt=request.attempt,
                stage_code=stage_name,
                stage_status="accepted",
                updated_at=datetime.now(timezone.utc),
                progress_source="wgs-runtime.request.v4",
            )
            if stage_name in {"prepare", "prepare_analysis"}:
                binding_root = Path(settings.wgs_binding_root)
                binding_root.mkdir(parents=True, exist_ok=True)
                binding_path = binding_root / f"{analysis_id}-attempt-{request.attempt}.json"
                binding_payload = {
                    "schema_version": "3",
                    "analysis_id": analysis_id,
                    "attempt": request.attempt,
                    "pipeline_release_id": release_id,
                    "run_id": f"{analysis_id}-a{request.attempt}",
                    "evidence_path": f"{analysis_id}/attempt-{request.attempt}",
                }
                partial = binding_path.with_suffix(".json.partial")
                partial.write_text(json.dumps(binding_payload, sort_keys=True) + "\n", encoding="utf-8")
                os.replace(partial, binding_path)
            if not contract_v2 and stage_name == "step3_monitor" and run.status == "failed":
                run.status = "running"
                run.ended_at = None
                run.pipeline_finished_at = None
                run.error_summary = None
                audit(
                    session=session,
                    username="airflow-internal",
                    action="run.step3_monitor_recovered",
                    analysis_id=analysis_id,
                    payload={"attempt": request.attempt},
                )
            if (
                not contract_v2
                and stage_name == "step4_publish"
                and run.status == "failed"
                and _is_known_step4_master_completion_race(
                    request_root=settings.wgs_runtime_request_root,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                )
            ):
                run.status = "publishing"
                run.ended_at = None
                run.pipeline_finished_at = None
                run.error_summary = None
                audit(
                    session=session,
                    username="airflow-internal",
                    action="run.step4_publish_recovered",
                    analysis_id=analysis_id,
                    payload={"attempt": request.attempt},
                )
            if (
                not contract_v2
                and stage_name == "step5_download"
                and run.status == "failed"
                and run.current_stage == "step4_publish"
            ):
                if _is_successful_runtime_stage(
                    request_root=settings.wgs_runtime_request_root,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    stage="step4_publish",
                ):
                    run.status = "downloading"
                    run.ended_at = None
                    run.pipeline_finished_at = None
                    run.error_summary = None
                    audit(
                        session=session,
                        username="airflow-internal",
                        action="run.step5_download_recovered",
                        analysis_id=analysis_id,
                        payload={"attempt": request.attempt},
                    )
            run.current_stage = stage_name
            if stage_name in {"step1_upload", "local_analysis"}:
                mark_execution_running(
                    session=session, analysis_id=analysis_id, attempt=request.attempt
                )
            session.commit()
            return {
                "analysis_id": analysis_id,
                "attempt": request.attempt,
                "stage": stage_name,
                "status": "registered",
                "request_path": str(path),
                "execution_id": execution.execution_id if contract_v2 else None,
                "generation": execution.generation if contract_v2 else None,
            }
    except WgsStagePredecessorPending as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "WGS_STAGE_PREDECESSOR_PENDING",
                "message": str(exc),
            },
        ) from exc
    except (OSError, ValueError, RuntimeError) as exc:
        message = str(exc)
        if message.startswith("release_unavailable:"):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "WGS_RELEASE_UNAVAILABLE",
                    "message": message,
                },
            ) from exc
        raise HTTPException(status_code=400, detail={"code": "WGS_RUNTIME_STAGE_FAILED", "message": message}) from exc


@app.post(
    "/api/internal/gatk/runs/{analysis_id}/stages/{stage_name}",
    dependencies=[Depends(require_internal_service_token)],
)
def internal_gatk_runtime_stage(
    analysis_id: str, stage_name: str, request: GatkRuntimeStageRequest
) -> dict[str, object]:
    settings = get_settings()
    if not settings.gatk_execution_enabled:
        raise HTTPException(
            status_code=409,
            detail={"code": "GATK_EXECUTION_DISABLED", "message": "GATK execution is disabled."},
        )
    try:
        with get_sessionmaker()() as session:
            if stage_name in {"acquire_input_transfer_slot", "acquire_result_transfer_slot"}:
                transfer_kind = "input" if stage_name == "acquire_input_transfer_slot" else "result"
                transfer_id = f"{analysis_id}-a{request.attempt}-{transfer_kind}"
                slot = acquire_obs_transfer_slot(
                    session=session,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    transfer_id=transfer_id,
                    transfer_kind=transfer_kind,
                )
                return {
                    "analysis_id": analysis_id,
                    "attempt": request.attempt,
                    "stage": stage_name,
                    "status": "acquired" if slot else "waiting",
                    "acquired": bool(slot),
                    "slot": slot,
                }
            if stage_name in {"release_input_transfer_slot", "release_result_transfer_slot", "release_leases"}:
                transfer_kind = None
                if stage_name == "release_input_transfer_slot":
                    transfer_kind = "input"
                elif stage_name == "release_result_transfer_slot":
                    transfer_kind = "result"
                result = release_obs_transfer_slot(
                    session=session,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    transfer_id=(
                        f"{analysis_id}-a{request.attempt}-{transfer_kind}"
                        if transfer_kind
                        else None
                    ),
                    transfer_kind=transfer_kind,
                )
                return {"analysis_id": analysis_id, "attempt": request.attempt, **result}
            if stage_name == "finalize_run":
                return finalize_gatk_run(
                    session=session,
                    settings=settings,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                )
            return register_gatk_stage(
                session=session,
                settings=settings,
                analysis_id=analysis_id,
                attempt=request.attempt,
                stage=stage_name,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "GATK_RUNTIME_INVALID", "message": str(exc)},
        ) from exc


@app.get(
    "/api/internal/gatk/runs/{analysis_id}/stage-status",
    dependencies=[Depends(require_internal_service_token)],
)
def internal_gatk_stage_status(
    analysis_id: str,
    attempt: int = Query(ge=1),
    stage: str = Query(min_length=1),
) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            return sync_gatk_stage_status(
                session=session,
                settings=get_settings(),
                analysis_id=analysis_id,
                attempt=attempt,
                stage=stage,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "GATK_EVIDENCE_INVALID", "message": str(exc)},
        ) from exc


@app.post(
    "/api/internal/wgs/runs/{analysis_id}/observer/activate",
    dependencies=[Depends(require_internal_service_token)],
)
def internal_wgs_observer_activate(
    analysis_id: str, request: WgsObserverLifecycleRequest
) -> dict[str, object]:
    try:
        with get_sessionmaker().begin() as session:
            state = activate_observer(
                session, analysis_id=analysis_id, attempt=request.attempt
            )
            return {
                "analysis_id": analysis_id,
                "attempt": request.attempt,
                "lifecycle_status": state.lifecycle_status,
                "monitoring_health": state.monitoring_health,
            }
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "WGS_OBSERVER_ACTIVATION_FAILED", "message": str(exc)},
        ) from exc


@app.post(
    "/api/internal/wgs/runs/{analysis_id}/observer/deactivate",
    dependencies=[Depends(require_internal_service_token)],
)
def internal_wgs_observer_deactivate(
    analysis_id: str, request: WgsObserverLifecycleRequest
) -> dict[str, object]:
    try:
        with get_sessionmaker().begin() as session:
            state = request_observer_drain(
                session, analysis_id=analysis_id, attempt=request.attempt
            )
            return {
                "analysis_id": analysis_id,
                "attempt": request.attempt,
                "lifecycle_status": state.lifecycle_status if state else "stopped",
                "monitoring_health": state.monitoring_health if state else "healthy",
            }
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "WGS_OBSERVER_DEACTIVATION_FAILED", "message": str(exc)},
        ) from exc


@app.get("/api/internal/wgs/runs/{analysis_id}/stage-status", dependencies=[Depends(require_internal_service_token)])
def internal_wgs_runtime_stage_status(analysis_id: str, attempt: int = Query(ge=1), stage: str = Query(min_length=1)) -> dict[str, object]:
    if not _wgs_runtime_adapter_enabled():
        raise HTTPException(status_code=409, detail={"code": "WGS_RUNTIME_DISABLED", "message": "WGS runtime adapter is disabled."})
    settings = get_settings()
    sync_runtime_stage_artifacts(
        session_factory=get_sessionmaker(),
        request_root=Path(settings.wgs_runtime_request_root),
        transfer_spool_root=Path(settings.wgs_transfer_spool_root),
        analysis_id=analysis_id,
        attempt=attempt,
        stage=stage,
    )
    marker = Path(settings.wgs_runtime_request_root) / analysis_id / f"attempt-{attempt}" / f"{stage}.status.json"
    payload = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else {}
    if payload and (
        payload.get("schema_version") != "wgs-runtime.stage-status.v1"
        or payload.get("analysis_id") != analysis_id
        or int(payload.get("attempt", 0)) != attempt
        or payload.get("stage") != stage
    ):
        raise HTTPException(status_code=500, detail={"code": "WGS_STAGE_STATUS_INVALID", "message": "stage status identity mismatch"})
    status_value = str(payload.get("status") or "pending")
    artifact_pending = False
    if stage in {"prepare", "prepare_sampleinfo", "prepare_analysis"} and status_value in {"success", "complete", "succeeded"}:
        with get_sessionmaker()() as session:
            run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.attempt == attempt))
            if run is not None:
                params = dict(run.params_json or {})
                try:
                    if stage == "prepare_sampleinfo":
                        sync_sampleinfo_preview(session=session, settings=settings, run=run)
                        params["submission_phase"] = "config_review"
                    else:
                        sync_prepared_samples(session=session, settings=settings, run=run)
                        if stage == "prepare_analysis":
                            params["submission_phase"] = "execution_review"
                    handoff_receipt = payload.get("prepare_handoff_receipt")
                    if isinstance(handoff_receipt, dict):
                        sync_prepare_handoff_decisions(
                            session=session,
                            run=run,
                            receipt=handoff_receipt,
                        )
                except WgsPreparedArtifactPending:
                    artifact_pending = True
                else:
                    run.params_json = params
                    session.commit()
    return {
        "analysis_id": analysis_id,
        "attempt": attempt,
        "stage": stage,
        "ready": status_value in {"success", "complete", "succeeded"} and not artifact_pending,
        "artifact_pending": artifact_pending,
        "failed": status_value == "failed",
        "status": status_value,
        "updated_at": payload.get("updated_at"),
        "retry_no": payload.get("retry_no"),
        "message": payload.get("message", ""),
        "master": payload.get("master"),
    }


@app.get(
    "/api/internal/wgs/runs/{analysis_id}/submission-state",
    dependencies=[Depends(require_internal_service_token)],
)
def internal_wgs_submission_state(
    analysis_id: str,
    attempt: int = Query(ge=1),
) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            return submission_state(
                session=session,
                analysis_id=analysis_id,
                attempt=attempt,
            )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "WGS_RUN_NOT_FOUND", "message": str(exc)}) from exc


@app.post(
    "/api/internal/wgs/runs/{analysis_id}/dag-terminal",
    dependencies=[Depends(require_internal_service_token)],
)
def internal_wgs_dag_terminal(
    analysis_id: str,
    request: WgsDagTerminalRequest,
) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            return mark_submission_dag_failed(
                session=session,
                analysis_id=analysis_id,
                attempt=request.attempt,
                failed_task_ids=request.failed_task_ids,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "WGS_DAG_TERMINAL_REJECTED", "message": str(exc)},
        ) from exc


@app.post(
    "/api/internal/wgs/runs/{analysis_id}/execution-commit",
    dependencies=[Depends(require_internal_service_token)],
)
def internal_wgs_execution_commit(
    analysis_id: str,
    request: WgsObserverLifecycleRequest,
) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            return commit_execution_choice(
                session=session,
                settings=get_settings(),
                analysis_id=analysis_id,
                attempt=request.attempt,
            )
    except ExecutionDispatchConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WGS_RUN_NOT_FOUND", "message": str(exc)},
        ) from exc


@app.post("/api/runs/{analysis_id}/actions/resume")
def resume_run(analysis_id: str, user: AuthenticatedUser = Depends(operator_user)) -> dict[str, object]:
    return _wgs_action(analysis_id, "resume", user)


@app.post("/api/runs/{analysis_id}/actions/rerun_failed")
def rerun_failed(analysis_id: str, user: AuthenticatedUser = Depends(operator_user)) -> dict[str, object]:
    return _wgs_action(analysis_id, "rerun_failed", user)


@app.post(
    "/api/runs/{analysis_id}/actions/repair-step4",
    status_code=status.HTTP_202_ACCEPTED,
)
def repair_step4(
    analysis_id: str,
    user: AuthenticatedUser = Depends(operator_user),
) -> dict[str, object]:
    if not _wgs_platform_execution_enabled() or not _wgs_runtime_adapter_enabled():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "WGS_RUNTIME_DISABLED",
                "message": "WGS runtime is not enabled; no repair action was started.",
            },
        )
    try:
        with get_sessionmaker()() as session:
            payload = request_step4_repair(
                session=session,
                airflow_client=get_airflow_client(),
                analysis_id=analysis_id,
                requested_by=user.username,
            )
            if payload is not None:
                audit(
                    session=session,
                    username=user.username,
                    action="run.repair_step4_cram",
                    analysis_id=analysis_id,
                    payload={"action_id": payload["action_id"]},
                )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "STEP4_REPAIR_UNAVAILABLE", "message": str(exc)},
        ) from exc
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.post(
    "/api/runs/{analysis_id}/actions/cleanup-step7",
    status_code=status.HTTP_202_ACCEPTED,
)
def cleanup_step7(
    analysis_id: str,
    request: WgsStep7CleanupRequest,
    user: AuthenticatedUser = Depends(admin_user),
) -> dict[str, object]:
    if not _wgs_platform_execution_enabled() or not _wgs_runtime_adapter_enabled():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "WGS_RUNTIME_DISABLED", "message": "WGS runtime is not enabled; SFS cleanup was not started."},
        )
    try:
        with get_sessionmaker()() as session:
            payload = request_step7_cleanup(
                session=session,
                airflow_client=get_airflow_client(),
                analysis_id=analysis_id,
                batch_confirmation=request.batch_confirmation,
                requested_by=user.username,
                retry_failed=request.retry_failed,
                expected_action_id=request.expected_action_id,
            )
            if payload is not None:
                audit(
                    session=session,
                    username=user.username,
                    action="run.cleanup_step7_sfs",
                    analysis_id=analysis_id,
                    payload={"action_id": payload["action_id"]},
                )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "STEP7_CLEANUP_UNAVAILABLE", "message": str(exc)},
        ) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"})
    return payload


@app.post("/api/runs/{analysis_id}/actions/cancel")
def cancel_run(analysis_id: str, user: AuthenticatedUser = Depends(operator_user)) -> dict[str, object]:
    return _wgs_action(analysis_id, "cancel", user)


def _wgs_action(analysis_id: str, action: str, user: AuthenticatedUser) -> dict[str, object]:
    if action in {"resume", "rerun_failed"}:
        if not _wgs_platform_execution_enabled():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "WGS_EXECUTION_DISABLED",
                    "message": "WGS execution is disabled; no recovery attempt was created.",
                },
            )
        if not _wgs_runtime_adapter_enabled():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "WGS_RUNTIME_DISABLED",
                    "message": "WGS runtime adapter is disabled; no recovery attempt was created.",
                },
            )
    try:
        with get_sessionmaker()() as session:
            payload = action_wgs_run(session=session, airflow_client=get_airflow_client(), analysis_id=analysis_id, action=action, requested_by=user.username)
            if payload is not None:
                audit(session=session, username=user.username, action=f"run.{action}", analysis_id=analysis_id)
    except ExecutionDispatchConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(exc)}) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"})
    return payload


@app.get("/api/runs/{analysis_id}/progress")
def run_progress(analysis_id: str) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(
                select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
            )
            adapter = (
                require_pipeline(get_settings(), run.pipeline_name).adapter
                if run is not None
                else None
            )
            rule_context = (
                adapter.project_rule_context(run=run)
                if adapter is not None and adapter.project_rule_context is not None
                else None
            )
            payload = get_run_progress(
                session=session,
                airflow_client=get_airflow_client(),
                analysis_id=analysis_id,
                rule_context=rule_context,
            )
            if payload is not None and run is not None and adapter is not None and adapter.project_progress is not None:
                payload = adapter.project_progress(
                    session=session,
                    run=run,
                    payload=payload,
                )
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    except httpx.HTTPError as exc:
        logger.exception("airflow task instance progress fetch failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "AIRFLOW_PROGRESS_FAILED", "message": str(exc)},
        ) from exc

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.get("/api/runs/{analysis_id}/resources")
def run_resources(analysis_id: str) -> dict[str, object]:
    with get_sessionmaker()() as session:
        payload = get_run_resource_summary(
            session=session,
            analysis_id=analysis_id,
            settings=get_settings(),
        )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_SUMMARY_NOT_FOUND", "message": f"Resource summary not found: {analysis_id}"},
        )
    return payload


@app.get("/api/runs/{analysis_id}/qc")
def run_qc(analysis_id: str) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(
                select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
            )
            if run is None:
                payload = None
            else:
                definition = require_pipeline(
                    get_settings(), run.pipeline_name, capability="qc"
                )
                if definition.adapter.project_qc is None:
                    raise PipelineCapabilityUnavailable(
                        f"Pipeline {definition.pipeline_id!r} has no QC projection adapter."
                    )
                payload = definition.adapter.project_qc(
                    session=session,
                    settings=get_settings(),
                    run=run,
                )
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.post("/api/events/snakemake", dependencies=[Depends(require_internal_service_token)])
def snakemake_event(request: SnakemakeEventRequest) -> dict[str, str]:
    with get_sessionmaker()() as session:
        recorded = record_snakemake_event(session=session, event=request.model_dump())
    if not recorded:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {request.analysis_id}"},
        )
    return {"status": "ok"}


@app.get("/api/runs/{analysis_id}/logs")
def run_logs(
    analysis_id: str,
    stream: str = Query(default="stderr", pattern="^(stdout|stderr|metadata)$"),
    key: str | None = Query(default=None, max_length=64),
    tail: int = Query(default=200, ge=1, le=1000),
) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(
                select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
            )
            adapter = (
                require_pipeline(get_settings(), run.pipeline_name).adapter
                if run is not None
                else None
            )
            handler = adapter.get_log if adapter is not None and adapter.get_log is not None else get_run_log
            payload = handler(
                session=session,
                analysis_id=analysis_id,
                stream=stream,
                tail=tail,
                settings=get_settings(),
                key=key,
            )
    except UnsupportedLogStreamError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_LOG_STREAM", "message": str(exc)},
        ) from exc
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    except InvalidRunPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RUN_PATH", "message": str(exc)},
        ) from exc
    except LogNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LOG_NOT_FOUND", "message": str(exc)},
        ) from exc

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.get("/api/runs/{analysis_id}/logs/index")
def run_log_index(analysis_id: str) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(
                select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
            )
            adapter = (
                require_pipeline(get_settings(), run.pipeline_name).adapter
                if run is not None
                else None
            )
            handler = adapter.list_logs if adapter is not None and adapter.list_logs is not None else list_run_logs
            payload = handler(session=session, analysis_id=analysis_id, settings=get_settings())
    except InvalidRunPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RUN_PATH", "message": str(exc)},
        ) from exc
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.get("/api/runs/{analysis_id}/artifacts")
def run_artifacts(analysis_id: str) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(
                select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
            )
            adapter = (
                require_pipeline(get_settings(), run.pipeline_name).adapter
                if run is not None
                else None
            )
            handler = (
                adapter.list_artifacts
                if adapter is not None and adapter.list_artifacts is not None
                else list_run_artifacts
            )
            payload = handler(
                session=session,
                analysis_id=analysis_id,
                settings=get_settings(),
            )
    except InvalidRunPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RUN_PATH", "message": str(exc)},
        ) from exc
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.get("/api/runs/{analysis_id}/config")
def run_config_detail(analysis_id: str) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(
                select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
            )
            if run is None:
                payload = None
            else:
                definition = require_pipeline(
                    get_settings(), run.pipeline_name, capability="profile"
                )
                if definition.adapter.project_config is None:
                    raise PipelineCapabilityUnavailable(
                        f"Pipeline {definition.pipeline_id!r} has no run configuration projection adapter."
                    )
                payload = definition.adapter.project_config(
                    session=session,
                    settings=get_settings(),
                    run=run,
                )
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return payload


@app.get("/api/health/db")
def database_health() -> dict[str, str]:
    try:
        check_database()
    except Exception:
        logger.exception("biodemo database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "message": "database unavailable"},
        ) from None

    return {"status": "ok"}


@app.get("/api/health/airflow")
def airflow_health() -> dict[str, object]:
    try:
        airflow_payload = get_airflow_client().health()
    except Exception:
        logger.exception("airflow health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "message": "airflow unavailable"},
        ) from None

    return {"status": "ok", "airflow": airflow_payload}


def _deployed_pipelines(settings) -> tuple[str, ...]:
    return get_pipeline_registry(settings).deployed_pipeline_ids


def _active_deployed_pipelines() -> tuple[str, ...]:
    settings = _deployment_guard_settings()
    if settings is not None:
        return _deployed_pipelines(settings)
    return ()


def _require_pipeline_deployed(settings, pipeline: str) -> None:
    if pipeline in {"all", "deployed"}:
        return
    try:
        require_pipeline(settings, pipeline)
    except PipelineRegistryError as exc:
        raise _pipeline_http_exception(exc) from exc


def _deployment_guard_settings():
    """Read deployment scope without making isolated service tests configure runtime secrets."""
    try:
        return get_settings()
    except RuntimeError as exc:
        if str(exc).endswith(" is required"):
            return None
        raise


def _guard_pipeline_deployed(pipeline: str) -> None:
    settings = _deployment_guard_settings()
    if settings is not None:
        _require_pipeline_deployed(settings, pipeline)


def _guard_wgs_execution(dry_run: bool) -> None:
    if dry_run:
        return
    allow_execution = os.getenv("WGS_ALLOW_EXECUTION", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not allow_execution:
        raise ValueError("WGS is deployed in dry-run validation mode; real execution is disabled.")


def _wgs_platform_execution_enabled() -> bool:
    return os.getenv("WGS_EXECUTION_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _wgs_runtime_adapter_enabled() -> bool:
    return os.getenv("WGS_RUNTIME_ADAPTER_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _wgs_step1_canary_enabled() -> bool:
    return os.getenv("WGS_STEP1_CANARY_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _wgs_step3_dryrun_canary_enabled() -> bool:
    return os.getenv("WGS_STEP3_DRYRUN_CANARY_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _wgs_node97_full_canary_enabled() -> bool:
    return os.getenv("WGS_NODE97_FULL_CANARY_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _wgs_contract_v2_enabled() -> bool:
    return os.getenv("WGS_CONTRACT_V2_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _wgs_submission_preview_enabled() -> bool:
    return os.getenv("WGS_SUBMISSION_PREVIEW_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on",
    }
