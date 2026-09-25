"""Real logger/plugin/native FINAL -> automatic evidence; synthetic API only."""
import copy
import hashlib
import json
import logging
from pathlib import Path

import pytest
from test_recovery_final import view_inputs, handoff, runtime, SubmissionManager, plugin_tests
from snakemake_logger_plugin_rule_status.failure_summary import FailureSummary
from snakemake_interface_logger_plugins.common import LogEvent


@pytest.fixture
def failed_master(view_inputs, monkeypatch, request):
    h, context = view_inputs
    active = getattr(request,'param',None) == 'active_worker'
    storage_rpc = getattr(request,'param',None) == 'storage_rpc'
    created = None
    platform = dict(pipeline=context['pipeline'], analysis_id=context['analysis_id'], attempt=1,
        stage='step3_monitor' if active else 'step2_master' if storage_rpc else getattr(request,'param','step2_master'), execution_id=context['execution_id'], generation=8, request_hash='b'*64)
    selected = h.bundle.parent/'selected'
    runtime._prepare_recovery_view(h.bundle, selected, h.contract, context=context, platform_execution=platform)
    record = dict(runtime._handoff_binding(selected,h.contract), **h.contract['identity'],
        job_name='master',job_uid='master-uid',pod_uid='pod-uid',deadline_epoch=1600,
        schema_version=2,state='START_CONFIRMED')
    runtime._atomic_write_text(runtime._master_handoff_path(selected,h.contract),json.dumps(record))
    monkeypatch.setattr(runtime,'_master_input_context',lambda:record)
    monkeypatch.setenv('CCE_INPUT_ROOT',str(selected))
    monkeypatch.setenv('CCE_RUN_ROOT',h.contract['paths']['run_dir'])
    Path(h.contract['paths']['run_dir']).mkdir()
    for phase in ('preflight','analysis'):
        env=runtime._recovery_phase_start(phase);root=Path(env['SNAKEMAKE_CCE_SUBMIT_EVIDENCE_DIR'])
        ctx=json.loads(Path(env['SNAKEMAKE_CCE_SUBMIT_CONTEXT_FILE']).read_bytes())
        clock=plugin_tests.Clock()
        failure=plugin_tests.admission()
        if storage_rpc:
            failure=plugin_tests.ApiException(status=500)
            failure.body=json.dumps(dict(kind='Status',apiVersion='v1',status='Failure',code=500,
                reason='InternalError',message='Internal error occurred: rpc error: code = Unavailable desc = connection reset by peer'))
        manager=SubmissionManager(ctx,root,plugin_tests.API(root,(['success'] if active and phase=='analysis' else [])+[failure]*3),
            monotonic=clock.monotonic,sleep=clock.sleep)
        manager.claim_executor()
        audit=FailureSummary(root/'submit-context.json',root)
        event=logging.LogRecord('synthetic',logging.INFO,'synthetic',1,'',(),None)
        event.event=LogEvent.WORKFLOW_STARTED;audit.emit(event)
        if phase=='analysis':
            if active:
                requested = plugin_tests.body();requested.metadata.namespace=ctx['namespace']
                created=manager.submit(requested,1)
            requested=plugin_tests.body();requested.metadata.name='snakejob-absent'
            with pytest.raises(plugin_tests.module().SubmissionFailure):
                manager.submit(requested,1)
            event=logging.LogRecord('synthetic',logging.ERROR,'synthetic',1,'',(),None)
            event.event=LogEvent.ERROR;event.exception='SubmissionFailure';audit.emit(event)
        audit.close();runtime._recovery_phase_finished(phase,1 if phase=='analysis' else 0)
    base=Path(h.contract['paths']['run_dir'])/'evidence'/record['run_id']
    (base/'jobs.ndjson').write_text(json.dumps(dict(schema_version=2,external_jobid=created.metadata.name,
        kubernetes_uid=created.metadata.uid,attempt=1))+'\n' if created else '')
    terminal=runtime._bind_master_terminal(dict(schema_version=1,state='FAILED',failed_stage='analysis',
        exit_code=1,exit_codes=dict(preflight=0,analysis=1,final_dryrun=None),finished_epoch=1500))
    snapshot=json.loads((base/'recovery-final.json').read_bytes())
    evidence={'START_CONFIRMED.json':dict(record,confirmed_epoch=1000),
        'RUN_FAILED.json':terminal,'recovery-final.json':snapshot}
    assert runtime._write_mirror_evidence(selected,record['run_id'],evidence,project=record['project'],batch=record['batch'])
    native={k:record[k] for k in ('project','batch','run_id','job_name','job_uid','pod_uid','attempt',
        'execution_generation','request_hash','config_sha256','manifest_sha256','files_sha256','deadline_epoch','recovery_context')}
    native['namespace']=h.contract['kubernetes']['namespace']
    binding=dict(schema_version=2,platform_execution=platform,native=native,
        source_bundle=str(h.bundle),selected_bundle=str(selected))
    master=dict(kind='Job',metadata=dict(name='master',uid='master-uid',namespace=native['namespace'],
        labels={'cce.biosan.cn/run-id':'synthetic-run'}),status=dict(conditions=[dict(type='Failed',status='True')]))
    worker = dict(kind='Job',metadata=dict(name=created.metadata.name,uid=created.metadata.uid,
        namespace=native['namespace'],labels={'cce.biosan.cn/run-id':'synthetic-run'}),status=dict(active=1)) if created else None
    pod = dict(kind='Pod',metadata=dict(name='worker-pod',uid='worker-pod-uid',namespace=native['namespace'],
        labels={'cce.biosan.cn/run-id':'synthetic-run'},
        ownerReferences=[dict(kind='Job',name=created.metadata.name,uid=created.metadata.uid,controller=True)]),
        spec=dict(containers=[dict(name='worker')]),status=dict(phase='Running')) if created else None
    h.wait_worker, h.wait_pod = worker, pod
    def query(config,kind,*args,**kwargs):
        if kind=='job':return copy.deepcopy(master if args[0]=='master' else worker if worker and args[0]==worker['metadata']['name'] else None)
        items = [v for v in (master,worker) if v] if kind=='jobs' else [pod] if pod and args[1] in (
            'cce.biosan.cn/run-id=synthetic-run','job-name='+worker['metadata']['name']) else []
        return dict(kind='JobList' if kind=='jobs' else 'PodList',metadata={},items=copy.deepcopy(items))
    monkeypatch.setattr(runtime,'_recovery_query',query)
    return h,selected,binding,evidence,master


