from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import (
    AnalysisRun,
    AuditLog,
    Base,
    WgsInputSnapshot,
    WgsLifecycleStatus,
    WgsMaintenanceAction,
)
from app.wgs_lifecycle_service import (
    LifecycleConflict,
    project_wgs_lifecycle,
    project_wgs_lifecycles,
    update_wgs_lifecycle_status,
)


def _sessions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _run(
    session,
    *,
    analysis_id="WGS_20260907_010203_A1B2C3",
    execution_mode="cce",
    fq_path="/controlled/fastq",
):
    run = AnalysisRun(
        analysis_id=analysis_id,
        pipeline_name="wgs",
        dag_id="bio_wgs",
        execution_mode=execution_mode,
        attempt=1,
        status="success",
        workdir=f"/runs/{analysis_id}",
        params_json={"analysis_batch": "20260907A"},
        pipeline_finished_at=datetime(2026, 9, 7, 1, 2, 3, tzinfo=timezone.utc),
    )
    session.add(run)
    session.add(
        WgsInputSnapshot(
            analysis_id=analysis_id,
            attempt=1,
            batch_no="20260907A",
            fq_path=fq_path,
            manifest_path=f"/runs/{analysis_id}/input-manifest.json",
            manifest_sha256="a" * 64,
            status="verified",
        )
    )
    session.flush()
    return run


def test_projection_keeps_workflow_cloud_release_backup_and_downstream_independent():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        session.add(
            WgsMaintenanceAction(
                action_id="step7-1",
                analysis_id=run.analysis_id,
                attempt=1,
                action_type="cleanup_step7_sfs",
                status="failed",
                requested_by="admin",
                error_message="cleanup failed",
            )
        )
        session.commit()

        lifecycle = project_wgs_lifecycle(session=session, run=run)

        assert lifecycle["workflow"]["status"] == "success"
        assert lifecycle["cloud_release"]["status"] == "failed"
        assert lifecycle["raw_fastq_backup"]["status"] == "not_started"
        assert lifecycle["raw_fastq_backup"]["revision"] == 1
        assert lifecycle["downstream_release"]["status"] == "not_started"


def test_local_workflow_projects_cloud_release_as_not_applicable():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session, execution_mode="local")
        session.commit()

        lifecycle = project_wgs_lifecycle(session=session, run=run)

        assert lifecycle["workflow"]["status"] == "success"
        assert lifecycle["cloud_release"]["status"] == "not_applicable"


def test_admin_registration_uses_revision_and_writes_audit_without_paths():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        session.commit()

        updated = update_wgs_lifecycle_status(
            session=session,
            run=run,
            kind="raw_fastq_backup",
            attempt=1,
            status="running",
            expected_revision=1,
            message="Archive job accepted",
            updated_by="admin",
        )

        assert updated["status"] == "running"
        assert updated["revision"] == 2
        row = session.scalar(select(WgsLifecycleStatus))
        assert row.scope_type == "input_snapshot"
        assert row.scope_key == f"sha256:{'a' * 64}"
        audit = session.scalar(select(AuditLog))
        assert audit.action == "wgs.lifecycle.raw_fastq_backup.update"
        assert "path" not in str(audit.payload_json).lower()

        with pytest.raises(LifecycleConflict) as caught:
            update_wgs_lifecycle_status(
                session=session,
                run=run,
                kind="raw_fastq_backup",
                attempt=1,
                status="success",
                expected_revision=1,
                message=None,
                updated_by="admin",
            )
        assert caught.value.code == "STALE_LIFECYCLE_STATUS"
        assert row.status == "running"


def test_raw_backup_status_is_shared_by_reanalysis_of_same_snapshot():
    sessions = _sessions()
    with sessions() as session:
        first = _run(session, analysis_id="WGS_20260907_010203_A1B2C3")
        second = AnalysisRun(
            analysis_id="WGS_20260907_020304_D4E5F6",
            pipeline_name="wgs",
            dag_id="bio_wgs",
            execution_mode="cce",
            attempt=1,
            status="success",
            workdir="/runs/second",
            params_json={"analysis_batch": "20260907A"},
        )
        session.add(second)
        session.add(
            WgsInputSnapshot(
                analysis_id=second.analysis_id,
                attempt=1,
                batch_no="20260907A",
                fq_path="/controlled/fastq-copy",
                manifest_path="/runs/second/input-manifest.json",
                manifest_sha256="a" * 64,
                status="verified",
            )
        )
        session.commit()
        update_wgs_lifecycle_status(
            session=session,
            run=first,
            kind="raw_fastq_backup",
            attempt=1,
            status="success",
            expected_revision=1,
            message=None,
            updated_by="admin",
        )

        projected = project_wgs_lifecycle(session=session, run=second)

        assert projected["raw_fastq_backup"]["status"] == "success"
        assert session.scalar(select(WgsLifecycleStatus)).analysis_id == first.analysis_id


def test_downstream_release_is_scoped_to_analysis_attempt():
    sessions = _sessions()
    with sessions() as session:
        run = _run(session)
        session.commit()
        update_wgs_lifecycle_status(
            session=session,
            run=run,
            kind="downstream_release",
            attempt=1,
            status="pending",
            expected_revision=1,
            message="Awaiting report system confirmation",
            updated_by="admin",
        )
        run.attempt = 2
        session.commit()

        projected = project_wgs_lifecycle(session=session, run=run)

        assert projected["downstream_release"]["status"] == "not_started"


def test_dashboard_bulk_projection_keeps_shared_snapshot_and_local_semantics():
    sessions = _sessions()
    with sessions() as session:
        first = _run(session, analysis_id="WGS_20260907_010203_A1B2C3")
        local = _run(
            session,
            analysis_id="WGS_20260907_020304_D4E5F6",
            execution_mode="local",
            fq_path="/controlled/fastq-copy",
        )
        session.commit()
        update_wgs_lifecycle_status(
            session=session,
            run=first,
            kind="raw_fastq_backup",
            attempt=1,
            status="success",
            expected_revision=1,
            message=None,
            updated_by="admin",
        )

        projected = project_wgs_lifecycles(session=session, runs=[first, local])

        assert projected[first.analysis_id]["raw_fastq_backup"]["status"] == "success"
        assert projected[local.analysis_id]["raw_fastq_backup"]["status"] == "success"
        assert projected[local.analysis_id]["cloud_release"]["status"] == "not_applicable"
