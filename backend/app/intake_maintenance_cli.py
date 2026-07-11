from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from app.db import get_sessionmaker
from app.maintenance_service import build_intake_cleanup_plan, execute_intake_cleanup_plan


CONFIRMATION = "DELETE_NON_RETAINED_INTAKE_DISCOVERY"


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or apply exact intake discovery cleanup.")
    parser.add_argument("--expected-analysis", action="append", required=True, dest="expected_analysis_ids")
    parser.add_argument("--keep-analysis", action="append", required=True, dest="keep_analysis_ids")
    parser.add_argument("--expected-discovery-total", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirmation")
    args = parser.parse_args()

    with get_sessionmaker()() as session:
        plan = build_intake_cleanup_plan(
            session=session,
            expected_analysis_ids=set(args.expected_analysis_ids),
            keep_analysis_ids=set(args.keep_analysis_ids),
            expected_discovery_total=args.expected_discovery_total,
        )
        payload: dict[str, object] = {"mode": "preview", "plan": asdict(plan)}
        if args.apply:
            if args.confirmation != CONFIRMATION:
                parser.error(f"--confirmation must equal {CONFIRMATION}")
            payload = {
                "mode": "applied",
                "plan": asdict(plan),
                "result": execute_intake_cleanup_plan(session=session, plan=plan),
            }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
