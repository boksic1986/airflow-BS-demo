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
    sync_airflow_status,
)
from app.input_scanner import FastqCandidate, InputPathError, scan_fastq_candidates, scan_nipt_batch_candidates
from app.intake_config import load_intake_config
from app.intake_retention_service import prune_scanner_history
from app.intake_service import list_intake_status, preview_intake_scan, scan_and_submit_intake
from app.operator_resources_service import list_failures_resource, list_samples_resource
from app.pipeline_config_service import (
    PipelineConfigError,
    ProfileChangedError,
    get_pipeline_config_template,
    get_run_config,
    validate_pipeline_config,
)
from app.progress_service import get_run_progress
from app.qc_service import list_run_qc
from app.rule_event_service import get_snakemake_rule_events_page, record_snakemake_event
from app.run_service import (
    create_wgs_run,
    create_nipt_docker_run,
    create_pgta_run,
    create_wes_mock_run,
    get_run_detail,
    list_run_samples,
    list_runs,
    reanalyze_run_to_airflow,
    submit_run_to_airflow,
)
from app.run_resources_service import get_run_resource_summary
from app.system_resources import get_system_resources
from app.workflow_catalog_service import get_workflow_catalog
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
from app.wgs_platform_service import action_wgs_run, acquire_obs_transfer_slot, create_wgs_platform_run, release_obs_transfer_slot, revalidate_wgs_run, submit_wgs_run
from app.wgs_release_catalog import load_wgs_release_catalog
from app.models import AnalysisRun, KubernetesWorkload, ObserverRunState, RuleState, RunValidationIssue, Sample, TransferJob, UserAccount
from app.wgs_timing_service import enrich_progress, serialize_rule_states
from app.wgs_runtime_adapter import build_stage_request, container_workdir_to_host, write_stage_request
from app.wgs_observer import sync_runtime_stage_artifacts
from app.wgs_observer_lifecycle import activate_observer, request_observer_drain
from app.wgs_t7_intake import get_wgs_t7_scanner_state, list_wgs_t7_intake
from app.wgs_step4_service import get_step4_repair_capability, request_step4_repair
from sqlalchemy import select


logger = logging.getLogger(__name__)
INTAKE_SCANNER_DAG_ID = "bio_intake_scan"

