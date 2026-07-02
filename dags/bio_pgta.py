from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from pgta_metadata_runner import (
    build_pgta_config,
    collect_metadata_artifact,
    run_pgta_metadata,
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


def _run_metadata(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="prepare_pgta_config")
    metadata_path = run_pgta_metadata(conf)
    conf["metadata_path"] = str(metadata_path)
    return conf


def _collect_metadata_artifact(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="run_metadata")
    return collect_metadata_artifact(conf)


with DAG(
    dag_id="bio_pgta",
    description="PGT-A metadata-only demo DAG",
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
    run_metadata = PythonOperator(
        task_id="run_metadata",
        python_callable=_run_metadata,
    )
    collect_metadata_artifact = PythonOperator(
        task_id="collect_metadata_artifact",
        python_callable=_collect_metadata_artifact,
    )

    validate_request >> prepare_pgta_config >> run_metadata >> collect_metadata_artifact
