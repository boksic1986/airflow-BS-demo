import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import AnalysisRun, Base, WgsMaintenanceAction
from app.wgs_step7_service import observe_maintenance, maintenance_context


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
