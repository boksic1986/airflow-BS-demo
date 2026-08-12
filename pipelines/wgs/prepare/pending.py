from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence

import pandas as pd

from .sampleinfo import SAMPLEINFO_COLUMNS
from .samplelists import SamplelistRepository, locate_fastq, raw_sample_id, read_basecount


PENDING_EXTRA_COLUMNS = ["pending_reason", "pending_at", "source_analysis_batch", "source_sampleinfo"]


@dataclass
class LinkSpec:
    sample_id: str
    read: str
    source: str
    destination_name: str


@dataclass
class AnalysisSelection:
    kept: pd.DataFrame
    pending: pd.DataFrame
    links: List[LinkSpec]
    warnings: List[str]


def _blank(value: object) -> bool:
    return str(value).strip() in {"", ".", "None", "nan"}


def order_group_key(row: pd.Series | Dict[str, object]) -> str:
    task_id = str(row.get("analysisTaskId", "")).strip()
    if not _blank(task_id):
        return "task:" + task_id
    order_id = str(row.get("订单编号", "")).strip()
    if not _blank(order_id):
        return "order:" + order_id
    return "sample:" + str(row.get("样本编号", "")).strip()


def _minimum_base(target: float, config: Dict[str, object]) -> float:
    boundary = float(config.get("low_target_boundary", 100))
    return float(config.get("low_minimum", 55) if target < boundary else config.get("high_minimum", 115))


def select_analysis_samples(
    sampleinfo: pd.DataFrame,
    repository: SamplelistRepository,
    fastq_root: str,
    basecount_dir: str,
    ready_flag_name: str,
    data_check_config: Dict[str, object],
    skip_data_check: bool = False,
    source_sampleinfo: str = "",
) -> AnalysisSelection:
    blockers: Dict[int, str] = {}
    row_links: Dict[int, List[LinkSpec]] = {}
    warnings: List[str] = []
    for index, row in sampleinfo.iterrows():
        analysis_id = str(row.get("样本编号", "")).strip()
        original_id = raw_sample_id(analysis_id)
        sequencing_batch = str(row.get("上机批次", "")).strip()
        sample_row = repository.find(original_id, sequencing_batch)
        if sample_row is None:
            blockers[index] = f"Samplelist中未定位到样本 {original_id}（批次 {sequencing_batch or '自动查找'}）"
            continue
        location = locate_fastq(sample_row, original_id, fastq_root, basecount_dir, ready_flag_name)
        if not location.ready:
            blockers[index] = f"FASTQ ready标志缺失：样本 {original_id}，上机批次 {sample_row.get('batchNo', '')}"
            continue

        skip_for_suffix = bool(re.search(r"-S\d+$", original_id))
        if not skip_data_check and not skip_for_suffix:
            try:
                target = float(sample_row.get("targetBase", ""))
            except (TypeError, ValueError):
                blockers[index] = f"targetBase无法解析：样本 {original_id}，值 {sample_row.get('targetBase', '')!r}"
                continue
            actual, base_error = read_basecount(location.basecount_file, f"{original_id}-WGS")
            if base_error:
                blockers[index] = f"{base_error}：样本 {original_id}，文件 {location.basecount_file}"
                continue
            minimum = _minimum_base(target, data_check_config)
            if actual is None or actual < minimum:
                blockers[index] = f"数据量不足：样本 {original_id}，实际 {actual}，最低 {minimum}"
                continue

        specs: List[LinkSpec] = []
        for read, source in (("R1", location.r1), ("R2", location.r2)):
            if not source or not Path(source).is_file():
                warnings.append(f"提示：样本 {analysis_id} 的 {read} 文件缺失，仅保留sampleinfo：{source or '未定位'}")
                continue
            specs.append(LinkSpec(analysis_id, read, source, f"{row['数据编号']}.{read}.fq.gz"))
        row_links[index] = specs

    blocked_groups = {order_group_key(sampleinfo.loc[index]) for index in blockers}
    kept_mask = ~sampleinfo.apply(lambda row: order_group_key(row) in blocked_groups, axis=1)
    kept = sampleinfo[kept_mask].copy().reset_index(drop=True)
    pending_rows: List[Dict[str, object]] = []
    if blocked_groups:
        group_reasons: Dict[str, List[str]] = {}
        for index, reason in blockers.items():
            group_reasons.setdefault(order_group_key(sampleinfo.loc[index]), []).append(reason)
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        for _, row in sampleinfo[~kept_mask].iterrows():
            group_key = order_group_key(row)
            item = row.to_dict()
            item.update(
                {
                    "pending_reason": "; ".join(group_reasons[group_key]),
                    "pending_at": now,
                    "source_analysis_batch": str(row.get("分析批次", "")),
                    "source_sampleinfo": source_sampleinfo,
                }
            )
            pending_rows.append(item)

    kept_indices = set(sampleinfo[kept_mask].index)
    links = [spec for index, specs in row_links.items() if index in kept_indices for spec in specs]
    pending = pd.DataFrame(pending_rows, columns=SAMPLEINFO_COLUMNS + PENDING_EXTRA_COLUMNS).fillna("")
    return AnalysisSelection(kept=kept, pending=pending, links=links, warnings=warnings)


def create_raw_links(raw_dir: Path | str, specs: Sequence[LinkSpec]) -> List[str]:
    target_dir = Path(raw_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    warnings: List[str] = []
    for spec in specs:
        destination = target_dir / spec.destination_name
        try:
            if os.path.lexists(destination):
                if destination.is_symlink() and os.readlink(destination) == spec.source:
                    continue
                raise FileExistsError(f"目标已存在且不是期望软链接: {destination}")
            destination.symlink_to(spec.source)
        except OSError as exc:
            warnings.append(
                f"提示：样本 {spec.sample_id} 创建 {spec.read} 软链接失败，仅保留sampleinfo："
                f"{spec.source} -> {destination}；{exc}"
            )
    return warnings


def update_pending(path: Path | str, pending: pd.DataFrame, resolved_sample_ids: Sequence[str]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    columns = SAMPLEINFO_COLUMNS + PENDING_EXTRA_COLUMNS
    if target.is_file() and target.stat().st_size:
        old = pd.read_csv(target, sep="\t", dtype=str, keep_default_na=False).fillna("")
        for column in columns:
            if column not in old.columns:
                old[column] = ""
        old = old[columns]
    else:
        old = pd.DataFrame(columns=columns)
    resolved = set(resolved_sample_ids)
    if resolved:
        old = old[~old["样本编号"].isin(resolved)]
    combined = pd.concat([old, pending], ignore_index=True).fillna("")
    if not combined.empty:
        combined = combined.drop_duplicates(subset=["样本编号", "pending_reason"], keep="last")
    fd, temporary_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        combined.to_csv(temporary, sep="\t", index=False, encoding="utf-8")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
