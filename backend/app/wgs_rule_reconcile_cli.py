from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.db import get_sessionmaker
from app.models import AnalysisRun, ObserverRunState
from app.wgs_observer import reconcile_rule_projection


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild one WGS Rule projection from registered evidence."
    )
    parser.add_argument("--analysis-id", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    args = parser.parse_args()

    settings = get_settings()
    root = Path(settings.wgs_evidence_root).resolve()
    with get_sessionmaker()() as session:
        run = session.scalar(
            select(AnalysisRun).where(
                AnalysisRun.analysis_id == args.analysis_id,
                AnalysisRun.pipeline_name == "wgs",
            )
        )
        state = session.scalar(
            select(ObserverRunState).where(
                ObserverRunState.analysis_id == args.analysis_id,
                ObserverRunState.attempt == args.attempt,
            )
        )
        if run is None or state is None:
            raise SystemExit("registered WGS run and observer evidence are required")
        relative = Path(state.relative_evidence_path)
        evidence = (root / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or root not in evidence.parents:
            raise SystemExit("registered evidence path escapes WGS_EVIDENCE_ROOT")
        result = reconcile_rule_projection(
            session,
            analysis_id=args.analysis_id,
            attempt=args.attempt,
            evidence_directory=evidence,
        )
        session.commit()
    print(json.dumps({"analysis_id": args.analysis_id, "attempt": args.attempt, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
