from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict

import yaml


DEFAULT_PREPARE_CONFIG = Path(__file__).with_name("config.yaml")


def load_yaml(path: Path | str) -> Dict[str, Any]:
    source = Path(path).expanduser().resolve()
    with source.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"配置文件顶层必须是映射: {source}")
    return value


def dump_yaml(value: Dict[str, Any], path: Path | str) -> None:
    target = Path(path)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(value, handle, allow_unicode=True, sort_keys=False)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _resolve_path(value: str, config_dir: Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = config_dir / path
    return str(path.resolve())


def load_prepare_config(path: Path | str = DEFAULT_PREPARE_CONFIG) -> Dict[str, Any]:
    source = Path(path).expanduser().resolve()
    config = load_yaml(source)
    config_dir = source.parent
    for key in ("project_root", "config_template", "resource_root"):
        if key not in config:
            raise ValueError(f"prepare 配置缺少 {key}: {source}")
        config[key] = _resolve_path(str(config[key]), config_dir)
    for key in ("project_root", "config_template", "resource_root"):
        if not Path(config[key]).exists():
            raise FileNotFoundError(f"prepare 配置路径不存在: {key}={config[key]}")
    return config


def load_analysis_template(config: Dict[str, Any], template_override: str | None = None) -> Dict[str, Any]:
    template_path = Path(template_override).expanduser().resolve() if template_override else Path(config["config_template"])
    template = load_yaml(template_path)
    version = str(template.get("version", "")).strip()
    if not version:
        raise ValueError(f"分析配置模板缺少 version: {template_path}")
    return template


def analysis_name(analysis_batch: str, platform: str, version: str) -> str:
    return f"WGS_{analysis_batch}_{platform}Hg38{version}"


def version_code(version: str) -> str:
    text = str(version).strip().lstrip("Vv")
    parts = [part for part in text.replace("-", ".").replace("_", ".").split(".") if part]
    if not parts:
        return ""
    output = [str(int(parts[0])) if parts[0].isdigit() else parts[0]]
    output.extend(f"{int(part):02d}" if part.isdigit() else part for part in parts[1:])
    return "".join(output)
