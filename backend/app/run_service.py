from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import secrets

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.input_scanner import FastqCandidate, InputPathError, ensure_allowed_path
from app.models import AnalysisRun, Sample


PGTA_DAG_ID = "bio_pgta"


def create_pgta_run(
    *,
    session: Session,
    settings,
    project_name: str,
    target: str,
    rawdata_root: str,
    selected_samples: list[FastqCandidate],
    email_to: str | None = None,
    note: str | None = None,
) -> dict:
    if target != "metadata":
        raise ValueError("Only target=metadata is supported before Airflow DAG integration.")
    if not selected_samples:
        raise ValueError("At least one sample must be selected.")
    sample_ids = [sample.sample_id for sample in selected_samples]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("selected_samples contains duplicate sample_id values.")

    rawdata_root_path = ensure_allowed_path(rawdata_root, settings.input_scan_roots)
    for sample in selected_samples:
        _validate_selected_sample(sample, rawdata_root_path, settings.input_scan_roots)

    analysis_id = _new_analysis_id()
    shared_root = Path(settings.container_shared_root)
    workdir = shared_root / "runs" / analysis_id
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = config_dir / "samples.selected.tsv"
    request_path = config_dir / "request.json"
    _write_manifest(manifest_path, selected_samples)
    _write_request(
        request_path,
        analysis_id=analysis_id,
        project_name=project_name,
        target=target,
        rawdata_root=str(rawdata_root_path),
        selected_samples=selected_samples,
        email_to=email_to,
        note=note,
    )

    params = {
        "project_name": project_name,
        "rawdata_root": str(rawdata_root_path),
        "target": target,
        "input_mode": "server_path_scan",
        "selected_count": len(selected_samples),
        "note": note,
    }
    run = AnalysisRun(
        analysis_id=analysis_id,
        pipeline_name="pgta",
        dag_id=PGTA_DAG_ID,
        dag_run_id=None,
        mode="new",
        status="created",
        sample_sheet_path=str(manifest_path),
        workdir=str(workdir),
        params_json=params,
        email_to=email_to,
    )
    session.add(run)
    for item in selected_samples:
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id=item.sample_id,
                fq1=item.r1,
                fq2=item.r2,
                metadata_json={
                    "source_dir": item.source_dir,
                    "r1_size": item.r1_size,
                    "r2_size": item.r2_size,
                    "r1_mtime": item.r1_mtime,
                    "r2_mtime": item.r2_mtime,
                    "discovery_method": item.discovery_method,
                },
                status="pending",
                qc_status="unknown",
            )
        )
    session.commit()

    return _run_payload(run, sample_count=len(selected_samples))


def list_runs(*, session: Session, pipeline: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    query = select(AnalysisRun)
    count_query = select(func.count()).select_from(AnalysisRun)
    if pipeline:
        query = query.where(AnalysisRun.pipeline_name == pipeline)
        count_query = count_query.where(AnalysisRun.pipeline_name == pipeline)
    if status:
        query = query.where(AnalysisRun.status == status)
        count_query = count_query.where(AnalysisRun.status == status)

    runs = session.scalars(query.order_by(desc(AnalysisRun.created_at)).limit(limit).offset(offset)).all()
    total = session.scalar(count_query) or 0
    return {"items": [_run_list_payload(session, run) for run in runs], "total": total}


def get_run_detail(*, session: Session, analysis_id: str) -> dict | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    if run is None:
        return None
    return _run_detail_payload(session, run)


def list_run_samples(*, session: Session, analysis_id: str) -> list[dict]:
    samples = session.scalars(select(Sample).where(Sample.analysis_id == analysis_id).order_by(Sample.sample_id)).all()
    return [
        {
            "sample_id": sample.sample_id,
            "family_id": sample.family_id,
            "sample_type": sample.sample_type,
            "sex": sample.sex,
            "fq1": sample.fq1,
            "fq2": sample.fq2,
            "status": sample.status,
            "qc_status": sample.qc_status,
            "metadata": sample.metadata_json,
        }
        for sample in samples
    ]


def _validate_selected_sample(sample: FastqCandidate, rawdata_root: Path, allowed_roots: list[str]) -> None:
    r1 = ensure_allowed_path(sample.r1, allowed_roots)
    r2 = ensure_allowed_path(sample.r2, allowed_roots)
    source_dir = ensure_allowed_path(sample.source_dir, allowed_roots)
    if not (r1.is_file() and r2.is_file()):
        raise InputPathError(f"Selected FASTQ pair is not readable: {sample.sample_id}")
    if not (r1.is_relative_to(rawdata_root) and r2.is_relative_to(rawdata_root) and source_dir.is_relative_to(rawdata_root)):
        raise InputPathError(f"Selected sample is outside rawdata_root: {sample.sample_id}")


def _write_manifest(path: Path, selected_samples: list[FastqCandidate]) -> None:
    lines = ["sample_id\tR1\tR2\tsource_dir"]
    for item in selected_samples:
        lines.append(f"{item.sample_id}\t{item.r1}\t{item.r2}\t{item.source_dir}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_request(
    path: Path,
    *,
    analysis_id: str,
    project_name: str,
    target: str,
    rawdata_root: str,
    selected_samples: list[FastqCandidate],
    email_to: str | None,
    note: str | None,
) -> None:
    payload = {
        "analysis_id": analysis_id,
        "pipeline": "pgta",
        "project_name": project_name,
        "target": target,
        "rawdata_root": rawdata_root,
        "selected_samples": [asdict(item) for item in selected_samples],
        "email_to": email_to,
        "note": note,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _new_analysis_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3).upper()
    return f"PGTA_{now}_{suffix}"


def _run_payload(run: AnalysisRun, *, sample_count: int) -> dict:
    return {
        "analysis_id": run.analysis_id,
        "pipeline": run.pipeline_name,
        "dag_id": run.dag_id,
        "dag_run_id": run.dag_run_id,
        "status": run.status,
        "workdir": run.workdir,
        "sample_count": sample_count,
    }


def _run_list_payload(session: Session, run: AnalysisRun) -> dict:
    sample_count = session.scalar(select(func.count()).select_from(Sample).where(Sample.analysis_id == run.analysis_id)) or 0
    return {
        "analysis_id": run.analysis_id,
        "pipeline": run.pipeline_name,
        "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        "sample_count": sample_count,
        "qc_status": "unknown",
    }


def _run_detail_payload(session: Session, run: AnalysisRun) -> dict:
    payload = _run_payload(run, sample_count=session.scalar(select(func.count()).select_from(Sample).where(Sample.analysis_id == run.analysis_id)) or 0)
    payload.update(
        {
            "mode": run.mode,
            "sample_sheet_path": run.sample_sheet_path,
            "params": run.params_json,
            "airflow_url": run.airflow_url,
            "error_summary": run.error_summary,
            "email_to": run.email_to,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "ended_at": run.ended_at.isoformat() if run.ended_at else None,
        }
    )
    return payload