app = FastAPI(title="airflow-demo backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_COOKIE = "wgs_session"


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


class SelectedSampleRequest(BaseModel):
    sample_id: str
    r1: str
    r2: str
    source_dir: str
    r1_size: int | None = None
    r2_size: int | None = None
    r1_mtime: float | None = None
    r2_mtime: float | None = None
    discovery_method: str = "server_path_scan"


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline: str
    project_name: str
    target: str = "metadata"
    rawdata_root: str | None = None
    selected_samples: list[SelectedSampleRequest] = Field(default_factory=list)
    template_id: str | None = None
    run_mode: str = "mount_smoke"
    cores: int | None = Field(default=None, ge=1, le=40)
    email_to: str | None = None
    note: str | None = None
    submitted_by: str | None = Field(default=None, max_length=128)
    runtime_profile_id: str | None = None
    config_template_hash: str | None = None
    snakemake_config_yaml: str | None = Field(default=None, max_length=65536)
    wgs_config_path: str | None = None
    wgs_precalling_config_path: str | None = None
    wgs_downstream_config_path: str | None = None
    wgs_targets_path: str | None = None
    wgs_stage: str = "precalling"
    wgs_dry_run: bool = True
    execution_mode: str = Field(default="cce", pattern="^cce$")
    batch_no: str | None = Field(default=None, min_length=1, max_length=128)
    fq_path: str | None = None

    @model_validator(mode="after")
    def validate_pipeline_inputs(self):
        if self.pipeline != "wgs":
            raise ValueError("Only pipeline=wgs is supported.")
        if self.pipeline == "wgs" and self.batch_no and self.fq_path:
            return self
        if self.pipeline == "pgta":
            if not self.rawdata_root:
                raise ValueError("rawdata_root is required for pipeline=pgta.")
            if not self.selected_samples:
                raise ValueError("selected_samples is required for pipeline=pgta.")
        if self.pipeline == "nipt_docker" and not self.template_id:
            if not self.rawdata_root:
                raise ValueError("rawdata_root is required for pipeline=nipt_docker.")
            if not self.selected_samples:
                raise ValueError("selected_samples is required for pipeline=nipt_docker.")
        if self.pipeline == "wgs":
            raise ValueError("batch_no and fq_path are required for pipeline=wgs.")
        return self


class PipelineConfigValidationRequest(BaseModel):
    pipeline: str
    target: str = "metadata"
    run_mode: str = "mount_smoke"
    cores: int | None = Field(default=None, ge=1, le=40)
    runtime_profile_id: str
    config_template_hash: str
    snakemake_config_yaml: str = Field(max_length=65536)


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


class WgsObserverLifecycleRequest(BaseModel):
    attempt: int = Field(ge=1)


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
        "execution_enabled": _wgs_platform_execution_enabled(),
        "runtime_adapter_enabled": _wgs_runtime_adapter_enabled(),
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
    return {
        "environment": getattr(settings, "platform_environment", "Demo"),
        "deployed_pipelines": list(_deployed_pipelines(settings)),
        "airflow_url": getattr(settings, "public_airflow_url", "") or None,
    }


def get_airflow_client() -> AirflowClient:
    settings = get_settings()
    return AirflowClient(
        base_url=settings.airflow_base_url,
        username=settings.airflow_api_username,
        password=settings.airflow_api_password,
    )


@app.post("/api/input/scan")
def scan_input(request: InputScanRequest) -> dict[str, object]:
    if request.pipeline not in {"pgta", "nipt_docker"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_PIPELINE", "message": "Only pipeline=pgta or pipeline=nipt_docker supports server path scan."},
        )

    try:
        settings = get_settings()
        _require_pipeline_deployed(settings, request.pipeline)
        if request.pipeline == "nipt_docker":
            result = scan_nipt_batch_candidates(
                rawdata_root=request.rawdata_root,
                allowed_roots=_scan_roots_for_pipeline(settings, request.pipeline),
                max_samples=request.max_samples,
            )
        else:
            result = scan_fastq_candidates(
                rawdata_root=request.rawdata_root,
                allowed_roots=_scan_roots_for_pipeline(settings, request.pipeline),
                max_samples=request.max_samples,
            )
    except InputPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT_PATH", "message": str(exc)},
        ) from exc

    return _scan_result_payload(result)


@app.get("/api/input/roots")
def input_roots(pipeline: str = Query(pattern="^(pgta|nipt_docker)$")) -> dict[str, object]:
    settings = get_settings()
    _require_pipeline_deployed(settings, pipeline)
    return {
        "pipeline": pipeline,
        "roots": _scan_roots_for_pipeline(settings, pipeline),
    }


@app.get("/api/intake/config")
def intake_config() -> dict[str, object]:
    return _load_intake_config(get_settings()).public_payload()


@app.get("/api/intake/scanner-state")
def intake_scanner_state() -> dict[str, object]:
    settings = _deployment_guard_settings()
    deployed = _deployed_pipelines(settings) if settings is not None else ("pgta", "nipt_docker")
    if deployed == ("wgs",):
        with get_sessionmaker()() as session:
            return get_wgs_t7_scanner_state(
                session=session,
                root=settings.wgs_t7_fastq_root,
                enabled=settings.wgs_intake_scan_enabled,
                schedule_seconds=settings.wgs_intake_scan_interval_seconds,
                auto_dispatch_enabled=settings.wgs_auto_dispatch_enabled,
            )
    trigger_contracts = _intake_trigger_contracts(deployed)
    try:
        airflow_client = get_airflow_client()
        dag_payload = airflow_client.get_dag(INTAKE_SCANNER_DAG_ID)
        dag_runs_payload = airflow_client.list_dag_runs(
            INTAKE_SCANNER_DAG_ID,
            limit=1,
            order_by="-start_date",
        )
    except Exception:
        logger.exception("intake scanner Airflow state unavailable")
        return {
            "dag_id": INTAKE_SCANNER_DAG_ID,
            "airflow_reachable": False,
            "is_paused": None,
            "latest_dag_run_id": None,
            "latest_dag_run_state": None,
            "latest_start_date": None,
            "latest_end_date": None,
            "schedule": "*/10 * * * *",
            "next_run": None,
            "trigger_contracts": trigger_contracts,
            "retention": _intake_retention_state(),
            "message": "Airflow scanner state unavailable",
        }

    latest_run = _latest_dag_run(dag_runs_payload)
    return {
        "dag_id": str(dag_payload.get("dag_id") or INTAKE_SCANNER_DAG_ID),
        "airflow_reachable": True,
        "is_paused": dag_payload.get("is_paused"),
        "latest_dag_run_id": latest_run.get("dag_run_id") if latest_run else None,
        "latest_dag_run_state": latest_run.get("state") if latest_run else None,
        "latest_start_date": latest_run.get("start_date") if latest_run else None,
        "latest_end_date": latest_run.get("end_date") if latest_run else None,
        "schedule": _dag_schedule(dag_payload),
        "next_run": dag_payload.get("next_dagrun") or dag_payload.get("next_dagrun_create_after"),
        "trigger_contracts": trigger_contracts,
        "retention": _intake_retention_state(),
        "message": None,
    }


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
    target: str = "metadata",
    run_mode: str = "mount_smoke",
    profile_id: str | None = None,
) -> dict[str, object]:
    del target, run_mode
    try:
        _guard_pipeline_deployed(pipeline)
        return get_pipeline_config_template(
            settings=get_settings(),
            pipeline=pipeline,
            profile_id=profile_id,
        )
    except PipelineConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CONFIG_VALIDATION_ERROR", "message": str(exc)},
        ) from exc


