"""Read-only recovery UI: durable actions are not proof that a Master started."""
from copy import deepcopy
from datetime import timedelta
import pytest
from sqlalchemy import select

from app.models import AnalysisRun, RunAction, WgsStageExecution, PipelineStageExecution
from app.run_service import get_run_detail
from test_cce_recovery_budget import run_store, reserve, NOW


def view(session, run, now=NOW):
    from app.cce_recovery_projection import recovery_views
    return recovery_views(session=session, runs=[run], now=now).get(run.analysis_id)


def execution(session, run, status='accepted', generation=2, payload=None, stage='step3_monitor'):
    model = WgsStageExecution if run.pipeline_name == 'wgs' else PipelineStageExecution
    kw = dict(analysis_id=run.analysis_id, attempt=run.attempt, stage_code=stage,
        execution_id=f'current-{generation}', generation=generation, status=status,
        request_hash='a'*64, release_id='frozen', terminal_payload_json=payload or {})
    if run.pipeline_name == 'gatk': kw['pipeline_name']='gatk'
    row=model(**kw);session.add(row);session.flush()
    return row


def test_wait_is_projected_by_detail_without_modifying_status_or_budget(run_store):
    reserve(run_store)
    with run_store() as s:
        run=s.scalar(select(AnalysisRun)); before=deepcopy(run.params_json)
        result=get_run_detail(session=s,analysis_id=run.analysis_id)
        # Real endpoint serializer, not an unused helper.
        assert 'recovery' in result
        from app.dashboard_service import get_dashboard_runs
        tracker=get_dashboard_runs(session=s,airflow_client=None,pipeline=run.pipeline_name,
            status=None,keyword=None,limit=10,offset=0)
        assert tracker['items'][0]['recovery']==result['recovery']
        result=view(s,run)
        assert result['state']=='waiting' and result['ordinal']==1
        assert result['next_retry_at']=='2026-09-22T00:01:00+00:00'
        assert run.status=='failed' and run.params_json==before and not s.dirty


def test_queued_or_running_controller_is_not_confirmed_replacement_master(run_store):
    data=reserve(run_store)
    with run_store.begin() as s:
        run=s.scalar(select(AnalysisRun));run.dag_run_id='replacement'
        run.params_json=dict(run.params_json,resume_action_id=data['action_id'])
        action=s.scalar(select(RunAction));action.result_status='queued'
        action.payload_json=dict(action.payload_json,dag_run_id='replacement',generation=2)
        row=execution(s,run,status='running')
        assert view(s,run)['state']=='waiting'
        row.terminal_payload_json={'cce_master_binding':{'schema_version':2,
            'platform_execution':dict(pipeline=run.pipeline_name,analysis_id=run.analysis_id,
                attempt=1,stage='step3_monitor',execution_id=row.execution_id,generation=2,request_hash=row.request_hash),
            'native':{'job_uid':'replacement-uid','pod_uid':'replacement-pod',
                'recovery_context':{'action':data['action_id']}}}}
        assert view(s,run)['state']=='recovering'
        # New generation without binding supersedes the previous positive evidence.
        execution(s,run,status='accepted',generation=3)
        assert view(s,run)['state']=='stale'


@pytest.mark.parametrize('status,when,want', [('uncertain',0,'checking'),('rejected',0,'needs_attention'),('reserved',3601,'needs_attention')])
def test_unconfirmed_rejected_and_expired_actions_never_claim_running(run_store,status,when,want):
    reserve(run_store)
    with run_store.begin() as s:
        run=s.scalar(select(AnalysisRun));action=s.scalar(select(RunAction))
        action.result_status=status;action.message='/private/token=never-publish'
        result=view(s,run,NOW+timedelta(seconds=when))
        assert result['state']==want
        assert '/private' not in str(result)


def test_old_attempt_and_user_stop_are_not_overridden(run_store):
    reserve(run_store)
    with run_store.begin() as s:
        run=s.scalar(select(AnalysisRun))
        run.status='paused'; assert view(s,run) is None
        run.status='failed';run.attempt=2; assert view(s,run) is None


