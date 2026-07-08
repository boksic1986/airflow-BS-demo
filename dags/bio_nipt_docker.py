from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from nipt_docker_runner import collect_nipt_artifacts, prepare_nipt_docker_run, run_nipt_docker, validate_nipt_conf


def _validate_request(**context):
    return validate_nipt_conf(context["dag_run"].conf or {})


def _prepare_nipt_docker_run(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="validate_request")
    return prepare_nipt_docker_run(conf)


def _run_nipt_docker(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="prepare_nipt_docker_run")
    run_summary = run_nipt_docker(conf)
    conf["run_summary"] = run_summary
    return conf


def _collect_nipt_artifacts(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="run_nipt_docker")
    return collect_nipt_artifacts(conf)


with DAG(
    dag_id="bio_nipt_docker",
    description="NIPT Docker scanned-batch DAG using repo-owned compose runner",
    start_date=datetime(2026, 7, 1),
    schedule=None,
    catchup=False,
    is_paused_upon_creation=False,
    tags=["airflow-demo", "nipt", "docker"],
) as dag:
    validate_request = PythonOperator(
        task_id="validate_request",
        python_callable=_validate_request,
    )
    prepare_nipt_docker_run_task = PythonOperator(
        task_id="prepare_nipt_docker_run",
        python_callable=_prepare_nipt_docker_run,
    )
    run_nipt_docker_task = PythonOperator(
        task_id="run_nipt_docker",
        python_callable=_run_nipt_docker,
    )
    collect_nipt_artifacts_task = PythonOperator(
        task_id="collect_nipt_artifacts",
        python_callable=_collect_nipt_artifacts,
    )

    validate_request >> prepare_nipt_docker_run_task >> run_nipt_docker_task >> collect_nipt_artifacts_task
