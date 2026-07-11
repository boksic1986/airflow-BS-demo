#!/biosoftware/miniconda/envs/snakemake_env/bin/python
import argparse
from pathlib import Path

import numpy as np

from pipeline_logging import setup_logger

CHROM_ORDER = tuple(str(index) for index in range(1, 23))


def load_primary_array(npz_path):
    with np.load(npz_path, allow_pickle=True, encoding="latin1") as data:
        if "sample" in data.files:
            sample = data["sample"].item()
            if isinstance(sample, dict):
                chromosome_values = []
                for chromosome in CHROM_ORDER:
                    raw = sample.get(chromosome)
                    if raw is None:
                        continue
                    values = np.asarray(raw)
                    if values.size and np.issubdtype(values.dtype, np.number):
                        chromosome_values.append(values.reshape(-1).astype(np.float64))
                if chromosome_values:
                    return "sample_dict_chr1_22", np.nan_to_num(
                        np.concatenate(chromosome_values),
                        nan=0.0,
                        posinf=0.0,
                        neginf=0.0,
                    )

        numeric = []
        for key in data.files:
            arr = np.asarray(data[key])
            if np.issubdtype(arr.dtype, np.number) and arr.size > 100:
                numeric.append((key, arr.reshape(-1).astype(np.float64)))
    if not numeric:
        raise ValueError(f"No usable numeric arrays in {npz_path}")
    key, values = max(numeric, key=lambda item: item[1].size)
    values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
    return key, values


