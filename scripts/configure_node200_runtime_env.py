#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


ENV_PATH = Path("/home/ctapa/.config/airflow-wgs/runtime.env")
PRODUCTION_RESULT_ROOT = "/sg2/50.ctapa/project/HWcloud/WGS_Clinical"
WGS_420_ROOT = "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0"
WGS_411_ROOT = "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1"
RELEASE_ROOTS = {
    "wgs-4.2.0-b067c72": WGS_420_ROOT,
    "wgs-4.1.1-6c98281": WGS_411_ROOT,
    "wgs-4.1.1-2499749": WGS_411_ROOT,
    "wgs-4.1.1-cdee32c": WGS_411_ROOT,
    "wgs-4.1.1-1656b5d": WGS_411_ROOT,
    "wgs-4.1.1-1778fca": WGS_411_ROOT,
}
VALUES = {
    "WGS_ANALYSIS_PROJECT_NODE200_ROOT": PRODUCTION_RESULT_ROOT,
    "WGS_REPO_ROOT": WGS_420_ROOT,
    "WGS_RELEASE_ROOTS_JSON": "'" + json.dumps(RELEASE_ROOTS, separators=(",", ":")) + "'",
    "WGS_PYTHON": "/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest/bin/python",
    "WGS_PREPARE_CONFIG": WGS_420_ROOT + "/prepare/config.yaml",
    "WGS_PREPARE_CONFIG_ROOT": WGS_420_ROOT + "/prepare",
    "CCE_OPERATOR_CONFIG": "/home/ctapa/.config/wgs/cce.yaml",
    "CCE_PIPELINE_BIN": "/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest/bin/cce-pipeline",
    "WGS_CCE_PROFILE_ROOT": "/bi/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs",
    "WGS_TRANSFER_ADAPTER": "obsutil",
}


def update_runtime_env(path: Path = ENV_PATH) -> None:
    original = path.read_text(encoding="utf-8").splitlines()
    remaining = dict(VALUES)
    updated: list[str] = []
    for line in original:
        key = line.split("=", 1)[0] if "=" in line and not line.lstrip().startswith("#") else ""
        if key in remaining:
            updated.append(f"{key}={remaining.pop(key)}")
        else:
            updated.append(line)
    updated.extend(f"{key}={value}" for key, value in remaining.items())
    encoded = ("\n".join(updated) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".runtime.env.", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def main() -> int:
    update_runtime_env()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
