#!/usr/bin/env python3
"""Build CNV native manifests and publish the legacy WGS file contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Iterable, Mapping, Sequence


RESULTS_SCHEMA = "cnvcalling.sample-results.v1"
SAMPLE_SCHEMA = "cnvcalling.sample-call.v1"
FINALIZE_SCHEMA = "cnvcalling.finalize.v1"
PUBLISH_SCHEMA = "wgs3.9.2.cnv-native-publish.v1"
SAMPLE_OUTPUTS = (
    "{sample}_raw_seg.tsv",
    "{sample}_NoFilt_seg.tsv",
    "{sample}_seg.tsv",
    "{sample}.normalize.bed",
    "{sample}.CN.bed",
    "{sample}_ploidy.tsv",
    "{sample}.log2r.mapd.tsv",
    "{sample}.log2r.mapd.summary.tsv",
)
PREPARE_OUTPUTS = ("mappingQC.csv", "corrQC.matridx.csv", "corrQC.tsv")
FINALIZE_OUTPUTS = (
    "All.chrom.CN.tsv",
    "merge.bed",
    "All.join.log2r.bed.gz",
    "All.join.log2r.bed.gz.tbi",
    "All.join.log2r.with_chr.bed.gz",
    "All.join.log2r.with_chr.bed.gz.tbi",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular_file(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label}: expected a regular non-symlink file")
    return path


def load_json(path: Path, label: str) -> Mapping[str, object]:
    regular_file(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{label}: invalid JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected an object")
    return value


def descriptor(path: Path, root: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def atomic_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def assignments(values: Iterable[str], label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{label}: expected NAME=VALUE")
        key, item = value.split("=", 1)
        if not key or not item or key in result:
            raise ValueError(f"{label}: invalid or duplicate assignment")
        result[key] = item
    return result


def build_results(
    root: Path,
    sample_states: Mapping[str, str],
    pedigree: Mapping[str, str],
    output: Path,
) -> None:
    root = root.resolve(strict=True)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("root: expected a non-symlink directory")
    samples = list(sample_states)
    if not samples or set(samples) != set(pedigree):
        raise ValueError("sample and pedigree identity drift")
    entries = []
    for sample in samples:
        state = regular_file(root / sample_states[sample], f"state {sample}")
        state_document = load_json(state, f"state {sample}")
        if (
            state_document.get("schema") != SAMPLE_SCHEMA
            or state_document.get("sample") != sample
        ):
            raise ValueError(f"state {sample}: identity drift")
        entries.append(
            {
                "sample": sample,
                "path": state.relative_to(root).as_posix(),
                "sha256": sha256(state),
            }
        )
    atomic_json(
        output,
        {
            "schema": RESULTS_SCHEMA,
            "samples": samples,
            "pedigree": {sample: pedigree[sample] for sample in samples},
            "results": entries,
        },
    )


def format_segments(source: Path, output: Path, mos_ratio_min: float) -> None:
    regular_file(source, "segments")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with source.open("r", encoding="utf-8", newline="") as in_handle:
            reader = csv.DictReader(in_handle, delimiter="\t")
            required = {
                "chrom",
                "start",
                "end",
                "CopyNumber",
                "zScore",
                "type",
                "MosRatio",
            }
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError("segments: schema drift")
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as out:
                writer = csv.writer(out, delimiter="\t", lineterminator="\n")
                for line_number, row in enumerate(reader, 2):
                    try:
                        selected = float(row["MosRatio"]) > mos_ratio_min
                    except ValueError as error:
                        raise ValueError(
                            f"segments line {line_number}: invalid MosRatio"
                        ) from error
                    if selected:
                        writer.writerow(
                            (
                                row["chrom"],
                                row["start"],
                                row["end"],
                                row["CopyNumber"],
                                row["zScore"],
                                "-" if row["type"] == "DEL" else "+",
                            )
                        )
                out.flush()
                os.fsync(out.fileno())
        os.replace(temporary, output)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_manifest_output(
    manifest: Mapping[str, object], source: Path, name: str, label: str
) -> None:
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict) or not isinstance(outputs.get(name), dict):
        raise ValueError(f"{label}: missing output {name}")
    expected = outputs[name].get("sha256")
    if expected != sha256(source):
        raise ValueError(f"{label}: SHA256 mismatch for {name}")


def publish_file(source: Path, destination: Path) -> None:
    regular_file(source, source.name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        regular_file(destination, destination.name)
        if sha256(destination) == sha256(source):
            return
        raise FileExistsError(f"destination differs: {destination}")
    fd, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    os.close(fd)
    try:
        shutil.copyfile(source, temporary)
        with open(temporary, "rb+") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def publish(
    prepare_dir: Path,
    samples_root: Path,
    finalize_dir: Path,
    samples: Sequence[str],
    output_root: Path,
) -> None:
    prepare_manifest = load_json(
        prepare_dir / "prepare-manifest.json", "prepare manifest"
    )
    if prepare_manifest.get("samples") != list(samples):
        raise ValueError("prepare sample identity drift")
    finalize_manifest = load_json(
        finalize_dir / "finalize-state.json", "finalize manifest"
    )
    if (
        finalize_manifest.get("schema") != FINALIZE_SCHEMA
        or finalize_manifest.get("samples") != list(samples)
    ):
        raise ValueError("finalize identity drift")

    published: list[Path] = []
    for name in PREPARE_OUTPUTS:
        source = regular_file(prepare_dir / name, f"prepare {name}")
        destination = output_root / name
        publish_file(source, destination)
        published.append(destination)

    for sample in samples:
        sample_dir = samples_root / sample
        state = load_json(sample_dir / "sample-result.json", f"sample {sample}")
        if state.get("schema") != SAMPLE_SCHEMA or state.get("sample") != sample:
            raise ValueError(f"sample {sample}: identity drift")
        for pattern in SAMPLE_OUTPUTS:
            name = pattern.format(sample=sample)
            source = regular_file(sample_dir / name, f"sample {sample} {name}")
            verify_manifest_output(state, source, name, f"sample {sample}")
            destination = output_root / name
            publish_file(source, destination)
            published.append(destination)

    finalize_names = list(FINALIZE_OUTPUTS) + [
        f"{sample}.ctrl.copynumber.txt" for sample in samples
    ]
    for name in finalize_names:
        source = regular_file(finalize_dir / name, f"finalize {name}")
        verify_manifest_output(finalize_manifest, source, name, "finalize")
        destination = output_root / name
        publish_file(source, destination)
        published.append(destination)

    state_path = output_root / "native-publish.json"
    atomic_json(
        state_path,
        {
            "schema": PUBLISH_SCHEMA,
            "samples": list(samples),
            "outputs": {
                path.name: descriptor(path, output_root) for path in published
            },
        },
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="command", required=True)
    results = sub.add_parser("build-results")
    results.add_argument("--root", required=True, type=Path)
    results.add_argument("--sample-state", action="append", required=True)
    results.add_argument("--pedigree", action="append", required=True)
    results.add_argument("--output", required=True, type=Path)
    segments = sub.add_parser("format-segments")
    segments.add_argument("--input", required=True, type=Path)
    segments.add_argument("--output", required=True, type=Path)
    segments.add_argument("--mos-ratio-min", type=float, default=0.3)
    publish_parser = sub.add_parser("publish")
    publish_parser.add_argument("--prepare-dir", required=True, type=Path)
    publish_parser.add_argument("--samples-root", required=True, type=Path)
    publish_parser.add_argument("--finalize-dir", required=True, type=Path)
    publish_parser.add_argument("--sample", action="append", required=True)
    publish_parser.add_argument("--output-root", required=True, type=Path)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    options = parser().parse_args(argv)
    if options.command == "build-results":
        build_results(
            options.root,
            assignments(options.sample_state, "sample-state"),
            assignments(options.pedigree, "pedigree"),
            options.output,
        )
    elif options.command == "format-segments":
        format_segments(options.input, options.output, options.mos_ratio_min)
    else:
        publish(
            options.prepare_dir,
            options.samples_root,
            options.finalize_dir,
            options.sample,
            options.output_root,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
