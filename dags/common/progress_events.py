from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
import urllib.request


RULE_RE = re.compile(r"^rule\s+([A-Za-z0-9_.-]+):")
JOBID_RE = re.compile(r"^\s*jobid:\s*([^\s]+)")
WILDCARDS_RE = re.compile(r"^\s*wildcards:\s*(.+)")
FINISHED_RE = re.compile(r"Finished jobid:\s*([^\s]+)(?:.*Rule:\s*([A-Za-z0-9_.-]+))?")
ERROR_RE = re.compile(r"Error in rule\s+([A-Za-z0-9_.-]+)")


def emit_progress_event(
    *,
    analysis_id: str,
    workdir: str | Path,
    event: str,
    rule: str,
    status: str,
    backend_event_url: str | None = None,
    sample_id: str | None = None,
    wildcards: dict[str, Any] | None = None,
    snakemake_jobid: str | None = None,
    qsub_jobid: str | None = None,
    stdout_path: str | Path | None = None,
    stderr_path: str | Path | None = None,
    message: str | None = None,
    return_code: int | None = None,
    resources: dict[str, Any] | None = None,
) -> Path:
    events_path = Path(workdir) / "logs" / "events" / "snakemake_events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "analysis_id": analysis_id,
        "event": event,
        "rule": rule,
        "sample_id": sample_id,
        "wildcards": wildcards or {},
        "snakemake_jobid": snakemake_jobid,
        "qsub_jobid": qsub_jobid,
        "status": status,
        "stdout_path": str(stdout_path) if stdout_path else None,
        "stderr_path": str(stderr_path) if stderr_path else None,
        "message": message,
        "return_code": return_code,
        "resources": resources,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _append_jsonl(events_path, payload)
    if backend_event_url:
        try:
            request = urllib.request.Request(
                backend_event_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5):
                pass
        except Exception as exc:  # noqa: BLE001 - progress POST must never fail the workflow.
            _append_jsonl(
                events_path,
                {
                    "analysis_id": analysis_id,
                    "event": "backend_post_error",
                    "status": "warning",
                    "rule": rule,
                    "sample_id": sample_id,
                    "message": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
    return events_path


class SnakemakeProgressParser:
    def __init__(
        self,
        *,
        analysis_id: str,
        workdir: str | Path,
        backend_event_url: str | None,
        stdout_path: str | Path | None = None,
        stderr_path: str | Path | None = None,
    ) -> None:
        self.analysis_id = analysis_id
        self.workdir = Path(workdir)
        self.backend_event_url = backend_event_url
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self._current: dict[str, Any] | None = None
        self._jobs: dict[str, dict[str, Any]] = {}
        self._started_jobids: set[str] = set()
        self._failed_jobids: set[str] = set()

    def process_line(self, line: str) -> None:
        rule_match = RULE_RE.search(line)
        if rule_match:
            self._flush_running()
            self._current = {"rule": rule_match.group(1), "wildcards": {}}
            return

        if self._current is not None:
            jobid_match = JOBID_RE.search(line)
            if jobid_match:
                self._current["snakemake_jobid"] = jobid_match.group(1)
                return
            wildcards_match = WILDCARDS_RE.search(line)
            if wildcards_match:
                self._current["wildcards"] = _parse_wildcards(wildcards_match.group(1))
                return
            if not line.strip():
                self._flush_running()
                return

        finished_match = FINISHED_RE.search(line)
        if finished_match:
            jobid = finished_match.group(1)
            context = self._jobs.get(jobid, {})
            rule = finished_match.group(2) or context.get("rule")
            if rule:
                emit_progress_event(
                    analysis_id=self.analysis_id,
                    workdir=self.workdir,
                    backend_event_url=self.backend_event_url,
                    event="job_finished",
                    rule=str(rule),
                    status="success",
                    sample_id=context.get("sample_id"),
                    wildcards=dict(context.get("wildcards") or {}),
                    snakemake_jobid=jobid,
                    stdout_path=self.stdout_path,
                    stderr_path=self.stderr_path,
                    return_code=0,
                )
            return

        error_match = ERROR_RE.search(line)
        if error_match:
            rule = error_match.group(1)
            context = _last_context_for_rule(self._jobs, rule)
            jobid = context.get("snakemake_jobid")
            if jobid:
                self._failed_jobids.add(str(jobid))
            emit_progress_event(
                analysis_id=self.analysis_id,
                workdir=self.workdir,
                backend_event_url=self.backend_event_url,
                event="job_failed",
                rule=rule,
                status="failed",
                sample_id=context.get("sample_id"),
                wildcards=dict(context.get("wildcards") or {}),
                snakemake_jobid=str(jobid) if jobid else None,
                stdout_path=self.stdout_path,
                stderr_path=self.stderr_path,
                message=line.strip(),
                return_code=1,
            )

    def finish(self) -> None:
        self._flush_running()

    def _flush_running(self) -> None:
        if not self._current:
            return
        rule = str(self._current.get("rule") or "")
        jobid = str(self._current.get("snakemake_jobid") or "")
        wildcards = dict(self._current.get("wildcards") or {})
        sample_id = _sample_id_from_wildcards(wildcards)
        context = {
            "rule": rule,
            "sample_id": sample_id,
            "wildcards": wildcards,
            "snakemake_jobid": jobid or None,
        }
        if jobid:
            self._jobs[jobid] = context
        if rule and jobid not in self._started_jobids:
            emit_progress_event(
                analysis_id=self.analysis_id,
                workdir=self.workdir,
                backend_event_url=self.backend_event_url,
                event="job_started",
                rule=rule,
                status="running",
                sample_id=sample_id,
                wildcards=wildcards,
                snakemake_jobid=jobid or None,
                stdout_path=self.stdout_path,
                stderr_path=self.stderr_path,
            )
            self._started_jobids.add(jobid)
        self._current = None


def parse_snakemake_output_for_events(
    *,
    analysis_id: str,
    workdir: str | Path,
    backend_event_url: str | None,
    stdout_text: str,
    stderr_text: str,
    stdout_path: str | Path,
    stderr_path: str | Path,
) -> None:
    parser = SnakemakeProgressParser(
        analysis_id=analysis_id,
        workdir=workdir,
        backend_event_url=backend_event_url,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    for line in stdout_text.splitlines(keepends=True):
        parser.process_line(line)
    for line in stderr_text.splitlines(keepends=True):
        parser.process_line(line)
    parser.finish()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _parse_wildcards(raw: str) -> dict[str, str]:
    wildcards: dict[str, str] = {}
    for part in raw.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        wildcards[key.strip()] = value.strip()
    return wildcards


def _sample_id_from_wildcards(wildcards: dict[str, Any]) -> str | None:
    for key in ("sample_id", "sample", "sample_name"):
        if wildcards.get(key):
            return str(wildcards[key])
    return None


def _last_context_for_rule(jobs: dict[str, dict[str, Any]], rule: str) -> dict[str, Any]:
    for jobid, context in reversed(list(jobs.items())):
        if context.get("rule") == rule:
            return {**context, "snakemake_jobid": jobid}
    return {}
