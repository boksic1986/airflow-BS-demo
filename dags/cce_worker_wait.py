"""One read-only Worker probe inside the existing Step3 reschedule sensor."""
from datetime import datetime, timezone
import json
import os
import re
import subprocess


def poll_recovery(backend, *, pipeline, conf, dag_run_id):
    path = f"/api/internal/{pipeline}/runs/{conf['analysis_id']}/stages/compute_recovery"
    payload = dict(attempt=conf['attempt'],adapter=pipeline+'-runtime-200',
        dag_run_id=dag_run_id,resume_action_id=conf.get('resume_action_id'))
    answer = backend(path,method='POST',payload=payload)
    if not answer or answer.get('status') != 'waiting' or not answer.get('worker_probe'):
        return answer or dict(status='waiting')
    probe = answer['worker_probe']
    try:
        # No shell text or paths can be supplied by the observation challenge.
        aid, attempt, generation = conf['analysis_id'], conf['attempt'], probe['generation']
        if (pipeline not in {'wgs','gatk'} or not re.fullmatch('[A-Za-z0-9_-]{1,128}',aid)
                or type(attempt) is not int or not 0 < attempt < 10**9
                or type(generation) is not int or not 0 < generation < 10**9
                or not re.fullmatch('[0-9a-f]{64}',probe['request_hash'])
                or not re.fullmatch('[0-9a-f]{32}',probe['nonce'])):
            return answer
        deadline = datetime.fromisoformat(answer['worker_wait_deadline'])
        if deadline.tzinfo is None:
            return answer
        remaining = (deadline-datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            return answer
        prefix = pipeline.upper()
        command = ['ssh','-tt','-o','BatchMode=yes','-o','ConnectTimeout=10',
            '-F',os.getenv(prefix+'_SSH_CONFIG_PATH','/opt/airflow/ssh/config'),
            os.getenv(prefix+'_RUNNER_200_ALIAS',pipeline+'-node200'),
            os.getenv(prefix+'_RUNNER_200_COMMAND','/home/ctapa/.config/airflow-'+pipeline+'/forced-command.sh'),
            '--recovery-probe',aid,str(attempt),str(generation),probe['request_hash'],probe['nonce']]
        result = subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,text=True,
            check=False,timeout=min(150,remaining))
        if datetime.now(timezone.utc) >= deadline:
            return answer
        if result.returncode or len(result.stdout) > 2*1024*1024:
            return answer
        observation = json.loads(result.stdout)
        if not isinstance(observation,dict) or any(observation.get(k) != v for k,v in probe.items()):
            return answer
    except (OSError,subprocess.SubprocessError,ValueError,TypeError,KeyError):
        # No local retry. The persisted deadline/action survives sensor reschedule.
        return answer
    return backend(path,method='POST',payload=dict(payload,worker_observation=observation)) or answer
