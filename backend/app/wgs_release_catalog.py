from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re

import yaml


RELEASE_ID_RE = re.compile(r"^wgs-[0-9]+\.[0-9]+\.[0-9]+-[0-9a-f]{7}$")
SAFE_PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
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
    profile_id: str | None = None
    profile_revision: str | None = None
    profile_sha256: str | None = None
    cce_pipeline_version: str | None = None


@dataclass(frozen=True)
class WgsReleaseCatalog:
    release: WgsRelease
    releases: tuple[WgsRelease, ...] = ()

    def by_id(self, release_id: str) -> WgsRelease:
        for item in self.releases or (self.release,):
            if item.release_id == release_id:
                return item
        raise ValueError(f"WGS release is not cataloged: {release_id}")


def load_wgs_release_catalog(path: Path | str) -> WgsReleaseCatalog:
    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("WGS release catalog must be a mapping")
    schema_version = str(payload.get("schema_version") or "")
    if schema_version == "3":
        raw = payload.get("release")
        if not isinstance(raw, dict):
            raise ValueError("WGS release catalog requires one release mapping")
        release = _parse_release(raw)
        return WgsReleaseCatalog(release=release, releases=(release,))
    if schema_version != "4":
        raise ValueError("WGS release catalog schema_version must be 3 or 4")
    raw_releases = payload.get("releases")
    if not isinstance(raw_releases, list) or not raw_releases:
        raise ValueError("WGS release catalog requires releases")
    releases = tuple(_parse_release(raw) for raw in raw_releases if isinstance(raw, dict))
    if len(releases) != len(raw_releases):
        raise ValueError("WGS release catalog entries must be mappings")
    if len({item.release_id for item in releases}) != len(releases):
        raise ValueError("WGS release catalog contains duplicate release IDs")
    current_release_id = str(payload.get("current_release_id") or "")
    current = next(
        (item for item in releases if item.release_id == current_release_id),
        None,
    )
    if current is None:
        raise ValueError("WGS current_release_id is not cataloged")
    return WgsReleaseCatalog(release=current, releases=releases)


def _parse_release(raw: dict[str, object]) -> WgsRelease:
    release = WgsRelease(
        release_id=str(raw.get("release_id") or ""),
        version=str(raw.get("version") or ""),
        source_commit=str(raw.get("source_commit") or ""),
        bs10610_repo_path=str(raw.get("bs10610_repo_path") or ""),
        node200_repo_path=str(raw.get("node200_repo_path") or ""),
        rule_event_schema_version=str(raw.get("rule_event_schema_version") or ""),
        profile_id=str(raw.get("profile_id") or "") or None,
        profile_revision=str(raw.get("profile_revision") or "") or None,
        profile_sha256=str(raw.get("profile_sha256") or "") or None,
        cce_pipeline_version=str(raw.get("cce_pipeline_version") or "") or None,
    )
    _validate_release(release)
    return release


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
    for label, value in (
        ("profile_id", release.profile_id),
        ("profile_revision", release.profile_revision),
        ("cce_pipeline_version", release.cce_pipeline_version),
    ):
        if value is not None and SAFE_PROFILE_RE.fullmatch(value) is None:
            raise ValueError(f"WGS {label} is invalid")
    if release.profile_sha256 is not None:
        _validate_hex(release.profile_sha256, length=64, label="profile_sha256")


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
