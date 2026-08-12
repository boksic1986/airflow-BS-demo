#!/usr/bin/env python3
"""Build the fixed production prepare-input manifest for an isolated run.

Frozen from CNVcalling commit 5e9d1053919fcc1c9bf2062641446a06c7a89de2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Sequence


INPUT_SCHEMA = "cnvcalling.prepare-input.v1"
PROFILE = "wgs-3.9.2-grch38"
REFERENCE_SCHEMA = "cnvcalling.reference-depth.v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_text(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _relative_parts(value: Path | str, label: str) -> tuple[str, ...]:
    text = os.fspath(value)
    pure = PurePosixPath(text)
    if (
        not text
        or "\\" in text
        or pure.is_absolute()
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise ValueError(f"{label}: unsafe relative path")
    return pure.parts


def _reject_symlink_components(root: Path, parts: Sequence[str], label: str) -> Path:
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label}: symlink paths are not allowed")
    return current


def _safe_file(root: Path, value: Path | str, label: str) -> Path:
    parts = _relative_parts(value, label)
    path = _reject_symlink_components(root, parts, label)
    if not path.is_file():
        raise ValueError(f"{label}: expected a regular file")
    return path


def _safe_directory(root: Path, value: Path | str, label: str) -> Path:
    parts = _relative_parts(value, label)
    path = _reject_symlink_components(root, parts, label)
    if not path.is_dir():
        raise ValueError(f"{label}: expected a directory")
    return path


def _safe_output(root: Path, value: Path | str) -> Path:
    parts = _relative_parts(value, "output")
    path = root.joinpath(*parts)
    if path.exists():
        raise FileExistsError(f"output already exists: {path}")
    _reject_symlink_components(root, parts[:-1], "output")
    if not path.parent.is_dir():
        raise ValueError("output: parent directory does not exist")
    return path


def _descriptor(path: Path, root: Path) -> dict[str, str]:
    return {
        "path": _relative_text(path, root),
        "sha256": _sha256(path),
    }


def _depth_samples(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        header_line = handle.readline()
    if not header_line:
        raise ValueError("depth: empty input")
    header = header_line.rstrip("\r\n").split("\t")
    if len(header) < 4 or header[:3] != ["chrom", "begin", "end"]:
        raise ValueError("depth: invalid header")
    samples = [
        re.sub(r"_dep$", "", column)
        for column in header[3:]
        if column.endswith("_dep")
    ]
    if (
        not samples
        or any(not sample for sample in samples)
        or len(set(samples)) != len(samples)
    ):
        raise ValueError("depth: expected unique non-empty _dep samples")
    return samples


def _fastq_sample(value: str) -> str:
    basename = Path(value).name
    basename = re.sub(r"\..*$", "", basename)
    return basename.replace("-R1", "").replace("-R2", "")


def _fastq_samples(path: Path) -> set[str]:
    samples: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\r\n").split("\t")
            if len(fields) not in (6, 8):
                raise ValueError(
                    f"fastq_count line {line_number}: expected 6 or 8 fields"
                )
            sample = _fastq_sample(fields[0])
            if not sample:
                raise ValueError(
                    f"fastq_count line {line_number}: empty sample"
                )
            samples.add(sample)
    if not samples:
        raise ValueError("fastq_count: no samples")
    return samples


def _log_paths(path: Path, samples: Sequence[str]) -> list[Path]:
    logs = sorted(
        (
            entry
            for entry in path.iterdir()
            if entry.name.endswith(".log")
        ),
        key=lambda entry: entry.name,
    )
    for log in logs:
        if log.is_symlink():
            raise ValueError("logs: symlink paths are not allowed")
        if not log.is_file():
            raise ValueError("logs: expected regular files")
    observed = [log.name[:-4] for log in logs]
    if set(observed) != set(samples) or len(observed) != len(samples):
        raise ValueError(
            "logs: sample drift; "
            f"expected {len(samples)}, got {len(observed)}"
        )
    by_sample = dict(zip(observed, logs))
    return [by_sample[sample] for sample in samples]


def _validate_reference_metadata(
    path: Path,
    current_samples: Sequence[str],
) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"reference metadata: {error}") from error
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != REFERENCE_SCHEMA
        or not isinstance(payload.get("samples"), list)
        or not payload["samples"]
        or any(
            not isinstance(sample, str) or not sample
            for sample in payload["samples"]
        )
        or len(set(payload["samples"])) != len(payload["samples"])
    ):
        raise ValueError("reference metadata: invalid sample identity")
    overlap = sorted(set(payload["samples"]).intersection(current_samples))
    if overlap:
        raise ValueError("reference metadata: sample drift overlaps current batch")


def build_manifest(
    *,
    root: Path | str,
    depth: Path | str,
    fastq_count: Path | str,
    logs_dir: Path | str,
    cytoband: Path | str,
    par: Path | str,
    gene_annotation: Path | str,
    reference_depth: Path | str,
    reference_metadata: Path | str,
    reference_sex: Path | str,
    output: Path | str,
) -> Path:
    run_root = Path(root)
    if run_root.is_symlink() or not run_root.is_dir():
        raise ValueError("root: expected a non-symlink directory")
    run_root = run_root.resolve(strict=True)

    depth_path = _safe_file(run_root, depth, "depth")
    fastq_path = _safe_file(run_root, fastq_count, "fastq_count")
    logs_path = _safe_directory(run_root, logs_dir, "logs")
    cytoband_path = _safe_file(run_root, cytoband, "cytoband")
    par_path = _safe_file(run_root, par, "par")
    gene_path = _safe_file(
        run_root,
        gene_annotation,
        "gene_annotation",
    )
    reference_depth_path = _safe_file(
        run_root,
        reference_depth,
        "reference_depth",
    )
    reference_metadata_path = _safe_file(
        run_root,
        reference_metadata,
        "reference_metadata",
    )
    reference_sex_path = _safe_file(
        run_root,
        reference_sex,
        "reference_sex",
    )
    output_path = _safe_output(run_root, output)

    samples = _depth_samples(depth_path)
    if _fastq_samples(fastq_path) != set(samples):
        raise ValueError("fastq_count: sample drift from depth _dep header")
    logs = _log_paths(logs_path, samples)
    _validate_reference_metadata(reference_metadata_path, samples)

    payload = {
        "schema": INPUT_SCHEMA,
        "profile": PROFILE,
        "samples": samples,
        "inputs": {
            "depth": _descriptor(depth_path, run_root),
            "fastq_count": _descriptor(fastq_path, run_root),
            "logs": [
                {
                    "sample": sample,
                    **_descriptor(log, run_root),
                }
                for sample, log in zip(samples, logs)
            ],
        },
        "reference": {
            "mode": "all",
            "depth_npy": _descriptor(reference_depth_path, run_root),
            "metadata_json": _descriptor(
                reference_metadata_path,
                run_root,
            ),
            "sex_tsv": _descriptor(reference_sex_path, run_root),
        },
        "resources": {
            "cytoband": _descriptor(cytoband_path, run_root),
            "par": _descriptor(par_path, run_root),
            "gene_annotation": _descriptor(gene_path, run_root),
        },
        "parameters": {
            "sex_cutoff": 0.0005,
            "corr_threshold": 0.78,
            "min_samples": 20,
            "max_samples": 40,
        },
    }

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{output_path.name}.staging-",
            dir=output_path.parent,
            delete=False,
        ) as handle:
            temporary_name = handle.name
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if output_path.exists():
            raise FileExistsError(f"output already exists: {output_path}")
        os.rename(temporary_name, output_path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    return output_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a fixed production cnvcompat prepare manifest."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--depth", required=True)
    parser.add_argument("--fastq-count", required=True)
    parser.add_argument("--logs-dir", required=True)
    parser.add_argument("--cytoband", required=True)
    parser.add_argument("--par", required=True)
    parser.add_argument("--gene-annotation", required=True)
    parser.add_argument("--reference-depth", required=True)
    parser.add_argument("--reference-metadata", required=True)
    parser.add_argument("--reference-sex", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    options = _parser().parse_args(argv)
    build_manifest(
        root=options.root,
        depth=options.depth,
        fastq_count=options.fastq_count,
        logs_dir=options.logs_dir,
        cytoband=options.cytoband,
        par=options.par,
        gene_annotation=options.gene_annotation,
        reference_depth=options.reference_depth,
        reference_metadata=options.reference_metadata,
        reference_sex=options.reference_sex,
        output=options.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
