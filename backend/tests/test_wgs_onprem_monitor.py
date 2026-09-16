"""Generation-fenced native observation, without native launch or live Airflow."""
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import AnalysisRun, WgsStageExecution
from app import main
from test_wgs_onprem_registration import context
from test_wgs_onprem_launch import prepared_claim


@pytest.fixture(autouse=True)
def internal_token(monkeypatch):
    monkeypatch.setattr(main, 'get_internal_service_token', lambda: 'synthetic-internal')


def monitoring(context, tmp_path):
    client, factory, settings, data = context
    claim_url, body, receipt, _ = prepared_claim(context, tmp_path)
    grant = client.post(claim_url, json=body).json()
    settings.wgs_onprem_monitor_enabled = True
    client.headers['X-Airflow-Demo-Token'] = 'synthetic-internal'
    request = dict(attempt=receipt['attempt'], generation=receipt['generation'])
    url = f"/api/internal/wgs/onprem/runs/{receipt['analysis_id']}/executions/{receipt['execution_id']}/observe"
    log = Path(data['project_dir']) / 'log'
    log.mkdir()
    prefix = log / f"step1.{grant['native_execution_id']}"
    return url, request, prefix


def metadata(prefix, finished=False):
    content = ('hostname\tsynthetic-node\nrun_mode\tlocal\n'
               'started_at\t2026-09-15T10:00:00+0800\n'
               'command\tDO_NOT_STORE_SYNTHETIC_RAW_COMMAND\n')
    if finished:
        content += 'finished_at\t2026-09-15T11:00:00+0800\n'
    Path(str(prefix) + '.metadata.tsv').write_text(content)


def test_start_observed_but_workflow_marker_does_not_prove_controller_exit(context, tmp_path):
    client, factory, _, _ = context
    url, body, prefix = monitoring(context, tmp_path)
    assert client.post(url, json=body).json()['observation'] == 'awaiting_start'
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        run.progress_percent = 100
        run.error_summary = 'synthetic previous execution error'
        session.commit()
    metadata(prefix)
    started = client.post(url, json=body)
    assert started.status_code == 200, started.text
    assert started.json()['status'] == 'running'
    metadata(prefix, finished=True)
    Path(str(prefix) + '.exitcode').write_text('0\n')
    result = client.post(url, json=body).json()
    assert result['observation'] == 'native_result_reported'
    assert result['done'] is False and result['native_exitcode'] == 0
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        stage = session.scalar(select(WgsStageExecution))
        assert run.status == stage.status == 'running'
        assert stage.started_at is not None and stage.ended_at is None
        assert run.dag_run_id is None and run.ended_at is None
        assert run.progress_percent == 0 and run.error_summary is None
        assert 'DO_NOT_STORE' not in str(run.params_json)


@pytest.mark.parametrize('fault', ['missing', 'wrong_mode', 'replaced_project'])
def test_evidence_error_preserves_last_running_state(context, tmp_path, fault):
    client, factory, _, data = context
    url, body, prefix = monitoring(context, tmp_path)
    metadata(prefix)
    assert client.post(url, json=body).status_code == 200
    path = Path(str(prefix) + '.metadata.tsv')
    if fault == 'missing':
        path.unlink()
    elif fault == 'wrong_mode':
        path.write_text(path.read_text().replace('local', 'sge'))
    else:
        (Path(data['project_dir']) / '.wgs-platform/project.json').write_text('{}')
    result = client.post(url, json=body)
    assert result.status_code == 200, result.text
    assert result.json()['monitoring_health'] == 'degraded'
    with factory() as session:
        assert session.scalar(select(AnalysisRun)).status == 'running'
        assert session.scalar(select(WgsStageExecution)).status == 'running'


def test_stale_generation_and_missing_internal_auth_cannot_project(context, tmp_path, monkeypatch):
    client, factory, settings, _ = context
    url, body, prefix = monitoring(context, tmp_path)
    metadata(prefix)
    assert client.post(url, json={**body, 'generation': 999}).status_code == 409
    settings.wgs_onprem_monitor_enabled = False
    assert client.post(url, json=body).status_code == 409
    settings.wgs_onprem_monitor_enabled = True
    monkeypatch.setattr(main, 'get_internal_service_token', lambda: 'synthetic-internal')
    client.headers.pop('X-Airflow-Demo-Token')
    assert client.post(url, json=body).status_code in (401, 403)
    monkeypatch.setattr(main, 'get_internal_service_token', lambda: '')
    assert client.post(url, json=body).status_code in (401, 403)
    with factory() as session:
        assert session.scalar(select(WgsStageExecution)).status == 'launching'
