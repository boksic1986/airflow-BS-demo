from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import secrets

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.input_scanner import FastqCandidate, InputPathError, ensure_allowed_path
from app.models import AnalysisRun, RunAction, Sample


PGTA_DAG_ID = "bio_pgta"
WES_DAG_ID = "bio_wes_qsub"
SUPPORTED_PGTA_TARGETS = {"metadata", "dryrun_cnv", "invalid_target", "baseline_qc"}
SUPPORTED_PGTA_REANALYSIS_MODES = {"resume"}
PGTA_REANALYSIS_TERMINAL_STATUSES = {"failed", "terminated"}
SUPPORTED_WES_TARGETS = {"final_summary"}
SUPPORTED_WES_REANALYSIS_MODES = {"resume", "rerun_rule"}
SUPPORTED_WES_RERUN_RULES = {"fastp", "bwa_mem", "markdup", "final_summary"}
WES_SAMPLE_RULES = {"fastp", "bwa_mem", "markdup"}
WES_MOCK_SAMPLES = {
    "S001": "pipelines/wes/mock_data/S001.input.txt",
    "S002": "pipelines/wes/mock_data/S002.input.txt",
}
WES_BACKEND_EVENT_URL = "http://backend:8000/api/events/snakemake"


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
    _validate_pgta_target(target)
    if not selected_samples:
        raise ValueError("At least one sample must be selected.")
    _validate_pgta_sample_count(target=target, selected_count=len(selected_samples))
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
    _ensure_airflow_writable(workdir)
    _ensure_airflow_writable(config_dir)

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


def create_wes_mock_run(
    *,
    session: Session,
    settings,
    project_name: str,
    target: str,
    email_to: str | None = None,
    note: str | None = None,
) -> dict:
    _validate_wes_target(target)

    analysis_id = _new_wes_analysis_id()
    shared_root = Path(settings.container_shared_root)
    workdir = shared_root / "runs" / analysis_id
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    _ensure_airflow_writable(workdir)
    _ensure_airflow_writable(config_dir)

    manifest_path = config_dir / "samples.selected.tsv"
    request_path = config_dir / "request.json"
    _write_wes_manifest(manifest_path)
    _write_wes_request(
        request_path,
        analysis_id=analysis_id,
        project_name=project_name,
        target=target,
        email_to=email_to,
        note=note,
    )

    params = {
        "project_name": project_name,
        "target": target,
        "input_mode": "mock_wes",
        "selected_count": len(WES_MOCK_SAMPLES),
        "max_jobs": 2,
        "note": note,
    }
    run = AnalysisRun(
        analysis_id=analysis_id,
        pipeline_name="wes_qsub",
        dag_id=WES_DAG_ID,
        dag_run_id=None,
        mode="new",
        status="created",
        sample_sheet_path=str(manifest_path),
        workdir=str(workdir),
        params_json=params,
        email_to=email_to,
    )
    session.add(run)
    for sample_id, input_path in WES_MOCK_SAMPLES.items():
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id=sample_id,
                fq1=input_path,
                fq2=None,
                metadata_json={"input_mode": "mock_wes", "source": input_path},
                status="pending",
                qc_status="unknown",
            )
        )
    session.commit()

    return _run_payload(run, sample_count=len(WES_MOCK_SAMPLES))


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


def submit_run_to_airflow(*, session: Session, airflow_client, analysis_id: str) -> dict | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    if run is None:
        return None
    _validate_submit_run(run)

    dag_run_id = f"manual__{analysis_id}"
    conf = _dag_conf(run)
    airflow_payload = airflow_client.trigger_dag_run(run.dag_id, dag_run_id=dag_run_id, conf=conf)
    dag_run_id = airflow_payload.get("dag_run_id") or dag_run_id

    run.status = "submitted"
    run.dag_run_id = dag_run_id
    _set_sample_status(session=session, analysis_id=analysis_id, status="running")
    run_action = RunAction(
        analysis_id=analysis_id,
        action="submit",
        payload_json={"dag_id": run.dag_id, "dag_run_id": dag_run_id, "conf": conf},
        result_status="accepted",
        message="Airflow DAG run submitted.",
    )
    session.add(run_action)
    session.commit()
    session.refresh(run)
    return _run_detail_payload(session, run)


