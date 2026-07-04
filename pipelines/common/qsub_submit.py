from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping
from urllib.error import URLError
from urllib.request import Request, urlopen


PROPERTY_PREFIX = "# properties = "
DEFAULT_EVENTS_RELATIVE_PATH = Path("logs/events/snakemake_events.jsonl")
SAMPLE_KEYS = ("sample_id", "sample", "sample_name")


@dataclass(frozen=True)
class SubmissionContext:
    jobscript: Path
    mode: str
    analysis_id: str
    workdir: Path
    rule: str
    sample_id: str | None
    wildcards: dict[str, Any]
    snakemake_jobid: str
    qsub_jobid: str
    stdout_path: Path
    stderr_path: Path
    events_path: Path
    backend_event_url: str | None
    threads: int
    resources: dict[str, Any]


def build_submission_context(jobscript: str | Path, *, environ: Mapping[str, str] | None = None) -> SubmissionContext:
    environ = environ or os.environ
    jobscript_path = Path(jobscript).resolve()
    properties = read_job_properties(jobscript_path)
    params = _dict_value(properties.get("params"))
    wildcards = _dict_value(properties.get("wildcards"))
    resources = _dict_value(properties.get("resources"))

    analysis_id = _required_value(
        environ.get("AIRFLOW_DEMO_ANALYSIS_ID") or params.get("analysis_id"),
        "analysis_id",
    )
    workdir = Path(_required_value(environ.get("AIRFLOW_DEMO_WORKDIR") or params.get("workdir"), "workdir")).resolve()
    rule = _required_value(properties.get("rule"), "rule")
    sample_id = _sample_id_from_wildcards(wildcards)
    snakemake_jobid = str(properties.get("jobid") or environ.get("AIRFLOW_DEMO_SNAKEMAKE_JOBID") or "unknown")
    safe_sample = sample_id or "project"
    qsub_jobid = _mock_job_id(analysis_id=analysis_id, snakemake_jobid=snakemake_jobid, rule=rule, sample_id=safe_sample)
    events_path = Path(environ.get("AIRFLOW_DEMO_EVENTS_PATH") or workdir / DEFAULT_EVENTS_RELATIVE_PATH).resolve()

    return SubmissionContext(
        jobscript=jobscript_path,
        mode=str(environ.get("AIRFLOW_DEMO_QSUB_MODE") or "mock").lower(),
        analysis_id=analysis_id,
        workdir=workdir,
        rule=rule,
        sample_id=sample_id,
        wildcards=wildcards,
        snakemake_jobid=snakemake_jobid,
        qsub_jobid=qsub_jobid,
        stdout_path=workdir / "logs" / "qsub" / f"{rule}.{safe_sample}.o",
        stderr_path=workdir / "logs" / "qsub" / f"{rule}.{safe_sample}.e",
        events_path=events_path,
        backend_event_url=_optional_text(environ.get("AIRFLOW_DEMO_BACKEND_EVENT_URL") or params.get("backend_event_url")),
        threads=int(properties.get("threads") or 1),
        resources=resources,
    )


def read_job_properties(jobscript: Path) -> dict[str, Any]:
    for line in jobscript.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(PROPERTY_PREFIX):
            return json.loads(line[len(PROPERTY_PREFIX) :])
    raise ValueError(f"Snakemake jobscript properties were not found: {jobscript}")


def run_mock_submission(context: SubmissionContext) -> int:
    emit_event(context, status="submitted", event_name="qsub_submitted")
    context.stdout_path.parent.mkdir(parents=True, exist_ok=True)
    context.stderr_path.parent.mkdir(parents=True, exist_ok=True)
    with context.stdout_path.open("w", encoding="utf-8") as stdout, context.stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(["bash", str(context.jobscript)], cwd=str(context.workdir), stdout=stdout, stderr=stderr, check=False)
    final_status = "success" if completed.returncode == 0 else "failed"
    emit_event(
        context,
        status=final_status,
        event_name=f"qsub_{final_status}",
        return_code=completed.returncode,
    )
    return completed.returncode


def emit_event(
    context: SubmissionContext,
    *,
    status: str,
    event_name: str = "qsub_submitted",
    return_code: int | None = None,
    message: str | None = None,
) -> None:
    event = {
        "analysis_id": context.analysis_id,
        "event": event_name,
        "rule": context.rule,
        "sample_id": context.sample_id,
        "wildcards": context.wildcards,
        "snakemake_jobid": context.snakemake_jobid,
        "qsub_jobid": context.qsub_jobid,
        "status": status,
        "stdout_path": str(context.stdout_path),
        "stderr_path": str(context.stderr_path),
        "message": message,
        "return_code": return_code,
        "resources": {**context.resources, "threads": context.threads},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _append_jsonl(context.events_path, event)
    if context.backend_event_url:
        _post_event_or_fallback(context, event)


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        print("Usage: qsub_submit.py <snakemake-jobscript>", file=sys.stderr)
        return 2
    context = build_submission_context(argv[0])
    if context.mode != "mock":
        raise RuntimeError("Only AIRFLOW_DEMO_QSUB_MODE=mock is supported until qsub is verified on the target server.")
    exit_code = run_mock_submission(context)
    print(context.qsub_jobid)
    return exit_code


def _post_event_or_fallback(context: SubmissionContext, event: dict[str, Any]) -> None:
    request = Request(
        context.backend_event_url,
        data=json.dumps(event).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            response.read()
    except (OSError, URLError) as exc:
        fallback_event = {
            **event,
            "event": "backend_post_error",
            "status": "backend_post_error",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _append_jsonl(context.events_path, fallback_event)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _dict_value(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _required_value(value: Any, label: str) -> str:
    text = _optional_text(value)
    if text is None:
        raise ValueError(f"Missing required qsub submission value: {label}")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sample_id_from_wildcards(wildcards: Mapping[str, Any]) -> str | None:
    for key in SAMPLE_KEYS:
        if wildcards.get(key) is not None:
            return _optional_text(wildcards[key])
    return None


def _mock_job_id(*, analysis_id: str, snakemake_jobid: str, rule: str, sample_id: str) -> str:
    raw = f"MOCK-{analysis_id}-{snakemake_jobid}-{rule}-{sample_id}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)[:128]


if __name__ == "__main__":
    raise SystemExit(main())
