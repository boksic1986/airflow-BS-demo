from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, RunAction, Sample, WgsSubmissionDraft
from app import wgs_platform_service
from app.wgs_orchestration_service import build_fastq_snapshot, fastq_source_fingerprint
from app.wgs_project_catalog import load_wgs_projects, public_project_catalog
from app.wgs_submission_service import (
    approve_wgs_config,
    approve_wgs_execution,
    complete_draft,
    create_and_submit_run,
    create_draft,
    get_draft,
    mark_submission_dag_failed,
    submission_state,
    submit_draft,
    create_automatic_wgs_run,
)
from app.wgs_platform_service import WgsPreparedArtifactPending, sync_prepared_samples
from app.wgs_stage_contract import canonical_wgs_stage, wgs_stage_definition


class RecordingAirflow:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trigger_dag_run(self, dag_id, *, dag_run_id=None, conf=None):
        self.calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf})
        return self.calls[-1]


def test_dag_failure_marks_staged_submission_failed_once(tmp_path: Path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    analysis_id = "WGS_20260907_044653_9C8591"

    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                dag_run_id=f"{analysis_id}-a1",
                attempt=1,
                status="submitted",
                workdir=str(tmp_path / analysis_id),
                params_json={
                    "submission_mode": "three_stage",
                    "submission_phase": "preparing_sampleinfo",
                },
            )
        )
        session.commit()

        first = mark_submission_dag_failed(
            session=session,
            analysis_id=analysis_id,
            attempt=1,
            failed_task_ids=["release_leases", "prepare_wgs_sampleinfo"],
        )
        first_ended_at = session.scalar(
            select(AnalysisRun.ended_at).where(AnalysisRun.analysis_id == analysis_id)
        )
        second = mark_submission_dag_failed(
            session=session,
            analysis_id=analysis_id,
            attempt=1,
            failed_task_ids=["prepare_wgs_sampleinfo"],
        )

        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        actions = session.scalars(
            select(RunAction).where(
                RunAction.analysis_id == analysis_id,
                RunAction.action == "airflow_dag_failed",
            )
        ).all()

    assert first["status"] == "failed"
    assert first["submission_phase"] == "failed"
    assert first["failed_task_ids"] == ["prepare_wgs_sampleinfo"]
    assert second == first
    assert run is not None
    assert run.status == "failed"
    assert run.ended_at is not None
    assert run.ended_at == first_ended_at
    assert run.pipeline_finished_at == first_ended_at
    assert run.params_json["submission_phase"] == "failed"
    assert "prepare_wgs_sampleinfo" in str(run.error_summary)
    assert len(actions) == 1


def test_dag_failure_reasserts_terminal_state_after_cleared_task_fails_again(
    tmp_path: Path,
) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    analysis_id = "WGS_20260907_044653_9C8591"

    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                dag_run_id=f"{analysis_id}-a2",
                attempt=2,
                status="running",
                current_stage="step1_upload",
                workdir=str(tmp_path / analysis_id),
                params_json={
                    "submission_mode": "three_stage",
                    "submission_phase": "executing",
                },
            )
        )
        session.commit()

        first = mark_submission_dag_failed(
            session=session,
            analysis_id=analysis_id,
            attempt=2,
            failed_task_ids=["input_transfer.wait_step1_upload"],
        )
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        assert run is not None
        run.status = "running"
        run.current_stage = "step2_master"
        run.error_summary = None
        session.commit()

        second = mark_submission_dag_failed(
            session=session,
            analysis_id=analysis_id,
            attempt=2,
            failed_task_ids=["submit_step2_master"],
        )
        actions = list(
            session.scalars(
                select(RunAction)
                .where(
                    RunAction.analysis_id == analysis_id,
                    RunAction.action == "airflow_dag_failed",
                )
                .order_by(RunAction.id)
            ).all()
        )

    assert first["failed_task_ids"] == ["input_transfer.wait_step1_upload"]
    assert second["failed_task_ids"] == ["submit_step2_master"]
    assert second["status"] == "failed"
    assert run.status == "failed"
    assert run.params_json["submission_phase"] == "failed"
    assert "submit_step2_master" in str(run.error_summary)
    assert [item.payload_json["failed_task_ids"] for item in actions] == [
        ["input_transfer.wait_step1_upload"],
        ["submit_step2_master"],
    ]


def test_dag_failure_rejects_wrong_attempt_and_preserves_success(tmp_path: Path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    analysis_id = "WGS_20260907_050000_ABCDEF"

    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                dag_run_id=f"{analysis_id}-a2",
                attempt=2,
                status="success",
                workdir=str(tmp_path / analysis_id),
                params_json={
                    "submission_mode": "three_stage",
                    "submission_phase": "approved",
                },
            )
        )
        session.commit()

        with pytest.raises(ValueError, match="unknown active WGS attempt"):
            mark_submission_dag_failed(
                session=session,
                analysis_id=analysis_id,
                attempt=1,
                failed_task_ids=["prepare_wgs_sampleinfo"],
            )

        preserved = mark_submission_dag_failed(
            session=session,
            analysis_id=analysis_id,
            attempt=2,
            failed_task_ids=["release_leases"],
        )
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )

    assert preserved["status"] == "success"
    assert run is not None and run.status == "success"


