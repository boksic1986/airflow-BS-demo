"""A fresh monitor must reconstruct authority, not trust a deserialized receipt."""
import copy
import hashlib
import json
import os
import shutil
import traceback
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from test_p02_registered_recovery import registered
from test_p02_resume_final import adapter, mirrored_final, final_inputs, view_inputs, handoff as native_handoff, runtime
from scripts import cce_paired_runtime as paired, wgs_runtime_gate, gatk_runtime_gate, wgs_resume
from cce_pipeline.assets import step3_status
from test_recovery_final import SubmissionManager, plugin_tests
REAL_RELEASE=runtime._release_batch_lock
REAL_QUERY=runtime._recovery_query
REAL_LEGACY_QUERY=runtime._kubectl_json
REAL_GATK_LOAD_BINDING=gatk_runtime_gate._load_binding
REAL_PREPARE_WORKER_MANIFEST=runtime._prepare_worker_manifest


@pytest.mark.parametrize('view_inputs',[
    {'pipeline':'wgs','analysis_id':'WGS_20260926_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260926_000000_AAAAAA'}],indirect=True)
@pytest.mark.parametrize('adapter',[{'initial':True}],indirect=True)
@pytest.mark.parametrize('outcome',['normal','recovery'])
def test_normal_registration_preserves_step1_owner_through_ttl(registered,monkeypatch,outcome):
    """Catch missing registration and the future-Step2-ID lock dependency."""
    state,_,gate,upload,upload_path,policy,bundle,h=registered
    pipeline='wgs' if gate is wgs_runtime_gate else 'gatk'
    binding=json.loads((bundle.parent/'batch-binding.json').read_bytes())
    frozen={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}
    policy_before=policy.read_bytes()
    assert state.cms=={} and state.job is None and state.worker is None
    assert json.loads(policy_before).get('bindings',[])==[]
    # The inherited Master fixture stubs manifest preparation. New-attempt
    # coverage must execute it: only emulate its remote Pod filesystem I/O.
    monkeypatch.setattr(runtime,'_prepare_worker_manifest',REAL_PREPARE_WORKER_MANIFEST)
    native_transport=runtime._run
    def manifest_transport(command,**kwargs):
        evidence=Path(h.contract['paths']['run_dir'])/'evidence'/h.contract['identity']['run_id']
        if (command[5]=='exec' and '-c' in command and command[-1]==str(evidence)
                and 'jobs.ndjson' in command[command.index('-c')+1]):
            script=command[command.index('-c')+1]
            if 'path.touch(exist_ok=True)' in script:
                evidence.mkdir(parents=True,exist_ok=True)
                (evidence/'jobs.ndjson').touch(exist_ok=True)
                return subprocess.CompletedProcess(command,0,b'',b'')
            if 'sys.stdout.write' in script:
                return subprocess.CompletedProcess(command,0,(evidence/'jobs.ndjson').read_bytes(),b'')
        return native_transport(command,**kwargs)
    monkeypatch.setattr(runtime,'_run',manifest_transport)

    def save(payload):
        value={k:v for k,v in payload.items() if not k.startswith('_')}
        value['request_hash']=paired._request_digest(value,pipeline)
        path=gate._request_path(value['analysis_id'],value['attempt'],value['stage'])
        path.write_text(json.dumps(value))
        return value,path

    def succeed(payload,path,**details):
        if pipeline=='wgs':gate._write_status(payload,'success',**details)
        else:gate._write_status(path,payload,'success','completed',**details)
        return json.loads(path.with_suffix('.status.json').read_bytes())

    def next_stage(previous,previous_path,stage):
        receipt=json.loads(previous_path.with_suffix('.status.json').read_bytes())
        return save({**{k:v for k,v in upload.items() if not k.startswith('_')},
            'stage':stage,'execution_id':previous['analysis_id']+'-a1-'+stage+'-g1',
            'generation':1,'predecessor_execution_id':previous['execution_id'],
            'predecessor_receipt_hash':hashlib.sha256(previous_path.with_suffix('.status.json').read_bytes()).hexdigest()
                if pipeline=='wgs' else receipt['receipt_hash']})

    def finish_worker(payload,path):
        value={k:payload[k] for k in ('analysis_id','attempt','stage','execution_id','generation','request_hash')}
        if pipeline=='wgs':value.update(pid=999999999,boot_id='synthetic-ended',process_start_time='0')
        else:value.update(schema_version='gatk-runtime.dispatcher.v1',state='finished',process=None)
        path.with_suffix('.worker.json' if pipeline=='wgs' else '.worker.state.json').write_text(json.dumps(value))

    # The successful prepare boundary exists before Step1. Step2 does not.
    prepare,prepare_path=save({**upload,'stage':'prepare',
        'execution_id':upload['analysis_id']+'-a1-prepare-g1'})
    if pipeline=='gatk':
        immutable=dict(schema_version=1,kind='gatk-airflow-prepare',
            analysis_id=upload['analysis_id'],attempt=1,generation=1,output_root=str(bundle.parent))
        immutable['request_hash']=paired._request_digest(immutable,pipeline)
        prepare_path.write_text(json.dumps(immutable))
        prepare={**immutable,'stage':'prepare','generation':1,
            'execution_id':upload['analysis_id']+'-a1-prepare-g1'}
        repository=bundle.parent/'synthetic-repository'
        (repository/'scripts').mkdir(parents=True)
        (repository/'scripts'/'airflow_handoff.py').write_text('# external prepare transport fixture\n')
        monkeypatch.setenv('GATK_REPOSITORY_ROOT',str(repository))
        def prepared(command,**kwargs):
            assert command[2:]==['--handoff-request',str(prepare_path)]
            with pytest.raises(RuntimeError):
                paired._inactive_dispatcher(prepare_path,gate,pipeline)
            with pytest.raises(RuntimeError):
                gate.start(upload['analysis_id'],1,'prepare',generation=3)
            if gate._dispatch_state(prepare_path)['generation']==1:
                raise subprocess.CalledProcessError(1,command,stderr='synthetic first prepare failure')
            return subprocess.CompletedProcess(command,0,'synthetic prepare complete','')
        def spawn_prepare(command,**kwargs):
            generation=int(command[-1])
            pid=os.fork()
            if pid==0:
                # Emulate Popen(close_fds=True), including the launch flock
                # held by start(): the worker must obtain its own lock.
                os.closerange(3,int(os.sysconf('SC_OPEN_MAX')))
                try:gate._execute(upload['analysis_id'],1,'prepare',generation)
                except BaseException:
                    traceback.print_exc();os._exit(1)
                os._exit(0)
            return SimpleNamespace(pid=pid)
        with monkeypatch.context() as transport:
            transport.setattr(gate.subprocess,'run',prepared)
            transport.setattr(gate.subprocess,'Popen',spawn_prepare)
            first=spawn_prepare(['1'])
            assert os.waitpid(first.pid,0)[1]==256
            assert gate._dispatch_state(prepare_path)['state']=='finished'
            retry=[]
            def launch(command,**kwargs):
                process=spawn_prepare(command,**kwargs)
                retry.append(process.pid)
                return process
            transport.setattr(gate.subprocess,'Popen',launch)
            assert gate.start(upload['analysis_id'],1,'prepare',generation=2)=={
                'status':'accepted','stage':'prepare','generation':2}
            assert os.waitpid(retry[0],0)[1]==0
        prepare={**prepare,'generation':2,
            'execution_id':upload['analysis_id']+'-a1-prepare-g2'}
        ended=gate._dispatch_state(prepare_path)
        assert ended['generation']==2 and ended['execution_id']==prepare['execution_id']
        paired._inactive_dispatcher(prepare_path,gate,pipeline)
        worker_path=prepare_path.with_suffix('.worker.state.json')
        ended_bytes=worker_path.read_bytes()
        try:
            worker_path.write_text(json.dumps({**ended,'process':None}))
            with pytest.raises(RuntimeError,match='active or uncertain'):
                paired._inactive_dispatcher(prepare_path,gate,pipeline)
        finally:
            worker_path.write_bytes(ended_bytes)
        assert prepare_path.read_bytes()==json.dumps(immutable).encode()
        binding=json.loads((bundle.parent/'batch-binding.json').read_bytes())
        monkeypatch.setattr(gate,'_load_binding',REAL_GATK_LOAD_BINDING)
    else:
        succeed(prepare,prepare_path)
    upload,upload_path=next_stage(prepare,prepare_path,'step1_upload')
    assert not gate._request_path(upload['analysis_id'],1,'step2_master').exists()
    command=gate._step_command(upload,'step1_upload') if pipeline=='wgs' else gate._step(upload,'step1_upload')
    assert command[2]=='step1-upload'
    writer=runtime.writer_for_bundle(runtime,bundle,h.contract,h.config)
    assert writer is not None
    h.config['obs']['upload_parallelism']=1
    # The upload protocol and protected native stage stay real; only OBS I/O
    # crosses a synthetic transport. Empty synthetic FASTQ inventory is valid.
    monkeypatch.setattr(runtime,'_obs_command',lambda *a,**k:subprocess.CompletedProcess([],0,b'',b''))
    writer=runtime.writer_for_bundle(runtime,bundle,h.contract,h.config)
    runtime.step1(bundle,h.contract,h.config,h.modules,writer=writer)
    initial_lock=copy.deepcopy(next(iter(state.cms.values())))
    initial_owner=json.loads(initial_lock['data']['lock'])['owner']
    assert initial_owner['generation']==1 and initial_owner['master_uid']==''
    succeed(upload,upload_path)
    submit,submit_path=next_stage(upload,upload_path,'step2_master')
    assert initial_owner['action']!=submit['execution_id']
    submit['_cce_master_result']=paired.submit_registered(submit,binding=binding,gate=gate,pipeline=pipeline)
    succeed(submit,submit_path)
    selected=Path(submit['_cce_master_result']['bundle'])
    bound_owner=json.loads(next(iter(state.cms.values()))['data']['lock'])['owner']
    assert bound_owner=={**initial_owner,'master_uid':'new-uid'}
    assert (state.creates,state.starts)==(1,1)
    assert policy.read_bytes()==policy_before
    assert frozen=={name:(bundle/name).read_bytes() for name in frozen}

    def seal(success):
        # Actual Master terminal producer, not a test-written lock/handoff.
        record=runtime._read_master_handoff(selected,h.contract)
        monkeypatch.setattr(runtime,'_master_input_context',lambda:record)
        monkeypatch.setenv('CCE_RUN_ROOT',h.contract['paths']['run_dir'])
        monkeypatch.setenv('CCE_INPUT_ROOT',str(selected))
        for phase in ('preflight','analysis'):
            env=runtime._recovery_phase_start(phase)
            root=Path(env['SNAKEMAKE_CCE_SUBMIT_EVIDENCE_DIR'])
            ctx=json.loads(Path(env['SNAKEMAKE_CCE_SUBMIT_CONTEXT_FILE']).read_bytes())
            SubmissionManager(ctx,root,plugin_tests.API(root,[])).claim_executor()
            runtime._recovery_phase_finished(phase,0)
        terminal=runtime._bind_master_terminal({'schema_version':1,'state':'SUCCEEDED' if success else 'FAILED',
            'exit_code':0 if success else 1,'finished_epoch':h.now+1,'failed_stage':'final_dryrun',
            'exit_codes':{'preflight':0,'analysis':0,'final_dryrun':0 if success else 1}})
        assert terminal['submission_inventory_complete'] is True, terminal
        evidence={'START_CONFIRMED.json':state.confirmation,
            'RUN_COMPLETE.json' if success else 'RUN_FAILED.json':terminal,
            'recovery-final.json':json.loads((Path(h.contract['paths']['run_dir'])/'evidence'/record['run_id']/'recovery-final.json').read_bytes())}
        if success:
            evidence['workflow-completion.json']={'required':[{'path':'ANALYSIS_COMPLETE',
                'content':json.dumps({'schema_version':1,'status':'PASS',**h.contract['identity']})}]}
        runtime._write_mirror_evidence(selected,record['run_id'],evidence,project=record['project'],batch=record['batch'])
        state.job=None  # TTL removes the cloud object, never the directory lock.

    h.modules=(*h.modules[:3],step3_status)
    monitor,monitor_path=next_stage(submit,submit_path,'step3_monitor')
    for payload,path in ((prepare,prepare_path),(upload,upload_path),(submit,submit_path)):
        if not (pipeline=='gatk' and path==prepare_path):finish_worker(payload,path)
    expected_uid='new-uid'
    expected_creates=1
    if outcome=='recovery':
        stale_writer=runtime.writer_for_bundle(runtime,bundle,h.contract,h.config)
        stale_writer.context.update(bound_owner)
        seal(False)
        create=runtime._create_job_from_path
        def replacement(config,manifest):
            job=create(config,manifest);job['metadata']['uid']='replacement-uid';return job
        monkeypatch.setattr(runtime,'_create_job_from_path',replacement)
        prior_query=runtime._kubectl_json
        def replacement_pods(config,kind,*args,**kwargs):
            if kind=='pods' and state.job and state.job['metadata']['uid']=='replacement-uid':
                return {'items':[{'metadata':{'name':'new-pod','uid':'replacement-pod',
                    'ownerReferences':[{'controller':True,'kind':'Job','uid':'replacement-uid'}]},
                    'status':{'phase':'Running','conditions':[{'type':'Ready','status':'True'}]}}]}
            return prior_query(config,kind,*args,**kwargs)
        monkeypatch.setattr(runtime,'_kubectl_json',replacement_pods)
        transport=runtime._run
        def confirm_replacement(command,**kwargs):
            result=transport(command,**kwargs)
            if 'touch' in command:state.confirmation['pod_uid']='replacement-pod'
            return result
        monkeypatch.setattr(runtime,'_run',confirm_replacement)
        monitor,monitor_path=save({**monitor,'resume_action_id':'resume-normal-path',
            'generation':2,'execution_id':upload['analysis_id']+'-a1-step3_monitor-g2'})
        result=paired.resume_registered(monitor,binding=binding,gate=gate,pipeline=pipeline)
        selected=Path(result['bundle'])
        expected_uid='replacement-uid';expected_creates=2
        bound_owner=json.loads(next(iter(state.cms.values()))['data']['lock'])['owner']
        assert bound_owner['generation']==2 and bound_owner['master_uid']==expected_uid
        with pytest.raises((RuntimeError,ValueError)):
            stale_writer.claim()
        assert paired.resume_registered(monitor,binding=binding,gate=gate,pipeline=pipeline)['master_uid']==expected_uid
    seal(True)
    observed=paired.monitor_registered(monitor,binding=binding,gate=gate,pipeline=pipeline)
    assert observed['master_state']=='SUCCEEDED'
    succeed(monitor,monitor_path,master=observed) if pipeline=='wgs' else succeed(monitor,monitor_path)
    assert json.loads(next(iter(state.cms.values()))['data']['lock'])['owner']==bound_owner
    assert (state.creates,state.starts)==(expected_creates,expected_creates)
    before_observation=copy.deepcopy(state.cms)
    current=runtime.resolve_current_owner(runtime,bundle,h.contract,h.config,read_only=True)
    assert current['selected_bundle']==selected
    assert current['expected_master_uid']==expected_uid
    assert {k:current['context'][k] for k in ('generation','action','master_uid')}==bound_owner
    assert state.cms==before_observation  # CLI status cannot claim a write lock.

    # Preserve the existing test's external delivery/log transport boundary;
    # execute native Step4/5/6 plus the platform's final release checks.
    delivered=[]
    def marker(name):
        root=bundle/'cloud_delivery';root.mkdir(exist_ok=True)
        values=dict(schema_version='1',status='PASS',**h.contract['identity'])
        (root/name).write_text('\n'.join(k+'='+str(v) for k,v in values.items()))
    def publish(**kw):delivered.append('publish');return True
    def download(**kw):delivered.append('download');marker('DOWNLOAD_VERIFIED')
    def materialize(*args,**kw):delivered.append('materialize');marker('MATERIALIZED')
    h.modules=(SimpleNamespace(reconcile_publish_status=publish,download_verify=download,
        materialize_results=materialize),*h.modules[1:])
    monkeypatch.setattr(runtime,'download_snakemake_logs',lambda *a,**k:None)
    monkeypatch.setattr(runtime,'_release_batch_lock',REAL_RELEASE)
    finish_worker(monitor,monitor_path)
    previous,previous_path=monitor,monitor_path
    for stage in ('step4_publish','step5_download','step6_materialize'):
        payload,path=next_stage(previous,previous_path,stage)
        paired.downstream_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
        succeed(payload,path)
        finish_worker(payload,path)
        previous,previous_path=payload,path
    assert delivered==['publish','download','materialize']
    assert json.loads(next(iter(state.cms.values()))['data']['lock'])['state']=='RELEASED'
    assert selected.stat().st_mode & 0o7777==0o755
    for name in ('BATCH_RUNTIME.yaml','PAYLOAD.yaml','master-job.yaml','payload/config.yaml'):
        assert (selected/name).stat().st_mode & 0o777==0o644
    assert policy.read_bytes()==policy_before
    assert frozen=={name:(bundle/name).read_bytes() for name in frozen}


