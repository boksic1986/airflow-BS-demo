import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel, Field, model_validator

from app.airflow_client import AirflowClient
from app.config import get_cors_origins, get_settings
from app.db import check_database, get_sessionmaker
from app.diagnostics_service import (
    InvalidRunPathError,
    LogNotFoundError,
    MissingDagRunError,
    UnsupportedLogStreamError,
    get_run_log,
    list_run_artifacts,
    sync_airflow_status,
)
from app.input_scanner import FastqCandidate, InputPathError, scan_fastq_candidates
from app.qc_service import list_run_qc
from app.rule_event_service import list_snakemake_rule_events, record_snakemake_event
from app.run_service import (
    create_pgta_run,
    create_wes_mock_run,
    get_run_detail,
    list_run_samples,
    list_runs,
    reanalyze_wes_run,
    submit_run_to_airflow,
)


logger = logging.getLogger(__name__)

app = FastAPI(title="airflow-demo backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
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
    pipeline: str
    project_name: str
    target: str = "metadata"
    rawdata_root: str | None = None
    selected_samples: list[SelectedSampleRequest] = Field(default_factory=list)
    email_to: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_pipeline_inputs(self):
        if self.pipeline == "pgta":
            if not self.rawdata_root:
                raise ValueError("rawdata_root is required for pipeline=pgta.")
            if not self.selected_samples:
                raise ValueError("selected_samples is required for pipeline=pgta.")
        return self


class ReanalysisRequest(BaseModel):
    mode: str
    rule: str | None = None
    sample_id: str | None = None
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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def get_airflow_client() -> AirflowClient:
    settings = get_settings()
    return AirflowClient(
        base_url=settings.airflow_base_url,
        username=settings.airflow_api_username,
        password=settings.airflow_api_password,
    )


@app.post("/api/input/scan")
def scan_input(request: InputScanRequest) -> dict[str, object]:
    if request.pipeline != "pgta":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_PIPELINE", "message": "Only pipeline=pgta supports server path scan."},
        )

    try:
        result = scan_fastq_candidates(
            rawdata_root=request.rawdata_root,
            allowed_roots=get_settings().input_scan_roots,
            max_samples=request.max_samples,
        )
    except InputPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT_PATH", "message": str(exc)},
        ) from exc

    return {
        "pipeline": result.pipeline,
        "rawdata_root": result.rawdata_root,
        "truncated": result.truncated,
        "items": [item.__dict__ for item in result.items],
    }


@app.post("/api/runs", status_code=status.HTTP_201_CREATED)
def create_run(request: CreateRunRequest) -> dict[str, object]:
    settings = get_settings()
    session_factory = get_sessionmaker()
    try:
        with session_factory() as session:
            if request.pipeline == "pgta":
                selected_samples = [_selected_sample_to_candidate(item) for item in request.selected_samples]
                return create_pgta_run(
                    session=session,
                    settings=settings,
                    project_name=request.project_name,
                    target=request.target,
                    rawdata_root=request.rawdata_root or "",
                    selected_samples=selected_samples,
                    email_to=request.email_to,
                    note=request.note,
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
            raise ValueError("Only pipeline=pgta or pipeline=wes_qsub is supported in this phase.")
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
    pipeline: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    with get_sessionmaker()() as session:
        return list_runs(session=session, pipeline=pipeline, status=status_filter, limit=limit, offset=offset)


@app.post("/api/runs/{analysis_id}/actions/submit")
def submit_run(analysis_id: str) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            payload = submit_run_to_airflow(
                session=session,
                airflow_client=get_airflow_client(),
                analysis_id=analysis_id,
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


@app.post("/api/runs/{analysis_id}/actions/reanalyze")
def reanalyze_run(analysis_id: str, request: ReanalysisRequest) -> dict[str, object]:
    try:
        with get_sessionmaker()() as session:
            payload = reanalyze_wes_run(
                session=session,
                airflow_client=get_airflow_client(),
                analysis_id=analysis_id,
                mode=request.mode,
                rule=request.rule,
                sample_id=request.sample_id,
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
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
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


@app.get("/api/runs/{analysis_id}/rules")
def run_rules(analysis_id: str) -> dict[str, object]:
    with get_sessionmaker()() as session:
        items = list_snakemake_rule_events(session=session, analysis_id=analysis_id)
    if items is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RUN_NOT_FOUND", "message": f"Run not found: {analysis_id}"},
        )
    return {"items": items}


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


@app.post("/api/events/snakemake")
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
