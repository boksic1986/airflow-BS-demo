"""Preparation must freeze the same target later used for analysis."""
import pytest
from sqlalchemy import select

from app.models import RunAction
from app.wgs_execution_dispatch_service import (
    ExecutionDispatchConflict,
    change_execution_choice,
    ensure_execution_dispatch,
    project_execution_dispatch,
    reset_execution_dispatch_for_attempt,
)
from app.wgs_submission_service import approve_wgs_config
from test_wgs_execution_dispatch import _run, _sessions, _settings


@pytest.mark.parametrize("mode,target", [
    ("cce", "cce"), ("local", "node-97"), ("sge", "sge-default"),
])
def test_config_approval_freezes_current_choice_and_blocks_late_switch(mode, target):
    with _sessions()() as session:
        run = _run(session)
        run.params_json = {
            **run.params_json, "native_prepare_contract": 1,
            "submission_mode": "three_stage", "submission_phase": "config_review",
        }
        dispatch = ensure_execution_dispatch(session=session, run=run)
        # A target change that wins the row lock is included in the freeze.
        dispatch.desired_mode, dispatch.desired_target = mode, target
        dispatch.dispatch_revision = 3
        run.execution_mode = mode
        session.commit()

        approved = approve_wgs_config(
            session=session, analysis_id=run.analysis_id, requested_by="operator",
            use_reference="all", resource_set="default",
        )
        frozen = approved["prepare_execution"]
        assert frozen == {"attempt": 1, "mode": mode, "target": target, "revision": 4}
        assert run.params_json["prepare_execution"] == frozen
        assert dispatch.committed_at is None  # No resource claim/analysis start.
        assert project_execution_dispatch(
            session=session, settings=_settings(), run=run,
        )["allow_switch"] is False
        with pytest.raises(ExecutionDispatchConflict) as caught:
            change_execution_choice(
                session=session, settings=_settings(), analysis_id=run.analysis_id,
                desired_mode="cce", desired_target="cce", expected_revision=3,
                requested_by="operator", reason="late browser request",
            )
        assert caught.value.code == "PREPARE_EXECUTION_FROZEN"
        again = approve_wgs_config(
            session=session, analysis_id=run.analysis_id, requested_by="operator",
            use_reference="all", resource_set="default",
        )
        assert again["prepare_execution"] == frozen
        assert dispatch.dispatch_revision == 4
        actions = session.scalars(select(RunAction).where(
            RunAction.action == "approve_wgs_config",
        )).all()
        assert len(actions) == 1
        assert actions[0].payload_json["prepare_execution"] == frozen


def test_legacy_config_approval_does_not_reinterpret_execution_contract():
    with _sessions()() as session:
        run = _run(session)
        run.params_json = {
            **run.params_json, "submission_mode": "three_stage",
            "submission_phase": "config_review",
        }
        dispatch = ensure_execution_dispatch(session=session, run=run)
        session.commit()
        approve_wgs_config(
            session=session, analysis_id=run.analysis_id, requested_by="operator",
            use_reference="all", resource_set="default",
        )
        assert "prepare_execution" not in run.params_json
        assert dispatch.dispatch_revision == 1
        assert project_execution_dispatch(
            session=session, settings=_settings(), run=run,
        )["allow_switch"] is True


def test_new_attempt_does_not_inherit_old_prepare_target():
    with _sessions()() as session:
        run = _run(session)
        ensure_execution_dispatch(session=session, run=run)
        run.params_json = {
            **run.params_json, "native_prepare_contract": 1,
            "execution_target": "node-97",
            "prepare_execution": {"attempt": 1, "mode": "local", "target": "node-97", "revision": 3},
        }
        run.attempt = 2
        reset_execution_dispatch_for_attempt(session=session, run=run)
        assert "prepare_execution" not in run.params_json
        assert run.params_json["execution_target"] == "cce"
        assert run.params_json["native_prepare_contract"] == 1
