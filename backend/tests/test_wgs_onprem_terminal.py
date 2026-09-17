"""A waited controller receipt closes one execution, never another generation."""
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, func

from app import main
from app.models import AnalysisRun, Sample, WgsStageExecution
from test_wgs_onprem_registration import context
from test_wgs_onprem_launch import prepared_claim


def terminal_fixture(context, tmp_path, monkeypatch, mode='local', rc=0):
    client, factory, settings, data = context
    url, body, registered, registration = prepared_claim(
        context, tmp_path, mode, 'sge-default' if mode == 'sge' else 'node-96')
    grant = client.post(url, json=body).json()
    settings.wgs_onprem_monitor_enabled = True
    monkeypatch.setattr(main, 'get_internal_service_token', lambda: 'synthetic-internal')
    client.headers['X-Airflow-Demo-Token'] = 'synthetic-internal'
    path = Path(data['project_dir']) / '.wgs-platform/executions' / registered['execution_id'] / 'g1/controller-exit.json'
    path.parent.mkdir(parents=True)
    receipt = {key: grant[key] for key in (
        'analysis_id', 'attempt', 'execution_id', 'generation', 'operation_id',
        'native_execution_id', 'manifest_sha256', 'execution_mode', 'execution_target',
        'execution_user', 'execution_uid')}
    receipt.update(schema_version='wgs.onprem-controller-exit.v1',
        platform_instance_id='test-instance', project_uuid=data['project_uuid'],
        hostname='synthetic-node', started_at='2026-09-15T02:00:00+00:00',
        finished_at='2026-09-15T03:00:00+00:00', wait_returncode=rc,
        controller_exit_confirmed=True, evidence_method='direct_child_wait')
    path.write_text(json.dumps(receipt))
    observe = f"/api/internal/wgs/onprem/runs/{registered['analysis_id']}/executions/{registered['execution_id']}/observe"
    return observe, {'attempt': 1, 'generation': 1}, path, receipt, registration


@pytest.mark.parametrize('mode,rc,status,eligible', [
    ('local', 0, 'success', True), ('local', 2, 'failed', True),
    ('local', -15, 'failed', False), ('sge', 2, 'failed', False)])
def test_waited_exit_closes_current_execution_and_preserves_rerun_boundary(
        context, tmp_path, monkeypatch, mode, rc, status, eligible):
    client, factory, _, data = context
    url, body, path, receipt, registration = terminal_fixture(context, tmp_path, monkeypatch, mode, rc)
    result = client.post(url, json=body)
    assert result.status_code == 200, result.text
    assert result.json()['done'] is True
    assert result.json()['status'] == status
    assert result.json()['relaunch_eligible'] is eligible
    assert client.post(url, json=body).json()['status'] == status
    with factory() as session:
        stage = session.scalar(select(WgsStageExecution))
        run = session.scalar(select(AnalysisRun))
        assert stage.status == run.status == status and stage.ended_at is not None
        assert stage.receipt_hash and stage.terminal_payload_json['controller_exit']['wait_returncode'] == rc
        assert session.scalar(select(func.count()).select_from(Sample)) == 0
    client.headers.pop('X-Airflow-Demo-Token')  # Resume uses the personal operator, not observer auth.
    next_run = client.post(f"/api/wgs/onprem/projects/{data['project_uuid']}/executions",
                          json={**registration, 'operation_id': str(uuid4())})
    assert next_run.status_code == (200 if eligible else 409), next_run.text
    if eligible:
        assert next_run.json()['generation'] == 2
        client.headers['X-Airflow-Demo-Token'] = 'synthetic-internal'
        assert client.post(url, json=body).status_code == 409


@pytest.mark.parametrize('fault', ['wrong_generation', 'wrong_hash', 'partial'])
def test_invalid_receipt_does_not_release_launch_guard(context, tmp_path, monkeypatch, fault):
    client, factory, _, _ = context
    url, body, path, receipt, _ = terminal_fixture(context, tmp_path, monkeypatch)
    if fault == 'wrong_generation': receipt['generation'] = 8
    elif fault == 'wrong_hash': receipt['manifest_sha256'] = 'a' * 64
    path.write_text('{' if fault == 'partial' else json.dumps(receipt))
    result = client.post(url, json=body)
    assert result.status_code == 200, result.text
    assert result.json()['done'] is False and result.json()['monitoring_health'] == 'degraded'
    with factory() as session:
        assert session.scalar(select(WgsStageExecution)).status == 'launching'
