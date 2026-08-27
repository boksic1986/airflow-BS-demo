from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base
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
    release_id = "wgs-4.1.1-1778fca"

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
