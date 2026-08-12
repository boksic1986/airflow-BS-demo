from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from sqlalchemy import select

from app.models import AnalysisRun, KubernetesWorkload, RuleEventRaw, RuleState


TERMINAL_RULE_EVENTS = {"job_finished": "success", "job_error": "failed"}


def ingest_evidence_once(*, session_factory, evidence_root: Path) -> dict[str, int]:
    ingested = 0
    for identity in evidence_root.glob("*/attempt-*/analysis.json"):
        try:
            metadata = json.loads(identity.read_text(encoding="utf-8"))
            analysis_id = str(metadata["analysis_id"])
            attempt = int(metadata.get("attempt", 1))
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
        attempt_root = identity.parent
        with session_factory() as session:
            if session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)) is None:
                continue
            for path in sorted((attempt_root / "rule-status" / "raw").glob("*.jsonl")):
                ingested += _ingest_rule_file(session, analysis_id, attempt, path)
            for path in sorted((attempt_root / "raw").glob("pod*.jsonl")):
                ingested += _ingest_pod_file(session, analysis_id, attempt, path)
            session.commit()
    return {"events_ingested": ingested}


def _ingest_rule_file(session, analysis_id: str, attempt: int, path: Path) -> int:
    count = 0
    for line_number, payload in _json_lines(path):
        event_id = str(payload.get("event_id") or _fallback_id(path, line_number, payload))
        exists = session.scalar(select(RuleEventRaw.id).where(RuleEventRaw.analysis_id == analysis_id, RuleEventRaw.attempt == attempt, RuleEventRaw.event_id == event_id))
        if exists is not None:
            continue
        event_type = str(payload.get("event") or "unknown")
        session.add(RuleEventRaw(analysis_id=analysis_id, attempt=attempt, event_id=event_id, event_type=event_type, payload_json=payload))
        instance_id = str(payload.get("rule_instance_id") or "")
        if instance_id:
            state = session.scalar(select(RuleState).where(RuleState.analysis_id == analysis_id, RuleState.attempt == attempt, RuleState.rule_instance_id == instance_id))
            if state is None:
                state = RuleState(analysis_id=analysis_id, attempt=attempt, rule_instance_id=instance_id, rule_name=str(payload.get("rule_name") or "unknown"), layer=payload.get("layer"), status="planned")
                session.add(state)
            if event_type == "job_started":
                state.status = "running"
                state.started_at = _event_time(payload)
            elif event_type in TERMINAL_RULE_EVENTS:
                state.status = TERMINAL_RULE_EVENTS[event_type]
                state.ended_at = _event_time(payload)
            state.updated_at = datetime.now(timezone.utc)
        session.flush()
        count += 1
    return count


def _ingest_pod_file(session, analysis_id: str, attempt: int, path: Path) -> int:
    count = 0
    for line_number, payload in _json_lines(path):
        pod_hash = str(payload.get("pod_hash") or "")
        if not pod_hash:
            continue
        event_id = str(payload.get("event_id") or _fallback_id(path, line_number, payload))
        row = session.scalar(select(KubernetesWorkload).where(KubernetesWorkload.analysis_id == analysis_id, KubernetesWorkload.attempt == attempt, KubernetesWorkload.pod_hash == pod_hash))
        if row is not None and row.event_id == event_id:
            continue
        if row is None:
            row = KubernetesWorkload(analysis_id=analysis_id, attempt=attempt, event_id=event_id, pod_hash=pod_hash, phase=str(payload.get("phase") or "Unknown"))
            session.add(row)
        row.event_id = event_id
        row.job_name = payload.get("job_name")
        row.phase = str(payload.get("phase") or "Unknown")
        row.reason = payload.get("reason")
        row.exit_code = payload.get("exit_code")
        row.image_id = payload.get("image_id")
        row.resources_json = payload.get("resources") or {}
        row.evidence_path = str(path)
        row.updated_at = datetime.now(timezone.utc)
        session.flush()
        count += 1
    return count


def _json_lines(path: Path):
    try:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if line.strip():
                    try:
                        yield number, json.loads(line)
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return


def _fallback_id(path: Path, line_number: int, payload: dict) -> str:
    material = f"{path.name}\0{line_number}\0{json.dumps(payload, sort_keys=True)}".encode()
    return hashlib.sha256(material).hexdigest()


def _event_time(payload: dict) -> datetime:
    try:
        return datetime.fromtimestamp(float(payload.get("timestamp")), tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return datetime.now(timezone.utc)

