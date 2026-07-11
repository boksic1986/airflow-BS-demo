#!/biosoftware/miniconda/envs/snakemake_env/bin/python
import argparse
import math
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from pipeline_logging import setup_logger

CHROM_ORDER = tuple(str(index) for index in range(1, 23))
SIGNAL_KEY = "sample_dict_chr1_22_aligned"


def run_command(command, logger, output_log_path=None):
    logger.info("$ %s", " ".join(shlex.quote(part) for part in command))
    if output_log_path is None:
        subprocess.run(command, check=True)
        return
    output_log_path = Path(output_log_path)
    output_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_log_path, "a", encoding="utf-8") as log_handle:
        subprocess.run(command, check=True, stdout=log_handle, stderr=log_handle)


def _to_numeric_vector(raw, npz_path, chr_name):
    if raw is None:
        return None
    arr = np.asarray(raw)
    if arr.size == 0:
        return None
    if not np.issubdtype(arr.dtype, np.number):
        raise ValueError(f"Non-numeric counts for chr{chr_name} in {npz_path}")
    vec = np.nan_to_num(
        arr.astype(np.float64).reshape(-1),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )
    return vec if vec.size > 0 else None


def load_sample_bins(npz_path):
    with np.load(npz_path, allow_pickle=True, encoding="latin1") as data:
        if "sample" not in data.files:
            raise ValueError(f"Missing 'sample' key in {npz_path}")
        sample_obj = data["sample"].item()
        if not isinstance(sample_obj, dict):
            raise ValueError(f"'sample' is not dict-like in {npz_path}")
        binsize = int(np.asarray(data["binsize"]).item()) if "binsize" in data.files else 0

        chr_bins = {}
        for chr_name in CHROM_ORDER:
            vec = _to_numeric_vector(sample_obj.get(chr_name), npz_path, chr_name)
            if vec is not None:
                chr_bins[chr_name] = vec

    if not chr_bins:
        raise ValueError(f"No usable chromosome count vectors found in {npz_path}")

    return {
        "binsize": binsize,
        "chr_bins": chr_bins,
    }


def build_matrix_from_loaded(loaded):
    if not loaded:
        raise ValueError("No usable NPZ sample payloads were loaded.")
    binsizes = sorted({entry["binsize"] for entry in loaded if entry["binsize"] > 0})
    if len(binsizes) > 1:
        raise ValueError(f"Inconsistent binsize across NPZ inputs: {binsizes}")

    chr_lengths = {}
    for chr_name in CHROM_ORDER:
        available = [entry["chr_bins"].get(chr_name) for entry in loaded]
        available = [vec for vec in available if vec is not None and vec.size > 0]
        if not available:
            continue
        chr_lengths[chr_name] = min(len(vec) for vec in available)

    if not chr_lengths:
        raise ValueError("No chromosome vectors available across loaded samples.")

    row_vectors = []
    for entry in loaded:
        segments = []
        chr_bins = entry["chr_bins"]
        for chr_name, target_len in chr_lengths.items():
            vec = chr_bins.get(chr_name)
            if vec is None:
                segments.append(np.zeros(target_len, dtype=np.float64))
            else:
                segments.append(vec[:target_len])
        row_vectors.append(np.concatenate(segments))

    matrix = np.vstack(row_vectors)
    if matrix.shape[1] < 100:
        raise ValueError("Too few usable bins after chromosome alignment (<100).")
    signal_key = SIGNAL_KEY
    return matrix, signal_key


def filter_usable_npz(sample_ids, bams, npz_paths, logger):
    kept_sample_ids = []
    kept_bams = []
    kept_npz_paths = []
    kept_loaded = []
    dropped_samples = []

    for sample_id, bam_path, npz_path in zip(sample_ids, bams, npz_paths):
        try:
            loaded = load_sample_bins(npz_path)
        except Exception as exc:  # noqa: BLE001
            dropped_samples.append(sample_id)
            logger.warning(
                "[prefilter] drop sample=%s npz=%s reason=%s",
                sample_id,
                npz_path,
                str(exc),
            )
            continue
        kept_sample_ids.append(sample_id)
        kept_bams.append(bam_path)
        kept_npz_paths.append(npz_path)
        kept_loaded.append(loaded)

    if dropped_samples:
        logger.warning(
            "[prefilter] dropped unusable NPZ samples (%d): %s",
            len(dropped_samples),
            ",".join(sorted(dropped_samples)),
        )

    return kept_sample_ids, kept_bams, kept_npz_paths, kept_loaded, dropped_samples


