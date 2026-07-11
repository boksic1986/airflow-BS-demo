from __future__ import annotations

import argparse
import csv
from pathlib import Path


def aggregate_qc(*, project_root, samples, output):
    root = Path(project_root)
    records = []
    for sample_id in samples:
        mapping = _read_one(root / "qc" / "mapping" / f"{sample_id}.mapping_qc.tsv")
        cnv = _read_one(root / "wisecondorx" / "cnv" / "qc" / f"{sample_id}.qc.tsv")
        cnv_status = str(cnv.get("status") or "UNKNOWN").lower()
        thresholds = {
            "total_counts": f">={cnv.get('threshold_min_total_counts', '')}",
            "nonzero_fraction": f">={cnv.get('threshold_min_nonzero_fraction', '')}",
            "mad_log1p": f"<={cnv.get('threshold_max_mad_log1p', '')}",
        }
        for name in ("raw_read_pairs", "clean_read_pairs", "mapped_reads", "mapping_rate", "estimated_depth_x"):
            records.append((sample_id, name, mapping.get(name, ""), "", "pass"))
        for name in ("total_counts", "nonzero_fraction", "mad_log1p"):
            records.append((sample_id, name, cnv.get(name, ""), thresholds[name], cnv_status))
        records.append((sample_id, "cnv_qc_decision", cnv.get("status", "UNKNOWN"), "PASS", cnv_status))
        records.append((sample_id, "cnv_qc_reason", cnv.get("reason", ""), "", cnv_status))
    _write_long_qc(Path(output), records)


def aggregate_prediction(*, project_root, samples, output):
    root = Path(project_root)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["sample_id", "prediction_status"])
        for sample_id in samples:
            status_path = root / "wisecondorx" / "cnv" / "predict" / f"{sample_id}.done"
            writer.writerow([sample_id, status_path.read_text(encoding="utf-8").strip()])


def _read_one(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return next(csv.DictReader(handle, delimiter="\t"))


def _write_long_qc(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["sample_id", "metric_name", "metric_value", "metric_numeric", "threshold", "status"])
        for sample_id, name, value, threshold, status in records:
            numeric = value if _is_number(value) else ""
            writer.writerow([sample_id, name, value, numeric, threshold, status])


def _is_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("qc", "prediction"))
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--samples", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    sample_ids = [item for item in args.samples.split(",") if item]
    if args.mode == "qc":
        aggregate_qc(project_root=args.project_root, samples=sample_ids, output=args.output)
    else:
        aggregate_prediction(project_root=args.project_root, samples=sample_ids, output=args.output)


if __name__ == "__main__":
    main()
