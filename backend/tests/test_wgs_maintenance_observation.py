import hashlib
import json
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.models import AnalysisRun, Base, RunStageState, WgsMaintenanceAction, WgsStageExecution
from app.wgs_step7_service import observe_maintenance, maintenance_context, request_step7_cleanup


@pytest.fixture
def setup(tmp_path):
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        run = AnalysisRun(analysis_id='WGS_20260922_010203_A1B2C3', pipeline_name='wgs',
            dag_id='bio_wgs', attempt=1, status='success', workdir='/synthetic')
        action = WgsMaintenanceAction(analysis_id=run.analysis_id, attempt=1,
            action_id='step7-sfs-123456abcdef', generation=1, action_type='cleanup_step7_sfs',
            status='queued', requested_by='synthetic', maintenance_dag_run_id='synthetic-maintenance')
        session.add_all([run, action]); session.commit()
        args = dict(session=session, request_root=tmp_path, analysis_id=run.analysis_id,
            action_id=action.action_id, attempt=1, generation=1, dag_run_id=action.maintenance_dag_run_id)
        yield run, action, args


def test_timeout_sync_does_not_change_analysis(setup):
    run, action, args = setup
    result = observe_maintenance(**args, status='failed', message='清理状态待确认')
    assert result['status'] == 'failed'
    assert action.error_message == '清理状态待确认'
    assert run.status == 'success'
    assert action.ended_at is not None


def test_protocol_scope_default_failure_callback_preserves_original_error(setup):
    run, action, args = setup
    original_error = '清理进程已退出，尚无成功回执'
    observe_maintenance(**args, status='failed', message=original_error)

    result = observe_maintenance(
        **args, status='failed', message='清理监控已停止，重试前需核对原执行',
    )

    assert result['error_message'] == original_error
    assert observe_maintenance(**args, status='failed')['error_message'] == original_error
    assert action.error_message == original_error
    assert action.status == 'failed'
    assert run.status == 'success'


def test_protocol_scope_stopped_legacy_retry_preserves_old_registration(setup):
    from app.wgs_observer import _ingest_runtime_stage_status
    from app.wgs_stage_catalog import load_wgs_stage_contract
    from app.wgs_stage_execution_service import register_stage_execution
    from test_wgs_step7_service import FakeAirflow

    run, old_action, args = setup
    session = args['session']
    run.params_json = {'analysis_batch': 'SYNTHETIC', 'orchestration_contract_version': 2}
    frozen_target = {'cce_bundle': '/approved/synthetic/frozen-cce'}
    old_action.target_snapshot_json = dict(frozen_target)
    old_body = {
        'analysis_id': run.analysis_id, 'attempt': 1, 'stage': 'step7_cleanup',
        'maintenance_action_id': old_action.action_id, 'step7_generation': 1,
        'step7_target_snapshot': dict(frozen_target),
        'stage_execution': {'protocol': 'cce.stage-execution.v1'},
    }
    old_hash = hashlib.sha256(json.dumps(
        old_body, sort_keys=True, separators=(',', ':'),
    ).encode()).hexdigest()
    old_execution = WgsStageExecution(
        execution_id='wse_synthetic_rejected_step7', analysis_id=run.analysis_id,
        attempt=1, stage_code='step7_cleanup', generation=1, status='accepted',
        request_hash=old_hash, release_id='wgs-4.2.2-441d5e7',
    )
    session.add(old_execution)
    for stage in ('step5_download', 'step6_materialize'):
        session.add(RunStageState(
            analysis_id=run.analysis_id, attempt=1, stage_code=stage,
            stage_label=stage, stage_status='success', progress_source='synthetic',
        ))
    session.commit()
    root = args['request_root'] / run.analysis_id / 'attempt-1'
    root.mkdir(parents=True)
    frozen_request = {
        **old_body, 'orchestration_contract_version': 2,
        'execution_id': old_execution.execution_id, 'generation': 1,
        'request_hash': old_hash,
    }
    original_bytes = (json.dumps(frozen_request, sort_keys=True) + '\n').encode()
    request_path = root / 'step7_cleanup.json'
    request_path.write_bytes(original_bytes)
    status_path = root / 'step7_cleanup.status.json'
    status_path.write_text(json.dumps({
        **frozen_request, 'schema_version': 'wgs-runtime.stage-status.v1',
        'status': 'accepted', 'updated_at': '2026-09-22T01:00:00+00:00',
    }))
    observe_maintenance(**args, status='failed', message='清理进程已退出，尚无成功回执')
    retried = request_step7_cleanup(
        session=session, airflow_client=FakeAirflow(), analysis_id=run.analysis_id,
        batch_confirmation='SYNTHETIC', requested_by='synthetic',
        retry_failed=True, expected_action_id=old_action.action_id,
    )
    new_action = session.scalar(select(WgsMaintenanceAction).where(
        WgsMaintenanceAction.action_id == retried['action_id'],
    ))
    retry_args = {
        **args, 'action_id': new_action.action_id, 'generation': 2,
        'dag_run_id': new_action.maintenance_dag_run_id,
    }
    context = maintenance_context(**retry_args)
    assert context['action'] == old_action.action_id
    assert context['runtime_identity']['request_hash'] == old_hash

    observe_maintenance(**retry_args, status='stopped')

    session.refresh(old_execution)
    assert old_execution.status == 'failed'
    assert old_execution.request_hash == old_hash
    assert request_path.read_bytes() == original_bytes
    sessions = sessionmaker(bind=session.get_bind())
    assert _ingest_runtime_stage_status(sessions, args['request_root'], status_path) is False
    session.refresh(old_execution)
    assert old_execution.status == 'failed'
    new_body = {
        **old_body, 'maintenance_action_id': new_action.action_id,
        'step7_generation': 2,
    }
    new_body.pop('stage_execution')
    execution = register_stage_execution(
        session=session, run=run,
        contract=load_wgs_stage_contract(Path(__file__).parents[2] / 'config' / 'wgs_stage_contract.yaml'),
        stage_code='step7_cleanup', request_payload=new_body,
    )
    session.commit()

    assert execution.generation == 2
    assert execution.status == 'accepted'
    assert 'stage_execution' not in new_body
    assert new_body['step7_target_snapshot'] == frozen_target
    assert new_action.target_snapshot_json == old_action.target_snapshot_json == frozen_target
    assert old_execution.request_hash == old_hash
    assert request_path.read_bytes() == original_bytes
    assert _ingest_runtime_stage_status(sessions, args['request_root'], status_path) is False
    session.refresh(execution)
    assert execution.status == 'accepted'
    assert run.status == 'success'