def test_step4_uncertain_wait_and_started_use_original_execution(run_store):
    with run_store.begin() as s:
        run=s.scalar(select(AnalysisRun));run.current_stage='step4_publish';run.dag_run_id='original'
        row=execution(s,run,stage='step4_publish')
        a=RunAction(analysis_id=run.analysis_id,action='cce_publish_dispatch',result_status='uncertain',
            payload_json=dict(pipeline=run.pipeline_name,attempt=1,stage='step4_publish',workdir=run.workdir,
                dag_run_id='original',execution_id=row.execution_id,generation=2,request_hash=row.request_hash,
                sequence=0,deadline=(NOW+timedelta(hours=1)).isoformat(),in_flight=True))
        s.add(a);s.flush()
        assert view(s,run)['state']=='checking'
        a.result_status='waiting';a.payload_json=dict(a.payload_json,next_retry_at=(NOW+timedelta(seconds=60)).isoformat())
        assert view(s,run)['state']=='waiting'
        a.result_status='running';a.payload_json=dict(a.payload_json,started_observed=True)
        assert view(s,run) is None  # confirmed original publish, ordinary progress resumes
        a.result_status='exhausted';assert view(s,run)['state']=='needs_attention'


def test_monitoring_degraded_is_not_a_workflow_failure(run_store):
    with run_store.begin() as s:
        run=s.scalar(select(AnalysisRun));run.status='running'
        row=execution(s,run,status='running',payload={'monitoring_health':'degraded'})
        assert view(s,run)['state']=='stale'
        assert run.status=='running'
        run.status='success';row.status='success'
        run.current_stage='finalize'
        assert view(s,run)['state']=='completed_degraded'
        row.terminal_payload_json={'monitoring_health':'healthy'}
        assert view(s,run) is None


def test_real_status_ingestion_keeps_current_monitor_evidence(run_store,tmp_path,monkeypatch):
    import json
    from types import SimpleNamespace
    from app import gatk_runtime_service
    from app.wgs_observer import _ingest_runtime_stage_status
    data=reserve(run_store)
    with run_store.begin() as s:
        run=s.scalar(select(AnalysisRun));run.status='running'
        run.params_json=dict(run.params_json,orchestration_contract_version=2)
        row=execution(s,run)
        action=s.scalar(select(RunAction));action.result_status='queued'
        action.payload_json=dict(action.payload_json,generation=2)
        identity=dict(pipeline=run.pipeline_name,analysis_id=run.analysis_id,attempt=1,
            stage=row.stage_code,execution_id=row.execution_id,generation=2,request_hash=row.request_hash)
    root=tmp_path/'requests'
    path=root/identity['analysis_id']/'attempt-1'/'step3_monitor.request.status.json'
    path.parent.mkdir(parents=True)
    payload=dict(identity,schema_version='wgs-runtime.stage-status.v1',status='running',orchestration_contract_version=2,
        updated_at=NOW.isoformat(),monitoring_health='healthy',
        cce_master_binding=dict(schema_version=2,platform_execution=identity,
            native=dict(job_uid='new-master',pod_uid='new-pod',recovery_context={'action':data['action_id']})))
    monkeypatch.setattr(gatk_runtime_service,'_ingest_gatk_evidence',lambda **kw:None)
    def ingest():
        path.write_text(json.dumps(payload),encoding='utf-8')
        if identity['pipeline']=='wgs':
            _ingest_runtime_stage_status(run_store,root,path)
        else:
            with run_store() as s:
                gatk_runtime_service.sync_gatk_stage_status(session=s,
                    settings=SimpleNamespace(gatk_runtime_request_root=str(root)),
                    analysis_id=identity['analysis_id'],attempt=1,stage='step3_monitor')
    def current():
        with run_store() as s:
            return view(s,s.scalar(select(AnalysisRun)))
    ingest()
    assert current()['state']=='recovering'
    assert current()['last_confirmed_at']==NOW.isoformat()
    payload.update(monitoring_health='degraded',updated_at=(NOW+timedelta(seconds=30)).isoformat())
    ingest()
    assert current()['state']=='stale'
    assert current()['last_confirmed_at']==NOW.isoformat()
    # Replayed healthy evidence cannot clear a newer degraded observation.
    payload.update(monitoring_health='healthy',updated_at=NOW.isoformat())
    ingest()
    assert current()['state']=='stale'
    payload['updated_at']=(NOW+timedelta(seconds=60)).isoformat()
    ingest()
    assert current()['state']=='recovering'
    # Wrong execution proof is never a confirmed replacement Master.
    payload['cce_master_binding']['platform_execution']=dict(identity,execution_id='old')
    payload['updated_at']=(NOW+timedelta(seconds=90)).isoformat()
    ingest()
    assert current()['state']=='waiting'
