from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, WgsSubmissionDraft
from app.wgs_orchestration_service import build_fastq_snapshot, fastq_source_fingerprint
from app.wgs_submission_service import (
    approve_wgs_config,
    approve_wgs_execution,
    complete_draft,
    create_and_submit_run,
    create_draft,
    get_draft,
    submission_state,
    submit_draft,
    create_automatic_wgs_run,
)
from app.wgs_stage_contract import canonical_wgs_stage, wgs_stage_definition


class RecordingAirflow:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trigger_dag_run(self, dag_id, *, dag_run_id=None, conf=None):
        self.calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf})
        return self.calls[-1]


def test_staged_prepare_steps_use_explicit_public_labels() -> None:
    assert wgs_stage_definition("prepare_sampleinfo").label == "Preparing sample information"
    assert wgs_stage_definition("prepare_analysis").label == "Preparing WGS analysis"
    assert canonical_wgs_stage("wait_prepare_wgs_sampleinfo", "running") == "prepare_sampleinfo"
    assert canonical_wgs_stage("wait_prepare_wgs_analysis", "running") == "prepare_analysis"


def test_direct_submission_binds_production_wgs_4_1_1_batch(tmp_path: Path) -> None:
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
            batch="20260902A",
            fastq_root_id="T7_Fastq",
        )
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == result["analysis_id"]))
        assert run is not None
        params = dict(run.params_json)

    assert params["batch_no"] == "WGS_20260902A_T7Hg38V4.1.1"
    assert params["sequencing_batch"] == "20260902A"
    assert params["analysis_batch"] == "20260902A"
    assert params["submission_mode"] == "three_stage"
    assert params["submission_phase"] == "preparing_sampleinfo"
    assert params["config_approved_at"] is None
    assert params["execution_approved_at"] is None
    assert "algo" not in params
    assert params["pipeline_release_id"] == "wgs-4.1.1-6c98281"
    assert airflow.calls[0]["dag_id"] == "bio_wgs"
    assert airflow.calls[0]["dag_run_id"] == f"{result['analysis_id']}-a1"


def test_step1_canary_scope_is_frozen_into_airflow_conf(tmp_path: Path) -> None:
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
            username="admin",
            project_id="WGS_Clinical",
            platform="T7",
            batch="20260902A",
            fastq_root_id="T7_Fastq",
            validation_scope="step1_only",
        )
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == result["analysis_id"])
        )
        assert run is not None
        assert run.params_json["validation_scope"] == "step1_only"
        assert run.params_json["sequencing_batch"] == "20260902A"
        assert run.params_json["analysis_batch"] == "20260902A_STEP1_CANARY"
        assert (
            run.params_json["batch_no"]
            == "WGS_20260902A_STEP1_CANARY_T7Hg38V4.1.1"
        )

    assert airflow.calls[0]["conf"]["params"]["validation_scope"] == "step1_only"


def test_step1_canary_uses_an_isolated_analysis_batch(tmp_path: Path) -> None:
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
        create_and_submit_run(
            session=session,
            settings=settings,
            airflow_client=airflow,
            username="operator",
            project_id="WGS_Clinical",
            platform="T7",
            batch="20260902A",
            fastq_root_id="T7_Fastq",
        )
        canary = create_and_submit_run(
            session=session,
            settings=settings,
            airflow_client=airflow,
            username="admin",
            project_id="WGS_Clinical",
            platform="T7",
            batch="20260902A",
            fastq_root_id="T7_Fastq",
            validation_scope="step1_only",
        )
        runs = list(session.scalars(select(AnalysisRun).order_by(AnalysisRun.id)))

    assert len(runs) == 2
    assert canary["analysis_id"] != runs[0].analysis_id
    assert runs[0].params_json["analysis_batch"] == "20260902A"
    assert runs[1].params_json["analysis_batch"] == "20260902A_STEP1_CANARY"


