from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, SnakemakeRuleEvent, utc_now
from app.workflow_phases import phase_for_rule, summarize_rule_events


START_STATUSES = {"planned", "submitted", "running", "started"}
END_STATUSES = {"success", "failed", "skipped", "error", "canceled", "cancelled", "terminated"}
RULE_PROGRESS = {
    "mapping": 15,
    "fastp_bwa": 35,
    "collect_mapping_qc": 45,
    "metadata": 50,
    "collect_run_metadata": 50,
    "cnv_qc": 60,
    "wisecondorx_convert_for_cnv": 65,
    "wisecondorx_gender_for_predict": 72,
    "wisecondorx_qc_for_predict": 80,
    "cnv_predict": 85,
    "wisecondorx_predict_cnv": 95,
    "aggregate_pgta_prediction_status": 98,
    "baseline_qc": 90,
}


def record_snakemake_event(*, session: Session, event: Mapping[str, Any]) -> bool:
    analysis_id = str(event["analysis_id"])
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    if run is None:
        return False

    rule = str(event["rule"])
    sample_id = _normalize_optional_string(event.get("sample_id")) or _sample_id_from_wildcards(event.get("wildcards") or {})
    snakemake_jobid = _normalize_optional_string(event.get("snakemake_jobid"))
    timestamp = event.get("timestamp") if isinstance(event.get("timestamp"), datetime) else utc_now()

    rule_event = _find_existing_event(
        session=session,
        analysis_id=analysis_id,
        rule=rule,
        sample_id=sample_id,
        snakemake_jobid=snakemake_jobid,
    )
    if rule_event is None:
        rule_event = SnakemakeRuleEvent(
            analysis_id=analysis_id,
            rule=rule,
            sample_id=sample_id,
            snakemake_jobid=snakemake_jobid,
            status=str(event["status"]),
            wildcards_json=dict(event.get("wildcards") or {}),
            updated_at=timestamp,
        )
        session.add(rule_event)

    _apply_event(rule_event, event=event, timestamp=timestamp)
    _update_run_progress(run=run, rule_event=rule_event, status=str(event["status"]), timestamp=timestamp)
    session.commit()
    return True


def list_snakemake_rule_events(
    *,
    session: Session,
    analysis_id: str,
    status: str | None = None,
    rule: str | None = None,
    sample_id: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    pipeline_name: str | None = None,
    pipeline_stage: str | None = None,
) -> list[dict[str, Any]] | None:
    if pipeline_name is None or (pipeline_name == "wgs" and pipeline_stage is None):
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        if run is None:
            return None
        pipeline_name = run.pipeline_name
        if pipeline_name == "wgs":
            params = run.params_json or {}
            pipeline_stage = str(params.get("wgs_stage") or params.get("stage") or "full")

    rows = session.scalars(
        select(SnakemakeRuleEvent)
        .where(SnakemakeRuleEvent.analysis_id == analysis_id)
        .order_by(
            SnakemakeRuleEvent.start_time,
            SnakemakeRuleEvent.rule,
            SnakemakeRuleEvent.sample_id,
            SnakemakeRuleEvent.snakemake_jobid,
        )
    ).all()
    items = [
        _rule_event_payload(row, pipeline_name=pipeline_name, pipeline_stage=pipeline_stage)
        for row in rows
    ]
    if status:
        items = [item for item in items if str(item.get("status") or "").lower() == status.lower()]
    if rule:
        items = [item for item in items if str(item.get("rule") or "") == rule]
    if sample_id:
        items = [item for item in items if str(item.get("sample_id") or "") == sample_id]
    if limit is not None:
        return items[offset : offset + limit]
    return items[offset:]


def get_snakemake_rule_events_page(
    *,
    session: Session,
    analysis_id: str,
    status: str | None,
    rule: str | None,
    sample_id: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any] | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    if run is None:
        return None
    all_items = list_snakemake_rule_events(
        session=session,
        analysis_id=analysis_id,
        pipeline_name=run.pipeline_name,
        pipeline_stage=_wgs_stage(run),
    )
    if all_items is None:
        return None
    filtered = all_items
    if status:
        filtered = [item for item in filtered if str(item.get("status") or "").lower() == status.lower()]
    if rule:
        filtered = [item for item in filtered if str(item.get("rule") or "") == rule]
    if sample_id:
        filtered = [item for item in filtered if str(item.get("sample_id") or "") == sample_id]
    return {
        "items": filtered[offset : offset + limit],
        "total": len(filtered),
        "limit": limit,
        "offset": offset,
        "summary": summarize_rule_events(
            all_items,
            pipeline_name=run.pipeline_name,
            pipeline_stage=_wgs_stage(run),
        ),
    }


def import_snakemake_events_jsonl(*, session: Session, analysis_id: str, events_path: str | Path) -> int:
    path = Path(events_path)
    if not path.is_file():
        return 0

    imported = 0
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw_line.strip():
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if not event.get("rule") or not event.get("status"):
            continue
        event = dict(event)
        event["analysis_id"] = analysis_id
        if isinstance(event.get("timestamp"), str):
            parsed = _parse_timestamp(str(event["timestamp"]))
            if parsed is not None:
                event["timestamp"] = parsed
        if record_snakemake_event(session=session, event=event):
            imported += 1
    return imported


