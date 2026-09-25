"""Real Airflow sensor callables: waiting reschedules, delegated stops old DAG."""
import importlib
from datetime import datetime, timedelta, timezone
import json
import subprocess
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from airflow.exceptions import AirflowSkipException

sys.path.insert(0,str(Path(__file__).parents[1]))


@pytest.mark.parametrize('pipeline',['wgs','gatk'])
def test_sensor_waits_then_stops_old_chain_without_deactivating_replacement(pipeline):
    module=importlib.import_module('bio_'+pipeline)
    conf=dict(analysis_id='SYNTHETIC',pipeline=pipeline,attempt=1,execution_mode='cce',
        params=dict(cce_recovery_policy=dict(enabled=True,attempt=1)))
    context=dict(dag_run=SimpleNamespace(conf=conf,run_id='actual-old-dag'))
    result={'status':'waiting'};calls=[];observed={'failed':True}
    def api(path,**kw):
        calls.append((path,kw))
        if '/stage-status?' in path:return dict(observed)
        if path.endswith('/stages/compute_recovery'):return dict(result)
        raise AssertionError('old monitor must not deactivate or advance after recovery')
    with patch.object(module,'_backend_json',side_effect=api):
        with patch.dict('os.environ',{'WGS_RUNTIME_ENABLED':'true','WGS_RUNTIME_ADAPTER':'wgs-runtime'}):
            if pipeline=='wgs':
                with patch.object(module,'_require_runtime_enabled'):
                    assert module.stage_ready('step3_monitor',**context) is False
                    observed.clear()  # Lost reply: GET now sees the replacement running.
                    result['status']='delegated'
                    with pytest.raises(AirflowSkipException):module.stage_ready('step3_monitor',**context)
            else:
                assert module.stage_ready('step3_monitor',**context) is False
                observed.clear()
                result['status']='delegated'
                with pytest.raises(AirflowSkipException):module.stage_ready('step3_monitor',**context)
    posts=[kw['payload'] for path,kw in calls if path.endswith('/stages/compute_recovery')]
    assert len(posts)==2 and all(p['dag_run_id']=='actual-old-dag' for p in posts)


@pytest.mark.parametrize('pipeline',['wgs','gatk'])
@pytest.mark.parametrize('lost',[False,True])
def test_existing_sensor_runs_one_bounded_read_only_probe(pipeline,lost):
    module=importlib.import_module('bio_'+pipeline)
    conf=dict(analysis_id='SYNTHETIC',pipeline=pipeline,attempt=1,execution_mode='cce',
        params=dict(cce_recovery_policy=dict(enabled=True,attempt=1)))
    context=dict(dag_run=SimpleNamespace(conf=conf,run_id='actual-old-dag'))
    challenge=dict(nonce='a'*32,execution_id='monitor',generation=1,request_hash='b'*64)
    observation=dict(challenge,cce_recovery_evidence={'synthetic':'validated by backend, not by sensor'})
    posts=[]
    def api(path,**kw):
        if '/stage-status?' in path:return dict(failed=True)
        assert path.endswith('/stages/compute_recovery')
        posts.append(kw['payload'])
        if len(posts)==1:
            return dict(status='waiting',worker_probe=challenge,
                worker_wait_deadline=(datetime.now(timezone.utc)+timedelta(seconds=20)).isoformat())
        assert kw['payload']['worker_observation']==observation
        return dict(status='delegated')
    def ssh(command,**kw):
        assert command[-6:]==['--recovery-probe','SYNTHETIC','1','1','b'*64,'a'*32]
        assert 'BatchMode=yes' in command and 0 < kw['timeout'] <= 20
        if lost:raise subprocess.TimeoutExpired(command,20)
        return SimpleNamespace(returncode=0,stdout=json.dumps(observation),stderr='')
    with patch.object(module,'_backend_json',side_effect=api),patch('cce_worker_wait.subprocess.run',side_effect=ssh) as execute:
        with patch.dict('os.environ',{'WGS_RUNTIME_ENABLED':'true','WGS_RUNTIME_ADAPTER':'wgs-runtime'}):
            # Only WGS uses a deployment gate; real stage_ready remains under test.
            with patch.object(module,'_require_runtime_enabled',create=True):
                if lost:assert module.stage_ready('step3_monitor',**context) is False
                else:
                    with pytest.raises(AirflowSkipException):module.stage_ready('step3_monitor',**context)
    assert execute.call_count==1 and len(posts)==(1 if lost else 2)
