from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from app.airflow_client import AirflowClient
from app.airflow_maintenance_service import build_airflow_cleanup_plan, execute_airflow_cleanup_plan
from app.config import get_settings


CONFIRMATION = "DELETE_NON_RETAINED_AIRFLOW_HISTORY"


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or apply exact Airflow history cleanup.")
    parser.add_argument("--keep-run", action="append", default=[])
    parser.add_argument("--delete-dag", action="append", default=[])
    parser.add_argument("--expected-count", action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirmation")
    args = parser.parse_args()

    keep_runs: dict[str, set[str]] = {}
    for value in args.keep_run:
        dag_id, run_id = _split_assignment(value, "--keep-run")
        keep_runs.setdefault(dag_id, set()).add(run_id)
    expected_counts = {
        dag_id: int(count)
        for dag_id, count in (_split_assignment(value, "--expected-count") for value in args.expected_count)
    }
    settings = get_settings()
    client = AirflowClient(
        base_url=settings.airflow_base_url,
        username=settings.airflow_api_username,
        password=settings.airflow_api_password,
    )
    plan = build_airflow_cleanup_plan(
        client=client,
        keep_runs=keep_runs,
        delete_dags=set(args.delete_dag),
        expected_counts=expected_counts,
    )
    payload: dict[str, object] = {"mode": "preview", "plan": asdict(plan)}
    if args.apply:
        if args.confirmation != CONFIRMATION:
            parser.error(f"--confirmation must equal {CONFIRMATION}")
        payload = {
            "mode": "applied",
            "plan": asdict(plan),
            "result": execute_airflow_cleanup_plan(client=client, plan=plan),
        }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def _split_assignment(value: str, option: str) -> tuple[str, str]:
    key, separator, item = value.partition("=")
    if not separator or not key.strip() or not item.strip():
        raise ValueError(f"{option} must use DAG_ID=VALUE")
    return key.strip(), item.strip()


if __name__ == "__main__":
    main()
