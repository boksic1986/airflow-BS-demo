from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, KubernetesWorkload
from app.wgs_timing_service import enrich_progress


def test_analysis_eta_selects_last_twenty_runs_from_same_release() -> None:
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

    assert payload["analysis_eta_history_count"] == 3
    assert payload["analysis_eta_model"] == "release_stage_wall_median_v1"
    assert payload["analysis_eta_seconds"] is not None


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
