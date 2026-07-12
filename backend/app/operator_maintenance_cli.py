from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from app.db import get_sessionmaker
from app.operator_maintenance_service import build_operator_correction_plan, execute_operator_correction_plan


CONFIRMATION = "CORRECT_RETAINED_PGTA_OPERATOR"


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or apply exact run operator corrections.")
    parser.add_argument("--expected", action="append", required=True, help="ANALYSIS_ID=OLD_OPERATOR")
    parser.add_argument("--new-operator", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirmation")
    args = parser.parse_args()
    expected = dict(_assignment(value) for value in args.expected)
    with get_sessionmaker()() as session:
        plan = build_operator_correction_plan(
            session=session,
            expected=expected,
            new_operator=args.new_operator,
            reason=args.reason,
        )
        payload: dict[str, object] = {"mode": "preview", "plan": asdict(plan)}
        if args.apply:
            if args.confirmation != CONFIRMATION:
                parser.error(f"--confirmation must equal {CONFIRMATION}")
            payload = {
                "mode": "applied",
                "plan": asdict(plan),
                "result": execute_operator_correction_plan(session=session, plan=plan),
            }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def _assignment(value: str) -> tuple[str, str]:
    analysis_id, separator, operator = value.partition("=")
    if not separator or not analysis_id.strip() or not operator.strip():
        raise ValueError("--expected must use ANALYSIS_ID=OLD_OPERATOR")
    return analysis_id.strip(), operator.strip()


if __name__ == "__main__":
    main()
