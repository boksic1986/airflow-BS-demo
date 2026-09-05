from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class WgsStageDefinition:
    code: str
    step_number: int | None
    label: str


WGS_ORCHESTRATION_STAGES = (
    WgsStageDefinition("step1_upload", 1, "Uploading FASTQ"),
    WgsStageDefinition("step2_master", 2, "Starting WGS workflow"),
    WgsStageDefinition("step3_monitor", 3, "WGS workflow running"),
    WgsStageDefinition("step4_publish", 4, "Publishing WGS results"),
    WgsStageDefinition("step5_download", 5, "Downloading WGS results"),
    WgsStageDefinition("step6_materialize", 6, "Materializing local results"),
)

WGS_AUXILIARY_STAGES = (
    WgsStageDefinition("prepare", None, "Preparing WGS batch"),
    WgsStageDefinition("prepare_sampleinfo", None, "Preparing sample information"),
    WgsStageDefinition("prepare_analysis", None, "Preparing WGS analysis"),
    WgsStageDefinition("step4_repair_cram", 4, "Repairing CRAM linkage"),
    WgsStageDefinition("step7_cleanup", 7, "Cleaning WGS SFS workspace"),
    WgsStageDefinition("step1_canary_complete", None, "Step1 validation passed"),
    WgsStageDefinition("final", None, "WGS workflow completed"),
)

WGS_STAGE_BY_CODE = {
    stage.code: stage for stage in (*WGS_ORCHESTRATION_STAGES, *WGS_AUXILIARY_STAGES)
}

WGS_STAGE_ALIASES = {
    "validate_request": "prepare",
    "prepare_wgs_batch": "prepare",
    "prepare_wgs_sampleinfo": "prepare_sampleinfo",
    "wait_prepare_wgs_sampleinfo": "prepare_sampleinfo",
    "prepare_wgs_analysis": "prepare_analysis",
    "wait_prepare_wgs_analysis": "prepare_analysis",
    "acquire_input_transfer_slot": "step1_upload",
    "release_input_transfer_slot": "step1_upload",
    "wait_step1_upload": "step1_upload",
    "submit_step2_master": "step2_master",
    "start_step3_monitor": "step3_monitor",
    "wait_step3_analysis": "step3_monitor",
    "start_step4_publish": "step4_publish",
    "wait_step4_publish": "step4_publish",
    "acquire_result_transfer_slot": "step5_download",
    "release_result_transfer_slot": "step5_download",
    "wait_step5_download": "step5_download",
    "materialize_step6_results": "step6_materialize",
    "finalize_run": "final",
    "finalize_step1_canary": "step1_canary_complete",
}


def wgs_stage_definition(code: str) -> WgsStageDefinition:
    try:
        return WGS_STAGE_BY_CODE[code]
    except KeyError as error:
        raise ValueError(f"unsupported WGS stage: {code}") from error


def canonical_wgs_stage(stage: str | None, run_status: str | None) -> str:
    if str(run_status or "").lower() == "success":
        return "final"
    value = str(stage or "created")
    canonical = WGS_STAGE_ALIASES.get(value, value)
    return canonical if canonical in WGS_STAGE_BY_CODE else "prepare"


def terminal_wgs_progress(
    *, updated_at: str | None, validation_scope: str | None = None
) -> dict[str, object]:
    """Return the terminal tracker payload from the shared WGS stage contract."""

    stage = wgs_stage_definition(
        "step1_canary_complete" if validation_scope == "step1_only" else "final"
    )
    return {
        "stage_code": stage.code,
        "step_number": stage.step_number,
        "stage_label": stage.label,
        "stage_status": "success",
        "progress_available": True,
        "progress_percent": 100,
        "completed_units": 1,
        "total_units": 1,
        "unit": "validation" if validation_scope == "step1_only" else "workflow",
        "current_item": None,
        "speed_bps": None,
        "eta_seconds": 0,
        "progress_source": "workflow-terminal-state",
        "stage_updated_at": updated_at,
    }


def project_wgs_orchestration(
    *,
    run_status: str | None,
    current_stage: str | None,
    stage_rows: Iterable[object],
) -> list[dict[str, object]]:
    """Project the six public stages from authoritative runtime evidence.

    Historical successful runs can predate ``run_stage_state``. Their terminal
    run status is sufficient to mark every orchestration stage successful, but
    never to invent byte/job progress.
    """

    rows = {str(row.stage_code): row for row in stage_rows}
    status = str(run_status or "created").lower()
    canonical = canonical_wgs_stage(current_stage, run_status)
    codes = [stage.code for stage in WGS_ORCHESTRATION_STAGES]
    current_index = codes.index(canonical) if canonical in codes else None
    items: list[dict[str, object]] = []
    for index, stage in enumerate(WGS_ORCHESTRATION_STAGES):
        row = rows.get(stage.code)
        if status == "success":
            stage_status = "success"
        elif row is not None:
            stage_status = _public_stage_status(row.stage_status)
        elif current_index is not None and index < current_index:
            stage_status = "success"
        elif current_index is not None and index == current_index:
            stage_status = wgs_stage_status_without_evidence(status)
        elif canonical == "final":
            stage_status = "success"
        else:
            stage_status = "pending"
        progress_available = bool(row and row.progress_available)
        items.append(
            {
                "stage_code": stage.code,
                "key": stage.code,
                "step_number": stage.step_number,
                "stage_label": stage.label,
                "label": stage.label,
                "stage_status": stage_status,
                "status": stage_status,
                "completed_jobs": 1 if stage_status == "success" else 0,
                "total_jobs": 1,
                "progress_available": progress_available,
                "progress_percent": row.progress_percent if progress_available else None,
                "completed_units": row.completed_units if progress_available else None,
                "total_units": row.total_units if progress_available else None,
                "unit": row.unit if progress_available else None,
                "current_item": row.current_item if row is not None else None,
                "speed_bps": row.speed_bps if progress_available else None,
                "eta_seconds": row.eta_seconds if progress_available else None,
                "progress_source": row.progress_source if row is not None else "run-status-projection",
                "updated_at": _iso(row.updated_at) if row is not None else None,
            }
        )
    return items


def _public_stage_status(value: object) -> str:
    status = str(value or "pending").lower()
    if status in {"complete", "completed", "succeeded"}:
        return "success"
    if status in {"cancelled", "terminated"}:
        return "canceled"
    if status in {"accepted", "submitted", "started"}:
        return "running"
    return status


def wgs_stage_status_without_evidence(run_status: str | None) -> str:
    """Project a public stage status when no runtime stage row exists."""

    run_status = str(run_status or "created").lower()
    if run_status in {"failed", "unknown_interrupted"}:
        return "failed"
    if run_status in {"cancelled", "canceled"}:
        return "canceled"
    if run_status in {"created", "submitted", "queued"}:
        return "pending"
    return "running"


def _iso(value: object) -> str | None:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None
