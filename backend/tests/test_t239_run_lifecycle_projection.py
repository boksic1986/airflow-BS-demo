from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, KubernetesWorkload, RunStageState, Sample
from app.wgs_lifecycle_service import project_wgs_lifecycle
from app.wgs_step7_service import get_step7_capability
from app.wgs_workspace_service import build_wgs_workspace


def _sessions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _successful_run(analysis_id: str = "WGS_T239") -> AnalysisRun:
    return AnalysisRun(
        analysis_id=analysis_id,
        pipeline_name="wgs",
        dag_id="bio_wgs",
        dag_run_id=f"manual__{analysis_id}",
        execution_mode="cce",
        attempt=1,
        status="success",
        workdir=f"/runs/{analysis_id}",
        submitted_by="wgs-intake-scanner",
        params_json={"analysis_batch": "20260906B"},
    )


def _add_terminal_delivery_stages(session, run: AnalysisRun) -> None:
    for stage in ("step5_download", "step6_materialize"):
        session.add(
            RunStageState(
                analysis_id=run.analysis_id,
                attempt=run.attempt,
                stage_code=stage,
                stage_label=stage,
                stage_status="success",
                progress_source="test",
            )
        )


def test_workspace_summary_aggregates_batch_qc_from_all_samples() -> None:
    factory = _sessions()
    with factory.begin() as session:
        run = _successful_run()
        session.add(run)
        session.add_all(
            [
                Sample(analysis_id=run.analysis_id, sample_id="S1", qc_status="pass"),
                Sample(analysis_id=run.analysis_id, sample_id="S2", qc_status="success"),
            ]
        )

    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        workspace = build_wgs_workspace(
            session=session,
            run=run,
            run_payload={"analysis_id": run.analysis_id},
        )

    assert workspace["summary"]["batch_qc_status"] == "pass"


def test_lifecycle_workflow_operator_matches_run_operator_display_name() -> None:
    factory = _sessions()
    with factory.begin() as session:
        session.add(_successful_run())

    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        lifecycle = project_wgs_lifecycle(session=session, run=run)

    assert lifecycle["workflow"]["updated_by"] == "wgs-scanner"


def test_step7_ignores_stale_child_workloads_after_terminal_master() -> None:
    factory = _sessions()
    now = datetime(2026, 9, 8, 2, 20, tzinfo=timezone.utc)
    with factory.begin() as session:
        run = _successful_run()
        session.add(run)
        _add_terminal_delivery_stages(session, run)
        session.add_all(
            [
                KubernetesWorkload(
                    analysis_id=run.analysis_id,
                    attempt=1,
                    event_id="child-stale",
                    pod_hash="child-stale",
                    job_name="snakejob-stale",
                    phase="Running",
                    resources_json={"workload_role": "work"},
                    observed_at=now - timedelta(minutes=10),
                    updated_at=now - timedelta(minutes=10),
                ),
                KubernetesWorkload(
                    analysis_id=run.analysis_id,
                    attempt=1,
                    event_id="master-success",
                    pod_hash="master-success",
                    job_name="wgs-master",
                    phase="Succeeded",
                    resources_json={"workload_role": "master"},
                    observed_at=now,
                    updated_at=now,
                ),
            ]
        )

    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        capability = get_step7_capability(
            session=session,
            run=run,
            execution_enabled=True,
            runtime_adapter_enabled=True,
        )

    assert capability["available"] is True
    assert capability["reason"] is None


def test_step7_still_blocks_an_active_workload_newer_than_terminal_master() -> None:
    factory = _sessions()
    now = datetime(2026, 9, 8, 2, 20, tzinfo=timezone.utc)
    with factory.begin() as session:
        run = _successful_run("WGS_T239_LIVE")
        session.add(run)
        _add_terminal_delivery_stages(session, run)
        session.add_all(
            [
                KubernetesWorkload(
                    analysis_id=run.analysis_id,
                    attempt=1,
                    event_id="master-success",
                    pod_hash="master-success",
                    job_name="wgs-master",
                    phase="Succeeded",
                    resources_json={"workload_role": "master"},
                    observed_at=now,
                    updated_at=now,
                ),
                KubernetesWorkload(
                    analysis_id=run.analysis_id,
                    attempt=1,
                    event_id="child-live",
                    pod_hash="child-live",
                    job_name="snakejob-live",
                    phase="Running",
                    resources_json={"workload_role": "work"},
                    observed_at=now + timedelta(seconds=1),
                    updated_at=now + timedelta(seconds=1),
                ),
            ]
        )

    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        capability = get_step7_capability(
            session=session,
            run=run,
            execution_enabled=True,
            runtime_adapter_enabled=True,
        )

    assert capability["available"] is False
    assert capability["reason"] == "cce_workload_active"
