import pytest

from app.airflow_maintenance_service import (
    AirflowCleanupSafetyError,
    build_airflow_cleanup_plan,
    execute_airflow_cleanup_plan,
)


class FakeAirflowClient:
    def __init__(self, runs_by_dag):
        self.runs_by_dag = {dag_id: list(items) for dag_id, items in runs_by_dag.items()}
        self.deleted_runs: list[tuple[str, str]] = []
        self.deleted_dags: list[str] = []

    def list_dag_runs(self, dag_id: str, *, limit: int = 100, offset: int = 0, order_by=None):
        del order_by
        items = self.runs_by_dag.get(dag_id, [])
        return {"dag_runs": items[offset : offset + limit], "total_entries": len(items)}

    def delete_dag_run(self, dag_id: str, run_id: str) -> None:
        self.deleted_runs.append((dag_id, run_id))
        self.runs_by_dag[dag_id] = [item for item in self.runs_by_dag[dag_id] if item["dag_run_id"] != run_id]

    def delete_dag(self, dag_id: str) -> None:
        self.deleted_dags.append(dag_id)
        self.runs_by_dag.pop(dag_id, None)


def run(run_id: str, state: str = "success") -> dict[str, str]:
    return {"dag_run_id": run_id, "state": state}


def test_airflow_cleanup_pages_history_and_keeps_only_approved_runs() -> None:
    pgta_runs = [run(f"old-{index}", "failed") for index in range(101)] + [run("keep-pgta")]
    client = FakeAirflowClient(
        {
            "bio_pgta": pgta_runs,
            "bio_nipt_docker": [run("old-nipt"), run("keep-nipt")],
            "bio_intake_scan": [run("old-scan"), run("keep-scan")],
            "bio_wes_qsub": [run("old-wes")],
        }
    )
    plan = build_airflow_cleanup_plan(
        client=client,
        keep_runs={
            "bio_pgta": {"keep-pgta"},
            "bio_nipt_docker": {"keep-nipt"},
            "bio_intake_scan": {"keep-scan"},
        },
        delete_dags={"bio_wes_qsub"},
        expected_counts={"bio_pgta": 102, "bio_nipt_docker": 2, "bio_intake_scan": 2, "bio_wes_qsub": 1},
    )

    assert len(plan.delete_runs) == 103
    assert plan.delete_dags == ("bio_wes_qsub",)
    result = execute_airflow_cleanup_plan(client=client, plan=plan)

    assert result == {"deleted_runs": 103, "deleted_dags": 1, "retained_runs": 3}
    assert client.deleted_dags == ["bio_wes_qsub"]
    assert {item["dag_run_id"] for item in client.runs_by_dag["bio_pgta"]} == {"keep-pgta"}
    assert {item["dag_run_id"] for item in client.runs_by_dag["bio_nipt_docker"]} == {"keep-nipt"}
    assert {item["dag_run_id"] for item in client.runs_by_dag["bio_intake_scan"]} == {"keep-scan"}


def test_airflow_cleanup_rejects_nonterminal_missing_or_changed_history() -> None:
    active = FakeAirflowClient({"bio_pgta": [run("keep"), run("active", "running")]})
    with pytest.raises(AirflowCleanupSafetyError, match="non-terminal"):
        build_airflow_cleanup_plan(
            client=active,
            keep_runs={"bio_pgta": {"keep"}},
            delete_dags=set(),
            expected_counts={"bio_pgta": 2},
        )

    missing = FakeAirflowClient({"bio_pgta": [run("old")]})
    with pytest.raises(AirflowCleanupSafetyError, match="keep runs are missing"):
        build_airflow_cleanup_plan(
            client=missing,
            keep_runs={"bio_pgta": {"keep"}},
            delete_dags=set(),
            expected_counts={"bio_pgta": 1},
        )

    changed = FakeAirflowClient({"bio_pgta": [run("old", "failed"), run("keep")]})
    plan = build_airflow_cleanup_plan(
        client=changed,
        keep_runs={"bio_pgta": {"keep"}},
        delete_dags=set(),
        expected_counts={"bio_pgta": 2},
    )
    changed.runs_by_dag["bio_pgta"].append(run("new-after-preview"))
    with pytest.raises(AirflowCleanupSafetyError, match="changed after preview"):
        execute_airflow_cleanup_plan(client=changed, plan=plan)