@pytest.mark.parametrize('field,value', [('attempt', 2), ('generation', 2),
    ('action_id', 'step7-other'), ('dag_run_id', 'another-dag-run')])
def test_stale_callback_cannot_overwrite(setup, field, value):
    _, action, args = setup
    with pytest.raises(ValueError, match='stale'):
        observe_maintenance(**{**args, field: value}, status='failed')
    assert action.status == 'queued'


def test_success_receipt_wins_over_timeout(setup):
    _, action, args = setup
    root = args['request_root']/args['analysis_id']/'attempt-1'
    root.mkdir(parents=True)
    (root/'step7_cleanup.status.json').write_text(json.dumps({
        'schema_version': 'wgs-runtime.stage-status.v1', 'analysis_id': args['analysis_id'],
        'attempt': 1, 'stage': 'step7_cleanup', 'maintenance_action_id': action.action_id,
        'step7_generation': 1, 'status': 'success'}))
    assert observe_maintenance(**args, status='failed')['status'] == 'success'
    assert observe_maintenance(**args, status='running')['status'] == 'success'


def test_unregistered_context_is_not_a_success(setup):
    _, _, args = setup
    assert maintenance_context(**args) == {'registered': False}


def test_context_uses_registered_identity_and_rejects_foreign(setup):
    _, action, args = setup
    root = args['request_root']/args['analysis_id']/'attempt-1'
    root.mkdir(parents=True)
    path = root/'step7_cleanup.json'
    value = {'analysis_id': args['analysis_id'], 'attempt': 1, 'stage': 'step7_cleanup',
        'maintenance_action_id': action.action_id, 'step7_generation': 1}
    path.write_text(json.dumps(value))
    assert maintenance_context(**args)['action'] == action.action_id
    value['maintenance_action_id'] = 'foreign'
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='identity'):
        maintenance_context(**args)


@pytest.mark.parametrize('state', ['accepted', 'running'])
def test_stale_nonterminal_receipt_does_not_hide_monitoring_failure(setup, state):
    from app.wgs_observer import _ingest_runtime_stage_status
    _, action, args = setup
    observe_maintenance(**args, status='failed', message='清理状态待确认')
    root = args['request_root']/args['analysis_id']/'attempt-1'
    root.mkdir(parents=True)
    path = root/'step7_cleanup.status.json'
    path.write_text(json.dumps({'schema_version': 'wgs-runtime.stage-status.v1',
        'analysis_id': args['analysis_id'], 'attempt': 1, 'stage': 'step7_cleanup',
        'maintenance_action_id': action.action_id, 'step7_generation': 1,
        'status': state, 'updated_at': '2026-09-22T01:00:00+00:00'}))
    sessions = sessionmaker(bind=args['session'].get_bind())
    assert _ingest_runtime_stage_status(sessions, args['request_root'], path) is False
    args['session'].refresh(action)
    assert action.status == 'failed'
    assert action.error_message == '清理状态待确认'
