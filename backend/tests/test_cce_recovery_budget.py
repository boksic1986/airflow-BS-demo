"""Attempt-scoped reservations: no dispatch, remote calls or real analysis.

The caller must validate runtime terminal evidence before reserving. These tests
exercise persistence and fences separately from the producer's evidence schema.
"""
from datetime import datetime, timedelta, timezone
import importlib

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, RunAction, WgsMaintenanceAction


NOW = datetime(2026, 9, 22, tzinfo=timezone.utc)


@pytest.fixture(params=["wgs", "gatk"])
def run_store(request):
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        session.add(AnalysisRun(
            analysis_id="SYNTHETIC_RECOVERY", pipeline_name=request.param,
            dag_id=f"bio_{request.param}", workdir="/synthetic/project", attempt=1,
            execution_mode="cce", status="failed", current_stage="step3_monitor",
            params_json={"cce_recovery_policy": {
                "version": 1, "attempt": 1, "enabled": True,
                "original_deadline": (NOW + timedelta(hours=1)).isoformat(),
            }, "cce_recovery_budget": {"attempt": 1, "count": 0,
                "original_deadline": (NOW + timedelta(hours=1)).isoformat()}},
        ))
    yield factory
    engine.dispose()


def reserve(factory, source="master-one", now=NOW):
    module = importlib.import_module("app.cce_recovery_budget")
    with factory.begin() as session:
        return module.reserve_compute_recovery(
            session=session, analysis_id="SYNTHETIC_RECOVERY", attempt=1,
            source_execution_id=f"execution-{source}", source_master_uid=source,
            now=now,
        )


def complete(factory, action_id):
    with factory.begin() as session:
        action = session.scalar(select(RunAction).where(
            RunAction.analysis_id == "SYNTHETIC_RECOVERY",
            RunAction.payload_json.is_not(None),
        ).order_by(RunAction.id.desc()))
        assert action.payload_json["action_id"] == action_id
        action.result_status = "success"


def test_replay_and_new_sessions_preserve_one_reservation(run_store):
    first = reserve(run_store)
    replay = reserve(run_store, now=NOW + timedelta(seconds=20))
    assert replay == first
    assert first["ordinal"] == 1
    assert first["next_retry_at"] == (NOW + timedelta(seconds=60)).isoformat()
    with run_store() as session:
        assert len(session.scalars(select(RunAction)).all()) == 1
        assert session.scalar(select(AnalysisRun)).attempt == 1


def test_two_different_master_failures_share_attempt_budget(run_store):
    first = reserve(run_store)
    complete(run_store, first["action_id"])
    second = reserve(run_store, "master-two", NOW + timedelta(minutes=3))
    assert second["ordinal"] == 2
    assert second["next_retry_at"] == (NOW + timedelta(minutes=6)).isoformat()
    assert second["original_deadline"] == first["original_deadline"]
    complete(run_store, second["action_id"])
    with pytest.raises(ValueError, match="exhausted"):
        reserve(run_store, "master-three", NOW + timedelta(minutes=7))
    # An old callback must resolve its old action, not spend another recovery.
    assert reserve(run_store) == first


@pytest.mark.parametrize("status", ["cancel_requested", "cancelled", "canceled", "terminated", "success", "paused", "pause_requested", "delete_requested"])
def test_user_stop_or_success_prevents_even_reserved_action_replay(run_store, status):
    reserve(run_store)
    with run_store.begin() as session:
        session.scalar(select(AnalysisRun)).status = status
    with pytest.raises(ValueError, match="stopped|terminal"):
        reserve(run_store)


@pytest.mark.parametrize("policy", [None, {}, {"version": 1, "attempt": 1, "enabled": False},
                                   {"version": 1, "attempt": 2, "enabled": True}])
def test_historical_or_disabled_policy_never_grants_a_budget(run_store, policy):
    with run_store.begin() as session:
        session.scalar(select(AnalysisRun)).params_json = {"cce_recovery_policy": policy}
    with pytest.raises(ValueError, match="policy"):
        reserve(run_store)
    with run_store() as session:
        assert session.scalar(select(RunAction)) is None


def test_deadline_cannot_be_extended_by_reservation(run_store):
    with pytest.raises(ValueError, match="deadline"):
        reserve(run_store, now=NOW + timedelta(hours=1))
    with run_store() as session:
        assert session.scalar(select(RunAction)) is None


def test_another_unfinished_recovery_blocks_new_master_reservation(run_store):
    reserve(run_store)
    with pytest.raises(ValueError, match="active"):
        reserve(run_store, "master-two")


@pytest.mark.parametrize("state", [None, {}, {"attempt": 1, "count": 1},
                                   {"attempt": 2, "count": 0}])
def test_missing_or_inconsistent_journal_never_resets_budget(run_store, state):
    with run_store.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.params_json = dict(run.params_json, cce_recovery_budget=state)
    with pytest.raises(ValueError, match="budget"):
        reserve(run_store)


def test_edited_policy_deadline_does_not_extend_original_budget(run_store):
    first = reserve(run_store)
    complete(run_store, first["action_id"])
    with run_store.begin() as session:
        run = session.scalar(select(AnalysisRun))
        policy = dict(run.params_json["cce_recovery_policy"],
                      original_deadline=(NOW + timedelta(days=1)).isoformat())
        run.params_json = dict(run.params_json, cce_recovery_policy=policy)
    with pytest.raises(ValueError, match="deadline"):
        reserve(run_store, "master-two")


def test_reservation_rolls_back_with_callers_transaction(run_store):
    module = importlib.import_module("app.cce_recovery_budget")
    with run_store() as session:
        module.reserve_compute_recovery(session=session, analysis_id="SYNTHETIC_RECOVERY",
            attempt=1, source_execution_id="execution-master-one",
            source_master_uid="master-one", now=NOW)
        session.rollback()
    assert reserve(run_store)["ordinal"] == 1


@pytest.mark.parametrize("kind", ["resume_stage", "cancel_submission", "maintenance"])
def test_existing_control_actions_fence_new_reservations(run_store, kind):
    with run_store.begin() as session:
        if kind == "maintenance":
            session.add(WgsMaintenanceAction(analysis_id="SYNTHETIC_RECOVERY", attempt=1,
                action_id="synthetic-maintenance", action_type="step7_cleanup",
                status="requested", requested_by="synthetic"))
        else:
            session.add(RunAction(analysis_id="SYNTHETIC_RECOVERY", action=kind,
                result_status="reserved", payload_json={"attempt": 1}))
    with pytest.raises(ValueError, match="active|stopped"):
        reserve(run_store)


def test_identity_or_target_changes_are_not_new_budget(run_store):
    with run_store.begin() as session:
        session.scalar(select(AnalysisRun)).attempt = 2
    with pytest.raises(ValueError, match="attempt"):
        reserve(run_store)
    with run_store.begin() as session:
        run = session.scalar(select(AnalysisRun))
        run.attempt = 1
        run.execution_mode = "local"
    with pytest.raises(ValueError, match="CCE"):
        reserve(run_store)


def test_not_enough_time_to_wait_does_not_spend_budget(run_store):
    with pytest.raises(ValueError, match="deadline"):
        reserve(run_store, now=NOW + timedelta(minutes=59, seconds=30))
    with run_store() as session:
        assert session.scalar(select(RunAction)) is None
