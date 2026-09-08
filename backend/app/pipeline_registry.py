from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable, Mapping

import yaml


PIPELINE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
KNOWN_CAPABILITIES = frozenset(
    {
        "artifacts",
        "intake",
        "input_scan",
        "profile",
        "qc",
        "resume",
        "rerun",
        "rules",
        "submit",
    }
)
KNOWN_EXECUTION_TARGETS = frozenset({"cce", "local", "sge"})


class PipelineRegistryError(ValueError):
    code = "PIPELINE_REGISTRY_INVALID"


class PipelineNotRegistered(PipelineRegistryError):
    code = "PIPELINE_NOT_REGISTERED"


class PipelineNotAvailable(PipelineRegistryError):
    code = "PIPELINE_NOT_AVAILABLE"


class PipelineCapabilityUnavailable(PipelineRegistryError):
    code = "PIPELINE_CAPABILITY_UNAVAILABLE"


@dataclass(frozen=True)
class PipelineAdapter:
    adapter_id: str
    sample_qc_failures: bool = True
    create_run: Callable[..., dict[str, Any]] | None = None
    scan_inputs: Callable[..., dict[str, Any]] | None = None
    input_roots: Callable[..., list[str]] | None = None
    config_template: Callable[..., dict[str, Any]] | None = None
    validate_config: Callable[..., Any] | None = None
    project_config: Callable[..., dict[str, Any] | None] | None = None
    submit_run: Callable[..., dict[str, Any] | None] | None = None
    reanalyze_run: Callable[..., dict[str, Any] | None] | None = None
    project_qc: Callable[..., dict[str, Any] | None] | None = None
    project_run_detail: Callable[..., dict[str, Any] | None] | None = None
    project_samples: Callable[..., dict[str, Any]] | None = None
    project_workflows: Callable[..., dict[str, list[dict[str, Any]]]] | None = None
    project_rule_context: Callable[..., dict[str, Any]] | None = None
    project_progress: Callable[..., dict[str, Any]] | None = None
    project_dashboard_metadata: Callable[..., dict[str, Any]] | None = None
    project_dashboard_lifecycles: Callable[..., dict[str, dict[str, Any]]] | None = None
    project_dashboard_qc_statuses: Callable[..., dict[str, str]] | None = None
    project_sample_summary: Callable[..., dict[str, Any]] | None = None
    sync_airflow_status: Callable[..., dict[str, Any] | None] | None = None
    get_log: Callable[..., dict[str, Any] | None] | None = None
    list_logs: Callable[..., dict[str, list[dict[str, Any]]] | None] | None = None
    list_artifacts: Callable[..., dict[str, list[dict[str, Any]]] | None] | None = None
    intake_status: Callable[..., dict[str, Any]] | None = None
    scanner_state: Callable[..., dict[str, Any]] | None = None


@dataclass(frozen=True)
class PipelineDefinition:
    pipeline_id: str
    display_name: str
    dag_id: str
    version: str | None
    enabled: bool
    submit_enabled: bool
    capabilities: frozenset[str]
    execution_targets: tuple[str, ...]
    adapter: PipelineAdapter

    def public_payload(self) -> dict[str, Any]:
        return {
            "id": self.pipeline_id,
            "display_name": self.display_name,
            "dag_id": self.dag_id,
            "version": self.version,
            "enabled": self.enabled,
            "submit_enabled": self.submit_enabled,
            "capabilities": sorted(self.capabilities),
            "execution_targets": list(self.execution_targets),
        }


class PipelineRegistry:
    def __init__(
        self,
        definitions: Mapping[str, PipelineDefinition],
        *,
        deployed_pipeline_ids: tuple[str, ...] | None = None,
    ) -> None:
        self._definitions = dict(definitions)
        requested = deployed_pipeline_ids or tuple(
            pipeline_id
            for pipeline_id, definition in self._definitions.items()
            if definition.enabled
        )
        for pipeline_id in requested:
            if pipeline_id not in self._definitions:
                raise PipelineNotRegistered(
                    f"Pipeline {pipeline_id!r} is not declared by the registry."
                )
            if not self._definitions[pipeline_id].enabled:
                raise PipelineNotAvailable(
                    f"Pipeline {pipeline_id!r} is disabled and cannot be deployed."
                )
        self._deployed_pipeline_ids = tuple(requested)

    @property
    def deployed_pipeline_ids(self) -> tuple[str, ...]:
        return self._deployed_pipeline_ids

    def get(self, pipeline_id: str) -> PipelineDefinition:
        definition = self._definitions.get(str(pipeline_id or "").strip())
        if definition is None:
            raise PipelineNotRegistered(
                f"Pipeline {pipeline_id!r} is not registered."
            )
        return definition

    def require(
        self, pipeline_id: str, *, capability: str | None = None
    ) -> PipelineDefinition:
        definition = self.get(pipeline_id)
        if pipeline_id not in self._deployed_pipeline_ids or not definition.enabled:
            raise PipelineNotAvailable(
                f"Pipeline {pipeline_id!r} is registered but not deployed."
            )
        if capability and capability not in definition.capabilities:
            raise PipelineCapabilityUnavailable(
                f"Pipeline {pipeline_id!r} does not provide capability {capability!r}."
            )
        return definition

    def public_payload(self) -> dict[str, Any]:
        return {
            "deployed_pipelines": list(self._deployed_pipeline_ids),
            "pipelines": [
                self._definitions[pipeline_id].public_payload()
                for pipeline_id in self._definitions
            ],
        }