@app.post("/api/pipeline-config/validate")
def pipeline_config_validate(request: PipelineConfigValidationRequest) -> dict[str, object]:
    try:
        _guard_pipeline_deployed(request.pipeline)
        validated = validate_pipeline_config(
            settings=get_settings(),
            pipeline=request.pipeline,
            profile_id=request.runtime_profile_id,
            template_hash=request.config_template_hash,
            config_yaml=request.snakemake_config_yaml,
            cores=request.cores,
        )
    except ProfileChangedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PROFILE_CHANGED", "message": str(exc)},
        ) from exc
    except PipelineConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CONFIG_VALIDATION_ERROR", "message": str(exc)},
        ) from exc
    return {
        "valid": True,
        "profile": {
            "id": validated.profile_id,
            "label": validated.profile_label,
            "pipeline_version": validated.pipeline_version,
            "config_version": validated.config_version,
        },
        "config_template_hash": validated.template_hash,
        "normalized_yaml": validated.normalized_yaml,
        "changed_paths": validated.changed_paths,
        "warnings": [],
        "errors": [],
    }


@app.post("/api/runs", status_code=status.HTTP_201_CREATED)
def create_run(request: CreateRunRequest, user: AuthenticatedUser = Depends(operator_user)) -> dict[str, object]:
    settings = get_settings()
    session_factory = get_sessionmaker()
    try:
        _require_pipeline_deployed(settings, request.pipeline)
        pipeline_config = _validated_create_config(request=request, settings=settings)
        with session_factory() as session:
            if request.pipeline == "wgs":
                payload = create_wgs_platform_run(
                    session=session,
                    settings=settings,
                    project_name=request.project_name,
                    execution_mode=request.execution_mode,
                    batch_no=str(request.batch_no or ""),
                    fq_path=str(request.fq_path or ""),
                    submitted_by=user.username,
                )
                audit(session=session, username=user.username, action="run.create", analysis_id=str(payload["analysis_id"]), payload={"execution_mode": request.execution_mode})
                return payload
            if request.pipeline == "pgta":
                selected_samples = [_selected_sample_to_candidate(item) for item in request.selected_samples]
                return create_pgta_run(
                    session=session,
                    settings=settings,
                    project_name=request.project_name,
                    target=request.target,
                    rawdata_root=request.rawdata_root or "",
                    selected_samples=selected_samples,
                    submitted_by=request.submitted_by,
                    email_to=request.email_to,
                    note=request.note,
                    pipeline_config=pipeline_config,
                )
            if request.pipeline == "wes_qsub":
                return create_wes_mock_run(
                    session=session,
                    settings=settings,
                    project_name=request.project_name,
                    target=request.target,
                    email_to=request.email_to,
                    note=request.note,
                )
            if request.pipeline == "nipt_docker":
                selected_samples = [_selected_sample_to_candidate(item) for item in request.selected_samples]
                return create_nipt_docker_run(
                    session=session,
                    settings=settings,
                    project_name=request.project_name,
                    template_id=request.template_id,
                    rawdata_root=request.rawdata_root,
                    selected_samples=selected_samples,
                    submitted_by=request.submitted_by,
                    run_mode=request.run_mode,
                    cores=request.cores,
                    email_to=request.email_to,
                    note=request.note,
                    pipeline_config=pipeline_config,
                )
            raise ValueError("Only deployed PGT-A, NIPT Docker, WES demo, or WGS pipelines are supported.")
    except ProfileChangedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PROFILE_CHANGED", "message": str(exc)},
        ) from exc
    except PipelineConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CONFIG_VALIDATION_ERROR", "message": str(exc)},
        ) from exc
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
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": str(exc)},
        ) from exc


