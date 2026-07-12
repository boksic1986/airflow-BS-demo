import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, RunAction
from app.operator_maintenance_service import (
    OperatorCorrectionSafetyError,
    build_operator_correction_plan,
    execute_operator_correction_plan,
)


def test_operator_correction_is_exact_and_audited() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        session.add_all(
            [
                AnalysisRun(analysis_id="PGTA_1", pipeline_name="pgta", dag_id="bio_pgta", status="success", workdir="/tmp/1", submitted_by="codex-validation"),
                AnalysisRun(analysis_id="PGTA_2", pipeline_name="pgta", dag_id="bio_pgta", status="success", workdir="/tmp/2", submitted_by="codex-validation"),
                AnalysisRun(analysis_id="NIPT_1", pipeline_name="nipt_docker", dag_id="bio_nipt_docker", status="success", workdir="/tmp/3", submitted_by="codex-t113"),
            ]
        )
        session.commit()
        plan = build_operator_correction_plan(
            session=session,
            expected={"PGTA_1": "codex-validation", "PGTA_2": "codex-validation"},
            new_operator="jiucheng",
            reason="Replace validation agent label with platform operator",
        )
        result = execute_operator_correction_plan(session=session, plan=plan)

        assert result == {"updated": 2, "new_operator": "jiucheng"}
        assert session.get(AnalysisRun, 1).submitted_by == "jiucheng"
        assert session.get(AnalysisRun, 2).submitted_by == "jiucheng"
        assert session.get(AnalysisRun, 3).submitted_by == "codex-t113"
        actions = session.scalars(select(RunAction).order_by(RunAction.analysis_id)).all()
        assert [item.action for item in actions] == ["metadata_correction", "metadata_correction"]
        assert actions[0].payload_json["old_operator"] == "codex-validation"
        assert actions[0].payload_json["new_operator"] == "jiucheng"


def test_operator_correction_rejects_active_or_changed_runs() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        session.add(AnalysisRun(analysis_id="PGTA_ACTIVE", pipeline_name="pgta", dag_id="bio_pgta", status="running", workdir="/tmp/active", submitted_by="codex-validation"))
        session.commit()
        with pytest.raises(OperatorCorrectionSafetyError, match="terminal successful"):
            build_operator_correction_plan(
                session=session,
                expected={"PGTA_ACTIVE": "codex-validation"},
                new_operator="jiucheng",
                reason="correction",
            )