@pytest.fixture
def handoff(tmp_path):
    # Declare downstream fields before the native producer freezes its inputs.
    for h in native_handoff.__wrapped__(tmp_path):
        h.contract.update(tools={'zstd_bin':'synthetic'},permissions={})
        (h.bundle/'BATCH_RUNTIME.yaml').write_text(yaml.safe_dump(h.contract))
        yield h


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
@pytest.mark.parametrize('outcome',['normal','lost_response','unknown','recover','bound_crash','reattach','interrupted','reattach_worker','reconnect'])
def test_registered_initial_submission_selects_its_view(registered,monkeypatch,outcome):
    state,launch,gate,payload,request,policy,old_bundle,h=registered
    pipeline='wgs' if gate is wgs_runtime_gate else 'gatk'
    if outcome=='reattach_worker' and pipeline!='wgs':
        pytest.skip('Only WGS has a separate reattach worker entry')
    initial_root=h.bundle.parent/'initial-runtime'
    request_root=initial_root/'requests'
    bundle=initial_root/'runs'/payload['analysis_id']/'attempt-1'/'cce'
    shutil.copytree(h.bundle,bundle)
    monkeypatch.setattr(wgs_runtime_gate,'REQUEST_ROOT',request_root)
    monkeypatch.setenv('GATK_RUNTIME_REQUEST_ROOT',str(request_root))
    request_root.mkdir(parents=True,exist_ok=True)
    request=gate._request_path(payload['analysis_id'],1,'step2_master')
    request.parent.mkdir(parents=True,exist_ok=True)
    if pipeline=='wgs':payload['control_workdir']=str(request.parent)
    binding=json.loads((old_bundle.parent/'batch-binding.json').read_bytes())
    binding['cce_bundle']=str(bundle)
    (bundle.parent/'batch-binding.json').write_text(json.dumps(binding))
    monkeypatch.setattr(gate,'_load_binding',lambda p:binding)
    payload.pop('resume_action_id');payload.update(runtime_workdir=str(bundle.parent))
    if pipeline=='gatk':payload['cce_bundle']=str(bundle)
    excluded={'request_hash'} if pipeline=='gatk' else {'execution_id','generation','request_hash',
        'predecessor_execution_id','predecessor_generation','predecessor_receipt_hash'}
    def save(p,path):
        p['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in p.items() if k not in excluded},
            sort_keys=True,separators=(',',':')).encode()).hexdigest();path.write_text(json.dumps(p))
    save(payload,request)
    value=json.loads(policy.read_bytes());registration=value['bindings'][0]
    registration.update(bundle=str(bundle),files_sha256=runtime._handoff_binding(bundle,h.contract)['files_sha256'])
    registration['context'].update(generation=1,action=payload['execution_id'],master_uid='')
    policy.write_text(json.dumps(value))
    state.cms.clear();state.job=None;state.worker=None
    state.lose=outcome in ('lost_response','unknown');state.hide=outcome=='unknown'
    monkeypatch.setenv('WGS_EXECUTION_ENABLED','true');monkeypatch.setenv('WGS_RUNTIME_ADAPTER_ENABLED','true')
    before={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}
    if outcome=='interrupted':
        finish=runtime._finish_master_handoff
        def interrupted(*a,**kw):raise TimeoutError('synthetic handoff disconnect')
        monkeypatch.setattr(runtime,'_finish_master_handoff',interrupted)
        with pytest.raises(TimeoutError,match='synthetic'):
            paired.submit_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
        monkeypatch.setattr(runtime,'_finish_master_handoff',finish)
        archived=request.parent/'request-history'/'step2_master'/('generation-'+str(payload['generation'])+'.json')
        archived.parent.mkdir(parents=True);archived.write_bytes(request.read_bytes())
        payload.update(resume_action_id='resume-interrupted-initial',generation=9,execution_id='interrupted-step2')
        save(payload,request)
    if outcome=='bound_crash':
        atomic=runtime._atomic_write_text
        def crash_after_bind(path,text,*a,**kw):
            if Path(path).name.startswith('submission-') and '"state": "confirmed"' in text:
                raise RuntimeError('synthetic crash after lock bind')
            return atomic(path,text,*a,**kw)
        monkeypatch.setattr(runtime,'_atomic_write_text',crash_after_bind)
        with pytest.raises(RuntimeError,match='synthetic crash'):
            paired.submit_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
        monkeypatch.setattr(runtime,'_atomic_write_text',atomic)
    for _ in range(2):
        if outcome=='unknown':
            with pytest.raises(RuntimeError,match='outcome'):
                paired.submit_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
            continue
        if outcome=='interrupted':
            payload['_cce_master_result']=paired.resume_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
            if pipeline=='wgs':gate._write_status(payload,'success')
            else:gate._write_status(request,payload,'success','submitted')
            continue
        if pipeline=='wgs':
            gate.run_stage(payload);gate._write_status(payload,'success')
        else:gate._execute_stage(payload['analysis_id'],1,'step2_master',8)
    if outcome=='unknown':
        assert (state.creates,state.starts)==(1,0)
        return
    receipt=json.loads(request.with_suffix('.status.json').read_bytes())
    assert receipt['cce_master_binding']['native']['execution_generation']==1
    current={k:v for k,v in payload.items() if not k.startswith('_')}
    current.update(stage='step3_monitor',execution_id=payload['analysis_id']+'-a1-step3_monitor-g1',generation=1,
        predecessor_execution_id=payload['execution_id'],predecessor_receipt_hash=
        hashlib.sha256(request.with_suffix('.status.json').read_bytes()).hexdigest() if pipeline=='wgs' else receipt['receipt_hash'])
    if outcome=='reconnect':
        current['cce_recovery_deadline']=datetime.fromtimestamp(h.now+3600,timezone.utc).isoformat()
    path=gate._request_path(payload['analysis_id'],1,'step3_monitor');save(current,path)
    h.modules=(*h.modules[:3],step3_status)
    query=runtime._kubectl_json
    def ready(config,kind,*a,**k):
        result=query(config,kind,*a,**k)
        if kind=='pods':
            for pod in result.get('items',[]):pod['status']['conditions']=[{'type':'Ready','status':'True'}]
        return result
    monkeypatch.setattr(runtime,'_kubectl_json',ready)
    monkeypatch.setattr(runtime,'_read_pod_evidence',lambda *a,**k:({'START_CONFIRMED.json':state.confirmation},None))
    if outcome=='reconnect':
        # Only the Kubernetes transport is fake; real selected monitor and both
        # native readers must carry the same persisted retry owner.
        if pipeline=='wgs':gate._write_status(current,'running','monitor started')
        else:gate._write_status(path,current,'running','monitor started')
        original_transport=runtime._run
        calls=[]
        def monitor_transport(command,**kw):
            if command[5]!='get':return original_transport(command,**kw)
            calls.append(command)
            if len(calls)==1:
                return subprocess.CompletedProcess(command,1,b'',b'Error (ServiceUnavailable)')
            if len(calls)==2:
                assert json.loads(path.with_suffix('.status.json').read_bytes())['monitor_reconnect']['retries_used']==1
            args=command[6:command.index('-o')]
            args=[v for v in args if v not in {'--ignore-not-found','--chunk-size=0'}]
            value=ready(h.config,*args)
            if value is not None and args[0]=='pods':
                value.update(kind='PodList',metadata={})
            return subprocess.CompletedProcess(command,0,json.dumps(value).encode() if value is not None else b'',b'')
        monkeypatch.setattr(runtime,'_run',monitor_transport)
        monkeypatch.setattr(runtime,'_recovery_query',REAL_QUERY)
        monkeypatch.setattr(runtime,'_kubectl_json',REAL_LEGACY_QUERY)
        factory=paired._monitor_query_owner
        clock=[h.now]
        def owner(*a):
            value=factory(*a);value.now=lambda:clock[0]
            value.sleep=lambda seconds:clock.__setitem__(0,clock[0]+seconds)
            return value
        monkeypatch.setattr(paired,'_monitor_query_owner',owner)
    assert paired.monitor_registered(current,binding=binding,gate=gate,pipeline=pipeline)['master_state']=='RUNNING'
    assert (state.creates,state.starts)==(1,1)
    if outcome=='reconnect':
        marker=json.loads(path.with_suffix('.status.json').read_bytes())['monitor_reconnect']
        assert marker['phase']=='healthy' and marker['retries_used']==0
        assert marker['last_success_at']==h.now+30 and len(calls)>2
        assert '_monitor_query_runner' not in h.config
    if outcome in ('reattach','reattach_worker'):
        archived=request.parent/'request-history'/'step2_master'/('generation-'+str(payload['generation'])+'.json')
        archived.parent.mkdir(parents=True);archived.write_bytes(request.read_bytes())
        old_execution={k:payload[k] for k in ('execution_id','generation','request_hash')}
        if outcome!='reattach_worker':request.with_suffix('.status.json').rename(archived.with_suffix('.status.json'))
        payload={k:v for k,v in payload.items() if not k.startswith('_')}
        payload.update(resume_action_id='observe-existing',generation=9,execution_id='observe-existing-step2')
        if outcome=='reattach_worker':payload['resume_previous_execution']=old_execution
        save(payload,request)
        if outcome=='reattach_worker':gate._finish_reattached_stage(payload)
        else:
            result=paired.resume_registered(payload,binding=binding,gate=gate,pipeline=pipeline)
            payload['_cce_master_result']=result
            if pipeline=='wgs':gate._write_status(payload,'success')
            else:gate._write_status(request,payload,'success','submitted')
        receipt=json.loads(request.with_suffix('.status.json').read_bytes())
        current.pop('_cce_master_result',None)
        current.update(resume_action_id=payload['resume_action_id'],predecessor_execution_id=payload['execution_id'],
            predecessor_receipt_hash=hashlib.sha256(request.with_suffix('.status.json').read_bytes()).hexdigest()
                if pipeline=='wgs' else receipt['receipt_hash'])
        save(current,path)
        assert paired.monitor_registered(current,binding=binding,gate=gate,pipeline=pipeline)['master_state']=='RUNNING'
        assert current['_cce_master_result']['cce_master_binding']['platform_execution']['generation']==8
        assert (state.creates,state.starts)==(1,1)
    if outcome=='recover':
        selected=Path(state.new_view)
        record=runtime._read_master_handoff(selected,h.contract)
        monkeypatch.setattr(runtime,'_master_input_context',lambda:record)
        for phase in ('preflight','analysis'):
            env=runtime._recovery_phase_start(phase)
            root=Path(env['SNAKEMAKE_CCE_SUBMIT_EVIDENCE_DIR'])
            ctx=json.loads(Path(env['SNAKEMAKE_CCE_SUBMIT_CONTEXT_FILE']).read_bytes())
            SubmissionManager(ctx,root,plugin_tests.API(root,[])).claim_executor()
            runtime._recovery_phase_finished(phase,0)
        terminal=runtime._bind_master_terminal({'schema_version':1,'state':'FAILED',
            'exit_code':1,'failed_stage':'final_dryrun','finished_epoch':h.now+1,
            'exit_codes':{'preflight':0,'analysis':0,'final_dryrun':1}})
        final=json.loads((Path(h.contract['paths']['run_dir'])/'evidence'/record['run_id']/'recovery-final.json').read_bytes())
        runtime._write_mirror_evidence(selected,record['run_id'],{'RUN_FAILED.json':terminal,'recovery-final.json':final,
            'START_CONFIRMED.json':state.confirmation},
            project=record['project'],batch=record['batch'])
        # Ended initial dispatcher and reclaimed Master; no fabricated old bundle handoff.
        ended={k:payload[k] for k in ('analysis_id','attempt','stage','execution_id','generation','request_hash')}
        if pipeline=='wgs':ended.update(pid=999999999,boot_id='ended',process_start_time='0')
        else:ended.update(schema_version='gatk-runtime.dispatcher.v1',state='finished',process=None)
        request.with_suffix('.worker.json' if pipeline=='wgs' else '.worker.state.json').write_text(json.dumps(ended))
        state.job=None
        create=runtime._create_job_from_path
        def replacement(config,manifest):
            job=create(config,manifest);job['metadata']['uid']='replacement-uid';return job
        monkeypatch.setattr(runtime,'_create_job_from_path',replacement)
        previous_query=runtime._kubectl_json
        def replacement_pods(config,kind,*a,**kw):
            if kind=='pods' and state.job and state.job['metadata']['uid']=='replacement-uid':
                return {'items':[{'metadata':{'name':'new-pod','uid':'replacement-pod',
                    'ownerReferences':[{'controller':True,'kind':'Job','uid':'replacement-uid'}]},
                    'status':{'phase':'Running','conditions':[{'type':'Ready','status':'True'}]}}]}
            return previous_query(config,kind,*a,**kw)
        monkeypatch.setattr(runtime,'_kubectl_json',replacement_pods)
        transport=runtime._run
        def confirm_replacement(command,**kw):
            value=transport(command,**kw)
            if 'touch' in command:state.confirmation['pod_uid']='replacement-pod'
            return value
        monkeypatch.setattr(runtime,'_run',confirm_replacement)
        current.pop('_cce_master_result',None)
        current.update(resume_action_id='resume-initial',generation=2,execution_id='resume-initial-step3')
        save(current,path)
        result=paired.resume_registered(current,binding=binding,gate=gate,pipeline=pipeline)
        assert result['cce_master_binding']['native']['execution_generation']==2
        assert result['cce_master_binding']['source_bundle']==str(bundle)
        assert paired.resume_registered(current,binding=binding,gate=gate,pipeline=pipeline)['master_uid']==result['master_uid']
        assert paired.monitor_registered(current,binding=binding,gate=gate,pipeline=pipeline)['master_state']=='RUNNING'
        assert (state.creates,state.starts)==(2,2)
    assert before=={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
def test_direct_step3_replacement_and_observation(registered,monkeypatch):
    state,launch,gate,payload,request,policy,bundle,h=registered
    pipeline='wgs' if gate is wgs_runtime_gate else 'gatk'
    # The authenticated recovery starts at Step3, not an invented successful Step2.
    request.unlink()
    payload.update(stage='step3_monitor',execution_id=payload['analysis_id']+'-a1-step3_monitor-g8')
    excluded={'request_hash'} if pipeline=='gatk' else {'execution_id','generation','request_hash',
        'predecessor_execution_id','predecessor_generation','predecessor_receipt_hash'}
    payload['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in payload.items() if k not in excluded},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()
    path=gate._request_path(payload['analysis_id'],1,payload['stage']);path.write_text(json.dumps(payload))
    binding=json.loads((bundle.parent/'batch-binding.json').read_bytes())
    h.modules=(*h.modules[:3],step3_status)
    monkeypatch.setattr(runtime,'_read_pod_evidence',lambda *a,**k:({'START_CONFIRMED.json':state.confirmation},None))
    query=runtime._kubectl_json
    def ready(config,kind,*a,**k):
        value=query(config,kind,*a,**k)
        if kind=='pods':
            for pod in value.get('items',[]):pod['status']['conditions']=[{'type':'Ready','status':'True'}]
        return value
    monkeypatch.setattr(runtime,'_kubectl_json',ready)
    monkeypatch.setattr(paired,'selected_runtime',lambda:(Path(runtime.__file__),'/operator/python'))
    class Observed(BaseException):pass
    def stop(*a):raise Observed()
    monkeypatch.setattr(gate.time,'sleep',stop)
    monkeypatch.setattr(gate,'_sync_rule_evidence' if pipeline=='wgs' else '_sync_evidence',lambda *a,**k:None)
    if pipeline=='wgs':monkeypatch.setattr(gate,'_binding_run_label',lambda b:'cce-run-0123456789abcdef')
    with pytest.raises(Observed):
        if pipeline=='wgs':wgs_resume.run_resume_stage(payload,gate=gate)
        else:gate._execute_stage(payload['analysis_id'],1,payload['stage'],8)
    receipt=json.loads(path.with_suffix('.status.json').read_bytes())
    assert receipt['status']=='running'
    assert receipt['cce_master_binding']['native']['job_uid']=='new-uid'
    # Replay uses durable recovery state. Observation must not need a Step2 receipt.
    assert paired.resume_registered(json.loads(path.read_bytes()),binding=binding,gate=gate,pipeline=pipeline)['master_uid']=='new-uid'
    fresh=json.loads(path.read_bytes())
    assert paired.monitor_registered(fresh,binding=binding,gate=gate,pipeline=pipeline)['master_state']=='RUNNING'
    assert fresh['_cce_master_result']['cce_master_submit_execution_id']==payload['execution_id']
    assert (state.creates,state.starts)==(1,1)


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
@pytest.mark.parametrize('fault',[None,'receipt_uid','old_terminal','journal_view','lock_owner','gate',
    'old_marker','reclaimed_success','reclaimed_failure','recoverable_failure','downstream','reconnect','reconnect_downstream','journal_deadline'])
def test_fresh_monitor_uses_selected_master_and_rejects_stale_authority(registered,monkeypatch,fault):
    state,launch,gate,submit,request,policy,bundle,h=registered
    if fault=='journal_deadline':
        from datetime import timedelta
        submit['cce_recovery_deadline']=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        submit['request_hash']=paired._request_digest(submit,'wgs' if gate is wgs_runtime_gate else 'gatk')
        request.write_text(json.dumps(submit))
    original={str(p.relative_to(bundle)):p.read_bytes() for p in bundle.rglob('*') if p.is_file()}
    receipt=launch()
    monkeypatch.setattr(paired,'selected_runtime',lambda:(Path(runtime.__file__),'/operator/python'))
    selected=Path(state.new_view)
    receipt_path=request.with_suffix('.status.json')
    pipeline='wgs' if gate is wgs_runtime_gate else 'gatk'
    if fault=='journal_deadline':
        journal=request.parent/('recovery-new-action.json' if pipeline=='wgs' else 'resume-master-uid.json')
        value=json.loads(journal.read_bytes());value['recovery_v2']['compute_deadline']+=1
        journal.write_text(json.dumps(value))
    if fault=='receipt_uid':
        receipt['cce_master_binding']['native']['job_uid']='foreign-uid'
        if pipeline=='gatk':
            receipt['receipt_hash']=hashlib.sha256(json.dumps({k:v for k,v in receipt.items() if k!='receipt_hash'},
                sort_keys=True,separators=(',',':')).encode()).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
    if fault=='journal_view':
        journal=(request.parent/('recovery-new-action.json' if pipeline=='wgs' else 'resume-master-uid.json'))
        value=json.loads(journal.read_bytes());value['recovery_v2']['view']=str(bundle)
        journal.write_text(json.dumps(value))
    if fault=='lock_owner':
        cm=next(iter(state.cms.values()));value=json.loads(cm['data']['lock'])
        value['owner']['master_uid']='foreign-uid';cm['data']['lock']=json.dumps(value)
    current={k:v for k,v in json.loads(request.read_bytes()).items() if k!='request_hash'}
    if not hasattr(h,'register_stage'):
        current.update(stage='step3_monitor',generation=1,
            execution_id=submit['analysis_id']+'-a1-step3_monitor-g1',
            predecessor_execution_id=submit['execution_id'],
            predecessor_receipt_hash=hashlib.sha256(receipt_path.read_bytes()).hexdigest() if pipeline=='wgs' else receipt['receipt_hash'])
    excluded=set() if pipeline=='gatk' else {'execution_id','generation','predecessor_execution_id',
        'predecessor_generation','predecessor_receipt_hash'}
    current['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in current.items() if k not in excluded},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()
    path=gate._request_path(submit['analysis_id'],1,'step3_monitor')
    if hasattr(h,'register_stage'):
        current=h.register_stage('step3_monitor')
    else:path.write_text(json.dumps(current))
    if fault in ('reconnect','reconnect_downstream'):
        current['resume_action_id']='observe-active-master'
        current.pop('request_hash')
        current['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in current.items() if k not in excluded},
            sort_keys=True,separators=(',',':')).encode()).hexdigest()
        path.write_text(json.dumps(current))
        ended={k:submit[k] for k in ('analysis_id','attempt','stage','execution_id','generation','request_hash')}
        if pipeline=='wgs':ended.update(pid=999999999,boot_id='ended',process_start_time='0')
        else:ended.update(schema_version='gatk-runtime.dispatcher.v1',state='finished',process=None)
        request.with_suffix('.worker.json' if pipeline=='wgs' else '.worker.state.json').write_text(json.dumps(ended))
    h.modules=(*h.modules[:3],step3_status)
    query=runtime._kubectl_json
    def ready_pods(config,kind,*args,**kwargs):
        result=query(config,kind,*args,**kwargs)
        if kind=='pods':
            for pod in result.get('items',[]):
                pod['status']['conditions']=[{'type':'Ready','status':'True'}]
        return result
    monkeypatch.setattr(runtime,'_kubectl_json',ready_pods)
    if getattr(h,'real_query_transport',False):
        native_transport=runtime._run
        def read_transport(command,**kw):
            if command[5]!='get':return native_transport(command,**kw)
            args=command[6:command.index('-o')]
            args=[v for v in args if v not in {'--ignore-not-found','--chunk-size=0'}]
            value=ready_pods(h.config,*args)
            if value is not None and args[0]=='pods':value.update(kind='PodList',metadata={})
            return subprocess.CompletedProcess(command,0,json.dumps(value).encode() if value is not None else b'',b'')
        monkeypatch.setattr(runtime,'_run',read_transport)
        monkeypatch.setattr(runtime,'_recovery_query',REAL_QUERY)
        monkeypatch.setattr(runtime,'_kubectl_json',REAL_LEGACY_QUERY)
    evidence={'analysis.log':'2 of 10 steps (20%) done\n','START_CONFIRMED.json':state.confirmation}
    if fault=='old_terminal':evidence['RUN_FAILED.json']=state.evidence['RUN_FAILED.json']
    if fault in ('old_marker','reclaimed_success','downstream','reconnect_downstream'):
        evidence['workflow-completion.json']={'required':[{'path':'ANALYSIS_COMPLETE',
            'content':json.dumps({'schema_version':1,'status':'PASS',**h.contract['identity']})}]}
    if fault in ('reclaimed_success','reclaimed_failure','recoverable_failure','downstream','reconnect_downstream'):
        record=runtime._read_master_handoff(selected,h.contract)
        monkeypatch.setattr(runtime,'_master_input_context',lambda:record)
        for phase in ('preflight','analysis'):
            env=runtime._recovery_phase_start(phase)
            root=Path(env['SNAKEMAKE_CCE_SUBMIT_EVIDENCE_DIR'])
            ctx=json.loads(Path(env['SNAKEMAKE_CCE_SUBMIT_CONTEXT_FILE']).read_bytes())
            clock=plugin_tests.Clock()
            manager=SubmissionManager(ctx,root,plugin_tests.API(root,[plugin_tests.admission()]*3),
                monotonic=clock.monotonic,sleep=clock.sleep)
            manager.claim_executor()
            if fault=='recoverable_failure':
                import logging
                from snakemake_logger_plugin_rule_status.failure_summary import FailureSummary
                from snakemake_interface_logger_plugins.common import LogEvent
                audit=FailureSummary(root/'submit-context.json',root)
                event=logging.LogRecord('synthetic',logging.INFO,'synthetic',1,'',(),None)
                event.event=LogEvent.WORKFLOW_STARTED;audit.emit(event)
                if phase=='analysis':
                    requested=plugin_tests.body();requested.metadata.name='snakejob-new-absent'
                    with pytest.raises(plugin_tests.module().SubmissionFailure):manager.submit(requested,1)
                    event=logging.LogRecord('synthetic',logging.ERROR,'synthetic',1,'',(),None)
                    event.event=LogEvent.ERROR;event.exception='SubmissionFailure';audit.emit(event)
                audit.close()
            runtime._recovery_phase_finished(phase,1 if fault=='recoverable_failure' and phase=='analysis' else 0)
        success=fault in ('reclaimed_success','downstream','reconnect_downstream')
        terminal=runtime._bind_master_terminal({'schema_version':1,'state':'SUCCEEDED' if success else 'FAILED',
            'exit_code':0 if success else 1,'failed_stage':'analysis' if fault=='recoverable_failure' else 'final_dryrun','finished_epoch':h.now+1,
            'exit_codes':{'preflight':0,'analysis':1 if fault=='recoverable_failure' else 0,
                'final_dryrun':None if fault=='recoverable_failure' else 0 if success else 1}})
        evidence['RUN_COMPLETE.json' if success else 'RUN_FAILED.json']=terminal
        evidence['recovery-final.json']=json.loads((Path(h.contract['paths']['run_dir'])/'evidence'/record['run_id']/'recovery-final.json').read_bytes())
        runtime._write_mirror_evidence(selected,record['run_id'],evidence,
            project=record['project'],batch=record['batch'])
        state.job=None
    monkeypatch.setattr(runtime,'_read_pod_evidence',lambda *a,**kw:(copy.deepcopy(evidence),None))
    class ObservedRunning(BaseException):pass
    def stop_after_observation(*args):raise ObservedRunning()
    def bridge(payload,binding,**kwargs):
        assert binding['cce_bundle']==str(selected), 'logger must follow selected Master'
        return None
    monkeypatch.setattr(gate,'_sync_rule_evidence' if pipeline=='wgs' else '_sync_evidence',bridge)
    monitor_binding=json.loads((bundle.parent/'batch-binding.json').read_bytes())
    # The native fixture uses synthetic-run. Keep that inventory identity;
    # normalize only the unrelated WGS display/bridge label boundary.
    if pipeline=='wgs':monkeypatch.setattr(gate,'_binding_run_label',lambda b:'cce-run-0123456789abcdef')
    monkeypatch.setattr(gate,'_load_binding',lambda payload:monitor_binding)
    # A genuine second process receives only registered JSON; no internal result.
    read_fd,write_fd=os.pipe()
    pid=os.fork()
    if pid==0:
        os.close(read_fd)
        try:
            payload=json.loads(path.read_bytes())
            if fault=='gate' or hasattr(h,'register_stage'):
                monkeypatch.setattr(gate.time,'sleep',stop_after_observation)
                try:
                    if pipeline=='wgs':wgs_resume.run_resume_stage(payload,gate=gate)
                    else:gate._execute_stage(submit['analysis_id'],1,'step3_monitor',current['generation'])
                except ObservedRunning:pass
                current_receipt=json.loads(path.with_suffix('.status.json').read_bytes())
                value=current_receipt['master'] if pipeline=='wgs' else {
                    'master_state':{'running':'RUNNING','success':'SUCCEEDED'}.get(current_receipt['status'],'FAILED'),
                    'completed':current_receipt['completed_units']}
            else:
                if fault=='reconnect':paired.prepare_monitor_registered(payload,binding=monitor_binding,gate=gate,pipeline=pipeline)
                value=paired.monitor_registered(payload,binding=json.loads((bundle.parent/'batch-binding.json').read_bytes()),
                    gate=gate,pipeline=pipeline)
                status={'SUCCEEDED':'success','FAILED':'failed'}.get(value['master_state'],'running')
                if pipeline=='wgs':gate._write_status(payload,status,master=value)
                else:gate._write_status(path,payload,status,'monitoring',master=value)
            answer={'status':value,'receipt':json.loads(path.with_suffix('.status.json').read_bytes()),'pid':os.getpid()}
        except Exception as error:
            answer={'error':type(error).__name__+': '+str(error),'traceback':traceback.format_exc()}
        with os.fdopen(write_fd,'w') as stream:json.dump(answer,stream)
        os._exit(0)
    os.close(write_fd)
    with os.fdopen(read_fd) as stream:answer=json.load(stream)
    assert os.waitpid(pid,0)[1]==0
    if fault not in (None,'gate','old_marker','reclaimed_success','reclaimed_failure','recoverable_failure','downstream','reconnect','reconnect_downstream'):
        assert 'error' in answer and not answer['error'].startswith('AttributeError'),answer
    else:
        if 'error' in answer:pytest.fail(answer.get('traceback',answer['error']))
        assert answer['pid']!=os.getpid()
        assert answer['status']['master_state']=={'reclaimed_success':'SUCCEEDED','downstream':'SUCCEEDED','reconnect_downstream':'SUCCEEDED','reclaimed_failure':'FAILED','recoverable_failure':'FAILED'}.get(fault,'RUNNING')
        assert answer['status']['completed']==(10 if fault in ('reclaimed_success','downstream','reconnect_downstream') else 2)
        assert answer['receipt']['cce_master_binding']['native']['job_uid']=='new-uid'
        assert answer['receipt']['cce_master_submit_execution_id']==submit['execution_id']
        assert answer['receipt']['execution_id']==current['execution_id']
        assert runtime._mirror_dir(selected,state.record['run_id']).is_dir()
        if fault=='recoverable_failure':
            proof=answer['receipt']['cce_recovery_evidence']
            assert proof['binding']==answer['receipt']['cce_master_binding']
            assert proof['terminal']['generation']==3
            assert proof['binding']['platform_execution']['generation']==8
            assert proof['terminal']['executor_failure_count']==1
            before_receipt=path.with_suffix('.status.json').read_bytes()
            before_mutations=(state.creates,state.deletes,state.starts,state.copies,copy.deepcopy(state.cms))
            observed=paired.worker_probe_command(['--recovery-probe',current['analysis_id'],str(current['attempt']),
                str(current['generation']),current['request_hash'],'a'*32],gate=gate,pipeline=pipeline)
            assert observed['cce_recovery_evidence']==proof
            assert path.with_suffix('.status.json').read_bytes()==before_receipt
            assert (state.creates,state.deletes,state.starts,state.copies,state.cms)==before_mutations
            with pytest.raises(ValueError):
                paired.probe_waiting_workers(json.loads(path.read_bytes()),binding=monitor_binding,
                    gate=gate,pipeline=pipeline,generation=current['generation']+1,request_hash=current['request_hash'],nonce='a'*32)
    if fault in ('downstream','reconnect_downstream'):
        monkeypatch.setattr(runtime,'_release_batch_lock',REAL_RELEASE)
        calls=[]
        def publish(**kw):calls.append(('publish',kw));return True
        def marker(name):
            root=bundle/'cloud_delivery';root.mkdir(exist_ok=True)
            values=dict(schema_version='1',status='PASS',**h.contract['identity'])
            (root/name).write_text('\n'.join(k+'='+str(v) for k,v in values.items()))
        def download(**kw):calls.append(('download',kw));marker('DOWNLOAD_VERIFIED')
        def materialize(*args,**kw):calls.append(('materialize',args));marker('MATERIALIZED')
        h.config['obs']={'obsutil_bin':'synthetic','config_file':'synthetic'}
        h.modules=(SimpleNamespace(reconcile_publish_status=publish,download_verify=download,
            materialize_results=materialize),*h.modules[1:])
        # Keep log transport at its existing tested boundary; exercise actual
        # native stage bodies, not a fake downstream stage or forged capability.
        monkeypatch.setattr(runtime,'download_snakemake_logs',lambda *a,**k:None)
        if pipeline=='gatk':
            monkeypatch.setattr(gate,'_materialize_to_approved_root',lambda p:materialize(bundle/'cloud_delivery','approved-root'))
        previous=current
        # Terminal worker sidecars model the real restricted dispatcher. A free
        # flock by itself must not count as proof that sibling writers ended.
        def finished_worker(request_path):
            p=json.loads(request_path.read_bytes())
            value={k:p[k] for k in ('analysis_id','attempt','stage','execution_id','generation','request_hash')}
            if pipeline=='wgs':value.update(pid=999999999,boot_id='synthetic-ended',process_start_time='0')
            else:value.update(schema_version='gatk-runtime.dispatcher.v1',state='finished',process=None)
            request_path.with_suffix('.worker.json' if pipeline=='wgs' else '.worker.state.json').write_text(json.dumps(value))
        finished_worker(request);finished_worker(path)
        # Keep the prior generation's verified terminal Worker: Task4 cannot
        # assume that the later TTL rollout has already removed it.
        for stage in ('step4_publish','step5_download','step6_materialize'):
            if hasattr(h,'ingest_stage'):h.ingest_stage(previous['stage'])
            previous_path=gate._request_path(submit['analysis_id'],1,previous['stage'])
            previous_receipt=json.loads(previous_path.with_suffix('.status.json').read_bytes())
            downstream={**previous,'stage':stage,'execution_id':submit['analysis_id']+'-a1-'+stage+'-g1',
                'predecessor_execution_id':previous['execution_id'],
                'predecessor_receipt_hash':hashlib.sha256(previous_path.with_suffix('.status.json').read_bytes()).hexdigest()
                    if pipeline=='wgs' else previous_receipt['receipt_hash']}
            downstream.pop('request_hash')
            downstream['request_hash']=hashlib.sha256(json.dumps({k:v for k,v in downstream.items() if k not in excluded},
                sort_keys=True,separators=(',',':')).encode()).hexdigest()
            stage_path=gate._request_path(submit['analysis_id'],1,stage)
            if hasattr(h,'register_stage'):downstream=h.register_stage(stage)
            else:stage_path.write_text(json.dumps(downstream))
            if stage=='step6_materialize':
                # Current-generation journal projection must never hide an
                # unknown live workload from the final directory release.
                marker('MATERIALIZED');state.unknown=True
                def reject_unknown(rt,base,view,uid,contract,config,modules,writer):
                    paired._release_registered_writer(downstream,monitor_binding,gate,pipeline,
                        rt,base,view,uid,contract,config,writer)
                with pytest.raises(ValueError,match='inventory|unknown|unbound'):
                    paired._selected_registered(downstream,binding=monitor_binding,gate=gate,
                        pipeline=pipeline,operation=reject_unknown)
                assert json.loads(next(iter(state.cms.values()))['data']['lock'])['state']=='OWNED'
                state.unknown=False
            command=gate._step_command(downstream,stage) if pipeline=='wgs' else gate._step(downstream,stage)
            assert command[1:3]==[str(paired.PLATFORM_SOURCE),'--registered-stage']
            # The existing transfer process boundary gets only registered IDs.
            # No Python capability or caller-chosen view survives this handoff.
            read_fd,write_fd=os.pipe();pid=os.fork()
            if pid==0:
                os.close(read_fd)
                try:
                    paired.run_registered_stage(command[3:])
                    answer={'calls':calls,'locks':state.cms}
                except Exception as error:answer={'error':traceback.format_exc()}
                with os.fdopen(write_fd,'w') as stream:json.dump(answer,stream,default=str)
                os._exit(0)
            os.close(write_fd)
            with os.fdopen(read_fd) as stream:child=json.load(stream)
            assert os.waitpid(pid,0)[1]==0
            if 'error' in child:pytest.fail(child['error'])
            calls=child['calls']
            state.cms=child['locks']
            if pipeline=='wgs':gate._write_status(downstream,'success')
            else:gate._write_status(stage_path,downstream,'success','completed')
            result=json.loads(stage_path.with_suffix('.status.json').read_bytes())
            assert result['cce_master_submit_execution_id']==submit['execution_id']
            previous=json.loads(stage_path.read_bytes())
            finished_worker(stage_path)
        assert [c[0] for c in calls]==['publish','download','materialize']
        assert calls[0][1]['work_root']==str(bundle/'delivery-publish')
        assert calls[1][1]['download_root']==str(bundle/'cloud_delivery')
        assert calls[2][1][0]==str(bundle/'cloud_delivery')
        assert json.loads(next(iter(state.cms.values()))['data']['lock'])['state']=='RELEASED'
        before_calls=len(calls)
        paired.downstream_registered(downstream,binding=monitor_binding,gate=gate,pipeline=pipeline,
            materialize=lambda p:pytest.fail('released Step6 must not materialize again'))
        assert len(calls)==before_calls
    assert (state.creates,state.starts)==(1,1)
    assert original=={name:(bundle/name).read_bytes() for name in original}
