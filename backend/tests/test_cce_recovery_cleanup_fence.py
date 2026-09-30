"""Old DagRuns cannot release replacement leases or drain its observer."""
import hashlib
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import main
from app.models import AnalysisRun, Base, ObsTransferLease, ObserverRunState, RunAction, TransferJob, WgsStageExecution


AID = 'SYNTHETIC_CLEANUP'
RELEASES = ['release_input_transfer_slot', 'release_result_transfer_slot', 'release_leases']


@pytest.fixture
def store(monkeypatch, tmp_path):
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        session.add(AnalysisRun(analysis_id=AID, pipeline_name='wgs', attempt=1,
            dag_id='bio_wgs', dag_run_id='replacement', execution_mode='cce',
            status='running', current_stage='step3_monitor', workdir='/synthetic/project',
            params_json={'pipeline_release_id': 'synthetic'}))
        for kind, direction in [('input', 'upload'), ('result', 'download')]:
            session.add(ObsTransferLease(slot_name=f'wgs-obs-{direction}-01',
                analysis_id=AID, attempt=1, transfer_id=f'{AID}-a1-{kind}'))
            session.add(TransferJob(analysis_id=AID, attempt=1,
                transfer_id=f'{AID}-a1-{kind}', direction=direction, status='success'))
        session.add(ObserverRunState(analysis_id=AID, attempt=1,
            pipeline_release_id='synthetic', run_label=AID,
            relative_evidence_path='synthetic/a1', lifecycle_status='active'))
    monkeypatch.setattr(main, 'get_sessionmaker', lambda: factory)
    monkeypatch.setattr(main, '_wgs_runtime_adapter_enabled', lambda: True)
    monkeypatch.setattr(main, 'get_settings', lambda: SimpleNamespace(
        gatk_execution_enabled=True, wgs_release_catalog_path='/synthetic/catalog',
        wgs_runtime_request_root=str(tmp_path)))
    monkeypatch.setattr(main, 'load_wgs_release_catalog', lambda path:
        SimpleNamespace(by_id=lambda release_id: SimpleNamespace()))
    yield factory
    engine.dispose()


def release(store, pipeline, stage, **identity):
    with store.begin() as session:
        session.scalar(select(AnalysisRun)).pipeline_name = pipeline
    request_type = main.WgsRuntimeStageRequest if pipeline == 'wgs' else main.GatkRuntimeStageRequest
    endpoint = main.internal_wgs_runtime_stage if pipeline == 'wgs' else main.internal_gatk_runtime_stage
    request = request_type(attempt=1, adapter=f'{pipeline}-runtime-200', **identity)
    return endpoint(AID, stage, request)


def recover(store, status='queued', **payload):
    with store.begin() as session:
        session.add(RunAction(analysis_id=AID, action='cce_compute_recovery',
            result_status=status, payload_json={'attempt': 1, **payload}))


def assert_preserved(store):
    with store() as session:
        assert all(lease.analysis_id == AID for lease in session.scalars(select(ObsTransferLease)))
        assert session.scalar(select(ObserverRunState)).lifecycle_status == 'active'
        assert session.scalar(select(AnalysisRun)).current_stage == 'step3_monitor'


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
@pytest.mark.parametrize('stage', RELEASES)
def test_old_dag_cannot_release_even_terminal_transfer(store, pipeline, stage):
    recover(store, status='success', dag_run_id='replacement')
    with pytest.raises(HTTPException) as error:
        release(store, pipeline, stage, dag_run_id='original')
    assert 'superseded_dag_run' in error.value.detail['message']
    assert_preserved(store)


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
@pytest.mark.parametrize('state,identity', [('reserved', {'dag_run_id': 'replacement'}),
                                         ('queued', {})])