def normalize_matrix(matrix):
    matrix = np.clip(matrix, a_min=0.0, a_max=None)
    totals = matrix.sum(axis=1, keepdims=True)
    totals[totals <= 0.0] = 1.0
    cpm = matrix / totals * 1e6
    return np.log1p(cpm)


def standardize_rows(matrix):
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std[std == 0.0] = 1.0
    return (matrix - mean) / std, mean, std


def pca_profile(matrix, max_components):
    standardized, _, _ = standardize_rows(matrix)
    _, singular_values, vt = np.linalg.svd(standardized, full_matrices=False)
    variances = singular_values ** 2
    total = variances.sum()
    if total <= 0.0:
        raise ValueError("Total PCA variance is zero.")
    explained = variances / total
    limit = min(max_components, explained.size)
    explained = explained[:limit]
    cumulative = np.cumsum(explained)
    return standardized, vt, explained, cumulative


def find_elbow_component(cumulative):
    points = np.arange(1, cumulative.size + 1, dtype=np.float64)
    y = cumulative.astype(np.float64)
    if cumulative.size <= 2:
        return int(cumulative.size)
    x1, y1 = points[0], y[0]
    x2, y2 = points[-1], y[-1]
    denom = math.hypot(y2 - y1, x2 - x1)
    if denom == 0.0:
        return 1
    distances = np.abs((y2 - y1) * points - (x2 - x1) * y + x2 * y1 - y2 * x1) / denom
    return int(np.argmax(distances)) + 1


def robust_z(values):
    values = np.asarray(values, dtype=np.float64)
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    if mad == 0.0:
        return np.zeros_like(values)
    return (values - median) / (1.4826 * mad)


def reconstruction_errors_from_svd(standardized, vt, n_components):
    basis = vt[:n_components]
    projected = standardized @ basis.T
    reconstructed = projected @ basis
    return np.mean((standardized - reconstructed) ** 2, axis=1)


def sample_qc_metrics(sample_ids, matrix, raw_totals, standardized, vt, n_components):
    median_profile = np.median(matrix, axis=0)
    row_centered = matrix - matrix.mean(axis=1, keepdims=True)
    median_centered = median_profile - np.mean(median_profile)
    numerator = row_centered @ median_centered
    denominator = np.linalg.norm(row_centered, axis=1) * np.linalg.norm(median_centered)
    correlations = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)

    residual = matrix - median_profile
    residual_median = np.median(residual, axis=1, keepdims=True)
    noise_mad = np.median(np.abs(residual - residual_median), axis=1)

    recon_error = reconstruction_errors_from_svd(standardized, vt, n_components)
    recon_z = robust_z(recon_error)
    noise_z = robust_z(noise_mad)

    rows = []
    for index, sample_id in enumerate(sample_ids):
        rows.append(
            {
                "sample_id": sample_id,
                "reads": float(raw_totals[index]),
                "corr_to_median": float(correlations[index]),
                "noise_mad": float(noise_mad[index]),
                "noise_mad_z": float(noise_z[index]),
                "reconstruction_error": float(recon_error[index]),
                "reconstruction_error_z": float(recon_z[index]),
            }
        )
    return rows


def label_outliers(metrics, cfg):
    outliers = []
    inliers = []
    for row in metrics:
        reasons = []
        if row["reads"] < cfg["min_reads_per_sample"]:
            reasons.append("low_reads")
        if row["corr_to_median"] < cfg["min_corr_to_median"]:
            reasons.append("low_corr")
        if row["reconstruction_error_z"] > cfg["max_reconstruction_error_z"]:
            reasons.append("high_recon_z")
        if row["noise_mad_z"] > cfg["max_noise_mad_z"]:
            reasons.append("high_noise_z")
        row["is_outlier"] = bool(reasons)
        row["reasons"] = ",".join(reasons) if reasons else "PASS"
        if row["is_outlier"]:
            outliers.append(row)
        else:
            inliers.append(row)
    return inliers, outliers


