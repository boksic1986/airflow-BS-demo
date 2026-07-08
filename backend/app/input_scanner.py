from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


class InputPathError(ValueError):
    pass


@dataclass(frozen=True)
class FastqCandidate:
    sample_id: str
    r1: str
    r2: str
    source_dir: str
    r1_size: int
    r2_size: int
    r1_mtime: float
    r2_mtime: float
    discovery_method: str = "server_path_scan"


@dataclass(frozen=True)
class ScanResult:
    pipeline: str
    rawdata_root: str
    truncated: bool
    items: list[FastqCandidate]


def ensure_allowed_path(path_value: str | Path, allowed_roots: list[str | Path]) -> Path:
    path = Path(path_value).expanduser().resolve()
    allowed = [Path(item).expanduser().resolve() for item in allowed_roots]
    if not allowed:
        raise InputPathError("No allowed input roots configured.")

    if not any(path == root or path.is_relative_to(root) for root in allowed):
        raise InputPathError(f"Path is outside allowed input roots: {path}")
    return path


def scan_fastq_candidates(
    *,
    rawdata_root: str | Path,
    allowed_roots: list[str | Path],
    max_samples: int = 200,
) -> ScanResult:
    if max_samples < 1:
        raise InputPathError("max_samples must be at least 1.")

    root = ensure_allowed_path(rawdata_root, allowed_roots)
    if not root.is_dir():
        raise InputPathError(f"rawdata_root is not a readable directory: {root}")

    items: list[FastqCandidate] = []
    for sample_dir in _iter_dirs(root):
        for sample_stem, r1, r2 in _paired_fastqs(sample_dir):
            if len(items) >= max_samples:
                return ScanResult(pipeline="pgta", rawdata_root=str(root), truncated=True, items=items)
            sample_id = _extract_terminal_repeated_token(sample_dir.name) or sample_stem
            items.append(_candidate(sample_id=sample_id, r1=r1, r2=r2, source_dir=sample_dir))

    return ScanResult(pipeline="pgta", rawdata_root=str(root), truncated=False, items=items)


def scan_nipt_batch_candidates(
    *,
    rawdata_root: str | Path,
    allowed_roots: list[str | Path],
    max_samples: int = 200,
) -> ScanResult:
    if max_samples < 1:
        raise InputPathError("max_samples must be at least 1.")

    root = ensure_allowed_path(rawdata_root, allowed_roots)
    if not root.is_dir():
        raise InputPathError(f"rawdata_root is not a readable directory: {root}")

    items: list[FastqCandidate] = []
    batch_dirs = _nipt_batch_dirs(root)
    for batch_dir in batch_dirs:
        for sample_stem, r1, r2 in _paired_nipt_clean_fastqs(batch_dir):
            if len(items) >= max_samples:
                return ScanResult(pipeline="nipt_docker", rawdata_root=str(root), truncated=True, items=items)
            items.append(
                _candidate(
                    sample_id=sample_stem,
                    r1=r1,
                    r2=r2,
                    source_dir=batch_dir,
                    discovery_method="nipt_docker_clean_scan",
                )
            )

    return ScanResult(pipeline="nipt_docker", rawdata_root=str(root), truncated=False, items=items)


def _iter_dirs(root: Path):
    yield root
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            yield path


def _paired_fastqs(sample_dir: Path) -> list[tuple[str, Path, Path]]:
    by_sample: dict[str, dict[str, Path]] = {}
    for path in sorted(sample_dir.iterdir()):
        if not path.is_file():
            continue
        parsed = _parse_fastq_name(path.name)
        if parsed is None:
            continue
        sample_stem, direction = parsed
        by_sample.setdefault(sample_stem, {})[direction] = path.resolve()

    pairs = []
    for sample_stem in sorted(by_sample):
        item = by_sample[sample_stem]
        if "R1" in item and "R2" in item:
            pairs.append((sample_stem, item["R1"], item["R2"]))
    return pairs


def _nipt_batch_dirs(root: Path) -> list[Path]:
    candidates = [path for path in _iter_dirs(root) if _paired_nipt_clean_fastqs(path)]
    selected: list[Path] = []
    for path in sorted(candidates, key=lambda item: (len(item.relative_to(root).parts), str(item))):
        if any(path != parent and path.is_relative_to(parent) for parent in selected):
            continue
        selected.append(path)
    return selected


def _paired_nipt_clean_fastqs(batch_dir: Path) -> list[tuple[str, Path, Path]]:
    by_sample: dict[str, dict[str, Path]] = {}
    for path in sorted(batch_dir.iterdir()):
        if not path.is_file():
            continue
        parsed = _parse_nipt_clean_fastq_name(path.name)
        if parsed is None:
            continue
        sample_stem, direction = parsed
        by_sample.setdefault(sample_stem, {})[direction] = path.resolve()

    pairs = []
    for sample_stem in sorted(by_sample):
        item = by_sample[sample_stem]
        if "R1" in item and "R2" in item:
            pairs.append((sample_stem, item["R1"], item["R2"]))
    return pairs


def _parse_fastq_name(name: str) -> tuple[str, str] | None:
    base = re.sub(r"(?i)\.(fastq|fq)(\.gz)?$", "", name)
    if base == name:
        return None

    match = re.search(r"(?i)(?:^|[._-])R?([12])(?:[._-]\d{3})?$", base)
    if not match:
        return None

    direction = "R1" if match.group(1) == "1" else "R2"
    sample_stem = base[: match.start()].rstrip("._-")
    if not sample_stem:
        return None
    return sample_stem, direction


def _parse_nipt_clean_fastq_name(name: str) -> tuple[str, str] | None:
    match = re.match(r"^(.+)\.R([12])\.clean\.fastq\.gz$", name)
    if not match:
        return None
    sample_stem = match.group(1).strip()
    if not sample_stem:
        return None
    direction = "R1" if match.group(2) == "1" else "R2"
    return sample_stem, direction


def _extract_terminal_repeated_token(name: str) -> str | None:
    match = re.search(r"[-_]([A-Za-z]*\d+|[A-Za-z]+)[-_]([A-Za-z]*\d+|[A-Za-z]+)$", name.strip())
    if not match:
        return None
    left = _normalize_sample_token(match.group(1))
    right = _normalize_sample_token(match.group(2))
    return left if left == right else None


def _normalize_sample_token(value: str) -> str:
    return value.strip().replace("_", "").replace(" ", "").upper()


def _candidate(
    *,
    sample_id: str,
    r1: Path,
    r2: Path,
    source_dir: Path,
    discovery_method: str = "server_path_scan",
) -> FastqCandidate:
    r1_stat = r1.stat()
    r2_stat = r2.stat()
    return FastqCandidate(
        sample_id=sample_id,
        r1=str(r1),
        r2=str(r2),
        source_dir=str(source_dir.resolve()),
        r1_size=r1_stat.st_size,
        r2_size=r2_stat.st_size,
        r1_mtime=r1_stat.st_mtime,
        r2_mtime=r2_stat.st_mtime,
        discovery_method=discovery_method,
    )
