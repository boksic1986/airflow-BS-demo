from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import List

import pandas as pd


def generate_keyword_file(
    script_path: Path | str,
    hp2gene_file: Path | str,
    hpo_file: Path | str,
    output_path: Path | str,
    python_executable: Path | str = sys.executable,
    display_dir: Path | str | None = None,
) -> None:
    script = Path(script_path)
    hp2gene = Path(hp2gene_file)
    hpo = Path(hpo_file)
    output = Path(output_path)
    for source in (script, hp2gene, hpo):
        if not source.exists():
            raise FileNotFoundError(f"关键词文件生成依赖不存在: {source}")
    json_path = output.parent / ".hpo.mongo.json"
    completed = subprocess.run(
        [
            str(python_executable),
            str(script),
            "-i",
            str(hp2gene),
            "-hpo",
            str(hpo),
            "-json",
            str(json_path),
            "-o",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    display = str(Path(display_dir)) if display_dir is not None else str(output.parent)
    for content, stream in ((completed.stdout, sys.stdout), (completed.stderr, sys.stderr)):
        if content:
            rendered = content.replace(str(output.parent), display)
            print(rendered, end="" if rendered.endswith("\n") else "\n", file=stream)
    completed.check_returncode()
    if not output.is_file():
        raise RuntimeError(f"关键词脚本未生成输出文件: {output}")
    if json_path.exists():
        json_path.unlink()


def normalize_keyword(value: str) -> str:
    return str(value).strip().casefold().replace("hpo.hpo", "hpo")


def split_english_keywords(value: object) -> List[str]:
    text = "" if value is None else str(value).strip()
    if text in {"", ".", "None", "nan"}:
        return []
    return [item.strip() for item in re.split(r"[|,]", text) if item.strip()]


def validate_english_keywords(
    sampleinfo: pd.DataFrame,
    keyword_file: Path | str,
    report_path: Path | str,
) -> pd.DataFrame:
    dictionary = pd.read_csv(keyword_file, sep="\t", dtype=str, keep_default_na=False).fillna("")
    if "配置关键词" not in dictionary.columns:
        raise ValueError(f"关键词文件缺少“配置关键词”列: {keyword_file}")
    available = {normalize_keyword(value) for value in dictionary["配置关键词"] if str(value).strip()}
    rows = []
    for _, sample in sampleinfo.iterrows():
        for keyword in split_english_keywords(sample.get("英文关键词", "")):
            normalized = normalize_keyword(keyword)
            matched = normalized in available
            rows.append(
                {
                    "样本编号": sample.get("样本编号", ""),
                    "订单编号": sample.get("订单编号", ""),
                    "英文关键词": keyword,
                    "标准化关键词": normalized,
                    "匹配状态": "matched" if matched else "unmatched",
                }
            )
            if not matched:
                print(
                    f"提示：样本 {sample.get('样本编号', '')}（订单 {sample.get('订单编号', '')}）"
                    f"英文关键词未在词库中匹配：{keyword}"
                )
    report = pd.DataFrame(rows, columns=["样本编号", "订单编号", "英文关键词", "标准化关键词", "匹配状态"])
    report.to_csv(report_path, sep="\t", index=False, encoding="utf-8")
    return report