def _safe_norm(value, low, high):
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def write_qc_svg(output_path, rows, cfg):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="220"></svg>\n')
        return

    rows = sorted(rows, key=lambda row: row["sample_id"])
    width = max(980, 140 + 28 * len(rows))
    height = 540
    left = 90
    right = 30
    top = 70
    panel_h = 130
    panel_gap = 40
    chart_w = width - left - right

    corr_y0 = top
    recon_y0 = top + panel_h + panel_gap
    noise_y0 = top + 2 * (panel_h + panel_gap)

    def x_pos(idx):
        if len(rows) == 1:
            return left + chart_w / 2
        return left + chart_w * idx / (len(rows) - 1)

    corr_vals = [row["corr_to_median"] for row in rows]
    recon_vals = [row["reconstruction_error_z"] for row in rows]
    noise_vals = [row["noise_mad_z"] for row in rows]

    corr_points = " ".join(f"{x_pos(i):.2f},{(corr_y0 + panel_h * (1 - _safe_norm(v, 0.6, 1.0))):.2f}" for i, v in enumerate(corr_vals))
    recon_points = " ".join(f"{x_pos(i):.2f},{(recon_y0 + panel_h * (1 - _safe_norm(v, -1.0, 6.0))):.2f}" for i, v in enumerate(recon_vals))
    noise_points = " ".join(f"{x_pos(i):.2f},{(noise_y0 + panel_h * (1 - _safe_norm(v, -1.0, 6.0))):.2f}" for i, v in enumerate(noise_vals))

    corr_thr_y = corr_y0 + panel_h * (1 - _safe_norm(cfg["min_corr_to_median"], 0.6, 1.0))
    recon_thr_y = recon_y0 + panel_h * (1 - _safe_norm(cfg["max_reconstruction_error_z"], -1.0, 6.0))
    noise_thr_y = noise_y0 + panel_h * (1 - _safe_norm(cfg["max_noise_mad_z"], -1.0, 6.0))

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')
    out.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    out.append('<text x="20" y="30" font-size="22" font-family="Arial,sans-serif" fill="#111">Reference Prefilter QC</text>')

    for y0, label in [(corr_y0, "Correlation to median"), (recon_y0, "Reconstruction error z"), (noise_y0, "Noise MAD z")]:
        out.append(f'<rect x="{left}" y="{y0}" width="{chart_w}" height="{panel_h}" fill="#f8fafc" stroke="#cbd5e1"/>')
        out.append(f'<text x="{left}" y="{y0 - 10}" font-size="13" font-family="Arial,sans-serif" fill="#334155">{label}</text>')

    out.append(f'<polyline fill="none" stroke="#0f766e" stroke-width="2.5" points="{corr_points}"/>')
    out.append(f'<polyline fill="none" stroke="#1d4ed8" stroke-width="2.5" points="{recon_points}"/>')
    out.append(f'<polyline fill="none" stroke="#9333ea" stroke-width="2.5" points="{noise_points}"/>')

    out.append(f'<line x1="{left}" y1="{corr_thr_y:.2f}" x2="{left + chart_w}" y2="{corr_thr_y:.2f}" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="6,4"/>')
    out.append(f'<line x1="{left}" y1="{recon_thr_y:.2f}" x2="{left + chart_w}" y2="{recon_thr_y:.2f}" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="6,4"/>')
    out.append(f'<line x1="{left}" y1="{noise_thr_y:.2f}" x2="{left + chart_w}" y2="{noise_thr_y:.2f}" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="6,4"/>')

    y_axis_bottom = noise_y0 + panel_h + 20
    for i, row in enumerate(rows):
        x = x_pos(i)
        status_color = "#16a34a" if not row["is_outlier"] else "#dc2626"
        out.append(f'<line x1="{x:.2f}" y1="{noise_y0 + panel_h}" x2="{x:.2f}" y2="{noise_y0 + panel_h + 5}" stroke="#64748b"/>')
        out.append(f'<text x="{x:.2f}" y="{y_axis_bottom}" font-size="10" font-family="Arial,sans-serif" transform="rotate(45 {x:.2f},{y_axis_bottom})" fill="#334155">{row["sample_id"]}</text>')
        out.append(f'<circle cx="{x:.2f}" cy="{corr_y0 + panel_h * (1 - _safe_norm(row["corr_to_median"], 0.6, 1.0)):.2f}" r="2.6" fill="{status_color}"/>')
        out.append(f'<circle cx="{x:.2f}" cy="{recon_y0 + panel_h * (1 - _safe_norm(row["reconstruction_error_z"], -1.0, 6.0)):.2f}" r="2.6" fill="{status_color}"/>')
        out.append(f'<circle cx="{x:.2f}" cy="{noise_y0 + panel_h * (1 - _safe_norm(row["noise_mad_z"], -1.0, 6.0)):.2f}" r="2.6" fill="{status_color}"/>')

    out.append("</svg>")
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out))


