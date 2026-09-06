from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml


@dataclass(frozen=True)
class WgsProject:
    project_id: str
    display_name: str
    project_name: str
    platforms: tuple[dict[str, str], ...]
    fastq_roots: tuple[dict[str, str], ...]
    editable_config: dict

    def platform(self, platform_id: str) -> dict[str, str]:
        value = next((item for item in self.platforms if item["platform_id"] == platform_id), None)
        if value is None:
            raise ValueError("platform is not registered for the selected WGS project")
        return value

    def fastq_root(self, root_id: str) -> dict[str, str]:
        value = next((item for item in self.fastq_roots if item["root_id"] == root_id), None)
        if value is None:
            raise ValueError("FASTQ root is not registered for the selected WGS project")
        return value


@dataclass(frozen=True)
class WgsIntakePolicy:
    project_id: str
    root_id: str
    control_plane_path: str
    interval_seconds: int
    scheduled_scan_enabled: bool
    auto_dispatch_enabled: bool


def load_wgs_projects(path: str | Path) -> tuple[WgsProject, ...]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or str(payload.get("schema_version")) != "1":
        raise ValueError("WGS project catalog schema_version must be 1")
    raw_projects = payload.get("projects")
    if not isinstance(raw_projects, list) or not raw_projects:
        raise ValueError("WGS project catalog requires at least one project")
    projects: list[WgsProject] = []
    seen: set[str] = set()
    for raw in raw_projects:
        if not isinstance(raw, dict):
            raise ValueError("WGS project entry must be a mapping")
        project_id = str(raw.get("project_id") or "")
        if not project_id or project_id in seen:
            raise ValueError("WGS project_id must be unique and non-empty")
        seen.add(project_id)
        platforms = tuple(dict(item) for item in raw.get("platforms") or [])
        roots = tuple(dict(item) for item in raw.get("fastq_roots") or [])
        if not platforms or not roots:
            raise ValueError("WGS project requires platforms and FASTQ roots")
        for root in roots:
            for field in ("node200_path", "control_plane_path"):
                path_value = PurePosixPath(str(root.get(field) or ""))
                if not path_value.is_absolute() or ".." in path_value.parts:
                    raise ValueError(
                        f"WGS FASTQ root {field} must be an absolute normalized path"
                    )
        projects.append(
            WgsProject(
                project_id=project_id,
                display_name=str(raw.get("display_name") or project_id),
                project_name=str(raw.get("project_name") or project_id),
                platforms=platforms,
                fastq_roots=roots,
                editable_config=dict(raw.get("editable_config") or {}),
            )
        )
    return tuple(projects)


def load_wgs_intake_policy(
    *, intake_path: str | Path, project_catalog_path: str | Path
) -> WgsIntakePolicy:
    try:
        payload = yaml.safe_load(Path(intake_path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"WGS intake configuration is unreadable: {error}") from error
    pipeline = (
        (payload.get("pipelines") or {}).get("wgs")
        if isinstance(payload, dict)
        else None
    )
    intake = pipeline.get("intake") if isinstance(pipeline, dict) else None
    if not isinstance(intake, dict):
        raise ValueError("WGS intake configuration requires pipelines.wgs.intake")
    project_id = str(intake.get("project_id") or "").strip()
    root_id = str(intake.get("root_id") or "").strip()
    projects = load_wgs_projects(project_catalog_path)
    project = next((item for item in projects if item.project_id == project_id), None)
    if project is None:
        raise ValueError("WGS intake project_id is not registered")
    root = project.fastq_root(root_id)
    try:
        interval_seconds = int(intake.get("interval_seconds"))
    except (TypeError, ValueError) as error:
        raise ValueError("WGS intake interval_seconds must be an integer") from error
    if interval_seconds < 60:
        raise ValueError("WGS intake interval_seconds must be at least 60")
    scheduled = intake.get("scheduled_scan_enabled")
    if not isinstance(scheduled, bool):
        raise ValueError("WGS intake scheduled_scan_enabled must be boolean")
    auto_dispatch = intake.get("auto_dispatch_enabled")
    if not isinstance(auto_dispatch, bool):
        raise ValueError("WGS intake auto_dispatch_enabled must be boolean")
    return WgsIntakePolicy(
        project_id=project_id,
        root_id=root_id,
        control_plane_path=str(root["control_plane_path"]),
        interval_seconds=interval_seconds,
        scheduled_scan_enabled=bool(pipeline.get("enabled")) and scheduled,
        auto_dispatch_enabled=auto_dispatch,
    )


def public_project_catalog(projects: tuple[WgsProject, ...]) -> dict:
    return {
        "items": [
            {
                "project_id": item.project_id,
                "display_name": item.display_name,
                "platforms": list(item.platforms),
                "fastq_roots": [
                    {"root_id": root["root_id"], "display_name": root.get("display_name") or root["root_id"]}
                    for root in item.fastq_roots
                    if not root.get("validation_scope")
                ],
                "editable_config": item.editable_config,
            }
            for item in projects
        ]
    }
