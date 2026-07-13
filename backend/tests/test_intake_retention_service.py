from datetime import datetime, timedelta, timezone

import pytest

from app.intake_retention_service import prune_scanner_history


class FakeAirflowClient:
    def __init__(self, runs):
        self.runs = list(runs)
        self.deleted: list[tuple[str, str]] = []

    def list_dag_runs(self, dag_id, *, limit=100, offset=0, order_by=None):
        assert dag_id == "bio_intake_scan"
        page = self.runs[offset : offset + limit]
        return {"dag_runs": page, "total_entries": len(self.runs)}

    def delete_dag_run(self, dag_id, dag_run_id):
        self.deleted.append((dag_id, dag_run_id))


def _run(run_id: str, state: str, ended_at: datetime | None) -> dict:
    return {
        "dag_run_id": run_id,
        "state": state,
        "end_date": ended_at.isoformat() if ended_at else None,
    }


def test_retention_deletes_only_old_terminal_scanner_runs() -> None:
    now = datetime(2026, 7, 13, tzinfo=timezone.utc)
    client = FakeAirflowClient(
        [
            _run("old-success", "success", now - timedelta(days=31)),
            _run("old-failed", "failed", now - timedelta(days=45)),
            _run("recent-success", "success", now - timedelta(days=2)),
            _run("current-running", "running", None),
        ]
    )

    result = prune_scanner_history(
        airflow_client=client,
        dag_id="bio_intake_scan",
        cutoff=now - timedelta(days=30),
        current_dag_run_id="current-running",
        dry_run=False,
    )

    assert client.deleted == [
        ("bio_intake_scan", "old-success"),
        ("bio_intake_scan", "old-failed"),
    ]
    assert result["deleted"] == 2
    assert result["protected"] == 2


def test_retention_rejects_analysis_dag() -> None:
    with pytest.raises(ValueError, match="bio_intake_scan"):
        prune_scanner_history(
            airflow_client=FakeAirflowClient([]),
            dag_id="bio_pgta",
            cutoff=datetime.now(timezone.utc),
            current_dag_run_id=None,
            dry_run=True,
        )
