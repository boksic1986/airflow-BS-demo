"""Existing manual entries must not race a pending automatic reservation."""
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models import AnalysisRun, RunAction, RunAttempt, WgsExecutionDispatch
from app import wgs_platform_service as platform
from test_wgs_resume_stage import AID, RELEASE, setup


@pytest.fixture
def legacy(setup, monkeypatch):
    factory, settings, client, path, _ = setup
    settings.wgs_release_catalog_path = '/synthetic/releases.yaml'
    lookups = []

    def catalog(path):
        lookups.append(str(path))

        def by_id(release):
            assert release == RELEASE
            return SimpleNamespace(release_id=RELEASE)

        return SimpleNamespace(by_id=by_id)

    # Only external release configuration is substituted. DB/action/dispatch and
    # submission paths run unchanged; the existing fixture substitutes Airflow.
    monkeypatch.setattr(platform, 'load_wgs_release_catalog', catalog)
    return factory, settings, client, path, lookups


def action(legacy, name):
    factory, settings, client, _, _ = legacy
    with factory() as session:
        return platform.action_wgs_run(session=session, settings=settings,
            airflow_client=client, analysis_id=AID, action=name, requested_by='operator')


@pytest.mark.parametrize('name', ['resume', 'rerun_failed'])
@pytest.mark.parametrize('state,payload', [
    ('reserved', {'attempt': 1}), ('queued', {'attempt': 1}),
    ('uncertain', {'attempt': 1}), ('reserved', {}),
    ('reserved', {'attempt': '1'}),
])
def test_legacy_retry_cannot_replace_attempt_during_automatic_recovery(legacy, name, state, payload):
    factory, _, client, path, lookups = legacy
    original = path.read_bytes()
    with factory.begin() as session:
        session.add(RunAction(analysis_id=AID, action='cce_compute_recovery',
            result_status=state, payload_json=payload))
    with pytest.raises(ValueError, match='automatic recovery'):
        action(legacy, name)
    assert client.posts == [] and lookups == [] and path.read_bytes() == original
    with factory() as session:
        run = session.scalar(select(AnalysisRun))
        assert run.attempt == 1 and run.status == 'failed' and run.dag_run_id == 'original'
        assert session.scalar(select(RunAttempt)) is None
        assert session.scalar(select(WgsExecutionDispatch)) is None
        assert len(session.scalars(select(RunAction)).all()) == 1


@pytest.mark.parametrize('name', ['resume', 'rerun_failed'])
def test_finished_automatic_history_does_not_disable_legacy_retry(legacy, name):
    factory, _, client, _, _ = legacy
    with factory.begin() as session:
        session.add(RunAction(analysis_id=AID, action='cce_compute_recovery',
            result_status='failed', payload_json={'attempt': 1, 'ordinal': 2}))
    result = action(legacy, name)
    assert result['attempt'] == 2 and result['status'] == 'submitted'
    assert len(client.posts) == 1 and client.posts[0][2]['attempt'] == 2
    with factory() as session:
        prior = session.scalar(select(RunAction).where(RunAction.action == 'cce_compute_recovery'))
        assert prior.payload_json == {'attempt': 1, 'ordinal': 2} and prior.result_status == 'failed'


def test_cancel_keeps_priority_over_pending_automatic_recovery(legacy):
    factory, _, client, _, lookups = legacy
    with factory.begin() as session:
        session.add(RunAction(analysis_id=AID, action='cce_compute_recovery',
            result_status='reserved', payload_json={'attempt': 1}))
    result = action(legacy, 'cancel')
    assert result['status'] == 'cancel_requested' and result['attempt'] == 1
    assert client.posts == [] and lookups == []


def test_locked_run_refreshes_stale_session_attempt_before_fence(legacy):
    factory, settings, client, _, _ = legacy
    with factory() as stale:
        held = stale.scalar(select(AnalysisRun))
        assert held.attempt == 1
        with factory.begin() as fresh:
            fresh.scalar(select(AnalysisRun)).attempt = 2
            fresh.add(RunAction(analysis_id=AID, action='cce_compute_recovery',
                result_status='reserved', payload_json={'attempt': 2}))
        with pytest.raises(ValueError, match='automatic recovery'):
            platform.action_wgs_run(session=stale, settings=settings, airflow_client=client,
                analysis_id=AID, action='resume', requested_by='operator')
        assert held.attempt == 2
    assert client.posts == []
