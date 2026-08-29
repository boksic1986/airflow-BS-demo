from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import WgsIntakeBatch, WgsIntakeScannerState


def reset_wgs_intake_baseline(session: Session) -> dict[str, int]:
    """Delete scanner-only history after proving no discovery is linked to a run."""

    linked = session.scalar(
        select(func.count())
        .select_from(WgsIntakeBatch)
        .where(WgsIntakeBatch.analysis_id.is_not(None))
    ) or 0
    if linked:
        raise ValueError(
            f"refusing WGS intake reset: {linked} row(s) have a linked AnalysisRun"
        )
    batches = session.scalar(select(func.count()).select_from(WgsIntakeBatch)) or 0
    scanner_states = (
        session.scalar(select(func.count()).select_from(WgsIntakeScannerState)) or 0
    )
    session.execute(delete(WgsIntakeBatch))
    session.execute(delete(WgsIntakeScannerState))
    return {
        "deleted_batches": int(batches),
        "deleted_scanner_states": int(scanner_states),
    }
