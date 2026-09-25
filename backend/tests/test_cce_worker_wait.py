"""One durable Airflow action waits, without changing the failed receipt."""
from copy import deepcopy
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import AnalysisRun, RunAction
from app.cce_recovery_poll import poll_compute_recovery
from test_cce_recovery_dispatch import automatic, setup, recovery, evidence, NOW


@pytest.fixture
def waiting(automatic):
    fixture, model, aid, _ = automatic
    factory = fixture[0]
    with factory.begin() as session:
        session.delete(session.scalar(select(RunAction)))
        run = session.scalar(select(AnalysisRun))
        run.params_json = dict(run.params_json, cce_recovery_budget=dict(
            run.params_json['cce_recovery_budget'], count=0))
        row = session.scalar(select(model).where(model.stage_code=='step3_monitor'))
        value = deepcopy(row.terminal_payload_json)
        value['cce_recovery_evidence']['terminal'].update(active_worker_jobs=1, active_worker_pods=1)
        row.terminal_payload_json = value
    def poll(seconds, observation=None):
        with factory() as session:
            return poll_compute_recovery(session=session,settings=fixture[1],airflow_client=fixture[2],
                analysis_id=aid,attempt=1,pipeline='wgs' if aid.startswith('WGS_') else 'gatk',
                dag_run_id='original',resume_action_id=None,now=NOW+timedelta(seconds=seconds),
                worker_observation=observation)
    def observed(challenge, active=False):
        proof=deepcopy(value['cce_recovery_evidence'])
        proof['terminal'].update(active_worker_jobs=int(active),active_worker_pods=int(active))
        return dict(challenge,cce_recovery_evidence=proof)
    return automatic, poll, observed, value


def test_wait_replays_one_action_then_dispatches_without_rewriting_terminal(waiting):
    case, poll, observed, original = waiting
    fixture, model, _, _ = case
    first = poll(0)
    assert first['status']=='waiting' and first['worker_probe']
    challenge = first['worker_probe']
    assert poll(30)['worker_probe']==challenge
    second = poll(60, observed(challenge, active=True))
    assert second['status']=='waiting'
    assert second['worker_probe']['nonce'] != challenge['nonce']
    assert poll(61, observed(challenge))['worker_probe']==second['worker_probe']
    from app.cce_compute_dispatch import dispatch_due_recovery
    with fixture[0]() as session:
        aid=case[2]
        assert dispatch_due_recovery(session=session,settings=fixture[1],airflow_client=fixture[2],
            analysis_id=aid,attempt=1,action_id=first['action_id'],now=NOW+timedelta(seconds=62))['status']=='waiting'
    assert not fixture[2].posts
    assert poll(90, observed(second['worker_probe']))['status']=='delegated'
    assert len(fixture[2].posts)==1
    with fixture[0]() as session:
        action = session.scalar(select(RunAction))
        assert action.payload_json['worker_wait']['deadline']==(NOW+timedelta(seconds=600)).isoformat()
        assert action.payload_json['worker_wait']['state']=='ready'
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count']==1
        old = session.scalar(select(model).where(model.stage_code=='step3_monitor',model.generation==1))
        assert old.terminal_payload_json==original


@pytest.mark.parametrize('fault', ['timeout','original_deadline','stop','changed_proof','unknown_probe'])
def test_wait_fails_closed_without_post_or_new_slot(waiting, fault):
    case, poll, observed, _ = waiting
    fixture, _, _, _ = case
    if fault=='original_deadline':
        with fixture[0].begin() as session:
            run = session.scalar(select(AnalysisRun));params=deepcopy(run.params_json)
            for name in ('cce_recovery_policy','cce_recovery_budget'):
                params[name]['original_deadline']=(NOW+timedelta(seconds=100)).isoformat()
            run.params_json=params
    first=poll(0)
    assert first['status']=='waiting'
    reply=observed(first['worker_probe'])
    if fault=='stop':
        with fixture[0].begin() as session:session.scalar(select(AnalysisRun)).status='cancel_requested'
    if fault=='changed_proof':reply['cce_recovery_evidence']['terminal']['submission_snapshot_sha256']='f'*64
    if fault=='unknown_probe':reply['nonce']='b'*32
    seconds=600 if fault=='timeout' else 100 if fault=='original_deadline' else 70
    assert poll(seconds,reply)['status']=='needs_attention'
    assert not fixture[2].posts
    with fixture[0]() as session:
        assert session.scalar(select(RunAction)).result_status=='rejected'
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count']==1
