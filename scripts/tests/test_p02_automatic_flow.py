"""Real fatal producer -> automatic action -> restricted runtime -> Step4–6.

Cloud/HTTP/SSH transport is synthetic; no production credentials or live jobs.
Reuse the accepted manual flow harness, not separate fake stage implementations.
"""
import json
import logging
from pathlib import Path

import pytest
from kubernetes import client
from snakemake_logger_plugin_rule_status.failure_summary import FailureSummary
from snakemake_interface_logger_plugins.common import LogEvent
from test_recovery_final import SubmissionManager, plugin_tests
from test_p02_manual_flow import run_authenticated_flow
from test_p02_selected_monitor import registered,adapter,view_inputs,handoff,runtime
from scripts import cce_paired_runtime as paired


@pytest.fixture
def final_inputs(view_inputs,monkeypatch,tmp_path):
    h,context=view_inputs
    view=h.bundle.parent/'view'
    pipeline,aid=context['pipeline'],context['analysis_id']
    bundle=tmp_path/'runs'/aid/'attempt-1'/'cce'
    source=dict(analysis_id=aid,attempt=1,stage='step2_master',generation=8,
        execution_id=aid+'-a1-step2_master-g8',orchestration_contract_version=2,
        schema_version='wgs-runtime.request.v4',runtime_workdir=str(bundle.parent),
        control_workdir=str(tmp_path/'requests'/aid/'attempt-1'),pipeline_release_id='synthetic',
        wgs_source_commit='a'*40,expected_batch_root=str(bundle.parent))
    if pipeline=='gatk':
        for key in ('control_workdir','pipeline_release_id','wgs_source_commit','expected_batch_root'):source.pop(key)
        source.update(schema_version='gatk-runtime.request.v1',pipeline='gatk',cce_bundle=str(bundle),
            profile_id='synthetic',profile_revision='r1')
    source['request_hash']=paired._request_digest(source,pipeline)
    h.initial_payload=source
    platform=dict(pipeline=pipeline,**{k:source[k] for k in
        ('analysis_id','attempt','stage','execution_id','generation','request_hash')})
    context=dict(context,execution_id=source['execution_id'])
    runtime._prepare_recovery_view(h.bundle,view,h.contract,context=context,platform_execution=platform)
    record={**runtime._handoff_binding(view,h.contract),**h.contract['identity'],
        'job_name':'master','job_uid':'master-uid','pod_uid':'pod-uid','deadline_epoch':1600}
    monkeypatch.setattr(runtime,'_master_input_context',lambda:record)
    monkeypatch.setenv('CCE_INPUT_ROOT',str(h.bundle))
    monkeypatch.setenv('CCE_RUN_ROOT',h.contract['paths']['run_dir'])
    Path(h.contract['paths']['run_dir']).mkdir()
    for phase in ('preflight','analysis'):
        env=runtime._recovery_phase_start(phase)
        root=Path(env['SNAKEMAKE_CCE_SUBMIT_EVIDENCE_DIR'])
        ctx=json.loads(Path(env['SNAKEMAKE_CCE_SUBMIT_CONTEXT_FILE']).read_bytes())
        clock=plugin_tests.Clock()
        manager=SubmissionManager(ctx,root,plugin_tests.API(root,['success']+[plugin_tests.admission()]*3),
            monotonic=clock.monotonic,sleep=clock.sleep)
        manager.claim_executor()
        audit=FailureSummary(root/'submit-context.json',root)
        event=logging.LogRecord('synthetic',logging.INFO,'synthetic',1,'',(),None)
        event.event=LogEvent.WORKFLOW_STARTED;audit.emit(event)
        if phase=='analysis':
            requested=plugin_tests.body();requested.metadata.namespace=ctx['namespace']
            worker=manager.submit(requested,1)
            worker.status=client.V1JobStatus(conditions=[client.V1JobCondition(type='Complete',status='True')])
            manager.record_worker_terminal(worker,1)
            base=Path(h.contract['paths']['run_dir'])/'evidence'/record['run_id']
            (base/'jobs.ndjson').write_text(json.dumps(dict(schema_version=2,
                external_jobid=worker.metadata.name,kubernetes_uid=worker.metadata.uid,attempt=1))+'\n')
            requested.metadata.name='snakejob-absent'
            with pytest.raises(plugin_tests.module().SubmissionFailure):manager.submit(requested,1)
            event=logging.LogRecord('synthetic',logging.ERROR,'synthetic',1,'',(),None)
            event.event=LogEvent.ERROR;event.exception='SubmissionFailure';audit.emit(event)
        audit.close();runtime._recovery_phase_finished(phase,1 if phase=='analysis' else 0)
    return h,record,root


@pytest.fixture
def mirrored_final(final_inputs):
    h,record,_=final_inputs
    view=h.bundle.parent/'view'
    record.update(schema_version=2,state='START_SENT')
    runtime._atomic_write_text(runtime._master_handoff_path(view,h.contract),json.dumps(record))
    terminal=runtime._bind_master_terminal(dict(schema_version=1,state='FAILED',failed_stage='analysis',
        exit_code=1,finished_epoch=1500,exit_codes=dict(preflight=0,analysis=1,final_dryrun=None)))
    snapshot=json.loads((Path(h.contract['paths']['run_dir'])/'evidence'/record['run_id']/'recovery-final.json').read_bytes())
    return h,view,record,{'START_CONFIRMED.json':dict(record,state='START_CONFIRMED',confirmed_epoch=1000),
        'RUN_FAILED.json':terminal,'recovery-final.json':snapshot}


@pytest.mark.parametrize('view_inputs',[{'pipeline':'wgs','analysis_id':'WGS_20260924_000000_AAAAAA'},
    {'pipeline':'gatk','analysis_id':'GATK_20260924_000000_AAAAAA'}],indirect=True)
def test_automatic_recovery_reaches_normal_downstream_receipts(registered,monkeypatch,tmp_path):
    run_authenticated_flow(registered,monkeypatch,tmp_path,automatic=True)
