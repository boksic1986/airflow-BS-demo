from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Base, AnalysisRun, Sample, RunAction
from app.wgs_submission_service import approve_wgs_config, mark_submission_dag_failed

@pytest.fixture
def setup():
    engine=create_engine('sqlite:///:memory:');Base.metadata.create_all(engine)
    with Session(engine) as s:
        r=AnalysisRun(analysis_id='MOCK',pipeline_name='wgs',dag_id='bio_wgs',dag_run_id='MOCK-a1',workdir='/synthetic',attempt=1,status='running',params_json={'submission_mode':'three_stage','submission_phase':'config_review'})
        s.add(r);s.add(Sample(analysis_id='MOCK',sample_id='CANDIDATE',status='pending',metadata_json={'selection_attempt':1,'selection_decision':'candidate'}));s.commit()
        yield s,r

class Airflow:
    state='running';fail=False;downstream=False
    def list_task_instances(self,dag,run):
        assert (dag,run)==('bio_wgs','MOCK-a1')
        return {'task_instances':[{'task_id':'prepare_wgs_sampleinfo','state':'success'},{'task_id':'wait_prepare_wgs_sampleinfo','state':'success'},{'task_id':'wait_wgs_config_approval','state':'up_for_reschedule'},{'task_id':'prepare_wgs_analysis','state':'running' if self.downstream else None}]}
    def stop_submission_dag(self,dag,run):
        if self.fail: raise TimeoutError('synthetic timeout')
        assert (dag,run)==('bio_wgs','MOCK-a1');self.state='failed'
    def get_dag_run(self,dag,run):return {'dag_run_id':run,'state':self.state}

def cancel(s,a,attempt=1):
    from app.wgs_submission_cancel import cancel_config_submission
    return cancel_config_submission(session=s,airflow_client=a,analysis_id='MOCK',attempt=attempt,requested_by='operator')

def test_cancel_retains_audit_and_candidate_identity(setup):
    s,r=setup;a=Airflow();cancel(s,a)
    assert r.status=='cancelled' and r.params_json['submission_phase']=='cancelled'
    sample=s.scalar(select(Sample));assert sample.status=='cancelled'
    assert sample.metadata_json['selection_decision']=='candidate'
    assert a.state=='failed'
    cancel(s,a);assert len(s.scalars(select(RunAction)).all())==1

@pytest.mark.parametrize('change',[{'submission_phase':'execution_review'},{'config_approved_at':'already'},{'submission_mode':'auto_dispatch'}])
def test_rejects_post_config_or_auto(setup,change):
    s,r=setup;r.params_json={**r.params_json,**change};s.commit()
    with pytest.raises(ValueError):cancel(s,Airflow())
    assert r.status=='running'

def test_rejects_old_attempt_and_active_downstream(setup):
    s,r=setup
    with pytest.raises(ValueError):cancel(s,Airflow(),2)
    a=Airflow();a.downstream=True
    with pytest.raises(ValueError):cancel(s,a)
    assert r.status=='running'

def test_timeout_keeps_fence_and_allows_retry(setup):
    s,r=setup;a=Airflow();a.fail=True
    with pytest.raises(TimeoutError):cancel(s,a)
    assert r.params_json['submission_phase']=='cancelling_submission'
    with pytest.raises(ValueError):approve_wgs_config(session=s,analysis_id='MOCK',requested_by='operator',use_reference='all',resource_set='default')
    a.fail=False;cancel(s,a);assert r.status=='cancelled'

def test_cancelled_not_overwritten_by_airflow_failure(setup):
    s,r=setup;cancel(s,Airflow())
    mark_submission_dag_failed(session=s,analysis_id='MOCK',attempt=1,failed_task_ids=['wait_wgs_config_approval'])
    assert r.status=='cancelled'

def test_config_approval_wins_before_cancel(setup):
    s,r=setup
    approve_wgs_config(session=s,analysis_id='MOCK',requested_by='operator',use_reference='all',resource_set='default')
    with pytest.raises(ValueError):cancel(s,Airflow())
    assert r.params_json['submission_phase']=='preparing_analysis'

def test_sync_api_preserves_cancelled(setup):
    from app.diagnostics_service import sync_wgs_airflow_status
    s,r=setup;cancel(s,Airflow())
    sync_wgs_airflow_status(session=s,airflow_client=Airflow(),analysis_id='MOCK',settings=SimpleNamespace())
    assert r.status=='cancelled'

def test_pending_and_other_attempt_samples_are_untouched(setup):
    s,r=setup
    s.add(Sample(analysis_id='MOCK',sample_id='PENDING',status='pending',metadata_json={'selection_decision':'pending','selection_attempt':1,'pending_reason':'waiting'}))
    s.add(Sample(analysis_id='MOCK',sample_id='OLD',status='success',metadata_json={'selection_decision':'selected','selection_attempt':0}));s.commit()
    cancel(s,Airflow())
    samples={x.sample_id:x for x in s.scalars(select(Sample))}
    assert samples['PENDING'].status=='pending' and samples['PENDING'].metadata_json['pending_reason']=='waiting'
    assert samples['OLD'].status=='success'

def test_airflow_stop_uses_patch_without_deleting_history():
    import httpx
    from app.airflow_client import AirflowClient
    seen=[]
    def handle(request):
        seen.append((request.method,request.url.path,request.content))
        return httpx.Response(200,json={'state':'failed'})
    c=AirflowClient(base_url='http://mock',username='mock',password='mock',transport=httpx.MockTransport(handle))
    c.stop_submission_dag('bio_wgs','MOCK-a1')
    assert seen==[('PATCH','/api/v1/dags/bio_wgs/dagRuns/MOCK-a1',b'{"state":"failed"}')]

def test_retry_after_remote_stop_succeeded_but_response_lost(setup):
    s,r=setup;a=Airflow();a.fail=True
    with pytest.raises(TimeoutError):cancel(s,a)
    a.fail=False;a.state='failed'
    a.list_task_instances=lambda *args: {'task_instances':[]}
    cancel(s,a)
    assert r.status=='cancelled'
