"""WGS cleanup only. Never consumes an analysis DagRun or transfer slot."""
from datetime import datetime, timedelta
import json
import os
import re
import subprocess
import time
from urllib.parse import urlencode

from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
from bio_wgs import _backend_json, BackendTransportUnavailable


DELAYS = (30, 60, 120)


def identity(context):
    conf = context['dag_run'].conf or {}
    aid = str(conf.get('analysis_id', ''))
    action = str(conf.get('maintenance_action_id', ''))
    attempt, generation = int(conf.get('attempt', 0)), int(conf.get('step7_generation', 0))
    if (not re.fullmatch(r'WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}', aid)
            or not re.fullmatch(r'step7-sfs-[a-f0-9]{12}', action)
            or attempt < 1 or generation < 1 or conf.get('maintenance_mode') != 'cleanup_step7'):
        raise AirflowFailException('invalid WGS maintenance identity')
    return aid, attempt, action, generation


def report(context, state, message=''):
    aid, attempt, action, generation = identity(context)
    return _backend_json(f'/api/internal/wgs/runs/{aid}/maintenance/{action}/observation',
        method='POST', payload={'attempt': attempt, 'generation': generation,
            'dag_run_id': context['dag_run'].run_id, 'status': state, 'message': message})


def remote(context, verb, action=None, generation=None):
    aid, attempt, current, current_generation = identity(context)
    command = ['ssh', '-T', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=15',
        '-o', 'ServerAliveCountMax=2', '-F', os.getenv('WGS_SSH_CONFIG_PATH', '/opt/airflow/ssh/config'),
        os.getenv('WGS_RUNNER_200_ALIAS', 'wgs-node200'),
        os.getenv('WGS_RUNNER_200_COMMAND', '/home/ctapa/.config/airflow-wgs/forced-command.sh'),
        verb, aid, str(attempt), action or current, str(generation or current_generation)]
    result = subprocess.run(command, capture_output=True, text=True,
                            stdin=subprocess.DEVNULL, timeout=60)
    if result.returncode:
        if result.returncode != 255 or any(term in result.stderr.lower() for term in
                ('permission denied', 'host key verification failed', 'no supported authentication')):
            raise AirflowFailException('Step7 identity, configuration or authentication rejected')
        raise ConnectionError('Step7 connection unavailable')
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise AirflowFailException('Step7 returned invalid status') from exc
    if (value.get('analysis_id') != aid or value.get('attempt') != attempt
            or value.get('maintenance_action_id') != (action or current)
            or value.get('step7_generation') != (generation or current_generation)):
        raise AirflowFailException('Step7 response identity mismatch')
    return value


def probe(context, action=None, generation=None):
    for index in range(len(DELAYS) + 1):
        try:
            return remote(context, 'wgs-step7-status', action, generation)
        except (ConnectionError, subprocess.TimeoutExpired):
            if index == len(DELAYS):
                raise AirflowFailException('清理状态待确认：连接查询已耗尽；未重复派发删除')
            time.sleep(DELAYS[index])


def registered_context(context):
    aid, attempt, action, generation = identity(context)
    query = urlencode({'attempt': attempt, 'generation': generation, 'dag_run_id': context['dag_run'].run_id})
    for index in range(len(DELAYS) + 1):
        try:
            return _backend_json(f'/api/internal/wgs/runs/{aid}/maintenance/{action}/context?{query}')
        except BackendTransportUnavailable:
            if index == len(DELAYS):
                raise AirflowFailException('清理状态待确认：维护查询不可用')
            time.sleep(DELAYS[index])


def start_cleanup(**context):
    aid, attempt, action, generation = identity(context)
    registered = registered_context(context)
    previous = registered.get('action') if registered.get('registered') else None
    if previous:
        value = probe(context, previous, registered['generation'])
        if value['status'] in ('running', 'success'):
            report(context, value['status'])
            return {'action': previous, 'generation': registered['generation']}
        if value['status'] not in ('failed', 'not_started'):
            raise AirflowFailException('清理状态待确认：原执行结果不明')
        if value['status'] == 'failed' and previous == action:
            raise AirflowFailException(value.get('message') or '清理已失败，请手动重试')
        if previous != action:
            report(context, 'stopped')
    if previous != action:
        try:
            _backend_json(f'/api/internal/wgs/runs/{aid}/stages/step7_cleanup', method='POST',
                payload={'attempt': attempt, 'adapter': 'wgs-runtime-200',
                         'command': f'wgs-runtime {aid} {attempt} step7_cleanup',
                         'maintenance_action_id': action, 'force_new_generation': bool(previous)})
        except BackendTransportUnavailable:
            recovered = registered_context(context)
            if recovered.get('action') != action or recovered.get('generation') != generation:
                raise AirflowFailException('清理状态待确认：注册响应丢失，未派发删除')
    value = probe(context)
    if value['status'] == 'not_started':
        # At most two sends of the SAME identity. The remote launch lock and
        # request identity fence make a delayed first send safe to reconcile.
        for send in range(2):
            try:
                remote(context, 'wgs-step7-start')
            except (ConnectionError, subprocess.TimeoutExpired):
                pass
            value = probe(context)
            if value['status'] != 'not_started':
                break
    if value['status'] not in ('running', 'success'):
        raise AirflowFailException(value.get('message') or '清理状态待确认：未确认后台执行')
    report(context, value['status'])
    return {'action': action, 'generation': generation}


def cleanup_ready(**context):
    source = context['ti'].xcom_pull(task_ids='step7_cleanup')
    if not source:
        raise AirflowFailException('Step7 execution identity missing')
    value = probe(context, source['action'], source['generation'])
    if value['status'] not in ('running', 'success'):
        raise AirflowFailException(value.get('message') or '清理状态待确认：后台执行已中断')
    observed = report(context, value['status'])
    return value['status'] == 'success' and observed.get('status') == 'success'


def mark_failed(context):
    # Do not issue another query/retry budget or another launch from a callback.
    report(context, 'failed', str(context.get('exception') or '清理监控已停止，重试前需核对原执行')[:500])


with DAG('bio_wgs_maintenance', start_date=datetime(2026, 9, 22), schedule=None,
         catchup=False, is_paused_upon_creation=False, max_active_runs=1,
         dagrun_timeout=timedelta(hours=24), default_args={'retries': 0},
         on_failure_callback=mark_failed, tags=['wgs', 'maintenance']) as dag:
    start = PythonOperator(task_id='step7_cleanup', python_callable=start_cleanup,
                           execution_timeout=timedelta(minutes=20), on_failure_callback=mark_failed)
    wait = PythonSensor(task_id='wait_step7_cleanup', python_callable=cleanup_ready,
                        mode='reschedule', poke_interval=30, timeout=24*3600,
                        execution_timeout=timedelta(minutes=10), on_failure_callback=mark_failed)
    start >> wait
