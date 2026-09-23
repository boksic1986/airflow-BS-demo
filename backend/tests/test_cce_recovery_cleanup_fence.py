"""Old DagRuns cannot release replacement leases or drain its observer."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import main
from app.models import AnalysisRun, Base, ObsTransferLease, ObserverRunState, RunAction, TransferJob


AID = 'SYNTHETIC_CLEANUP'
RELEASES = ['release_input_transfer_slot', 'release_result_transfer_slot', 'release_leases']


@pytest.fixture
def store(monkeypatch):
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
        gatk_execution_enabled=True, wgs_release_catalog_path='/synthetic/catalog'))
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
