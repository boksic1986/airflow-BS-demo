from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import re


ANALYSIS_ID_RE = re.compile(r"^WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")
RELEASE_ID_RE = re.compile(r"^wgs-[0-9]+\.[0-9]+\.[0-9]+-[0-9a-f]{7}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
STAGES = {
    "prepare",
    "step1_upload",
    "step2_master",
    "step3_monitor",
    "step4_publish",
    "step4_repair_cram",
    "step5_download",
    "step6_materialize",
}


def container_workdir_to_host(
    workdir: str, *, container_root: str, host_root: str
) -> str:
    container = PurePosixPath(container_root)
    value = PurePosixPath(workdir)
    try:
        relative = value.relative_to(container)
    except ValueError as error:
        raise ValueError("workdir is outside the approved container result root") from error
    host = PurePosixPath(host_root)
    if not host.is_absolute() or ".." in relative.parts:
        raise ValueError("host result root or workdir is invalid")
    return str(host / relative)


def build_stage_request(
    *,
    analysis_id: str,
    attempt: int,
    stage: str,
    pipeline_release_id: str,
    wgs_version: str,
    wgs_source_commit: str,
    workdir: Path | str,
    bs_runtime_root: str,
    node200_runtime_root: str,
    project_name: str,
    batch_no: str,
    fq_path: str,
) -> dict[str, object]:
    if ANALYSIS_ID_RE.fullmatch(analysis_id) is None:
        raise ValueError("invalid WGS analysis_id")
    if attempt < 1:
        raise ValueError("attempt must be positive")
    if stage not in STAGES:
        raise ValueError("unsupported WGS runtime stage")
    if RELEASE_ID_RE.fullmatch(pipeline_release_id) is None:
        raise ValueError("invalid WGS pipeline_release_id")
    if not str(wgs_version).startswith("V"):
        raise ValueError("invalid WGS version")
    if COMMIT_RE.fullmatch(wgs_source_commit) is None:
        raise ValueError("invalid WGS source commit")
    for label, value in (("project name", project_name), ("batch number", batch_no)):
        if SAFE_COMPONENT_RE.fullmatch(str(value).strip()) is None:
            raise ValueError(f"invalid {label}")
    fastq = PurePosixPath(fq_path)
    if not fastq.is_absolute() or ".." in fastq.parts:
        raise ValueError("fq_path must be an absolute normalized node200 path")
    bs_root = PurePosixPath(bs_runtime_root)
    node_root = PurePosixPath(node200_runtime_root)
    if not bs_root.is_absolute() or not node_root.is_absolute():
        raise ValueError("runtime roots must be absolute")
    relative = PurePosixPath("runs") / analysis_id / f"attempt-{attempt}"
    return {
        "schema_version": "wgs-runtime.request.v3",
        "analysis_id": analysis_id,
        "attempt": attempt,
        "stage": stage,
        "pipeline_release_id": pipeline_release_id,
        "wgs_version": str(wgs_version),
        "wgs_source_commit": wgs_source_commit,
        "workdir": str(Path(workdir)),
        "bs10610_workdir": str(bs_root / relative),
        "node200_workdir": str(node_root / relative),
        "project_name": str(project_name).strip(),
        "batch_no": str(batch_no).strip(),
        "fq_path": str(fastq),
    }


def write_stage_request(
    root: Path | str,
    request: dict[str, object],
    *,
    shared_gid: int | None = None,
) -> Path:
    base = Path(root).resolve()
    analysis_id = str(request["analysis_id"])
    attempt = int(request["attempt"])
    stage = str(request["stage"])
    if (
        ANALYSIS_ID_RE.fullmatch(analysis_id) is None
        or stage not in STAGES
        or attempt < 1
    ):
        raise ValueError("invalid runtime request identity")
    target = (base / analysis_id / f"attempt-{attempt}" / f"{stage}.json").resolve()
    if base not in target.parents:
        raise ValueError("runtime request path escapes request root")
    target.parent.mkdir(parents=True, exist_ok=True)
    if shared_gid is not None:
        if shared_gid < 1:
            raise ValueError("shared runtime group id must be positive")
        os.chown(target.parent, -1, shared_gid)
        os.chmod(target.parent, 0o2770)
    partial = target.with_suffix(".json.partial")
    partial.write_text(json.dumps(request, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, target)
    return target
