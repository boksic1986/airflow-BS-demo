from datetime import timedelta
import pytest

from sqlalchemy import select

from app.models import AnalysisRun, WgsIntakeBatch, WgsExecutionDispatch
from app.wgs_auto_dispatch import dispatch_ready_wgs_intake
from test_wgs_auto_dispatch import RecordingAirflow, ready_row, sessionmaker_for_test, settings
from test_wgs_samplelist_intake import NOW


def test_samplelist_dispatch_requires_scan_gate(tmp_path):
    sessions = sessionmaker_for_test()
    config = settings(tmp_path, not_before=NOW - timedelta(minutes=1))
    config.wgs_intake_scan_enabled = False
    airflow = RecordingAirflow()
    with sessions() as session:
        row = ready_row(batch="20990101A", ready_at=NOW)
        row.discovery_mode = "samplelist_batches"
        row.project_id, row.platform_id, row.root_id = "WGS_Clinical", "T7", "T7_Fastq"
        session.add(row); session.commit()
        result = dispatch_ready_wgs_intake(session=session, settings=config, airflow_client=airflow, now=NOW)
        assert result["submitted"] == 0
        assert session.scalars(select(AnalysisRun)).all() == []


def test_unbound_ready_corruption_never_submits(tmp_path):
    sessions = sessionmaker_for_test()
    config = settings(tmp_path, not_before=NOW - timedelta(minutes=1))
    config.wgs_intake_scan_enabled = True
    with sessions() as session:
        session.add(WgsIntakeBatch(discovery_mode="samplelist_batches", project_id="WGS_Clinical",
            platform_id="T7", root_id="T7_Fastq", sequencing_batch="20990101A", state="ready", ready_at=NOW))
        session.commit()
        result = dispatch_ready_wgs_intake(session=session, settings=config, airflow_client=RecordingAirflow(), now=NOW)
        assert result["submitted"] == 0
        assert session.scalars(select(AnalysisRun)).all() == []


def test_linked_failed_run_is_never_replaced_by_newer_same_batch(tmp_path):
    sessions = sessionmaker_for_test()
    config = settings(tmp_path, not_before=NOW - timedelta(minutes=1))
    config.wgs_intake_scan_enabled = True
    with sessions() as session:
        for name, status, created in [("SYN_OLD", "failed", NOW-timedelta(days=1)), ("SYN_NEW", "running", NOW)]:
            session.add(AnalysisRun(analysis_id=name, pipeline_name="wgs", dag_id="bio_wgs", execution_mode="cce",
                status=status, workdir=str(tmp_path/name), created_at=created,
                params_json={"sequencing_batch": "20990101A", "project_id": "WGS_Clinical", "platform": "T7"}))
        row = ready_row(batch="20990101A", ready_at=NOW)
        row.analysis_id = "SYN_OLD"
        row.discovery_mode = "samplelist_batches"
        row.project_id, row.platform_id, row.root_id = "WGS_Clinical", "T7", "T7_Fastq"
        session.add(row); session.commit()
        dispatch_ready_wgs_intake(session=session, settings=config, airflow_client=RecordingAirflow(), now=NOW)
        assert row.analysis_id == "SYN_OLD"


def test_ready_scanned_batch_uses_custom_project_and_is_idempotent_with_manual(tmp_path):
    import yaml
    from app.wgs_samplelist_intake import scan_wgs_samplelist_intake
    from app.wgs_submission_service import create_and_submit_run
    from test_wgs_t7_intake import chip
    from test_wgs_samplelist_intake import export
    sessions = sessionmaker_for_test()
    config = settings(tmp_path, not_before=NOW - timedelta(minutes=1))
    config.wgs_intake_scan_enabled = True
    source, root = tmp_path / "lists", tmp_path / "fastq"
    source.mkdir(); root.mkdir()
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(yaml.safe_dump({"schema_version": 1, "projects": [{"project_id": "SYN-PROJECT", "project_name": "SYN-DISPLAY-NAME",
        "platforms": [{"platform_id": "T7"}], "fastq_roots": [{"root_id": "SYN-ROOT", "node200_path": str(root), "control_plane_path": str(root)}]}]}))
    config.wgs_project_catalog_path = str(catalog)
    def scan():
        return scan_wgs_samplelist_intake(session_factory=sessions, root=root, samplelist_root=source,
            project_id="SYN-PROJECT", platform_id="T7", root_id="SYN-ROOT", scan_enabled=True, now=NOW)
    scan()
    export(source / "Samplelist_new.txt", "20990101A")
    chip(root, "1th_20990101A_SYN", ready=True, files=("SYN001-WGS.R1.fq.gz", "SYN001-WGS.R2.fq.gz"))
    scan(); scan()
    airflow = RecordingAirflow()
    with sessions() as session:
        first = dispatch_ready_wgs_intake(session=session, settings=config, airflow_client=airflow, now=NOW)
        second = dispatch_ready_wgs_intake(session=session, settings=config, airflow_client=airflow, now=NOW)
        manual = create_and_submit_run(session=session, settings=config, airflow_client=airflow, username="synthetic",
            project_id="SYN-PROJECT", platform="T7", fastq_root_id="SYN-ROOT", batch="20990101A")
        run, = session.scalars(select(AnalysisRun)).all()
        assert first["submitted"] == 1
        assert second["already_registered"] == 1
        assert manual["analysis_id"] == run.analysis_id
        assert run.params_json["project_id"] == "SYN-PROJECT"
        assert run.params_json["fastq_root"] == str(root)
        assert session.scalar(select(WgsExecutionDispatch)).project_id == "SYN-PROJECT"
        assert len(airflow.calls) == 1


