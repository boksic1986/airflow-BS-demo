"""Backend-first registration; synthetic projects, real auth and disposable DB."""
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.auth_service import create_session, create_user
from app.models import AnalysisRun, Base, Sample
from app.wgs_platform_service import action_wgs_run, submit_wgs_run


@pytest.fixture
def context(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    settings = SimpleNamespace(
        auth_required=True, internal_service_token="synthetic-internal",
        wgs_onprem_registration_enabled=True, wgs_platform_instance_id="test-instance",
        wgs_onprem_project_roots=[str(tmp_path)], deployed_pipelines=("wgs",),
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: factory)
    # Registration must not even initialize the Airflow transport.
    monkeypatch.setattr(main, "get_airflow_client", lambda: pytest.fail("registration contacted Airflow"))
    with factory() as session:
        create_user(session=session, username="hanjj", password="synthetic-only-password", role="operator")
        user, token = create_session(session=session, username="hanjj", password="synthetic-only-password")
    client = TestClient(main.app)
    client.cookies.set(main.SESSION_COOKIE, token)
    client.headers["X-CSRF-Token"] = user.csrf_token
    project = tmp_path / "SYN_PROJECT"
    (project / ".wgs-platform").mkdir(parents=True)
    data = dict(
        schema_version="wgs.onprem-project-registration.v1", project_uuid=str(uuid4()),
        platform_instance_id="test-instance", project_dir=str(project), batch_name="SYN_BATCH",
        execution_mode="local", execution_target="node-96",
        prepare_summary=dict(selected_count=2, pending_count=1, version="V4.2.1",
            source_commit=None, prepared_at="2026-09-15T10:00:00+08:00",
            files={name: dict(relative_path=filename, sha256="a" * 64) for name, filename in
                   [("config", "config.yaml"), ("sampleinfo", "SYN.sampleinfo.txt"), ("step1", "Step1_run.sh")]}),
    )
    write_binding(data)
    yield client, factory, settings, data
    client.close()
    engine.dispose()


def write_binding(data):
    (Path(data["project_dir"]) / ".wgs-platform/project.json").write_text(json.dumps({
        "schema_version": "wgs.platform-project.v1", "project_uuid": data["project_uuid"],
        "platform_instance_id": data["platform_instance_id"],
    }))


def test_register_without_web_run_is_idempotent_and_same_path_new_project_is_distinct(context):
    client, factory, settings, data = context
    response = client.post("/api/wgs/onprem/projects", json=data)
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["status"] == "created" and first["execution_status"] == "not_started"
    assert client.post("/api/wgs/onprem/projects", json=data).json() == first
    changed = {**data, "prepare_summary": {**data["prepare_summary"], "selected_count": 9}}
    assert client.post("/api/wgs/onprem/projects", json=changed).status_code == 409
    new = {**data, "project_uuid": str(uuid4())}
    write_binding(new)
    second = client.post("/api/wgs/onprem/projects", json=new)
    assert second.status_code == 200, second.text
    assert second.json()["analysis_id"] != first["analysis_id"]
    with factory() as session:
        runs = list(session.scalars(select(AnalysisRun)))
        assert len(runs) == 2
        assert all(r.submitted_by == "hanjj" and r.dag_run_id is None and r.started_at is None for r in runs)
        assert session.scalar(select(func.count()).select_from(Sample)) == 0
        for action in ("resume", "rerun_failed", "cancel"):
            with pytest.raises(ValueError, match="monitor"):
                action_wgs_run(session=session, settings=settings, airflow_client=None,
                    analysis_id=first["analysis_id"], action=action, requested_by="hanjj")
        with pytest.raises(ValueError, match="monitor"):
            submit_wgs_run(session=session, airflow_client=None, analysis_id=first["analysis_id"])


@pytest.mark.parametrize("fault,expected", [("disabled", 409), ("instance", 409),
    ("target", 422), ("outside", 400), ("binding", 409), ("empty", 422)])
def test_registration_rejects_invalid_input_without_creating_run(context, tmp_path, fault, expected):
    client, factory, settings, data = context
    if fault == "disabled": settings.wgs_onprem_registration_enabled = False
    elif fault == "instance": data["platform_instance_id"] = "another-instance"
    elif fault == "target": data["execution_target"] = "sge-default"
    elif fault == "outside": settings.wgs_onprem_project_roots = [str(tmp_path / "other")]
    elif fault == "binding": data["project_uuid"] = str(uuid4())
    elif fault == "empty": data["prepare_summary"]["selected_count"] = 0
    response = client.post("/api/wgs/onprem/projects", json=data)
    assert response.status_code == expected, response.text
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 0


def test_registration_requires_personal_authenticated_session_and_csrf(context):
    client, factory, settings, data = context
    client.headers.pop("X-CSRF-Token")
    assert client.post("/api/wgs/onprem/projects", json=data).status_code == 403
    client.cookies.clear()
    assert client.post("/api/wgs/onprem/projects", json=data).status_code == 401
    client.headers["X-Airflow-Demo-Token"] = "synthetic-internal"
    assert client.post("/api/wgs/onprem/projects", json=data).status_code == 403
    settings.auth_required = False
    assert client.post("/api/wgs/onprem/projects", json=data).status_code == 403
