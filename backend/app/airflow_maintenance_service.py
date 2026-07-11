from __future__ import annotations

from dataclasses import dataclass


TERMINAL_STATES = {"success", "failed"}


class AirflowCleanupSafetyError(RuntimeError):
    pass


@dataclass(frozen=True)
class AirflowCleanupPlan:
    snapshot_runs: tuple[tuple[str, str, str], ...]
    keep_runs: tuple[tuple[str, str], ...]
    delete_runs: tuple[tuple[str, str], ...]
    delete_dags: tuple[str, ...]
    expected_counts: tuple[tuple[str, int], ...]


def build_airflow_cleanup_plan(
    *,
    client,
    keep_runs: dict[str, set[str]],
    delete_dags: set[str],
    expected_counts: dict[str, int],
) -> AirflowCleanupPlan:
    target_dags = set(keep_runs) | set(delete_dags)
    if target_dags != set(expected_counts):
        raise AirflowCleanupSafetyError("expected counts must cover exactly the retained and deleted DAGs")
    if set(keep_runs) & set(delete_dags):
        raise AirflowCleanupSafetyError("a DAG cannot be retained and deleted in the same cleanup")

    snapshot: list[tuple[str, str, str]] = []
    delete_runs: list[tuple[str, str]] = []
    normalized_keep: list[tuple[str, str]] = []
    for dag_id in sorted(target_dags):
        runs = _list_all_dag_runs(client=client, dag_id=dag_id)
        if len(runs) != expected_counts[dag_id]:
            raise AirflowCleanupSafetyError(
                f"expected {expected_counts[dag_id]} runs for {dag_id}, found {len(runs)}"
            )
        run_states = {str(item["dag_run_id"]): str(item.get("state") or "") for item in runs}
        keep_ids = set(keep_runs.get(dag_id, set()))
        missing = sorted(keep_ids - set(run_states))
        if missing:
            raise AirflowCleanupSafetyError(
                f"keep runs are missing for {dag_id}: {', '.join(missing)}"
            )
        invalid_keep = sorted(run_id for run_id in keep_ids if run_states[run_id] != "success")
        if invalid_keep:
            raise AirflowCleanupSafetyError(
                f"keep runs must be successful for {dag_id}: {', '.join(invalid_keep)}"
            )
        nonterminal = sorted(
            run_id for run_id, state in run_states.items() if state not in TERMINAL_STATES
        )
        if nonterminal:
            raise AirflowCleanupSafetyError(
                f"non-terminal runs block cleanup for {dag_id}: {', '.join(nonterminal)}"
            )
        snapshot.extend((dag_id, run_id, state) for run_id, state in run_states.items())
        normalized_keep.extend((dag_id, run_id) for run_id in keep_ids)
        if dag_id not in delete_dags:
            delete_runs.extend((dag_id, run_id) for run_id in run_states if run_id not in keep_ids)

    return AirflowCleanupPlan(
        snapshot_runs=tuple(sorted(snapshot)),
        keep_runs=tuple(sorted(normalized_keep)),
        delete_runs=tuple(sorted(delete_runs)),
        delete_dags=tuple(sorted(delete_dags)),
        expected_counts=tuple(sorted(expected_counts.items())),
    )


def execute_airflow_cleanup_plan(*, client, plan: AirflowCleanupPlan) -> dict[str, int]:
    try:
        current = build_airflow_cleanup_plan(
            client=client,
            keep_runs=_group_keep_runs(plan.keep_runs),
            delete_dags=set(plan.delete_dags),
            expected_counts=dict(plan.expected_counts),
        )
    except AirflowCleanupSafetyError as exc:
        raise AirflowCleanupSafetyError(
            f"Airflow history changed after preview: {exc}"
        ) from exc
    if current.snapshot_runs != plan.snapshot_runs:
        raise AirflowCleanupSafetyError("Airflow history changed after preview; generate a new cleanup plan")

    for dag_id, run_id in plan.delete_runs:
        client.delete_dag_run(dag_id, run_id)
    for dag_id in plan.delete_dags:
        client.delete_dag(dag_id)
    return {
        "deleted_runs": len(plan.delete_runs),
        "deleted_dags": len(plan.delete_dags),
        "retained_runs": len(plan.keep_runs),
    }


def _list_all_dag_runs(*, client, dag_id: str, page_size: int = 100) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    offset = 0
    while True:
        payload = client.list_dag_runs(dag_id, limit=page_size, offset=offset)
        page = list(payload.get("dag_runs") or [])
        items.extend(page)
        total = int(payload.get("total_entries", len(items)))
        if not page or len(items) >= total:
            return items
        offset += len(page)


def _group_keep_runs(items: tuple[tuple[str, str], ...]) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for dag_id, run_id in items:
        grouped.setdefault(dag_id, set()).add(run_id)
    return grouped
