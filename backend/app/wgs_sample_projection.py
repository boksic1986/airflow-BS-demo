from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.models import AnalysisRun, RuleState, Sample
from app.wgs_artifact_selection import select_batch_qcstat
from app.wgs_run_projection import load_wgs_runtime_binding, resolve_bound_wgs_batch_root
from app.wgs_timing_service import phase_for_rule


TERMINAL_SUCCESS = {"success", "succeeded", "complete", "completed"}
ACTIVE = {"running", "started", "submitted", "pending"}
QC_FIELDS = {
    "Clean_Q30%": "clean_q30_percent",
    "Mapped_Reads%": "mapped_reads_percent",
    "Average_Depth": "average_depth",
    ">=20X": "coverage_20x_percent",
    "contamination": "contamination",
}


def get_wgs_sample_projection(*, session, settings, run: AnalysisRun) -> dict[str, list[dict[str, Any]]]:
    """Return the only public WGS sample projections.

    The manifest is read from the frozen batch with a strict allow-list.  The
    analysis matrix is derived server-side from Sample, RuleState and the
    controlled QCstat artifact so React never has to reinterpret runtime state.
    """
    batch_root = _batch_root(settings=settings, run=run)
    manifest = _read_manifest(batch_root / "sampleinfo.tsv") if batch_root else []
    qc = _read_qc(batch_root) if batch_root else {}
    samples = session.scalars(
        select(Sample).where(Sample.analysis_id == run.analysis_id).order_by(Sample.sample_id)
    ).all()
    rules = session.scalars(
        select(RuleState).where(
            RuleState.analysis_id == run.analysis_id,
            RuleState.attempt == int(run.attempt or 1),
        )
    ).all()
    by_sample: dict[str, list[RuleState]] = {}
    for rule in rules:
        if rule.sample_id:
            by_sample.setdefault(str(rule.sample_id), []).append(rule)
    expected_total = max((len(rows) for rows in by_sample.values()), default=0)
    items = [
        _matrix_row(
            sample=sample,
            run=run,
            rules=_matching_rules(sample=sample, by_sample=by_sample),
            expected_total=expected_total,
            qc=qc,
        )
        for sample in samples
    ]
    return {"manifest": manifest, "items": items}


def _batch_root(*, settings, run: AnalysisRun) -> Path | None:
    try:
        binding = load_wgs_runtime_binding(
            request_root=settings.wgs_runtime_request_root,
            analysis_id=run.analysis_id,
            attempt=int(run.attempt or 1),
        )
        return resolve_bound_wgs_batch_root(
            binding=binding,
            node_analysis_root=settings.wgs_results_host_root,
            local_analysis_root=settings.host_results_root,
        )
    except (KeyError, OSError, TypeError, ValueError):
        return None


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.is_file() or path.is_symlink():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for source in csv.DictReader(handle, delimiter="\t"):
            sample_id = _text(source.get("样本编号"))
            if not sample_id:
                continue
            rows.append(
                {
                    "sample_id": sample_id,
                    "data_id": _text(source.get("数据编号")),
                    "sample_type": _text(source.get("样本类型")),
                    "family_id": _text(source.get("家系编号")),
                    "family_relation": _text(source.get("家系关系")),
                    "received_date": _text(source.get("收样日期")),
                    "estimated_report_date": _text(source.get("预计报告日期")),
                }
            )
    return rows


def _read_qc(batch_root: Path) -> dict[str, dict[str, Any]]:
    qc_path = select_batch_qcstat(batch_root)
    if qc_path is None:
        return {}
    output: dict[str, dict[str, Any]] = {}
    with qc_path.open(encoding="utf-8-sig", newline="") as handle:
        for source in csv.DictReader(handle, delimiter="\t"):
            identifiers = {_text(source.get("Sample_ID")), _text(source.get("Name"))}
            identifiers.discard(None)
            status = _qc_status(_text(source.get("是否通过质控")))
            metrics = {
                public: _text(source.get(column))
                for column, public in QC_FIELDS.items()
                if _text(source.get(column)) is not None
            }
            value = {"status": status, "metrics": metrics}
            for identifier in identifiers:
                output[str(identifier)] = value
    return output


def _matching_rules(*, sample: Sample, by_sample: dict[str, list[RuleState]]) -> list[RuleState]:
    metadata = dict(sample.metadata_json or {})
    aliases = {
        sample.sample_id,
        str(metadata.get("data_id") or ""),
        str(metadata.get("data_id") or "").removesuffix("-WGS"),
        sample.sample_id.removesuffix("-WGS"),
    }
    rows: dict[str, RuleState] = {}
    for alias in aliases:
        for row in by_sample.get(alias, []):
            rows[row.rule_instance_id] = row
    return list(rows.values())


def _matrix_row(*, sample: Sample, run: AnalysisRun, rules: list[RuleState], expected_total: int,
                qc: dict[str, dict[str, Any]]) -> dict[str, Any]:
    metadata = dict(sample.metadata_json or {})
    ordered = sorted(
        rules,
        key=lambda row: (
            row.sequence if row.sequence is not None else 9_223_372_036_854_775_807,
            row.rule_name,
        ),
    )
    failed = next((row for row in reversed(ordered) if row.status.lower() in {"failed", "error"}), None)
    running = next((row for row in reversed(ordered) if row.status.lower() in ACTIVE), None)
    current = failed or running or (ordered[-1] if ordered else None)
    completed = sum(row.status.lower() in TERMINAL_SUCCESS for row in ordered)
    total = max(expected_total, len(ordered))
    progress = round(completed * 100 / total) if total else None
    started = [row.started_at for row in ordered if row.started_at]
    ended = [row.ended_at for row in ordered if row.ended_at]
    elapsed = None
    if started:
        end = max(ended) if ended and not running else datetime.now(timezone.utc)
        start = min(_aware(value) for value in started)
        elapsed = max(0, int((_aware(end) - start).total_seconds()))
    status = (
        "failed" if failed else "running" if running else
        "success" if ordered and completed == len(ordered) else sample.status
    )
    data_id = str(metadata.get("data_id") or sample.sample_id)
    qc_value = qc.get(sample.sample_id) or qc.get(data_id) or qc.get(data_id.removesuffix("-WGS")) or {}
    current_stage = (
        (current.phase or phase_for_rule(current.rule_name, pipeline_name="wgs"))
        if current
        else _text(run.current_stage)
    )
    return {
        "sample_id": sample.sample_id,
        "data_id": data_id,
        "family_id": sample.family_id,
        "family_relation": _text(metadata.get("family_relation")),
        "current_stage": current_stage,
        "current_rule": current.rule_name if current else None,
        "completed_rules": completed,
        "total_rules": total,
        "progress_percent": progress,
        "status": status,
        "elapsed_seconds": elapsed,
        "qc_status": qc_value.get("status", sample.qc_status or "unknown"),
        "qc_metrics": dict(qc_value.get("metrics") or {}),
    }


def _qc_status(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return "unknown"
    if normalized in {"通过", "是", "pass", "passed", "true", "yes"}:
        return "pass"
    if normalized in {"不通过", "否", "fail", "failed", "false", "no"}:
        return "fail"
    return "warn"


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
