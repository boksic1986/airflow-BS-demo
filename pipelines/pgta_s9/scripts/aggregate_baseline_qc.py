#!/biosoftware/miniconda/envs/snakemake_env/bin/python
import argparse
import csv
from pathlib import Path

from pipeline_logging import setup_logger


def load_qc_rows(qc_tsvs):
    rows = []
    for qc_tsv in qc_tsvs:
        qc_path = Path(qc_tsv)
        with open(qc_path, "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            file_rows = list(reader)
        if len(file_rows) != 1:
            raise ValueError(f"Expected exactly 1 row in {qc_path}, found {len(file_rows)}")
        row = file_rows[0]
        row["source_tsv"] = str(qc_path)
        rows.append(row)
    return sorted(rows, key=lambda item: item["target_bam"])


def write_summary(summary_output, rows):
    summary_path = Path(summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "bin_size",
        "qc_decision",
        "qc_reason",
        "mapped_fragments",
        "usable_bins",
        "zero_bin_fraction",
        "bin_cv",
        "adjacent_diff_mad",
        "gini_coefficient",
        "pearson_r",
        "spearman_r",
        "median_abs_z",
        "outlier_frac_abs_z_gt_3",
        "outlier_frac_abs_z_gt_5",
        "gc_fraction_mean",
        "gc_signal_pearson_r",
        "gc_signal_spearman_r",
        "gc_signal_slope",
        "target_bam",
        "source_tsv",
    ]
    with open(summary_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            sample_id = Path(row["target_bam"]).name.replace(".sorted.bam", "")
            writer.writerow(
                {
                    "sample_id": sample_id,
                    "bin_size": row["bin_size"],
                    "qc_decision": row["qc_decision"],
                    "qc_reason": row["qc_reason"],
                    "mapped_fragments": row["mapped_fragments"],
                    "usable_bins": row["usable_bins"],
                    "zero_bin_fraction": row["zero_bin_fraction"],
                    "bin_cv": row["bin_cv"],
                    "adjacent_diff_mad": row["adjacent_diff_mad"],
                    "gini_coefficient": row["gini_coefficient"],
                    "pearson_r": row["pearson_r"],
                    "spearman_r": row["spearman_r"],
                    "median_abs_z": row["median_abs_z"],
                    "outlier_frac_abs_z_gt_3": row["outlier_frac_abs_z_gt_3"],
                    "outlier_frac_abs_z_gt_5": row["outlier_frac_abs_z_gt_5"],
                    "gc_fraction_mean": row["gc_fraction_mean"],
                    "gc_signal_pearson_r": row["gc_signal_pearson_r"],
                    "gc_signal_spearman_r": row["gc_signal_spearman_r"],
                    "gc_signal_slope": row["gc_signal_slope"],
                    "target_bam": row["target_bam"],
                    "source_tsv": row["source_tsv"],
                }
            )


def write_pass_samples(pass_samples_output, rows):
    output_path = Path(pass_samples_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    passed = []
    for row in rows:
        if row["qc_decision"].strip().upper() == "PASS":
            passed.append(Path(row["target_bam"]).name.replace(".sorted.bam", ""))
    with open(output_path, "w", encoding="utf-8") as handle:
        for sample_id in sorted(passed):
            handle.write(f"{sample_id}\n")


def _to_float(row, key):
    try:
        return float(row[key])
    except Exception:  # noqa: BLE001
        return float("nan")


def _median_text(rows, key, digits=4):
    values = [_to_float(row, key) for row in rows]
    values = [value for value in values if value == value]
    if not values:
        return "NA"
    values = sorted(values)
    n = len(values)
    if n % 2 == 1:
        median = values[n // 2]
    else:
        median = (values[n // 2 - 1] + values[n // 2]) / 2.0
    return f"{median:.{digits}f}"


def write_markdown_report(report_output, rows):
    report_path = Path(report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    total = len(rows)
    pass_count = sum(row["qc_decision"].strip().upper() == "PASS" for row in rows)
    warn_count = sum(row["qc_decision"].strip().upper() == "WARN" for row in rows)
    fail_count = sum(row["qc_decision"].strip().upper() == "FAIL" for row in rows)
    bin_sizes = sorted({row["bin_size"] for row in rows if row.get("bin_size")})
    bin_size_text = ",".join(bin_sizes) if bin_sizes else "NA"

    if fail_count == 0 and warn_count == 0:
        final_judgement = "本批 baseline 样本在当前 200 kb bin 粒度下整体表现均一，与参考样本一致性良好，可作为项目常用建库体系的支持证据。"
    elif fail_count == 0:
        final_judgement = "本批 baseline 样本总体可用，但存在告警样本，建议结合原始文库和补测信息复核后再作为项目常用建库体系证据。"
    else:
        final_judgement = "当前 baseline 样本中存在 FAIL 样本，现阶段不足以直接证明该建库体系可稳定作为项目常用建库试剂。"

    indicator_rows = [
        ("mapped_fragments", "用于 QC 计数的有效比对片段数，越高越好。"),
        ("zero_bin_fraction", "零覆盖 bin 比例，越低越好。"),
        ("bin_cv", "各 bin read count 变异系数，越低说明覆盖越均一。"),
        ("adjacent_diff_mad", "相邻 bin 信号差值的稳健离散度，越低越平滑。"),
        ("gini_coefficient", "bin reads 分布不均匀程度，越低越好。"),
        ("pearson_r / spearman_r", "目标样本与参考中位 profile 的相关性，越高越好。"),
        ("median_abs_z", "样本相对参考的 bin 级偏离中位数，越低越好。"),
        ("outlier_frac_abs_z_gt_3", "绝对 z-score 大于 3 的 bin 比例，越低越好。"),
        ("gc_signal_pearson_r / gc_signal_spearman_r", "GC 含量与标准化 bin 信号的相关性，绝对值越小表示 GC 偏差越弱。"),
        ("gc_signal_slope", "GC 与标准化信号线性趋势斜率，绝对值越接近 0 越好。"),
    ]

    lines = []
    lines.append("# baseline 文库均一性 QC 报告")
    lines.append("")
    lines.append("## 1. 总体说明")
    lines.append("")
    lines.append(f"- 样本数：{total}")
    lines.append(f"- PASS/WARN/FAIL：{pass_count}/{warn_count}/{fail_count}")
    lines.append(f"- 当前 bin size：{bin_size_text} bp")
    lines.append("- 常染色体范围：chr1-22")
    lines.append("- GC 统计：已计算每个 bin 的 GC 含量，并评估 GC 与标准化 bin 信号的相关性")
    lines.append("")
    lines.append("## 2. 指标说明")
    lines.append("")
    lines.append("| 指标 | 统计量说明 |")
    lines.append("| --- | --- |")
    for key, desc in indicator_rows:
        lines.append(f"| {key} | {desc} |")
    lines.append("")
    lines.append("## 3. 样本结果汇总")
    lines.append("")
    lines.append("| 样本 | 判定 | mapped_fragments | zero_bin_fraction | bin_cv | gini | pearson_r | median_abs_z | gc_signal_slope | qc_reason |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for row in rows:
        sample_id = Path(row["target_bam"]).name.replace(".sorted.bam", "")
        lines.append(
            "| {sample} | {decision} | {mapped} | {zero_frac} | {bin_cv} | {gini} | {pearson} | {median_abs_z} | {gc_slope} | {reason} |".format(
                sample=sample_id,
                decision=row["qc_decision"],
                mapped=row["mapped_fragments"],
                zero_frac=f"{_to_float(row, 'zero_bin_fraction'):.4f}",
                bin_cv=f"{_to_float(row, 'bin_cv'):.4f}",
                gini=f"{_to_float(row, 'gini_coefficient'):.4f}",
                pearson=f"{_to_float(row, 'pearson_r'):.4f}",
                median_abs_z=f"{_to_float(row, 'median_abs_z'):.4f}",
                gc_slope=f"{_to_float(row, 'gc_signal_slope'):.4f}",
                reason=row["qc_reason"],
            )
        )
    lines.append("")
    lines.append("## 4. 汇总统计")
    lines.append("")
    lines.append(f"- mapped_fragments 中位数：{_median_text(rows, 'mapped_fragments', 0)}")
    lines.append(f"- zero_bin_fraction 中位数：{_median_text(rows, 'zero_bin_fraction')}")
    lines.append(f"- bin_cv 中位数：{_median_text(rows, 'bin_cv')}")
    lines.append(f"- adjacent_diff_mad 中位数：{_median_text(rows, 'adjacent_diff_mad')}")
    lines.append(f"- gini_coefficient 中位数：{_median_text(rows, 'gini_coefficient')}")
    lines.append(f"- pearson_r 中位数：{_median_text(rows, 'pearson_r')}")
    lines.append(f"- spearman_r 中位数：{_median_text(rows, 'spearman_r')}")
    lines.append(f"- median_abs_z 中位数：{_median_text(rows, 'median_abs_z')}")
    lines.append(f"- outlier_frac_abs_z_gt_3 中位数：{_median_text(rows, 'outlier_frac_abs_z_gt_3')}")
    lines.append(f"- gc_signal_pearson_r 中位数：{_median_text(rows, 'gc_signal_pearson_r')}")
    lines.append(f"- gc_signal_spearman_r 中位数：{_median_text(rows, 'gc_signal_spearman_r')}")
    lines.append(f"- gc_signal_slope 中位数：{_median_text(rows, 'gc_signal_slope')}")
    lines.append("")
    lines.append("## 5. 最终 QC 判定")
    lines.append("")
    lines.append(final_judgement)
    lines.append("")
    lines.append("注：该结论用于支持“当前 baseline 样本集下文库均一性和稳定性表现是否足以支撑常规建库方案”，不替代后续 reference/tune/predict 的技术验证。")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Aggregate per-sample baseline BAM QC outputs.")
    parser.add_argument("--qc-tsvs", nargs="+", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--pass-samples-output", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--log", default="", help="Optional log file path")
    args = parser.parse_args()

    logger = setup_logger("aggregate_baseline_qc", args.log or None)
    rows = load_qc_rows(args.qc_tsvs)
    write_summary(args.summary_output, rows)
    write_pass_samples(args.pass_samples_output, rows)
    write_markdown_report(args.report_output, rows)
    logger.info("baseline QC aggregated: samples=%d summary=%s", len(rows), args.summary_output)
    logger.info("baseline QC PASS list written: %s", args.pass_samples_output)
    logger.info("baseline QC markdown report written: %s", args.report_output)


if __name__ == "__main__":
    main()
