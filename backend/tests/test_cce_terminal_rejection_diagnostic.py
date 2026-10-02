"""Terminal rejection diagnostics preserve the existing native fence."""
import hashlib
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import cce_recovery_budget as budget
from app.models import AnalysisRun, Base, WgsStageExecution
from app.wgs_stage_execution_service import _sha256


def test_rejected_terminal_logs_selected_stage_without_payload(monkeypatch, tmp_path, caplog):
    body = {'analysis_id': 'SYNTHETIC_TERMINAL', 'attempt': 1,
            'stage': 'step2_master', 'stage_execution': {'protocol': 'cce.stage-execution.v1'}}
    request_hash = _sha256(body)
    frozen = {**body, 'execution_id': 'synthetic-step2', 'generation': 2,
              'request_hash': request_hash, 'orchestration_contract_version': 2}
    root = tmp_path / body['analysis_id'] / 'attempt-1'
    root.mkdir(parents=True)
    (root / 'step2_master.json').write_text(json.dumps(frozen), encoding='utf-8')
    row = SimpleNamespace(analysis_id=body['analysis_id'], attempt=1,
        stage_code='step2_master', status='success',
        release_id='synthetic-release', execution_id='synthetic-step2', generation=2,
        request_hash=request_hash, receipt_hash=hashlib.sha256(b'synthetic receipt').hexdigest(),
        predecessor_execution_id=None, predecessor_generation=None, predecessor_receipt_hash=None)
    run = SimpleNamespace(analysis_id=body['analysis_id'], attempt=1, pipeline_name='wgs',
        execution_mode='cce', current_stage='step2_master',
        params_json={'pipeline_release_id': 'synthetic-release', 'orchestration_contract_version': 2,
                     'private_input': 'DO_NOT_LOG_SYNTHETIC_PRIVATE_VALUE'})
    monkeypatch.setattr(budget, '_current_native_stage_row', lambda **_: row)
    observation = {'schema': 'cce.stage-execution.snapshot.v1',
        'execution_ref': {'protocol': 'cce.stage-execution.v1', 'pipeline': 'wgs',
            'analysis_id': run.analysis_id, 'attempt': 1, 'stage': 'step3_monitor',
            'execution_id': 'synthetic-step3', 'stage_generation': 1,
            'request_hash': 'b' * 64, 'registration_sha256': 'c' * 64},
        'state': 'failed', 'evidence_ref': 'd' * 64, 'runtime_identity': None,
        'compute_identity': None, 'observation_health': 'healthy'}
    assert budget._marked_native_terminal(session=None, run=run,
        settings=SimpleNamespace(wgs_runtime_request_root=str(tmp_path)),
        native_stage_observation=observation) == (False, row)
    diagnostic = json.loads(caplog.records[-1].message)
    assert diagnostic['event'] == 'native_terminal_rejected'
    assert diagnostic['predicate'] == 'native_stage_terminal'
    assert diagnostic['validator_reason'] == 'native stage success execution identity differs'
    assert diagnostic['current_stage'] == diagnostic['selected_stage'] == 'step2_master'
    assert diagnostic['execution_id'] == row.execution_id
    assert 'DO_NOT_LOG_SYNTHETIC_PRIVATE_VALUE' not in caplog.text
    assert 'synthetic-step3' not in caplog.text


@pytest.mark.parametrize('variant', ['current', 'foreign_execution', 'old_generation',
    'wrong_request_hash', 'wrong_receipt', 'wrong_terminal', 'old_dag',
    'newer_generation', 'later_stage', 'legacy_query_unconfirmed'])
def test_normal_terminal_uses_latest_registration_and_preserves_cleanup(tmp_path, variant):
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    aid = 'SYNTHETIC_CURRENT_TERMINAL'
    root = tmp_path / aid / 'attempt-1'
    root.mkdir(parents=True)
    rows = []

    def execution(stage, generation, status):
        body = {'analysis_id': aid, 'attempt': 1, 'stage': stage,
                'stage_execution': {'protocol': 'cce.stage-execution.v1'}}
        digest = _sha256(body)
        frozen = {**body, 'execution_id': f'synthetic-{stage}-{generation}',
                  'generation': generation, 'request_hash': digest,
                  'orchestration_contract_version': 2}
        (root / f'{stage}.json').write_text(json.dumps(frozen), encoding='utf-8')
        row = WgsStageExecution(analysis_id=aid, attempt=1, stage_code=stage,
            execution_id=frozen['execution_id'], generation=generation,
            request_hash=digest, release_id='synthetic-release', status=status,
            receipt_hash=hashlib.sha256(f'synthetic-{stage}-receipt'.encode()).hexdigest())
        rows.append(row)
        return row

    step2 = execution('step2_master', 2, 'success')
    step3 = execution('step3_monitor', 1, 'failed')
    observation = {'schema': 'cce.stage-execution.snapshot.v1',
        'execution_ref': {'protocol': 'cce.stage-execution.v1', 'pipeline': 'wgs',
            'analysis_id': aid, 'attempt': 1, 'stage': 'step3_monitor',
            'execution_id': step3.execution_id, 'stage_generation': 1,
            'request_hash': step3.request_hash, 'registration_sha256': 'e' * 64},
        'state': 'failed', 'evidence_ref': step3.receipt_hash,
        'runtime_identity': None, 'compute_identity': None, 'observation_health': 'healthy'}
    changes = {'foreign_execution': ('execution_id', 'synthetic-foreign'),
               'old_generation': ('stage_generation', 2),
               'wrong_request_hash': ('request_hash', 'f' * 64)}
    if variant in changes:
        key, value = changes[variant]
        observation['execution_ref'][key] = value
    if variant == 'wrong_receipt':
        observation['evidence_ref'] = 'f' * 64
    if variant == 'wrong_terminal':
        observation['state'] = 'succeeded'
    if variant == 'newer_generation':
        execution('step3_monitor', 2, 'failed')
    if variant == 'later_stage':
        execution('step4_publish', 1, 'running')
    if variant == 'legacy_query_unconfirmed':
        step3.terminal_payload_json = {
            'cce_monitor_observation': {'monitor_reconnect': {'phase': 'exhausted'}}}
    with factory.begin() as session:
        session.add(AnalysisRun(analysis_id=aid, pipeline_name='wgs', attempt=1,
            dag_id='bio_wgs', dag_run_id='synthetic-current-dag', execution_mode='cce',
            status='running', current_stage='step2_master', workdir='/synthetic/project',
            params_json={'pipeline_release_id': 'synthetic-release',
                         'orchestration_contract_version': 2}))
        session.add_all(rows)
    with factory() as session:
        run = session.get(AnalysisRun, 1)
        assert budget._current_native_stage_row(session=session, run=run,
            cleanup_stage='release_leases').execution_id == step2.execution_id
        reason = budget.dag_failure_fence_reason(session=session, run=run,
            dag_run_id='synthetic-old-dag' if variant == 'old_dag' else run.dag_run_id,
            native_stage_observation=observation,
            settings=(None if variant == 'legacy_query_unconfirmed' else
                      SimpleNamespace(wgs_runtime_request_root=str(tmp_path))))
        expected = (None if variant == 'current' else 'superseded_dag_run'
                    if variant == 'old_dag' else 'native_stage_unconfirmed')
        assert reason == expected
        assert run.current_stage == 'step2_master' and run.status == 'running'
        if variant == 'legacy_query_unconfirmed':
            run.current_stage = 'step3_monitor'
            assert budget.dag_failure_fence_reason(session=session, run=run,
                dag_run_id=run.dag_run_id) == 'monitor_execution_unconfirmed'
    engine.dispose()