def run_cnv_qc(
    sample_id,
    npz,
    output_tsv,
    output_plot,
    pass_marker,
    min_total_counts,
    min_nonzero_fraction,
    max_mad_log1p,
    logger,
):
    logger.info("start CNV QC for sample=%s npz=%s", sample_id, npz)
    signal_key, values = load_primary_array(Path(npz))
    total_counts = float(np.sum(values))
    nonzero_fraction = float(np.mean(values > 0))
    log_values = np.log1p(np.clip(values, a_min=0.0, a_max=None))
    mad_log1p = float(np.median(np.abs(log_values - np.median(log_values))))

    fail_reasons = []
    if total_counts < min_total_counts:
        fail_reasons.append("low_total_counts")
    if nonzero_fraction < min_nonzero_fraction:
        fail_reasons.append("low_nonzero_fraction")
    if mad_log1p > max_mad_log1p:
        fail_reasons.append("high_mad_log1p")

    passed = len(fail_reasons) == 0
    status = "PASS" if passed else "FAIL"
    reason_text = "PASS" if passed else ",".join(fail_reasons)
    logger.info(
        "metrics sample=%s signal=%s total=%.0f nonzero=%.6f mad_log1p=%.6f status=%s reason=%s",
        sample_id,
        signal_key,
        total_counts,
        nonzero_fraction,
        mad_log1p,
        status,
        reason_text,
    )

    output_tsv = Path(output_tsv)
    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_tsv, "w", encoding="utf-8") as handle:
        handle.write(
            "sample_id\tsignal_key\ttotal_counts\tnonzero_fraction\tmad_log1p\t"
            "threshold_min_total_counts\tthreshold_min_nonzero_fraction\tthreshold_max_mad_log1p\tstatus\treason\n"
        )
        handle.write(
            f"{sample_id}\t{signal_key}\t{total_counts:.0f}\t{nonzero_fraction:.6f}\t{mad_log1p:.6f}\t"
            f"{min_total_counts:.0f}\t{min_nonzero_fraction:.6f}\t{max_mad_log1p:.6f}\t{status}\t{reason_text}\n"
        )

    output_plot = Path(output_plot)
    output_plot.parent.mkdir(parents=True, exist_ok=True)
    width, height = 900, 340
    left, top = 90, 90
    bar_h = 36
    gap = 28
    max_w = 640

    tc_ratio = 0.0 if min_total_counts <= 0 else min(total_counts / min_total_counts, 2.0)
    nz_ratio = 0.0 if min_nonzero_fraction <= 0 else min(nonzero_fraction / min_nonzero_fraction, 2.0)
    mad_ratio = 2.0 if max_mad_log1p <= 0 else min(mad_log1p / max_mad_log1p, 2.0)

    def bar(y, label, value, threshold, ratio, reverse=False):
        fill = "#16a34a"
        if (not reverse and value < threshold) or (reverse and value > threshold):
            fill = "#dc2626"
        ratio_width = max_w * (ratio / 2.0)
        return [
            f'<text x="{left}" y="{y-10}" font-size="14" font-family="Arial,sans-serif" fill="#111">{label}</text>',
            f'<rect x="{left}" y="{y}" width="{max_w}" height="{bar_h}" fill="#f1f5f9" stroke="#cbd5e1"/>',
            f'<rect x="{left}" y="{y}" width="{ratio_width:.2f}" height="{bar_h}" fill="{fill}"/>',
            f'<line x1="{left + max_w/2:.2f}" y1="{y-4}" x2="{left + max_w/2:.2f}" y2="{y+bar_h+4}" stroke="#475569" stroke-dasharray="4,3"/>',
            f'<text x="{left + max_w + 14}" y="{y + 24}" font-size="13" font-family="Arial,sans-serif" fill="#334155">value={value:.6g}, threshold={threshold:.6g}</text>',
        ]

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')
    svg.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    svg.append(f'<text x="20" y="34" font-size="24" font-family="Arial,sans-serif" fill="#111">CNV QC Metrics - {sample_id}</text>')
    svg.append(f'<text x="20" y="58" font-size="13" font-family="Arial,sans-serif" fill="#334155">status: {status} ({reason_text})</text>')
    svg.extend(bar(top, "Total counts / min_total_counts", total_counts, min_total_counts, tc_ratio, reverse=False))
    svg.extend(bar(top + bar_h + gap, "Nonzero fraction / min_nonzero_fraction", nonzero_fraction, min_nonzero_fraction, nz_ratio, reverse=False))
    svg.extend(bar(top + 2 * (bar_h + gap), "MAD(log1p) / max_mad_log1p", mad_log1p, max_mad_log1p, mad_ratio, reverse=True))
    svg.append('</svg>')
    output_plot.write_text("\n".join(svg), encoding="utf-8")
    logger.info("qc report written: tsv=%s plot=%s", output_tsv, output_plot)

    pass_marker = Path(pass_marker)
    pass_marker.parent.mkdir(parents=True, exist_ok=True)
    pass_marker.write_text(status + "\n", encoding="utf-8")
    if passed:
        logger.info("pass marker written: %s", pass_marker)
    else:
        logger.warning("CNV QC failed for %s: %s; prediction will be skipped", sample_id, reason_text)


def main():
    parser = argparse.ArgumentParser(description="QC check for WisecondorX CNV input NPZ.")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--npz", required=True)
    parser.add_argument("--output-tsv", required=True)
    parser.add_argument("--output-plot", required=True)
    parser.add_argument("--pass-marker", required=True)
    parser.add_argument("--min-total-counts", type=float, required=True)
    parser.add_argument("--min-nonzero-fraction", type=float, required=True)
    parser.add_argument("--max-mad-log1p", type=float, required=True)
    parser.add_argument("--log", default="", help="Optional log file path")
    args = parser.parse_args()
    logger = setup_logger("cnv_qc", args.log or None)
    run_cnv_qc(
        sample_id=args.sample_id,
        npz=args.npz,
        output_tsv=args.output_tsv,
        output_plot=args.output_plot,
        pass_marker=args.pass_marker,
        min_total_counts=args.min_total_counts,
        min_nonzero_fraction=args.min_nonzero_fraction,
        max_mad_log1p=args.max_mad_log1p,
        logger=logger,
    )


if __name__ == "__main__":
    main()
