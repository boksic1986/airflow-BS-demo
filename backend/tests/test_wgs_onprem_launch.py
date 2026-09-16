"""One-shot native launch claims: real API/DB, no actual WGS execution."""
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import AnalysisRun, WgsStageExecution
from test_wgs_onprem_registration import context
from test_wgs_onprem_execution import setup_execution


def prepared_claim(context, tmp_path, mode="local", target="node-96"):
    client, factory, settings, data = context
    data.update(execution_mode=mode, execution_target=target)
    url, registration, analysis_id = setup_execution(context, tmp_path)
    registration.update(execution_mode=mode, execution_target=target)
    config = Path(data["project_dir"]) / "config.yaml"
    config.write_text(config.read_text().replace("executor: local", f"executor: {mode}"))
    response = client.post(url, json=registration)
    assert response.status_code == 200, response.text
    receipt = response.json()
    request = dict(platform_instance_id="test-instance", operation_id=registration["operation_id"],
                   generation=receipt["generation"], manifest_sha256=receipt["manifest_sha256"])
    settings.wgs_onprem_launch_enabled = True
    return f"/api/wgs/onprem/executions/{receipt['execution_id']}/claim", request, receipt, registration


@pytest.mark.parametrize("mode,target", [("local", "node-96"), ("local", "node-97"), ("sge", "sge-default")])
def test_native_claim_grants_only_once_without_claiming_process_started(context, tmp_path, mode, target):
    client, factory, settings, data = context
    url, body, receipt, registration = prepared_claim(context, tmp_path, mode, target)
    response = client.post(url, json=body)
    assert response.status_code == 200, response.text
    grant = response.json()
    assert grant["claim_granted"] is True
    assert grant["execution_id"] == receipt["execution_id"]
    assert grant["native_execution_id"] == f"{receipt['analysis_id']}-a1-g1-{receipt['execution_id']}"
    assert grant["execution_target"] == target
    assert client.post(url, json=body).status_code == 409
    register_url = f"/api/wgs/onprem/projects/{data['project_uuid']}/executions"
    assert client.post(register_url, json=registration).json() == receipt
    assert client.post(register_url, json={**registration, "operation_id": str(uuid4())}).status_code == 409
    with factory() as session:
        stage = session.scalar(select(WgsStageExecution))
        run = session.scalar(select(AnalysisRun))
        assert stage.status == "launching" and stage.started_at is None
        assert run.status == "created" and run.started_at is None and run.dag_run_id is None


@pytest.mark.parametrize("fault,expected", [("disabled",409), ("edited",409), ("profile_edited",409), ("identity",409),
                                          ("old_generation",409), ("owner",403)])
def test_invalid_claim_never_consumes_permission(context, tmp_path, fault, expected):
    client, factory, settings, data = context
    url, body, receipt, registration = prepared_claim(context, tmp_path)
    if fault == "disabled": settings.wgs_onprem_launch_enabled = False
    elif fault == "edited":
        path = Path(data["project_dir"]) / "config.yaml"
        path.write_text(path.read_text().replace("haplotyper", "dnascope"))
    elif fault == "profile_edited":
        path = Path(data["project_dir"]) / "pipeline/cfg/profiles/local/config.yaml"
        path.write_text("jobs: 2\n")
    elif fault == "identity": body["operation_id"] = str(uuid4())
    elif fault == "old_generation": body["generation"] = 999
    elif fault == "owner":
        with factory() as session:
            session.scalar(select(AnalysisRun)).submitted_by = "other-user"
            session.commit()
    response = client.post(url, json=body)
    assert response.status_code == expected, response.text
    with factory() as session:
        assert session.scalar(select(WgsStageExecution)).status == "accepted"


def test_claim_requires_personal_session_not_internal_service(context, tmp_path):
    client, factory, settings, data = context
    url, body, _, _ = prepared_claim(context, tmp_path)
    client.headers.pop("X-CSRF-Token")
    assert client.post(url, json=body).status_code == 403
    client.cookies.clear()
    assert client.post(url, json=body).status_code == 401
    client.headers["X-Airflow-Demo-Token"] = "synthetic-internal"
    assert client.post(url, json=body).status_code == 403


@pytest.mark.parametrize("argv", [["--", "--config", "sample=SYN_OTHER"],
    ["--", "--configfile=other.yaml"], ["--", "-sOther.smk"], ["--", "--prof", "other-profile"]])
def test_claim_rejects_overrides_of_frozen_native_inputs(context, tmp_path, argv):
    client, factory, settings, data = context
    _, _, _, registration = prepared_claim(context, tmp_path)
    # Close only the unlaunched synthetic fixture reservation and register distinct argv.
    with factory() as session:
        session.scalar(select(WgsStageExecution)).status = "canceled"
        session.commit()
    registration.update(operation_id=str(uuid4()), argv=argv)
    result = client.post(f"/api/wgs/onprem/projects/{data['project_uuid']}/executions", json=registration)
    assert result.status_code == 200, result.text
    receipt = result.json()
    body = dict(platform_instance_id="test-instance", operation_id=registration["operation_id"],
                generation=receipt["generation"], manifest_sha256=receipt["manifest_sha256"])
    response = client.post(f"/api/wgs/onprem/executions/{receipt['execution_id']}/claim", json=body)
    assert response.status_code == 400, response.text
    with factory() as session:
        current = session.scalar(select(WgsStageExecution).where(WgsStageExecution.execution_id == receipt["execution_id"]))
        assert current.status == "accepted"
