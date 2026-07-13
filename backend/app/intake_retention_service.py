from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SCANNER_DAG_ID = "bio_intake_scan"
TERMINAL_STATES = {"success", "failed"}


def prune_scanner_history(
    *,
    airflow_client,
    dag_id: str,
    cutoff: datetime,
    current_dag_run_id: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    if dag_id != SCANNER_DAG_ID:
        raise ValueError(f"Retention is restricted to {SCANNER_DAG_ID}.")

    runs = _list_all_runs(airflow_client=airflow_client, dag_id=dag_id)
    delete_ids: list[str] = []
    protected = 0
    for run in runs:
        run_id = str(run.get("dag_run_id") or "")
        state = str(run.get("state") or "").lower()
        ended_at = _parse_datetime(run.get("end_date"))
        if (
            not run_id
            or run_id == current_dag_run_id
            or state not in TERMINAL_STATES
            or ended_at is None
            or ended_at >= cutoff
        ):
            protected += 1
            continue
        delete_ids.append(run_id)

    if not dry_run:
        for run_id in delete_ids:
            airflow_client.delete_dag_run(dag_id, run_id)
    return {
        "dag_id": dag_id,
        "cutoff": _as_aware(cutoff).isoformat(),
        "dry_run": dry_run,
        "candidates": len(delete_ids),
        "deleted": 0 if dry_run else len(delete_ids),
        "protected": protected,
        "dag_run_ids": delete_ids,
    }


def _list_all_runs(*, airflow_client, dag_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    offset = 0
    page_size = 100
    while True:
        payload = airflow_client.list_dag_runs(dag_id, limit=page_size, offset=offset)
        page = list(payload.get("dag_runs") or [])
        items.extend(page)
        total = int(payload.get("total_entries") or len(items))
        if not page or len(items) >= total or len(page) < page_size:
            break
        offset += len(page)
    return items


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return _as_aware(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError:
        return None


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
