from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import re


RUN_LABEL_RE = re.compile(r"^wgs401-[0-9a-f]{16}$")


class WgsRuleStatusHandler(logging.Handler):
    def __init__(
        self,
        *,
        analysis_id: str,
        attempt: int,
        pipeline_release_id: str,
        run_label: str,
        events_path: Path,
        role: str,
        stream_id: str,
    ) -> None:
        super().__init__()
        if RUN_LABEL_RE.fullmatch(run_label) is None:
            raise ValueError("invalid wgs401 run label")
        if role not in {"master", "worker"}:
            raise ValueError("role must be master or worker")
        self.analysis_id = analysis_id
        self.attempt = int(attempt)
        self.pipeline_release_id = pipeline_release_id
        self.run_label = run_label
        self.events_path = Path(events_path)
        self.role = role
        self.stream_id = stream_id

    def emit(self, record: logging.LogRecord) -> None:
        event = str(getattr(record, "event", "log")).lower()
        rule_name = str(getattr(record, "rule", None) or getattr(record, "rule_name", None) or "unknown")
        wildcards = dict(getattr(record, "wildcards", {}) or {})
        job_id = str(getattr(record, "job_id", None) or getattr(record, "jobid", None) or "")
        material = json.dumps(
            {"job_id": job_id, "rule_name": rule_name, "wildcards": wildcards},
            sort_keys=True,
            separators=(",", ":"),
        )
        payload = {
            "schema_version": "1",
            "event_id": hashlib.sha256(
                f"{self.run_label}\0{event}\0{material}".encode()
            ).hexdigest(),
            "analysis_id": self.analysis_id,
            "attempt": self.attempt,
            "pipeline_release_id": self.pipeline_release_id,
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "run_label": self.run_label,
            "role": self.role,
            "stream_id": self.stream_id,
            "rule_instance_id": hashlib.sha256(material.encode()).hexdigest()[:16],
            "rule_name": rule_name,
            "wildcards": wildcards,
            "sample_id": str(wildcards.get("sample") or wildcards.get("sample_id") or "") or None,
            "layer": getattr(record, "layer", None),
            "job_id": job_id or None,
            "snakemake_jobid": job_id or None,
            "event": event,
            "status": _status(event),
            "message": record.getMessage(),
        }
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            handle.flush()


def _status(event: str) -> str:
    if event == "job_started":
        return "running"
    if event == "job_finished":
        return "success"
    if event in {"job_error", "group_error", "error"}:
        return "failed"
    if event in {"job_info", "rule_planned"}:
        return "planned"
    return "unknown_interrupted"
