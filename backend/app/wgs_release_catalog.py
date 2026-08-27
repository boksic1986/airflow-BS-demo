from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re

import yaml


RELEASE_ID_RE = re.compile(r"^wgs-[0-9]+\.[0-9]+\.[0-9]+-[0-9a-f]{7}$")
BS10610_PROJECT_ROOT = PurePosixPath(
    "/mnt/biodevrwbi/33.chenjiucheng/project"
)
NODE200_PROJECT_ROOT = PurePosixPath("/bi/biodevrwbi/33.chenjiucheng/project")


@dataclass(frozen=True)
class WgsRelease:
    release_id: str
    version: str
    source_commit: str
    bs10610_repo_path: str
    node200_repo_path: str
    rule_event_schema_version: str


@dataclass(frozen=True)
class WgsReleaseCatalog:
    release: WgsRelease


def load_wgs_release_catalog(path: Path | str) -> WgsReleaseCatalog:
    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or str(payload.get("schema_version")) != "3":
        raise ValueError("WGS release catalog schema_version must be 3")
    raw = payload.get("release")
    if not isinstance(raw, dict):
        raise ValueError("WGS release catalog requires one release mapping")
    release = WgsRelease(
        release_id=str(raw.get("release_id") or ""),
        version=str(raw.get("version") or ""),
        source_commit=str(raw.get("source_commit") or ""),
        bs10610_repo_path=str(raw.get("bs10610_repo_path") or ""),
        node200_repo_path=str(raw.get("node200_repo_path") or ""),
        rule_event_schema_version=str(raw.get("rule_event_schema_version") or ""),
    )
    _validate_release(release)
    return WgsReleaseCatalog(release=release)


def _validate_release(release: WgsRelease) -> None:
    if RELEASE_ID_RE.fullmatch(release.release_id) is None:
        raise ValueError("WGS release_id must be wgs-X.Y.Z-<7 hex>")
    if not release.version.startswith("V") or not release.version[1:]:
        raise ValueError("WGS version must start with V")
    _validate_hex(release.source_commit, length=40, label="source_commit")
    if release.release_id.rsplit("-", 1)[-1] != release.source_commit[:7]:
        raise ValueError("WGS release_id commit prefix must match source_commit")
    _validate_repo_path(
        release.bs10610_repo_path,
        root=BS10610_PROJECT_ROOT,
        label="BS10610",
    )
    _validate_repo_path(
        release.node200_repo_path,
        root=NODE200_PROJECT_ROOT,
        label="node200",
    )
    if PurePosixPath(release.bs10610_repo_path).name != PurePosixPath(
        release.node200_repo_path
    ).name:
        raise ValueError("BS10610 and node200 WGS repositories must identify the same directory")
    if release.rule_event_schema_version not in {"1", "rule-event.v1"}:
        raise ValueError("unsupported Rule event schema version")


def _validate_repo_path(value: str, *, root: PurePosixPath, label: str) -> None:
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts or root not in path.parents:
        raise ValueError(f"{label} WGS repository must be below {root}")
    if not path.name.startswith("wgs-"):
        raise ValueError(f"{label} WGS repository must be a versioned wgs-* path")


def _validate_hex(value: str, *, length: int, label: str) -> None:
    if len(value) != length or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{label} must be {length} lowercase hexadecimal characters")
