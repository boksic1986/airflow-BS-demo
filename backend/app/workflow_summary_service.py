from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, SnakemakeRuleEvent
from app.workflow_phases import phase_for_rule


WORKFLOW_TEMPLATES = {
    "pgta": [
        ("mapping", "Mapping"),
        ("metadata", "Metadata"),
        ("cnv_qc", "CNV QC"),
        ("cnv_prediction", "CNV prediction"),
    ],
    "nipt_docker": [
        ("input_qc", "Input QC"),
        ("mapping", "Mapping"),
        ("cnv", "CNV"),
        ("t21_classifier", "T21 classifier"),
        ("fetal_fraction", "Fetal fraction"),
        ("final_qc", "Final QC"),
    ],
}

FAILED = {"failed", "fail", "error"}
RUNNING = {"planned", "submitted", "running", "started"}
COMPLETED = {"success", "skipped"}


def workflow_summaries_by_run(*, session: Session, runs: list[AnalysisRun]) -> dict[str, list[dict[str, object]]]:
    analysis_ids = [run.analysis_id for run in runs]
    events = list(
        session.scalars(
            select(SnakemakeRuleEvent).where(SnakemakeRuleEvent.analysis_id.in_(analysis_ids))
        ).all()
    ) if analysis_ids else []
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for item in events:
        grouped[item.analysis_id][phase_for_rule(item.rule)].append(str(item.status or "unknown").lower())

    result: dict[str, list[dict[str, object]]] = {}
    for run in runs:
        stages = []
        for key, label in WORKFLOW_TEMPLATES.get(run.pipeline_name, []):
            statuses = grouped[run.analysis_id].get(label, [])
            stages.append(
                {
                    "key": key,
                    "label": label,
                    "status": _stage_status(statuses),
                    "completed_jobs": sum(status in COMPLETED for status in statuses),
                    "total_jobs": len(statuses),
                }
            )
        result[run.analysis_id] = stages
    return result


def _stage_status(statuses: list[str]) -> str:
    if any(status in FAILED for status in statuses):
        return "failed"
    if any(status in RUNNING for status in statuses):
        return "running"
    if statuses and all(status in COMPLETED for status in statuses):
        return "success"
    return "pending"
