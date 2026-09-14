"""Admin-requested cleanup, intentionally separate from analysis completion."""
from datetime import datetime, timedelta, timezone
import os
import re
import subprocess

from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
from bio_gatk import _backend_json


def _identity(context):
    conf = context['dag_run'].conf or {}
    aid = str(conf.get('analysis_id') or '')
    action = str(conf.get('maintenance_action_id') or '')
    attempt = int(conf.get('attempt') or 0)
    if (conf.get('pipeline') != 'gatk' or attempt < 1
        or not re.fullmatch(r'GATK_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}', aid)
        or not re.fullmatch(r'gatk-step7-[a-f0-9]{12}', action)):
        raise ValueError('invalid GATK maintenance identity')
    return aid, attempt, action


def start_cleanup(**context):
    aid, attempt, action = _identity(context)
    value = _backend_json(f'/api/internal/gatk/runs/{aid}/maintenance/{action}', method='POST',
        payload={'attempt':attempt,'adapter':'gatk-runtime-200'})
    command = ['ssh','-tt','-F',os.environ.get('GATK_SSH_CONFIG_PATH','/opt/airflow/ssh/config'),
        os.environ.get('GATK_RUNNER_200_ALIAS','gatk-node200'),
        os.environ.get('GATK_RUNNER_200_COMMAND','/home/ctapa/.config/airflow-gatk/forced-command.sh'),
        'gatk-runtime', aid, str(attempt), 'step7_cleanup', str(int(value['generation']))]
    subprocess.run(command, check=True, timeout=600, stdin=subprocess.DEVNULL)


def cleanup_ready(**context):
    aid, attempt, action = _identity(context)
    value = _backend_json(f'/api/internal/gatk/runs/{aid}/maintenance/{action}?attempt={attempt}')
    if value.get('failed'):
        raise AirflowFailException(value.get('message') or 'GATK cleanup failed')
    return bool(value.get('ready'))


def mark_failed(context):
    aid, attempt, action = _identity(context)
    _backend_json(f'/api/internal/gatk/runs/{aid}/maintenance/{action}/failed', method='POST',
        payload={'attempt':attempt,'adapter':'gatk-runtime-200'})


with DAG('bio_gatk_maintenance', start_date=datetime(2026,9,14,tzinfo=timezone.utc),
    schedule=None, catchup=False, is_paused_upon_creation=False,
    on_failure_callback=mark_failed,
    default_args={'retries':3,'retry_delay':timedelta(seconds=30),'retry_exponential_backoff':True},
    tags=['gatk','maintenance']) as dag:
    start = PythonOperator(task_id='step7_cleanup', python_callable=start_cleanup)
    wait = PythonSensor(task_id='wait_step7_cleanup', python_callable=cleanup_ready,
        mode='reschedule', poke_interval=30, timeout=24*3600)
    start >> wait
