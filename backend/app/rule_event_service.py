from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, SnakemakeRuleEvent, utc_now


START_STATUSES = {"planned", "submitted", "running", "started"}
END_STATUSES = {"success", "failed", "skipped", "error"}


def record_snakemake_event(*, session: Session, event: Mapping[str, Any]) -> bool:
    analysis_id = str(event["analysis_id"])
    run_exists = session.scalar(select(AnalysisRun.analysis_id).where(AnalysisRun.analysis_id == analysis_id))
    if run_exists is None:
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
    session.commit()
    return True


def list_snakemake_rule_events(*, session: Session, analysis_id: str) -> list[dict[str, Any]] | None:
    run_exists = session.scalar(select(AnalysisRun.analysis_id).where(AnalysisRun.analysis_id == analysis_id))
    if run_exists is None:
        return None

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
    return [_rule_event_payload(row) for row in rows]


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


def _rule_event_payload(row: SnakemakeRuleEvent) -> dict[str, Any]:
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
    }


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
