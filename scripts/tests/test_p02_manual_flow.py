"""Authenticated service -> real DAG subprocess -> restricted native flow.

Only synthetic SQLite, HTTP/SSH transport and Kubernetes/OBS boundaries are used.
Run in the approved cached Airflow image with paired native/backend dependencies.
"""
import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

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
    request.write_text(json.dumps(payload))
    if pipeline=='wgs':
        binding_path=bundle.parent/'batch-binding.json'
        binding=json.loads(binding_path.read_bytes())
        binding.update(schema_version='wgs-runtime.batch-binding.v2',pipeline_release_id='synthetic',
            wgs_source_commit='a'*40,resolved_runtime={})
        binding_path.write_text(json.dumps(binding))
    model=WgsStageExecution if pipeline=='wgs' else PipelineStageExecution
    with factory.begin() as session:
        session.add(AnalysisRun(analysis_id=aid,pipeline_name=pipeline,dag_id='bio_'+pipeline,
            dag_run_id='original',execution_mode='cce',workdir=str(bundle.parent),status='failed',
            current_stage='step2_master',attempt=1,params_json=params))
        for stage,status in [('step1_upload','success'),('step2_master','failed')]:
            values=dict(analysis_id=aid,attempt=1,stage_code=stage,status=status,generation=8,
                execution_id=payload['execution_id'] if stage=='step2_master' else 'completed-upload',
                request_hash=payload['request_hash'],receipt_hash='b'*64,release_id='synthetic')
            if pipeline=='gatk':values['pipeline_name']=pipeline
            session.add(model(**values))
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
    monkeypatch.setattr(main,'authenticate_session',lambda **kw:
        AuthenticatedUser(1,'synthetic-operator','operator','csrf') if kw['raw_token'] else None)
    monkeypatch.setenv('WGS_RUNTIME_ADAPTER_ENABLED','true')
    monkeypatch.setenv('WGS_EXECUTION_ENABLED','true')
    client=TestClient(main.app)
    try:
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
            value=dict(pipeline=pipeline,conf=conf,dag_run_id=dag_id,stage=stage,registration={'generation':9})
            result=subprocess.run(['/usr/local/bin/python',str(Path(__file__).with_name('p02_dag_transport.py'))],
                input=json.dumps(value),text=True,capture_output=True,env=env,timeout=45)
            assert result.returncode==0,result.stderr
            transport=json.loads(result.stdout)
            registrations=[c for c in transport['calls'] if '/stages/' in c['path']]
            assert len(registrations)==len(transport['commands'])==1
            assert all('/stages/' in c['path'] or c['path'].endswith('/observer/activate') for c in transport['calls'])
            call=registrations[0]
            assert call['payload']['dag_run_id']==dag_id
            if pipeline=='wgs':main.internal_wgs_runtime_stage(aid,stage,main.WgsRuntimeStageRequest(**call['payload']))
            else:main.internal_gatk_runtime_stage(aid,stage,main.GatkRuntimeStageRequest(**call['payload']))
            return json.loads(gate._request_path(aid,1,stage).read_bytes())
        def ingest(stage):
            if pipeline=='wgs':
                main.internal_wgs_runtime_stage_status(aid,attempt=1,stage=stage)
            else:
                from app.gatk_runtime_service import sync_gatk_stage_status
                with factory() as session:
                    sync_gatk_stage_status(session=session,settings=settings,analysis_id=aid,attempt=1,stage=stage)
        updated=register('step2_master');payload.clear();payload.update(updated)
        def launch():
            if pipeline=='wgs':
                from scripts import wgs_resume
                wgs_resume.run_resume_stage(payload,gate=gate);gate._write_status(payload,'success')
            else:gate._execute_stage(aid,1,'step2_master',payload['generation'])
            ingest('step2_master')
            return json.loads(request.with_suffix('.status.json').read_bytes())
        h.register_stage=register;h.ingest_stage=ingest
        native_flow((state,launch,gate,payload,request,policy,bundle,h),monkeypatch,'downstream')
        ingest('step6_materialize')
        with factory() as session:
            run=session.scalar(select(AnalysisRun));assert run.attempt==1 and run.workdir==str(bundle.parent)
            assert session.scalar(select(RunAction)).payload_json['action_id']==conf['resume_action_id']
            assert session.scalar(select(model).where(model.stage_code=='step6_materialize')).status=='success'
        assert len(airflow.posts)==1
    finally:
        client.close();engine.dispose()