def reanalyze_wes_run(
    *,
    session: Session,
    airflow_client,
    analysis_id: str,
    mode: str,
    rule: str | None = None,
    sample_id: str | None = None,
    reason: str | None = None,
) -> dict | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    if run is None:
        return None
    return _reanalyze_wes_run_object(
        session=session,
        airflow_client=airflow_client,
        run=run,
        mode=mode,
        rule=rule,
        sample_id=sample_id,
        reason=reason,
    )


def reanalyze_run_to_airflow(
    *,
    session: Session,
    airflow_client,
    analysis_id: str,
    mode: str,
    rule: str | None = None,
    sample_id: str | None = None,
    reason: str | None = None,
) -> dict | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    if run is None:
        return None
    if run.pipeline_name == "pgta":
        return _reanalyze_pgta_run_object(
            session=session,
            airflow_client=airflow_client,
            run=run,
            mode=mode,
            rule=rule,
            sample_id=sample_id,
            reason=reason,
        )
    if run.pipeline_name == "wes_qsub":
        return _reanalyze_wes_run_object(
            session=session,
            airflow_client=airflow_client,
            run=run,
            mode=mode,
            rule=rule,
            sample_id=sample_id,
            reason=reason,
        )
    raise ValueError("Only pipeline=pgta or pipeline=wes_qsub supports reanalysis in this phase.")


def _reanalyze_wes_run_object(
    *,
    session: Session,
    airflow_client,
    run: AnalysisRun,
    mode: str,
    rule: str | None,
    sample_id: str | None,
    reason: str | None,
) -> dict:
    _validate_wes_reanalysis(run=run, mode=mode, rule=rule, sample_id=sample_id)

    params = dict(run.params_json or {})
    params["target"] = "final_summary"
    if mode == "rerun_rule":
        params["rule"] = rule
        params["sample_id"] = sample_id

    run.mode = mode
    run.status = "submitted"
    _set_sample_status(session=session, analysis_id=run.analysis_id, status="running")
    run.params_json = params
    run.error_summary = None
    run.ended_at = None

    dag_run_id = f"manual__{run.analysis_id}__{mode}__{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    conf = _dag_conf(run)
    airflow_payload = airflow_client.trigger_dag_run(run.dag_id, dag_run_id=dag_run_id, conf=conf)
    dag_run_id = airflow_payload.get("dag_run_id") or dag_run_id
    run.dag_run_id = dag_run_id
    session.add(
        RunAction(
            analysis_id=run.analysis_id,
            action=mode,
            payload_json={
                "dag_id": run.dag_id,
                "dag_run_id": dag_run_id,
                "conf": conf,
                "rule": rule,
                "sample_id": sample_id,
                "reason": reason,
            },
            result_status="accepted",
            message="WES mock reanalysis DAG run submitted.",
        )
    )
    session.commit()
    session.refresh(run)
    return {
        "analysis_id": run.analysis_id,
        "new_dag_run_id": dag_run_id,
        "mode": mode,
        "status": run.status,
    }


def _reanalyze_pgta_run_object(
    *,
    session: Session,
    airflow_client,
    run: AnalysisRun,
    mode: str,
    rule: str | None,
    sample_id: str | None,
    reason: str | None,
) -> dict:
    _validate_pgta_reanalysis(run=run, mode=mode, rule=rule, sample_id=sample_id)

    params = dict(run.params_json or {})
    params["target"] = "baseline_qc"
    previous_dag_run_id = run.dag_run_id

    run.mode = mode
    run.status = "submitted"
    _set_sample_status(session=session, analysis_id=run.analysis_id, status="running")
    run.params_json = params
    run.error_summary = None
    run.ended_at = None

    dag_run_id = f"manual__{run.analysis_id}__{mode}__{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    conf = _dag_conf(run)
    airflow_payload = airflow_client.trigger_dag_run(run.dag_id, dag_run_id=dag_run_id, conf=conf)
    dag_run_id = airflow_payload.get("dag_run_id") or dag_run_id
    run.dag_run_id = dag_run_id
    session.add(
        RunAction(
            analysis_id=run.analysis_id,
            action=mode,
            payload_json={
                "dag_id": run.dag_id,
                "dag_run_id": dag_run_id,
                "previous_dag_run_id": previous_dag_run_id,
                "conf": conf,
                "rule": rule,
                "sample_id": sample_id,
                "reason": reason,
            },
            result_status="accepted",
            message="PGT-A baseline_qc resume DAG run submitted.",
        )
    )
    session.commit()
    session.refresh(run)
    return {
        "analysis_id": run.analysis_id,
        "new_dag_run_id": dag_run_id,
        "mode": mode,
        "status": run.status,
    }