@app.get("/api/runs")
def runs_list(
    pipeline: str | None = Query(default=None, pattern="^(all|deployed|pgta|nipt_docker|wgs)$"),
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
        )


@app.get("/api/samples")
def samples_list(
    pipeline: str | None = Query(default=None, pattern="^(all|deployed|pgta|nipt_docker|wgs)$"),
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
        )


@app.get("/api/failures")
def failures_list(
    pipeline: str = Query(default="all", pattern="^(all|deployed|pgta|nipt_docker|wgs)$"),
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
        )


@app.get("/api/dashboard/overview")
def dashboard_overview(
    pipeline: str = Query(default="all", pattern="^(all|deployed|pgta|nipt_docker|wgs)$"),
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
        )


@app.get("/api/dashboard/runs")
def dashboard_runs(
    pipeline: str = Query(default="all", pattern="^(all|deployed|pgta|nipt_docker|wgs)$"),
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
        )


@app.post("/api/runs/{analysis_id}/actions/submit")
def submit_run(analysis_id: str, user: AuthenticatedUser = Depends(operator_user)) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            detail = get_run_detail(session=session, analysis_id=analysis_id)
            if detail is not None:
                _guard_pipeline_deployed(str(detail.get("pipeline") or detail.get("pipeline_name") or ""))
                if str(detail.get("pipeline") or detail.get("pipeline_name") or "") == "wgs":
                    _guard_wgs_execution(bool((detail.get("params") or {}).get("wgs_dry_run", True)))
            if detail is not None and str(detail.get("pipeline") or "") == "wgs" and detail.get("execution_mode") in {"cce", "sge", "local"}:
                if not _wgs_platform_execution_enabled():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="WGS execution is disabled until Phase 2 workflow integration is approved.",
                    )
                payload = submit_wgs_run(session=session, airflow_client=get_airflow_client(), analysis_id=analysis_id)
            else:
                payload = submit_run_to_airflow(session=session, airflow_client=get_airflow_client(), analysis_id=analysis_id)
            if payload is not None:
                audit(session=session, username=user.username, action="run.submit", analysis_id=analysis_id)
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
        _guard_pipelines_deployed(request.pipelines)
        with get_sessionmaker()() as session:
            return scan_and_submit_intake(
                session=session,
                settings=get_settings(),
                airflow_client=get_airflow_client(),
                pipelines=request.pipelines,
                bootstrap=request.bootstrap,
                max_samples=request.max_samples,
            )
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


@app.post("/api/intake/scan-preview")
def intake_scan_preview(request: IntakeScanRequest) -> dict[str, object]:
    try:
        _guard_pipelines_deployed(request.pipelines)
        with get_sessionmaker()() as session:
            return preview_intake_scan(
                session=session,
                settings=get_settings(),
                pipelines=request.pipelines,
                bootstrap=request.bootstrap,
                max_samples=request.max_samples,
            )
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


