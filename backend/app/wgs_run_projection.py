from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


class WgsBindingPathError(ValueError):
    pass


def public_wgs_batch(params: Mapping[str, Any] | None) -> str | None:
    values = params or {}
    for key in ("analysis_batch", "sequencing_batch", "batch_no"):
        value = str(values.get(key) or "").strip()
        if value:
            return value
    return None


def wgs_params_match_batch(
    params: Mapping[str, Any] | None, batch: str
) -> bool:
    """Match one public batch code against every supported WGS run identity."""

    values = params or {}
    if any(
        str(values.get(key) or "").strip() == batch
        for key in ("sequencing_batch", "analysis_batch")
    ):
        return True
    batch_no = str(values.get("batch_no") or "").strip()
    return batch_no == batch or batch_no.startswith(f"WGS_{batch}_")


def public_wgs_params(params: Mapping[str, Any] | None) -> dict[str, Any]:
    projected = dict(params or {})
    projected["batch_no"] = public_wgs_batch(projected)
    return projected


def load_wgs_runtime_binding(
    *, request_root: str | Path, analysis_id: str, attempt: int
) -> dict[str, Any]:
    root = Path(request_root).resolve().parent
    path = (
        root / "runs" / analysis_id / f"attempt-{attempt}" / "batch-binding.json"
    ).resolve()
    if root not in path.parents or path.is_symlink() or not path.is_file():
        raise WgsBindingPathError("WGS frozen batch binding is unavailable")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WgsBindingPathError("WGS frozen batch binding is unreadable") from error
    try:
        identity_matches = (
            isinstance(payload, dict)
            and str(payload.get("analysis_id") or "") == analysis_id
            and int(payload.get("attempt") or 0) == attempt
        )
    except (TypeError, ValueError):
        identity_matches = False
    if not identity_matches:
        raise WgsBindingPathError("WGS frozen batch binding identity mismatch")
    return payload


def resolve_bound_wgs_batch_root(
    *,
    binding: Mapping[str, Any],
    node_analysis_root: str,
    local_analysis_root: str | Path,
) -> Path:
    node_root = PurePosixPath(node_analysis_root)
    node_batch = PurePosixPath(str(binding.get("batch_root") or ""))
    if not node_root.is_absolute() or not node_batch.is_absolute():
        raise WgsBindingPathError("WGS batch root must be absolute")
    try:
        relative = node_batch.relative_to(node_root)
    except ValueError as error:
        raise WgsBindingPathError(
            "WGS batch root escapes the approved analysis root"
        ) from error
    if not relative.parts or ".." in relative.parts:
        raise WgsBindingPathError("WGS batch root is not a batch directory")
    local_root = Path(local_analysis_root).resolve()
    candidate = (local_root / Path(*relative.parts)).resolve()
    if local_root not in candidate.parents:
        raise WgsBindingPathError(
            "WGS local batch root escapes the approved analysis root"
        )
    return candidate
