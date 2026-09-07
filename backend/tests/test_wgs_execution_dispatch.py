from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import (
    AnalysisRun,
    Base,
    ObsTransferLease,
    PlatformResourceSnapshot,
    RunAttempt,
    WgsExecutionDispatch,
    WgsExecutionTargetSlot,
)
from app.wgs_execution_dispatch_service import (
    ExecutionDispatchConflict,
    change_execution_choice,
    commit_execution_choice,
    ensure_execution_dispatch,
    mark_execution_needs_recovery,
    mark_execution_running,
    mark_execution_terminal,
    project_execution_dispatch,
)


def _sessions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _settings(**overrides):
    values = {
        "wgs_local_node97_enabled": True,
        "wgs_local_node96_enabled": True,
        "wgs_sge_enabled": False,
        "wgs_local_min_logical_cpus": 96,
        "wgs_local_admission_samples": 3,
        "wgs_local_admission_cpu_percent": 25.0,
        "wgs_local_admission_load_ratio": 0.25,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _run(session, *, analysis_id="WGS_20260906_010203_A1B2C3", batch="20260906A"):
    row = AnalysisRun(
        analysis_id=analysis_id,
        pipeline_name="wgs",
        dag_id="bio_wgs",
        execution_mode="cce",
        attempt=1,
        status="submitted",
        workdir=f"/runs/{analysis_id}",
        params_json={
            "project_id": "WGS_Clinical",
            "project_name": "WGS_Clinical",
            "analysis_batch": batch,
            "sequencing_batch": batch,
            "submission_phase": "approved",
        },
    )
    session.add(row)
    session.add(
        RunAttempt(
            analysis_id=analysis_id,
            attempt=1,
            execution_mode="cce",
            status="created",
        )
    )
    session.flush()
    return row


def _node_snapshot(session, target="node-97", *, cpu=(10.0, 12.0, 8.0), loads=(10.0, 12.0, 8.0), age_seconds=0):
    now = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    history = []
    for index, (cpu_value, load_value) in enumerate(zip(cpu, loads, strict=True)):
        history.append(
            {
                "at": (now - timedelta(minutes=2 - index)).isoformat(),
                "cpu_used_percent": cpu_value,
                "node_load1": load_value,
                "node_load5": load_value,
                "node_load15": load_value,
                "node_memory_MemTotal_bytes": 1000,
                "node_memory_MemAvailable_bytes": 800,
                "logical_cpu_count": 128,
            }
        )
    row = PlatformResourceSnapshot(
        resource_key=target,
        resource_type="node",
        display_name={"node-97": "172.17.61.97", "node-96": "172.17.61.96"}[target],
        status="healthy",
        current_json=dict(history[-1]),
        history_json=history,
        source_updated_at=now,
        collected_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    return row


def test_choice_changes_same_attempt_and_increments_revision():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        _node_snapshot(session)
        initial = ensure_execution_dispatch(session=session, run=run)
        initial_revision = initial.dispatch_revision
        session.commit()

        changed = change_execution_choice(
            session=session,
            settings=_settings(),
            analysis_id=run.analysis_id,
            desired_mode="local",
            desired_target="node-97",
            expected_revision=initial_revision,
            requested_by="operator",
            reason="use idle local node",
        )

        attempt = session.scalar(
            select(RunAttempt).where(
                RunAttempt.analysis_id == run.analysis_id,
                RunAttempt.attempt == 1,
            )
        )
        assert changed["desired_target"] == "node-97"
        assert changed["dispatch_revision"] == initial_revision + 1
        assert run.attempt == 1
        assert attempt.execution_mode == "local"
        assert run.execution_mode == "local"


def test_stale_revision_is_rejected_without_mutation():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        dispatch = ensure_execution_dispatch(session=session, run=run)
        session.commit()

        with pytest.raises(ExecutionDispatchConflict) as caught:
            change_execution_choice(
                session=session,
                settings=_settings(),
                analysis_id=run.analysis_id,
                desired_mode="cce",
                desired_target="cce",
                expected_revision=dispatch.dispatch_revision - 1,
                requested_by="operator",
                reason="stale browser",
            )

        assert caught.value.code == "STALE_EXECUTION_CHOICE"
        assert dispatch.desired_target == "cce"


def test_local_target_requires_three_low_cpu_and_load_samples():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        _node_snapshot(session, cpu=(10.0, 26.0, 10.0))
        dispatch = ensure_execution_dispatch(session=session, run=run)
        session.commit()

        projected = project_execution_dispatch(
            session=session,
            settings=_settings(),
            run=run,
        )
        node = next(item for item in projected["targets"] if item["target"] == "node-97")
        assert node["status"] == "high_load"
        assert node["available"] is False
        assert "three" in node["reason"].lower()

        with pytest.raises(ExecutionDispatchConflict) as caught:
            change_execution_choice(
                session=session,
                settings=_settings(),
                analysis_id=run.analysis_id,
                desired_mode="local",
                desired_target="node-97",
                expected_revision=dispatch.dispatch_revision,
                requested_by="operator",
                reason="try overloaded node",
            )
        assert caught.value.code == "TARGET_UNAVAILABLE"


def test_local_target_rejects_nonconsecutive_metric_history():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        snapshot = _node_snapshot(session)
        repeated = dict(snapshot.history_json[-1])
        snapshot.history_json = [repeated, repeated, repeated]
        ensure_execution_dispatch(session=session, run=run)
        session.commit()

        projected = project_execution_dispatch(
            session=session,
            settings=_settings(),
            run=run,
        )
        node = next(item for item in projected["targets"] if item["target"] == "node-97")
        assert node["status"] == "stale"
        assert "consecutive" in node["reason"].lower()


def test_committing_cce_acquires_upload_slot_and_freezes_choice():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        dispatch = ensure_execution_dispatch(session=session, run=run)
        dispatch.dispatch_state = "waiting_resource"
        session.add(ObsTransferLease(slot_name="wgs-obs-upload-01"))
        session.commit()

        committed = commit_execution_choice(
            session=session,
            settings=_settings(),
            analysis_id=run.analysis_id,
            attempt=1,
        )
        assert committed["committed"] is True
        assert committed["desired_target"] == "cce"
        assert committed["dispatch_state"] == "committed"
        lease = session.scalar(
            select(ObsTransferLease).where(
                ObsTransferLease.slot_name == "wgs-obs-upload-01"
            )
        )
        assert lease.analysis_id == run.analysis_id
        assert lease.attempt == 1
        assert lease.lease_expires_at is None

        with pytest.raises(ExecutionDispatchConflict) as caught:
            change_execution_choice(
                session=session,
                settings=_settings(),
                analysis_id=run.analysis_id,
                desired_mode="cce",
                desired_target="cce",
                expected_revision=committed["dispatch_revision"],
                requested_by="operator",
                reason="too late",
            )
        assert caught.value.code == "EXECUTION_ALREADY_COMMITTED"


def test_cce_waits_without_committing_when_upload_slot_is_owned():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        dispatch = ensure_execution_dispatch(session=session, run=run)
        dispatch.dispatch_state = "waiting_resource"
        session.add(
            ObsTransferLease(
                slot_name="wgs-obs-upload-01",
                analysis_id="WGS_20260906_999999_FFFFFF",
                attempt=1,
                transfer_id="other-upload",
                leased_at=datetime.now(timezone.utc) - timedelta(hours=3),
                lease_expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
            )
        )
        session.commit()

        result = commit_execution_choice(
            session=session,
            settings=_settings(),
            analysis_id=run.analysis_id,
            attempt=1,
        )
        assert result["committed"] is False
        assert result["dispatch_state"] == "waiting_resource"
        assert result["blocking_reason"] == "Waiting for CCE upload slot"
        projected = project_execution_dispatch(
            session=session, settings=_settings(), run=run
        )
        cce = next(item for item in projected["targets"] if item["target"] == "cce")
        assert cce["status"] == "waiting_upload_slot"
        assert cce["available"] is True


def test_dispatch_state_survives_new_session_and_releases_local_slot_at_terminal():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        _node_snapshot(session)
        session.add_all(
            [
                ObsTransferLease(slot_name="wgs-obs-upload-01"),
                ObsTransferLease(slot_name="wgs-obs-download-01"),
            ]
        )
        dispatch = ensure_execution_dispatch(session=session, run=run)
        session.commit()
        change_execution_choice(
            session=session,
            settings=_settings(),
            analysis_id=run.analysis_id,
            desired_mode="local",
            desired_target="node-97",
            expected_revision=dispatch.dispatch_revision,
            requested_by="operator",
            reason="accepted local validation",
        )
        committed = commit_execution_choice(
            session=session,
            settings=_settings(),
            analysis_id=run.analysis_id,
            attempt=1,
        )
        assert committed["committed"] is True
        directional_leases = session.scalars(
            select(ObsTransferLease).where(
                ObsTransferLease.slot_name.in_(
                    ("wgs-obs-upload-01", "wgs-obs-download-01")
                )
            )
        ).all()
        assert len(directional_leases) == 2
        assert all(lease.analysis_id is None for lease in directional_leases)

    with sessions() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.attempt == 1
        mark_execution_running(session=session, analysis_id=run.analysis_id, attempt=1)
        session.commit()
        projected = project_execution_dispatch(
            session=session, settings=_settings(), run=run
        )
        assert projected["dispatch_state"] == "running"
        mark_execution_terminal(
            session=session, analysis_id=run.analysis_id, attempt=1
        )
        session.commit()
        projected = project_execution_dispatch(
            session=session, settings=_settings(), run=run
        )
        assert projected["dispatch_state"] == "terminal"
        assert projected["desired_target"] == "node-97"


def test_failed_local_execution_releases_target_slot_when_recovery_is_required():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        _node_snapshot(session)
        dispatch = ensure_execution_dispatch(session=session, run=run)
        session.commit()
        change_execution_choice(
            session=session,
            settings=_settings(),
            analysis_id=run.analysis_id,
            desired_mode="local",
            desired_target="node-97",
            expected_revision=dispatch.dispatch_revision,
            requested_by="operator",
            reason="accepted local validation",
        )
        commit_execution_choice(
            session=session,
            settings=_settings(),
            analysis_id=run.analysis_id,
            attempt=1,
        )
        mark_execution_running(
            session=session, analysis_id=run.analysis_id, attempt=1
        )
        session.commit()

        mark_execution_needs_recovery(
            session=session,
            analysis_id=run.analysis_id,
            attempt=1,
            reason="node97 workflow exited 143",
        )
        session.commit()

        slot = session.get(WgsExecutionTargetSlot, "node-97")
        assert slot is not None
        assert slot.analysis_id is None
        assert slot.attempt is None
        projected = project_execution_dispatch(
            session=session, settings=_settings(), run=run
        )
        assert projected["dispatch_state"] == "needs_recovery"
        assert projected["blocking_reason"] == "node97 workflow exited 143"


def test_project_batch_claim_is_idempotent_but_rejects_another_run():
    sessions = _sessions()
    with sessions() as session:
        first = _run(session)
        one = ensure_execution_dispatch(session=session, run=first)
        two = ensure_execution_dispatch(session=session, run=first)
        assert one.id == two.id
        second = _run(
            session,
            analysis_id="WGS_20260906_010204_B1C2D3",
            batch="20260906A",
        )
        with pytest.raises(ExecutionDispatchConflict) as caught:
            ensure_execution_dispatch(session=session, run=second)
        assert caught.value.code == "BATCH_EXECUTION_EXISTS"


def test_historical_duplicate_batch_remains_readable_without_new_claim():
    sessions = _sessions()
    with sessions() as session:
        first = _run(session)
        ensure_execution_dispatch(session=session, run=first)
        second = _run(
            session,
            analysis_id="WGS_20260906_010204_B1C2D3",
            batch="20260906A",
        )
        second.params_json = {
            **second.params_json,
            "submission_mode": "legacy",
        }
        session.commit()

        assert project_execution_dispatch(
            session=session,
            settings=_settings(),
            run=second,
        ) is None


def test_historical_running_attempt_without_dispatch_remains_observable():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        mark_execution_running(session=session, analysis_id=run.analysis_id, attempt=1)
        session.commit()

        assert session.scalar(select(WgsExecutionDispatch)) is None


def test_phase_one_projects_local_and_sge_as_unsupported():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        _node_snapshot(session)
        _node_snapshot(session, target="node-96")
        ensure_execution_dispatch(session=session, run=run)
        session.commit()

        payload = project_execution_dispatch(
            session=session,
            settings=_settings(
                wgs_local_node97_enabled=False,
                wgs_local_node96_enabled=False,
                wgs_sge_enabled=False,
            ),
            run=run,
        )

        states = {item["target"]: item["status"] for item in payload["targets"]}
        assert states == {
            "cce": "available",
            "node-97": "unsupported",
            "node-96": "unsupported",
            "sge-default": "unsupported",
        }