@app.get("/api/intake/status")
def intake_status(
    pipeline: str | None = Query(default=None, pattern="^(all|deployed|pgta|nipt_docker|wgs)$"),
    state_filter: str | None = Query(
        default=None,
        alias="state",
        pattern="^(bootstrap|observed|ready|submitted|error|disabled|waiting_barcode_stat|no_new_wgs|needs_review|bootstrap_ignored)$",
    ),
    lifecycle: str = Query(default="active", pattern="^(active|archived|all)$"),
    view_filter: str = Query(default="all", alias="view", pattern="^(pending|history|all)$"),
    keyword: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    deployed_pipelines = _active_deployed_pipelines()
    aggregate_scope = pipeline in {None, "all", "deployed"}
    if pipeline and not aggregate_scope:
        _guard_pipeline_deployed(pipeline)
    with get_sessionmaker()() as session:
        if pipeline == "wgs" or (
            aggregate_scope
            and len(deployed_pipelines) == 1
            and deployed_pipelines[0] == "wgs"
        ):
            return list_wgs_t7_intake(
                session=session,
                state=state_filter,
                view=view_filter,
                keyword=keyword,
                limit=limit,
                offset=offset,
            )
        return list_intake_status(
            session=session,
            pipeline=None if aggregate_scope else pipeline,
            state=state_filter,
            lifecycle=lifecycle,
            view=view_filter,
            keyword=keyword,
            limit=limit,
            offset=offset,
            deployed_pipelines=deployed_pipelines if aggregate_scope else None,
        )


@app.get("/api/workflows")
def workflows() -> dict[str, object]:
    settings = _deployment_guard_settings()
    deployed = _deployed_pipelines(settings) if settings is not None else ("pgta", "nipt_docker")
    with get_sessionmaker()() as session:
        return get_workflow_catalog(session=session, pipelines=deployed)


@app.get("/api/system/resources")
def system_resources() -> dict[str, object]:
    return get_system_resources()


@app.post("/api/runs/{analysis_id}/actions/reanalyze")
def reanalyze_run(analysis_id: str, request: ReanalysisRequest) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            detail = get_run_detail(session=session, analysis_id=analysis_id)
            if detail is not None:
                _guard_pipeline_deployed(str(detail.get("pipeline") or detail.get("pipeline_name") or ""))
            payload = reanalyze_run_to_airflow(
                session=session,
                airflow_client=get_airflow_client(),
                analysis_id=analysis_id,
                mode=request.mode,
                rule=request.rule,
                sample_id=request.sample_id,
                stage=request.stage,
                reason=request.reason,
            )
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
            payload = sync_airflow_status(
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
    with get_sessionmaker()() as session:
        payload = get_run_detail(session=session, analysis_id=analysis_id)
        observer = session.scalar(select(ObserverRunState).where(ObserverRunState.analysis_id == analysis_id).order_by(ObserverRunState.attempt.desc()))
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        step4_repair = (
            get_step4_repair_capability(
                session=session,
                run=run,
                execution_enabled=_wgs_platform_execution_enabled(),
                runtime_adapter_enabled=_wgs_runtime_adapter_enabled(),
            )
            if run is not None and run.pipeline_name == "wgs"
            else None
        )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    _guard_pipeline_deployed(str(payload.get("pipeline") or payload.get("pipeline_name") or ""))
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    payload["pipeline_release_id"] = params.get("pipeline_release_id")
    payload["wgs_version"] = params.get("wgs_version")
    payload["wgs_source_commit"] = params.get("wgs_source_commit")
    payload["resolved_runtime"] = params.get("resolved_runtime")
    payload["rule_event_schema_version"] = params.get("rule_event_schema_version")
    payload["observer"] = ({
        "lifecycle_status": observer.lifecycle_status,
        "monitoring_health": observer.monitoring_health,
        "activated_at": observer.activated_at.isoformat() if observer.activated_at else None,
        "deactivated_at": observer.deactivated_at.isoformat() if observer.deactivated_at else None,
        "last_success_at": observer.last_success_at.isoformat() if observer.last_success_at else None,
        "last_error": observer.last_error,
        "updated_at": observer.updated_at.isoformat(),
    } if observer else None)
    payload["step4_repair"] = step4_repair
    return payload


@app.get("/api/runs/{analysis_id}/samples")
def run_samples(analysis_id: str) -> dict[str, object]:
    with get_sessionmaker()() as session:
        if get_run_detail(session=session, analysis_id=analysis_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
            )
        return {"items": list_run_samples(session=session, analysis_id=analysis_id)}


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
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs"))
        if run is None:
            raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"})
        items = session.scalars(
            select(KubernetesWorkload)
            .where(
                KubernetesWorkload.analysis_id == analysis_id,
                KubernetesWorkload.job_name.like("wgs-master-%"),
            )
            .order_by(KubernetesWorkload.attempt, KubernetesWorkload.job_name)
        ).all()
    return {"items": [{"attempt": item.attempt, "pod_hash": item.pod_hash, "job_name": item.job_name, "phase": item.phase, "reason": item.reason, "exit_code": item.exit_code, "image_id": item.image_id, "node_name": item.node_name, "message": item.message, "resources": item.resources_json, "observed_at": item.observed_at.isoformat() if item.observed_at else None, "updated_at": item.updated_at.isoformat()} for item in items]}


@app.get("/api/runs/{analysis_id}/transfers")
def run_transfers(analysis_id: str) -> dict[str, object]:
    with get_sessionmaker()() as session:
        items = session.scalars(select(TransferJob).where(TransferJob.analysis_id == analysis_id).order_by(TransferJob.id)).all()
    return {"items": [{"id": item.id, "transfer_id": item.transfer_id, "attempt": item.attempt, "transfer_type": item.transfer_type, "direction": item.direction, "source": item.source, "destination": item.destination, "status": item.status, "progress_detail_available": item.progress_detail_available, "bytes_total": item.bytes_total if item.progress_detail_available else None, "bytes_transferred": item.bytes_transferred if item.progress_detail_available else None, "files_total": item.files_total if item.progress_detail_available else None, "files_completed": item.files_completed if item.progress_detail_available else None, "current_file": item.current_file if item.progress_detail_available else None, "progress_percent": item.progress_percent if item.progress_detail_available else None, "speed_bps": item.speed_bps if item.progress_detail_available else None, "eta_seconds": item.eta_seconds if item.progress_detail_available else None, "estimated_finish_at": item.estimated_finish_at.isoformat() if item.progress_detail_available and item.estimated_finish_at else None, "checkpoint_ref": item.checkpoint_ref, "heartbeat_at": item.heartbeat_at.isoformat() if item.heartbeat_at else None, "verification_status": item.verification_status, "message": item.message, "error_message": item.error_message, "started_at": item.started_at.isoformat() if item.started_at else None, "ended_at": item.ended_at.isoformat() if item.ended_at else None} for item in items]}


@app.get("/api/runs/{analysis_id}/rules")
def run_rules(
    analysis_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    rule: str | None = None,
    sample_id: str | None = None,
    limit: int = Query(default=1000, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    with get_sessionmaker()() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs"))
        if run is None:
            raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"})
        states = session.scalars(select(RuleState).where(RuleState.analysis_id == analysis_id).order_by(RuleState.attempt, RuleState.layer, RuleState.rule_name)).all()
        filtered = [row for row in states if (not status_filter or row.status == status_filter) and (not rule or row.rule_name == rule) and (not sample_id or row.sample_id == sample_id)]
        page = filtered[offset:offset + limit]
        return {"items": serialize_rule_states(session=session, run=run, rows=page), "total": len(filtered), "limit": limit, "offset": offset}


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
    if request.adapter != "wgs-runtime-200" or not _wgs_runtime_adapter_enabled():
        raise HTTPException(status_code=409, detail={"code": "WGS_RUNTIME_DISABLED", "message": "WGS runtime adapter is disabled."})
    try:
        with get_sessionmaker()() as session:
            run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id, AnalysisRun.pipeline_name == "wgs"))
            if run is None or run.attempt != request.attempt:
                raise ValueError("unknown active WGS attempt")
            params = dict(run.params_json or {})
            release_id = str(params["pipeline_release_id"])
            release = load_wgs_release_catalog(
                Path(get_settings().wgs_release_catalog_path)
            ).release
            if stage_name == "prepare":
                if release.release_id != release_id:
                    raise ValueError("release_unavailable: run WGS release is not current")
                if str(params.get("wgs_source_commit") or "") != release.source_commit:
                    raise ValueError("release_unavailable: run WGS commit is not current")
            if stage_name in {"acquire_input_transfer_slot", "acquire_result_transfer_slot"}:
                transfer_kind = "input" if stage_name == "acquire_input_transfer_slot" else "result"
                transfer_id = f"{analysis_id}-a{request.attempt}-{transfer_kind}"
                slot = acquire_obs_transfer_slot(session=session, analysis_id=analysis_id, attempt=request.attempt, transfer_id=transfer_id)
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
                released = release_obs_transfer_slot(
                    session=session,
                    analysis_id=analysis_id,
                    attempt=request.attempt,
                    transfer_id=transfer_id,
                )
                return {"analysis_id": analysis_id, "attempt": request.attempt, "stage": stage_name, "status": "released", "released": released}
            if stage_name == "finalize_run":
                marker = Path(get_settings().wgs_runtime_request_root) / analysis_id / f"attempt-{request.attempt}" / "step6_materialize.status.json"
                status_payload = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else {}
                if status_payload.get("status") != "success":
                    raise ValueError("Step6 materialization is not complete")
                run.status = "success"
                run.current_stage = "finalize_run"
                session.commit()
                return {"analysis_id": analysis_id, "attempt": request.attempt, "stage": stage_name, "status": "success"}
            expected_command = f"wgs-runtime {analysis_id} {request.attempt} {stage_name}"
            if request.command != expected_command:
                raise ValueError("runtime command does not match the registered stage")
            settings = get_settings()
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
                workdir=container_workdir_to_host(
                    run.workdir,
                    container_root=settings.host_results_root,
                    host_root=settings.wgs_results_host_root,
                ),
                bs_runtime_root=settings.wgs_runtime_bs_root,
                node200_runtime_root=settings.wgs_runtime_node200_root,
                project_name=str(params["project_name"]),
                batch_no=str(params["batch_no"]),
                fq_path=fq_node200,
            )
            path = write_stage_request(settings.wgs_runtime_request_root, payload)
            if stage_name == "prepare":
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
            run.current_stage = stage_name
            session.commit()
            return {"analysis_id": analysis_id, "attempt": request.attempt, "stage": stage_name, "status": "registered", "request_path": str(path)}
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
    return {"analysis_id": analysis_id, "attempt": attempt, "stage": stage, "ready": status_value in {"success", "complete", "succeeded"}, "failed": status_value == "failed", "status": status_value, "message": payload.get("message", ""), "master": payload.get("master")}


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


@app.post("/api/runs/{analysis_id}/actions/cancel")
def cancel_run(analysis_id: str, user: AuthenticatedUser = Depends(operator_user)) -> dict[str, object]:
    return _wgs_action(analysis_id, "cancel", user)


def _wgs_action(analysis_id: str, action: str, user: AuthenticatedUser) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            payload = action_wgs_run(session=session, airflow_client=get_airflow_client(), analysis_id=analysis_id, action=action, requested_by=user.username)
            if payload is not None:
                audit(session=session, username=user.username, action=f"run.{action}", analysis_id=analysis_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(exc)}) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"})
    return payload


