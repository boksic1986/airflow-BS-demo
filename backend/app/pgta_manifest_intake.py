from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
from pathlib import Path

from app.input_scanner import FastqCandidate


class ManifestIntakeError(ValueError):
    pass


@dataclass(frozen=True)
class PgtaManifestRequest:
    request_id: str
    project_id: str
    source_batch: str
    operator: str | None
    manifest_path: str
    fingerprint: str
    samples: list[FastqCandidate]


@dataclass(frozen=True)
class PgtaManifestFailure:
    request_id: str
    manifest_path: str
    fingerprint: str
    message: str


@dataclass(frozen=True)
class PgtaManifestScanResult:
    requests: list[PgtaManifestRequest]
    errors: list[PgtaManifestFailure]


def scan_pgta_manifest_requests(*, inbox_root: str | Path, data_root: str | Path) -> list[PgtaManifestRequest]:
    result = scan_pgta_manifest_request_results(inbox_root=inbox_root, data_root=data_root)
    if result.errors:
        raise ManifestIntakeError(result.errors[0].message)
    return result.requests


def scan_pgta_manifest_request_results(
    *, inbox_root: str | Path, data_root: str | Path
) -> PgtaManifestScanResult:
    inbox = Path(inbox_root).resolve()
    data = Path(data_root).resolve()
    if not inbox.is_dir():
        return PgtaManifestScanResult(requests=[], errors=[])
    if not data.is_dir():
        raise ManifestIntakeError(f"PGT-A data root is not readable: {data}")

    requests: list[PgtaManifestRequest] = []
    errors: list[PgtaManifestFailure] = []
    for manifest in sorted(inbox.glob("*.samples.tsv")):
        request_id = manifest.name[: -len(".samples.tsv")]
        if not request_id or not manifest.with_name(f"{request_id}.READY").is_file():
            continue
        manifest = manifest.resolve()
        try:
            requests.append(_parse_request(manifest=manifest, request_id=request_id, data_root=data))
        except (ManifestIntakeError, OSError, UnicodeError, csv.Error) as error:
            errors.append(
                PgtaManifestFailure(
                    request_id=request_id,
                    manifest_path=str(manifest),
                    fingerprint=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                    message=str(error),
                )
            )
    return PgtaManifestScanResult(requests=requests, errors=errors)


def _parse_request(*, manifest: Path, request_id: str, data_root: Path) -> PgtaManifestRequest:
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"project_id", "source_batch", "sample_id", "operator"}
        if set(reader.fieldnames or []) != required:
            raise ManifestIntakeError(
                f"Manifest {manifest.name} must contain exactly: project_id,source_batch,sample_id,operator"
            )
        rows = [{key: str(value or "").strip() for key, value in row.items()} for row in reader]
    if not rows:
        raise ManifestIntakeError(f"Manifest {manifest.name} has no samples.")

    project_ids = {row["project_id"] for row in rows if row["project_id"]}
    source_batches = {row["source_batch"] for row in rows if row["source_batch"]}
    operators = {row["operator"] for row in rows if row["operator"]}
    if len(project_ids) != 1 or len(source_batches) != 1 or len(operators) > 1:
        raise ManifestIntakeError("Manifest project_id, source_batch, and operator must be consistent across rows.")

    sample_ids = [row["sample_id"] for row in rows]
    if any(not sample_id for sample_id in sample_ids):
        raise ManifestIntakeError("Manifest contains an empty sample_id.")
    if len(sample_ids) != len(set(sample_ids)):
        raise ManifestIntakeError("Manifest contains duplicate sample_id values.")

    source_batch = next(iter(source_batches))
    source_dir = (data_root / source_batch).resolve()
    if source_dir == data_root or not source_dir.is_relative_to(data_root):
        raise ManifestIntakeError(f"source_batch escapes the configured data root: {source_batch}")
    if not source_dir.is_dir():
        raise ManifestIntakeError(f"source_batch is not a readable directory: {source_batch}")

    samples = [_resolve_sample(source_dir=source_dir, sample_id=sample_id) for sample_id in sample_ids]
    fingerprint = _fingerprint(manifest=manifest, samples=samples)
    return PgtaManifestRequest(
        request_id=request_id,
        project_id=next(iter(project_ids)),
        source_batch=source_batch,
        operator=next(iter(operators), None),
        manifest_path=str(manifest),
        fingerprint=fingerprint,
        samples=samples,
    )


def _resolve_sample(*, source_dir: Path, sample_id: str) -> FastqCandidate:
    matches: list[tuple[Path, Path]] = []
    expected_stems = {sample_id, f"{sample_id}_combined"}
    for r1 in source_dir.rglob("*.fastq.gz"):
        stem = r1.name[: -len("_R1.fastq.gz")] if r1.name.endswith("_R1.fastq.gz") else None
        if stem not in expected_stems:
            continue
        r2 = r1.with_name(f"{stem}_R2.fastq.gz")
        if r2.is_file():
            matches.append((r1.resolve(), r2.resolve()))
    if len(matches) != 1:
        raise ManifestIntakeError(
            f"sample_id={sample_id} must resolve to exactly one R1/R2 pair under {source_dir}; found {len(matches)}"
        )
    r1, r2 = matches[0]
    r1_stat = r1.stat()
    r2_stat = r2.stat()
    return FastqCandidate(
        sample_id=sample_id,
        r1=str(r1),
        r2=str(r2),
        source_dir=str(r1.parent),
        r1_size=r1_stat.st_size,
        r2_size=r2_stat.st_size,
        r1_mtime=r1_stat.st_mtime,
        r2_mtime=r2_stat.st_mtime,
        discovery_method="pgta_manifest_ready",
    )


def _fingerprint(*, manifest: Path, samples: list[FastqCandidate]) -> str:
    digest = hashlib.sha256(manifest.read_bytes())
    for sample in samples:
        digest.update(
            f"{sample.sample_id}\t{sample.r1}\t{sample.r1_size}\t{sample.r1_mtime}\t"
            f"{sample.r2}\t{sample.r2_size}\t{sample.r2_mtime}\n".encode("utf-8")
        )
    return digest.hexdigest()
