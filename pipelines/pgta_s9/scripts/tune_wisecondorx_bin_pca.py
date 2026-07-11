#!/biosoftware/miniconda/envs/snakemake_env/bin/python
import argparse
import math
import shlex
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from pipeline_logging import setup_logger

CHROM_ORDER = tuple(str(index) for index in range(1, 23))
SIGNAL_KEY = "sample_dict_chr1_22_aligned"


def parse_int_list(value):
    values = [int(item.strip()) for item in str(value).split(",") if item.strip()]
    if not values:
        raise ValueError("Empty integer list.")
    return sorted(set(values))


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


def filter_usable_npz(sample_ids, bams, npz_paths, logger, stage_tag):
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
                "[%s] drop sample=%s npz=%s reason=%s",
                stage_tag,
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
            "[%s] dropped unusable NPZ samples (%d): %s",
            stage_tag,
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
    if np.any(np.diff(cumulative) < -1e-12):
        raise ValueError("PCA cumulative explained variance must be non-decreasing.")
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
    elbow_index = int(np.argmax(distances))
    return elbow_index + 1


def choose_pca_components(cumulative, min_components, min_explained_variance):
    elbow = find_elbow_component(cumulative)
    selected = max(elbow, min_components)
    if min_explained_variance > 0.0:
        reaches = np.where(cumulative >= min_explained_variance)[0]
        if reaches.size > 0:
            selected = max(selected, int(reaches[0]) + 1)
    selected = min(selected, cumulative.size)
    return selected, elbow


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


