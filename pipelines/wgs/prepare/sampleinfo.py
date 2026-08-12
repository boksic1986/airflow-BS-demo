from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import pandas as pd

from .config_loader import version_code
from .metadata import WGS_ITEM_NAMES, first_nonempty, record_order_key, record_sample_id


SAMPLEINFO_COLUMNS = [
    "上机批次", "分析批次", "上传批次", "重新实验/暂停分析", "注意事项", "家系人数", "projectId", "订单编号",
    "样本条码", "家系编号", "家系名", "姓名", "样本编号", "数据编号", "样本类型", "是否患者", "家系关系",
    "性别", "出生日期", "收样日期", "预计报告日期", "送检医院", "送检医生", "项目编号", "检测项目",
    "检测方法", "临床主诉", "中文关键词", "英文关键词", "医院编号", "医院条码号",
    "analysisTaskId", "taskSampleId", "version",
]

BLANK_VALUES = {"", ".", "None", "nan"}


def clean_text(value: Any, default: str = ".") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    text = str(value).strip()
    if not text or text == "nan":
        return default
    return re.sub(r"[\t\n\r\v\f]", "", text)


def format_date(value: Any) -> str:
    text = first_nonempty(value)
    if not text:
        return "."
    if re.fullmatch(r"\d{11,}(?:\.\d+)?", text):
        parsed = pd.to_datetime(float(text), unit="ms", errors="coerce")
    else:
        parsed = pd.to_datetime(text, errors="coerce")
    return text if pd.isna(parsed) else parsed.strftime("%Y-%m-%d")


def expected_report_key(row: Mapping[str, Any]) -> Tuple[int, str]:
    value = first_nonempty(row.get("expectedReportDate"))
    if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        number = float(value)
        parsed = pd.to_datetime(number, unit="ms" if abs(number) >= 10_000_000_000 else "s", errors="coerce")
    else:
        parsed = pd.to_datetime(value, errors="coerce")
    timestamp = -1 if pd.isna(parsed) else int(parsed.value)
    return timestamp, first_nonempty(row.get("orderCode"), record_order_key(dict(row)))


def _record_identity(row: Mapping[str, Any]) -> Tuple[str, str]:
    return record_sample_id(dict(row)), record_order_key(dict(row))


