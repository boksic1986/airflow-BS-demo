"""Select a private runtime only after the gate validates a stored request."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def select_release_runtime(payload: dict, *, default_cli: str) -> str:
    """Unmapped historical releases keep their existing interpreter and CLI.

    Pins are administrator-owned environment configuration, never executable
    paths supplied by the request. Re-exec keeps the exact gate arguments and
    revalidates the request before any stage side effects.
    """
    try:
        pins = json.loads(os.environ.get("WGS_RELEASE_RUNTIMES_JSON", "{}"))
        if not isinstance(pins, dict):
            raise ValueError()
        pin = pins.get(str(payload.get("pipeline_release_id") or ""))
        if pin is None:
            return default_cli
        if not isinstance(pin, dict) or set(pin) != {"python", "cce_pipeline", "version"}:
            raise ValueError()
        if not pin["version"] or pin["version"] != payload.get("cce_pipeline_version"):
            raise ValueError()
        root = Path(os.environ.get(
            "WGS_RELEASE_RUNTIME_ROOT", "/home/ctapa/.config/airflow-wgs/runtime-releases"
        ))
        if not root.is_absolute() or root.is_symlink() or not root.is_dir():
            raise ValueError()
        paths = [Path(pin[key]) for key in ("python", "cce_pipeline")]
        for path in paths:
            if (not path.is_absolute() or ".." in path.parts or path.is_symlink()
                    or root.resolve() not in path.resolve().parents
                    or not path.is_file() or not os.access(path, os.X_OK)):
                raise ValueError()
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise RuntimeError("release runtime pin is invalid or unavailable") from exc

    python, cli = paths
    environment = dict(os.environ)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment.update(WGS_PYTHON=str(python), CCE_PIPELINE_BIN=str(cli), PYTHONNOUSERSITE="1")
    if Path(sys.executable).resolve() != python.resolve():
        os.execve(str(python), [str(python), *sys.argv], environment)
        raise RuntimeError("release runtime exec unexpectedly returned")
    os.environ.update({key: environment[key] for key in ("WGS_PYTHON", "CCE_PIPELINE_BIN", "PYTHONNOUSERSITE")})
    return str(cli)
