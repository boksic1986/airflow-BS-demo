from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from wes_qsub_runner import collect_wes_artifacts, prepare_wes_config, run_wes_qsub, validate_wes_conf


def _validate_request(**context):
    return validate_wes_conf(context["dag_run"].conf or {})


def _prepare_wes_config(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="validate_request")
    config_path = prepare_wes_config(conf)
    conf["config_path"] = str(config_path)
    return conf


def _run_wes_qsub(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="prepare_wes_config")
    run_summary = run_wes_qsub(conf)
    conf["run_summary"] = run_summary
    return conf


def _collect_wes_artifacts(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="run_wes_qsub")
    return collect_wes_artifacts(conf)


with DAG(
    dag_id="bio_wes_qsub",
    description="WES mock DAG using Snakemake cluster-generic profile and mock qsub wrapper",
    start_date=datetime(2026, 7, 1),
    schedule=None,
    catchup=False,
    is_paused_upon_creation=False,
    tags=["airflow-demo", "wes", "qsub", "mock"],
) as dag:
    validate_request = PythonOperator(
        task_id="validate_request",
        python_callable=_validate_request,
    )
    prepare_wes_config_task = PythonOperator(
        task_id="prepare_wes_config",
        python_callable=_prepare_wes_config,
    )
    run_wes_qsub_task = PythonOperator(
        task_id="run_wes_qsub",
        python_callable=_run_wes_qsub,
    )
    collect_wes_artifacts_task = PythonOperator(
        task_id="collect_wes_artifacts",
        python_callable=_collect_wes_artifacts,
    )

    validate_request >> prepare_wes_config_task >> run_wes_qsub_task >> collect_wes_artifacts_task
