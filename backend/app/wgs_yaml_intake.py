from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Any

import yaml


MAX_REQUEST_BYTES = 64 * 1024
REQUEST_SUFFIX = ".wgs.yaml"
ALLOWED_FIELDS = {
    "version",
    "request_id",
    "project",
    "operator",
    "precalling_config",
    "downstream_config",
    "targets",
    "stage",
    "submit",
}
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
FASTQ_SUFFIXES = (".fq.gz", ".fastq.gz")
PAIR_PATTERN = re.compile(r"^(.+?)[._]R([12])(?:[._].*)?\.(?:fastq|fq)\.gz$")


class WgsYamlIntakeError(ValueError):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: _UniqueKeyLoader, node, deep: bool = False):
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise WgsYamlIntakeError("WGS request YAML mapping keys must be strings.")
        if key in mapping:
            raise WgsYamlIntakeError(f"Duplicate YAML key is not allowed: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


@dataclass(frozen=True)
class WgsYamlRequest:
    request_id: str
    project: str
    operator: str
    precalling_config_path: str
    downstream_config_path: str
    targets_path: str
    stage: str
    submit: bool
    sample_count: int
    fastq_file_count: int
    total_bytes: int
    max_mtime_ns: int
    fingerprint: str
    manifest_path: str


@dataclass(frozen=True)
class WgsYamlFailure:
    request_id: str
    manifest_path: str
    fingerprint: str
    message: str


@dataclass(frozen=True)
class WgsYamlScanResult:
    requests: list[WgsYamlRequest]
    errors: list[WgsYamlFailure]


def scan_wgs_yaml_request_results(
    *,
    inbox_root: str | Path,
    allowed_roots: list[str | Path],
    request_glob: str = f"*{REQUEST_SUFFIX}",
) -> WgsYamlScanResult:
    inbox = Path(inbox_root).expanduser().resolve()
    if not inbox.is_dir():
        raise WgsYamlIntakeError(f"WGS request inbox is not a readable directory: {inbox}")
    roots = [Path(root).expanduser().resolve() for root in allowed_roots]
    if not roots:
        raise WgsYamlIntakeError("No approved WGS config roots are configured.")

    requests: list[WgsYamlRequest] = []
    errors: list[WgsYamlFailure] = []
    for path in sorted(inbox.glob(request_glob)):
        if not path.is_file() or not path.name.endswith(REQUEST_SUFFIX):
            continue
        request_id = path.name[: -len(REQUEST_SUFFIX)]
        if not (inbox / f"{request_id}.READY").is_file():
            continue
        raw = path.read_bytes()
        failure_fingerprint = hashlib.sha256(raw).hexdigest()
        try:
            requests.append(
                _parse_request(
                    path=path,
                    raw=raw,
                    expected_request_id=request_id,
                    approved_roots=roots,
                )
            )
        except (WgsYamlIntakeError, OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            errors.append(
                WgsYamlFailure(
                    request_id=request_id,
                    manifest_path=str(path),
                    fingerprint=failure_fingerprint,
                    message=str(exc),
                )
            )
    return WgsYamlScanResult(requests=requests, errors=errors)


def _parse_request(
    *,
    path: Path,
    raw: bytes,
    expected_request_id: str,
    approved_roots: list[Path],
) -> WgsYamlRequest:
    if len(raw) > MAX_REQUEST_BYTES:
        raise WgsYamlIntakeError(f"WGS request exceeds {MAX_REQUEST_BYTES} bytes.")
    text = raw.decode("utf-8")
    _reject_advanced_yaml(text)
    loaded = yaml.load(text, Loader=_UniqueKeyLoader)
    if not isinstance(loaded, dict):
        raise WgsYamlIntakeError("WGS request YAML root must be a mapping.")
    unknown = sorted(set(loaded) - ALLOWED_FIELDS)
    if unknown:
        raise WgsYamlIntakeError("WGS request contains unknown fields: " + ", ".join(unknown))
    missing = sorted(ALLOWED_FIELDS - set(loaded))
    if missing:
        raise WgsYamlIntakeError("WGS request is missing required fields: " + ", ".join(missing))
    if loaded["version"] != 1 or isinstance(loaded["version"], bool):
        raise WgsYamlIntakeError("version must be integer 1.")
    request_id = _identifier(loaded["request_id"], field="request_id")
    if request_id != expected_request_id:
        raise WgsYamlIntakeError(f"request_id must match file name {expected_request_id}{REQUEST_SUFFIX}.")
    project = _identifier(loaded["project"], field="project")
    operator = _identifier(loaded["operator"], field="operator")
    stage = str(loaded["stage"] or "")
    if stage not in {"precalling", "full"}:
        raise WgsYamlIntakeError("stage must be precalling or full.")
    submit = loaded["submit"]
    if not isinstance(submit, bool):
        raise WgsYamlIntakeError("submit must be true or false.")

    pre = _approved_file(loaded["precalling_config"], approved_roots, "precalling_config")
    down = _approved_file(loaded["downstream_config"], approved_roots, "downstream_config")
    targets = _approved_file(loaded["targets"], approved_roots, "targets")
    pre_config = _read_mapping(pre)
    _read_mapping(down)
    sample_info = _approved_file(pre_config.get("sample_info"), approved_roots, "sample_info")
    fastq_dir = _approved_directory(pre_config.get("fastqDir"), approved_roots, "fastqDir")
    sample_count = _sample_count(sample_info)
    fastqs = sorted(
        item.resolve()
        for item in fastq_dir.iterdir()
        if item.is_file() and item.name.endswith(FASTQ_SUFFIXES)
    )
    _validate_fastq_pairs(fastqs)

    digest = hashlib.sha256(raw)
    for artifact in (pre, down, targets, sample_info):
        digest.update(str(artifact).encode("utf-8"))
        digest.update(hashlib.sha256(artifact.read_bytes()).digest())
    total_bytes = 0
    max_mtime_ns = 0
    for fastq in fastqs:
        stat = fastq.stat()
        total_bytes += stat.st_size
        max_mtime_ns = max(max_mtime_ns, stat.st_mtime_ns)
        digest.update(
            f"{fastq}\t{stat.st_size}\t{stat.st_mtime_ns}\n".encode("utf-8")
        )
    return WgsYamlRequest(
        request_id=request_id,
        project=project,
        operator=operator,
        precalling_config_path=str(pre),
        downstream_config_path=str(down),
        targets_path=str(targets),
        stage=stage,
        submit=submit,
        sample_count=sample_count,
        fastq_file_count=len(fastqs),
        total_bytes=total_bytes,
        max_mtime_ns=max_mtime_ns,
        fingerprint=digest.hexdigest(),
        manifest_path=str(path.resolve()),
    )


def _approved_file(value: Any, roots: list[Path], label: str) -> Path:
    path = Path(str(value or "")).expanduser().resolve()
    if not any(path == root or path.is_relative_to(root) for root in roots):
        raise WgsYamlIntakeError(f"{label} is outside approved roots: {path}")
    if not path.is_file():
        raise WgsYamlIntakeError(f"{label} is not a readable file: {path}")
    return path


def _approved_directory(value: Any, roots: list[Path], label: str) -> Path:
    path = Path(str(value or "")).expanduser().resolve()
    if not any(path == root or path.is_relative_to(root) for root in roots):
        raise WgsYamlIntakeError(f"{label} is outside approved roots: {path}")
    if not path.is_dir():
        raise WgsYamlIntakeError(f"{label} is not a readable directory: {path}")
    return path


def _read_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise WgsYamlIntakeError(f"WGS config must be a YAML mapping: {path}")
    return payload


def _sample_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        next(reader, None)
        count = sum(1 for row in reader if row and any(str(value).strip() for value in row))
    if count < 1:
        raise WgsYamlIntakeError("WGS sample_info contains no sample rows.")
    return count


def _validate_fastq_pairs(paths: list[Path]) -> None:
    pairs: dict[str, set[str]] = {}
    for path in paths:
        match = PAIR_PATTERN.match(path.name)
        if match:
            pairs.setdefault(match.group(1), set()).add(match.group(2))
    if not pairs:
        raise WgsYamlIntakeError("WGS fastqDir contains no recognizable R1/R2 FASTQ pairs.")
    incomplete = sorted(sample for sample, reads in pairs.items() if reads != {"1", "2"})
    if incomplete:
        raise WgsYamlIntakeError("WGS fastqDir has incomplete FASTQ pairs: " + ", ".join(incomplete))


def _identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
        raise WgsYamlIntakeError(
            f"{field} must use only letters, digits, dot, underscore, or hyphen and cannot contain a path."
        )
    return value


def _reject_advanced_yaml(text: str) -> None:
    for event in yaml.parse(text):
        if isinstance(event, yaml.events.AliasEvent) or getattr(event, "anchor", None) is not None:
            raise WgsYamlIntakeError("YAML aliases and anchors are not allowed.")
        tag = getattr(event, "tag", None)
        if tag and not str(tag).startswith("tag:yaml.org,2002:"):
            raise WgsYamlIntakeError("custom YAML tags are not allowed.")
