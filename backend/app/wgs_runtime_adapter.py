from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import re


ANALYSIS_ID_RE = re.compile(r"^WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")
SNAPSHOT_ID_RE = re.compile(
    r"^wgs-v4\.1\.1-candidate-[0-9a-f]{7}-[0-9a-f]{8}$"
)
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
DEVELOPMENT_ROOT = PurePosixPath(
    "/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development"
)
NODE200_DEVELOPMENT_ROOT = PurePosixPath(
    "/bi/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development"
)
STAGES = {
    "prepare",
    "step1_upload",
    "step2_master",
    "step3_monitor",
    "step4_publish",
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
    snapshot_id: str,
    snapshot_path: str,
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
    if SNAPSHOT_ID_RE.fullmatch(snapshot_id) is None:
        raise ValueError("invalid WGS 4.1.1 candidate snapshot id")
    snapshot = PurePosixPath(snapshot_path)
    if snapshot.name != snapshot_id or DEVELOPMENT_ROOT not in snapshot.parents:
        raise ValueError("snapshot path is outside the approved Airflow development root")
    node200_snapshot = NODE200_DEVELOPMENT_ROOT / snapshot.name
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
        "schema_version": "wgs-runtime.request.v2",
        "analysis_id": analysis_id,
        "attempt": attempt,
        "stage": stage,
        "pipeline_snapshot_id": snapshot_id,
        "pipeline_snapshot_path": str(snapshot),
        "node200_pipeline_snapshot_path": str(node200_snapshot),
        "workdir": str(Path(workdir)),
        "bs10610_workdir": str(bs_root / relative),
        "node200_workdir": str(node_root / relative),
        "project_name": str(project_name).strip(),
        "batch_no": str(batch_no).strip(),
        "fq_path": str(fastq),
    }


def write_stage_request(root: Path | str, request: dict[str, object]) -> Path:
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
    partial = target.with_suffix(".json.partial")
    partial.write_text(json.dumps(request, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, target)
    return target
