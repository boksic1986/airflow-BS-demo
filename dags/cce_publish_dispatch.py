"""Step4 uses the existing runner and reschedule sensor, never task-wide retry."""
from datetime import datetime,timezone
import json
import os
import re
import subprocess
from airflow.exceptions import AirflowFailException


def enabled(conf):
    policy=(conf.get('params') or {}).get('cce_recovery_policy') or {}
    return policy.get('enabled') is True and policy.get('attempt')==conf['attempt']


def _request(backend,pipeline,conf,dag,operation,**extra):
    return backend(f"/api/internal/{pipeline}/runs/{conf['analysis_id']}/stages/publish_recovery",
        method='POST',payload=dict(attempt=conf['attempt'],adapter=pipeline+'-runtime-200',
            dag_run_id=dag,resume_action_id=conf.get('resume_action_id'),publish_operation=operation,**extra))


def _command(pipeline,conf,answer,probe=False):
    aid,attempt=conf['analysis_id'],conf['attempt']
    identity=answer['probe'] if probe else answer
    generation=identity['generation'];digest=identity['request_hash']
    if (pipeline not in {'wgs','gatk'} or not re.fullmatch('[A-Za-z0-9_-]{1,128}',aid)
            or type(attempt) is not int or not 0<attempt<10**9
            or type(generation) is not int or not 0<generation<10**9
            or not re.fullmatch('[0-9a-f]{64}',digest)):
        raise AirflowFailException('Invalid Step4 dispatch identity')
    prefix=pipeline.upper()
    command=['ssh','-tt','-o','BatchMode=yes','-o','ConnectTimeout=10',
        '-F',os.getenv(prefix+'_SSH_CONFIG_PATH','/opt/airflow/ssh/config'),
        os.getenv(prefix+'_RUNNER_200_ALIAS',pipeline+'-node200'),
        os.getenv(prefix+'_RUNNER_200_COMMAND','/home/ctapa/.config/airflow-'+pipeline+'/forced-command.sh'),
        '--publish-probe' if probe else '--publish-dispatch',aid,str(attempt),str(generation),digest]
    if probe:
        if not re.fullmatch('[0-9a-f]{32}',identity['nonce']):
            raise AirflowFailException('Invalid Step4 challenge')
        command.append(identity['nonce'])
    deadline=datetime.fromisoformat(answer['deadline'])
    if deadline.tzinfo is None:raise AirflowFailException('Invalid Step4 deadline')
    remaining=(deadline-datetime.now(timezone.utc)).total_seconds()
    if remaining<=0:raise AirflowFailException('Step4 original deadline exhausted; manual review required')
    return command,min(30 if probe else 120,remaining)


def _send(backend,*,pipeline,conf,dag_run_id,answer):
    command,timeout=_command(pipeline,conf,answer)
    identity=dict(publish_execution_id=answer['execution_id'],publish_sequence=answer['sequence'])
    _request(backend,pipeline,conf,dag_run_id,'check',**identity)
    # No retry loop. subprocess.run waits for termination, including TimeoutExpired.
    # Process death outside this catch leaves the committed intent unresolved.
    try:
        subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,text=True,
            check=False,timeout=timeout)
    except (OSError,subprocess.SubprocessError):
        pass
    _request(backend,pipeline,conf,dag_run_id,'finish',**identity)


def start_publish(backend,*,pipeline,conf,dag_run_id):
    answer=_request(backend,pipeline,conf,dag_run_id,'begin')
    if answer.get('dispatch') is True:
        _send(backend,pipeline=pipeline,conf=conf,dag_run_id=dag_run_id,answer=answer)
    return dict(answer,runner_status='reconciling')


def poll_publish(backend,*,pipeline,conf,dag_run_id):
    answer=_request(backend,pipeline,conf,dag_run_id,'poll')
    probe=answer.get('probe')
    if probe:
        command,timeout=_command(pipeline,conf,answer,probe=True)
        try:
            result=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,text=True,
                check=False,timeout=timeout)
            if result.returncode or len(result.stdout)>2*1024*1024:return answer
            observation=json.loads(result.stdout)
            if not isinstance(observation,dict) or any(observation.get(k)!=v for k,v in probe.items()):return answer
        except (OSError,subprocess.SubprocessError,ValueError,TypeError):
            return answer
        answer=_request(backend,pipeline,conf,dag_run_id,'poll',publish_observation=observation)
    if answer.get('dispatch') is True:
        _send(backend,pipeline=pipeline,conf=conf,dag_run_id=dag_run_id,answer=answer)
    if answer.get('status') in {'expired','exhausted','stopped','failed','canceled'}:
        raise AirflowFailException('Step4 dispatch stopped; inspect original execution before manual recovery')
    return answer