@pytest.mark.parametrize("scenario", ["other_root", "other_owner", "linked_other_root", "compatible", "late_other_owner", "late_failed_owner", "late_canceled_owner"])
def test_existing_automatic_run_requires_matching_root_and_exclusive_intake_owner(tmp_path, scenario, monkeypatch):
    import yaml
    from app.wgs_samplelist_intake import scan_wgs_samplelist_intake
    from app.wgs_submission_service import _catalog_run_spec, _create_catalog_run_record
    from test_wgs_t7_intake import chip
    from test_wgs_samplelist_intake import export
    sessions = sessionmaker_for_test()
    config = settings(tmp_path, not_before=NOW - timedelta(minutes=1))
    config.wgs_intake_scan_enabled = True
    root, other, source = tmp_path / "root-A", tmp_path / "root-B", tmp_path / "lists"
    root.mkdir(); other.mkdir(); source.mkdir()
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(yaml.safe_dump({"schema_version": 1, "projects": [{"project_id": "SYN-PROJECT",
        "platforms": [{"platform_id": "T7"}], "fastq_roots": [
            {"root_id": name, "node200_path": str(path), "control_plane_path": str(path)}
            for name, path in (("ROOT-A", root), ("ROOT-B", other))]}]}))
    config.wgs_project_catalog_path = str(catalog)
    def scan():
        scan_wgs_samplelist_intake(session_factory=sessions, root=root, samplelist_root=source,
            project_id="SYN-PROJECT", platform_id="T7", root_id="ROOT-A", now=NOW, scan_enabled=True)
    scan()
    export(source / "Samplelist_new.txt", "20990101A")
    chip(root, "1th_20990101A_SYN", ready=True, files=("SYN001-WGS.R1.fq.gz", "SYN001-WGS.R2.fq.gz"))
    scan(); scan()
    airflow = RecordingAirflow()
    with sessions() as session:
        row = session.scalar(select(WgsIntakeBatch))
        def create_existing():
            spec = _catalog_run_spec(settings=config, project_id="SYN-PROJECT", platform="T7", batch="20990101A",
                fastq_root_id="ROOT-B" if "other_root" in scenario else "ROOT-A", use_reference=None)
            run, _ = _create_catalog_run_record(session=session, settings=config, username="synthetic", spec=spec)
            run.params_json = {**run.params_json, "submission_mode": "auto_dispatch"}
            if scenario in {"late_failed_owner", "late_canceled_owner"}:
                run.status = "failed" if scenario == "late_failed_owner" else "cancelled"
            if scenario == "other_owner" or scenario.startswith("late_"):
                session.add(WgsIntakeBatch(source_path="/synthetic/legacy", chip_id="SYN-LEGACY", sequencing_batch="20990101A",
                    analysis_id=run.analysis_id, state="no_new_wgs"))
            elif scenario == "linked_other_root":
                row.analysis_id = run.analysis_id
            session.commit()
            return run
        captured = []
        if scenario.startswith("late_"):
            # Simulate publication after the dispatcher's initial runs snapshot,
            # retaining the real filesystem readiness and actual creation service.
            from app import wgs_auto_dispatch
            original_ready = wgs_auto_dispatch._bound_ready
            def publish_after_snapshot(intake_row, runtime_settings):
                if not captured:
                    captured.append(create_existing())
                return original_ready(intake_row, runtime_settings)
            monkeypatch.setattr(wgs_auto_dispatch, "_bound_ready", publish_after_snapshot)
        else:
            captured.append(create_existing())
        dispatch_ready_wgs_intake(session=session, settings=config, airflow_client=airflow, now=NOW)
        run, = captured
        if scenario == "compatible":
            assert row.analysis_id == run.analysis_id
            assert run.status == "submitted"
            assert len(airflow.calls) == 1
        else:
            assert run.status == {"late_failed_owner": "failed", "late_canceled_owner": "cancelled"}.get(scenario, "created")
            assert airflow.calls == []
            assert row.state == "needs_review"
            assert row.analysis_id == (run.analysis_id if scenario == "linked_other_root" else None)
            assert run.params_json.get("config_approved_at") is None
            assert run.params_json.get("execution_approved_at") is None