def _unique_records(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        key = _record_identity(row)
        if key not in seen:
            output.append(dict(row))
            seen.add(key)
    return output


def _suffix_map(provider, rows: Sequence[Dict[str, Any]], reanalysis: bool) -> Dict[Tuple[str, str], str]:
    output: Dict[Tuple[str, str], str] = {}
    by_sample: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_sample[record_sample_id(row)].append(row)
    for sample_id, selected_rows in by_sample.items():
        all_records = sorted(_unique_records(provider.records_for_sample(sample_id)), key=expected_report_key)
        rank_by_order = {record_order_key(record): rank for rank, record in enumerate(all_records)}
        if reanalysis:
            suffix = "" if len(all_records) <= 1 else f"R{len(all_records) - 1}"
            for row in selected_rows:
                output[_record_identity(row)] = suffix
        else:
            for row in selected_rows:
                rank = rank_by_order.get(record_order_key(row), 0)
                output[_record_identity(row)] = "" if rank == 0 else f"R{rank}"
        by_date: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for record in all_records:
            by_date[expected_report_key(record)[0]].append(record)
        for timestamp, tied in by_date.items():
            if timestamp >= 0 and len(tied) > 1:
                assignments = []
                for record in sorted(tied, key=expected_report_key):
                    rank = rank_by_order[record_order_key(record)]
                    assignments.append(f"{first_nonempty(record.get('orderCode'))}={'无后缀' if rank == 0 else f'R{rank}'}")
                print(f"提示：样本 {sample_id} 的多个订单 expectedReportDate 相同，按订单编号升序分配：" + ",".join(assignments))
    return output


def _merge_keywords(rows: Sequence[Dict[str, Any]], field: str) -> str:
    values: List[str] = []
    for row in rows:
        value = clean_text(row.get(field), "")
        if value in BLANK_VALUES:
            continue
        for item in re.split(r"[|,]", value):
            keyword = item.strip()
            if keyword and keyword not in values:
                values.append(keyword)
    return "|".join(values) or "."


def _affected(row: Mapping[str, Any]) -> str:
    if clean_text(row.get("relationship"), "") == "先证者":
        return "是"
    truthy = str(row.get("issick", "")).strip().lower() in {"1", "true", "yes", "y", "是"}
    return "是" if truthy or "也是患者" in str(row.get("addnote", "")) else "否"


def _note(row: Mapping[str, Any]) -> str:
    values = [clean_text(row.get("ordernote"), ""), clean_text(row.get("analysenote"), "")]
    values = [value for value in values if value not in BLANK_VALUES]
    return ";".join(values) or "."


def _row_to_sampleinfo(
    row: Dict[str, Any],
    analysis_batch: str,
    analysis_id: str,
    sequence_row: Mapping[str, Any],
    family_rows: Sequence[Dict[str, Any]],
    template_version: str,
) -> Dict[str, str]:
    proband = next((item for item in family_rows if clean_text(item.get("relationship"), "") == "先证者"), None)
    family_name = (clean_text((proband or row).get("username"), "") + "家系") if clean_text((proband or row).get("username"), "") else "."
    chinese = clean_text(row.get("mainkeyword"), "")
    english = clean_text(row.get("mainkeywordEN"), "")
    if clean_text(row.get("relationship"), "") == "先证者" or not chinese:
        chinese = _merge_keywords(family_rows, "mainkeyword")
        english = _merge_keywords(family_rows, "mainkeywordEN")
    item_code = clean_text(row.get("itemCode"), "")
    values = [
        clean_text(sequence_row.get("batchNo"), ""), analysis_batch, ".", ".", _note(row), str(len(family_rows)),
        clean_text(row.get("projectId"), ""), clean_text(row.get("orderCode"), ""), clean_text(row.get("orderBarCode"), ""),
        clean_text(row.get("familyCode"), ""), family_name, clean_text(row.get("username"), ""), analysis_id,
        f"{analysis_id}-WGS", clean_text(row.get("sampleType"), ""), _affected(row), clean_text(row.get("relationship"), "other"),
        clean_text(row.get("gender"), ""), format_date(row.get("bornDate")), format_date(row.get("sampleAcceptDate")),
        format_date(row.get("expectedReportDate")), clean_text(row.get("sendHospital"), ""), clean_text(row.get("sendDoctor"), ""),
        item_code, clean_text(row.get("itemName"), WGS_ITEM_NAMES.get(item_code, item_code)), "WGS",
        clean_text(row.get("clinicalDiag"), ""), chinese or ".", english or ".", clean_text(row.get("healthNum"), "None"),
        clean_text(row.get("hospitalBarCode"), "None"), clean_text(row.get("analysisTaskId"), ""),
        clean_text(row.get("taskSampleId"), ""), version_code(template_version),
    ]
    return dict(zip(SAMPLEINFO_COLUMNS, values))


def generate_sampleinfo(
    sample_ids: Sequence[str],
    provider,
    analysis_batch: str,
    template_version: str,
    sequence_rows: pd.DataFrame | None = None,
    reanalysis: bool = False,
) -> pd.DataFrame:
    selected_orders: List[str] = []
    for sample_id in sample_ids:
        records = sorted(_unique_records(provider.records_for_sample(sample_id)), key=expected_report_key)
        if not records:
            print(f"提示：Mongo/HTTP 中未找到有效 WGS 样本记录，跳过 {sample_id}")
            continue
        chosen = [records[-1]] if reanalysis else records
        for row in chosen:
            order_key = record_order_key(row)
            if order_key and order_key not in selected_orders:
                selected_orders.append(order_key)
    if not selected_orders:
        return pd.DataFrame(columns=SAMPLEINFO_COLUMNS)

    selected_rows: List[Dict[str, Any]] = []
    for order_key in selected_orders:
        family_rows = provider.records_for_order(order_key)
        if not family_rows:
            print(f"提示：未找到订单/任务 {order_key} 的有效家系记录")
            continue
        selected_rows.extend(family_rows)
    selected_rows = _unique_records(selected_rows)
    selected_rows = provider.enrich(selected_rows)
    suffixes = _suffix_map(provider, selected_rows, reanalysis)

    sequence_lookup: Dict[str, Dict[str, Any]] = {}
    if sequence_rows is not None and not sequence_rows.empty:
        for _, sequence_row in sequence_rows.iterrows():
            sequence_lookup.setdefault(str(sequence_row.get("sampleId", "")), sequence_row.to_dict())

    rows_by_order: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in selected_rows:
        rows_by_order[record_order_key(row)].append(row)
    output: List[Dict[str, str]] = []
    for order_key in selected_orders:
        family_rows = rows_by_order.get(order_key, [])
        for row in sorted(
            family_rows,
            key=lambda item: (
                clean_text(item.get("relationship"), "") != "先证者",
                clean_text(item.get("relationship"), ""),
                record_sample_id(item),
            ),
        ):
            original_id = record_sample_id(row)
            suffix = suffixes.get(_record_identity(row), "")
            analysis_id = original_id + suffix
            output.append(
                _row_to_sampleinfo(
                    row,
                    analysis_batch,
                    analysis_id,
                    sequence_lookup.get(original_id, {}),
                    family_rows,
                    template_version,
                )
            )
    frame = pd.DataFrame(output, columns=SAMPLEINFO_COLUMNS).fillna("")
    for _, row in frame.iterrows():
        missing = [column for column in ("中文关键词", "英文关键词") if str(row[column]).strip() in BLANK_VALUES]
        if missing:
            print(f"提示：样本 {row['样本编号']}（订单 {row['订单编号']}）关键词为空：{','.join(missing)}")
    return frame


def write_sampleinfo(frame: pd.DataFrame, path: Path | str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, sep="\t", index=False, encoding="utf-8")