def test_unresolved_or_identityless_cleanup_does_not_mutate(store, pipeline, state, identity):
    recover(store, status=state, dag_run_id='replacement')
    with pytest.raises(HTTPException):
        release(store, pipeline, 'release_leases', **identity)
    assert_preserved(store)


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
@pytest.mark.parametrize('stage', RELEASES)
def test_current_bound_dag_releases_only_requested_terminal_slot(store, pipeline, stage):
    recover(store, dag_run_id='replacement')
    result = release(store, pipeline, stage, dag_run_id='replacement')
    assert result['released'] and not result['retained']
    with store() as session:
        remaining = [lease.slot_name for lease in session.scalars(select(ObsTransferLease))
                     if lease.analysis_id == AID]
        expected = {'release_input_transfer_slot': ['wgs-obs-download-01'],
                    'release_result_transfer_slot': ['wgs-obs-upload-01'], 'release_leases': []}
        assert remaining == expected[stage]


@pytest.mark.parametrize('pipeline', ['wgs', 'gatk'])
def test_current_identity_cannot_override_nonterminal_transfer(store, pipeline):
    recover(store, dag_run_id='replacement')
    with store.begin() as session:
        for transfer in session.scalars(select(TransferJob)):
            transfer.status = 'running'
    result = release(store, pipeline, 'release_leases', dag_run_id='replacement')
    assert result['retained'] and not result['released']
    with store() as session:
        assert all(lease.analysis_id == AID for lease in session.scalars(select(ObsTransferLease)))


@pytest.mark.parametrize('identity,allowed', [({'dag_run_id': 'original'}, False),
                                            ({}, False), ({'dag_run_id': 'replacement'}, True)])
def test_observer_drain_requires_current_bound_dag(store, identity, allowed):
    recover(store, dag_run_id='replacement')
    request = main.WgsObserverLifecycleRequest(attempt=1, **identity)
    if allowed:
        assert main.internal_wgs_observer_deactivate(AID, request)['lifecycle_status'] == 'draining'
    else:
        with pytest.raises(HTTPException):
            main.internal_wgs_observer_deactivate(AID, request)
        assert_preserved(store)


def test_old_attempt_and_manual_resume_identity_cannot_drain_observer(store):
    with store.begin() as session:
        session.scalar(select(AnalysisRun)).params_json = {'resume_action_id': 'manual-current'}
    for identity in [dict(attempt=2, dag_run_id='replacement', resume_action_id='manual-current'),
                     dict(attempt=1, dag_run_id='replacement', resume_action_id='manual-old'),
                     dict(attempt=1, resume_action_id='manual-current')]:
        with pytest.raises(HTTPException):
            main.internal_wgs_observer_deactivate(AID, main.WgsObserverLifecycleRequest(**identity))
        assert_preserved(store)
    with store.begin() as session:
        session.scalar(select(AnalysisRun)).dag_run_id = None
    with pytest.raises(HTTPException):
        main.internal_wgs_observer_deactivate(AID, main.WgsObserverLifecycleRequest(
            attempt=1, resume_action_id='manual-current'))
    assert_preserved(store)
    with store.begin() as session:
        session.scalar(select(AnalysisRun)).dag_run_id = 'replacement'
    result = main.internal_wgs_observer_deactivate(AID, main.WgsObserverLifecycleRequest(
        attempt=1, dag_run_id='replacement', resume_action_id='manual-current'))
    assert result['lifecycle_status'] == 'draining'


def test_legacy_no_recovery_cleanup_is_compatible(store):
    assert release(store, 'wgs', 'release_leases')['released']
    result = main.internal_wgs_observer_deactivate(AID, main.WgsObserverLifecycleRequest(attempt=1))
    assert result['lifecycle_status'] == 'draining'


def test_partial_release_rechecks_identity_before_changing_run_projection(store, monkeypatch):
    # The existing primitive commits when either slot is released, dropping the
    # run lock; a replacement can become current before retained-slot projection.
    with store.begin() as session:
        session.scalar(select(TransferJob).where(TransferJob.direction == 'download')).status = 'running'
    release_slot = main.release_obs_transfer_slot
    def interleaved_release(**kwargs):
        result = release_slot(**kwargs)
        with store.begin() as session:
            session.scalar(select(AnalysisRun)).dag_run_id = 'next-replacement'
        return result
    monkeypatch.setattr(main, 'release_obs_transfer_slot', interleaved_release)
    with pytest.raises(HTTPException):
        release(store, 'wgs', 'release_leases', dag_run_id='replacement')
    with store() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.current_stage == 'step3_monitor' and run.dag_run_id == 'next-replacement'
        assert session.scalar(select(ObsTransferLease).where(
            ObsTransferLease.slot_name == 'wgs-obs-download-01')).analysis_id == AID


