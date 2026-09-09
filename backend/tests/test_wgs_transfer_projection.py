from datetime import datetime, timezone

from app.models import TransferJob
from app.wgs_transfer_projection import serialize_transfer_job


def _job(**overrides) -> TransferJob:
    values = {
        "analysis_id": "WGS_20260907_152648_54EFF2",
        "attempt": 1,
        "transfer_id": "WGS_20260907_152648_54EFF2-a1-input",
        "transfer_type": "input_upload",
        "direction": "upload",
        "status": "running",
        "bytes_total": 8950,
        "bytes_transferred": 2304,
        "files_total": 18,
        "files_completed": 0,
        "progress_percent": 26,
        "progress_detail_available": True,
        "started_at": datetime(2026, 9, 7, 15, 30, tzinfo=timezone.utc),
        "heartbeat_at": datetime(2026, 9, 7, 17, 52, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return TransferJob(**values)


def test_transfer_projection_uses_bytes_and_one_decimal_percent() -> None:
    payload = serialize_transfer_job(_job())

    assert payload["progress_percent"] == 25.7
    assert payload["bytes_transferred"] == 2304
    assert payload["bytes_total"] == 8950
    assert payload["started_at"] == "2026-09-07T15:30:00+00:00"
    assert payload["finished_at"] is None


def test_successful_transfer_projection_is_exactly_complete() -> None:
    payload = serialize_transfer_job(
        _job(status="success", bytes_transferred=8949, progress_percent=99)
    )

    assert payload["progress_percent"] == 100.0


def test_transfer_projection_hides_untrusted_detail() -> None:
    payload = serialize_transfer_job(_job(progress_detail_available=False))

    assert payload["progress_percent"] is None
    assert payload["bytes_total"] is None
    assert payload["bytes_transferred"] is None


def test_transfer_projection_identifies_obsutil_checkpoint_engine() -> None:
    payload = serialize_transfer_job(_job(checkpoint_ref="obsutil-checkpoint"))

    assert payload["transfer_engine"] == "obsutil"
