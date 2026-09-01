from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Callable

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import AnalysisRun, ObserverRunState, RunAttempt
from app.wgs_evidence_binding import CCE_RUN_LABEL_PATTERN


OBSERVER_CHANNEL = "wgs_observer_activation"
ObserverNotifier = Callable[[Session, str, int], None]


def activate_observer(
    session: Session,
    *,
    analysis_id: str,
    attempt: int,
    notify: ObserverNotifier | None = None,
) -> ObserverRunState:
    analysis, run_attempt = _load_attempt(session, analysis_id, attempt)
    release_id = str((analysis.params_json or {}).get("pipeline_release_id") or "")
    if not release_id:
        raise ValueError("WGS run is missing pipeline_release_id")
    run_label = run_attempt.run_label or f"{analysis_id}-a{attempt}"
    run_attempt.run_label = run_label
    evidence_path = f"{analysis_id}/attempt-{attempt}"
    state = session.scalar(
        select(ObserverRunState).where(
            ObserverRunState.analysis_id == analysis_id,
            ObserverRunState.attempt == attempt,
        )
    )
    now = datetime.now(timezone.utc)
    if state is None:
        state = ObserverRunState(
            analysis_id=analysis_id,
            attempt=attempt,
            pipeline_release_id=release_id,
            run_label=run_label,
            relative_evidence_path=evidence_path,
            lifecycle_status="active",
            monitoring_health="healthy",
            activated_at=now,
        )
        session.add(state)
    else:
        runtime_label_bound = (
            CCE_RUN_LABEL_PATTERN.fullmatch(state.run_label or "") is not None
        )
        if (
            state.pipeline_release_id != release_id
            or (state.run_label != run_label and not runtime_label_bound)
            or state.relative_evidence_path != evidence_path
        ):
            raise ValueError("observer activation conflicts with persisted binding")
        state.lifecycle_status = "active"
        state.activated_at = state.activated_at or now
        state.deactivated_at = None
        state.updated_at = now
    session.flush()
    (notify or notify_observer_change)(session, analysis_id, attempt)
    return state


def request_observer_drain(
    session: Session,
    *,
    analysis_id: str,
    attempt: int,
    notify: ObserverNotifier | None = None,
) -> ObserverRunState | None:
    state = session.scalar(
        select(ObserverRunState).where(
            ObserverRunState.analysis_id == analysis_id,
            ObserverRunState.attempt == attempt,
        )
    )
    if state is None:
        # A cleanup path may run before Step3 was ever accepted.  Treat that as
        # already stopped without manufacturing a misleading observer record.
        _load_attempt(session, analysis_id, attempt)
        return None
    if state.lifecycle_status != "stopped":
        state.lifecycle_status = "draining"
        state.updated_at = datetime.now(timezone.utc)
    session.flush()
    (notify or notify_observer_change)(session, analysis_id, attempt)
    return state


def list_observer_work(session_factory) -> list[tuple[str, int]]:
    with session_factory() as session:
        rows = session.execute(
            select(ObserverRunState.analysis_id, ObserverRunState.attempt).where(
                ObserverRunState.lifecycle_status.in_(("active", "draining"))
            )
        ).all()
    return [(str(analysis_id), int(attempt)) for analysis_id, attempt in rows]


def notify_observer_change(session: Session, analysis_id: str, attempt: int) -> None:
    if session.get_bind().dialect.name != "postgresql":
        return
    payload = json.dumps(
        {"analysis_id": analysis_id, "attempt": attempt}, separators=(",", ":")
    )
    session.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {"channel": OBSERVER_CHANNEL, "payload": payload},
    )


def _load_attempt(
    session: Session, analysis_id: str, attempt: int
) -> tuple[AnalysisRun, RunAttempt]:
    analysis = session.scalar(
        select(AnalysisRun).where(
            AnalysisRun.analysis_id == analysis_id,
            AnalysisRun.pipeline_name == "wgs",
        )
    )
    run_attempt = session.scalar(
        select(RunAttempt).where(
            RunAttempt.analysis_id == analysis_id,
            RunAttempt.attempt == attempt,
        )
    )
    if analysis is None or run_attempt is None or analysis.attempt != attempt:
        raise ValueError("unknown active WGS attempt")
    return analysis, run_attempt