def test_unknown_stage_cannot_fail_or_release(store, tmp_path):
    """One current WGS registration per stage shares the exact failure/cleanup fence."""
    from app.wgs_stage_execution_service import _sha256
    from app.wgs_submission_service import mark_submission_dag_failed
    from test_cce_recovery_evidence import digest

    stages = ('step1_upload', 'step2_master', 'step3_monitor',
              'step4_publish', 'step5_download', 'step6_materialize')
    root = tmp_path / AID / 'attempt-1'
    root.mkdir(parents=True)
    settings = main.get_settings()
    snapshots = {}
    for stage in stages:
        execution_id = f'synthetic-{stage}'
        body = {'analysis_id': AID, 'attempt': 1, 'stage': stage,
                'stage_execution': {'protocol': 'cce.stage-execution.v1'}}
        request_hash = _sha256(body)
        frozen = {**body, 'orchestration_contract_version': 2,
                  'execution_id': execution_id, 'generation': 1,
                  'request_hash': request_hash}
        (root / f'{stage}.json').write_text(json.dumps(frozen), encoding='utf-8')
        receipt = {'schema_version': 'wgs-runtime.stage-status.v1',
                   'analysis_id': AID, 'attempt': 1, 'stage': stage,
                   'execution_id': execution_id, 'generation': 1,
                   'request_hash': request_hash, 'status': 'failed'}
        raw = json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()
        (root / f'{stage}.status.json').write_bytes(raw)
        receipt_hash = hashlib.sha256(raw).hexdigest()
        ref = {'protocol': 'cce.stage-execution.v1', 'pipeline': 'wgs',
               'analysis_id': AID, 'attempt': 1, 'stage': stage,
               'execution_id': execution_id, 'stage_generation': 1,
               'request_hash': request_hash, 'registration_sha256': 'e' * 64}
        snapshots[stage] = {'schema': 'cce.stage-execution.snapshot.v1',
                            'execution_ref': ref, 'state': 'unknown',
                            'evidence_ref': receipt_hash, 'runtime_identity': None,
                            'compute_identity': None, 'observation_health': 'degraded'}
        with store.begin() as session:
            run = session.scalar(select(AnalysisRun))
            run.current_stage = stage
            run.params_json = {'pipeline_release_id': 'synthetic',
                               'orchestration_contract_version': 2}
            session.add(WgsStageExecution(
                analysis_id=AID, attempt=1, stage_code=stage,
                execution_id=execution_id, generation=1, status='failed',
                request_hash=request_hash, release_id='synthetic',
                receipt_hash=receipt_hash,
                evidence_type='wgs-runtime.stage-status.v1',
                evidence_key=f'{stage}.status.json',
                terminal_payload_json=(
                    {'cce_monitor_observation': {'monitor_reconnect': {'phase': 'exhausted'}}}
                    if stage == 'step3_monitor' else {}
                ),
            ))
        with store() as session:
            run = session.scalar(select(AnalysisRun))
            answer = mark_submission_dag_failed(
                session=session, analysis_id=AID, attempt=1,
                failed_task_ids=[f'wait_{stage}'], dag_run_id='replacement',
                native_stage_observation=snapshots[stage], settings=settings,
            )
            assert answer['ignored'] and answer['reason'] == 'native_stage_unconfirmed'
            assert run.status == 'running' and run.current_stage == stage
        cleanup = ('release_input_transfer_slot' if stage == 'step1_upload'
                   else 'release_result_transfer_slot' if stage == 'step5_download'
                   else 'release_leases')
        with pytest.raises(HTTPException):
            release(store, 'wgs', cleanup, dag_run_id='replacement',
                    native_stage_observation=snapshots[stage])
        with store() as session:
            assert all(lease.analysis_id == AID for lease in session.scalars(select(ObsTransferLease)))
            assert session.scalar(select(ObserverRunState)).lifecycle_status == 'active'
        if stage == 'step3_monitor':
            with pytest.raises(HTTPException):
                main.internal_wgs_observer_deactivate(AID,
                    main.WgsObserverLifecycleRequest(
                        attempt=1, dag_run_id='replacement',
                        native_stage_observation=snapshots[stage],
                    ))

    failed = {**snapshots['step3_monitor'], 'state': 'failed',
              'observation_health': 'healthy'}
    with store.begin() as session:
        session.scalar(select(AnalysisRun)).current_stage = 'step3_monitor'
    with store() as session:
        stale = mark_submission_dag_failed(
            session=session, analysis_id=AID, attempt=1,
            failed_task_ids=['wait_step3_analysis'], dag_run_id='old-dag',
            native_stage_observation=failed, settings=settings,
        )
        assert stale['ignored'] and stale['reason'] == 'superseded_dag_run'
        missing = mark_submission_dag_failed(
            session=session, analysis_id=AID, attempt=1,
            failed_task_ids=['wait_step3_analysis'], dag_run_id='replacement',
            settings=settings,
        )
        assert missing['ignored'] and missing['reason'] == 'native_stage_unconfirmed'
        mismatched = {**failed, 'execution_ref': {**failed['execution_ref'],
                                                'stage_generation': 2}}
        wrong = mark_submission_dag_failed(
            session=session, analysis_id=AID, attempt=1,
            failed_task_ids=['wait_step3_analysis'], dag_run_id='replacement',
            native_stage_observation=mismatched, settings=settings,
        )
        assert wrong['ignored'] and wrong['reason'] == 'native_stage_unconfirmed'
        confirmed = mark_submission_dag_failed(
            session=session, analysis_id=AID, attempt=1,
            failed_task_ids=['wait_step3_analysis'], dag_run_id='replacement',
            native_stage_observation=failed, settings=settings,
        )
        assert not confirmed.get('ignored') and confirmed['status'] == 'failed'
        assert session.scalar(select(AnalysisRun)).status == 'failed'

    observer_request = main.WgsObserverLifecycleRequest(
        attempt=1, dag_run_id='replacement', native_stage_observation=failed)
    with pytest.raises(HTTPException) as error:
        main.internal_wgs_observer_deactivate(AID, observer_request)
    assert 'step3_worker_quiet_unconfirmed' in error.value.detail['message']
    with pytest.raises(HTTPException):
        release(store, 'wgs', 'release_leases', dag_run_id='replacement',
                native_stage_observation=failed)
    with store() as session:
        assert session.scalar(select(ObserverRunState)).lifecycle_status == 'active'
        assert all(lease.analysis_id == AID for lease in session.scalars(select(ObsTransferLease)))

    # Bind the current Step3 receipt to the same-attempt registered Step2 Master.
    source_ref = snapshots['step2_master']['execution_ref']
    platform = dict(pipeline='wgs', analysis_id=AID, attempt=1,
                    stage='step2_master', execution_id=source_ref['execution_id'],
                    generation=source_ref['stage_generation'],
                    request_hash=source_ref['request_hash'])
    binding = dict(schema_version=2, platform_execution=platform,
                   source_bundle='/synthetic/source', selected_bundle='/synthetic/selected',
                   native=dict(attempt=1, execution_generation=3, request_hash='d' * 64,
                               run_id='synthetic-native', namespace='synthetic',
                               job_uid='master-one', pod_uid='master-pod-one',
                               recovery_context=dict(pipeline='wgs', analysis_id=AID,
                                                     execution_id='native')))
    identity = dict(pipeline='wgs', analysis_id=AID, attempt='1',
                    execution_id='native:analysis', generation=3,
                    request_hash='d' * 64, run_id='synthetic-native',
                    namespace='synthetic', master_job_uid='master-one',
                    master_pod_uid='master-pod-one')
    candidate = dict(identity, schema='snakemake.kubernetes.executor-failure.v1',
                     observed_epoch=1, automatic_recovery_allowed=False,
                     requires_master_terminal=True,
                     failures=[dict(worker_name='synthetic-worker', worker_uid=None,
                                    category='WORKER_CREATE_ADMISSION_TIMEOUT',
                                    creation_state='ABSENT', request_count=3,
                                    retryable=True, exhausted=True)])
    terminal = dict(identity, schema='cce.master-terminal.v1', sealed=True, complete=True,
                    plugin_failure_sha256=digest(candidate),
                    submission_snapshot_sha256='e' * 64,
                    master_state='failed', master_pod_state='terminated', exit_code=1,
                    fatal_source='executor_submission', executor_failure_count=1,
                    rule_failure_count=0, other_failure_count=0,
                    worker_inventory_complete=True, worker_ownership_verified=True,
                    submissions_reconciled=True, active_worker_jobs=1,
                    active_worker_pods=0, unresolved_submissions=0)
    proof = dict(schema_version=2, binding=binding, phase='analysis',
                 candidate=candidate, terminal=terminal)
    with store.begin() as session:
        source = session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step2_master'))
        monitor = session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor'))
        source.terminal_payload_json = {'cce_master_binding': binding}
        monitor.terminal_payload_json = dict(monitor.terminal_payload_json,
            cce_master_submit_execution_id=source.execution_id,
            cce_master_binding=binding, cce_recovery_evidence=proof)
    with pytest.raises(HTTPException) as error:
        main.internal_wgs_observer_deactivate(AID, observer_request)
    assert 'step3_worker_quiet_unconfirmed' in error.value.detail['message']

    quiet = deepcopy(proof)
    quiet['terminal']['active_worker_jobs'] = 0
    with store.begin() as session:
        monitor = session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor'))
        monitor.terminal_payload_json = dict(monitor.terminal_payload_json,
                                             cce_recovery_evidence=quiet)
    # An initial marked monitor has no action binding yet. Complete schema2
    # failure evidence alone must not reserve while its native state is unknown.
    from datetime import datetime, timedelta, timezone
    from app.cce_recovery_service import reserve_monitored_recovery
    from app.cce_recovery_poll import poll_compute_recovery
    recovery_actions = select(RunAction).where(RunAction.action == 'cce_compute_recovery')
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    deadline = (now + timedelta(hours=1)).isoformat()
    with store() as session:
        run = session.scalar(select(AnalysisRun))
        run.status = 'running'
        run.params_json = dict(run.params_json,
            cce_recovery_policy=dict(version=1, attempt=1, enabled=True, original_deadline=deadline),
            cce_recovery_budget=dict(attempt=1, count=0, original_deadline=deadline))
        monitor = session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor'))
        payload = dict(monitor.terminal_payload_json)
        payload.pop('cce_monitor_observation', None)
        monitor.terminal_payload_json = payload
        session.flush()
        trial = session.begin_nested()
        permit = reserve_monitored_recovery(session=session, analysis_id=AID, attempt=1,
            monitor_execution_id=monitor.execution_id, evidence_root=None, now=now)
        assert permit['ordinal'] == 1  # Prove this fixture's evidence is otherwise eligible.
        trial.rollback()
        session.commit()
    with store() as session:
        result = poll_compute_recovery(session=session, settings=settings,
            airflow_client=SimpleNamespace(), analysis_id=AID, attempt=1,
            pipeline='wgs', dag_run_id='replacement', resume_action_id=None, now=now,
            native_stage_observation=snapshots['step3_monitor'])
        assert result['status'] == 'needs_attention'
        assert not session.scalars(recovery_actions).all()
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count'] == 0
    # A stale UI reconnect phase cannot overrule an exact current native terminal.
    with store.begin() as session:
        monitor = session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor'))
        monitor.terminal_payload_json = dict(monitor.terminal_payload_json,
            cce_monitor_observation={'monitor_reconnect': {'phase': 'exhausted'}})
    with store() as session:
        result = poll_compute_recovery(session=session, settings=settings,
            airflow_client=SimpleNamespace(), analysis_id=AID, attempt=1,
            pipeline='wgs', dag_run_id='replacement', resume_action_id=None, now=now,
            native_stage_observation=snapshots['step3_monitor'])
        assert result['status'] == 'needs_attention'
        assert not session.scalars(recovery_actions).all()
    with store.begin() as session:
        session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor')).status = 'canceled'
    canceled = dict(failed, state='canceled')
    with store() as session:
        result = poll_compute_recovery(session=session, settings=settings,
            airflow_client=SimpleNamespace(), analysis_id=AID, attempt=1,
            pipeline='wgs', dag_run_id='replacement', resume_action_id=None, now=now,
            native_stage_observation=canceled)
        assert result['status'] == 'not_eligible'
        assert not session.scalars(recovery_actions).all()
    with store.begin() as session:
        monitor = session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor'))
        monitor.status = 'failed'
        monitor.terminal_payload_json = dict(monitor.terminal_payload_json,
                                             cce_recovery_evidence=proof)
    settings.wgs_contract_v2_enabled = True
    with store() as session:
        result = poll_compute_recovery(session=session, settings=settings,
            airflow_client=SimpleNamespace(), analysis_id=AID, attempt=1,
            pipeline='wgs', dag_run_id='replacement', resume_action_id=None, now=now,
            native_stage_observation=failed)
        assert result['status'] == 'waiting'
        challenge = result['worker_probe']
        wait_deadline = result['worker_wait_deadline']
        assert len(session.scalars(recovery_actions).all()) == 1
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count'] == 1
    with store.begin() as session:
        session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor')).generation = 2
    with store() as session:
        stale = poll_compute_recovery(session=session, settings=settings,
            airflow_client=SimpleNamespace(), analysis_id=AID, attempt=1,
            pipeline='wgs', dag_run_id='replacement', resume_action_id=None,
            now=now + timedelta(seconds=1),
            worker_observation=dict(challenge, cce_recovery_evidence=quiet))
        assert stale['status'] == 'needs_attention'
        action = session.scalar(recovery_actions)
        assert action.payload_json['worker_wait']['state'] == 'waiting'
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count'] == 1
    with store.begin() as session:
        session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor')).generation = 1
    # The real second POST contains the independent Worker nonce proof only.
    # Native permission belongs to this reservation, not the next HTTP request.
    with store() as session:
        followup = poll_compute_recovery(session=session, settings=settings,
            airflow_client=SimpleNamespace(), analysis_id=AID, attempt=1,
            pipeline='wgs', dag_run_id='replacement', resume_action_id=None,
            now=now + timedelta(seconds=1),
            worker_observation=dict(challenge, cce_recovery_evidence=quiet))
        assert followup['status'] == 'waiting'  # Original retry_at has not arrived.
        actions = session.scalars(recovery_actions).all()
        assert len(actions) == 1
        wait = actions[0].payload_json['worker_wait']
        assert wait['state'] == 'ready' and wait['last_nonce'] == challenge['nonce']
        assert wait['deadline'] == wait_deadline
        assert actions[0].payload_json['original_deadline'] == deadline
        assert actions[0].payload_json['source_monitor_terminal_binding']['execution_id'] == challenge['execution_id']
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count'] == 1
    with store.begin() as session:
        for action in session.scalars(recovery_actions).all():
            session.delete(action)
        run = session.scalar(select(AnalysisRun))
        run.params_json = dict(run.params_json, cce_recovery_budget=dict(
            run.params_json['cce_recovery_budget'], count=0))
        monitor = session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor'))
        monitor.terminal_payload_json = dict(monitor.terminal_payload_json,
                                             cce_recovery_evidence=quiet)
    assert main.internal_wgs_observer_deactivate(
        AID, observer_request)['lifecycle_status'] == 'draining'
    released = release(store, 'wgs', 'release_leases', dag_run_id='replacement',
                       native_stage_observation=failed)
    assert released['released'] and not released['retained']

    # Step1/prepare cleanup may reach observer-deactivate before Step3 exists.
    with store.begin() as session:
        monitor = session.scalar(select(WgsStageExecution).where(
            WgsStageExecution.stage_code == 'step3_monitor'))
        session.delete(monitor)
        session.scalar(select(ObserverRunState)).lifecycle_status = 'active'
    with pytest.raises(HTTPException):
        main.internal_wgs_observer_deactivate(AID, observer_request)
    with store.begin() as session:
        session.scalar(select(ObserverRunState)).lifecycle_status = 'stopped'
    assert main.internal_wgs_observer_deactivate(
        AID, observer_request)['lifecycle_status'] == 'stopped'
