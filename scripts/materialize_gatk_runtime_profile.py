#!/usr/bin/env python3
"""Apply the Airflow-only GATK Snakemake profile overlay."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


ALLOWED_OVERRIDES = {"latency-wait"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _load_mapping(path: Path, label: str) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a YAML mapping")
    return value


def materialize_profile(
    *,
    source: Path,
    overlay: Path,
    output: Path,
    provenance: Path,
    source_commit: str,
) -> dict[str, Any]:
    source = source.resolve()
    overlay = overlay.resolve()
    if not source.is_file() or source.is_symlink():
        raise ValueError("GATK source profile must be a regular file")
    if not overlay.is_file() or overlay.is_symlink():
        raise ValueError("Airflow profile overlay must be a regular file")
    if not source_commit.strip():
        raise ValueError("source_commit is required")

    profile = _load_mapping(source, "GATK source profile")
    overlay_value = _load_mapping(overlay, "Airflow profile overlay")
    if overlay_value.get("schema_version") != 1:
        raise ValueError("unsupported Airflow profile overlay schema")
    overrides = overlay_value.get("snakemake_profile")
    if not isinstance(overrides, dict) or not overrides:
        raise ValueError("Airflow profile overlay has no Snakemake settings")
    unsupported = sorted(set(overrides) - ALLOWED_OVERRIDES)
    if unsupported:
        raise ValueError(f"unsupported key in Airflow profile overlay: {unsupported[0]}")
    latency_wait = overrides.get("latency-wait")
    if (
        not isinstance(latency_wait, int)
        or isinstance(latency_wait, bool)
        or not 1 <= latency_wait <= 600
    ):
        raise ValueError("latency-wait must be an integer between 1 and 600")

    rendered = dict(profile)
    rendered.update(overrides)
    _atomic_write(output, yaml.safe_dump(rendered, sort_keys=False))
    result = {
        "schema_version": 1,
        "kind": "gatk-airflow-snakemake-profile-overlay",
        "source_commit": source_commit.strip(),
        "source_path": str(source),
        "source_sha256": _sha256(source),
        "overlay_path": str(overlay),
        "overlay_sha256": _sha256(overlay),
        "output_path": str(output.resolve()),
        "output_sha256": _sha256(output),
        "overrides": dict(overrides),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write(provenance, json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    print(json.dumps(materialize_profile(**vars(args)), sort_keys=True))


if __name__ == "__main__":
    main()
