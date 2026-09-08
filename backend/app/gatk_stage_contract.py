from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GatkStageDefinition:
    code: str
    label: str
    step_number: int


GATK_STAGES = (
    GatkStageDefinition("validate_request", "Validate", 0),
    GatkStageDefinition("prepare", "Prepare GATK contract", 1),
    GatkStageDefinition("step1_upload", "Upload FASTQ", 2),
    GatkStageDefinition("step2_master", "Create GATK Master", 3),
    GatkStageDefinition("step3_monitor", "Run GATK analysis", 4),
    GatkStageDefinition("step4_publish", "Publish results", 5),
    GatkStageDefinition("step5_download", "Download results", 6),
    GatkStageDefinition("step6_materialize", "Materialize delivery", 7),
    GatkStageDefinition("finalize_run", "Finalize", 8),
)


def gatk_stage_definition(code: str | None) -> GatkStageDefinition:
    value = str(code or "").strip()
    aliases = {
        "acquire_input_transfer_slot": "step1_upload",
        "release_input_transfer_slot": "step1_upload",
        "acquire_result_transfer_slot": "step5_download",
        "release_result_transfer_slot": "step5_download",
        "release_leases": "finalize_run",
    }
    value = aliases.get(value, value)
    return next(
        (item for item in GATK_STAGES if item.code == value),
        GATK_STAGES[0],
    )


def project_gatk_orchestration(
    *, run_status: str | None, current_stage: str | None, stage_rows: list[object]
) -> list[dict[str, object]]:
    rows = {str(row.stage_code): row for row in stage_rows}
    current = gatk_stage_definition(current_stage)
    terminal_status = str(run_status or "").lower()
    projected: list[dict[str, object]] = []
    for definition in GATK_STAGES:
        row = rows.get(definition.code)
        if row is not None:
            status = str(row.stage_status or "pending").lower()
        elif terminal_status == "success":
            status = "success"
        elif definition.step_number < current.step_number:
            status = "success"
        elif definition.step_number == current.step_number:
            status = terminal_status if terminal_status in {"failed", "canceled", "terminated"} else "running"
        else:
            status = "pending"
        projected.append(
            {
                "stage_code": definition.code,
                "step_number": definition.step_number,
                "label": definition.label,
                "status": status,
                "stage_status": status,
                "progress_available": bool(
                    row is not None and getattr(row, "progress_available", False)
                ),
                "progress_percent": getattr(row, "progress_percent", None)
                if row is not None
                else None,
                "completed_units": getattr(row, "completed_units", None)
                if row is not None
                else None,
                "total_units": getattr(row, "total_units", None)
                if row is not None
                else None,
                "unit": getattr(row, "unit", None) if row is not None else None,
                "completed_jobs": 1 if status == "success" else 0,
                "total_jobs": 1,
            }
        )
    return projected
