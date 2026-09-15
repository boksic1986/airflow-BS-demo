from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Iterator, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml

from app.wgs_release_catalog import load_wgs_release_catalog, parse_wgs_release

try:
    import fcntl
except ImportError:  # pragma: no cover - deployment and acceptance are Linux
    fcntl = None


SHA256_PATTERN = r"^[0-9a-f]{64}$"
RECEIPT_KEY = "registration_receipt"


class WgsManagedRelease(BaseModel):
    model_config = ConfigDict(extra="forbid")

    release_id: str
    version: str
    source_commit: str
    bs10610_repo_path: str
    node200_repo_path: str
    rule_event_schema_version: str
    profile_id: str = Field(min_length=1)
    profile_revision: str = Field(min_length=1)
    profile_sha256: str = Field(pattern=SHA256_PATTERN)
    cce_pipeline_version: str = Field(min_length=1)
    node200_profile_path: str = Field(min_length=1)
    pipeline_build_sha256: str = Field(pattern=SHA256_PATTERN)
    resource_manifest_sha256: str = Field(pattern=SHA256_PATTERN)


class WgsManagedAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    release_id: str = Field(min_length=1, pattern=r"^.*\S.*$")
    asset_manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    profile_id: str
    profile_revision: str
    profile_sha256: str = Field(pattern=SHA256_PATTERN)
    source_commit: str
    pipeline_build_sha256: str = Field(pattern=SHA256_PATTERN)
    resource_manifest_sha256: str = Field(pattern=SHA256_PATTERN)
    status: Literal["PASS"]
    state_verified: Literal[True]


class WgsReleaseRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["cce-release.v1"]
    release: WgsManagedRelease
    assets: WgsManagedAssets
    receipt_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_release_receipt(self):
        release = self.release.model_dump()
        parse_wgs_release(release)
        assets = self.assets.model_dump()
        for field in (
            "profile_id",
            "profile_revision",
            "profile_sha256",
            "source_commit",
            "pipeline_build_sha256",
            "resource_manifest_sha256",
        ):
            if assets[field] != release[field]:
                raise ValueError(f"assets.{field} must match release.{field}")
        if self.receipt_sha256 != receipt_sha256(self):
            raise ValueError("receipt_sha256 does not match the canonical payload")
        return self


class WgsReleaseActivation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_sha256: str = Field(pattern=SHA256_PATTERN)
    expected_current_release_id: str


class WgsReleaseManagementError(ValueError):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def receipt_sha256(registration: WgsReleaseRegistration) -> str:
    unsigned = registration.model_dump(exclude={"receipt_sha256"})
    encoded = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_release_writes_enabled(settings) -> None:
    if not bool(getattr(settings, "wgs_release_management_enabled", False)):
        raise WgsReleaseManagementError(
            status_code=409,
            code="WGS_RELEASE_MANAGEMENT_DISABLED",
            message="WGS release management is disabled.",
        )
    if not bool(getattr(settings, "auth_required", False)):
        raise WgsReleaseManagementError(
            status_code=409,
            code="WGS_RELEASE_MANAGEMENT_REQUIRES_AUTH",
            message="WGS release writes require AUTH_REQUIRED=true.",
        )


def register_wgs_release(
    path: Path | str, registration: WgsReleaseRegistration
) -> dict[str, object]:
    source = Path(path)
    with _catalog_lock(source):
        payload = _load_schema4_payload(source)
        releases = payload["releases"]
        incoming = registration.release.model_dump()
        receipt = registration.model_dump()
        existing = next(
            (
                row
                for row in releases
                if isinstance(row, dict)
                and str(row.get("release_id") or "") == incoming["release_id"]
            ),
            None,
        )
        replayed = False
        changed = False
        if existing is None:
            releases.append({**incoming, RECEIPT_KEY: receipt})
            changed = True
        else:
            if any(existing.get(key) != value for key, value in incoming.items()):
                raise _conflict(incoming["release_id"])
            stored_receipt = existing.get(RECEIPT_KEY)
            if stored_receipt is None:
                existing[RECEIPT_KEY] = receipt
                changed = True
            elif stored_receipt != receipt:
                raise _conflict(incoming["release_id"])
            else:
                replayed = True
        if changed:
            _atomic_write_catalog(source, payload)
        return {
            "status": "registered",
            "release_id": incoming["release_id"],
            "receipt_sha256": registration.receipt_sha256,
            "active": payload["current_release_id"] == incoming["release_id"],
            "replayed": replayed,
        }


