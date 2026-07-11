from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess


def collect_mapping_qc(*, sample_id, fastp_json, bam, reference, samtools, output):
    fastp = json.loads(Path(fastp_json).read_text(encoding="utf-8"))
    before = (fastp.get("summary") or {}).get("before_filtering") or {}
    after = (fastp.get("summary") or {}).get("after_filtering") or {}
    flagstat = subprocess.run([samtools, "flagstat", bam], text=True, capture_output=True, check=True).stdout
    stats = subprocess.run([samtools, "stats", bam], text=True, capture_output=True, check=True).stdout
    total_reads = int(before.get("total_reads") or 0)
    clean_reads = int(after.get("total_reads") or 0)
    mapped_reads, mapping_rate = _flagstat_mapping(flagstat)
    mapped_bases = _stats_value(stats, "bases mapped (cigar)")
    reference_bases = _reference_bases(Path(reference))
    estimated_depth = mapped_bases / reference_bases if reference_bases else 0.0
    row = {
        "sample_id": sample_id,
        "raw_read_pairs": total_reads // 2,
        "clean_read_pairs": clean_reads // 2,
        "mapped_reads": mapped_reads,
        "mapping_rate": mapping_rate,
        "estimated_depth_x": estimated_depth,
    }
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "sample_id\traw_read_pairs\tclean_read_pairs\tmapped_reads\tmapping_rate\testimated_depth_x\n"
        + f"{sample_id}\t{row['raw_read_pairs']}\t{row['clean_read_pairs']}\t{mapped_reads}\t{mapping_rate:.6f}\t{estimated_depth:.6f}\n",
        encoding="utf-8",
    )
    return row


def _flagstat_mapping(text):
    for line in text.splitlines():
        if " mapped (" not in line:
            continue
        mapped = int(line.split("+", 1)[0].strip())
        match = re.search(r"\(([-0-9.]+)%", line)
        return mapped, (float(match.group(1)) / 100.0 if match else 0.0)
    return 0, 0.0


def _stats_value(text, label):
    prefix = f"SN\t{label}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return float(line.split("\t")[2])
    return 0.0


def _reference_bases(reference):
    fai = Path(str(reference) + ".fai")
    if not fai.is_file():
        return 0
    return sum(int(line.split("\t")[1]) for line in fai.read_text(encoding="utf-8").splitlines() if line.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--fastp-json", required=True)
    parser.add_argument("--bam", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--samtools", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    collect_mapping_qc(**vars(args))


if __name__ == "__main__":
    main()