def cross_validated_mse(matrix, n_components, seed, folds=5):
    sample_count, feature_count = matrix.shape
    fold_count = min(folds, sample_count)
    if sample_count < 3 or n_components < 1:
        return None

    rng = np.random.default_rng(seed)
    indices = rng.permutation(sample_count)
    split = [fold for fold in np.array_split(indices, fold_count) if fold.size > 0]
    fold_errors = []

    for test_indices in split:
        train_mask = np.ones(sample_count, dtype=bool)
        train_mask[test_indices] = False
        train_indices = np.where(train_mask)[0]
        if train_indices.size < 2:
            continue

        train = matrix[train_indices]
        test = matrix[test_indices]
        train_std, mean, std = standardize_rows(train)
        test_std = (test - mean) / std

        max_components = min(train_indices.size - 1, feature_count)
        if max_components < 1 or n_components > max_components:
            return None

        _, _, vt = np.linalg.svd(train_std, full_matrices=False)
        basis = vt[:n_components]
        projected = test_std @ basis.T
        reconstructed = projected @ basis
        fold_errors.append(float(np.mean((test_std - reconstructed) ** 2)))

    if not fold_errors:
        return None
    return float(np.mean(fold_errors))


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

    metrics = []
    for index, sample_id in enumerate(sample_ids):
        metrics.append(
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
    return metrics


def label_outliers(metrics, qc_cfg):
    outliers = []
    inliers = []
    for row in metrics:
        reasons = []
        if row["reads"] < qc_cfg["min_reads_per_sample"]:
            reasons.append("low_reads")
        if row["corr_to_median"] < qc_cfg["min_corr_to_median"]:
            reasons.append("low_corr")
        if row["reconstruction_error_z"] > qc_cfg["max_reconstruction_error_z"]:
            reasons.append("high_recon_z")
        if row["noise_mad_z"] > qc_cfg["max_noise_mad_z"]:
            reasons.append("high_noise_z")
        row["is_outlier"] = bool(reasons)
        row["reasons"] = ",".join(reasons) if reasons else "PASS"
        if row["is_outlier"]:
            outliers.append(row)
        else:
            inliers.append(row)
    return inliers, outliers


def write_pca_profile_tsv(profile_path, explained, cumulative):
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    with open(profile_path, "w", encoding="utf-8") as handle:
        handle.write("component\texplained_variance_ratio\tcumulative_explained_variance_ratio\n")
        for index, (component_var, cumulative_var) in enumerate(zip(explained, cumulative), start=1):
            handle.write(f"{index}\t{component_var:.10f}\t{cumulative_var:.10f}\n")


def write_pca_svg(plot_path, binsize, explained, cumulative, elbow_component, min_explained):
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 980, 640
    left, right, top, bottom = 90, 40, 60, 80
    chart_width = width - left - right
    chart_height = height - top - bottom

    n_points = explained.size
    if n_points < 1:
        raise ValueError("Cannot draw PCA plot with zero points.")

    def x_coord(component_index):
        if n_points == 1:
            return left + chart_width / 2.0
        return left + chart_width * (component_index - 1) / (n_points - 1)

    def y_coord(value):
        return top + chart_height * (1.0 - value)

    points = " ".join(f"{x_coord(i + 1):.2f},{y_coord(cumulative[i]):.2f}" for i in range(n_points))
    elbow_x = x_coord(elbow_component)
    elbow_y = y_coord(cumulative[elbow_component - 1])
    has_variance_target = min_explained > 0.0
    target_y = y_coord(min_explained) if has_variance_target else None

    x_ticks = []
    tick_step = max(1, n_points // 10)
    for idx in range(1, n_points + 1, tick_step):
        x_ticks.append((idx, x_coord(idx)))
    if x_ticks[-1][0] != n_points:
        x_ticks.append((n_points, x_coord(n_points)))

    y_ticks = [(value, y_coord(value)) for value in [0.0, 0.25, 0.5, 0.75, 1.0]]

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        f'<text x="{left}" y="35" font-size="22" font-family="Arial, sans-serif" fill="#111111">PCA Cumulative Explained Variance</text>',
        f'<text x="{left}" y="56" font-size="12" font-family="Arial, sans-serif" fill="#475569">Current binsize={binsize}; cumulative values are computed within this binsize only.</text>',
        f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" stroke="#222222" stroke-width="1"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" stroke="#222222" stroke-width="1"/>',
        f'<polyline fill="none" stroke="#0f766e" stroke-width="3" points="{points}" />',
        f'<line x1="{elbow_x:.2f}" y1="{top}" x2="{elbow_x:.2f}" y2="{top + chart_height}" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="6,4"/>',
        f'<circle cx="{elbow_x:.2f}" cy="{elbow_y:.2f}" r="5" fill="#dc2626"/>',
        f'<text x="{elbow_x + 8:.2f}" y="{elbow_y - 8:.2f}" font-size="14" font-family="Arial, sans-serif" fill="#dc2626">Elbow PC={elbow_component}</text>',
    ]
    if has_variance_target:
        lines.append(f'<line x1="{left}" y1="{target_y:.2f}" x2="{left + chart_width}" y2="{target_y:.2f}" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="6,4"/>')
        lines.append(f'<text x="{left + 4}" y="{target_y - 6:.2f}" font-size="12" font-family="Arial, sans-serif" fill="#475569">Min variance {min_explained:.0%}</text>')
    else:
        lines.append(f'<text x="{left + 4}" y="{top + 16:.2f}" font-size="12" font-family="Arial, sans-serif" fill="#475569">Min variance threshold disabled, PCA selected by elbow</text>')

    for tick_value, tick_y in y_ticks:
        lines.append(f'<line x1="{left - 5}" y1="{tick_y:.2f}" x2="{left}" y2="{tick_y:.2f}" stroke="#222222" stroke-width="1"/>')
        lines.append(
            f'<text x="{left - 12}" y="{tick_y + 4:.2f}" text-anchor="end" font-size="12" '
            f'font-family="Arial, sans-serif" fill="#334155">{tick_value:.0%}</text>'
        )

    for tick_label, tick_x in x_ticks:
        lines.append(f'<line x1="{tick_x:.2f}" y1="{top + chart_height}" x2="{tick_x:.2f}" y2="{top + chart_height + 5}" stroke="#222222" stroke-width="1"/>')
        lines.append(
            f'<text x="{tick_x:.2f}" y="{top + chart_height + 22}" text-anchor="middle" font-size="11" '
            f'font-family="Arial, sans-serif" fill="#334155">{tick_label}</text>'
        )

    lines.append(f'<text x="{left + chart_width / 2:.2f}" y="{height - 24}" text-anchor="middle" font-size="14" font-family="Arial, sans-serif" fill="#111111">PCA component count</text>')
    lines.append(f'<text x="{24}" y="{top + chart_height / 2:.2f}" transform="rotate(-90 24,{top + chart_height / 2:.2f})" text-anchor="middle" font-size="14" font-family="Arial, sans-serif" fill="#111111">Cumulative explained variance</text>')
    lines.append("</svg>")

    with open(plot_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def write_summary(summary_output, rows):
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_output, "w", encoding="utf-8") as handle:
        handle.write(
            "binsize\tpca_components\tselected_pca\telbow_pca\tcum_explained_variance\tcomponent_explained_variance\t"
            "component_cum_explained_variance\tis_selected_pca\tpca_profile_tsv\tcv_reconstruction_mse\t"
            "inliers\toutliers\toutlier_fraction\tsignal_key\tsamples\tfeatures\tstatus\n"
        )
        for row in rows:
            cv_mse = "NA" if row["cv_mse"] is None else f"{row['cv_mse']:.10f}"
            handle.write(
                f"{row['binsize']}\t{row['pca_components']}\t{row['selected_pca']}\t{row['elbow_pca']}\t{row['cum_var']:.6f}\t"
                f"{row['component_var']:.6f}\t{row['component_cum_var']:.6f}\t"
                f"{str(row['is_selected_pca']).lower()}\t{row['pca_profile_tsv']}\t{cv_mse}\t"
                f"{row['inliers']}\t{row['outliers']}\t{row['outlier_fraction']:.6f}\t{row['signal_key']}\t"
                f"{row['samples']}\t{row['features']}\t{row['status']}\n"
            )


def write_best_yaml(best_output, best_row):
    best_output.parent.mkdir(parents=True, exist_ok=True)
    with open(best_output, "w", encoding="utf-8") as handle:
        handle.write(f"best_binsize: {best_row['binsize']}\n")
        handle.write(f"best_pca_components: {best_row['pca_components']}\n")
        handle.write(f"best_selected_pca: {best_row['selected_pca']}\n")
        handle.write(f"best_elbow_pca: {best_row['elbow_pca']}\n")
        handle.write(f"best_cum_explained_variance: {best_row['cum_var']:.6f}\n")
        handle.write(f"best_component_explained_variance: {best_row['component_var']:.6f}\n")
        handle.write(f"best_component_cum_explained_variance: {best_row['component_cum_var']:.6f}\n")
        handle.write(f"best_pca_profile_tsv: {best_row['pca_profile_tsv']}\n")
        handle.write(f"best_cv_reconstruction_mse: {best_row['cv_mse']:.10f}\n")
        handle.write(f"best_inliers: {best_row['inliers']}\n")
        handle.write(f"best_outliers: {best_row['outliers']}\n")
        handle.write(f"signal_key: {best_row['signal_key']}\n")


def write_qc_table(qc_output, rows):
    qc_output.parent.mkdir(parents=True, exist_ok=True)
    with open(qc_output, "w", encoding="utf-8") as handle:
        handle.write(
            "sample_id\treads\tcorr_to_median\tnoise_mad\tnoise_mad_z\t"
            "reconstruction_error\treconstruction_error_z\tis_outlier\treasons\n"
        )
        for row in rows:
            handle.write(
                f"{row['sample_id']}\t{row['reads']:.0f}\t{row['corr_to_median']:.6f}\t{row['noise_mad']:.6f}\t"
                f"{row['noise_mad_z']:.6f}\t{row['reconstruction_error']:.6f}\t{row['reconstruction_error_z']:.6f}\t"
                f"{str(row['is_outlier']).lower()}\t{row['reasons']}\n"
            )


def write_inlier_samples(output_path, rows):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        for row in rows:
            if not row["is_outlier"]:
                handle.write(f"{row['sample_id']}\n")


def _safe_norm(value, low, high):
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def write_reference_qc_svg(output_path, rows, qc_cfg):
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

    corr_thr_y = corr_y0 + panel_h * (1 - _safe_norm(qc_cfg["min_corr_to_median"], 0.6, 1.0))
    recon_thr_y = recon_y0 + panel_h * (1 - _safe_norm(qc_cfg["max_reconstruction_error_z"], -1.0, 6.0))
    noise_thr_y = noise_y0 + panel_h * (1 - _safe_norm(qc_cfg["max_noise_mad_z"], -1.0, 6.0))

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')
    out.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    out.append('<text x="20" y="30" font-size="22" font-family="Arial,sans-serif" fill="#111">Reference QC Metrics</text>')

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

    out.append('</svg>')
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out))


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


