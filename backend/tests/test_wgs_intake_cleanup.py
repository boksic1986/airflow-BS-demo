from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import AnalysisRun, Base, WgsIntakeBatch, WgsIntakeScannerState
from app.wgs_intake_cleanup import reset_wgs_intake_baseline


def make_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def intake_row(index: int, *, analysis_id: str | None = None) -> WgsIntakeBatch:
    return WgsIntakeBatch(
        source_path=f"/bi/fastq/T7_Fastq/{index}th_20260830A_E{index:09d}",
        chip_id=f"{index}th_20260830A_E{index:09d}",
        sequencing_batch="20260830A",
        analysis_id=analysis_id,
        state="bootstrap_ignored",
    )


def test_reset_removes_all_1830_unlinked_discoveries_and_scanner_baseline() -> None:
    sessions = make_sessionmaker()
    with sessions.begin() as session:
        session.add_all(intake_row(index) for index in range(1830))
        session.add(WgsIntakeScannerState(id=1, last_scanned_directory_count=1830))

    with sessions.begin() as session:
        result = reset_wgs_intake_baseline(session)

    assert result == {"deleted_batches": 1830, "deleted_scanner_states": 1}
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(WgsIntakeBatch)) == 0
        assert session.scalar(select(func.count()).select_from(WgsIntakeScannerState)) == 0


def test_reset_aborts_without_deleting_when_any_discovery_is_linked() -> None:
    sessions = make_sessionmaker()
    with sessions.begin() as session:
        session.add(
            AnalysisRun(
                analysis_id="WGS_20260830_010203_A1B2C3",
                pipeline_name="wgs",
                dag_id="bio_wgs",
                workdir="/runs/WGS_20260830_010203_A1B2C3",
                params_json={},
            )
        )
        session.add(intake_row(1, analysis_id="WGS_20260830_010203_A1B2C3"))
        session.add(intake_row(2))
        session.add(WgsIntakeScannerState(id=1, last_scanned_directory_count=2))

    with sessions() as session:
        try:
            reset_wgs_intake_baseline(session)
        except ValueError as exc:
            assert "linked AnalysisRun" in str(exc)
            session.rollback()
        else:
            raise AssertionError("linked intake reset must be rejected")

    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(WgsIntakeBatch)) == 2
        assert session.scalar(select(func.count()).select_from(WgsIntakeScannerState)) == 1