def cancel_incomplete_rule_events(
    *, session: Session, analysis_id: str, parent_status: str, timestamp: datetime
) -> int:
    normalized_parent = str(parent_status or "").lower()
    if normalized_parent not in {"failed", "terminated"}:
        return 0
    rows = session.scalars(
        select(SnakemakeRuleEvent).where(
            SnakemakeRuleEvent.analysis_id == analysis_id,
            func.lower(SnakemakeRuleEvent.status).in_(START_STATUSES),
        )
    ).all()
    for row in rows:
        row.status = "canceled"
        row.end_time = row.end_time or timestamp
        row.updated_at = timestamp
        row.message = f"Canceled because parent workflow {normalized_parent}."
    return len(rows)


def _find_existing_event(
    *,
    session: Session,
    analysis_id: str,
    rule: str,
    sample_id: str | None,
    snakemake_jobid: str | None,
) -> SnakemakeRuleEvent | None:
    query = select(SnakemakeRuleEvent).where(
        SnakemakeRuleEvent.analysis_id == analysis_id,
        SnakemakeRuleEvent.rule == rule,
    )
    if sample_id is None:
        query = query.where(SnakemakeRuleEvent.sample_id.is_(None))
    else:
        query = query.where(SnakemakeRuleEvent.sample_id == sample_id)
    if snakemake_jobid is None:
        query = query.where(SnakemakeRuleEvent.snakemake_jobid.is_(None))
    else:
        query = query.where(SnakemakeRuleEvent.snakemake_jobid == snakemake_jobid)
    return session.scalar(query)


def _apply_event(rule_event: SnakemakeRuleEvent, *, event: Mapping[str, Any], timestamp: datetime) -> None:
    status = str(event["status"])
    rule_event.status = status
    rule_event.updated_at = timestamp

    if event.get("wildcards"):
        rule_event.wildcards_json = dict(event["wildcards"])
    for attr in ("qsub_jobid", "stdout_path", "stderr_path", "message"):
        value = _normalize_optional_string(event.get(attr))
        if value is not None:
            setattr(rule_event, attr, value)
    if event.get("return_code") is not None:
        rule_event.return_code = int(event["return_code"])
    if event.get("resources") is not None:
        rule_event.resources_json = dict(event["resources"])

    normalized_status = status.lower()
    if normalized_status in START_STATUSES and rule_event.start_time is None:
        rule_event.start_time = timestamp
    if normalized_status in END_STATUSES:
        rule_event.end_time = timestamp


def _rule_event_payload(
    row: SnakemakeRuleEvent,
    *,
    pipeline_name: str | None = None,
    pipeline_stage: str | None = None,
) -> dict[str, Any]:
    return {
        "rule": row.rule,
        "sample_id": row.sample_id,
        "status": row.status,
        "snakemake_jobid": row.snakemake_jobid,
        "qsub_jobid": row.qsub_jobid,
        "stdout_path": row.stdout_path,
        "stderr_path": row.stderr_path,
        "start_time": _isoformat(row.start_time),
        "end_time": _isoformat(row.end_time),
        "message": row.message,
        "return_code": row.return_code,
        "wildcards": row.wildcards_json or {},
        "phase": phase_for_rule(
            row.rule,
            pipeline_name=pipeline_name,
            pipeline_stage=pipeline_stage,
        ),
    }


def _wgs_stage(run: AnalysisRun) -> str | None:
    if run.pipeline_name != "wgs":
        return None
    params = run.params_json or {}
    return str(params.get("wgs_stage") or params.get("stage") or "full")


def _update_run_progress(*, run: AnalysisRun, rule_event: SnakemakeRuleEvent, status: str, timestamp: datetime) -> None:
    rule = rule_event.rule
    weight = RULE_PROGRESS.get(rule, int(run.progress_percent or 10))
    run.progress_percent = max(int(run.progress_percent or 0), weight)
    run.current_stage = rule
    run.progress_updated_at = timestamp
    normalized_status = str(status).lower()
    if normalized_status in {"failed", "error"}:
        run.status = "failed"
    if (
        normalized_status == "success"
        and run.pipeline_finished_at is None
        and _is_pipeline_completion_event(run=run, rule_event=rule_event)
    ):
        run.pipeline_finished_at = timestamp


def _is_pipeline_completion_event(*, run: AnalysisRun, rule_event: SnakemakeRuleEvent) -> bool:
    if rule_event.sample_id is not None:
        return False
    params = run.params_json or {}
    if run.pipeline_name == "pgta":
        target = str(params.get("target") or "metadata")
        return rule_event.rule == {
            "predict": "cnv_predict",
            "baseline_qc": "baseline_qc",
            "metadata": "metadata",
            "dryrun_cnv": "dryrun_cnv",
        }.get(target)
    if run.pipeline_name == "nipt_docker":
        run_mode = str(params.get("run_mode") or "mount_smoke")
        marker = "all" if run_mode == "full_run" else "nipt_mount_smoke"
        return rule_event.rule == marker
    return False


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sample_id_from_wildcards(wildcards: Mapping[str, Any]) -> str | None:
    for key in ("sample_id", "sample", "sample_name"):
        if wildcards.get(key) is not None:
            return _normalize_optional_string(wildcards[key])
    return None


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