@app.get("/api/runs/{analysis_id}/progress")
def run_progress(analysis_id: str) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            payload = get_run_progress(
                session=session,
                airflow_client=get_airflow_client(),
                analysis_id=analysis_id,
            )
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
    if str(payload.get("pipeline") or "") == "wgs":
        with get_sessionmaker()() as session:
            run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
            if run is not None:
                payload = enrich_progress(session=session, run=run, payload=payload)
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
    with get_sessionmaker()() as session:
        payload = list_run_qc(session=session, analysis_id=analysis_id)
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
            payload = get_run_log(
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
            payload = list_run_logs(session=session, analysis_id=analysis_id, settings=get_settings())
    except InvalidRunPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RUN_PATH", "message": str(exc)},
        ) from exc
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
            payload = list_run_artifacts(
                session=session,
                analysis_id=analysis_id,
                settings=get_settings(),
            )
    except InvalidRunPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RUN_PATH", "message": str(exc)},
        ) from exc

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
            payload = get_run_config(
                session=session,
                analysis_id=analysis_id,
                settings=get_settings(),
            )
    except PipelineConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CONFIG_VALIDATION_ERROR", "message": str(exc)},
        ) from exc
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


def _validated_create_config(*, request: CreateRunRequest, settings):
    values = (
        request.runtime_profile_id,
        request.config_template_hash,
        request.snakemake_config_yaml,
    )
    if all(value is None for value in values):
        return None
    if request.pipeline not in {"pgta", "nipt_docker"}:
        raise PipelineConfigError("Editable Snakemake config is only available for PGT-A and NIPT Docker.")
    if any(value is None for value in values):
        raise PipelineConfigError(
            "runtime_profile_id, config_template_hash, and snakemake_config_yaml must be supplied together."
        )
    return validate_pipeline_config(
        settings=settings,
        pipeline=request.pipeline,
        profile_id=str(request.runtime_profile_id),
        template_hash=str(request.config_template_hash),
        config_yaml=str(request.snakemake_config_yaml),
        cores=request.cores,
    )


