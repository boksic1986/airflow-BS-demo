"""Actual Step4 callables reconcile uncertainty instead of repeating the task."""
from datetime import datetime,timedelta,timezone
import importlib
import json
import sys
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from airflow.exceptions import AirflowFailException
sys.path.insert(0,str(Path(__file__).parents[1]))


@pytest.fixture(params=['wgs','gatk'])
def case(request):
    pipeline=request.param
    module=importlib.import_module('bio_'+pipeline)
    conf=dict(analysis_id='SYNTHETIC',attempt=1,execution_mode='cce',pipeline=pipeline,
        params=dict(cce_recovery_policy=dict(enabled=True,attempt=1)))
    context=dict(dag_run=SimpleNamespace(conf=conf,run_id='actual-dag'))
    grant=dict(status='uncertain',dispatch=True,execution_id='original',generation=3,
        request_hash='b'*64,sequence=0,deadline=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())
    return pipeline,module,context,grant


@pytest.mark.parametrize('lost',[False,True])
def test_start_commits_then_sends_exact_original_once_and_acknowledges_exited_ssh(case,lost):
    pipeline,module,context,grant=case
    calls=[]
    def api(path,**kw):
        body=kw['payload'];calls.append(body)
        assert body['dag_run_id']=='actual-dag'
        if path.endswith('/stages/step4_publish'):return dict(generation=3,execution_id='original')
        assert path.endswith('/stages/publish_recovery')
        if body['publish_operation']=='begin':return grant
        if body['publish_operation']=='check':return dict(grant,dispatch=False)
        assert body['publish_operation']=='finish' and body['publish_sequence']==0
        return dict(grant,dispatch=False)
    def ssh(command,**kw):
        assert calls[-1]['publish_operation']=='check'
        assert command[-5:]==['--publish-dispatch','SYNTHETIC','1','3','b'*64]
        assert 0<kw['timeout']<=120
        if lost:raise subprocess.TimeoutExpired(command,120)
        return SimpleNamespace(returncode=255,stdout='',stderr='synthetic disconnect')
    with patch.object(module,'_backend_json',side_effect=api),patch.object(module.subprocess,'run',side_effect=ssh) as proc,patch.object(module,'_require_runtime_enabled',create=True):
        result=(module.run_stage_on_200 if pipeline=='wgs' else module.run_stage)('step4_publish',**context)
    assert proc.call_count==1 and result['runner_status']=='reconciling'
    assert calls[-1]['publish_operation']=='finish'


@pytest.mark.parametrize('ready',[False,True])
def test_sensor_requires_normal_receipt_even_after_probe_success(case,ready):
    pipeline,module,context,grant=case
    probe=dict(pipeline=pipeline,analysis_id='SYNTHETIC',attempt=1,stage='step4_publish',
        execution_id='original',generation=3,request_hash='b'*64,nonce='a'*32)
    calls=[]
    def api(path,**kw):
        if '/stage-status?' in path:return dict(ready=ready,failed=False)
        body=kw['payload'];calls.append(body)
        assert body['publish_operation']=='poll'
        if len(calls)==1:return dict(grant,dispatch=False,probe=probe)
        assert body['publish_observation']==dict(probe,schema_version='cce.publish-observation.v1',status='success')
        return dict(grant,dispatch=False,status='success',probe=None)
    def ssh(command,**kw):
        assert command[-6:]==['--publish-probe','SYNTHETIC','1','3','b'*64,'a'*32]
        return SimpleNamespace(returncode=0,stdout=json.dumps(dict(probe,
            schema_version='cce.publish-observation.v1',status='success')),stderr='')
    with patch.object(module,'_backend_json',side_effect=api),patch.object(module.subprocess,'run',side_effect=ssh),patch.object(module,'_require_runtime_enabled',create=True):
        assert module.stage_ready('step4_publish',**context) is ready
    assert len(calls)==2


@pytest.mark.parametrize('status',['expired','exhausted','stopped'])
def test_exhaustion_stops_sensor_without_any_publish(case,status):
    _,module,context,grant=case
    def api(path,**kw):
        if '/stage-status?' in path:return dict(ready=False,failed=False)
        return dict(grant,status=status,dispatch=False,probe=None)
    with patch.object(module,'_backend_json',side_effect=api),patch.object(module.subprocess,'run') as proc,patch.object(module,'_require_runtime_enabled',create=True):
        with pytest.raises(AirflowFailException):module.stage_ready('step4_publish',**context)
    proc.assert_not_called()


def test_disabled_policy_keeps_existing_sensor_without_publish_control(case):
    _,module,context,_=case
    context['dag_run'].conf['params']['cce_recovery_policy']['enabled']=False
    def api(path,**kw):
        assert '/stage-status?' in path
        return dict(ready=True,failed=False)
    with patch.object(module,'_backend_json',side_effect=api),patch.object(module.subprocess,'run') as proc,patch.object(module,'_require_runtime_enabled',create=True):
        assert module.stage_ready('step4_publish',**context) is True
    proc.assert_not_called()


@pytest.mark.parametrize('lost_probe',[False,True])
def test_due_sensor_sends_only_after_backend_accepts_fresh_probe(case,lost_probe):
    pipeline,module,context,grant=case
    probe=dict(pipeline=pipeline,analysis_id='SYNTHETIC',attempt=1,stage='step4_publish',
        execution_id='original',generation=3,request_hash='b'*64,nonce='a'*32)
    posts=[];commands=[]
    def api(path,**kw):
        if '/stage-status?' in path:return dict(ready=False,failed=False)
        body=kw['payload'];posts.append(body['publish_operation'])
        if body['publish_operation']=='poll':
            if 'publish_observation' not in body:return dict(grant,dispatch=False,probe=probe,status='waiting')
            assert body['publish_observation']['status']=='not_started'
            return dict(grant,sequence=1,probe=None)
        assert body['publish_sequence']==1
        return dict(grant,sequence=1,dispatch=False)
    def ssh(command,**kw):
        commands.append(command)
        if '--publish-probe' in command:
            if lost_probe:raise subprocess.TimeoutExpired(command,30)
            return SimpleNamespace(returncode=0,stdout=json.dumps(dict(probe,
                schema_version='cce.publish-observation.v1',status='not_started')),stderr='')
        assert posts[-1]=='check' and '--publish-dispatch' in command
        return SimpleNamespace(returncode=0,stdout='{}',stderr='')
    with patch.object(module,'_backend_json',side_effect=api),patch.object(module.subprocess,'run',side_effect=ssh),patch.object(module,'_require_runtime_enabled',create=True):
        assert module.stage_ready('step4_publish',**context) is False
    assert posts==(['poll'] if lost_probe else ['poll','poll','check','finish'])
    assert len(commands)==(1 if lost_probe else 2)
