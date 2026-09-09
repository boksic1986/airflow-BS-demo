#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import tempfile

import yaml


CONFIG_PATH = Path("/home/ctapa/.config/wgs/cce.yaml")
REPOSITORY_ROOT = "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1"
EVIDENCE_ROOT = os.getenv(
    "WGS_CCE_EVIDENCE_ROOT",
    "/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud/runtime/cce-evidence",
)
OBSUTIL_WRAPPER = "/home/ctapa/.config/airflow-wgs/wgs_obsutil_progress.py"


def _bounded_integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be {minimum}..{maximum}")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def sdk_transfer_profile() -> dict[str, int | bool]:
    return {
        "sdk_multipart_part_size_mib": _bounded_integer(
            "WGS_OBS_SDK_MULTIPART_PART_SIZE_MIB", 64, 8, 1024
        ),
        "sdk_multipart_task_num": _bounded_integer(
            "WGS_OBS_SDK_MULTIPART_TASK_NUM", 4, 1, 32
        ),
        "sdk_attach_crc64": _boolean("WGS_OBS_SDK_ATTACH_CRC64", True),
    }


def main() -> int:
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    paths = payload.setdefault("paths", {})
    paths["repository_root"] = REPOSITORY_ROOT
    paths["evidence_root"] = EVIDENCE_ROOT
    paths["cce_evidence_root"] = EVIDENCE_ROOT
    obs = payload.setdefault("obs", {})
    obs["obsutil_bin"] = OBSUTIL_WRAPPER
    obs.update(sdk_transfer_profile())

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".cce.yaml.", dir=str(CONFIG_PATH.parent), text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, CONFIG_PATH)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
