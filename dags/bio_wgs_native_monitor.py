"""Opt-in native observation only; deliberately independent of the CCE graph."""
from datetime import datetime, timedelta, timezone
import os
import re

from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.sensors.python import PythonSensor
from bio_wgs import _backend_json


def observe(**context):
    if os.getenv('WGS_ONPREM_MONITOR_ENABLED', 'false').lower() not in {'true', '1', 'yes'}:
        raise AirflowFailException('Native monitoring is disabled')
    conf = context['dag_run'].conf or {}
    if (set(conf) != {'pipeline', 'monitor_only', 'analysis_id', 'execution_id', 'attempt', 'generation'}
            or conf.get('pipeline') != 'wgs' or conf.get('monitor_only') is not True
            or not re.fullmatch(r'WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}', str(conf.get('analysis_id', '')))
            or not re.fullmatch(r'wse_[a-f0-9]{24}', str(conf.get('execution_id', '')))
            or any(type(conf.get(key)) is not int or conf[key] < 1 for key in ('attempt', 'generation'))):
        raise AirflowFailException('Invalid native observation identity')
    result = _backend_json(
        f"/api/internal/wgs/onprem/runs/{conf['analysis_id']}/executions/{conf['execution_id']}/observe",
        method='POST', payload={'attempt': conf['attempt'], 'generation': conf['generation']})
    if any(result.get(key) != conf[key] for key in ('analysis_id', 'execution_id', 'attempt', 'generation')):
        raise AirflowFailException('Native observation returned a different execution')
    if result.get('done') is True:
        if result.get('status') == 'success':
            return True
        if result.get('status') in {'failed', 'canceled'}:
            raise AirflowFailException('Native execution ended unsuccessfully; inspect its evidence')
        raise AirflowFailException('Native observation returned an invalid terminal status')
    # A file result or monitoring failure never launches/restarts/fails native work.
    return False


with DAG('bio_wgs_native_monitor', start_date=datetime(2026, 9, 15, tzinfo=timezone.utc),
         schedule=None, catchup=False, is_paused_upon_creation=True,
         default_args={'retries': 3, 'retry_delay': timedelta(seconds=30),
                       'retry_exponential_backoff': True},
         tags=['wgs', 'native', 'monitor-only']) as dag:
    PythonSensor(task_id='observe_native_execution', python_callable=observe,
                 mode='reschedule', poke_interval=30, timeout=24 * 3600)
