from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, QcMetric, Sample


QC_STATUSES = ("pass", "warn", "fail", "unknown")
WES_QC_RELATIVE_PATH = Path("reports/qc_summary.tsv")
PGTA_BASELINE_QC_RELATIVE_PATH = Path("qc/baseline/baseline_qc_summary.tsv")
PGTA_BASELINE_METRIC_COLUMNS = (
    "mapped_fragments",
    "zero_bin_fraction",
    "bin_cv",
    "pearson_r",
    "median_abs_z",
    "gc_signal_slope",
)


@dataclass(frozen=True)
class ParsedQcMetric:
    sample_id: str | None
    metric_name: str
    metric_value: str | None
    metric_numeric: Decimal | None
    threshold: str | None
    status: str
    source_file: str


def import_wes_qc_metrics(*, session: Session, run: AnalysisRun, settings) -> None:
    if run.pipeline_name != "wes_qsub":
        return
    qc_path = _safe_qc_path(run, settings, relative_path=WES_QC_RELATIVE_PATH)
    if not qc_path.is_file():
        return

    metrics = parse_qc_summary_tsv(qc_path)
    _replace_qc_metrics(session=session, run=run, metrics=metrics)


def import_pgta_baseline_qc_metrics(*, session: Session, run: AnalysisRun, settings) -> None:
    if run.pipeline_name != "pgta" or (run.params_json or {}).get("target") != "baseline_qc":
        return
    qc_path = _safe_qc_path(run, settings, relative_path=PGTA_BASELINE_QC_RELATIVE_PATH)
    if not qc_path.is_file():
        return

    metrics = parse_pgta_baseline_qc_summary_tsv(qc_path)
    _replace_qc_metrics(session=session, run=run, metrics=metrics)


def import_run_qc_metrics(*, session: Session, run: AnalysisRun, settings) -> None:
    import_wes_qc_metrics(session=session, run=run, settings=settings)
    import_pgta_baseline_qc_metrics(session=session, run=run, settings=settings)


def _replace_qc_metrics(*, session: Session, run: AnalysisRun, metrics: list[ParsedQcMetric]) -> None:
    session.execute(delete(QcMetric).where(QcMetric.analysis_id == run.analysis_id))
    for metric in metrics:
        session.add(
            QcMetric(
                analysis_id=run.analysis_id,
                sample_id=metric.sample_id,
                metric_name=metric.metric_name,
                metric_value=metric.metric_value,
                metric_numeric=metric.metric_numeric,
                threshold=metric.threshold,
                status=metric.status,
                source_file=metric.source_file,
            )
        )
    _refresh_sample_qc_status(session=session, analysis_id=run.analysis_id, metrics=metrics)


def list_run_qc(*, session: Session, analysis_id: str) -> dict[str, Any] | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    if run is None:
        return None

    metrics = session.scalars(
        select(QcMetric)
        .where(QcMetric.analysis_id == analysis_id)
        .order_by(QcMetric.sample_id, QcMetric.metric_name)
    ).all()
    summary = {status: 0 for status in QC_STATUSES}
    items = []
    for metric in metrics:
        status = _normalize_status(metric.status)
        summary[status] += 1
        items.append(
            {
                "sample_id": metric.sample_id,
                "metric_name": metric.metric_name,
                "metric_value": metric.metric_value,
                "metric_numeric": float(metric.metric_numeric) if metric.metric_numeric is not None else None,
                "threshold": metric.threshold,
                "status": status,
                "source_file": metric.source_file,
            }
        )
    return {"summary": summary, "items": items}


def parse_qc_summary_tsv(path: Path) -> list[ParsedQcMetric]:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"sample_id", "metric_name", "metric_value", "metric_numeric", "threshold", "status"}
        if set(reader.fieldnames or []) != required:
            raise ValueError(f"Unsupported QC summary header in {path}")
        for row in reader:
            metric_name = str(row.get("metric_name") or "").strip()
            if not metric_name:
                continue
            rows.append(
                ParsedQcMetric(
                    sample_id=_blank_to_none(row.get("sample_id")),
                    metric_name=metric_name,
                    metric_value=_blank_to_none(row.get("metric_value")),
                    metric_numeric=_parse_decimal(row.get("metric_numeric")),
                    threshold=_blank_to_none(row.get("threshold")),
                    status=_normalize_status(row.get("status")),
                    source_file=str(path),
                )
            )
    return rows


def parse_pgta_baseline_qc_summary_tsv(path: Path) -> list[ParsedQcMetric]:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"sample_id", "qc_decision", *PGTA_BASELINE_METRIC_COLUMNS}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Unsupported PGT-A baseline QC header in {path}; missing: {','.join(sorted(missing))}")
        for row in reader:
            sample_id = _blank_to_none(row.get("sample_id"))
            if not sample_id:
                continue
            decision_status = _normalize_pgta_decision(row.get("qc_decision"))
            rows.append(
                ParsedQcMetric(
                    sample_id=sample_id,
                    metric_name="baseline_qc_decision",
                    metric_value=_blank_to_none(row.get("qc_decision")),
                    metric_numeric=None,
                    threshold="PASS",
                    status=decision_status,
                    source_file=str(path),
                )
            )
            for column in PGTA_BASELINE_METRIC_COLUMNS:
                rows.append(
                    ParsedQcMetric(
                        sample_id=sample_id,
                        metric_name=column,
                        metric_value=_blank_to_none(row.get(column)),
                        metric_numeric=_parse_decimal(row.get(column)),
                        threshold=None,
                        status=decision_status,
                        source_file=str(path),
                    )
                )
    return rows


def _refresh_sample_qc_status(*, session: Session, analysis_id: str, metrics: list[ParsedQcMetric]) -> None:
    statuses_by_sample: dict[str, list[str]] = {}
    for metric in metrics:
        if metric.sample_id:
            statuses_by_sample.setdefault(metric.sample_id, []).append(metric.status)

    samples = session.scalars(select(Sample).where(Sample.analysis_id == analysis_id)).all()
    for sample in samples:
        sample.qc_status = _aggregate_status(statuses_by_sample.get(sample.sample_id, []))


def _aggregate_status(statuses: list[str]) -> str:
    if not statuses:
        return "unknown"
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    if "unknown" in statuses:
        return "unknown"
    return "pass"


def _safe_qc_path(run: AnalysisRun, settings, *, relative_path: Path) -> Path:
    shared_root = Path(settings.container_shared_root).resolve()
    workdir = Path(run.workdir).resolve()
    path = (workdir / relative_path).resolve()
    if not _is_relative_to(workdir, shared_root) or not _is_relative_to(path, workdir):
        raise ValueError(f"QC path is outside shared run root: {path}")
    return path


def _normalize_status(value: str | None) -> str:
    status = str(value or "unknown").strip().lower()
    return status if status in QC_STATUSES else "unknown"


def _normalize_pgta_decision(value: str | None) -> str:
    decision = str(value or "").strip().upper()
    if decision == "PASS":
        return "pass"
    if decision == "WARN":
        return "warn"
    if decision == "FAIL":
        return "fail"
    return "unknown"


def _blank_to_none(value: str | None) -> str | None:
    value = str(value or "").strip()
    return value or None


def _parse_decimal(value: str | None) -> Decimal | None:
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _is_relative_to(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)
