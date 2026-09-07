from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest
from sqlalchemy import select

from app.models import AnalysisRun, Base, RunStageState, WgsMaintenanceAction
from app.wgs_step7_service import authorize_step7_runtime, get_step7_capability, request_step7_cleanup


class FakeAirflow:
    def __init__(self) -> None:
        self.calls = []
        self.runs = {}

    def trigger_dag_run(self, dag_id, *, dag_run_id, conf):
        self.calls.append((dag_id, dag_run_id, conf))
        payload = {"dag_run_id": dag_run_id, "conf": conf}
        self.runs[(dag_id, dag_run_id)] = payload
        return payload

    def get_dag_run(self, dag_id, dag_run_id):
        return self.runs.get((dag_id, dag_run_id))


def test_step7_requires_successful_delivery_and_uses_server_generated_contract() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    airflow = FakeAirflow()
    with sessions() as session:
        run = AnalysisRun(
            analysis_id="WGS_20260901_010203_A1B2C3",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            dag_run_id="manual__wgs",
            execution_mode="cce",
            attempt=1,
            status="success",
            workdir="/data/wgs-results/run",
            params_json={
                "batch_no": "WGS_20260901A_T7Hg38V4.1.1",
                "sequencing_batch": "20260901A",
                "analysis_batch": "20260901A",
            },
        )
        session.add(run)
        for stage in ("step5_download", "step6_materialize"):
            session.add(
                RunStageState(
                    analysis_id=run.analysis_id,
                    attempt=1,
                    stage_code=stage,
                    stage_label=stage,
                    stage_status="success",
                    progress_source="test",
                )
            )
        session.commit()
        capability = get_step7_capability(
            session=session, run=run, execution_enabled=True, runtime_adapter_enabled=True
        )
        assert capability["available"] is True
        assert capability["required_batch"] == "20260901A"
        action = request_step7_cleanup(
            session=session,
            airflow_client=airflow,
            analysis_id=run.analysis_id,
            batch_confirmation=" 20260901A ",
            requested_by="admin",
        )
        assert action["action_type"] == "cleanup_step7_sfs"
        assert airflow.calls[0][2]["maintenance_mode"] == "cleanup_step7"
        assert "confirm" not in airflow.calls[0][2]
        assert "path" not in airflow.calls[0][2]
        persisted = session.scalar(select(WgsMaintenanceAction))
        assert authorize_step7_runtime(
            session=session, run=run, action_id=persisted.action_id
        ).action_id == persisted.action_id
        with pytest.raises(ValueError, match="no active admin"):
            authorize_step7_runtime(
                session=session, run=run, action_id="step7-sfs-forged"
            )


def test_step7_persists_requested_action_before_airflow_and_reuses_dag_run() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    airflow = FakeAirflow()
    with sessions() as session:
        run = AnalysisRun(
            analysis_id="WGS_20260901_010203_D4E5F6",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            dag_run_id="manual__wgs",
            execution_mode="cce",
            attempt=1,
            status="success",
            workdir="/data/wgs-results/run2",
            params_json={"batch_no": "WGS_20260901B_T7Hg38V4.1.1"},
        )
        session.add(run)
        for stage in ("step5_download", "step6_materialize"):
            session.add(RunStageState(
                analysis_id=run.analysis_id,
                attempt=1,
                stage_code=stage,
                stage_label=stage,
                stage_status="success",
                progress_source="test",
            ))
        session.commit()
        original_trigger = airflow.trigger_dag_run

        def fail_before_create(*args, **kwargs):
            raise RuntimeError("Airflow unavailable")

        airflow.trigger_dag_run = fail_before_create
        with pytest.raises(RuntimeError, match="unavailable"):
            request_step7_cleanup(
                session=session,
                airflow_client=airflow,
                analysis_id=run.analysis_id,
                batch_confirmation="WGS_20260901B_T7Hg38V4.1.1",
                requested_by="admin",
            )
        action = session.scalar(select(WgsMaintenanceAction))
        assert action is not None
        assert action.status == "requested"

        airflow.trigger_dag_run = original_trigger
        retried = request_step7_cleanup(
            session=session,
            airflow_client=airflow,
            analysis_id=run.analysis_id,
            batch_confirmation="WGS_20260901B_T7Hg38V4.1.1",
            requested_by="admin",
        )
        assert retried["action_id"] == action.action_id
        assert retried["status"] == "queued"
        assert len(airflow.calls) == 1


