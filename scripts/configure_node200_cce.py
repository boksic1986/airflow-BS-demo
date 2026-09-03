#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import tempfile

import yaml


CONFIG_PATH = Path("/home/hanjj/.config/wgs/cce.yaml")
REPOSITORY_ROOT = "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1"
EVIDENCE_ROOT = (
    "/sg2/14.hanjingjing/Cloud_WGS_Clinical/airflow-wgs/runtime/cce-evidence"
)
OBSUTIL_WRAPPER = "/home/hanjj/.config/airflow-wgs/wgs_obsutil_progress.py"


def main() -> int:
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    paths = payload.setdefault("paths", {})
    paths["repository_root"] = REPOSITORY_ROOT
    paths["evidence_root"] = EVIDENCE_ROOT
    paths["cce_evidence_root"] = EVIDENCE_ROOT
    payload.setdefault("obs", {})["obsutil_bin"] = OBSUTIL_WRAPPER

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