def write_qc_table(output_path, rows, removed_state):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(
            "sample_id\treads\tcorr_to_median\tnoise_mad\tnoise_mad_z\t"
            "reconstruction_error\treconstruction_error_z\tis_outlier\treasons\tremoved_iteration\n"
        )
        for row in sorted(rows, key=lambda r: r["sample_id"]):
            state = removed_state.get(row["sample_id"], {})
            removed_iteration = state.get("removed_iteration", 0)
            handle.write(
                f"{row['sample_id']}\t{row['reads']:.0f}\t{row['corr_to_median']:.6f}\t{row['noise_mad']:.6f}\t"
                f"{row['noise_mad_z']:.6f}\t{row['reconstruction_error']:.6f}\t{row['reconstruction_error_z']:.6f}\t"
                f"{str(row['is_outlier']).lower()}\t{row['reasons']}\t{removed_iteration}\n"
            )


def write_inliers(output_path, inlier_ids):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        for sample_id in sorted(inlier_ids):
            handle.write(f"{sample_id}\n")


def write_summary(output_path, payload):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        for key in sorted(payload):
            handle.write(f"{key}: {payload[key]}\n")


def convert_all_bams(wisecondorx, bams, sample_ids, binsize, output_dir, threads, logger):
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_npz_pairs = [(sample_id, bam_path, output_dir / f"{sample_id}.npz") for sample_id, bam_path in zip(sample_ids, bams)]
    npz_paths = [item[2] for item in sample_npz_pairs]
    pending = [(sample_id, bam_path, npz_path) for sample_id, bam_path, npz_path in sample_npz_pairs if not npz_path.exists()]
    if not pending:
        logger.info("[convert] reused existing npz files: %d (binsize=%s)", len(npz_paths), binsize)
        return npz_paths

    convert_log_dir = output_dir / "convert_logs"
    convert_log_dir.mkdir(parents=True, exist_ok=True)

    max_workers = max(1, min(int(threads), len(pending)))
    logger.info("[convert] start binsize=%s pending=%d workers=%d", binsize, len(pending), max_workers)

    def convert_one(sample_id, bam_path, npz_path):
        sample_log = convert_log_dir / f"{sample_id}.convert.log"
        run_command(
            [
                wisecondorx,
                "convert",
                str(bam_path),
                str(npz_path),
                "--binsize",
                str(binsize),
            ],
            logger,
            sample_log,
        )
        return sample_id, npz_path, sample_log

    if max_workers == 1:
        for sample_id, bam_path, npz_path in pending:
            sid, out_npz, sample_log = convert_one(sample_id, bam_path, npz_path)
            logger.info("[convert] done sample=%s npz=%s log=%s", sid, out_npz, sample_log)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(convert_one, sample_id, bam_path, npz_path) for sample_id, bam_path, npz_path in pending]
            for future in as_completed(futures):
                sid, out_npz, sample_log = future.result()
                logger.info("[convert] done sample=%s npz=%s log=%s", sid, out_npz, sample_log)

    return npz_paths


