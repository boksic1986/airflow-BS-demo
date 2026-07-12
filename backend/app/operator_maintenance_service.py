from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisRun, RunAction


class OperatorCorrectionSafetyError(RuntimeError):
    pass


@dataclass(frozen=True)
class OperatorCorrectionPlan:
    snapshot: tuple[tuple[str, str, str | None], ...]
    new_operator: str
    reason: str


def build_operator_correction_plan(
    *,
    session: Session,
    expected: dict[str, str],
    new_operator: str,
    reason: str,
) -> OperatorCorrectionPlan:
    operator = new_operator.strip()
    correction_reason = reason.strip()
    if not expected or not operator or not correction_reason:
        raise OperatorCorrectionSafetyError("expected runs, new operator, and reason are required")
    runs = list(session.scalars(select(AnalysisRun).where(AnalysisRun.analysis_id.in_(expected))).all())
    by_id = {run.analysis_id: run for run in runs}
    missing = sorted(set(expected) - set(by_id))
    if missing:
        raise OperatorCorrectionSafetyError("operator correction runs are missing: " + ", ".join(missing))
    invalid_status = sorted(run.analysis_id for run in runs if run.status != "success")
    if invalid_status:
        raise OperatorCorrectionSafetyError(
            "operator correction requires terminal successful runs: " + ", ".join(invalid_status)
        )
    changed = sorted(
        run.analysis_id for run in runs if (run.submitted_by or "") != expected[run.analysis_id]
    )
    if changed:
        raise OperatorCorrectionSafetyError("operator snapshot changed for: " + ", ".join(changed))
    return OperatorCorrectionPlan(
        snapshot=tuple(sorted((run.analysis_id, run.status, run.submitted_by) for run in runs)),
        new_operator=operator[:128],
        reason=correction_reason,
    )


def execute_operator_correction_plan(*, session: Session, plan: OperatorCorrectionPlan) -> dict[str, object]:
    expected = {analysis_id: old_operator or "" for analysis_id, _status, old_operator in plan.snapshot}
    current = build_operator_correction_plan(
        session=session,
        expected=expected,
        new_operator=plan.new_operator,
        reason=plan.reason,
    )
    if current.snapshot != plan.snapshot:
        raise OperatorCorrectionSafetyError("operator metadata changed after preview")
    runs = list(session.scalars(select(AnalysisRun).where(AnalysisRun.analysis_id.in_(expected))).all())
    for run in runs:
        old_operator = run.submitted_by
        run.submitted_by = plan.new_operator
        session.add(
            RunAction(
                analysis_id=run.analysis_id,
                action="metadata_correction",
                requested_by=plan.new_operator,
                payload_json={
                    "old_operator": old_operator,
                    "new_operator": plan.new_operator,
                    "reason": plan.reason,
                },
                result_status="success",
                message="Operator audit label corrected without changing workflow provenance.",
            )
        )
    session.commit()
    return {"updated": len(runs), "new_operator": plan.new_operator}
