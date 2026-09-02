from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, WgsSubmissionDraft
from app.wgs_orchestration_service import build_fastq_snapshot, fastq_source_fingerprint
from app.wgs_submission_service import complete_draft, create_and_submit_run, create_draft, get_draft, submit_draft


class RecordingAirflow:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trigger_dag_run(self, dag_id, *, dag_run_id=None, conf=None):
        self.calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf})
        return self.calls[-1]


def test_direct_submission_binds_wgs_4_2_batch_and_algorithm(tmp_path: Path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    settings = SimpleNamespace(
        wgs_project_catalog_path=str(Path(__file__).parents[2] / "config" / "wgs_projects.yaml"),
        wgs_release_catalog_path=str(Path(__file__).parents[2] / "config" / "wgs_releases.yaml"),
        host_results_root=str(tmp_path / "results"),
        container_shared_root=str(tmp_path / "shared"),
    )
    airflow = RecordingAirflow()

    with sessions() as session:
        result = create_and_submit_run(
            session=session,
            settings=settings,
            airflow_client=airflow,
            username="operator",
            project_id="WGS_Clinical",
            platform="T7",
            sequencing_batch="20260902A",
            analysis_batch="20260902A",
            fastq_root_id="T7_Fastq",
            use_reference="all",
            algo="Haplotyper",
        )
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == result["analysis_id"]))
        assert run is not None
        params = dict(run.params_json)

    assert params["batch_no"] == "WGS_20260902A_T7Hg38V4.2.0"
    assert params["analysis_batch"] == "20260902A"
    assert params["algo"] == "Haplotyper"
    assert params["pipeline_release_id"] == "wgs-4.2.0-7879718"
    assert airflow.calls[0]["dag_id"] == "bio_wgs"


def test_draft_preview_is_private_and_does_not_create_analysis_run(tmp_path: Path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    controlled = tmp_path / "intake"
    prepared = controlled / "drafts" / "D1"
    prepared.mkdir(parents=True)
    settings = SimpleNamespace(
        wgs_project_catalog_path=str(Path(__file__).parents[2] / "config" / "wgs_projects.yaml"),
        wgs_submission_draft_root=str(tmp_path / "draft-work"),
        wgs_submission_draft_ttl_hours=24,
        wgs_config_roots=[str(controlled)],
    )
    with sessions() as session:
        payload = create_draft(
            session=session,
            settings=settings,
            owner_username="operator",
            project_id="WGS_Clinical",
            platform="T7",
            sequencing_batch="20260901A",
            analysis_batch="WGS_20260901A_T7Hg38V4.1.1",
            fastq_root_id="T7_Fastq",
            use_reference=True,
        )
        assert payload["status"] == "queued"
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 0
        completed = complete_draft(
            session=session,
            settings=settings,
            draft_id=payload["draft_id"],
            prepared_fq_path=str(prepared),
            samples=[{
                "sample_id": "WGS001",
                "family_id": "F001",
                "r1_filename": "WGS001-WGS.R1.fq.gz",
                "r2_filename": "WGS001-WGS.R2.fq.gz",
                "patient_name": "must not leave the private draft",
                "hospital": "must not leave the private draft",
            }],
            families=[{"family_id": "F001", "sample_count": 1, "diagnosis": "private"}],
            resolved_config={"profile_id": "wgs-4.1.1", "resource_set": "production", "raw_yaml": "secret"},
            source_fingerprint="a" * 64,
        )
        assert completed is not None
        assert completed["status"] == "preview_ready"
        assert completed["preview"]["samples"][0] == {
            "sample_id": "WGS001",
            "family_id": "F001",
            "r1_filename": "WGS001-WGS.R1.fq.gz",
            "r2_filename": "WGS001-WGS.R2.fq.gz",
        }
        assert completed["preview"]["families"] == [{"family_id": "F001", "sample_count": 1}]
        assert completed["resolved_config"] == {"use_reference": True, "profile_id": "wgs-4.1.1", "resource_set": "production"}
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 0
        row = session.scalar(select(WgsSubmissionDraft))
        assert "patient_name" not in str(row.preview_json)
        assert get_draft(session=session, draft_id=payload["draft_id"], username="viewer") is None


def test_final_submit_rejects_expired_or_changed_preview(tmp_path: Path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    controlled = tmp_path / "intake"
    source = tmp_path / "source"
    controlled.mkdir()
    source.mkdir()
    for read in ("R1", "R2"):
        target = source / f"S1_{read}.fastq.gz"
        target.write_bytes(read.encode())
        (controlled / target.name).symlink_to(target)
    settings = SimpleNamespace(
        wgs_project_catalog_path=str(Path(__file__).parents[2] / "config" / "wgs_projects.yaml"),
        wgs_submission_draft_root=str(tmp_path / "draft-work"),
        wgs_submission_draft_ttl_hours=24,
        wgs_config_roots=[str(controlled)],
        wgs_fastq_roots=[str(source)],
    )
    with sessions() as session:
        payload = create_draft(
            session=session,
            settings=settings,
            owner_username="operator",
            project_id="WGS_Clinical",
            platform="T7",
            sequencing_batch="20260901A",
            analysis_batch="WGS_20260901A_T7Hg38V4.1.1",
            fastq_root_id="T7_Fastq",
            use_reference=False,
        )
        snapshot = build_fastq_snapshot(
            fq_path=str(controlled),
            allowed_link_roots=[str(controlled)],
            allowed_fastq_roots=[str(source)],
            manifest_path=tmp_path / "preview.json",
        )
        complete_draft(
            session=session,
            settings=settings,
            draft_id=payload["draft_id"],
            prepared_fq_path=str(controlled),
            samples=[],
            families=[],
            resolved_config={},
            source_fingerprint=fastq_source_fingerprint(snapshot),
        )
        row = session.scalar(select(WgsSubmissionDraft))
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
        with pytest.raises(ValueError, match="expired"):
            submit_draft(
                session=session,
                settings=settings,
                airflow_client=object(),
                draft_id=payload["draft_id"],
                username="operator",
                idempotency_key="expired-draft",
            )
        row.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        (source / "S1_R1.fastq.gz").write_bytes(b"changed")
        session.commit()
        with pytest.raises(ValueError, match="fingerprint changed"):
            submit_draft(
                session=session,
                settings=settings,
                airflow_client=object(),
                draft_id=payload["draft_id"],
                username="operator",
                idempotency_key="changed-draft",
            )
