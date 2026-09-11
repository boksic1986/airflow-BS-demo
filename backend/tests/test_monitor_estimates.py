from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import AnalysisRun, Base, WgsStageExecution
from app.wgs_stage_execution_service import transition_stage_execution
from app.wgs_timing_service import enrich_progress


def test_fixed_stage_baseline_queue_freeze_retry_and_read_consistency():
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        run = AnalysisRun(analysis_id="EST", pipeline_name="wgs", dag_id="bio_wgs", workdir="/synthetic", attempt=1, status="running", execution_mode="cce", current_stage="step4_publish", params_json={"pipeline_release_id": "rel"})
        session.add(run)
        for i, duration in enumerate((90, 120, 150)):
            old = AnalysisRun(analysis_id=f"OLD{i}", pipeline_name="wgs", dag_id="bio_wgs", workdir="/synthetic", execution_mode="cce", status="success")
            session.add(old)
            session.add(WgsStageExecution(analysis_id=old.analysis_id, attempt=1, execution_id=f"OLD{i}", generation=1, stage_code="step4_publish", request_hash="a"*64, release_id="rel", status="success", started_at=now-timedelta(days=1, seconds=duration), ended_at=now-timedelta(days=1)))
        row = WgsStageExecution(analysis_id="EST", attempt=1, execution_id="EX1", generation=1, stage_code="step4_publish", request_hash="a"*64, release_id="rel", status="accepted")
        session.add(row)
        session.commit()
        from app.wgs_stage_estimates import stage_estimate
        assert stage_estimate(row, now=now)["estimated_progress_percent"] is None
        transition_stage_execution(session=session, execution_id="EX1", generation=1, status="running", observed_at=now)
        session.commit()
        session.expire_all()
        result = stage_estimate(row, now=now+timedelta(seconds=120))
        assert result["estimate_baseline_seconds"] == 120
        assert result["estimate_history_count"] == 3
        assert result["estimated_progress_percent"] == pytest.approx(62.6)
        assert result["estimate_overrun"] is True
        session.add(WgsStageExecution(analysis_id="OLD0", attempt=2, execution_id="LATER", generation=1, stage_code="step4_publish", request_hash="a"*64, release_id="rel", status="success", started_at=now, ended_at=now+timedelta(seconds=999)))
        session.commit()
        assert stage_estimate(row, now=now+timedelta(seconds=240))["estimate_baseline_seconds"] == 120
        payload = enrich_progress(session=session, run=run, payload={})
        rail = next(s for s in payload["orchestration_stages"] if s["stage_code"] == "step4_publish")
        assert payload["estimated_progress_percent"] == rail["estimated_progress_percent"]
        assert payload["progress_percent"] is None
        assert not session.dirty
        from app.wgs_workspace_service import build_wgs_workspace
        from app.wgs_stage_estimates import stage_estimates
        workspace = build_wgs_workspace(session=session, run=run, run_payload={})
        assert workspace["progress"]["estimate_baseline_seconds"] == payload["estimate_baseline_seconds"]
        assert workspace["progress"]["estimated_progress_percent"] == payload["estimated_progress_percent"]
        run.status = "cancelled"
        run.ended_at = now + timedelta(seconds=120)
        assert stage_estimates(session, run, now=now+timedelta(days=1))["step4_publish"]["estimated_progress_percent"] == 62.6
        run.status = "running"
        transition_stage_execution(session=session, execution_id="EX1", generation=1, status="failed", observed_at=now+timedelta(seconds=120))
        session.commit()
        assert stage_estimate(row, now=now+timedelta(days=1))["estimated_progress_percent"] == 62.6
        assert stage_estimate(row, now=now+timedelta(days=1))["estimate_frozen"] is True
        retry = WgsStageExecution(analysis_id="EST", attempt=1, execution_id="EX2", generation=2, stage_code="step4_publish", request_hash="b"*64, release_id="rel", status="accepted")
        session.add(retry)
        session.commit()
        assert stage_estimate(retry, now=now)["estimated_progress_percent"] is None
        assert transition_stage_execution(session=session, execution_id="EX1", generation=1, status="success", receipt_hash="a"*64) is False


def test_insufficient_history_and_success_without_fabricated_start():
    from app.wgs_stage_estimates import stage_estimate
    row = WgsStageExecution(execution_id="x", generation=1, status="running")
    assert stage_estimate(row)["estimated_progress_percent"] is None
    row.status = "success"
    assert stage_estimate(row)["estimated_progress_percent"] == 100