@pytest.mark.parametrize('failed_master',['active_worker'],indirect=True)
def test_final_active_worker_is_wait_only_then_fresh_terminal_proof(failed_master):
    from scripts.cce_recovery_failure import collect_failure_evidence
    from scripts.cce_recovery_inventory import lineage_workers
    from scripts.cce_recovery_workloads import probe_final_workloads
    h,selected,binding,_,_=failed_master
    def collect():
        return collect_failure_evidence(runtime=runtime,selected=selected,contract=h.contract,
            config=h.config,run_label='synthetic-run',binding=binding)
    before={str(p):p.read_bytes() for p in selected.rglob('*') if p.is_file()}
    first=collect()
    assert first['terminal']['active_worker_jobs']==first['terminal']['active_worker_pods']==1
    workers=lineage_workers(runtime,h.contract,selected,runtime._recovery_final_evidence(selected,h.contract,'master-uid'),())
    with pytest.raises(ValueError):
        probe_final_workloads(runtime=runtime,config=h.config,namespace=binding['native']['namespace'],
            run_label='synthetic-run',master_job='master',master_job_uid='master-uid',master_state='FAILED',workers=workers)
    h.wait_worker['status']=dict(conditions=[dict(type='Complete',status='True')])
    h.wait_pod['status']=dict(phase='Succeeded',containerStatuses=[dict(name='worker',state=dict(terminated=dict(exitCode=0)))])
    second=collect()
    assert second['terminal']['active_worker_jobs']==second['terminal']['active_worker_pods']==0
    second['terminal'].update(active_worker_jobs=1,active_worker_pods=1)
    assert second==first
    h.wait_pod['metadata']['ownerReferences'][0]['uid']='foreign'
    with pytest.raises(ValueError):collect()
    assert before=={str(p):p.read_bytes() for p in selected.rglob('*') if p.is_file()}


