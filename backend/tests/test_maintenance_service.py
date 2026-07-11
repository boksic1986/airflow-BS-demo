import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.maintenance_service import CleanupSafetyError, build_cleanup_plan, execute_cleanup_plan
from app.models import AnalysisRun, Base, IntakeDiscovery, QcMetric, RunAction, Sample, SnakemakeRuleEvent


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def seed_runs(session_factory) -> None:
    with session_factory() as session:
        for analysis_id in ("KEEP_FULL", "DELETE_SMOKE", "DELETE_FAILED"):
            status = "success" if analysis_id != "DELETE_FAILED" else "failed"
            session.add(
                AnalysisRun(
                    analysis_id=analysis_id,
                    pipeline_name="pgta",
                    dag_id="bio_pgta",
                    mode="new",
                    status=status,
                    workdir=f"/data/airflow-demo/runs/{analysis_id}",
                    params_json={},
                )
            )
            session.add(Sample(analysis_id=analysis_id, sample_id=f"{analysis_id}_S1", status=status, qc_status="pass"))
            session.add(SnakemakeRuleEvent(analysis_id=analysis_id, rule="all", status=status, snakemake_jobid="0"))
            session.add(QcMetric(analysis_id=analysis_id, sample_id=f"{analysis_id}_S1", metric_name="qc", status="pass"))
            session.add(RunAction(analysis_id=analysis_id, action="submit", payload_json={}, result_status="accepted"))
        session.add(
            IntakeDiscovery(
                pipeline_name="pgta",
                root_path="/data/raw",
                batch_id="old-batch",
                fingerprint="abc",
                analysis_id="DELETE_SMOKE",
                ready_state="ready",
                submit_state="submitted",
            )
        )
        session.commit()


def test_cleanup_preview_is_read_only_and_apply_cascades_exact_snapshot() -> None:
    session_factory = make_test_sessionmaker()
    seed_runs(session_factory)
    with session_factory() as session:
        plan = build_cleanup_plan(session=session, keep_ids={"KEEP_FULL"}, expected_total=3)
        assert plan.delete_ids == ("DELETE_FAILED", "DELETE_SMOKE")
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 3

        result = execute_cleanup_plan(session=session, plan=plan)

        assert result == {"before": 3, "deleted": 2, "retained": 1, "cleared_intake_references": 1}
        assert session.scalars(select(AnalysisRun.analysis_id)).all() == ["KEEP_FULL"]
        assert session.scalar(select(func.count()).select_from(Sample)) == 1
        assert session.scalar(select(func.count()).select_from(SnakemakeRuleEvent)) == 1
        assert session.scalar(select(func.count()).select_from(QcMetric)) == 1
        assert session.scalar(select(func.count()).select_from(RunAction)) == 1
        intake = session.scalar(select(IntakeDiscovery))
        assert intake.analysis_id is None
        assert intake.submit_state == "bootstrap"


def test_cleanup_aborts_when_database_changes_after_preview() -> None:
    session_factory = make_test_sessionmaker()
    seed_runs(session_factory)
    with session_factory() as session:
        plan = build_cleanup_plan(session=session, keep_ids={"KEEP_FULL"}, expected_total=3)
        session.add(
            AnalysisRun(
                analysis_id="NEW_RUN_AFTER_PREVIEW",
                pipeline_name="pgta",
                dag_id="bio_pgta",
                mode="new",
                status="created",
                workdir="/data/airflow-demo/runs/NEW_RUN_AFTER_PREVIEW",
                params_json={},
            )
        )
        session.commit()

        with pytest.raises(CleanupSafetyError, match="changed after preview"):
            execute_cleanup_plan(session=session, plan=plan)

        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 4


def test_cleanup_requires_expected_total_and_existing_keep_ids() -> None:
    session_factory = make_test_sessionmaker()
    seed_runs(session_factory)
    with session_factory() as session:
        with pytest.raises(CleanupSafetyError, match="expected 4 runs, found 3"):
            build_cleanup_plan(session=session, keep_ids={"KEEP_FULL"}, expected_total=4)
        with pytest.raises(CleanupSafetyError, match="keep ids are missing"):
            build_cleanup_plan(session=session, keep_ids={"MISSING"}, expected_total=3)


def test_cleanup_requires_an_exact_override_for_a_stale_active_record() -> None:
    session_factory = make_test_sessionmaker()
    seed_runs(session_factory)
    with session_factory() as session:
        stale = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == "DELETE_SMOKE"))
        assert stale is not None
        stale.status = "running"
        session.commit()

        with pytest.raises(CleanupSafetyError, match="active runs must finish"):
            build_cleanup_plan(session=session, keep_ids={"KEEP_FULL"}, expected_total=3)

        plan = build_cleanup_plan(
            session=session,
            keep_ids={"KEEP_FULL"},
            expected_total=3,
            allow_active_delete_ids={"DELETE_SMOKE"},
        )
        assert plan.delete_ids == ("DELETE_FAILED", "DELETE_SMOKE")

        with pytest.raises(CleanupSafetyError, match="not active runs"):
            build_cleanup_plan(
                session=session,
                keep_ids={"KEEP_FULL"},
                expected_total=3,
                allow_active_delete_ids={"DELETE_FAILED"},
            )