def run_reference_prefilter_qc(
    wisecondorx,
    bams,
    sample_ids,
    binsize,
    pca_min_components,
    pca_max_components,
    min_reference_samples,
    min_reads_per_sample,
    min_corr_to_median,
    max_reconstruction_error_z,
    max_noise_mad_z,
    max_iterations,
    threads,
    workdir,
    qc_output,
    plot_output,
    inlier_samples_output,
    summary_output,
    logger,
):
    logger.info(
        "start prefilter: samples=%d binsize=%s threads=%d max_iterations=%d",
        len(sample_ids),
        binsize,
        threads,
        max_iterations,
    )

    bams = [Path(path) for path in bams]
    sample_ids = list(sample_ids)
    if len(bams) != len(sample_ids):
        raise ValueError("--bams and --sample-ids must contain the same number of items.")
    if len(sample_ids) < min_reference_samples:
        raise ValueError("Input samples are fewer than --min-reference-samples.")

    qc_cfg = {
        "min_reads_per_sample": min_reads_per_sample,
        "min_corr_to_median": min_corr_to_median,
        "max_reconstruction_error_z": max_reconstruction_error_z,
        "max_noise_mad_z": max_noise_mad_z,
    }

    workdir = Path(workdir)
    qc_output = Path(qc_output)
    plot_output = Path(plot_output)
    inlier_samples_output = Path(inlier_samples_output)
    summary_output = Path(summary_output)

    npz_paths = convert_all_bams(
        wisecondorx=wisecondorx,
        bams=bams,
        sample_ids=sample_ids,
        binsize=binsize,
        output_dir=workdir / "converted",
        threads=threads,
        logger=logger,
    )

    (
        sample_ids,
        bams,
        npz_paths,
        loaded_arrays,
        dropped_npz_samples,
    ) = filter_usable_npz(sample_ids, bams, npz_paths, logger)
    if len(sample_ids) < min_reference_samples:
        dropped_text = ",".join(sorted(dropped_npz_samples)) if dropped_npz_samples else "none"
        raise ValueError(
            "Usable samples after NPZ validation are fewer than --min-reference-samples: "
            f"{len(sample_ids)} < {min_reference_samples}. dropped={dropped_text}"
        )

    matrix_raw, signal_key = build_matrix_from_loaded(loaded_arrays)
    matrix = normalize_matrix(matrix_raw)
    totals = matrix_raw.sum(axis=1)
    idx_map = {sample_id: idx for idx, sample_id in enumerate(sample_ids)}

    current_ids = list(sample_ids)
    removed_state = {sample_id: {"removed_iteration": 0, "reasons": "PASS"} for sample_id in sample_ids}
    last_metrics = []
    selected_pca = 0
    elbow_pca = 0
    completed_iterations = 0

    for iteration in range(1, max_iterations + 1):
        completed_iterations = iteration
        current_indices = [idx_map[s] for s in current_ids]
        current_matrix = matrix[current_indices, :]
        current_totals = totals[current_indices]
        max_components = min(pca_max_components, current_matrix.shape[0] - 1, current_matrix.shape[1])
        if max_components < 1:
            break
        standardized, vt, _, cumulative = pca_profile(current_matrix, max_components)
        elbow_pca = find_elbow_component(cumulative)
        selected_pca = max(min(pca_min_components, max_components), elbow_pca)
        selected_pca = min(selected_pca, max_components)

        metrics = sample_qc_metrics(current_ids, current_matrix, current_totals, standardized, vt, selected_pca)
        inliers, outliers = label_outliers(metrics, qc_cfg)
        last_metrics = metrics
        if not outliers:
            break
        if len(inliers) < min_reference_samples:
            break
        outlier_ids = {row["sample_id"] for row in outliers}
        for row in outliers:
            removed_state[row["sample_id"]] = {
                "removed_iteration": iteration,
                "reasons": row["reasons"],
            }
        current_ids = [sid for sid in current_ids if sid not in outlier_ids]

    current_id_set = set(current_ids)
    final_outlier_ids = set(sample_ids) - current_id_set
    rows_for_output = []
    metric_lookup = {row["sample_id"]: row for row in last_metrics}
    for sample_id in sample_ids:
        row = metric_lookup.get(sample_id)
        if row is None:
            row = {
                "sample_id": sample_id,
                "reads": float(totals[idx_map[sample_id]]),
                "corr_to_median": 0.0,
                "noise_mad": 0.0,
                "noise_mad_z": 0.0,
                "reconstruction_error": 0.0,
                "reconstruction_error_z": 0.0,
                "is_outlier": sample_id in final_outlier_ids,
                "reasons": removed_state[sample_id]["reasons"] if sample_id in final_outlier_ids else "PASS",
            }
        else:
            row = dict(row)
            row["is_outlier"] = sample_id in final_outlier_ids
            row["reasons"] = removed_state[sample_id]["reasons"] if sample_id in final_outlier_ids else "PASS"
        rows_for_output.append(row)

    if len(current_ids) < min_reference_samples:
        raise ValueError(f"Prefilter leaves only {len(current_ids)} inliers, below minimum {min_reference_samples}.")

    write_qc_table(qc_output, rows_for_output, removed_state)
    write_qc_svg(plot_output, rows_for_output, qc_cfg)
    write_inliers(inlier_samples_output, current_ids)
    write_summary(
        summary_output,
        {
            "binsize": binsize,
            "signal_key": signal_key,
            "input_samples": len(sample_ids),
            "final_inliers": len(current_ids),
            "final_outliers": len(final_outlier_ids),
            "iterations": completed_iterations,
            "selected_pca": selected_pca,
            "elbow_pca": elbow_pca,
            "dropped_unusable_npz_samples": len(dropped_npz_samples),
            "dropped_unusable_npz_sample_ids": ",".join(sorted(dropped_npz_samples)) if dropped_npz_samples else "NONE",
        },
    )
    logger.info(
        "prefilter completed: input=%d inliers=%d outliers=%d dropped_npz=%d selected_pca=%d elbow=%d",
        len(sample_ids),
        len(current_ids),
        len(final_outlier_ids),
        len(dropped_npz_samples),
        selected_pca,
        elbow_pca,
    )