def test_prepared_binding_visibility_race_is_retryable(tmp_path: Path, monkeypatch) -> None:
    def missing_binding(**_kwargs):
        raise wgs_platform_service.WgsBindingPathError(
            "WGS frozen batch binding is unavailable"
        )

    monkeypatch.setattr(wgs_platform_service, "load_wgs_runtime_binding", missing_binding)

    with pytest.raises(WgsPreparedArtifactPending, match="binding is not visible"):
        sync_prepared_samples(
            session=None,
            settings=SimpleNamespace(
                wgs_runtime_request_root=tmp_path / "requests",
                wgs_runtime_run_root=tmp_path / "runs",
            ),
            run=SimpleNamespace(analysis_id="WGS_20260906_123456_A1B2C3", attempt=1),
        )


def test_staged_prepare_steps_use_explicit_public_labels() -> None:
    assert wgs_stage_definition("prepare_sampleinfo").label == "Preparing sample information"
    assert wgs_stage_definition("prepare_analysis").label == "Preparing WGS analysis"
    assert canonical_wgs_stage("wait_prepare_wgs_sampleinfo", "running") == "prepare_sampleinfo"
    assert canonical_wgs_stage("wait_prepare_wgs_analysis", "running") == "prepare_analysis"


def test_direct_submission_binds_production_wgs_4_2_0_batch(tmp_path: Path) -> None:
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

    assert params["batch_no"] == "WGS_20260902A_T7Hg38V4.2.0"
    assert params["sequencing_batch"] == "20260902A"
    assert params["analysis_batch"] == "20260902A"
    assert params["submission_mode"] == "three_stage"
    assert params["submission_phase"] == "preparing_sampleinfo"
    assert params["config_approved_at"] is None
    assert params["execution_approved_at"] is None
    assert "algo" not in params
    assert params["pipeline_release_id"] == "wgs-4.2.0-b067c72"
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
        assert run.params_json["analysis_batch"] == "20260902A_STEP1_SDK_CANARY"
        assert (
            run.params_json["batch_no"]
            == "WGS_20260902A_STEP1_SDK_CANARY_T7Hg38V4.2.0"
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
    assert runs[1].params_json["analysis_batch"] == "20260902A_STEP1_SDK_CANARY"


def test_step3_dryrun_uses_an_isolated_analysis_batch(tmp_path: Path) -> None:
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
            fastq_root_id="T7_Step3_Dryrun_Canary",
            validation_scope="step3_dryrun",
        )

    assert result["params"]["validation_scope"] == "step3_dryrun"
    assert result["params"]["analysis_batch"] == "20260902A_STEP3_DRYRUN_CANARY"
    assert airflow.calls[0]["conf"]["params"]["validation_scope"] == "step3_dryrun"


def test_node97_full_canary_uses_hidden_isolated_analysis_batch(tmp_path: Path) -> None:
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
            batch="20260825A",
            fastq_root_id="T7_Node97_Full_Canary",
            validation_scope="node97_full",
        )

    assert result["params"]["validation_scope"] == "node97_full"
    assert result["params"]["analysis_batch"] == "20260825A_NODE97_FULL_CANARY"
    assert airflow.calls[0]["conf"]["params"]["validation_scope"] == "node97_full"


def test_step3_dryrun_requires_hidden_validation_fastq_root(tmp_path: Path) -> None:
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
        with pytest.raises(ValueError, match="validation FASTQ root"):
            create_and_submit_run(
                session=session,
                settings=settings,
                airflow_client=airflow,
                username="admin",
                project_id="WGS_Clinical",
                platform="T7",
                batch="20260902A",
                fastq_root_id="T7_Fastq",
                validation_scope="step3_dryrun",
            )


def test_public_catalog_hides_validation_only_fastq_roots() -> None:
    projects = load_wgs_projects(Path(__file__).parents[2] / "config" / "wgs_projects.yaml")

    payload = public_project_catalog(projects)

    roots = payload["items"][0]["fastq_roots"]
    assert [root["root_id"] for root in roots] == ["T7_Fastq"]


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
        run.params_json = {**run.params_json, "submission_phase": "config_review"}
        session.commit()
        replayed = approve_wgs_config(
            session=session,
            analysis_id=analysis_id,
            requested_by="operator",
            use_reference="ref",
            resource_set="default",
        )
        assert replayed["submission_phase"] == "preparing_analysis"

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

        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="RETRY-SAMPLE",
                status="pending",
            )
        )
        stale_approval = "2026-09-06T12:00:00+00:00"
        run.params_json = {
            **run.params_json,
            "submission_phase": "execution_review",
            "execution_approved_at": stale_approval,
        }
        session.commit()

        approved = approve_wgs_execution(
            session=session,
            analysis_id=analysis_id,
            requested_by="operator",
        )

        assert approved["submission_phase"] == "approved"
        session.refresh(run)
        assert run.params_json["execution_approved_at"] != stale_approval


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