def load_pipeline_registry(
    path: str | Path,
    *,
    adapters: Mapping[str, PipelineAdapter],
    deployed_pipeline_ids: tuple[str, ...] | None = None,
) -> PipelineRegistry:
    registry_path = Path(path)
    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PipelineRegistryError(
            f"Pipeline registry could not be loaded: {registry_path}"
        ) from exc
    return build_pipeline_registry(
        payload,
        adapters=adapters,
        deployed_pipeline_ids=deployed_pipeline_ids,
    )


def build_pipeline_registry(
    payload: object,
    *,
    adapters: Mapping[str, PipelineAdapter],
    deployed_pipeline_ids: tuple[str, ...] | None = None,
) -> PipelineRegistry:
    if not isinstance(payload, Mapping):
        raise PipelineRegistryError("Pipeline registry root must be a mapping.")
    if payload.get("version") != 1 or not isinstance(payload.get("pipelines"), Mapping):
        raise PipelineRegistryError(
            "Pipeline registry must use version=1 and define pipelines."
        )
    definitions: dict[str, PipelineDefinition] = {}
    for pipeline_id, raw in payload["pipelines"].items():
        if not isinstance(pipeline_id, str) or not PIPELINE_ID_PATTERN.fullmatch(pipeline_id):
            raise PipelineRegistryError(f"Invalid pipeline id: {pipeline_id!r}")
        if not isinstance(raw, Mapping):
            raise PipelineRegistryError(
                f"Pipeline {pipeline_id!r} must be a mapping."
            )
        adapter_id = _required_string(raw, "adapter", pipeline_id=pipeline_id)
        adapter = adapters.get(adapter_id)
        if adapter is None:
            raise PipelineRegistryError(
                f"Pipeline {pipeline_id!r} references unknown adapter {adapter_id!r}."
            )
        capabilities = frozenset(
            _string_sequence(raw, "capabilities", pipeline_id=pipeline_id)
        )
        unknown_capabilities = sorted(capabilities - KNOWN_CAPABILITIES)
        if unknown_capabilities:
            raise PipelineRegistryError(
                f"Pipeline {pipeline_id!r} has unknown capabilities: {', '.join(unknown_capabilities)}"
            )
        execution_targets = tuple(
            _string_sequence(raw, "execution_targets", pipeline_id=pipeline_id)
        )
        unknown_targets = sorted(set(execution_targets) - KNOWN_EXECUTION_TARGETS)
        if unknown_targets:
            raise PipelineRegistryError(
                f"Pipeline {pipeline_id!r} has unknown execution targets: {', '.join(unknown_targets)}"
            )
        enabled = _required_bool(raw, "enabled", pipeline_id=pipeline_id)
        submit_enabled = _required_bool(
            raw, "submit_enabled", pipeline_id=pipeline_id
        )
        if submit_enabled and (not enabled or "submit" not in capabilities):
            raise PipelineRegistryError(
                f"Pipeline {pipeline_id!r} submit_enabled requires an enabled pipeline with submit capability."
            )
        definitions[pipeline_id] = PipelineDefinition(
            pipeline_id=pipeline_id,
            display_name=_required_string(raw, "display_name", pipeline_id=pipeline_id),
            dag_id=_required_string(raw, "dag_id", pipeline_id=pipeline_id),
            version=_optional_string(raw, "version", pipeline_id=pipeline_id),
            enabled=enabled,
            submit_enabled=submit_enabled,
            capabilities=capabilities,
            execution_targets=execution_targets,
            adapter=adapter,
        )
    return PipelineRegistry(
        definitions,
        deployed_pipeline_ids=deployed_pipeline_ids,
    )


def _required_string(
    raw: Mapping[str, Any], field: str, *, pipeline_id: str
) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PipelineRegistryError(
            f"Pipeline {pipeline_id!r} field {field!r} must be a non-empty string."
        )
    return value.strip()


def _optional_string(
    raw: Mapping[str, Any], field: str, *, pipeline_id: str
) -> str | None:
    value = raw.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise PipelineRegistryError(
            f"Pipeline {pipeline_id!r} field {field!r} must be a non-empty string when provided."
        )
    return value.strip()


def _required_bool(
    raw: Mapping[str, Any], field: str, *, pipeline_id: str
) -> bool:
    value = raw.get(field)
    if type(value) is not bool:
        raise PipelineRegistryError(
            f"Pipeline {pipeline_id!r} field {field!r} must be a boolean."
        )
    return value


def _string_sequence(
    raw: Mapping[str, Any], field: str, *, pipeline_id: str
) -> tuple[str, ...]:
    value = raw.get(field)
    if not isinstance(value, list):
        raise PipelineRegistryError(
            f"Pipeline {pipeline_id!r} field {field!r} must be a list of strings."
        )
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise PipelineRegistryError(
                f"Pipeline {pipeline_id!r} field {field!r} must contain non-empty strings."
            )
        normalized.append(item.strip())
    if len(normalized) != len(set(normalized)):
        raise PipelineRegistryError(
            f"Pipeline {pipeline_id!r} field {field!r} must not contain duplicates."
        )
    return tuple(normalized)