def main():
    parser = argparse.ArgumentParser(description="Iterative reference sample prefiltering for WisecondorX.")
    parser.add_argument("--wisecondorx", required=True)
    parser.add_argument("--bams", nargs="+", required=True)
    parser.add_argument("--sample-ids", nargs="+", required=True)
    parser.add_argument("--binsize", type=int, default=100000)
    parser.add_argument("--pca-min-components", type=int, default=2)
    parser.add_argument("--pca-max-components", type=int, default=20)
    parser.add_argument("--min-reference-samples", type=int, default=8)
    parser.add_argument("--min-reads-per-sample", type=float, default=3_000_000)
    parser.add_argument("--min-corr-to-median", type=float, default=0.9)
    parser.add_argument("--max-reconstruction-error-z", type=float, default=3.5)
    parser.add_argument("--max-noise-mad-z", type=float, default=3.5)
    parser.add_argument("--max-iterations", type=int, default=3)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--qc-output", required=True)
    parser.add_argument("--plot-output", required=True)
    parser.add_argument("--inlier-samples-output", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()
    logger = setup_logger("reference_prefilter_qc", args.log)
    run_reference_prefilter_qc(
        wisecondorx=args.wisecondorx,
        bams=args.bams,
        sample_ids=args.sample_ids,
        binsize=args.binsize,
        pca_min_components=args.pca_min_components,
        pca_max_components=args.pca_max_components,
        min_reference_samples=args.min_reference_samples,
        min_reads_per_sample=args.min_reads_per_sample,
        min_corr_to_median=args.min_corr_to_median,
        max_reconstruction_error_z=args.max_reconstruction_error_z,
        max_noise_mad_z=args.max_noise_mad_z,
        max_iterations=args.max_iterations,
        threads=args.threads,
        workdir=args.workdir,
        qc_output=args.qc_output,
        plot_output=args.plot_output,
        inlier_samples_output=args.inlier_samples_output,
        summary_output=args.summary_output,
        logger=logger,
    )


if __name__ == "__main__":
    main()
