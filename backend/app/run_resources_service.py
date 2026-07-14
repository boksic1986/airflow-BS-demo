from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisRun


def get_run_resource_summary(*, session: Session, analysis_id: str, settings) -> dict[str, object] | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    if run is None or not run.workdir:
        return None
    workdir = Path(run.workdir).resolve()
    allowed_roots = {
        Path(settings.container_shared_root).resolve(),
        Path(getattr(settings, "host_results_root", settings.container_shared_root)).resolve(),
    }
    if not any(workdir == root or workdir.is_relative_to(root) for root in allowed_roots):
        return None
    summary_path = workdir / "reports" / "resource_summary.json"
    if not summary_path.is_file():
        return None
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return {
        "analysis_id": analysis_id,
        "pipeline": run.pipeline_name,
        **payload,
        "summary_artifact": "reports/resource_summary.json",
    }
