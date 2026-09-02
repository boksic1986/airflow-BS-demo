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
            path_value = PurePosixPath(str(root.get("node200_path") or ""))
            if not path_value.is_absolute() or ".." in path_value.parts:
                raise ValueError("WGS FASTQ root must be an absolute normalized path")
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
                ],
                "editable_config": item.editable_config,
            }
            for item in projects
        ]
    }