@pytest.mark.parametrize('failed_master',['active_worker'],indirect=True)
def test_same_uid_completion_is_reobserved_before_original_deadline(failed_master,monkeypatch):
    import time
    from scripts.cce_recovery_failure import collect_failure_evidence
    h,selected,binding,_,_=failed_master
    original=runtime._recovery_query
    worker=h.wait_worker['metadata']['name']
    changed=False
    full_lists=0
    def query(config,kind,*args,**kwargs):
        nonlocal changed,full_lists
        if kind=='jobs':full_lists+=1
        if kind=='pods' and args[1]=='job-name='+worker and not changed:
            h.wait_worker['status']={'conditions':[{'type':'Complete','status':'True'}]}
            h.wait_pod['status']={'phase':'Succeeded','containerStatuses':[{'name':'worker',
                'state':{'terminated':{'exitCode':0}}}]}
            changed=True
        return original(config,kind,*args,**kwargs)
    monkeypatch.setattr(runtime,'_recovery_query',query)
    result=collect_failure_evidence(runtime=runtime,selected=selected,contract=h.contract,
        config=h.config,run_label='synthetic-run',binding=binding,
        original_deadline_epoch=time.time()+120)
    assert result['terminal']['active_worker_jobs']==0
    assert result['terminal']['active_worker_pods']==0
    assert full_lists==2


@pytest.mark.parametrize('failed_master',['active_worker'],indirect=True)
def test_paired_failed_monitor_reuses_hashed_original_deadline_for_reobservation(failed_master,monkeypatch,tmp_path):
    import time
    from datetime import datetime,timezone
    from scripts import cce_paired_runtime as paired
    h,selected,binding,_,_=failed_master
    worker=h.wait_worker['metadata']['name']
    original=runtime._recovery_query
    changed=False
    def query(config,kind,*args,**kwargs):
        nonlocal changed
        if kind=='pods' and args[1]=='job-name='+worker and not changed:
            h.wait_worker['status']={'conditions':[{'type':'Complete','status':'True'}]}
            h.wait_pod['status']={'phase':'Succeeded','containerStatuses':[{'name':'worker',
                'state':{'terminated':{'exitCode':0}}}]}
            changed=True
        return original(config,kind,*args,**kwargs)
    monkeypatch.setattr(runtime,'_recovery_query',query)
    monkeypatch.setattr(paired,'_source_history',lambda *args:())
    deadline=datetime.fromtimestamp(time.time()+120,timezone.utc).isoformat()
    proof=paired._automatic_failure_evidence(
        {'stage':'step3_monitor','cce_recovery_deadline':deadline},
        {'master_state':'FAILED'},runtime=runtime,bundle=h.bundle,selected=selected,
        contract=h.contract,config=h.config,run_label='synthetic-run',exported=binding,
        request_root=tmp_path,pipeline=binding['platform_execution']['pipeline'])
    assert changed and proof['terminal']['active_worker_jobs']==0


@pytest.mark.parametrize('failed_master',['active_worker'],indirect=True)
def test_same_uid_master_gc_is_reobserved_from_fresh_lists(failed_master,monkeypatch):
    import time
    from scripts.cce_recovery_failure import collect_failure_evidence
    h,selected,binding,_,_=failed_master
    original=runtime._recovery_query
    removed=False
    full_lists=0
    def query(config,kind,*args,**kwargs):
        nonlocal removed,full_lists
        if kind=='jobs':
            full_lists+=1
            value=original(config,kind,*args,**kwargs)
            if removed:value['items']=[item for item in value['items'] if item['metadata']['name']!='master']
            return value
        if kind=='job' and args[0]=='master':
            removed=True
            return None
        return original(config,kind,*args,**kwargs)
    monkeypatch.setattr(runtime,'_recovery_query',query)
    proof=collect_failure_evidence(runtime=runtime,selected=selected,contract=h.contract,
        config=h.config,run_label='synthetic-run',binding=binding,
        original_deadline_epoch=time.time()+120)
    assert removed and full_lists==2 and proof['terminal']['active_worker_jobs']==1