def test_automatic_submission_is_preapproved_and_never_restarts_a_failed_run(
    tmp_path: Path,
) -> None:
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
        first = create_automatic_wgs_run(
            session=session,
            settings=settings,
            airflow_client=airflow,
            username="wgs-intake-scanner",
            project_id="WGS_Clinical",
            platform="T7",
            batch="20260904A",
            fastq_root_id="T7_Fastq",
        )
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == first["analysis_id"])
        )
        assert run is not None
        assert run.params_json["submission_mode"] == "auto_dispatch"
        assert run.params_json["submission_phase"] == "approved"
        assert run.params_json["config_approved_at"]
        assert run.params_json["execution_approved_at"]
        run.status = "failed"
        session.commit()

        second = create_automatic_wgs_run(
            session=session,
            settings=settings,
            airflow_client=airflow,
            username="wgs-intake-scanner",
            project_id="WGS_Clinical",
            platform="T7",
            batch="20260904A",
            fastq_root_id="T7_Fastq",
        )

    assert second["analysis_id"] == first["analysis_id"]
    assert second["attempt"] == 1
    assert len(airflow.calls) == 1


def test_resubmitting_a_failed_catalog_batch_creates_a_new_attempt(tmp_path: Path) -> None:
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
        first = create_and_submit_run(
            session=session,
            settings=settings,
            airflow_client=airflow,
            username="operator",
            project_id="WGS_Clinical",
            platform="T7",
            batch="20260902A",
            fastq_root_id="T7_Fastq",
        )
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == first["analysis_id"])
        )
        assert run is not None
        run.status = "failed"
        run.ended_at = datetime.now(timezone.utc)
        run.pipeline_finished_at = datetime.now(timezone.utc)
        run.error_summary = "stale attempt failed"
        session.commit()

        second = create_and_submit_run(
            session=session,
            settings=settings,
            airflow_client=airflow,
            username="operator",
            project_id="WGS_Clinical",
            platform="T7",
            batch="20260902A",
            fastq_root_id="T7_Fastq",
        )
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == first["analysis_id"])
        )
        assert run is not None

    assert second["analysis_id"] == first["analysis_id"]
    assert second["attempt"] == 2
    assert second["dag_run_id"] == f"{first['analysis_id']}-a2"
    assert [call["dag_run_id"] for call in airflow.calls] == [
        f"{first['analysis_id']}-a1",
        f"{first['analysis_id']}-a2",
    ]
    assert run.params_json["submission_phase"] == "preparing_sampleinfo"
    assert run.error_summary is None
    assert run.ended_at is None
    assert run.pipeline_finished_at is None


def test_three_stage_approvals_are_server_controlled_and_idempotent(tmp_path: Path) -> None:
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
        created = create_and_submit_run(
            session=session,
            settings=settings,
            airflow_client=airflow,
            username="operator",
            project_id="WGS_Clinical",
            platform="T7",
            batch="20260902A",
            fastq_root_id="T7_Fastq",
        )
        analysis_id = str(created["analysis_id"])
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        assert run is not None
        run.params_json = {**run.params_json, "submission_phase": "config_review"}
        session.commit()

        first = approve_wgs_config(
            session=session,
            analysis_id=analysis_id,
            requested_by="operator",
            use_reference="ref",
            resource_set="default",
        )
        second = approve_wgs_config(
            session=session,
            analysis_id=analysis_id,
            requested_by="operator",
            use_reference="ref",
            resource_set="default",
        )
        assert first == second
        assert submission_state(session=session, analysis_id=analysis_id, attempt=1)["config_approved"] is True

        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        run.params_json = {**run.params_json, "submission_phase": "execution_review"}
        session.commit()
        assert approve_wgs_config(
            session=session,
            analysis_id=analysis_id,
            requested_by="operator",
            use_reference="ref",
            resource_set="default",
        )["config_approved"] is True
        with pytest.raises(ValueError, match="no prepared samples"):
            approve_wgs_execution(
                session=session,
                analysis_id=analysis_id,
                requested_by="operator",
            )


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
