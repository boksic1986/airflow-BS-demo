"""Native execution identity/snapshot checks; no controller or Airflow launch."""
import json
from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models import AnalysisRun, Sample, WgsStageExecution
from test_wgs_onprem_registration import context, write_binding


def inputs(project, sample="SYN_A", family="SYN_F1", caller="haplotyper"):
    project = Path(project)
    (project / "config.yaml").write_text(
        f"execution:\n  executor: local\nsample_info: samples.tsv\n"
        f"new_sample_info: selected.tsv\ncaller: {caller}\nsample: [{sample}]\n", encoding="utf-8")
    for filename in ("samples.tsv", "selected.tsv"):
        (project / filename).write_text(
            f"数据编号\t样本编号\t家系编号\n{sample}\tSYN_METADATA\t{family}\n"
            "SYN_UNSELECTED\tSYN_OTHER\tSYN_OTHER_FAMILY\n", encoding="utf-8")
    (project / "Step1_run.sh").write_text("#!/bin/bash\nexit 0\n")
    for mode in ("local", "sge"):
        profile = project / "pipeline" / "cfg" / "profiles" / mode
        profile.mkdir(parents=True, exist_ok=True)
        (profile / "config.yaml").write_text("jobs: 1\n")
        (profile / "runtime.yaml").write_text("resources: {}\n")


def setup_execution(context, tmp_path):
    client, factory, settings, data = context
    settings.wgs_onprem_snapshot_root = str(tmp_path / "private-snapshots")
    Path(settings.wgs_onprem_snapshot_root).mkdir(mode=0o700)
    inputs(data["project_dir"])
    result = client.post("/api/wgs/onprem/projects", json=data)
    assert result.status_code == 200, result.text
    body = dict(schema_version="wgs.onprem-execution-registration.v1",
        platform_instance_id="test-instance", operation_id=str(uuid4()),
        project_dir=data["project_dir"], execution_mode="local", execution_target="node-96",
        argv=["--", "--rerun-incomplete"], execution_user="synthetic-os-user", execution_uid=1234)
    return f"/api/wgs/onprem/projects/{data['project_uuid']}/executions", body, result.json()["analysis_id"]


def test_execution_retry_and_edited_resume_preserve_private_history(context, tmp_path):
    client, factory, settings, data = context
    url, body, analysis_id = setup_execution(context, tmp_path)
    first = client.post(url, json=body)
    assert first.status_code == 200, first.text
    first = first.json()
    assert first["generation"] == 1 and first["attempt"] == 1
    assert first["launch_allowed"] is False  # Candidate registration is not a controller.
    inputs(body["project_dir"], "SYN_RENAMED", "SYN_F2", "dnascope")
    assert client.post(url, json=body).json() == first  # Retry must not resnapshot mutable files.
    assert client.post(url, json={**body, "operation_id": str(uuid4())}).status_code == 409
    with factory() as session:
        stage = session.scalar(select(WgsStageExecution))
        assert stage.status == "accepted" and stage.started_at is None
        stage.status = "failed"  # Synthetic predecessor terminal evidence; not a live DB edit.
        session.commit()
    second = client.post(url, json={**body, "operation_id": str(uuid4())})
    assert second.status_code == 200, second.text
    second = second.json()
    assert second["analysis_id"] == analysis_id and second["attempt"] == 1
    assert second["generation"] == 2 and second["execution_id"] != first["execution_id"]
    from app.models import WgsOnpremExecutionSnapshot
    with factory() as session:
        snapshots = list(session.scalars(select(WgsOnpremExecutionSnapshot).order_by(WgsOnpremExecutionSnapshot.created_at)))
        assert [row.sample_scope_json for row in snapshots] == [
            [{"data_id": "SYN_A", "sample_id": "SYN_METADATA", "family_id": "SYN_F1"}],
            [{"data_id": "SYN_RENAMED", "sample_id": "SYN_METADATA", "family_id": "SYN_F2"}]]
        first_path = Path(snapshots[0].snapshot_path)
        assert "haplotyper" in (first_path / "config.yaml").read_text()
        assert "SYN_RENAMED" not in (first_path / "sample_info.tsv").read_text()
        manifest = json.loads((first_path / "manifest.json").read_text())
        assert manifest["registered_by"] == "hanjj"
        assert manifest["execution_user"] == "synthetic-os-user"
        assert manifest["execution_user_source"] == "reported_by_authenticated_launcher"
        assert first_path.stat().st_mode & 0o077 == 0
        assert (first_path / "config.yaml").stat().st_mode & 0o077 == 0
        assert session.scalar(select(func.count()).select_from(Sample)) == 0
        run = session.scalar(select(AnalysisRun))
        assert run.submitted_by == "hanjj" and run.dag_run_id is None and run.started_at is None


