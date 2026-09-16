"""Real API/DB/client with an isolated Airflow HTTP transport, never real jobs."""
import json

import httpx
from sqlalchemy import select

from app import main
from app.airflow_client import AirflowClient
from app.models import AnalysisRun, WgsStageExecution
from test_wgs_onprem_registration import context
from test_wgs_onprem_launch import prepared_claim


def attachment(context, tmp_path, monkeypatch, handler):
    client, factory, settings, data = context
    claim_url, body, receipt, _ = prepared_claim(context, tmp_path)
    assert client.post(claim_url, json=body).status_code == 200
    settings.wgs_onprem_monitor_enabled = True
    airflow = AirflowClient(base_url='http://synthetic-airflow', username='synthetic',
                            password='synthetic', transport=httpx.MockTransport(handler))
    monkeypatch.setattr(main, 'get_airflow_client', lambda: airflow)
    return claim_url.removesuffix('/claim') + '/monitor', body, receipt


def test_attach_retry_uses_one_monitor_dag_and_never_starts_analysis(context, tmp_path, monkeypatch):
    calls = []
    def handler(request):
        payload = json.loads(request.content)
        calls.append((request.method, request.url.path, payload))
        return httpx.Response(200, json=payload)
    url, body, receipt = attachment(context, tmp_path, monkeypatch, handler)
    client, factory, settings, _ = context
    first = client.post(url, json=body)
    assert first.status_code == 200, first.text
    assert client.post(url, json=body).json() == first.json()
    assert len(calls) == 1
    assert calls[0] == ('POST', '/api/v1/dags/bio_wgs_native_monitor/dagRuns', {
        'dag_run_id': f"native__{receipt['execution_id']}",
        'conf': {'pipeline': 'wgs', 'monitor_only': True, 'analysis_id': receipt['analysis_id'],
                 'execution_id': receipt['execution_id'], 'attempt': 1, 'generation': 1}})
    with factory() as session:
        stage = session.scalar(select(WgsStageExecution))
        run = session.scalar(select(AnalysisRun))
        assert stage.status == 'launching' and stage.started_at is None
        assert run.status == 'created' and run.started_at is None
        assert run.dag_id == 'bio_wgs_native_monitor'
    settings.wgs_onprem_monitor_enabled = False
    assert client.post(url, json=body).status_code == 409


def test_lost_attach_response_reconciles_same_dag_without_new_claim(context, tmp_path, monkeypatch):
    accepted = {}
    calls = []
    def handler(request):
        calls.append(request.method)
        if request.method == 'POST':
            if not accepted:
                accepted.update(json.loads(request.content))
                raise httpx.ReadTimeout('synthetic lost response', request=request)
            return httpx.Response(409, json={'detail': 'already exists'})
        return httpx.Response(200, json=accepted)
    url, body, receipt = attachment(context, tmp_path, monkeypatch, handler)
    client, factory, _, _ = context
    assert client.post(url, json=body).status_code == 503
    with factory() as session:
        assert session.scalar(select(WgsStageExecution)).status == 'launching'
    resumed = client.post(url, json=body)
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()['dag_run_id'] == f"native__{receipt['execution_id']}"
    assert calls == ['POST', 'POST', 'GET']


def test_monitor_conflict_and_wrong_owner_cannot_attach(context, tmp_path, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request.method)
        return httpx.Response(409 if request.method == 'POST' else 200,
                              json={'dag_run_id': 'unrelated', 'conf': {}})
    url, body, receipt = attachment(context, tmp_path, monkeypatch, handler)
    client, factory, _, _ = context
    assert client.post(url, json={**body, 'generation': 8}).status_code == 409
    assert calls == []
    assert client.post(url, json=body).status_code == 409
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.dag_run_id is None
        run.submitted_by = 'another-user'
        session.commit()
    assert client.post(url, json=body).status_code == 403
    assert calls == ['POST', 'GET']
