"""Late receipts must not reuse a cached pre-recovery run or execution."""
from contextlib import contextmanager
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from app.gatk_runtime_service import sync_gatk_stage_status
from app.models import AnalysisRun, Base, PipelineStageExecution, RunStageState, WgsStageExecution
from app.wgs_observer import _ingest_runtime_stage_status


@pytest.fixture(params=["wgs", "gatk"])
def receipt_case(request, tmp_path):
    pipeline = request.param
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    model = WgsStageExecution if pipeline == "wgs" else PipelineStageExecution
    identity = dict(analysis_id="synthetic-receipt", attempt=1,
                    stage_code="step4_publish", execution_id="execution-one",
                    generation=1, request_hash="a" * 64, release_id="synthetic-release")
    if pipeline == "gatk":
        identity["pipeline_name"] = pipeline
    session = sessions()
    run = AnalysisRun(analysis_id="synthetic-receipt", pipeline_name=pipeline,
                      dag_id="bio_" + pipeline, attempt=1, status="running",
                      current_stage="step4_publish", execution_mode="cce",
                      workdir="/synthetic/workdir",
                      params_json={"orchestration_contract_version": 2})
    execution = model(**identity, status="running")
    session.add_all([run, execution])
    session.commit()
    root = tmp_path / "requests"
    path = root / run.analysis_id / "attempt-1" / "step4_publish.request.status.json"
    path.parent.mkdir(parents=True)
    payload = dict(schema_version="wgs-runtime.stage-status.v1",
                   orchestration_contract_version=2, analysis_id=run.analysis_id,
                   attempt=1, stage="step4_publish", execution_id="execution-one",
                   generation=1, request_hash="a" * 64, status="failed",
                   message="late source failure", updated_at="2026-09-23T01:00:00Z")
    path.write_text(json.dumps(payload), encoding="utf-8")

    @contextmanager
    def observer_session():
        yield session

    def ingest():
        if pipeline == "wgs":
            return _ingest_runtime_stage_status(observer_session, root, path)
        return sync_gatk_stage_status(session=session,
            settings=SimpleNamespace(gatk_runtime_request_root=str(root)),
            analysis_id=run.analysis_id, attempt=1, stage="step4_publish")

    yield session, run, execution, model, ingest
    session.close()
    engine.dispose()


def test_cached_active_attempt_cannot_project_after_attempt_changes(receipt_case):
    session, run, execution, _, ingest = receipt_case
    # Durable state has advanced; objects held by this caller still say attempt 1.
    session.execute(update(AnalysisRun).values(attempt=2, status="queued",
        current_stage="step3_monitor").execution_options(synchronize_session=False))
    session.commit()
    assert run.attempt == 1
    with pytest.raises(ValueError, match="active.*attempt"):
        ingest()
    session.expire_all()
    assert (run.attempt, run.status, run.current_stage) == (2, "queued", "step3_monitor")
    assert execution.status == "running"
    assert session.scalar(select(RunStageState)) is None


def test_cached_running_execution_cannot_replace_durable_success(receipt_case):
    session, _, execution, model, ingest = receipt_case
    session.execute(update(model).values(status="success", receipt_hash="b" * 64)
                    .execution_options(synchronize_session=False))
    session.commit()
    assert execution.status == "running"
    ingest()
    session.expire_all()
    assert execution.status == "success"
    assert execution.receipt_hash == "b" * 64
    assert session.scalar(select(RunStageState)) is None


def test_old_generation_cannot_replace_recovery_projection(receipt_case):
    session, run, execution, model, ingest = receipt_case
    execution.status = "failed"
    fields = dict(analysis_id=run.analysis_id, attempt=1, stage_code="step4_publish",
                  execution_id="execution-two", generation=2, request_hash="c" * 64,
                  release_id="synthetic-release", status="running")
    if run.pipeline_name == "gatk":
        fields["pipeline_name"] = "gatk"
    replacement = model(**fields)
    session.add(replacement)
    session.commit()
    ingest()
    session.expire_all()
    assert run.status == "running"
    assert replacement.status == "running"
    assert session.scalar(select(RunStageState)) is None


def test_current_failure_still_updates_execution_and_projection(receipt_case):
    session, run, execution, _, ingest = receipt_case
    ingest()
    session.expire_all()
    assert execution.status == "failed"
    assert run.status == "failed"
    assert session.scalar(select(RunStageState)).stage_status == "failed"
