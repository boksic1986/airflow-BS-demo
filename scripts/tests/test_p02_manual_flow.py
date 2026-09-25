"""Authenticated service -> real DAG subprocess -> restricted native flow.

Only synthetic SQLite, HTTP/SSH transport and Kubernetes/OBS boundaries are used.
Run in the approved cached Airflow image with paired native/backend dependencies.
"""
import json
import hashlib
import os
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from threading import Timer

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from test_p02_selected_monitor import (registered,adapter,mirrored_final,final_inputs,view_inputs,handoff,
    runtime,test_fresh_monitor_uses_selected_master_and_rejects_stale_authority as native_flow)
from scripts import cce_paired_runtime as paired,wgs_runtime_gate


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
def test_authenticated_manual_flow(registered,monkeypatch,tmp_path):
    run_authenticated_flow(registered,monkeypatch,tmp_path)


def run_authenticated_flow(registered,monkeypatch,tmp_path,*,automatic=False):
    from app import main
    from app.models import Base,AnalysisRun,WgsStageExecution,PipelineStageExecution,RunAction
    from app.auth_service import AuthenticatedUser
    from app.pipeline_registry import PipelineRegistry
    from app.pipeline_registry_service import get_pipeline_registry
    state,_,gate,payload,request,policy,bundle,h=registered
    pipeline='wgs' if gate is wgs_runtime_gate else 'gatk'
    aid=payload['analysis_id']
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine);factory=sessionmaker(bind=engine,expire_on_commit=False)
    root=Path(__file__).parents[2]
    settings=SimpleNamespace(auth_required=True,internal_service_token='',
        pipeline_registry_path=str(root/'config/pipelines.yaml'),wgs_contract_v2_enabled=True,
        wgs_runtime_request_root=str(request.parent.parent.parent),wgs_runtime_shared_gid=None,
        wgs_stage_contract_path=str(root/'config/wgs_stage_contract.yaml'),
        wgs_transfer_spool_root=str(tmp_path/'transfers'),gatk_execution_enabled=True,
        gatk_runtime_request_root=str(request.parent.parent.parent),gatk_runtime_node200_root=str(bundle.parents[3]),
        gatk_transfer_spool_root=str(tmp_path/'transfers'),gatk_evidence_root=str(tmp_path/'evidence'))
    payload.pop('resume_action_id')
    params={'orchestration_contract_version':2}
    if pipeline=='wgs':
        payload.update(pipeline_release_id='synthetic',wgs_source_commit='a'*40,
            expected_batch_root=str(bundle.parent))
        params.update(pipeline_release_id='synthetic',wgs_source_commit='a'*40)
    else:
        payload.update(profile_id='synthetic',profile_revision='r1')
        params.update(runtime_profile_id='synthetic',runtime_profile_revision='r1')
    payload['request_hash']=paired._request_digest(payload,pipeline)
    if automatic:
        assert payload==h.initial_payload
    request.write_text(json.dumps(payload))
    source = dict(payload)
    proof = None
    if automatic:
        from datetime import datetime,timedelta,timezone
        from scripts.cce_recovery_failure import collect_failure_evidence
        from scripts.cce_recovery_inventory import VerifiedMasterResult
        now=datetime.now(timezone.utc)
        deadline=(now+timedelta(hours=1)).isoformat()
        params.update(cce_recovery_policy=dict(version=1,attempt=1,enabled=True,original_deadline=deadline),
            cce_recovery_budget=dict(attempt=1,count=0,original_deadline=deadline))
        record=state.record
        native={k:record[k] for k in ('project','batch','run_id','job_name','job_uid','pod_uid',
            'attempt','execution_generation','request_hash','config_sha256','manifest_sha256',
            'files_sha256','deadline_epoch','recovery_context')}
        native['namespace']=h.contract['kubernetes']['namespace']
        platform=dict(pipeline=pipeline,**{k:source[k] for k in
            ('analysis_id','attempt','stage','execution_id','generation','request_hash')})
        bound=dict(schema_version=2,platform_execution=platform,native=native,
            source_bundle=str(bundle),selected_bundle=str(bundle))
        proof=collect_failure_evidence(runtime=runtime,selected=bundle,contract=h.contract,
            config=h.config,run_label='synthetic-run',binding=bound)
        assert proof is not None
        payload.update(stage='step3_monitor',execution_id=aid+'-a1-step3_monitor-g8',
            predecessor_execution_id=source['execution_id'],predecessor_generation=8,
            predecessor_receipt_hash='b'*64,cce_recovery_deadline=deadline)
        payload['request_hash']=paired._request_digest(payload,pipeline)
        request=gate._request_path(aid,1,'step3_monitor');request.write_text(json.dumps(payload))
        monitor=dict(pipeline=pipeline,**{k:payload[k] for k in
            ('analysis_id','attempt','stage','execution_id','generation','request_hash')})
        payload['_cce_master_result']=VerifiedMasterResult({},bound,monitor,failure_evidence=proof)
        if pipeline=='wgs':gate._write_status(payload,'failed')
        else:gate._write_status(request,payload,'failed','synthetic failure')
        payload.pop('_cce_master_result')
        failed_receipt=json.loads(request.with_suffix('.status.json').read_bytes())
    if pipeline=='wgs':
        binding_path=bundle.parent/'batch-binding.json'
        binding=json.loads(binding_path.read_bytes())
        binding.update(schema_version='wgs-runtime.batch-binding.v2',pipeline_release_id='synthetic',
            wgs_source_commit='a'*40,resolved_runtime={})
        binding_path.write_text(json.dumps(binding))
    model=WgsStageExecution if pipeline=='wgs' else PipelineStageExecution
    workdir=str(request.parent) if automatic and pipeline=='wgs' else str(bundle.parent)
    with factory.begin() as session:
        session.add(AnalysisRun(analysis_id=aid,pipeline_name=pipeline,dag_id='bio_'+pipeline,
            dag_run_id='original',execution_mode='cce',workdir=workdir,status='failed',
            current_stage='step3_monitor' if automatic else 'step2_master',attempt=1,params_json=params))
        for stage,status in [('step1_upload','success'),('step2_master','failed')]:
            values=dict(analysis_id=aid,attempt=1,stage_code=stage,status='success' if automatic else status,generation=8,
                execution_id=source['execution_id'] if stage=='step2_master' else 'completed-upload',
                request_hash=source['request_hash'],receipt_hash='b'*64,release_id='synthetic',
                terminal_payload_json={'cce_master_binding':bound} if automatic and stage=='step2_master' else {})
            if pipeline=='gatk':values['pipeline_name']=pipeline
            session.add(model(**values))
        if automatic:
            values=dict(analysis_id=aid,attempt=1,stage_code='step3_monitor',status='failed',generation=8,
                execution_id=payload['execution_id'],request_hash=payload['request_hash'],
                release_id='synthetic' if pipeline=='wgs' else 'synthetic@r1',terminal_payload_json=failed_receipt)
            if pipeline=='gatk':values['pipeline_name']=pipeline
            session.add(model(**values))
            # Both source/monitor release identities must match the frozen adapter.
            if pipeline=='gatk':
                for row in session.new:
                    if isinstance(row,model):row.release_id='synthetic@r1'
    class Airflow:
        def __init__(self):self.posts=[];self.runs={}
        def get_dag_run(self,dag,identity):
            if identity not in self.runs:
                raise httpx.HTTPStatusError('missing',request=httpx.Request('GET','http://synthetic'),response=httpx.Response(404))
            return self.runs[identity]
        def trigger_dag_run(self,dag,*,dag_run_id,conf):
            self.posts.append((dag,dag_run_id,conf))
            self.runs[dag_run_id]=dict(dag_run_id=dag_run_id,conf=conf,state='queued')
            raise httpx.ReadTimeout('lost synthetic POST response')
    airflow=Airflow()
    definition=get_pipeline_registry(settings).get(pipeline)
    registry=PipelineRegistry({pipeline:replace(definition,capabilities=definition.capabilities|{'resume'})})
    monkeypatch.setattr(main,'get_settings',lambda:settings)
    monkeypatch.setattr(main,'get_sessionmaker',lambda:factory)
    monkeypatch.setattr(main,'get_airflow_client',lambda:airflow)
    monkeypatch.setattr(main,'get_pipeline_registry',lambda _:registry)
    if pipeline=='wgs':
        from app.wgs_release_catalog import WgsRelease,WgsReleaseCatalog
        settings.wgs_release_catalog_path='/synthetic/catalog'
        catalog=WgsReleaseCatalog(WgsRelease('synthetic','V0.0.0','a'*40,
            '/synthetic/source','/synthetic/source','1'))
        monkeypatch.setattr(main,'load_wgs_release_catalog',lambda _:catalog)
    monkeypatch.setattr(main,'authenticate_session',lambda **kw:
        AuthenticatedUser(1,'synthetic-operator','operator','csrf') if kw['raw_token'] else None)
    monkeypatch.setenv('WGS_RUNTIME_ADAPTER_ENABLED','true')
    monkeypatch.setenv('WGS_EXECUTION_ENABLED','true')
    client=TestClient(main.app)
    try:
        if automatic:
            from app.cce_recovery_poll import poll_compute_recovery
            def poll(seconds):
                with factory() as session:
                    return poll_compute_recovery(session=session,settings=settings,airflow_client=airflow,
                        analysis_id=aid,attempt=1,pipeline=pipeline,dag_run_id='original',resume_action_id=None,
                        now=now+timedelta(seconds=seconds))
            assert poll(0)['status']=='waiting' and not airflow.posts
            assert poll(60)['status']=='delegated'
            assert poll(61)['status']=='delegated'
        else:
            body={'attempt':1,'stage':'step2_master','idempotency_key':'one-click'}
            assert client.post(f'/api/runs/{aid}/actions/resume-stage',json=body).status_code in (401,403)
            client.cookies.set(main.SESSION_COOKIE,'session');client.headers['X-CSRF-Token']='csrf'
            response=client.post(f'/api/runs/{aid}/actions/resume-stage',json=body)
            assert response.status_code==200,response.text
            assert client.post(f'/api/runs/{aid}/actions/resume-stage',json=body).json()==response.json()
        assert len(airflow.posts)==1
        _,dag_id,conf=airflow.posts[0]
        def register(stage):
            # DAG uses its own SQLAlchemy 1.4 environment; backend/native use 2.x.
            env={**os.environ,'PYTHONPATH':str(root/'dags')+':/home/airflow/.local/lib/python3.11/site-packages'}
            value=dict(pipeline=pipeline,conf=conf,dag_run_id=dag_id,stage=stage)
            process=subprocess.Popen(['/usr/local/bin/python',str(Path(__file__).with_name('p02_dag_transport.py'))],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
            timer=Timer(45,process.kill);timer.start()
            result=None
            try:
                process.stdin.write(json.dumps(value)+'\n');process.stdin.flush()
                for line in process.stdout:
                    transport=json.loads(line)
                    if 'backend' not in transport:break
                    call=transport['backend'];called_stage=call['path'].rsplit('/',1)[-1]
                    if '/stages/' not in call['path']:
                        assert call['path'].endswith('/observer/activate')
                        result={}
                    elif pipeline=='wgs':
                        result=main.internal_wgs_runtime_stage(aid,called_stage,main.WgsRuntimeStageRequest(**call['payload']))
                    else:result=main.internal_gatk_runtime_stage(aid,called_stage,main.GatkRuntimeStageRequest(**call['payload']))
                    process.stdin.write(json.dumps(result)+'\n');process.stdin.flush()
                process.wait(timeout=5)
                assert process.returncode==0,process.stderr.read()
            finally:
                timer.cancel()
                if process.poll() is None:process.kill();process.wait()
                process.stdin.close();process.stdout.close();process.stderr.close()
            registrations=[c for c in transport['calls'] if '/stages/' in c['path']]
            assert len(registrations)==(4 if automatic and stage=='step4_publish' else 1)
            assert len(transport['commands'])==(0 if stage=='finalize_run' else 1)
            assert all('/stages/' in c['path'] or c['path'].endswith('/observer/activate') for c in transport['calls'])
            call=registrations[0]
            assert call['payload']['dag_run_id']==dag_id
            if stage=='finalize_run':return result
            return json.loads(gate._request_path(aid,1,stage).read_bytes())
        def ingest(stage):
            if pipeline=='wgs':
                main.internal_wgs_runtime_stage_status(aid,attempt=1,stage=stage)
            else:
                from app.gatk_runtime_service import sync_gatk_stage_status
                with factory() as session:
                    sync_gatk_stage_status(session=session,settings=settings,analysis_id=aid,attempt=1,stage=stage)
        initial_stage='step3_monitor' if automatic else 'step2_master'
        updated=register(initial_stage);payload.clear();payload.update(updated)
        def launch():
            if automatic:
                if pipeline=='wgs':
                    gate._prepare_contract_generation(payload,request_sha=hashlib.sha256(request.read_bytes()).hexdigest())
                binding=gate._load_binding(payload)
                payload['_cce_master_result']=paired.resume_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
                if pipeline=='wgs':gate._write_status(payload,'running','replacement started')
                else:gate._write_status(request,payload,'running','replacement started')
            elif pipeline=='wgs':
                from scripts import wgs_resume
                wgs_resume.run_resume_stage(payload,gate=gate);gate._write_status(payload,'success')
            else:gate._execute_stage(aid,1,'step2_master',payload['generation'])
            ingest(initial_stage)
            return json.loads(request.with_suffix('.status.json').read_bytes())
        h.register_stage=register;h.ingest_stage=ingest
        h.real_query_transport=automatic
        native_flow((state,launch,gate,payload,request,policy,bundle,h),monkeypatch,'downstream')
        ingest('step6_materialize')
        assert register('finalize_run')['status']=='success'
        with factory() as session:
            run=session.scalar(select(AnalysisRun));assert run.attempt==1 and run.workdir==workdir
            assert run.status=='success' and run.current_stage=='finalize_run' and run.progress_percent==100
            assert session.scalar(select(RunAction)).payload_json['action_id']==conf['resume_action_id']
            assert session.scalar(select(model).where(model.stage_code=='step6_materialize')).status=='success'
            if automatic:
                assert run.params_json['cce_recovery_budget']['count']==1
                assert session.scalar(select(RunAction)).action=='cce_compute_recovery'
                assert session.scalar(select(model).where(model.stage_code=='step3_monitor',model.generation==8)).status=='failed'
                assert (state.creates,state.starts)==(1,1)
        assert len(airflow.posts)==1
    finally:
        client.close();engine.dispose()
