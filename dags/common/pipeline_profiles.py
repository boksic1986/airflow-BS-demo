from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

import yaml


@dataclass(frozen=True)
class ResolvedRuntimeProfile:
    profile_id: str
    template_hash: str
    runtime: dict[str, Any]
    editable_config: dict[str, Any]
    editable_schema: dict[str, Any]


def validate_runtime_profile_availability(
    profile: ResolvedRuntimeProfile | None,
    *,
    pipeline: str,
    docker_executable: str | None = None,
    command_runner=subprocess.run,
) -> None:
    if profile is None:
        return
    if pipeline == "pgta":
        _validate_pgta_runtime_paths(profile)
        return
    if pipeline == "nipt_docker":
        docker = docker_executable or shutil.which("docker")
        if not docker:
            raise ValueError("Approved NIPT runtime is unavailable: docker executable was not found.")
        for key in ("docker_image", "fetal_image"):
            image = str(profile.runtime.get(key) or "").strip()
            if not image:
                raise ValueError(f"Approved NIPT runtime is missing {key}.")
            try:
                completed = command_runner(
                    [docker, "image", "inspect", image],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValueError(f"Approved NIPT {key} could not be inspected: {exc}") from exc
            if completed.returncode != 0:
                detail = str(completed.stderr or "image is not available").strip()
                raise ValueError(f"Approved NIPT {key} is unavailable: {detail}")
        return
    raise ValueError(f"Unsupported runtime profile pipeline: {pipeline}")


def resolve_runtime_profile(
    conf: dict[str, Any],
    *,
    pipeline: str,
    profile_config_path: Path | None = None,
) -> ResolvedRuntimeProfile | None:
    params = dict(conf.get("params") or {})
    profile_id = str(params.get("runtime_profile_id") or "").strip()
    if not profile_id:
        return None
    path = profile_config_path or Path(
        os.getenv("PIPELINE_PROFILE_CONFIG_PATH", "/opt/airflow/config/pipeline_profiles.yaml")
    )
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        profile = payload["pipelines"][pipeline]["profiles"][profile_id]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Unknown runtime profile for pipeline={pipeline}: {profile_id}") from exc
    current_hash = _profile_hash(profile_id, profile)
    if params.get("config_template_hash") != current_hash:
        raise ValueError("runtime profile hash does not match the submitted run")

    workdir = Path(str(conf["workdir"]))
    requested_path = workdir / "config" / "snakemake.user.yaml"
    if not requested_path.is_file():
        raise ValueError(f"requested Snakemake config is missing: {requested_path}")
    requested_text = requested_path.read_text(encoding="utf-8")
    if params.get("config_requested_hash") != _sha256_text(requested_text):
        raise ValueError("requested config hash does not match the submitted run")
    requested = yaml.safe_load(requested_text) or {}
    if not isinstance(requested, dict):
        raise ValueError("requested Snakemake config must be a mapping")

    defaults = deepcopy(profile.get("editable_defaults") or {})
    schema = dict(profile.get("editable_schema") or {})
    unknown = sorted(set(_flatten_leaf_paths(requested)) - set(schema))
    if unknown:
        raise ValueError("requested config contains protected fields: " + ", ".join(unknown))
    editable = _deep_merge(defaults, requested)
    missing = sorted(set(schema) - set(_flatten_leaf_paths(editable)))
    if missing:
        raise ValueError("requested config is missing editable fields: " + ", ".join(missing))
    return ResolvedRuntimeProfile(
        profile_id=profile_id,
        template_hash=current_hash,
        runtime=dict(profile.get("runtime") or {}),
        editable_config=editable,
        editable_schema=schema,
    )


def apply_editable_config(
    base_config: dict[str, Any],
    resolved_profile: ResolvedRuntimeProfile | None,
) -> dict[str, Any]:
    if resolved_profile is None:
        return base_config
    result = deepcopy(base_config)
    for path in resolved_profile.editable_schema:
        value = _get_path(resolved_profile.editable_config, path)
        _set_path(result, path, deepcopy(value))
    return result


def write_resolved_config(*, workdir: Path, config: dict[str, Any]) -> Path:
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(config, sort_keys=False, allow_unicode=False)
    resolved_path = config_dir / "snakemake.resolved.yaml"
    resolved_path.write_text(text, encoding="utf-8")
    provenance_path = config_dir / "config_provenance.json"
    provenance: dict[str, Any] = {}
    if provenance_path.is_file():
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            provenance = {}
    provenance.update(
        {
            "state": "resolved",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_config_hash": _sha256_text(text),
        }
    )
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved_path


def _profile_hash(profile_id: str, profile: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"id": profile_id, "profile": profile},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_text(canonical)


def _validate_pgta_runtime_paths(profile: ResolvedRuntimeProfile) -> None:
    contracts = (
        ("snakemake_bin", "file", True),
        ("python_bin", "file", True),
        ("samtools_bin", "file", True),
        ("fastp_bin", "file", True),
        ("bwa_bin", "file", True),
        ("wisecondorx_bin", "file", True),
        ("reference_genome", "file", False),
        ("pipeline_root", "directory", False),
    )
    for key, kind, executable in contracts:
        raw_path = str(profile.runtime.get(key) or "").strip()
        if not raw_path:
            raise ValueError(f"Approved PGT-A runtime is missing {key}.")
        path = Path(raw_path)
        available = path.is_file() if kind == "file" else path.is_dir()
        if not available:
            raise ValueError(f"Approved PGT-A {key} is unavailable: {path}")
        if executable and not os.access(path, os.X_OK):
            raise ValueError(f"Approved PGT-A {key} is not executable: {path}")
    snakefile = Path(str(profile.runtime["pipeline_root"])) / "Snakefile"
    if not snakefile.is_file():
        raise ValueError(f"Approved PGT-A pipeline_root has no Snakefile: {snakefile}")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _flatten_leaf_paths(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(item, dict):
            result.update(_flatten_leaf_paths(item, path))
        else:
            result[path] = item
    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _get_path(config: dict[str, Any], path: str) -> Any:
    current: Any = config
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"editable profile value is missing: {path}")
        current = current[part]
    return current


def _set_path(config: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = config
    for part in parts[:-1]:
        child = current.get(part)
        if child is None:
            child = {}
            current[part] = child
        if not isinstance(child, dict):
            raise ValueError(f"cannot merge editable config into non-mapping path: {path}")
        current = child
    current[parts[-1]] = value