@pytest.mark.parametrize(
    ("terminal_status", "expected_reason"),
    (("success", "cleanup_completed"), ("failed", "cleanup_failed")),
)
def test_step7_terminal_action_is_not_presented_as_runnable_again(
    terminal_status: str, expected_reason: str
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        run = AnalysisRun(
            analysis_id="WGS_20260901_010203_A7B8C9",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            dag_run_id="manual__wgs",
            execution_mode="cce",
            attempt=1,
            status="success",
            workdir="/data/wgs-results/run3",
            params_json={"analysis_batch": "20260901C"},
        )
        session.add(run)
        for stage in ("step5_download", "step6_materialize"):
            session.add(
                RunStageState(
                    analysis_id=run.analysis_id,
                    attempt=1,
                    stage_code=stage,
                    stage_label=stage,
                    stage_status="success",
                    progress_source="test",
                )
            )
        session.add(
            WgsMaintenanceAction(
                action_id="step7-sfs-terminal",
                analysis_id=run.analysis_id,
                attempt=1,
                action_type="cleanup_step7_sfs",
                linkage_group="sfs",
                status=terminal_status,
                requested_by="admin",
                source_dag_run_id=run.dag_run_id,
                maintenance_dag_run_id="maintenance__step7",
            )
        )
        session.commit()

        capability = get_step7_capability(
            session=session,
            run=run,
            execution_enabled=True,
            runtime_adapter_enabled=True,
        )

        assert capability["available"] is False
        assert capability["reason"] == expected_reason
        assert capability["latest_action"]["status"] == terminal_status


def test_failed_step7_can_retry_as_new_generation_without_overwriting_history() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    airflow = FakeAirflow()
    with sessions() as session:
        run = AnalysisRun(
            analysis_id="WGS_20260906_092052_75A45B",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            dag_run_id="scheduled__wgs",
            execution_mode="cce",
            attempt=1,
            status="success",
            workdir="/runtime/runs/WGS_20260906_092052_75A45B/attempt-1",
            params_json={"analysis_batch": "20260905A", "project_name": "WGS_Clinical"},
        )
        session.add(run)
        for stage in ("step5_download", "step6_materialize"):
            session.add(RunStageState(
                analysis_id=run.analysis_id,
                attempt=1,
                stage_code=stage,
                stage_label=stage,
                stage_status="success",
                progress_source="test",
            ))
        failed = WgsMaintenanceAction(
            action_id="step7-sfs-generation-1",
            analysis_id=run.analysis_id,
            attempt=1,
            action_type="cleanup_step7_sfs",
            linkage_group="sfs",
            generation=1,
            status="failed",
            requested_by="admin",
            source_dag_run_id=run.dag_run_id,
            maintenance_dag_run_id="maintenance__generation1",
            error_message="WGS_RUNTIME_RUN_ROOT is required",
            target_snapshot_json={"project": "WGS_Clinical", "batch": "20260905A"},
        )
        session.add(failed)
        session.commit()

        retried = request_step7_cleanup(
            session=session,
            airflow_client=airflow,
            analysis_id=run.analysis_id,
            batch_confirmation="20260905A",
            requested_by="admin",
            retry_failed=True,
            expected_action_id=failed.action_id,
        )

        history = list(session.scalars(
            select(WgsMaintenanceAction)
            .where(WgsMaintenanceAction.analysis_id == run.analysis_id)
            .order_by(WgsMaintenanceAction.generation)
        ))
        assert [item.generation for item in history] == [1, 2]
        assert history[0].status == "failed"
        assert history[1].retry_of_action_id == history[0].action_id
        assert retried["generation"] == 2
        assert airflow.calls[0][2]["step7_target_snapshot"]["batch"] == "20260905A"


def test_step7_retry_rejects_stale_expected_action() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        run = AnalysisRun(
            analysis_id="WGS_20260903_111456_397777",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            attempt=1,
            status="success",
            workdir="/runtime/run",
            params_json={"analysis_batch": "20260902A"},
        )
        session.add(run)
        for stage in ("step5_download", "step6_materialize"):
            session.add(RunStageState(analysis_id=run.analysis_id, attempt=1, stage_code=stage, stage_label=stage, stage_status="success", progress_source="test"))
        session.add(WgsMaintenanceAction(
            action_id="step7-current",
            analysis_id=run.analysis_id,
            attempt=1,
            action_type="cleanup_step7_sfs",
            generation=1,
            linkage_group="sfs",
            status="failed",
            requested_by="admin",
        ))
        session.commit()

        with pytest.raises(ValueError, match="stale_step7_action"):
            request_step7_cleanup(
                session=session,
                airflow_client=FakeAirflow(),
                analysis_id=run.analysis_id,
                batch_confirmation="20260902A",
                requested_by="admin",
                retry_failed=True,
                expected_action_id="step7-old",
            )