def build_reference(wisecondorx, binsize, npz_paths, reference_output, threads, logger):
    reference_output.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            wisecondorx,
            "newref",
            *[str(path) for path in npz_paths],
            str(reference_output),
            "--binsize",
            str(binsize),
            "--cpus",
            str(threads),
        ],
        logger,
    )


def run_tune_wisecondorx(
    wisecondorx,
    bams,
    sample_ids,
    bin_sizes,
    pca_min_components,
    pca_max_components,
    pca_min_explained_variance,
    min_reference_samples,
    max_outlier_fraction,
    min_reads_per_sample,
    min_corr_to_median,
    max_reconstruction_error_z,
    max_noise_mad_z,
    threads,
    workdir,
    summary_output,
    best_output,
    qc_output,
    plot_output,
    qc_stats_plot_output,
    inlier_samples_output,
    reference_output,
    logger,
    allowed_samples_file="",
    skip_build_reference=True,
    seed=42,
):
    logger.info(
        "start tuning: samples=%d bins=%s threads=%d pca=[%d,%d]",
        len(sample_ids),
        bin_sizes,
        threads,
        pca_min_components,
        pca_max_components,
    )

    bams = [Path(path) for path in bams]
    sample_ids = list(sample_ids)
    if len(bams) != len(sample_ids):
        raise ValueError("--bams and --sample-ids must contain the same number of items.")

    if allowed_samples_file:
        allowed_path = Path(allowed_samples_file)
        if not allowed_path.exists():
            raise FileNotFoundError(f"allowed samples file not found: {allowed_path}")
        allowed = {line.strip() for line in allowed_path.read_text(encoding="utf-8").splitlines() if line.strip()}
        keep_indices = [idx for idx, sample_id in enumerate(sample_ids) if sample_id in allowed]
        if not keep_indices:
            raise ValueError("No samples left after filtering by --allowed-samples-file.")
        sample_ids = [sample_ids[idx] for idx in keep_indices]
        bams = [bams[idx] for idx in keep_indices]

    if len(bams) < 3:
        raise ValueError("At least 3 samples are required for reference tuning.")

    bin_sizes = parse_int_list(bin_sizes)
    qc_cfg = {
        "min_reference_samples": min_reference_samples,
        "max_outlier_fraction": max_outlier_fraction,
        "min_reads_per_sample": min_reads_per_sample,
        "min_corr_to_median": min_corr_to_median,
        "max_reconstruction_error_z": max_reconstruction_error_z,
        "max_noise_mad_z": max_noise_mad_z,
    }

    workdir = Path(workdir)
    summary_output = Path(summary_output)
    best_output = Path(best_output)
    qc_output = Path(qc_output)
    plot_output = Path(plot_output)
    qc_stats_plot_output = Path(qc_stats_plot_output)
    inlier_samples_output = Path(inlier_samples_output)
    reference_output = Path(reference_output)

    rows = []
    per_bin_details = {}

    for binsize in bin_sizes:
        converted_dir = workdir / f"bin_{binsize}" / "converted"
        plot_path = workdir / f"bin_{binsize}" / "pca_elbow.svg"
        profile_path = workdir / f"bin_{binsize}" / "pca_profile.tsv"
        npz_paths = convert_all_bams(
            wisecondorx=wisecondorx,
            bams=bams,
            sample_ids=sample_ids,
            binsize=binsize,
            output_dir=converted_dir,
            threads=threads,
            logger=logger,
        )

        (
            usable_sample_ids,
            _usable_bams,
            usable_npz_paths,
            loaded_arrays,
            dropped_npz_samples,
        ) = filter_usable_npz(sample_ids, bams, npz_paths, logger, stage_tag=f"tuning/bin_{binsize}")
        usable_count = len(usable_sample_ids)
        if usable_count < 3:
            rows.append(
                {
                    "binsize": binsize,
                    "pca_components": 0,
                    "selected_pca": 0,
                    "elbow_pca": 0,
                    "cum_var": 0.0,
                    "component_var": 0.0,
                    "component_cum_var": 0.0,
                    "is_selected_pca": False,
                    "pca_profile_tsv": str(profile_path),
                    "cv_mse": None,
                    "inliers": 0,
                    "outliers": usable_count,
                    "outlier_fraction": 1.0 if usable_count > 0 else 0.0,
                    "signal_key": SIGNAL_KEY,
                    "samples": usable_count,
                    "features": 0,
                    "status": "FAIL_USABLE_SAMPLE_COUNT",
                }
            )
            continue

        raw_matrix, signal_key = build_matrix_from_loaded(loaded_arrays)
        raw_totals = raw_matrix.sum(axis=1)
        matrix = normalize_matrix(raw_matrix)
        sample_count, feature_count = matrix.shape
        sample_index = {sample_id: idx for idx, sample_id in enumerate(usable_sample_ids)}

        max_components = min(pca_max_components, sample_count - 1, feature_count)
        if max_components < 1:
            rows.append(
                {
                    "binsize": binsize,
                    "pca_components": 0,
                    "selected_pca": 0,
                    "elbow_pca": 0,
                    "cum_var": 0.0,
                    "component_var": 0.0,
                    "component_cum_var": 0.0,
                    "is_selected_pca": False,
                    "pca_profile_tsv": str(profile_path),
                    "cv_mse": None,
                    "inliers": 0,
                    "outliers": sample_count,
                    "outlier_fraction": 1.0,
                    "signal_key": signal_key,
                    "samples": sample_count,
                    "features": feature_count,
                    "status": "INVALID_PCA_COMPONENTS",
                }
            )
            continue

        standardized, vt, explained, cumulative = pca_profile(matrix, max_components)
        selected_pca, elbow_pca = choose_pca_components(
            cumulative=cumulative,
            min_components=min(pca_min_components, max_components),
            min_explained_variance=pca_min_explained_variance,
        )
        write_pca_profile_tsv(profile_path, explained, cumulative)
        write_pca_svg(plot_path, binsize, explained, cumulative, elbow_pca, pca_min_explained_variance)
        min_components = min(max(1, pca_min_components), max_components)
        for pca_components in range(min_components, max_components + 1):
            metrics = sample_qc_metrics(usable_sample_ids, matrix, raw_totals, standardized, vt, pca_components)
            inliers, outliers = label_outliers(metrics, qc_cfg)
            outlier_fraction = len(outliers) / max(len(metrics), 1)

            status = "PASS"
            cv_mse = None
            if len(inliers) < qc_cfg["min_reference_samples"]:
                status = "FAIL_INLIER_COUNT"
            elif outlier_fraction > qc_cfg["max_outlier_fraction"]:
                status = "FAIL_OUTLIER_FRACTION"
            else:
                inlier_indices = [sample_index[row["sample_id"]] for row in inliers]
                inlier_matrix = matrix[inlier_indices, :]
                effective_max_components = min(inlier_matrix.shape[0] - 1, inlier_matrix.shape[1])
                if pca_components > effective_max_components:
                    status = "FAIL_EFFECTIVE_PCA"
                else:
                    cv_mse = cross_validated_mse(inlier_matrix, pca_components, seed=seed)
                    if cv_mse is None:
                        status = "FAIL_CV"

            row = {
                "binsize": binsize,
                "pca_components": pca_components,
                "selected_pca": selected_pca,
                "elbow_pca": elbow_pca,
                "cum_var": float(cumulative[pca_components - 1]),
                "component_var": float(explained[pca_components - 1]),
                "component_cum_var": float(cumulative[pca_components - 1]),
                "is_selected_pca": bool(pca_components == selected_pca),
                "pca_profile_tsv": str(profile_path),
                "cv_mse": cv_mse,
                "inliers": len(inliers),
                "outliers": len(outliers),
                "outlier_fraction": outlier_fraction,
                "signal_key": signal_key,
                "samples": sample_count,
                "features": feature_count,
                "status": status,
            }
            rows.append(row)
            per_bin_details[(binsize, pca_components)] = {
                "metrics": metrics,
                "inliers": inliers,
                "outliers": outliers,
                "plot_path": plot_path,
                "sample_ids": usable_sample_ids,
                "npz_paths": usable_npz_paths,
                "selected_pca": selected_pca,
                "dropped_npz_samples": dropped_npz_samples,
            }

    write_summary(summary_output, rows)
    valid_rows = [row for row in rows if row["status"] == "PASS" and row["cv_mse"] is not None]
    if not valid_rows:
        raise ValueError("No (binsize, pca_components) pair passed strict QC and CV constraints.")

    best_row = sorted(valid_rows, key=lambda item: item["cv_mse"])[0]
    write_best_yaml(best_output, best_row)

    best_details = per_bin_details[(best_row["binsize"], best_row["pca_components"])]
    write_qc_table(qc_output, best_details["metrics"])
    write_inlier_samples(inlier_samples_output, best_details["metrics"])
    write_reference_qc_svg(qc_stats_plot_output, best_details["metrics"], qc_cfg)
    plot_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(best_details["plot_path"], plot_output)

    inlier_sample_ids = {row["sample_id"] for row in best_details["inliers"]}
    inlier_npz = [
        path
        for sample_id, path in zip(best_details["sample_ids"], best_details["npz_paths"])
        if sample_id in inlier_sample_ids
    ]
    if len(inlier_npz) < qc_cfg["min_reference_samples"]:
        raise ValueError("Best bin has insufficient inliers for final reference.")

    if not skip_build_reference:
        build_reference(
            wisecondorx=wisecondorx,
            binsize=best_row["binsize"],
            npz_paths=inlier_npz,
            reference_output=reference_output,
            threads=threads,
            logger=logger,
        )
    logger.info(
        "tuning completed: bins=%d best_binsize=%s best_pca=%s inliers=%d",
        len(bin_sizes),
        best_row["binsize"],
        best_row["pca_components"],
        len(inlier_npz),
    )


