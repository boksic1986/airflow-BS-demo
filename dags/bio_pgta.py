from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from pgta_metadata_runner import (
    build_pgta_config,
    collect_pgta_artifact,
    run_pgta_target,
    validate_pgta_conf,
)


def _validate_request(**context):
    return validate_pgta_conf(context["dag_run"].conf or {})


def _prepare_pgta_config(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="validate_request")
    config_path = build_pgta_config(conf)
    conf["config_path"] = str(config_path)
    return conf


def _run_pgta_target(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="prepare_pgta_config")
    artifact_path = run_pgta_target(conf)
    conf["artifact_path"] = str(artifact_path)
    return conf


def _collect_pgta_artifact(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="run_pgta_target")
    return collect_pgta_artifact(conf)


with DAG(
    dag_id="bio_pgta",
    description="PGT-A demo DAG for metadata, dry-run, and controlled failure smoke",
    start_date=datetime(2026, 7, 1),
    schedule=None,
    catchup=False,
    is_paused_upon_creation=False,
    tags=["airflow-demo", "pgta"],
) as dag:
    validate_request = PythonOperator(
        task_id="validate_request",
        python_callable=_validate_request,
    )
    prepare_pgta_config = PythonOperator(
        task_id="prepare_pgta_config",
        python_callable=_prepare_pgta_config,
    )
    run_pgta_target_task = PythonOperator(
        task_id="run_pgta_target",
        python_callable=_run_pgta_target,
    )
    collect_pgta_artifact_task = PythonOperator(
        task_id="collect_pgta_artifact",
        python_callable=_collect_pgta_artifact,
    )

    validate_request >> prepare_pgta_config >> run_pgta_target_task >> collect_pgta_artifact_task
