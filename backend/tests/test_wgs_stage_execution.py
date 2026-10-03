from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, RunStageState, WgsStageExecution
from app.stage_execution_contract import freeze_stage_execution_protocol
from app.wgs_observer import upsert_stage_state
from app.wgs_stage_catalog import StageContractError, load_wgs_stage_contract
from app.wgs_stage_execution_service import (
    WgsStagePredecessorPending,
    register_stage_execution,
    transition_stage_execution,
)
from app.wgs_workspace_service import _heavy_slot_waiting_count, build_wgs_workspace


def sessions():
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def add_run(factory):
    with factory.begin() as session:
        session.add(AnalysisRun(analysis_id="WGS_20260904_120000_A1B2C3", pipeline_name="wgs", dag_id="bio_wgs", workdir="/runs/test", status="running", attempt=1, params_json={"pipeline_release_id": "wgs-4.1.1-6c98281", "orchestration_contract_version": 2}))


def contract_path() -> Path:
    return Path(__file__).parents[2] / "config" / "wgs_stage_contract.yaml"


@pytest.mark.parametrize("stage, marked", [
    ("step1_upload", True),
    ("step2_master", True),
    ("step3_monitor", True),
    ("step4_publish", True),
    ("step5_download", True),
    ("step6_materialize", True),
    ("step7_cleanup", False),
    ("prepare_analysis", False),
])
def test_protocol_scope_freezer_marks_only_step1_to_step6(stage, marked) -> None:
    request = {"stage": stage, "batch": "synthetic"}
    expected = dict(request)
    if marked:
        expected["stage_execution"] = {"protocol": "cce.stage-execution.v1"}

    freeze_stage_execution_protocol(request)

    assert request == expected


@pytest.mark.parametrize("marker", [
    None,
    {"protocol": "cce.stage-execution.v0"},
    {"protocol": "cce.stage-execution.v1"},
])
def test_protocol_scope_freezer_rejects_explicit_step7_marker(marker) -> None:
    request = {"stage": "step7_cleanup", "stage_execution": marker}
    original = json.dumps(request, sort_keys=True)

    with pytest.raises(ValueError, match="stage execution"):
        freeze_stage_execution_protocol(request)

    assert json.dumps(request, sort_keys=True) == original