def test_gatk_sidecar_writer_starts_only_running_and_preserves_terminal_clock(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    import app.gatk_runtime_service as service
    from test_gatk_runtime_service import _sessions, _settings, _run, _execution, ANALYSIS_ID
    from app.wgs_stage_estimates import stage_estimate
    settings = _settings(tmp_path)
    sessions = _sessions()
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now
    monkeypatch.setattr(service, "datetime", Clock)
    with sessions() as session:
        run = _run()
        run.execution_mode = "cce"
        session.add(run)
        for i in range(3):
            history = _execution("step4_publish", i + 5, "success")
            history.started_at = now-timedelta(days=1, seconds=120)
            history.ended_at = now-timedelta(days=1)
            session.add(history)
        row = _execution("step6_materialize", 1, "accepted")
        session.add(row)
        session.commit()
        path = Path(settings.gatk_runtime_request_root) / ANALYSIS_ID / "attempt-1" / "step6_materialize.request.status.json"
        path.parent.mkdir(parents=True)
        payload = {"analysis_id": ANALYSIS_ID, "attempt": 1, "stage": "step6_materialize", "generation": 1, "execution_id": row.execution_id, "request_hash": row.request_hash, "status": "success"}
        path.write_text(json.dumps(payload))
        service.sync_gatk_stage_status(session=session, settings=settings, analysis_id=ANALYSIS_ID, attempt=1, stage="step6_materialize")
        assert row.started_at is None
        ended = row.ended_at
        now += timedelta(seconds=50)
        service.sync_gatk_stage_status(session=session, settings=settings, analysis_id=ANALYSIS_ID, attempt=1, stage="step6_materialize")
        assert row.ended_at == ended
        row4 = _execution("step4_publish", 9, "accepted")
        session.add(row4)
        session.commit()
        path4 = path.with_name("step4_publish.request.status.json")
        path4.write_text(json.dumps({**payload, "stage": "step4_publish", "generation": 9, "execution_id": row4.execution_id, "request_hash": row4.request_hash, "status": "running"}))
        service.sync_gatk_stage_status(session=session, settings=settings, analysis_id=ANALYSIS_ID, attempt=1, stage="step4_publish")
        assert stage_estimate(row4, now=now+timedelta(seconds=120))["estimated_progress_percent"] == 62.6
        from app.gatk_workspace_service import build_gatk_workspace
        from app.pipeline_registry_service import _project_gatk_progress
        workspace = build_gatk_workspace(session=session, run=run, run_payload={})
        progress = _project_gatk_progress(session=session, run=run, payload={})
        assert workspace["progress"]["estimate_baseline_seconds"] == 120
        assert progress["estimate_baseline_seconds"] == 120
        assert workspace["progress"]["estimated_progress_percent"] == progress["estimated_progress_percent"]


@pytest.mark.parametrize("terminal", ["failed", "canceled"])
def test_gatk_matching_history_and_terminal_retry_generation(tmp_path, monkeypatch, terminal):
    import json
    from pathlib import Path
    import app.gatk_runtime_service as service
    from test_gatk_runtime_service import _sessions, _settings, _run, _execution, ANALYSIS_ID
    from app.wgs_stage_estimates import stage_estimate, stage_estimates, KEY
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now
    monkeypatch.setattr(service, "datetime", Clock)
    settings = _settings(tmp_path)
    with _sessions()() as session:
        run = _run()
        run.execution_mode = "cce"
        session.add(run)
        for i, mismatch in enumerate([None, None, None, "pipeline", "release", "target"]):
            old = _run()
            old.analysis_id = f"H{i}"
            old.pipeline_name = "wgs" if mismatch == "pipeline" else "gatk"
            old.execution_mode = "cce"
            old.params_json = {"execution_target": "local" if mismatch == "target" else "cce"}
            session.add(old)
            h = _execution("step4_publish", i+10, "success")
            h.analysis_id = old.analysis_id
            h.pipeline_name = old.pipeline_name
            h.release_id = "different-release" if mismatch == "release" else h.release_id
            h.started_at = now-timedelta(days=1, seconds=999 if mismatch else 120)
            h.ended_at = now-timedelta(days=1)
            session.add(h)
        first = _execution("step4_publish", 1, "accepted")
        session.add(first)
        session.commit()
        path = Path(settings.gatk_runtime_request_root) / ANALYSIS_ID / "attempt-1" / "step4_publish.request.status.json"
        path.parent.mkdir(parents=True)
        def observe(row, status):
            path.write_text(json.dumps({"analysis_id": ANALYSIS_ID, "attempt": 1, "stage": "step4_publish", "generation": row.generation, "execution_id": row.execution_id, "request_hash": row.request_hash, "status": status}))
            return service.sync_gatk_stage_status(session=session, settings=settings, analysis_id=ANALYSIS_ID, attempt=1, stage="step4_publish")
        observe(first, "running")
        assert stage_estimate(first)["estimate_history_count"] == 3
        assert stage_estimate(first)["estimate_baseline_seconds"] == 120
        assert len(first.terminal_payload_json[KEY]["history_execution_ids"]) == 3
        now += timedelta(seconds=120)
        observe(first, terminal)
        assert stage_estimate(first)["estimated_progress_percent"] == 62.6
        assert stage_estimate(first)["estimate_frozen"] is True
        ended = first.ended_at
        now += timedelta(days=1)
        observe(first, "running")
        assert first.ended_at == ended
        assert stage_estimate(first)["estimated_progress_percent"] == 62.6
        retry = _execution("step4_publish", 2, "accepted")
        session.add(retry)
        run.status = "running"
        run.ended_at = None
        run.pipeline_finished_at = None
        session.commit()
        assert stage_estimates(session, run)["step4_publish"]["estimated_progress_percent"] is None
        observe(first, "success")  # Late generation 1 cannot start or complete generation 2.
        assert retry.status == "accepted"
        observe(retry, "running")
        fresh = stage_estimates(session, run, now=now)["step4_publish"]
        assert fresh["estimate_generation"] == 2
        assert fresh["estimated_progress_percent"] == 0
        assert fresh["estimate_frozen"] is False
