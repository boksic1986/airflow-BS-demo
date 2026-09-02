from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, KubernetesWorkload, RuleState, RunStageState
from app.wgs_timing_service import enrich_progress, serialize_rule_states


def test_analysis_eta_is_not_inferred_from_coarse_stage_position() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    now = datetime.now(timezone.utc)
    release_id = "wgs-4.1.1-1656b5d"

    with sessions() as session:
        current = AnalysisRun(
            analysis_id="WGS_CURRENT",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            status="running",
            workdir="/data/wgs-results/runs/WGS_CURRENT",
            current_stage="step3_monitor",
            params_json={"pipeline_release_id": release_id},
        )
        session.add(current)
        for index in range(3):
            ended = now - timedelta(days=40 - index)
            session.add(
                AnalysisRun(
                    analysis_id=f"WGS_MATCH_{index}",
                    pipeline_name="wgs",
                    dag_id="bio_wgs",
                    execution_mode="cce",
                    status="success",
                    workdir=f"/data/wgs-results/runs/WGS_MATCH_{index}",
                    started_at=ended - timedelta(hours=10),
                    ended_at=ended,
                    params_json={"pipeline_release_id": release_id},
                )
            )
        for index in range(20):
            ended = now - timedelta(hours=index)
            session.add(
                AnalysisRun(
                    analysis_id=f"WGS_OTHER_{index}",
                    pipeline_name="wgs",
                    dag_id="bio_wgs",
                    execution_mode="cce",
                    status="success",
                    workdir=f"/data/wgs-results/runs/WGS_OTHER_{index}",
                    started_at=ended - timedelta(hours=2),
                    ended_at=ended,
                    params_json={"pipeline_release_id": "wgs-4.1.0-deadbee"},
                )
            )
        session.commit()

        payload = enrich_progress(session=session, run=current, payload={})

    assert "overall_progress_percent" not in payload
    assert payload["analysis_eta_history_count"] == 0
    assert payload["analysis_eta_model"] == "runtime_exact_eta_unavailable"
    assert payload["analysis_eta_seconds"] is None


def test_progress_uses_bound_master_current_rule_when_rule_events_lag() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with sessions() as session:
        current = AnalysisRun(
            analysis_id="WGS_CURRENT",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            status="running",
            attempt=1,
            workdir="/data/wgs-results/runs/WGS_CURRENT",
            current_stage="step3_monitor",
            params_json={"pipeline_release_id": "wgs-4.1.1-test"},
        )
        session.add(current)
        session.add(
            KubernetesWorkload(
                analysis_id=current.analysis_id,
                attempt=1,
                event_id="step3:cce-master-test",
                pod_hash="step3-master-status",
                job_name="cce-master-test",
                phase="Running",
                job_status_json={
                    "current_rule": "pre_process_mapping",
                    "current_rules": ["pre_process_mapping", "pre_process_Dedup"],
                },
            )
        )
        session.commit()

        payload = enrich_progress(session=session, run=current, payload={})

    assert payload["current_rule"] == "pre_process_mapping"


def test_wgs_progress_uses_authoritative_stage_units_not_airflow_task_count() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with sessions() as session:
        current = AnalysisRun(
            analysis_id="WGS_STAGE_PROGRESS",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            status="running",
            attempt=1,
            workdir="/data/wgs-results/runs/WGS_STAGE_PROGRESS",
            current_stage="step3_monitor",
            params_json={"pipeline_release_id": "wgs-4.1.1-test"},
        )
        session.add(current)
        session.add(
            RunStageState(
                analysis_id=current.analysis_id,
                attempt=1,
                stage_code="step3_monitor",
                step_number=3,
                stage_label="WGS workflow running",
                stage_status="running",
                progress_available=True,
                progress_percent=99,
                completed_units=206,
                total_units=209,
                unit="rules",
                current_item="cloud_finalize_delivery",
                progress_source="cce-pipeline.step3-status.v2",
            )
        )
        session.commit()

        payload = enrich_progress(
            session=session,
            run=current,
            payload={"percent": 45, "current_step": "wait_step3_analysis"},
        )

    assert payload["stage_code"] == "step3_monitor"
    assert payload["step_number"] == 3
    assert payload["stage_label"] == "WGS workflow running"
    assert payload["stage_status"] == "running"
    assert payload["progress_available"] is True
    assert payload["progress_percent"] == 99
    assert payload["completed_units"] == 206
    assert payload["total_units"] == 209
    assert payload["unit"] == "rules"
    assert payload["current_item"] == "cloud_finalize_delivery"
    assert payload["progress_source"] == "cce-pipeline.step3-status.v2"
    assert payload["percent"] == 99