def test_project_move_same_path_reuse_and_duplicate_binding(context, tmp_path):
    client, factory, settings, data = context
    url, body, analysis_id = setup_execution(context, tmp_path)
    old = Path(body["project_dir"])
    moved = tmp_path / "SYN_MOVED"
    shutil.copytree(old, moved)
    assert client.post(url, json={**body, "project_dir": str(moved)}).status_code == 409
    # Reuse old pathname for another project, while P1 binding remains at moved.
    replacement = {**data, "project_uuid": str(uuid4())}
    write_binding(replacement)
    registered = client.post("/api/wgs/onprem/projects", json=replacement)
    assert registered.status_code == 200, registered.text
    assert registered.json()["analysis_id"] != analysis_id
    response = client.post(url, json={**body, "project_dir": str(moved)})
    assert response.status_code == 200, response.text
    assert response.json()["analysis_id"] == analysis_id
    with factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        assert run.workdir == str(moved)
        assert run.params_json["onprem_registration"]["project_dir"] == str(old)


@pytest.mark.parametrize("fault,expected", [("config_mode", 400), ("missing", 400),
    ("outside_reference", 400), ("secret", 400), ("target", 409), ("disabled", 409),
    ("scope_mismatch", 400), ("ambiguous_data_id", 400)])
def test_bad_execution_inputs_create_no_execution(context, tmp_path, fault, expected):
    client, factory, settings, data = context
    url, body, _ = setup_execution(context, tmp_path)
    project = Path(body["project_dir"])
    if fault == "config_mode":
        (project / "config.yaml").write_text((project / "config.yaml").read_text().replace("local", "sge"))
    elif fault == "missing": (project / "selected.tsv").unlink()
    elif fault == "outside_reference":
        (project / "selected.tsv").unlink()
        outside = tmp_path / "outside.tsv"
        outside.write_text("样本编号\t家系编号\nSYN_OTHER\tF\n", encoding="utf-8")
        (project / "selected.tsv").symlink_to(outside)
    elif fault == "secret": body["argv"] = ["--api-token=synthetic-secret"]
    elif fault == "target": body["execution_target"] = "node-97"
    elif fault == "disabled": settings.wgs_onprem_registration_enabled = False
    elif fault == "scope_mismatch":
        (project / "config.yaml").write_text((project / "config.yaml").read_text().replace("sample: [SYN_A]", "sample: [SYN_MISSING]"))
    elif fault == "ambiguous_data_id":
        text = (project / "samples.tsv").read_text(encoding="utf-8")
        (project / "samples.tsv").write_text(text + "SYN_A\tSYN_DIFFERENT\tSYN_F2\n", encoding="utf-8")
    response = client.post(url, json=body)
    assert response.status_code == expected, response.text
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(WgsStageExecution)) == 0


def test_execution_auth_and_operation_conflicts(context, tmp_path):
    client, factory, settings, data = context
    url, body, _ = setup_execution(context, tmp_path)
    response = client.post(url, json=body)
    assert response.status_code == 200, response.text
    assert client.post(url, json={**body, "argv": ["--", "all"]}).status_code == 409
    with factory() as session:
        session.scalar(select(AnalysisRun)).submitted_by = "another-operator"
        session.commit()
    assert client.post(url, json=body).status_code == 403
    client.headers.pop("X-CSRF-Token")
    assert client.post(url, json=body).status_code == 403
    client.cookies.clear()
    assert client.post(url, json=body).status_code == 401
    client.headers["X-Airflow-Demo-Token"] = "synthetic-internal"
    assert client.post(url, json=body).status_code == 403
