from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml


DEVELOPMENT_ROOT = PurePosixPath(
    "/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development"
)


@dataclass(frozen=True)
class PipelineSnapshot:
    snapshot_id: str
    pipeline: str
    version: str
    server_path: str
    source_commit: str
    snapshot_manifest_sha256: str
    rule_event_schema_version: str
    cce_pipeline_version: str
    cce_pipeline_source_commit: str
    cce_pipeline_wheel_sha256: str
    cce_profile_id: str
    cce_profile_sha256: str
    master_image_digest: str
    status: str
    execution_enabled: bool


@dataclass(frozen=True)
class SnapshotCatalog:
    default_snapshot_id: str
    snapshots: tuple[PipelineSnapshot, ...]

    def default_development(self) -> PipelineSnapshot:
        matches = [
            item for item in self.snapshots if item.snapshot_id == self.default_snapshot_id
        ]
        if len(matches) != 1 or matches[0].status != "development":
            raise ValueError("default snapshot must identify one development snapshot")
        return matches[0]


def load_snapshot_catalog(path: Path | str) -> SnapshotCatalog:
    source = Path(path)
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or str(payload.get("schema_version")) != "2":
        raise ValueError("snapshot catalog schema_version must be 2")
    rows = payload.get("snapshots")
    if not isinstance(rows, list) or not rows:
        raise ValueError("snapshot catalog requires snapshots")
    snapshots: list[PipelineSnapshot] = []
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError("snapshot entry must be a mapping")
        snapshot = PipelineSnapshot(
            snapshot_id=str(raw.get("snapshot_id") or ""),
            pipeline=str(raw.get("pipeline") or ""),
            version=str(raw.get("version") or ""),
            server_path=str(raw.get("server_path") or ""),
            source_commit=str(raw.get("source_commit") or ""),
            snapshot_manifest_sha256=str(
                raw.get("snapshot_manifest_sha256") or ""
            ),
            rule_event_schema_version=str(
                raw.get("rule_event_schema_version") or ""
            ),
            cce_pipeline_version=str(raw.get("cce_pipeline_version") or ""),
            cce_pipeline_source_commit=str(
                raw.get("cce_pipeline_source_commit") or ""
            ),
            cce_pipeline_wheel_sha256=str(
                raw.get("cce_pipeline_wheel_sha256") or ""
            ),
            cce_profile_id=str(raw.get("cce_profile_id") or ""),
            cce_profile_sha256=str(raw.get("cce_profile_sha256") or ""),
            master_image_digest=str(raw.get("master_image_digest") or ""),
            status=str(raw.get("status") or ""),
            execution_enabled=bool(raw.get("execution_enabled", False)),
        )
        _validate_snapshot(snapshot)
        if snapshot.snapshot_id in seen:
            raise ValueError(f"duplicate snapshot_id: {snapshot.snapshot_id}")
        seen.add(snapshot.snapshot_id)
        snapshots.append(snapshot)
    catalog = SnapshotCatalog(
        default_snapshot_id=str(payload.get("default_snapshot_id") or ""),
        snapshots=tuple(snapshots),
    )
    catalog.default_development()
    return catalog


def _validate_snapshot(snapshot: PipelineSnapshot) -> None:
    if snapshot.pipeline != "wgs":
        raise ValueError("snapshot pipeline must be wgs")
    if snapshot.status != "development":
        raise ValueError("snapshot status must be development")
    if snapshot.execution_enabled:
        raise ValueError("development snapshot execution must remain disabled")
    path = PurePosixPath(snapshot.server_path)
    if (
        not path.is_absolute()
        or ".." in path.parts
        or path == DEVELOPMENT_ROOT
        or DEVELOPMENT_ROOT not in path.parents
    ):
        raise ValueError("snapshot server_path must be below Airflow development root")
    if len(snapshot.source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in snapshot.source_commit
    ):
        raise ValueError("source_commit must be 40 lowercase hexadecimal characters")
    if len(snapshot.snapshot_manifest_sha256) != 64 or any(
        character not in "0123456789abcdef"
        for character in snapshot.snapshot_manifest_sha256
    ):
        raise ValueError("snapshot manifest must be a lowercase SHA256")
    if snapshot.rule_event_schema_version not in {"1", "rule-event.v1"}:
        raise ValueError("unsupported Rule event schema version")
    if snapshot.cce_pipeline_version != "0.5.0":
        raise ValueError("cce-pipeline version must be 0.5.0")
    _validate_hex(
        snapshot.cce_pipeline_source_commit,
        length=40,
        label="cce-pipeline source commit",
    )
    _validate_hex(
        snapshot.cce_pipeline_wheel_sha256,
        length=64,
        label="cce-pipeline wheel SHA256",
    )
    if snapshot.cce_profile_id != "wgs-4.1.1-r1":
        raise ValueError("cce profile id must be wgs-4.1.1-r1")
    _validate_hex(
        snapshot.cce_profile_sha256,
        length=64,
        label="cce profile SHA256",
    )
    if not snapshot.master_image_digest.startswith("sha256:"):
        raise ValueError("master image digest must use sha256")
    _validate_hex(
        snapshot.master_image_digest.removeprefix("sha256:"),
        length=64,
        label="master image digest",
    )


def _validate_hex(value: str, *, length: int, label: str) -> None:
    if len(value) != length or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{label} must be {length} lowercase hexadecimal characters")