@pytest.mark.parametrize("stage, predecessor, marked", [
    ("step1_upload", "prepare", True),
    ("step2_master", "step1_upload", True),
    ("step3_monitor", "step2_master", True),
    ("step4_publish", "step3_monitor", True),
    ("step5_download", "step4_publish", True),
    ("step6_materialize", "step5_download", True),
    ("step7_cleanup", None, False),
])
def test_protocol_scope_wgs_registration_freezes_only_native_stages(
    stage, predecessor, marked,
) -> None:
    factory = sessions()
    add_run(factory)
    contract = load_wgs_stage_contract(contract_path())
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        if predecessor:
            session.add(WgsStageExecution(
                execution_id="wse_synthetic_predecessor",
                analysis_id=run.analysis_id, attempt=1, stage_code=predecessor,
                generation=1, status="success", request_hash="a" * 64,
                receipt_hash="b" * 64, release_id="wgs-4.1.1-6c98281",
            ))
            session.flush()
        request = {"stage": stage, "batch": "synthetic"}
        if stage == "step7_cleanup":
            request.update(
                maintenance_action_id="step7-sfs-synthetic",
                cce_pipeline_version="0.8.8",
                step7_target_snapshot={"cce_bundle": "/approved/synthetic/frozen-cce"},
            )
        expected = dict(request)
        if marked:
            expected["stage_execution"] = {"protocol": "cce.stage-execution.v1"}

        execution = register_stage_execution(
            session=session, run=run, contract=contract,
            stage_code=stage, request_payload=request,
        )

        assert request == expected
        assert execution.request_hash == hashlib.sha256(
            json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        assert execution.generation == 1


@pytest.mark.parametrize("stage", ["step1_upload", "step7_cleanup"])
def test_protocol_scope_wgs_reuses_unmarked_request_without_changing_hash(stage) -> None:
    factory = sessions()
    add_run(factory)
    contract = load_wgs_stage_contract(contract_path())
    request = {"stage": stage, "batch": "synthetic"}
    original = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    original_hash = hashlib.sha256(original).hexdigest()
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        old = WgsStageExecution(
            execution_id="wse_synthetic_legacy", analysis_id=run.analysis_id,
            attempt=1, stage_code=stage, generation=1, status="accepted",
            request_hash=original_hash, release_id="wgs-4.1.1-6c98281",
        )
        session.add(old)
        session.flush()

        execution = register_stage_execution(
            session=session, run=run, contract=contract,
            stage_code=stage, request_payload=request,
        )

        assert execution.execution_id == old.execution_id
        assert execution.request_hash == original_hash
        assert execution.generation == 1
        assert json.dumps(request, sort_keys=True, separators=(",", ":")).encode() == original
        assert session.scalars(select(WgsStageExecution)).all() == [old]


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


def test_workspace_prefers_fresh_active_stage_projection_over_stale_run_stage() -> None:
    factory = sessions()
    now = datetime(2026, 9, 7, 6, 49, tzinfo=timezone.utc)
    with factory.begin() as session:
        run = AnalysisRun(
            analysis_id="WGS_20260907_044653_9C8591",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            workdir="/runs/test",
            status="running",
            current_stage="release_leases",
            attempt=2,
            params_json={"orchestration_contract_version": 2},
        )
        session.add(run)
        session.add(
            RunStageState(
                analysis_id=run.analysis_id,
                attempt=2,
                stage_code="step2_master",
                step_number=2,
                stage_label="Starting WGS workflow",
                stage_status="accepted",
                progress_source="wgs-runtime.request.v4",
                updated_at=now,
            )
        )

    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        workspace = build_wgs_workspace(
            session=session,
            run=run,
            run_payload={"analysis_id": run.analysis_id},
        )

    assert workspace["progress"]["stage_code"] == "step2_master"
    assert workspace["progress"]["stage_status"] == "accepted"


@pytest.mark.parametrize(
    ("run_status", "stage_code"),
    (("publishing", "step4_publish"), ("downloading", "step5_download")),
)
def test_workspace_prefers_fresh_named_active_stage_projection(
    run_status: str, stage_code: str
) -> None:
    factory = sessions()
    now = datetime(2026, 9, 7, 7, 10, tzinfo=timezone.utc)
    with factory.begin() as session:
        run = AnalysisRun(
            analysis_id=f"WGS_20260907_{run_status.upper()}",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            workdir="/runs/test",
            status=run_status,
            current_stage="release_leases",
            attempt=1,
            params_json={"orchestration_contract_version": 2},
        )
        session.add(run)
        session.add(
            RunStageState(
                analysis_id=run.analysis_id,
                attempt=1,
                stage_code=stage_code,
                step_number=4 if stage_code == "step4_publish" else 5,
                stage_label=(
                    "Publishing WGS results"
                    if stage_code == "step4_publish"
                    else "Downloading WGS results"
                ),
                stage_status="running",
                progress_source="wgs-runtime.stage-status.v1",
                updated_at=now,
            )
        )

    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        workspace = build_wgs_workspace(
            session=session,
            run=run,
            run_payload={"analysis_id": run.analysis_id},
        )

    assert workspace["progress"]["stage_code"] == stage_code
    assert workspace["progress"]["stage_status"] == "running"


def test_stage_contract_loads_heavy_slot_and_fails_closed(tmp_path) -> None:
    contract = load_wgs_stage_contract(contract_path())
    assert contract.version == 2
    assert contract.heavy_io.limit == 25
    assert contract.heavy_io.mode == "enforce"
    assert contract.stages["step5_download"].predecessor == "step4_publish"
    assert contract.stages["step1_upload"].predecessors_by_submission_mode == {
        "three_stage": "prepare_analysis",
        "auto_dispatch": "prepare_analysis",
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
        with pytest.raises(WgsStagePredecessorPending, match="predecessor"):
            register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare_analysis", request_payload={"batch": "A"}, now=now)
        transition_stage_execution(session=session, execution_id=prepare.execution_id, generation=1, status="running", observed_at=now + timedelta(seconds=1))
        transition_stage_execution(session=session, execution_id=prepare.execution_id, generation=1, status="success", observed_at=now + timedelta(seconds=2), receipt_hash="a" * 64, evidence_type="terminal_marker", evidence_key="prepare.status.json")
        analysis = register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare_analysis", request_payload={"batch": "A"}, now=now + timedelta(seconds=3))
        assert analysis.predecessor_execution_id == prepare.execution_id
        assert analysis.predecessor_generation == 1
        assert analysis.predecessor_receipt_hash == "a" * 64


def test_force_retry_reuses_an_active_identical_stage_generation() -> None:
    factory = sessions()
    add_run(factory)
    contract = load_wgs_stage_contract(contract_path())
    now = datetime(2026, 9, 4, 4, 0, tzinfo=timezone.utc)
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        first = register_stage_execution(
            session=session,
            run=run,
            contract=contract,
            stage_code="prepare_sampleinfo",
            request_payload={"batch": "A"},
            now=now,
        )
        retried = register_stage_execution(
            session=session,
            run=run,
            contract=contract,
            stage_code="prepare_sampleinfo",
            request_payload={"batch": "A"},
            now=now + timedelta(seconds=1),
            force_new_generation=True,
        )

        assert retried.execution_id == first.execution_id
        assert retried.generation == 1


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


def test_step1_predecessor_uses_prepare_analysis_for_auto_dispatch() -> None:
    factory = sessions()
    add_run(factory)
    contract = load_wgs_stage_contract(contract_path())
    now = datetime(2026, 9, 4, 4, 0, tzinfo=timezone.utc)
    with factory.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.params_json = {**run.params_json, "submission_mode": "auto_dispatch"}
        sampleinfo = register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare_sampleinfo", request_payload={"batch": "A"}, now=now)
        transition_stage_execution(session=session, execution_id=sampleinfo.execution_id, generation=1, status="success", observed_at=now + timedelta(seconds=1), receipt_hash="c" * 64)
        analysis = register_stage_execution(session=session, run=run, contract=contract, stage_code="prepare_analysis", request_payload={"batch": "A"}, now=now + timedelta(seconds=2))
        transition_stage_execution(session=session, execution_id=analysis.execution_id, generation=1, status="success", observed_at=now + timedelta(seconds=3), receipt_hash="d" * 64)
        step1 = register_stage_execution(session=session, run=run, contract=contract, stage_code="step1_upload", request_payload={"batch": "A"}, now=now + timedelta(seconds=4))
        assert step1.predecessor_execution_id == analysis.execution_id
