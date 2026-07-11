from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from app.db import get_sessionmaker
from app.maintenance_service import build_cleanup_plan, execute_cleanup_plan


CONFIRMATION = "DELETE_NON_RETAINED_BIODEMO_RUNS"


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or apply an exact biodemo run cleanup plan.")
    parser.add_argument("--keep", action="append", required=True, dest="keep_ids")
    parser.add_argument("--expected-total", type=int, required=True)
    parser.add_argument(
        "--allow-active-delete",
        action="append",
        default=[],
        dest="allow_active_delete_ids",
        help="Explicit analysis ID of a stale active record that may be deleted.",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirmation")
    args = parser.parse_args()

    with get_sessionmaker()() as session:
        plan = build_cleanup_plan(
            session=session,
            keep_ids=set(args.keep_ids),
            expected_total=args.expected_total,
            allow_active_delete_ids=set(args.allow_active_delete_ids),
        )
        payload: dict[str, object] = {"mode": "preview", "plan": asdict(plan)}
        if args.apply:
            if args.confirmation != CONFIRMATION:
                parser.error(f"--confirmation must equal {CONFIRMATION}")
            payload = {"mode": "applied", "plan": asdict(plan), "result": execute_cleanup_plan(session=session, plan=plan)}
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
