from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_PIPELINES = {"pgta", "nipt_docker"}


@dataclass(frozen=True)
class IntakeDefaults:
    ready_rule: str = "stable_fingerprint"
    stable_scans: int = 2
    auto_submit: bool = False


@dataclass(frozen=True)
class IntakeRoot:
    id: str
    container_path: str
    host_path: str | None = None


@dataclass(frozen=True)
class IntakePipelineConfig:
    name: str
    enabled: bool
    roots: list[IntakeRoot] = field(default_factory=list)
    file_flavor: str | None = None
    r1_pattern: str | None = None
    r2_pattern: str | None = None
    ignore_patterns: list[str] = field(default_factory=list)
    auto_submit: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IntakeConfig:
    version: int
    source: str
    defaults: IntakeDefaults
    pipelines: dict[str, IntakePipelineConfig]

    def pipeline(self, name: str) -> IntakePipelineConfig:
        return self.pipelines[name]

    def roots_for_pipeline(self, name: str, *, enabled_only: bool = True) -> list[str]:
        pipeline = self.pipelines.get(name)
        if pipeline is None:
            return []
        if enabled_only and not pipeline.enabled:
            return []
        return [root.container_path for root in pipeline.roots]

    def auto_submit_enabled(self, name: str) -> bool:
        pipeline = self.pipelines.get(name)
        if pipeline is None:
            return False
        return self.defaults.auto_submit and _bool_value(pipeline.auto_submit.get("enabled"), default=False)

    def public_payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source": self.source,
            "defaults": {
                "ready_rule": self.defaults.ready_rule,
                "stable_scans": self.defaults.stable_scans,
                "auto_submit": self.defaults.auto_submit,
            },
            "pipelines": {
                name: {
                    "enabled": pipeline.enabled,
                    "roots": [{"id": root.id, "container_path": root.container_path} for root in pipeline.roots],
                    "file_flavor": pipeline.file_flavor,
                    "r1_pattern": pipeline.r1_pattern,
                    "r2_pattern": pipeline.r2_pattern,
                    "ignore_patterns": pipeline.ignore_patterns,
                    "auto_submit": {
                        **pipeline.auto_submit,
                        "enabled": self.auto_submit_enabled(name),
                        "pipeline_enabled": _bool_value(pipeline.auto_submit.get("enabled"), default=False),
                    },
                }
                for name, pipeline in self.pipelines.items()
            },
        }


def load_intake_config(
    *,
    path: str | None,
    fallback_pgta_roots: list[str],
    fallback_nipt_roots: list[str],
) -> IntakeConfig:
    if path and Path(path).exists():
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return _from_mapping(raw, source=str(Path(path)))
    return _fallback_config(fallback_pgta_roots=fallback_pgta_roots, fallback_nipt_roots=fallback_nipt_roots)


def _from_mapping(raw: dict[str, Any], *, source: str) -> IntakeConfig:
    defaults_raw = raw.get("defaults") or {}
    defaults = IntakeDefaults(
        ready_rule=str(defaults_raw.get("ready_rule") or "stable_fingerprint"),
        stable_scans=_int_value(defaults_raw.get("stable_scans"), default=2),
        auto_submit=_bool_value(defaults_raw.get("auto_submit"), default=False),
    )
    pipelines: dict[str, IntakePipelineConfig] = {}
    for name, item in (raw.get("pipelines") or {}).items():
        if name not in SUPPORTED_PIPELINES:
            continue
        item = item or {}
        roots = [
            IntakeRoot(
                id=str(root.get("id") or f"{name}_root_{index + 1}"),
                container_path=str(root.get("container_path") or root.get("path") or ""),
                host_path=root.get("host_path"),
            )
            for index, root in enumerate(item.get("roots") or [])
            if root.get("container_path") or root.get("path")
        ]
        pipelines[name] = IntakePipelineConfig(
            name=name,
            enabled=_bool_value(item.get("enabled"), default=True),
            roots=roots,
            file_flavor=item.get("file_flavor"),
            r1_pattern=item.get("r1_pattern"),
            r2_pattern=item.get("r2_pattern"),
            ignore_patterns=[str(pattern) for pattern in item.get("ignore_patterns") or []],
            auto_submit=dict(item.get("auto_submit") or {}),
        )
    return IntakeConfig(version=_int_value(raw.get("version"), default=1), source=source, defaults=defaults, pipelines=pipelines)


def _fallback_config(*, fallback_pgta_roots: list[str], fallback_nipt_roots: list[str]) -> IntakeConfig:
    return IntakeConfig(
        version=1,
        source="env_fallback",
        defaults=IntakeDefaults(),
        pipelines={
            "pgta": IntakePipelineConfig(
                name="pgta",
                enabled=True,
                roots=[IntakeRoot(id=f"pgta_root_{index + 1}", container_path=root) for index, root in enumerate(fallback_pgta_roots)],
                auto_submit={"enabled": False, "target": "metadata"},
            ),
            "nipt_docker": IntakePipelineConfig(
                name="nipt_docker",
                enabled=True,
                roots=[IntakeRoot(id=f"nipt_root_{index + 1}", container_path=root) for index, root in enumerate(fallback_nipt_roots)],
                file_flavor="clean_fastq",
                r1_pattern="*.R1.clean.fastq.gz",
                r2_pattern="*.R2.clean.fastq.gz",
                ignore_patterns=["002/*.adapter.fastq.gz"],
                auto_submit={"enabled": False, "run_mode": "mount_smoke"},
            ),
        },
    )


def _int_value(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_value(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