def test_wgs_progress_does_not_fabricate_numeric_progress_for_step4() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with sessions() as session:
        current = AnalysisRun(
            analysis_id="WGS_STAGE_INDETERMINATE",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            status="publishing",
            attempt=1,
            workdir="/data/wgs-results/runs/WGS_STAGE_INDETERMINATE",
            current_stage="step4_publish",
            params_json={"pipeline_release_id": "wgs-4.1.1-test"},
        )
        session.add(current)
        session.add(
            RunStageState(
                analysis_id=current.analysis_id,
                attempt=1,
                stage_code="step4_publish",
                step_number=4,
                stage_label="Publishing WGS results",
                stage_status="running",
                progress_available=False,
                progress_source="wgs-runtime.stage-status.v1",
            )
        )
        session.commit()

        payload = enrich_progress(
            session=session,
            run=current,
            payload={"percent": 87, "current_step": "wait_step4_publish"},
        )

    assert payload["progress_available"] is False
    assert payload["progress_percent"] is None
    assert payload["completed_units"] is None
    assert payload["total_units"] is None
    assert payload["speed_bps"] is None
    assert payload["eta_seconds"] is None
    assert payload["percent"] is None


def test_historical_success_projects_all_six_orchestration_stages_as_success() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with sessions() as session:
        run = AnalysisRun(
            analysis_id="WGS_HISTORICAL_SUCCESS",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            status="success",
            attempt=1,
            workdir="/data/wgs-results/runs/WGS_HISTORICAL_SUCCESS",
            current_stage="Workflow complete",
            params_json={"pipeline_release_id": "wgs-4.1.1-test"},
        )
        session.add(run)
        session.commit()

        payload = enrich_progress(session=session, run=run, payload={})

    assert payload["stage_code"] == "final"
    assert [item["stage_code"] for item in payload["orchestration_stages"]] == [
        "step1_upload",
        "step2_master",
        "step3_monitor",
        "step4_publish",
        "step5_download",
        "step6_materialize",
    ]
    assert {item["status"] for item in payload["orchestration_stages"]} == {"success"}


@pytest.mark.parametrize(
    ("run_status", "expected"),
    [
        ("created", "pending"),
        ("queued", "pending"),
        ("running", "running"),
        ("failed", "failed"),
        ("unknown_interrupted", "failed"),
        ("cancelled", "canceled"),
    ],
)
def test_progress_without_stage_evidence_uses_run_status(
    run_status: str, expected: str
) -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with sessions() as session:
        run = AnalysisRun(
            analysis_id=f"WGS_NO_STAGE_{run_status}",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            status=run_status,
            attempt=1,
            workdir=f"/data/wgs-results/runs/WGS_NO_STAGE_{run_status}",
            current_stage="step3_monitor",
            params_json={"pipeline_release_id": "wgs-4.1.1-test"},
        )
        session.add(run)
        session.commit()
        payload = enrich_progress(session=session, run=run, payload={})

    assert payload["stage_status"] == expected


def test_successful_run_reconciles_missing_cloud_finalize_terminal_event() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with sessions() as session:
        run = AnalysisRun(
            analysis_id="WGS_RECONCILED_SUCCESS",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            status="success",
            attempt=1,
            workdir="/data/wgs-results/runs/WGS_RECONCILED_SUCCESS",
            params_json={"pipeline_release_id": "wgs-4.1.1-test"},
        )
        row = RuleState(
            analysis_id=run.analysis_id,
            attempt=1,
                rule_instance_id="cloud-finalize",
                rule_name="cloud_finalize_delivery",
                status="running",
            )
        session.add_all([run, row])
        session.commit()

        item = serialize_rule_states(session=session, run=run, rows=[row])[0]

    assert item["status"] == "success"
    assert item["phase"] == "Cloud delivery"
    assert "verified successful run" in item["message"]


def test_rule_projection_contains_order_identity_and_registered_logs() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with sessions() as session:
        run = AnalysisRun(
            analysis_id="WGS_RULE_PROJECTION",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            status="running",
            attempt=1,
            workdir="/data/wgs-results/runs/WGS_RULE_PROJECTION",
            params_json={"pipeline_release_id": "wgs-4.1.1-test"},
        )
        row = RuleState(
            analysis_id=run.analysis_id,
            attempt=1,
            rule_instance_id="rule-1",
            sequence=42,
            phase="variant-calling",
            layer=8,
            rule_name="HaplotypeCaller",
            snakemake_jobid="321",
            sample_id="WGS001",
            family_id="F001",
            wildcards_json={"sample": "WGS001"},
            status="failed",
            message="worker exited 1",
            log_paths_json=["stderr:rule-1"],
        )
        session.add_all([run, row])
        session.commit()

        item = serialize_rule_states(session=session, run=run, rows=[row])[0]

    assert item["sequence"] == 42
    assert item["phase"] == "Variant analysis"
    assert item["snakemake_jobid"] == "321"
    assert item["sample_id"] == "WGS001"
    assert item["family_id"] == "F001"
    assert item["wildcards"] == {"sample": "WGS001"}
    assert item["message"] == "worker exited 1"
    assert item["log_keys"] == ["stderr:rule-1"]
