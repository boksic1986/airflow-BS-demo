"""Real reader + validator + budget, synthetic files and database only."""
from datetime import datetime, timedelta, timezone
import importlib
import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, PipelineStageExecution, RunAction, WgsStageExecution
from test_cce_recovery_evidence import evidence

NOW = datetime(2026, 9, 22, tzinfo=timezone.utc)


@pytest.fixture
def store(tmp_path, evidence):
    context, candidate, terminal = evidence
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    model = WgsStageExecution if context["pipeline"] == "wgs" else PipelineStageExecution
    extra = {} if model is WgsStageExecution else {"pipeline_name": "gatk"}
    root = tmp_path / "controlled"
    scope = root / "execution-one"
    scope.mkdir(parents=True)
    (scope / "executor-failure.json").write_text(json.dumps(candidate))
    (scope / "master-terminal.json").write_text(json.dumps(terminal))
    deadline = (NOW + timedelta(hours=1)).isoformat()
    release = "synthetic-release" if model is WgsStageExecution else "synthetic-profile@1"
    with factory.begin() as session:
        session.add(AnalysisRun(analysis_id=context["analysis_id"], pipeline_name=context["pipeline"],
            dag_id="bio_" + context["pipeline"], attempt=1, execution_mode="cce",
            status="failed", current_stage="step3_monitor", workdir="/synthetic/project",
            params_json=dict(pipeline_release_id=release, runtime_profile_id="synthetic-profile",
                runtime_profile_revision=1,
                cce_recovery_policy=dict(version=1, attempt=1, enabled=True, original_deadline=deadline),
                cce_recovery_budget=dict(attempt=1, count=0, original_deadline=deadline))))
        session.flush()
        session.add(model(**extra, analysis_id=context["analysis_id"], attempt=1,
            execution_id="execution-one", stage_code="step2_master", generation=1,
            status="success", request_hash="a" * 64, release_id=release,
            terminal_payload_json={"cce_master_binding": {"context": context,
                "evidence_scope": "execution-one", "workdir": "/synthetic/project"}}))
        session.add(model(**extra, analysis_id=context["analysis_id"], attempt=1,
            execution_id="monitor-one", stage_code="step3_monitor", generation=1,
            status="failed", request_hash="b" * 64, release_id=release,
            terminal_payload_json={"cce_master_submit_execution_id": "execution-one"}))
    yield factory, root, model
    engine.dispose()


def reserve(store):
    factory, root, _ = store
    module = importlib.import_module("app.cce_recovery_service")
    with factory.begin() as session:
        return module.reserve_monitored_recovery(session=session,
            analysis_id="SYNTHETIC_RECOVERY", attempt=1,
            monitor_execution_id="monitor-one", evidence_root=root, now=NOW)


def test_distinct_master_submit_and_monitor_bind_one_durable_action(store):
    first = reserve(store)
    assert reserve(store) == first
    assert first["source_execution_id"] == "execution-one"
    assert first["ordinal"] == 1
    factory, _, _ = store
    with factory() as session:
        actions = session.scalars(select(RunAction)).all()
        assert len(actions) == 1
        binding = actions[0].payload_json["evidence_binding"]
        assert binding["monitor_execution_id"] == "monitor-one"
        assert binding["monitor_request_hash"] == "b" * 64
        assert binding["submit_request_hash"] == "a" * 64
        assert binding["category"] == "worker_create_admission_timeout"
        assert binding["evidence_key"] == "execution-one/master-terminal.json"
        run = session.scalar(select(AnalysisRun))
        assert (run.status, run.attempt) == ("failed", 1)


@pytest.mark.parametrize("change", ["new_monitor", "new_master", "missing_binding", "changed_hash",
    "changed_release", "changed_workdir", "foreign_master", "not_failed", "user_stop"])
def test_stale_changed_or_unbound_execution_spends_no_budget(store, change):
    factory, _, model = store
    with factory.begin() as session:
        master = session.scalar(select(model).where(model.execution_id == "execution-one"))
        monitor = session.scalar(select(model).where(model.execution_id == "monitor-one"))
        run = session.scalar(select(AnalysisRun))
        if change in {"new_monitor", "new_master"}:
            source = monitor if change == "new_monitor" else master
            extra = {} if model is WgsStageExecution else {"pipeline_name": "gatk"}
            session.add(model(**extra, analysis_id=run.analysis_id, attempt=1,
                execution_id="replacement", stage_code=source.stage_code, generation=2,
                status="accepted", request_hash="c" * 64, release_id=source.release_id))
        elif change == "missing_binding":
            master.terminal_payload_json = {}
        elif change == "changed_hash":
            master.request_hash = "c" * 64
        elif change == "changed_release":
            master.release_id = "other-release"
        elif change == "changed_workdir":
            run.workdir = "/synthetic/other"
        elif change == "foreign_master":
            monitor.terminal_payload_json = {"cce_master_submit_execution_id": "foreign"}
        elif change == "not_failed":
            monitor.status = "running"
        else:
            run.status = "cancel_requested"
    with pytest.raises(ValueError):
        reserve(store)
    with factory() as session:
        assert session.scalar(select(RunAction)) is None
        assert session.scalar(select(AnalysisRun)).params_json["cce_recovery_budget"]["count"] == 0


def test_invalid_terminal_never_reserves_and_replay_cannot_replace_evidence(store):
    factory, root, _ = store
    path = root / "execution-one" / "master-terminal.json"
    terminal = json.loads(path.read_text())
    path.write_text(json.dumps(dict(terminal, rule_failure_count=1)))
    with pytest.raises(ValueError):
        reserve(store)
    path.write_text(json.dumps(terminal))
    first = reserve(store)
    path.write_text(json.dumps(dict(terminal, observation_note="changed after acceptance")))
    with pytest.raises(ValueError, match="binding"):
        reserve(store)
    with factory() as session:
        action = session.scalar(select(RunAction))
        assert action.payload_json == first
        assert session.scalar(select(AnalysisRun)).params_json["cce_recovery_budget"]["count"] == 1
