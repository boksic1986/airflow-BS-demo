import logging

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.airflow_client import AirflowClient
from app.config import get_settings
from app.db import check_database, get_sessionmaker
from app.input_scanner import FastqCandidate, InputPathError, scan_fastq_candidates
from app.run_service import create_pgta_run, get_run_detail, list_run_samples, list_runs


logger = logging.getLogger(__name__)

app = FastAPI(title="airflow-demo backend")


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
    rawdata_root: str
    selected_samples: list[SelectedSampleRequest] = Field(min_length=1)
    email_to: str | None = None
    note: str | None = None


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
    if request.pipeline != "pgta":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_PIPELINE", "message": "Only pipeline=pgta is supported in this phase."},
        )

    settings = get_settings()
    session_factory = get_sessionmaker()
    try:
        selected_samples = [_selected_sample_to_candidate(item) for item in request.selected_samples]
        with session_factory() as session:
            return create_pgta_run(
                session=session,
                settings=settings,
                project_name=request.project_name,
                target=request.target,
                rawdata_root=request.rawdata_root,
                selected_samples=selected_samples,
                email_to=request.email_to,
                note=request.note,
            )
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