def _selected_sample_to_candidate(item: SelectedSampleRequest) -> FastqCandidate:
    from pathlib import Path

    r1_path = Path(item.r1)
    r2_path = Path(item.r2)
    r1_stat = r1_path.stat() if item.r1_size is None or item.r1_mtime is None else None
    r2_stat = r2_path.stat() if item.r2_size is None or item.r2_mtime is None else None
    return FastqCandidate(
        sample_id=item.sample_id,
        r1=item.r1,
        r2=item.r2,
        source_dir=item.source_dir,
        r1_size=item.r1_size if item.r1_size is not None else r1_stat.st_size,
        r2_size=item.r2_size if item.r2_size is not None else r2_stat.st_size,
        r1_mtime=item.r1_mtime if item.r1_mtime is not None else r1_stat.st_mtime,
        r2_mtime=item.r2_mtime if item.r2_mtime is not None else r2_stat.st_mtime,
        discovery_method=item.discovery_method,
    )


def _scan_roots_for_pipeline(settings, pipeline: str) -> list[str]:
    roots = _load_intake_config(settings).roots_for_pipeline(pipeline)
    if roots:
        return roots
    if pipeline == "nipt_docker":
        return list(getattr(settings, "nipt_input_scan_roots", []) or [])
    return list(getattr(settings, "pgta_input_scan_roots", None) or getattr(settings, "input_scan_roots", []) or [])


