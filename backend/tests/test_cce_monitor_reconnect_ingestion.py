"""Producer status -> real ingestion -> normal detail projection and DagRun fence."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from app.models import AnalysisRun
from app import gatk_runtime_service
from app.wgs_observer import _ingest_runtime_stage_status
from app.wgs_submission_service import mark_submission_dag_failed
from test_cce_recovery_budget import run_store
from test_cce_recovery_projection import execution, view
from test_cce_monitor_reconnect import monitor_fixture, native, CONFIG, REAL_QUERY
from scripts.cce_query_reconnect import QueryReconnectStopped
import subprocess
import json


def setup_case(run_store, tmp_path, monkeypatch):
    with run_store() as s: pipeline = s.scalar(select(AnalysisRun)).pipeline_name
    case = monitor_fixture(tmp_path, monkeypatch, pipeline)
    with run_store.begin() as s:
        run = s.scalar(select(AnalysisRun))
        run.analysis_id = case.payload['analysis_id']
        run.status = 'running'; run.dag_run_id = 'original'
        run.params_json = dict(run.params_json, orchestration_contract_version=2)
        row = execution(s, run, status='running', generation=1)
        row.execution_id = case.payload['execution_id']; row.request_hash = case.payload['request_hash']
    monkeypatch.setattr(gatk_runtime_service, '_ingest_gatk_evidence', lambda **kw: None)
    def ingest():
        if pipeline == 'wgs':
            _ingest_runtime_stage_status(run_store, case.root, case.path.with_suffix('.status.json'))
        else:
            with run_store() as s:
                gatk_runtime_service.sync_gatk_stage_status(session=s,
                    settings=SimpleNamespace(gatk_runtime_request_root=str(case.root)),
                    analysis_id=case.payload['analysis_id'], attempt=1, stage='step3_monitor')
    return case, pipeline, ingest


def test_exhausted_monitor_is_not_remote_analysis_failure_even_after_callback(run_store, tmp_path, monkeypatch):
    case, pipeline, ingest = setup_case(run_store, tmp_path, monkeypatch)
    owner = case.owner()
    monkeypatch.setattr(native, '_run', lambda *a, **kw: subprocess.CompletedProcess([], 1, b'', b'connection reset by peer'))
    with pytest.raises(QueryReconnectStopped):
        REAL_QUERY({**CONFIG, '_monitor_query_runner': owner.run}, 'job', 'master')
    case.write('failed')
    ingest()
    with run_store() as s:
        run = s.scalar(select(AnalysisRun))
        assert run.status == 'running' and run.ended_at is None
        result = view(s, run, datetime.fromtimestamp(case.clock[0], timezone.utc))
        assert result['state'] == 'needs_attention' and result['limit'] == 6 and result['ordinal'] == 6
        callback = mark_submission_dag_failed if pipeline == 'wgs' else gatk_runtime_service.mark_gatk_dag_failed
        response = callback(session=s, analysis_id=run.analysis_id, attempt=1,
            dag_run_id='original', failed_task_ids=['step3_monitor'])
        assert response['ignored'] and response['reason'] == 'monitor_execution_unconfirmed'
        assert run.status == 'running' and run.ended_at is None
        # Periodic DagRun reconciliation must obey the same fence as callbacks.
        from app.diagnostics_service import sync_wgs_airflow_status
        from app.gatk_airflow_sync import sync_gatk_airflow_status
        monkeypatch.setattr('app.diagnostics_service.build_wgs_error_summary',
            lambda **kw: pytest.fail('monitor outage was projected as WGS analysis failure'))
        run.dag_id = f'bio_{pipeline}'
        run.dag_run_id = f'{run.analysis_id}-a1'
        s.commit()
        client = SimpleNamespace(get_dag_run=lambda dag, identity: {
            'dag_id': dag, 'dag_run_id': identity, 'state': 'failed'})
        sync = sync_wgs_airflow_status if pipeline == 'wgs' else sync_gatk_airflow_status
        sync(session=s, airflow_client=client, analysis_id=run.analysis_id,
             settings=SimpleNamespace())
        assert run.status == 'running' and run.ended_at is None


def test_waiting_and_confirmed_observation_project_without_new_compute(run_store, tmp_path, monkeypatch):
    case, _, ingest = setup_case(run_store, tmp_path, monkeypatch)
    owner = case.owner()
    owner.sleep = lambda seconds: (_ for _ in ()).throw(SystemExit('worker interrupted'))
    monkeypatch.setattr(native, '_run', lambda *a, **kw: subprocess.CompletedProcess([], 1, b'', b'connection refused'))
    with pytest.raises(SystemExit):
        REAL_QUERY({**CONFIG, '_monitor_query_runner': owner.run}, 'job', 'master')
    ingest()
    with run_store() as s:
        result = view(s, s.scalar(select(AnalysisRun)), datetime.fromtimestamp(1000, timezone.utc))
        assert result['state'] == 'checking' and result['limit'] == 6 and result['ordinal'] == 0
        assert result['next_retry_at'] == '1970-01-01T00:17:10+00:00'
    owner = case.owner()
    monkeypatch.setattr(native, '_run', lambda *a, **kw: subprocess.CompletedProcess([], 0, b'', b''))
    REAL_QUERY({**CONFIG, '_monitor_query_runner': owner.run}, 'job', 'master')
    owner.confirmed(); case.write('running', monitoring_health='healthy')
    ingest()
    with run_store() as s:
        run = s.scalar(select(AnalysisRun))
        assert run.status == 'running' and view(s, run) is None


def test_query_control_advances_without_refreshing_old_rule_observation(run_store, tmp_path, monkeypatch):
    from app.models import RunStageState, WgsStageExecution, PipelineStageExecution
    from app.cce_monitor_observation import query_unconfirmed
    from test_cce_monitor_reconnect import confirmed_monitor_result
    case, pipeline, ingest = setup_case(run_store, tmp_path, monkeypatch)
    binding_path = case.root.parent / 'runs' / case.payload['analysis_id'] / 'attempt-1' / 'batch-binding.json'
    binding_path.parent.mkdir(parents=True, exist_ok=True)
    binding_path.write_text(json.dumps({'schema_version': 'wgs-runtime.batch-binding.v2',
        'analysis_id': case.payload['analysis_id'], 'attempt': 1,
        'master_job': 'cce-master-synthetic', 'namespace': 'synthetic'}))
    case.write('running', master={'master_state': 'RUNNING', 'completed': 6, 'total': 333, 'percent': 1.8},
        master_job='cce-master-synthetic', namespace='synthetic', run_label='cce-run-aaaaaaaaaaaaaaaa',
        completed_units=6, total_units=333, progress_percent=1, unit='rules')
    ingest()
    with run_store() as s:
        measured = s.scalar(select(RunStageState))
        old_business_time = measured.updated_at
        assert measured.completed_units == 6 and measured.total_units == 333
    owner = case.owner()
    owner.sleep = lambda seconds: (_ for _ in ()).throw(SystemExit('interrupt before reserved retry'))
    with pytest.raises(SystemExit):
        owner.run(lambda timeout: (_ for _ in ()).throw(native.RecoveryQueryError('TRANSPORT')))
    ingest()
    model = WgsStageExecution if pipeline == 'wgs' else PipelineStageExecution
    with run_store() as s:
        assert query_unconfirmed(s.scalar(select(model)))
        measured = s.scalar(select(RunStageState))
        assert measured.updated_at == old_business_time
        assert measured.completed_units == 6  # Retained progress is not a new measurement.
    confirmed_monitor_result(case, monkeypatch, {'master_state': 'RUNNING', 'completed': 7,
        'total': 333, 'percent': 2.1, 'current_rule': 'synthetic-rule', 'message': 'workflow running'})
    ingest()
    with run_store() as s:
        assert not query_unconfirmed(s.scalar(select(model)))
        measured = s.scalar(select(RunStageState))
        assert measured.completed_units == 7 and measured.total_units == 333
        assert measured.updated_at > old_business_time