def _validate_selected_sample(sample: FastqCandidate, rawdata_root: Path, allowed_roots: list[str]) -> None:
    r1 = ensure_allowed_path(sample.r1, allowed_roots)
    r2 = ensure_allowed_path(sample.r2, allowed_roots)
    source_dir = ensure_allowed_path(sample.source_dir, allowed_roots)
    if not (r1.is_file() and r2.is_file()):
        raise InputPathError(f"Selected FASTQ pair is not readable: {sample.sample_id}")
    if not (r1.is_relative_to(rawdata_root) and r2.is_relative_to(rawdata_root) and source_dir.is_relative_to(rawdata_root)):
        raise InputPathError(f"Selected sample is outside rawdata_root: {sample.sample_id}")


def _validate_submit_run(run: AnalysisRun) -> None:
    if run.status != "created":
        raise ValueError("Run must have status=created before submit.")
    params = run.params_json or {}
    if run.pipeline_name == "pgta":
        _validate_pgta_target(str(params.get("target") or "metadata"))
        _validate_pgta_sample_count(
            target=str(params.get("target") or "metadata"),
            selected_count=_pgta_selected_count(run),
        )
    elif run.pipeline_name == "wes_qsub":
        _validate_wes_target(str(params.get("target") or "final_summary"))
    else:
        raise ValueError("Only pipeline=pgta or pipeline=wes_qsub can be submitted by this endpoint.")
    if not run.sample_sheet_path:
        raise ValueError("Run is missing sample_sheet_path.")
    if not run.workdir:
        raise ValueError("Run is missing workdir.")


def _validate_pgta_target(target: str) -> None:
    if target not in SUPPORTED_PGTA_TARGETS:
        supported = ", ".join(sorted(SUPPORTED_PGTA_TARGETS))
        raise ValueError(f"Unsupported PGT-A target: {target}. Supported targets: {supported}.")


def _validate_pgta_sample_count(*, target: str, selected_count: int) -> None:
    if target == "baseline_qc" and selected_count < 2:
        raise ValueError("baseline_qc requires at least 2 selected samples for reference-style baseline comparison.")


def _pgta_selected_count(run: AnalysisRun) -> int:
    params = run.params_json or {}
    selected_count = params.get("selected_count")
    if isinstance(selected_count, int):
        return selected_count
    if isinstance(selected_count, str) and selected_count.isdigit():
        return int(selected_count)
    if not run.sample_sheet_path:
        return 0
    manifest = Path(run.sample_sheet_path)
    if not manifest.is_file():
        return 0
    return max(0, len([line for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]) - 1)


def _validate_wes_target(target: str) -> None:
    if target not in SUPPORTED_WES_TARGETS:
        supported = ", ".join(sorted(SUPPORTED_WES_TARGETS))
        raise ValueError(f"Unsupported WES target: {target}. Supported targets: {supported}.")


def _validate_wes_reanalysis(*, run: AnalysisRun, mode: str, rule: str | None, sample_id: str | None) -> None:
    if run.pipeline_name != "wes_qsub":
        raise ValueError("Only pipeline=wes_qsub supports reanalysis in this phase.")
    if mode not in SUPPORTED_WES_REANALYSIS_MODES:
        supported = ", ".join(sorted(SUPPORTED_WES_REANALYSIS_MODES))
        raise ValueError(f"Unsupported WES reanalysis mode: {mode}. Supported modes: {supported}.")
    if run.status in {"submitted", "running", "queued"}:
        raise ValueError("Run is already active; sync or wait before reanalysis.")
    if not run.dag_run_id:
        raise ValueError("Run must have an existing dag_run_id before reanalysis.")
    if not run.sample_sheet_path:
        raise ValueError("Run is missing sample_sheet_path.")
    if not run.workdir:
        raise ValueError("Run is missing workdir.")
    _validate_wes_target(str((run.params_json or {}).get("target") or "final_summary"))

    if mode == "resume":
        return

    if rule not in SUPPORTED_WES_RERUN_RULES:
        supported = ", ".join(sorted(SUPPORTED_WES_RERUN_RULES))
        raise ValueError(f"Unsupported WES rerun rule: {rule}. Supported rules: {supported}.")
    if rule in WES_SAMPLE_RULES:
        if sample_id not in WES_MOCK_SAMPLES:
            supported_samples = ", ".join(sorted(WES_MOCK_SAMPLES))
            raise ValueError(f"sample_id is required for rule {rule}; supported samples: {supported_samples}.")
    elif sample_id:
        raise ValueError("sample_id is not supported for final_summary rerun.")