def activate_wgs_release(
    path: Path | str, release_id: str, activation: WgsReleaseActivation
) -> dict[str, object]:
    source = Path(path)
    with _catalog_lock(source):
        payload = _load_schema4_payload(source)
        current_release_id = str(payload["current_release_id"])
        if current_release_id != activation.expected_current_release_id:
            raise WgsReleaseManagementError(
                status_code=409,
                code="WGS_RELEASE_ACTIVATION_CONFLICT",
                message="WGS current release changed; refresh and retry activation.",
            )
        entry = next(
            (
                row
                for row in payload["releases"]
                if isinstance(row, dict)
                and str(row.get("release_id") or "") == release_id
            ),
            None,
        )
        if entry is None:
            raise WgsReleaseManagementError(
                status_code=404,
                code="WGS_RELEASE_NOT_FOUND",
                message=f"WGS release is not cataloged: {release_id}",
            )
        receipt = entry.get(RECEIPT_KEY)
        if (
            not isinstance(receipt, dict)
            or receipt.get("receipt_sha256") != activation.receipt_sha256
        ):
            raise WgsReleaseManagementError(
                status_code=409,
                code="WGS_RELEASE_RECEIPT_CONFLICT",
                message="Activation receipt does not match the registered release.",
            )
        if current_release_id != release_id:
            payload["current_release_id"] = release_id
            _atomic_write_catalog(source, payload)
        return {
            "status": "activated",
            "previous_current_release_id": current_release_id,
            "current_release_id": release_id,
            "receipt_sha256": activation.receipt_sha256,
        }


def list_wgs_releases(path: Path | str) -> dict[str, object]:
    source = Path(path)
    catalog = load_wgs_release_catalog(source)
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    raw_entries = {
        str(row.get("release_id") or ""): row
        for row in raw.get("releases", [raw.get("release")])
        if isinstance(row, dict)
    }

    def serialize(release) -> dict[str, object]:
        result = {key: value for key, value in asdict(release).items() if value is not None}
        receipt = raw_entries.get(release.release_id, {}).get(RECEIPT_KEY)
        result["receipt_sha256"] = (
            str(receipt.get("receipt_sha256")) if isinstance(receipt, dict) else None
        )
        return result

    current = serialize(catalog.release)
    candidates = [
        serialize(release)
        for release in catalog.releases
        if release.release_id != catalog.release.release_id
    ]
    return {
        "current_release_id": catalog.release.release_id,
        "current": current,
        "candidates": candidates,
    }


def _conflict(release_id: str) -> WgsReleaseManagementError:
    return WgsReleaseManagementError(
        status_code=409,
        code="WGS_RELEASE_CONFLICT",
        message=f"WGS release {release_id} is already registered with different contents.",
    )


@contextmanager
def _catalog_lock(source: Path) -> Iterator[None]:
    if source.is_symlink():
        raise WgsReleaseManagementError(
            status_code=409,
            code="WGS_RELEASE_CATALOG_UNWRITABLE",
            message="WGS release catalog must be a regular file in a writable directory.",
        )
    lock_path = source.with_name(f"{source.name}.lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _load_schema4_payload(source: Path) -> dict[str, object]:
    catalog = load_wgs_release_catalog(source)
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if str(payload.get("schema_version") or "") == "3":
        legacy_release = payload.pop("release")
        payload["schema_version"] = "4"
        payload["current_release_id"] = catalog.release.release_id
        payload["releases"] = [legacy_release]
    return payload


def _atomic_write_catalog(source: Path, payload: dict[str, object]) -> None:
    mode = stat.S_IMODE(source.stat().st_mode)
    encoded = yaml.safe_dump(payload, sort_keys=False).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=source.parent, prefix=f".{source.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        load_wgs_release_catalog(temporary)
        os.replace(temporary, source)
        directory_descriptor = os.open(source.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()
