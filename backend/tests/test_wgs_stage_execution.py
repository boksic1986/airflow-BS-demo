from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, WgsStageExecution
from app.wgs_observer import upsert_stage_state
from app.wgs_stage_catalog import StageContractError, load_wgs_stage_contract
from app.wgs_stage_execution_service import register_stage_execution, transition_stage_execution
from app.wgs_workspace_service import _heavy_slot_waiting_count


def sessions():
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def add_run(factory):
    with factory.begin() as session:
        session.add(AnalysisRun(analysis_id="WGS_20260904_120000_A1B2C3", pipeline_name="wgs", dag_id="bio_wgs", workdir="/runs/test", status="running", attempt=1, params_json={"pipeline_release_id": "wgs-4.1.1-6c98281", "orchestration_contract_version": 2}))


def contract_path() -> Path:
    return Path(__file__).parents[2] / "config" / "wgs_stage_contract.yaml"


def test_heavy_slot_waiting_count_uses_only_fresh_waiting_snapshots(tmp_path) -> None:
    current = tmp_path / "WGS_20260904_120000_A1B2C3" / "attempt-1"
    current.mkdir(parents=True)
    (current / "heavy-slot-status.json").write_text(
        json.dumps(
            {
                "schema_version": "wgs-heavy-slot-status.v1",
                "state": "waiting",
                "limit": 25,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    stale = tmp_path / "WGS_20260903_120000_D4E5F6" / "attempt-1"
    stale.mkdir(parents=True)
    (stale / "heavy-slot-status.json").write_text(
        json.dumps(
            {
                "schema_version": "wgs-heavy-slot-status.v1",
                "state": "waiting",
                "limit": 25,
                "updated_at": (
                    datetime.now(timezone.utc) - timedelta(minutes=3)
                ).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    assert _heavy_slot_waiting_count(str(tmp_path)) == 1


def test_stage_contract_loads_heavy_slot_and_fails_closed(tmp_path) -> None:
    contract = load_wgs_stage_contract(contract_path())
    assert contract.version == 2
    assert contract.heavy_io.limit == 25
    assert contract.heavy_io.mode == "enforce"
    assert contract.stages["step5_download"].predecessor == "step4_publish"
    assert contract.stages["step1_upload"].predecessors_by_submission_mode == {
        "three_stage": "prepare_analysis",
        "default": "prepare",
    }
    with pytest.raises(StageContractError, match="does not exist"):
        load_wgs_stage_contract(tmp_path / "missing.yaml")


def test_stage_execution_is_idempotent_and_requires_exact_successful_predecessor() -> None:
    factory = sessions()
    add_run(factory)
    contract = load_wgs_stage_contract(contract_path())
    now = datetime(2026, 9, 4, 4, 0, tzinfo=timezone.utc)
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        prepare = register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare_sampleinfo", request_payload={"batch": "A"}, now=now)
        duplicate = register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare_sampleinfo", request_payload={"batch": "A"}, now=now)
        assert duplicate.execution_id == prepare.execution_id
        with pytest.raises(ValueError, match="predecessor"):
            register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare_analysis", request_payload={"batch": "A"}, now=now)
        transition_stage_execution(session=session, execution_id=prepare.execution_id, generation=1, status="running", observed_at=now + timedelta(seconds=1))
        transition_stage_execution(session=session, execution_id=prepare.execution_id, generation=1, status="success", observed_at=now + timedelta(seconds=2), receipt_hash="a" * 64, evidence_type="terminal_marker", evidence_key="prepare.status.json")
        analysis = register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare_analysis", request_payload={"batch": "A"}, now=now + timedelta(seconds=3))
        assert analysis.predecessor_execution_id == prepare.execution_id
        assert analysis.predecessor_generation == 1
        assert analysis.predecessor_receipt_hash == "a" * 64


def test_old_generation_event_cannot_override_new_projection() -> None:
    factory = sessions()
    add_run(factory)
    contract = load_wgs_stage_contract(contract_path())
    now = datetime(2026, 9, 4, 4, 0, tzinfo=timezone.utc)
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        first = register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare_sampleinfo", request_payload={"batch": "A"}, now=now)
        transition_stage_execution(session=session, execution_id=first.execution_id, generation=1, status="failed", observed_at=now + timedelta(seconds=1), receipt_hash="b" * 64)
        second = register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare_sampleinfo", request_payload={"batch": "A", "retry": 1}, now=now + timedelta(seconds=2), force_new_generation=True)
        assert second.generation == 2
        assert transition_stage_execution(session=session, execution_id=first.execution_id, generation=1, status="success", observed_at=now + timedelta(seconds=3), receipt_hash="c" * 64) is False
        assert session.scalar(select(WgsStageExecution).where(WgsStageExecution.execution_id == second.execution_id)).status == "accepted"


def test_failed_terminal_marker_closes_append_only_execution_without_success_receipt() -> None:
    factory = sessions()
    add_run(factory)
    contract = load_wgs_stage_contract(contract_path())
    now = datetime(2026, 9, 4, 4, 0, tzinfo=timezone.utc)
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        execution = register_stage_execution(
            session=session,
            run=run,
            contract=contract,
            stage_code="prepare_sampleinfo",
            request_payload={"batch": "A"},
            now=now,
        )
        upsert_stage_state(
            session,
            analysis_id=run.analysis_id,
            attempt=run.attempt,
            stage_code="prepare_sampleinfo",
            stage_status="failed",
            updated_at=now + timedelta(seconds=3),
            message="runner exited 1",
            evidence_key="prepare.status.json",
        )
        session.flush()
        session.refresh(execution)
        assert execution.status == "failed"
        assert execution.ended_at.replace(tzinfo=timezone.utc) == now + timedelta(seconds=3)
        assert execution.receipt_hash is None


def test_step1_predecessor_uses_prepare_for_auto_dispatch() -> None:
    factory = sessions()
    add_run(factory)
    contract = load_wgs_stage_contract(contract_path())
    now = datetime(2026, 9, 4, 4, 0, tzinfo=timezone.utc)
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.params_json = {**run.params_json, "submission_mode": "auto_dispatch"}
        prepare = register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare", request_payload={"batch": "A"}, now=now)
        transition_stage_execution(session=session, execution_id=prepare.execution_id, generation=1, status="success", observed_at=now + timedelta(seconds=1), receipt_hash="d" * 64)
        step1 = register_stage_execution(session=session, run=run, contract=contract, stage_code="step1_upload", request_payload={"batch": "A"}, now=now + timedelta(seconds=2))
        assert step1.predecessor_execution_id == prepare.execution_id
