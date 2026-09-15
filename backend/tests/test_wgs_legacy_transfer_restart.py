"""Same-attempt restart projection; no worker launch or network side effects."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import RunStageState, TransferJob
from app.wgs_observer import _ingest_runtime_stage_status, _ingest_transfer_progress, upsert_stage_state
from test_wgs_observer import prepare_run


def fixture(tmp_path, *, terminal="failed", direction="upload"):
    sessions, analysis_id, *_ = prepare_run(tmp_path)
    stage = "step1_upload" if direction == "upload" else "step5_download"
    transfer_id = f"{analysis_id}-a1-{'input' if direction == 'upload' else 'result'}"
    failed_at = datetime(2026, 8, 12, 2, tzinfo=timezone.utc)
    started = failed_at + timedelta(minutes=2)
    heartbeat = started + timedelta(seconds=10)
    root = tmp_path / "runtime" / "runner-requests"
    folder = root / analysis_id / "attempt-1"
    folder.mkdir(parents=True)
    request = {"analysis_id": analysis_id, "attempt": 1, "stage": stage}
    request_bytes = json.dumps(request).encode()
    (folder / f"{stage}.json").write_bytes(request_bytes)
    worker = {**request, "pid": 1234, "boot_id": "synthetic-boot", "process_start_time": "5678",
              "request_sha256": hashlib.sha256(request_bytes).hexdigest(), "started_at": started.isoformat(), "retry_no": 0}
    worker_path = folder / f"{stage}.worker.json"
    worker_path.write_text(json.dumps(worker))
    payload = {**request, "schema_version": "wgs-runtime.stage-status.v1", "retry_no": 0,
               "status": "running", "updated_at": heartbeat.isoformat()}
    status_path = folder / f"{stage}.status.json"
    status_path.write_text(json.dumps(payload))
    with sessions() as session:
        upsert_stage_state(session, analysis_id=analysis_id, attempt=1, stage_code=stage,
                           stage_status=terminal, updated_at=failed_at)
        session.add(TransferJob(analysis_id=analysis_id, attempt=1, transfer_id=transfer_id,
                               direction=direction, status=terminal, started_at=failed_at - timedelta(minutes=1),
                               ended_at=failed_at, heartbeat_at=failed_at))
        session.commit()
    return sessions, root, status_path, worker_path, payload, worker, started


@pytest.mark.parametrize("direction", ["upload", "download"])
def test_verified_legacy_restart_reopens_both_projections_and_clears_end(tmp_path, direction):
    sessions, root, status, _, _, _, started = fixture(tmp_path, direction=direction)
    assert _ingest_runtime_stage_status(sessions, root, status)
    with sessions() as session:
        row = session.scalar(select(RunStageState))
        transfer = session.scalar(select(TransferJob))
        assert row.stage_status == transfer.status == "running"
        assert row.ended_at is transfer.ended_at is None
        assert row.started_at.replace(tzinfo=timezone.utc) == started
        assert transfer.started_at.replace(tzinfo=timezone.utc) == started
    assert not _ingest_runtime_stage_status(sessions, root, status)


def test_restart_reconciles_stage_even_when_transfer_heartbeat_already_imported(tmp_path):
    sessions, root, status, _, payload, _, _ = fixture(tmp_path)
    with sessions() as session:
        transfer = session.scalar(select(TransferJob))
        transfer.status = "running"
        transfer.heartbeat_at = datetime.fromisoformat(payload["updated_at"])
        session.commit()
    assert _ingest_runtime_stage_status(sessions, root, status)
    with sessions() as session:
        assert session.scalar(select(RunStageState)).stage_status == "running"
        assert session.scalar(select(TransferJob)).ended_at is None


@pytest.mark.parametrize("invalid", ["missing", "request_hash", "attempt", "stage", "old_start", "missing_process", "symlink", "malformed"])
def test_unverified_worker_cannot_reopen_failed_transfer(tmp_path, invalid):
    sessions, root, status, worker_path, payload, worker, started = fixture(tmp_path)
    if invalid == "missing":
        worker_path.unlink()
    elif invalid == "symlink":
        outside = tmp_path / "outside.json"
        worker_path.rename(outside)
        worker_path.symlink_to(outside)
    elif invalid == "malformed":
        worker_path.write_text("[]")
    else:
        if invalid == "request_hash": worker["request_sha256"] = "0" * 64
        if invalid == "attempt": worker["attempt"] = 2
        if invalid == "stage": worker["stage"] = "step5_download"
        if invalid == "old_start": worker["started_at"] = (started - timedelta(minutes=3)).isoformat()
        if invalid == "missing_process": worker.pop("process_start_time")
        worker_path.write_text(json.dumps(worker))
    _ingest_runtime_stage_status(sessions, root, status)
    with sessions() as session:
        assert session.scalar(select(RunStageState)).stage_status == "failed"
        assert session.scalar(select(TransferJob)).status == "failed"


def test_legacy_worker_never_reopens_success(tmp_path):
    sessions, root, status, *_ = fixture(tmp_path, terminal="success")
    _ingest_runtime_stage_status(sessions, root, status)
    with sessions() as session:
        assert session.scalar(select(RunStageState)).stage_status == "success"
        assert session.scalar(select(TransferJob)).status == "success"


def test_completed_restart_can_repair_without_observed_running_poll(tmp_path):
    sessions, root, status, _, payload, _, started = fixture(tmp_path)
    payload["status"] = "success"
    status.write_text(json.dumps(payload))
    assert _ingest_runtime_stage_status(sessions, root, status)
    with sessions() as session:
        row = session.scalar(select(RunStageState))
        assert row.stage_status == "success"
        assert row.started_at.replace(tzinfo=timezone.utc) == started
        assert row.ended_at.replace(tzinfo=timezone.utc) == datetime.fromisoformat(payload["updated_at"])


def test_progress_cannot_bypass_failed_stage_or_reverse_success(tmp_path):
    sessions, root, status, _, payload, _, _ = fixture(tmp_path)
    spool = tmp_path / "transfer-spool"
    spool.mkdir()
    progress = spool / "progress.json"
    progress.write_text(json.dumps({"schema_version": "wgs-runtime.transfer-progress.v2",
        "analysis_id": payload["analysis_id"], "attempt": 1,
        "transfer_id": f"{payload['analysis_id']}-a1-input", "direction": "upload",
        "state": "running", "bytes_total": 100, "bytes_done": 50,
        "files_total": 1, "files_done": 0, "heartbeat_at": payload["updated_at"]}))
    _ingest_transfer_progress(sessions, spool, progress)
    with sessions() as session:
        assert session.scalar(select(TransferJob)).status == "failed"
    assert _ingest_runtime_stage_status(sessions, root, status)
    payload["status"] = "success"
    payload["updated_at"] = (datetime.fromisoformat(payload["updated_at"]) + timedelta(seconds=5)).isoformat()
    status.write_text(json.dumps(payload))
    _ingest_runtime_stage_status(sessions, root, status)
    raw = json.loads(progress.read_text())
    raw["heartbeat_at"] = (datetime.fromisoformat(payload["updated_at"]) + timedelta(seconds=5)).isoformat()
    progress.write_text(json.dumps(raw))
    _ingest_transfer_progress(sessions, spool, progress)
    with sessions() as session:
        assert session.scalar(select(TransferJob)).status == "success"


def test_old_snapshot_and_cross_attempt_cannot_overwrite_restarted_execution(tmp_path):
    sessions, root, status, _, payload, _, started = fixture(tmp_path)
    _ingest_runtime_stage_status(sessions, root, status)
    payload.update(status="failed", updated_at=(started - timedelta(seconds=1)).isoformat())
    status.write_text(json.dumps(payload))
    assert not _ingest_runtime_stage_status(sessions, root, status)
    with sessions() as session:
        assert session.scalar(select(RunStageState)).stage_status == "running"
        assert session.scalar(select(TransferJob)).ended_at is None
    payload["attempt"] = 2
    status.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        _ingest_runtime_stage_status(sessions, root, status)
