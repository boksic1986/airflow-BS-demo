from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, ObsTransferLease, TransferJob
from app.wgs_platform_service import acquire_obs_transfer_slot, release_obs_transfer_slot


ANALYSIS_ID = "WGS_20260907_010203_A1B2C3"
UPLOAD_ID = f"{ANALYSIS_ID}-a1-input"
DOWNLOAD_ID = f"{ANALYSIS_ID}-a1-result"


def _sessions():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _lease(*, slot_name: str, transfer_id: str) -> ObsTransferLease:
    return ObsTransferLease(
        slot_name=slot_name,
        analysis_id=ANALYSIS_ID,
        attempt=1,
        transfer_id=transfer_id,
        leased_at=datetime(2026, 9, 7, 1, 2, 3, tzinfo=timezone.utc),
        lease_expires_at=None,
    )


def _transfer(*, transfer_id: str, direction: str, status: str) -> TransferJob:
    return TransferJob(
        analysis_id=ANALYSIS_ID,
        attempt=1,
        transfer_id=transfer_id,
        direction=direction,
        status=status,
    )


def test_running_transfer_evidence_retains_directional_lease() -> None:
    sessions = _sessions()
    with sessions() as session:
        session.add(_lease(slot_name="wgs-obs-upload-01", transfer_id=UPLOAD_ID))
        session.add(_transfer(transfer_id=UPLOAD_ID, direction="upload", status="running"))
        session.commit()

        result = release_obs_transfer_slot(
            session=session,
            analysis_id=ANALYSIS_ID,
            attempt=1,
            transfer_id=UPLOAD_ID,
            transfer_kind="input",
        )

        assert result == {
            "released": False,
            "retained": True,
            "reason": "transfer_not_terminal",
            "slots": ["wgs-obs-upload-01"],
        }
        lease = session.scalar(
            select(ObsTransferLease).where(
                ObsTransferLease.slot_name == "wgs-obs-upload-01"
            )
        )
        assert lease.analysis_id == ANALYSIS_ID
        assert lease.transfer_id == UPLOAD_ID


def test_upload_and_download_leases_are_independent() -> None:
    sessions = _sessions()
    with sessions() as session:
        session.add_all(
            [
                ObsTransferLease(slot_name="wgs-obs-upload-01"),
                ObsTransferLease(slot_name="wgs-obs-download-01"),
            ]
        )
        session.commit()

        upload = acquire_obs_transfer_slot(
            session=session,
            analysis_id=ANALYSIS_ID,
            attempt=1,
            transfer_id=UPLOAD_ID,
            transfer_kind="input",
        )
        download = acquire_obs_transfer_slot(
            session=session,
            analysis_id="WGS_20260907_020304_D4E5F6",
            attempt=1,
            transfer_id="WGS_20260907_020304_D4E5F6-a1-result",
            transfer_kind="result",
        )

        assert upload == "wgs-obs-upload-01"
        assert download == "wgs-obs-download-01"


def test_same_attempt_cannot_replace_directional_transfer_identity() -> None:
    sessions = _sessions()
    with sessions() as session:
        session.add(_lease(slot_name="wgs-obs-upload-01", transfer_id=UPLOAD_ID))
        session.commit()

        acquired = acquire_obs_transfer_slot(
            session=session,
            analysis_id=ANALYSIS_ID,
            attempt=1,
            transfer_id=f"{ANALYSIS_ID}-a1-different-input",
            transfer_kind="input",
        )

        assert acquired is None
        lease = session.scalar(
            select(ObsTransferLease).where(
                ObsTransferLease.slot_name == "wgs-obs-upload-01"
            )
        )
        assert lease.transfer_id == UPLOAD_ID


@pytest.mark.parametrize("terminal_status", ["success", "failed", "canceled"])
def test_exact_terminal_evidence_releases_only_matching_direction(
    terminal_status: str,
) -> None:
    sessions = _sessions()
    with sessions() as session:
        session.add_all(
            [
                _lease(slot_name="wgs-obs-upload-01", transfer_id=UPLOAD_ID),
                _lease(slot_name="wgs-obs-download-01", transfer_id=DOWNLOAD_ID),
                _transfer(
                    transfer_id=UPLOAD_ID,
                    direction="upload",
                    status=terminal_status,
                ),
                _transfer(
                    transfer_id=DOWNLOAD_ID,
                    direction="download",
                    status="running",
                ),
            ]
        )
        session.commit()

        result = release_obs_transfer_slot(
            session=session,
            analysis_id=ANALYSIS_ID,
            attempt=1,
            transfer_id=UPLOAD_ID,
            transfer_kind="input",
        )

        assert result == {
            "released": True,
            "retained": False,
            "reason": None,
            "slots": ["wgs-obs-upload-01"],
        }
        rows = {
            row.slot_name: row
            for row in session.scalars(select(ObsTransferLease)).all()
        }
        assert rows["wgs-obs-upload-01"].analysis_id is None
        assert rows["wgs-obs-download-01"].analysis_id == ANALYSIS_ID


def test_final_cleanup_releases_terminal_and_retains_unknown_owned_direction() -> None:
    sessions = _sessions()
    with sessions() as session:
        session.add_all(
            [
                _lease(slot_name="wgs-obs-upload-01", transfer_id=UPLOAD_ID),
                _lease(slot_name="wgs-obs-download-01", transfer_id=DOWNLOAD_ID),
                _transfer(transfer_id=UPLOAD_ID, direction="upload", status="success"),
            ]
        )
        session.commit()

        result = release_obs_transfer_slot(
            session=session,
            analysis_id=ANALYSIS_ID,
            attempt=1,
        )

        assert result == {
            "released": True,
            "retained": True,
            "reason": "transfer_not_terminal",
            "slots": ["wgs-obs-upload-01", "wgs-obs-download-01"],
        }
        rows = {
            row.slot_name: row
            for row in session.scalars(select(ObsTransferLease)).all()
        }
        assert rows["wgs-obs-upload-01"].analysis_id is None
        assert rows["wgs-obs-download-01"].analysis_id == ANALYSIS_ID


def test_wrong_transfer_id_cannot_release_owned_lease() -> None:
    sessions = _sessions()
    with sessions() as session:
        session.add(_lease(slot_name="wgs-obs-upload-01", transfer_id=UPLOAD_ID))
        session.add(_transfer(transfer_id=UPLOAD_ID, direction="upload", status="success"))
        session.commit()

        with pytest.raises(ValueError, match="another transfer"):
            release_obs_transfer_slot(
                session=session,
                analysis_id=ANALYSIS_ID,
                attempt=1,
                transfer_id="wrong-transfer",
                transfer_kind="input",
            )
