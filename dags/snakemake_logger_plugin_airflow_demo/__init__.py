from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any
import urllib.request

from snakemake_interface_logger_plugins.base import LogHandlerBase
from snakemake_interface_logger_plugins.common import LogEvent
from snakemake_interface_logger_plugins.settings import LogHandlerSettingsBase


@dataclass
class LogHandlerSettings(LogHandlerSettingsBase):
    analysis_id: str = field(default="", metadata={"help": "airflow-demo analysis id."})
    workdir: Path = field(default=Path("."), metadata={"help": "Run workdir."})
    events_path: Path = field(
        default=Path("logs/events/snakemake_events.jsonl"),
        metadata={"help": "JSONL file where Snakemake events are written."},
    )
    backend_event_url: str = field(
        default="",
        metadata={"help": "Reserved backend event receiver URL for future use."},
    )
    post_timeout_seconds: float = field(
        default=2.0,
        metadata={"help": "Reserved backend POST timeout for future use."},
    )


class LogHandler(LogHandlerBase):
    def __post_init__(self) -> None:
        settings = self.settings or LogHandlerSettings()
        self.analysis_id = str(settings.analysis_id or "")
        self.workdir = Path(settings.workdir)
        events_path = Path(settings.events_path)
        if not events_path.is_absolute():
            events_path = self.workdir / events_path
        self.events_path = events_path
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self.backend_event_url = str(settings.backend_event_url or "").strip()
        self.post_timeout_seconds = float(settings.post_timeout_seconds)
        self.job_context: dict[str, dict[str, Any]] = {}
        self.baseFilename = str(self.events_path)

    def emit(self, record: logging.LogRecord) -> None:
        payload = self._record_to_payload(record)
        self._append_payload(payload)
        self._post_backend_event(payload)

    def _append_payload(self, payload: dict[str, Any]) -> None:
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")

    def _post_backend_event(self, payload: dict[str, Any]) -> None:
        if not self.backend_event_url or not payload.get("rule"):
            return
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        request = urllib.request.Request(
            self.backend_event_url,
            data=body,
            headers={"Content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.post_timeout_seconds) as response:
                response.read()
        except Exception as exc:
            self._append_payload(
                {
                    "analysis_id": self.analysis_id,
                    "event": "backend_post_error",
                    "status": "warning",
                    "rule": payload.get("rule"),
                    "sample_id": payload.get("sample_id"),
                    "wildcards": payload.get("wildcards") or {},
                    "snakemake_jobid": payload.get("snakemake_jobid"),
                    "qsub_jobid": payload.get("qsub_jobid"),
                    "stdout_path": payload.get("stdout_path"),
                    "stderr_path": payload.get("stderr_path"),
                    "message": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    @property
    def writes_to_stream(self) -> bool:
        return False

    @property
    def writes_to_file(self) -> bool:
        return True

    @property
    def has_filter(self) -> bool:
        return False

    @property
    def has_formatter(self) -> bool:
        return False

    @property
    def needs_rulegraph(self) -> bool:
        return False

    def _record_to_payload(self, record: logging.LogRecord) -> dict[str, Any]:
        event = _event_name(getattr(record, "event", None))
        wildcards = _extract_wildcards(record)
        rule = _extract_rule(record)
        payload = {
            "analysis_id": self.analysis_id,
            "event": event,
            "status": _status_for_event(event),
            "rule": rule,
            "sample_id": _extract_sample_id(record, wildcards),
            "wildcards": wildcards,
            "snakemake_jobid": _string_or_none(_first_present(record, "job_id", "jobid", "snakemake_jobid")),
            "qsub_jobid": _string_or_none(getattr(record, "qsub_jobid", None)),
            "stdout_path": _string_or_none(getattr(record, "stdout_path", None)),
            "stderr_path": _string_or_none(getattr(record, "stderr_path", None)),
            "message": record.getMessage(),
            "return_code": _int_or_none(_first_present(record, "return_code", "exit_code")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._fill_payload_from_job_context(payload)
        self._remember_job_context(payload)
        return payload

    def _fill_payload_from_job_context(self, payload: dict[str, Any]) -> None:
        jobid = payload.get("snakemake_jobid")
        if not jobid:
            return
        context = self.job_context.get(str(jobid))
        if not context:
            return
        for key in ("rule", "sample_id", "qsub_jobid", "stdout_path", "stderr_path"):
            if not payload.get(key) and context.get(key):
                payload[key] = context[key]
        if not payload.get("wildcards") and context.get("wildcards"):
            payload["wildcards"] = context["wildcards"]

    def _remember_job_context(self, payload: dict[str, Any]) -> None:
        jobid = payload.get("snakemake_jobid")
        if not jobid or not payload.get("rule"):
            return
        existing = self.job_context.setdefault(str(jobid), {})
        for key in ("rule", "sample_id", "qsub_jobid", "stdout_path", "stderr_path"):
            if payload.get(key):
                existing[key] = payload[key]
        if payload.get("wildcards"):
            existing["wildcards"] = payload["wildcards"]


def _event_name(event: Any) -> str:
    if event is None:
        return "log"
    value = getattr(event, "value", None)
    return str(value or event).lower()


def _status_for_event(event: str) -> str:
    if event == LogEvent.JOB_STARTED.value:
        return "running"
    if event == LogEvent.JOB_FINISHED.value:
        return "success"
    if event in {LogEvent.JOB_ERROR.value, LogEvent.GROUP_ERROR.value, LogEvent.ERROR.value}:
        return "failed"
    if event == LogEvent.WORKFLOW_STARTED.value:
        return "started"
    if event == LogEvent.PROGRESS.value:
        return "progress"
    return "info"


def _extract_rule(record: logging.LogRecord) -> str | None:
    value = _first_present(record, "rule", "rule_name")
    if value:
        return str(value)
    job = getattr(record, "job", None)
    if job is not None:
        rule = getattr(job, "rule", None)
        name = getattr(rule, "name", None)
        return str(name or rule) if rule is not None else None
    return None


def _extract_wildcards(record: logging.LogRecord) -> dict[str, Any]:
    wildcards = _first_present(record, "wildcards", "wildcards_dict")
    job = getattr(record, "job", None)
    if wildcards is None and job is not None:
        wildcards = _first_present(job, "wildcards_dict", "wildcards")
    return _mapping_from_object(wildcards)


def _extract_sample_id(record: logging.LogRecord, wildcards: dict[str, Any]) -> str | None:
    sample_id = _first_present(record, "sample_id", "sample")
    if sample_id:
        return str(sample_id)
    for key in ("sample_id", "sample", "sample_name"):
        if key in wildcards and wildcards[key] is not None:
            return str(wildcards[key])
    return None


def _mapping_from_object(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    if hasattr(value, "items"):
        return dict(value.items())
    data = {}
    for key in dir(value):
        if key.startswith("_"):
            continue
        item = getattr(value, key)
        if not callable(item):
            data[key] = item
    return data


def _first_present(obj: Any, *names: str) -> Any:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
