from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, WgsIntakeBatch
from app.wgs_auto_dispatch import dispatch_ready_wgs_intake


class RecordingAirflow:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trigger_dag_run(self, dag_id, *, dag_run_id=None, conf=None):
        value = {"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf}
        self.calls.append(value)
        return value

    def get_dag_run(self, dag_id, dag_run_id):
        return next(
            (
                item
                for item in self.calls
                if item["dag_id"] == dag_id and item["dag_run_id"] == dag_run_id
            ),
            None,
        )


def settings(tmp_path: Path, *, not_before: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        wgs_auto_dispatch_enabled=True,
        wgs_auto_dispatch_not_before=not_before.isoformat(),
        wgs_project_catalog_path=str(Path(__file__).parents[2] / "config" / "wgs_projects.yaml"),
        wgs_release_catalog_path=str(Path(__file__).parents[2] / "config" / "wgs_releases.yaml"),
        host_results_root=str(tmp_path / "results"),
        container_shared_root=str(tmp_path / "shared"),
    )


def sessionmaker_for_test():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def ready_row(*, batch: str, ready_at: datetime) -> WgsIntakeBatch:
    return WgsIntakeBatch(
        source_path=f"/bi/fastq/T7_Fastq/2300th_{batch}_E250000001",
        chip_id=f"2300th_{batch}_E250000001",
        sequencing_batch=batch,
        state="ready",
        eligible_pair_count=2,
        pair_issue_count=0,
        excluded_addon_pair_count=0,
        eligible_fingerprint="a" * 64,
        observed_fingerprint="a" * 64,
        first_seen_at=ready_at,
        last_scanned_at=ready_at,
        ready_at=ready_at,
    )


def test_auto_dispatch_skips_and_links_a_batch_already_submitted_manually(
    tmp_path: Path,
) -> None:
    sessions = sessionmaker_for_test()
    now = datetime(2026, 9, 4, 8, 0, tzinfo=timezone.utc)
    airflow = RecordingAirflow()
    with sessions() as session:
        session.add(ready_row(batch="20260904A", ready_at=now))
        session.add(
            AnalysisRun(
                analysis_id="WGS_MANUAL_1",
                pipeline_name="wgs",
                dag_id="bio_wgs",
                dag_run_id="WGS_MANUAL_1-a1",
                execution_mode="cce",
                status="running",
                workdir=str(tmp_path / "manual"),
                params_json={"sequencing_batch": "20260904A"},
                submitted_by="operator",
            )
        )
        session.commit()

        result = dispatch_ready_wgs_intake(
            session=session,
            settings=settings(tmp_path, not_before=now - timedelta(minutes=1)),
            airflow_client=airflow,
            now=now,
        )
        row = session.scalar(select(WgsIntakeBatch))

    assert result["already_registered"] == 1
    assert result["submitted"] == 0
    assert row.analysis_id == "WGS_MANUAL_1"
    assert airflow.calls == []


def test_auto_dispatch_creates_one_preapproved_run_and_repeat_is_idempotent(
    tmp_path: Path,
) -> None:
    sessions = sessionmaker_for_test()
    now = datetime(2026, 9, 4, 8, 0, tzinfo=timezone.utc)
    airflow = RecordingAirflow()
    config = settings(tmp_path, not_before=now - timedelta(minutes=1))
    with sessions() as session:
        session.add(ready_row(batch="20260904B", ready_at=now))
        session.commit()
        first = dispatch_ready_wgs_intake(
            session=session,
            settings=config,
            airflow_client=airflow,
            now=now,
        )
        second = dispatch_ready_wgs_intake(
            session=session,
            settings=config,
            airflow_client=airflow,
            now=now + timedelta(minutes=10),
        )
        row = session.scalar(select(WgsIntakeBatch))
        run = session.scalar(select(AnalysisRun))

    assert first["submitted"] == 1
    assert second["already_registered"] == 1
    assert row.analysis_id == run.analysis_id
    assert run.params_json["submission_mode"] == "auto_dispatch"
    assert run.params_json["sequencing_batch"] == "20260904B"
    assert len(airflow.calls) == 1


def test_auto_dispatch_does_not_launch_ready_rows_before_activation_watermark(
    tmp_path: Path,
) -> None:
    sessions = sessionmaker_for_test()
    now = datetime(2026, 9, 4, 8, 0, tzinfo=timezone.utc)
    airflow = RecordingAirflow()
    with sessions() as session:
        session.add(ready_row(batch="20260903A", ready_at=now - timedelta(days=1)))
        session.commit()
        result = dispatch_ready_wgs_intake(
            session=session,
            settings=settings(tmp_path, not_before=now),
            airflow_client=airflow,
            now=now,
        )

    assert result["baseline_skipped"] == 1
    assert result["submitted"] == 0
    assert airflow.calls == []
