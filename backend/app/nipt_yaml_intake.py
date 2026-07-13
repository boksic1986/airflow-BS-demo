from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Any

import yaml

from app.input_scanner import FastqCandidate, scan_nipt_batch_candidates


MAX_REQUEST_BYTES = 64 * 1024
REQUEST_SUFFIX = ".nipt.yaml"
ALLOWED_FIELDS = {
    "version",
    "request_id",
    "project_id",
    "batch_id",
    "samples",
    "submitted_by",
    "runtime_profile_id",
    "run_mode",
    "cores",
    "submit",
}
REQUIRED_FIELDS = ALLOWED_FIELDS - {"submitted_by"}
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class NiptYamlIntakeError(ValueError):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: _UniqueKeyLoader, node, deep: bool = False):
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise NiptYamlIntakeError("NIPT request YAML mapping keys must be strings.")
        if key in mapping:
            raise NiptYamlIntakeError(f"Duplicate YAML key is not allowed: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


@dataclass(frozen=True)
class NiptYamlRequest:
    request_id: str
    project_id: str
    batch_id: str
    source_dir: str
    rawdata_root: str
    samples: list[FastqCandidate]
    submitted_by: str | None
    runtime_profile_id: str
    run_mode: str
    cores: int
    submit: bool
    fingerprint: str
    manifest_path: str


@dataclass(frozen=True)
class NiptYamlFailure:
    request_id: str
    manifest_path: str
    fingerprint: str
    message: str


@dataclass(frozen=True)
class NiptYamlScanResult:
    requests: list[NiptYamlRequest]
    errors: list[NiptYamlFailure]


def scan_nipt_yaml_request_results(
    *,
    inbox_root: str | Path,
    allowed_roots: list[str | Path],
    max_samples: int = 200,
    request_glob: str = f"*{REQUEST_SUFFIX}",
) -> NiptYamlScanResult:
    inbox = Path(inbox_root).expanduser().resolve()
    if not inbox.is_dir():
        raise NiptYamlIntakeError(f"NIPT request inbox is not a readable directory: {inbox}")
    roots = [Path(root).expanduser().resolve() for root in allowed_roots]
    if not roots:
        raise NiptYamlIntakeError("No approved NIPT FASTQ roots are configured.")

    requests: list[NiptYamlRequest] = []
    errors: list[NiptYamlFailure] = []
    for path in sorted(inbox.glob(request_glob)):
        if not path.is_file() or not path.name.endswith(REQUEST_SUFFIX):
            continue
        request_id = path.name[: -len(REQUEST_SUFFIX)]
        raw = path.read_bytes()
        failure_fingerprint = hashlib.sha256(raw).hexdigest()
        try:
            requests.append(
                _parse_request(
                    path=path,
                    raw=raw,
                    expected_request_id=request_id,
                    allowed_roots=roots,
                    max_samples=max_samples,
                )
            )
        except (NiptYamlIntakeError, OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            errors.append(
                NiptYamlFailure(
                    request_id=request_id,
                    manifest_path=str(path.resolve()),
                    fingerprint=failure_fingerprint,
                    message=str(exc),
                )
            )
    return NiptYamlScanResult(requests=requests, errors=errors)


def _parse_request(
    *,
    path: Path,
    raw: bytes,
    expected_request_id: str,
    allowed_roots: list[Path],
    max_samples: int,
) -> NiptYamlRequest:
    if len(raw) > MAX_REQUEST_BYTES:
        raise NiptYamlIntakeError(f"NIPT request exceeds {MAX_REQUEST_BYTES} bytes.")
    text = raw.decode("utf-8")
    _reject_advanced_yaml(text)
    loaded = yaml.load(text, Loader=_UniqueKeyLoader)
    if not isinstance(loaded, dict):
        raise NiptYamlIntakeError("NIPT request YAML root must be a mapping.")
    unknown = sorted(set(loaded) - ALLOWED_FIELDS)
    if unknown:
        raise NiptYamlIntakeError("NIPT request contains unknown fields: " + ", ".join(unknown))
    missing = sorted(REQUIRED_FIELDS - set(loaded))
    if missing:
        raise NiptYamlIntakeError("NIPT request is missing required fields: " + ", ".join(missing))

    if loaded["version"] != 1 or isinstance(loaded["version"], bool):
        raise NiptYamlIntakeError("version must be integer 1.")
    request_id = _identifier(loaded["request_id"], field="request_id")
    if request_id != expected_request_id:
        raise NiptYamlIntakeError(
            f"request_id must match file name {expected_request_id}{REQUEST_SUFFIX}."
        )
    project_id = _identifier(loaded["project_id"], field="project_id")
    batch_id = _identifier(loaded["batch_id"], field="batch_id")
    runtime_profile_id = _identifier(loaded["runtime_profile_id"], field="runtime_profile_id")
    if loaded["run_mode"] != "full_run":
        raise NiptYamlIntakeError("run_mode must be full_run for NIPT YAML intake.")
    cores = loaded["cores"]
    if isinstance(cores, bool) or not isinstance(cores, int) or not 1 <= cores <= 40:
        raise NiptYamlIntakeError("cores must be an integer between 1 and 40.")
    submit = loaded["submit"]
    if not isinstance(submit, bool):
        raise NiptYamlIntakeError("submit must be true or false.")
    submitted_by = loaded.get("submitted_by")
    if submitted_by is not None:
        submitted_by = _identifier(submitted_by, field="submitted_by")

    rawdata_root, source_dir = _resolve_batch(batch_id=batch_id, allowed_roots=allowed_roots)
    scan = scan_nipt_batch_candidates(
        rawdata_root=source_dir,
        allowed_roots=[rawdata_root],
        max_samples=max_samples + 1,
    )
    candidates = [item for item in scan.items if Path(item.source_dir).resolve() == source_dir]
    _validate_complete_pairs(source_dir)
    if not candidates:
        raise NiptYamlIntakeError(f"NIPT batch {batch_id} contains no complete clean FASTQ pairs.")
    selected = _select_samples(loaded["samples"], candidates)
    if len(selected) > max_samples:
        raise NiptYamlIntakeError(f"NIPT request exceeds max_samples={max_samples}.")

    normalized = {
        "version": 1,
        "request_id": request_id,
        "project_id": project_id,
        "batch_id": batch_id,
        "samples": [item.sample_id for item in selected],
        "submitted_by": submitted_by,
        "runtime_profile_id": runtime_profile_id,
        "run_mode": "full_run",
        "cores": cores,
        "submit": submit,
    }
    digest = hashlib.sha256(yaml.safe_dump(normalized, sort_keys=True).encode("utf-8"))
    for item in selected:
        digest.update(
            "\t".join(
                [
                    item.sample_id,
                    item.r1,
                    item.r2,
                    str(item.r1_size),
                    str(item.r2_size),
                    str(item.r1_mtime),
                    str(item.r2_mtime),
                ]
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return NiptYamlRequest(
        request_id=request_id,
        project_id=project_id,
        batch_id=batch_id,
        source_dir=str(source_dir),
        rawdata_root=str(rawdata_root),
        samples=selected,
        submitted_by=submitted_by,
        runtime_profile_id=runtime_profile_id,
        run_mode="full_run",
        cores=cores,
        submit=submit,
        fingerprint=digest.hexdigest(),
        manifest_path=str(path.resolve()),
    )


def _reject_advanced_yaml(text: str) -> None:
    for event in yaml.parse(text):
        if isinstance(event, yaml.events.AliasEvent) or getattr(event, "anchor", None) is not None:
            raise NiptYamlIntakeError("YAML aliases and anchors are not allowed.")
        tag = getattr(event, "tag", None)
        if tag and not str(tag).startswith("tag:yaml.org,2002:"):
            raise NiptYamlIntakeError("custom YAML tags are not allowed.")


def _identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
        raise NiptYamlIntakeError(
            f"{field} must use only letters, digits, dot, underscore, or hyphen and cannot contain a path."
        )
    return value


def _resolve_batch(*, batch_id: str, allowed_roots: list[Path]) -> tuple[Path, Path]:
    matches: list[tuple[Path, Path]] = []
    for root in allowed_roots:
        if not root.is_dir():
            continue
        if root.name == batch_id:
            matches.append((root, root))
        for candidate in root.rglob(batch_id):
            if candidate.is_dir() and candidate.name == batch_id:
                matches.append((root, candidate.resolve()))
    unique = {(str(root), str(batch)): (root, batch) for root, batch in matches}
    if not unique:
        raise NiptYamlIntakeError(f"batch_id {batch_id} was not found under approved NIPT FASTQ roots.")
    if len(unique) > 1:
        raise NiptYamlIntakeError(f"batch_id {batch_id} matches more than one approved NIPT batch.")
    return next(iter(unique.values()))


def _select_samples(value: Any, candidates: list[FastqCandidate]) -> list[FastqCandidate]:
    by_id = {item.sample_id: item for item in candidates}
    if value == "all":
        return [by_id[sample_id] for sample_id in sorted(by_id)]
    if not isinstance(value, list) or not value:
        raise NiptYamlIntakeError("samples must be all or a non-empty list of sample IDs.")
    requested = [_identifier(item, field="samples item") for item in value]
    if len(requested) != len(set(requested)):
        raise NiptYamlIntakeError("samples contains duplicate sample IDs.")
    missing = sorted(set(requested) - set(by_id))
    if missing:
        raise NiptYamlIntakeError("Requested samples are not present in the resolved batch: " + ", ".join(missing))
    return [by_id[sample_id] for sample_id in requested]


def _validate_complete_pairs(batch: Path) -> None:
    by_sample: dict[str, set[str]] = {}
    pattern = re.compile(r"^(.+)\.R([12])\.clean\.fastq\.gz$")
    for path in batch.iterdir():
        if not path.is_file():
            continue
        match = pattern.match(path.name)
        if match:
            by_sample.setdefault(match.group(1), set()).add(match.group(2))
    incomplete = sorted(sample_id for sample_id, reads in by_sample.items() if reads != {"1", "2"})
    if incomplete:
        raise NiptYamlIntakeError("NIPT batch has incomplete clean FASTQ pairs: " + ", ".join(incomplete))
