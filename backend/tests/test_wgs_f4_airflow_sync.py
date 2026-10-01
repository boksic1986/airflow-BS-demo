"""Synthetic WGS Airflow projection boundaries for guarded Step6 finalization."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import diagnostics_service
from app.models import AnalysisRun, Base


@pytest.mark.parametrize(
    ("execution_mode", "validation_scope", "current_stage"),
    [
        ("cce", "step1_only", "finalize_step1_canary"),
        ("cce", "step3_dryrun", "finalize_step3_dryrun"),
        ("cce", "node97_full", "finalize_local_run"),
        ("local", None, "finalize_local_run"),
    ],
)
def test_wgs_airflow_sync_keeps_canary_and_local_success_projection(
    tmp_path, monkeypatch, execution_mode, validation_scope, current_stage
):
    engine = create_engine(
        "sqlite+pysqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    analysis_id = "WGS_SYNTHETIC_F4_CANARY"
    params = {"orchestration_contract_version": 2}
    if validation_scope is not None:
        params["validation_scope"] = validation_scope
    with factory.begin() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                dag_run_id="synthetic-dag-run",
                execution_mode=execution_mode,
                workdir=str(tmp_path),
                status="success",
                current_stage=current_stage,
                params_json=params,
            )
        )

    monkeypatch.setattr(diagnostics_service, "_safe_workdir", lambda *_args: tmp_path)
    monkeypatch.setattr(
        diagnostics_service, "_safe_child_path", lambda root, child, _settings: root / child
    )
    monkeypatch.setattr(
        diagnostics_service, "import_snakemake_events_jsonl", lambda **_kwargs: None
    )
    airflow = SimpleNamespace(
        get_dag_run=lambda *_args: {
            "state": "success",
            "end_date": datetime.now(timezone.utc).isoformat(),
        },
        list_task_instances=lambda *_args: {"task_instances": []},
    )
    with factory() as session:
        payload = diagnostics_service.sync_wgs_airflow_status(
            session=session,
            airflow_client=airflow,
            analysis_id=analysis_id,
            settings=SimpleNamespace(),
        )
        run = session.scalar(select(AnalysisRun))
        assert payload["status"] == run.status == "success"
        assert run.current_stage == "Workflow complete"
        assert run.ended_at is not None
    engine.dispose()
