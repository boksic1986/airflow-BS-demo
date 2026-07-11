from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, QcMetric


PIPELINE_METRICS = {
    "pgta": ("clean_read_pairs", "mapping_rate", "mapped_reads", "estimated_depth_x", "cnv_qc_decision"),
    "nipt_docker": ("read_count", "Q30", "unique_mapping_rate", "fetal_fraction"),
}


def qc_highlights_by_run(*, session: Session, runs: list[AnalysisRun]) -> dict[str, list[dict[str, Any]]]:
    run_ids = [run.analysis_id for run in runs]
    if not run_ids:
        return {}
    metrics_by_run: dict[str, dict[str, list[tuple[float | None, str | None, str]]]] = {}
    rows = session.execute(
        select(
            QcMetric.analysis_id,
            QcMetric.metric_name,
            QcMetric.metric_numeric,
            QcMetric.metric_value,
            QcMetric.status,
        ).where(QcMetric.analysis_id.in_(run_ids))
    ).all()
    for analysis_id, name, numeric, value, status in rows:
        metrics_by_run.setdefault(analysis_id, {}).setdefault(name, []).append(
            (float(numeric) if numeric is not None else None, value, str(status or "unknown"))
        )

    run_by_id = {run.analysis_id: run for run in runs}
    result: dict[str, list[dict[str, Any]]] = {}
    for analysis_id, metrics in metrics_by_run.items():
        items = []
        for key in PIPELINE_METRICS.get(run_by_id[analysis_id].pipeline_name, ()):
            values = metrics.get(key) or []
            if not values:
                continue
            numeric_values = [value for value, _, _ in values if value is not None]
            display_value: float | str | None
            if numeric_values:
                display_value = (
                    sum(numeric_values)
                    if key in {"clean_read_pairs", "mapped_reads", "read_count"}
                    else sum(numeric_values) / len(numeric_values)
                )
            else:
                display_values = sorted({str(value) for _, value, _ in values if value})
                display_value = display_values[0] if len(display_values) == 1 else ", ".join(display_values)
            items.append(
                {
                    "key": key,
                    "value": display_value,
                    "unit": _unit(key),
                    "status": aggregate_qc_status([status for _, _, status in values]),
                }
            )
        result[analysis_id] = items
    return result


def aggregate_qc_status(statuses: list[str | None]) -> str:
    normalized = [str(value or "unknown").strip().lower() for value in statuses]
    if any(value in {"failed", "fail", "error"} for value in normalized):
        return "fail"
    if "warn" in normalized or "warning" in normalized:
        return "warn"
    if normalized and all(value in {"pass", "success"} for value in normalized):
        return "pass"
    return "unknown"


def _unit(key: str) -> str:
    if key in {"Q30", "unique_mapping_rate"}:
        return "percent"
    if key in {"mapping_rate", "fetal_fraction"}:
        return "fraction"
    if key == "estimated_depth_x":
        return "x"
    if key == "cnv_qc_decision":
        return ""
    return "reads"
