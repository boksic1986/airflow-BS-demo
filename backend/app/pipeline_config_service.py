from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisRun


MAX_CONFIG_BYTES = 64 * 1024


class PipelineConfigError(ValueError):
    pass


class ProfileChangedError(PipelineConfigError):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: _UniqueKeyLoader, node, deep: bool = False):
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise PipelineConfigError(f"Duplicate YAML key is not allowed: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True)
class ValidatedPipelineConfig:
    pipeline: str
    profile_id: str
    profile_label: str
    pipeline_version: str
    config_version: str
    template_hash: str
    requested_yaml: str
    normalized_yaml: str
    normalized_config: dict[str, Any]
    changed_paths: list[str]
    requested_hash: str
    runtime_profile_snapshot: dict[str, Any]

    def params(self) -> dict[str, Any]:
        return {
            "runtime_profile_id": self.profile_id,
            "runtime_profile_label": self.profile_label,
            "runtime_pipeline_version": self.pipeline_version,
            "runtime_config_version": self.config_version,
            "config_template_hash": self.template_hash,
            "config_requested_hash": self.requested_hash,
            "config_changed_paths": self.changed_paths,
        }


def get_pipeline_config_template(
    *,
    settings,
    pipeline: str,
    profile_id: str | None = None,
) -> dict[str, Any]:
    registry = _load_registry(settings)
    pipeline_entry, selected_id, profile = _select_profile(
        registry=registry,
        pipeline=pipeline,
        profile_id=profile_id,
    )
    profiles = [
        _public_profile(item_id, item)
        for item_id, item in (pipeline_entry.get("profiles") or {}).items()
        if item.get("submit_visible", True)
    ]
    defaults = deepcopy(profile.get("editable_defaults") or {})
    normalized_yaml = _dump_yaml(defaults)
    return {
        "pipeline": pipeline,
        "profile": _public_profile(selected_id, profile),
        "profiles": profiles,
        "config_template_hash": _profile_hash(selected_id, profile),
        "editable_yaml": normalized_yaml,
        "changed_paths": [],
    }


def validate_pipeline_config(
    *,
    settings,
    pipeline: str,
    profile_id: str,
    template_hash: str,
    config_yaml: str,
    cores: int | None = None,
) -> ValidatedPipelineConfig:
    registry = _load_registry(settings)
    _, selected_id, profile = _select_profile(
        registry=registry,
        pipeline=pipeline,
        profile_id=profile_id,
    )
    current_hash = _profile_hash(selected_id, profile)
    if template_hash != current_hash:
        raise ProfileChangedError("Runtime profile changed after the editor was loaded. Reload the defaults and validate again.")

    requested = _load_user_yaml(config_yaml)
    defaults = deepcopy(profile.get("editable_defaults") or {})
    schema = profile.get("editable_schema") or {}
    if not isinstance(defaults, dict) or not isinstance(schema, dict):
        raise PipelineConfigError(f"Profile {selected_id} has an invalid editable config contract.")

    requested_paths = _all_config_paths(requested)
    allowed_paths = set(schema)
    for path in schema:
        parts = path.split(".")
        allowed_paths.update(".".join(parts[:index]) for index in range(1, len(parts)))
    unknown = sorted(set(requested_paths) - allowed_paths)
    if unknown:
        raise PipelineConfigError("Config contains protected or unknown fields: " + ", ".join(unknown))

    normalized = _deep_merge(defaults, requested)
    values = _flatten_leaf_paths(normalized)
    missing = sorted(set(schema) - set(values))
    if missing:
        raise PipelineConfigError("Config is missing required editable fields: " + ", ".join(missing))
    for path, rule in schema.items():
        _validate_value(path=path, value=values[path], rule=rule)
    _validate_context_limits(pipeline=pipeline, values=values, cores=cores)

    default_values = _flatten_leaf_paths(defaults)
    changed_paths = sorted(path for path, value in values.items() if default_values.get(path) != value)
    normalized_yaml = _dump_yaml(normalized)
    return ValidatedPipelineConfig(
        pipeline=pipeline,
        profile_id=selected_id,
        profile_label=str(profile.get("label") or selected_id),
        pipeline_version=str(profile.get("pipeline_version") or "unknown"),
        config_version=str(profile.get("config_version") or "unknown"),
        template_hash=current_hash,
        requested_yaml=config_yaml,
        normalized_yaml=normalized_yaml,
        normalized_config=normalized,
        changed_paths=changed_paths,
        requested_hash=_sha256_text(config_yaml),
        runtime_profile_snapshot=deepcopy(profile.get("runtime") or {}),
    )


def persist_requested_config(*, workdir: Path, config: ValidatedPipelineConfig) -> None:
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    requested_path = config_dir / "snakemake.user.yaml"
    requested_path.write_text(config.requested_yaml, encoding="utf-8")
    provenance = {
        "version": 1,
        "state": "waiting_for_prepare",
        "pipeline": config.pipeline,
        "runtime_profile_id": config.profile_id,
        "runtime_profile_label": config.profile_label,
        "pipeline_version": config.pipeline_version,
        "config_version": config.config_version,
        "config_template_hash": config.template_hash,
        "config_requested_hash": config.requested_hash,
        "changed_paths": config.changed_paths,
        "resolved_config_hash": None,
        "runtime_profile_snapshot": config.runtime_profile_snapshot,
    }
    provenance_path = config_dir / "config_provenance.json"
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    requested_path.chmod(0o664)
    provenance_path.chmod(0o664)


def get_run_config(*, session: Session, analysis_id: str, settings) -> dict[str, Any] | None:
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
    if run is None:
        return None
    workdir = _safe_workdir(Path(run.workdir), settings)
    config_dir = workdir / "config"
    requested_path = _safe_run_file(config_dir / "snakemake.user.yaml", workdir)
    resolved_path = _safe_run_file(config_dir / "snakemake.resolved.yaml", workdir)
    provenance_path = _safe_run_file(config_dir / "config_provenance.json", workdir)
    params = dict(run.params_json or {})

    provenance: dict[str, Any] = {}
    if provenance_path:
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            provenance = {}

    if resolved_path:
        state = "resolved"
    elif requested_path:
        state = "waiting_for_prepare"
    else:
        state = "legacy"
        resolved_path = _safe_run_file(_legacy_resolved_path(run.pipeline_name, workdir), workdir)

    profile_id = str(params.get("runtime_profile_id") or provenance.get("runtime_profile_id") or "")
    profile = None
    if profile_id:
        profile = {
            "id": profile_id,
            "label": str(params.get("runtime_profile_label") or provenance.get("runtime_profile_label") or profile_id),
            "pipeline_version": str(params.get("runtime_pipeline_version") or provenance.get("pipeline_version") or "unknown"),
            "config_version": str(params.get("runtime_config_version") or provenance.get("config_version") or "unknown"),
        }

    return {
        "analysis_id": analysis_id,
        "pipeline": run.pipeline_name,
        "state": state,
        "profile": profile,
        "config_template_hash": params.get("config_template_hash") or provenance.get("config_template_hash"),
        "config_requested_hash": params.get("config_requested_hash") or provenance.get("config_requested_hash"),
        "resolved_config_hash": provenance.get("resolved_config_hash"),
        "changed_paths": params.get("config_changed_paths") or provenance.get("changed_paths") or [],
        "requested_yaml": requested_path.read_text(encoding="utf-8") if requested_path else None,
        "resolved_yaml": resolved_path.read_text(encoding="utf-8") if resolved_path else None,
    }


def _load_registry(settings) -> dict[str, Any]:
    path = Path(
        str(
            getattr(settings, "pipeline_profile_config_path", None)
            or "/app/config/pipeline_profiles.yaml"
        )
    )
    if not path.is_file():
        raise PipelineConfigError(f"Pipeline profile config not found: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise PipelineConfigError(f"Pipeline profile config is invalid: {exc}") from exc
    if payload.get("version") != 1 or not isinstance(payload.get("pipelines"), dict):
        raise PipelineConfigError("Pipeline profile config must use version=1 and define pipelines.")
    return payload


def _select_profile(*, registry: dict[str, Any], pipeline: str, profile_id: str | None):
    if pipeline not in {"pgta", "nipt_docker"}:
        raise PipelineConfigError("Only pipeline=pgta or pipeline=nipt_docker supports editable Snakemake config.")
    pipeline_entry = (registry.get("pipelines") or {}).get(pipeline)
    if not isinstance(pipeline_entry, dict):
        raise PipelineConfigError(f"No runtime profiles are configured for pipeline={pipeline}.")
    selected_id = str(profile_id or pipeline_entry.get("default_profile") or "")
    profiles = pipeline_entry.get("profiles") or {}
    profile = profiles.get(selected_id)
    if not selected_id or not isinstance(profile, dict):
        raise PipelineConfigError(f"Unknown runtime profile for pipeline={pipeline}: {selected_id}")
    return pipeline_entry, selected_id, profile


def _public_profile(profile_id: str, profile: dict[str, Any]) -> dict[str, str]:
    return {
        "id": profile_id,
        "label": str(profile.get("label") or profile_id),
        "pipeline_version": str(profile.get("pipeline_version") or "unknown"),
        "config_version": str(profile.get("config_version") or "unknown"),
    }


def _profile_hash(profile_id: str, profile: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"id": profile_id, "profile": profile},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_text(canonical)


def _load_user_yaml(text: str) -> dict[str, Any]:
    if len(text.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise PipelineConfigError(f"Snakemake config exceeds {MAX_CONFIG_BYTES} bytes.")
    try:
        for token in yaml.scan(text):
            if isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken, yaml.tokens.TagToken)):
                raise PipelineConfigError("YAML anchors, aliases, and custom tags are not allowed.")
        payload = yaml.load(text, Loader=_UniqueKeyLoader)
    except PipelineConfigError:
        raise
    except yaml.YAMLError as exc:
        raise PipelineConfigError(f"Snakemake config YAML is invalid: {exc}") from exc
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise PipelineConfigError("Snakemake config YAML must have a mapping at the root.")
    return payload


def _flatten_leaf_paths(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip() or "." in key:
            raise PipelineConfigError("Config keys must be non-empty strings without dots.")
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(_flatten_leaf_paths(item, path))
        else:
            result[path] = item
    return result


def _all_config_paths(value: dict[str, Any], prefix: str = "") -> list[str]:
    result: list[str] = []
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip() or "." in key:
            raise PipelineConfigError("Config keys must be non-empty strings without dots.")
        path = f"{prefix}.{key}" if prefix else key
        result.append(path)
        if isinstance(item, dict):
            result.extend(_all_config_paths(item, path))
    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _validate_value(*, path: str, value: Any, rule: Any) -> None:
    if not isinstance(rule, dict):
        raise PipelineConfigError(f"Editable schema is invalid for {path}.")
    expected = rule.get("type")
    valid_type = {
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "string": isinstance(value, str),
    }.get(str(expected), False)
    if not valid_type:
        raise PipelineConfigError(f"Config field {path} must be {expected}.")
    if "enum" in rule and value not in rule["enum"]:
        raise PipelineConfigError(f"Config field {path} must be one of {rule['enum']}.")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            raise PipelineConfigError(f"Config field {path} must be a finite number.")
        if "minimum" in rule and value < rule["minimum"]:
            raise PipelineConfigError(f"Config field {path} must be >= {rule['minimum']}.")
        if "maximum" in rule and value > rule["maximum"]:
            raise PipelineConfigError(f"Config field {path} must be <= {rule['maximum']}.")


def _validate_context_limits(*, pipeline: str, values: dict[str, Any], cores: int | None) -> None:
    if pipeline != "nipt_docker" or cores is None:
        return
    for path in (
        "params.map_threads",
        "params.aneuscreen_threads",
        "mapper_v2.workers",
        "mapper_v2.worker_auto_max",
    ):
        value = values.get(path)
        if isinstance(value, int) and value > cores:
            raise PipelineConfigError(f"Config field {path} cannot exceed requested NIPT cores ({cores}).")


def _dump_yaml(payload: dict[str, Any]) -> str:
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_workdir(workdir: Path, settings) -> Path:
    shared_root = Path(settings.container_shared_root).resolve()
    resolved = workdir.resolve()
    try:
        resolved.relative_to(shared_root)
    except ValueError as exc:
        raise PipelineConfigError(f"Run workdir is outside shared root: {resolved}") from exc
    return resolved


def _legacy_resolved_path(pipeline: str, workdir: Path) -> Path:
    if pipeline == "pgta":
        return workdir / "config.yaml"
    if pipeline == "nipt_docker":
        return workdir / "config" / "nipt_run_config.yaml"
    return workdir / "config" / "snakemake.resolved.yaml"


def _safe_run_file(path: Path, workdir: Path) -> Path | None:
    if path.is_symlink():
        raise PipelineConfigError(f"Run config file must not be a symlink: {path.name}")
    if not path.exists():
        return None
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(workdir.resolve())
    except (OSError, ValueError) as exc:
        raise PipelineConfigError(f"Run config file is outside the run workdir: {path.name}") from exc
    if not resolved.is_file():
        raise PipelineConfigError(f"Run config path is not a file: {path.name}")
    return resolved