@pytest.mark.parametrize('failed_master',['active_worker'],indirect=True)
def test_persistent_same_uid_movement_stops_after_three_fresh_lists(failed_master,monkeypatch):
    import time
    from scripts.cce_recovery_failure import collect_failure_evidence
    from scripts.cce_recovery_workloads import InventoryMoved
    h,selected,binding,_,_=failed_master
    original=runtime._recovery_query
    full_lists=0
    def query(config,kind,*args,**kwargs):
        nonlocal full_lists
        if kind=='jobs':full_lists+=1
        if kind=='job' and args[0]=='master':return None
        return original(config,kind,*args,**kwargs)
    monkeypatch.setattr(runtime,'_recovery_query',query)
    with pytest.raises(InventoryMoved):
        collect_failure_evidence(runtime=runtime,selected=selected,contract=h.contract,
            config=h.config,run_label='synthetic-run',binding=binding,
            original_deadline_epoch=time.time()+120)
    assert full_lists==3


@pytest.mark.parametrize('failed_master',['active_worker'],indirect=True)
def test_reobservation_never_accepts_after_original_deadline(failed_master,monkeypatch):
    import time
    from scripts.cce_recovery_failure import collect_failure_evidence
    h,selected,binding,_,_=failed_master
    original=runtime._recovery_query
    worker=h.wait_worker['metadata']['name']
    clock=[time.time()]
    full_lists=0
    def query(config,kind,*args,**kwargs):
        nonlocal full_lists
        if kind=='jobs':full_lists+=1
        if kind=='pods' and args[1]=='job-name='+worker:
            clock[0]+=2
            h.wait_worker['status']={'conditions':[{'type':'Complete','status':'True'}]}
            h.wait_pod['status']={'phase':'Succeeded','containerStatuses':[{'name':'worker',
                'state':{'terminated':{'exitCode':0}}}]}
        return original(config,kind,*args,**kwargs)
    monkeypatch.setattr(runtime,'_recovery_query',query)
    monkeypatch.setattr(time,'time',lambda:clock[0])
    with pytest.raises(ValueError):
        collect_failure_evidence(runtime=runtime,selected=selected,contract=h.contract,
            config=h.config,run_label='synthetic-run',binding=binding,
            original_deadline_epoch=clock[0]+1)
    assert full_lists==1


