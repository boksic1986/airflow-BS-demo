from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path


def build_subset(*, source_batch: Path, output_root: Path, sample_ids: list[str], read_pairs: int) -> dict:
    source_batch = source_batch.resolve()
    output_root = output_root.resolve()
    if read_pairs < 1:
        raise ValueError("read_pairs must be positive")
    if output_root == source_batch or output_root.is_relative_to(source_batch):
        raise ValueError("validation output must be outside the read-only source batch")

    output_root.mkdir(parents=True, exist_ok=True)
    records = []
    for sample_id in sample_ids:
        r1, r2 = resolve_pair(source_batch=source_batch, sample_id=sample_id)
        sample_dir = output_root / f"Sample_{sample_id}"
        sample_dir.mkdir(parents=True, exist_ok=True)
        out_r1 = sample_dir / f"{sample_id}_combined_R1.fastq.gz"
        out_r2 = sample_dir / f"{sample_id}_combined_R2.fastq.gz"
        count = copy_pairs(r1=r1, r2=r2, out_r1=out_r1, out_r2=out_r2, limit=read_pairs)
        records.append(
            {
                "sample_id": sample_id,
                "source_r1": str(r1),
                "source_r2": str(r2),
                "output_r1": str(out_r1),
                "output_r2": str(out_r2),
                "read_pairs": count,
                "output_r1_sha256": sha256_file(out_r1),
                "output_r2_sha256": sha256_file(out_r2),
            }
        )
    provenance = {
        "source_batch": str(source_batch),
        "selection": "deterministic prefix",
        "requested_read_pairs_per_sample": read_pairs,
        "samples": records,
    }
    (output_root / "validation_subset.provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return provenance


def resolve_pair(*, source_batch: Path, sample_id: str) -> tuple[Path, Path]:
    matches = []
    for stem in (sample_id, f"{sample_id}_combined"):
        for r1 in source_batch.rglob(f"{stem}_R1.fastq.gz"):
            r2 = r1.with_name(f"{stem}_R2.fastq.gz")
            if r2.is_file():
                matches.append((r1.resolve(), r2.resolve()))
    unique = sorted(set(matches))
    if len(unique) != 1:
        raise ValueError(f"sample_id={sample_id} resolved to {len(unique)} FASTQ pairs")
    return unique[0]


def copy_pairs(*, r1: Path, r2: Path, out_r1: Path, out_r2: Path, limit: int) -> int:
    count = 0
    with gzip.open(r1, "rt", encoding="ascii", errors="strict") as in_r1, gzip.open(
        r2, "rt", encoding="ascii", errors="strict"
    ) as in_r2, gzip.open(out_r1, "wt", encoding="ascii") as target_r1, gzip.open(
        out_r2, "wt", encoding="ascii"
    ) as target_r2:
        while count < limit:
            record_r1 = [in_r1.readline() for _ in range(4)]
            record_r2 = [in_r2.readline() for _ in range(4)]
            if not record_r1[0] and not record_r2[0]:
                break
            if not all(record_r1) or not all(record_r2):
                raise ValueError(f"truncated paired FASTQ near record {count + 1}: {r1}, {r2}")
            target_r1.writelines(record_r1)
            target_r2.writelines(record_r2)
            count += 1
    if count == 0:
        for path in (out_r1, out_r2):
            path.unlink(missing_ok=True)
        raise ValueError(f"empty paired FASTQ input: {r1}, {r2}")
    return count


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a read-only-derived PGT-A validation FASTQ subset.")
    parser.add_argument("--source-batch", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--sample-id", action="append", required=True, dest="sample_ids")
    parser.add_argument("--read-pairs", type=int, default=1_000_000)
    args = parser.parse_args()
    build_subset(
        source_batch=args.source_batch,
        output_root=args.output_root,
        sample_ids=args.sample_ids,
        read_pairs=args.read_pairs,
    )


if __name__ == "__main__":
    main()