def _deployed_pipelines(settings) -> tuple[str, ...]:
    configured = tuple(getattr(settings, "deployed_pipelines", ()) or ())
    return configured or ("wgs",)


def _active_deployed_pipelines() -> tuple[str, ...]:
    settings = _deployment_guard_settings()
    if settings is not None:
        return _deployed_pipelines(settings)
    # Direct service tests do not load runtime settings; production requests
    # always take their scope from DEPLOYED_PIPELINES above.
    return ("pgta", "nipt_docker", "wgs")


def _require_pipeline_deployed(settings, pipeline: str) -> None:
    if pipeline in {"all", "deployed"}:
        return
    if not tuple(getattr(settings, "deployed_pipelines", ()) or ()):
        return
    if pipeline not in _deployed_pipelines(settings):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "PIPELINE_NOT_DEPLOYED",
                "message": f"Pipeline is not deployed in this environment: {pipeline}",
            },
        )


def _require_pipelines_deployed(settings, pipelines: list[str]) -> None:
    for pipeline in pipelines:
        _require_pipeline_deployed(settings, pipeline)


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


def _guard_pipelines_deployed(pipelines: list[str]) -> None:
    settings = _deployment_guard_settings()
    if settings is not None:
        _require_pipelines_deployed(settings, pipelines)


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


def _load_intake_config(settings):
    return load_intake_config(
        path=getattr(settings, "intake_config_path", None),
        fallback_pgta_roots=list(getattr(settings, "pgta_input_scan_roots", None) or getattr(settings, "input_scan_roots", []) or []),
        fallback_nipt_roots=list(getattr(settings, "nipt_input_scan_roots", []) or []),
    )


def _latest_dag_run(payload: dict[str, object]) -> dict[str, object] | None:
    dag_runs = payload.get("dag_runs")
    if not isinstance(dag_runs, list) or not dag_runs:
        return None
    latest = dag_runs[0]
    return latest if isinstance(latest, dict) else None


def _dag_schedule(payload: dict[str, object]) -> str:
    schedule = payload.get("schedule_interval") or payload.get("timetable_description")
    if isinstance(schedule, dict):
        value = schedule.get("value")
        return str(value) if value else "*/10 * * * *"
    return str(schedule or "*/10 * * * *")


def _intake_trigger_contracts(pipelines: tuple[str, ...] | list[str]) -> dict[str, str]:
    contracts = {
        "pgta": "*.samples.tsv + *.READY",
        "nipt_docker": "*.nipt.yaml or configured discovery root",
        "wgs": "*.wgs.yaml + *.READY",
    }
    return {pipeline: contracts[pipeline] for pipeline in pipelines if pipeline in contracts}


def _intake_retention_state() -> dict[str, object]:
    return {"enabled": True, "days": 30, "scope": "bio_intake_scan only"}


def _scan_result_payload(result) -> dict[str, object]:
    return {
        "pipeline": result.pipeline,
        "rawdata_root": result.rawdata_root,
        "truncated": result.truncated,
        "items": [item.__dict__ for item in result.items],
    }