@pytest.mark.parametrize('change',[None,'mixed_rule','incomplete','native_identity','platform_identity','active_master'])
def test_actual_final_failure_evidence_keeps_native_and_platform_identity(failed_master,change):
    from scripts.cce_recovery_failure import collect_failure_evidence
    h,selected,binding,evidence,master=failed_master
    if change in {'mixed_rule','incomplete'}:
        audit=evidence['recovery-final.json']['phases']['analysis']['failure_summary']
        if change=='mixed_rule':audit['counts']['rule']=1
        else:audit['complete']=False
        evidence['RUN_FAILED.json']['submission_snapshot_sha256']=hashlib.sha256(
            runtime._recovery_encoded(evidence['recovery-final.json'])).hexdigest()
        runtime._write_mirror_evidence(selected,binding['native']['run_id'],evidence,
            project=binding['native']['project'],batch=binding['native']['batch'])
    elif change=='native_identity':binding['native']['request_hash']='c'*64
    elif change=='platform_identity':binding['platform_execution']['generation']=2
    elif change=='active_master':master['status']={'active':1}
    def collect():return collect_failure_evidence(runtime=runtime,selected=selected,contract=h.contract,
        config=h.config,run_label='synthetic-run',binding=binding)
    if change:
        with pytest.raises((RuntimeError,ValueError)):collect()
        return
    result=collect()
    assert result['terminal']['generation']==2
    assert result['terminal']['execution_id']=='exec-next:analysis'
    assert result['terminal']['request_hash']==binding['native']['request_hash']!='b'*64
    assert result['binding']['platform_execution']['generation']==8
    assert result['terminal']['rule_failure_count']==0
    assert result['terminal']['executor_failure_count']==1
    assert result['candidate']['failures'][0]['category']=='WORKER_CREATE_ADMISSION_TIMEOUT'


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs'}, {'pipeline':'gatk'}],indirect=True)
@pytest.mark.parametrize('failed_master',['step2_master','step3_monitor','storage_rpc'],indirect=True)
def test_schema2_evidence_through_normal_receipt_and_reservation(failed_master,tmp_path,monkeypatch):
    from datetime import datetime,timedelta,timezone
    from sqlalchemy import create_engine,select
    from sqlalchemy.orm import sessionmaker
    from app.models import AnalysisRun,Base,WgsStageExecution,PipelineStageExecution,RunAction
    from app.cce_recovery_service import reserve_monitored_recovery
    from scripts.cce_recovery_failure import collect_failure_evidence
    from scripts.cce_recovery_inventory import VerifiedMasterResult
    from scripts import wgs_runtime_gate,gatk_runtime_gate
    h,selected,binding,_,_=failed_master
    proof=collect_failure_evidence(runtime=runtime,selected=selected,contract=h.contract,
        config=h.config,run_label='synthetic-run',binding=binding)
    source=binding['platform_execution'];pipeline=source['pipeline']
    monitor=dict(source,stage='step3_monitor',execution_id='monitor',generation=9,request_hash='c'*64)
    result=VerifiedMasterResult({},binding,monitor,failure_evidence=proof)
    payload=dict(monitor,orchestration_contract_version=2,_cce_master_result=result)
    path=tmp_path/'step3.json'
    if pipeline=='wgs':
        monkeypatch.setattr(wgs_runtime_gate,'_sidecar_path',lambda p,s:path.with_suffix(s))
        wgs_runtime_gate._write_status(payload,'failed')
        receipt=json.loads(path.with_suffix('.status.json').read_bytes())
    else:receipt=gatk_runtime_gate._write_status(path,payload,'failed','synthetic')
    assert receipt['cce_recovery_evidence']==proof
    # Editing the exposed result cannot replace the evidence captured by the writer.
    result['cce_recovery_evidence']['terminal']['request_hash']='f'*64
    from scripts.cce_recovery_inventory import master_receipt_fields
    assert master_receipt_fields(payload,pipeline=pipeline,details={})['cce_recovery_evidence']==proof
    now=datetime(2026,9,25,tzinfo=timezone.utc);deadline=(now+timedelta(hours=1)).isoformat()
    engine=create_engine('sqlite+pysqlite://');Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,expire_on_commit=False)
    model=WgsStageExecution if pipeline=='wgs' else PipelineStageExecution
    extra={} if pipeline=='wgs' else dict(pipeline_name=pipeline)
    release='synthetic' if pipeline=='wgs' else 'synthetic@1'
    with factory.begin() as session:
        session.add(AnalysisRun(analysis_id=source['analysis_id'],pipeline_name=pipeline,dag_id='bio_'+pipeline,
            attempt=1,execution_mode='cce',status='failed',current_stage='step3_monitor',workdir='/platform/run',
            params_json=dict(pipeline_release_id=release,runtime_profile_id='synthetic',runtime_profile_revision=1,
                cce_recovery_policy=dict(version=1,attempt=1,enabled=True,original_deadline=deadline),
                cce_recovery_budget=dict(attempt=1,count=0,original_deadline=deadline))))
        session.flush()
        for execution,status,data in ((source,'success',{'cce_master_binding':binding}), (monitor,'failed',receipt)):
            session.add(model(**extra,analysis_id=source['analysis_id'],attempt=1,
                execution_id=execution['execution_id'],generation=execution['generation'],stage_code=execution['stage'],
                status=status,request_hash=execution['request_hash'],release_id=release,terminal_payload_json=data))
    def reserve():
        with factory.begin() as session:
            return reserve_monitored_recovery(session=session,analysis_id=source['analysis_id'],attempt=1,
                monitor_execution_id='monitor',evidence_root=tmp_path/'no-legacy-files',now=now)
    first=reserve();assert reserve()==first
    if proof['candidate']['failures'][0]['category']=='WORKER_CREATE_STORAGE_RPC_UNAVAILABLE':
        assert first['evidence_binding']['category']=='worker_create_storage_rpc_unavailable'
    assert first['source_execution_id']==source['execution_id']!='exec-next:analysis'
    assert first['evidence_binding']['submit_generation']==8
    assert first['evidence_binding']['submit_request_hash']=='b'*64
    with factory.begin() as session:
        row=session.scalar(select(model).where(model.execution_id=='monitor'))
        row.terminal_payload_json={**receipt,'cce_recovery_evidence':dict(proof,binding=dict(binding,
            platform_execution=dict(source,generation=2)))}
    with pytest.raises(ValueError):reserve()
    with factory() as session:
        assert len(session.scalars(select(RunAction)).all())==1
        assert session.scalar(select(AnalysisRun)).params_json['cce_recovery_budget']['count']==1
    engine.dispose()