def main():
    parser = argparse.ArgumentParser(description="Tune WisecondorX bin size and PCA elbow with strict QC.")
    parser.add_argument("--wisecondorx", required=True)
    parser.add_argument("--bams", nargs="+", required=True)
    parser.add_argument("--sample-ids", nargs="+", required=True)
    parser.add_argument("--allowed-samples-file", default="")
    parser.add_argument("--bin-sizes", required=True)
    parser.add_argument("--pca-min-components", type=int, default=2)
    parser.add_argument("--pca-max-components", type=int, default=20)
    parser.add_argument("--pca-min-explained-variance", type=float, default=0.0)
    parser.add_argument("--min-reference-samples", type=int, default=8)
    parser.add_argument("--max-outlier-fraction", type=float, default=0.25)
    parser.add_argument("--min-reads-per-sample", type=float, default=3_000_000)
    parser.add_argument("--min-corr-to-median", type=float, default=0.9)
    parser.add_argument("--max-reconstruction-error-z", type=float, default=3.5)
    parser.add_argument("--max-noise-mad-z", type=float, default=3.5)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--best-output", required=True)
    parser.add_argument("--qc-output", required=True)
    parser.add_argument("--plot-output", required=True)
    parser.add_argument("--qc-stats-plot-output", required=True)
    parser.add_argument("--inlier-samples-output", required=True)
    parser.add_argument("--reference-output", required=True)
    parser.add_argument("--skip-build-reference", action="store_true")
    parser.add_argument("--log", required=True)
    args = parser.parse_args()
    logger = setup_logger("tune_wisecondorx_bin_pca", args.log)
    run_tune_wisecondorx(
        wisecondorx=args.wisecondorx,
        bams=args.bams,
        sample_ids=args.sample_ids,
        allowed_samples_file=args.allowed_samples_file,
        bin_sizes=args.bin_sizes,
        pca_min_components=args.pca_min_components,
        pca_max_components=args.pca_max_components,
        pca_min_explained_variance=args.pca_min_explained_variance,
        min_reference_samples=args.min_reference_samples,
        max_outlier_fraction=args.max_outlier_fraction,
        min_reads_per_sample=args.min_reads_per_sample,
        min_corr_to_median=args.min_corr_to_median,
        max_reconstruction_error_z=args.max_reconstruction_error_z,
        max_noise_mad_z=args.max_noise_mad_z,
        threads=args.threads,
        seed=args.seed,
        workdir=args.workdir,
        summary_output=args.summary_output,
        best_output=args.best_output,
        qc_output=args.qc_output,
        plot_output=args.plot_output,
        qc_stats_plot_output=args.qc_stats_plot_output,
        inlier_samples_output=args.inlier_samples_output,
        reference_output=args.reference_output,
        skip_build_reference=args.skip_build_reference,
        logger=logger,
    )


if __name__ == "__main__":
    main()