def _validate_pgta_reanalysis(*, run: AnalysisRun, mode: str, rule: str | None, sample_id: str | None) -> None:
    if run.pipeline_name != "pgta":
        raise ValueError("Only pipeline=pgta supports PGT-A reanalysis.")
    if mode not in SUPPORTED_PGTA_REANALYSIS_MODES:
        supported = ", ".join(sorted(SUPPORTED_PGTA_REANALYSIS_MODES))
        raise ValueError(f"Unsupported PGT-A reanalysis mode: {mode}. Supported modes: {supported}.")
    if run.status in {"submitted", "running", "queued"}:
        raise ValueError("Run is already active; sync or wait before reanalysis.")
    if run.status not in PGTA_REANALYSIS_TERMINAL_STATUSES:
        raise ValueError("PGT-A resume requires a run status of failed or terminated.")
    if rule or sample_id:
        raise ValueError("PGT-A resume does not support rule or sample selection in this phase.")
    if not run.dag_run_id:
        raise ValueError("Run must have an existing dag_run_id before reanalysis.")
    if not run.sample_sheet_path:
        raise ValueError("Run is missing sample_sheet_path.")
    if not run.workdir:
        raise ValueError("Run is missing workdir.")

    target = str((run.params_json or {}).get("target") or "metadata")
    _validate_pgta_target(target)
    if target != "baseline_qc":
        raise ValueError("PGT-A resume is only supported for baseline_qc runs.")
    _validate_pgta_sample_count(target=target, selected_count=_pgta_selected_count(run))


def _ensure_airflow_writable(path: Path) -> None:
    path.chmod(0o775)


def _set_sample_status(*, session: Session, analysis_id: str, status: str) -> None:
    samples = session.scalars(select(Sample).where(Sample.analysis_id == analysis_id)).all()
    for sample in samples:
        sample.status = status


def _dag_conf(run: AnalysisRun) -> dict:
    conf = {
        "analysis_id": run.analysis_id,
        "pipeline": run.pipeline_name,
        "mode": run.mode,
        "sample_sheet_path": run.sample_sheet_path,
        "workdir": run.workdir,
        "email_to": run.email_to,
        "params": run.params_json or {},
    }
    if run.pipeline_name == "wes_qsub":
        conf["backend_event_url"] = WES_BACKEND_EVENT_URL
    return conf


def _write_manifest(path: Path, selected_samples: list[FastqCandidate]) -> None:
    lines = ["sample_id\tR1\tR2\tsource_dir"]
    for item in selected_samples:
        lines.append(f"{item.sample_id}\t{item.r1}\t{item.r2}\t{item.source_dir}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_wes_manifest(path: Path) -> None:
    lines = ["sample_id\tinput"]
    for sample_id, input_path in WES_MOCK_SAMPLES.items():
        lines.append(f"{sample_id}\t{input_path}")
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


def _write_wes_request(
    path: Path,
    *,
    analysis_id: str,
    project_name: str,
    target: str,
    email_to: str | None,
    note: str | None,
) -> None:
    payload = {
        "analysis_id": analysis_id,
        "pipeline": "wes_qsub",
        "project_name": project_name,
        "target": target,
        "samples": WES_MOCK_SAMPLES,
        "email_to": email_to,
        "note": note,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _new_analysis_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3).upper()
    return f"PGTA_{now}_{suffix}"


def _new_wes_analysis_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3).upper()
    return f"WES_{now}_{suffix}"


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
