from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from pgta_airflow_runner import (
    build_pgta_airflow_config,
    collect_metadata_artifact,
    collect_snakemake_events,
    run_snakemake9_with_logger,
    validate_pgta_airflow_conf,
)


def _validate_request(**context):
    return validate_pgta_airflow_conf(context["dag_run"].conf or {})


def _prepare_pgta_config(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="validate_request")
    config_path = build_pgta_airflow_config(conf)
    conf["config_path"] = str(config_path)
    return conf


def _run_snakemake9_with_logger(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="prepare_pgta_config")
    events_path = run_snakemake9_with_logger(conf)
    conf["events_path"] = str(events_path)
    return conf


def _collect_snakemake_events(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="run_snakemake9_with_logger")
    summary = collect_snakemake_events(conf)
    conf["snakemake_event_summary"] = summary
    return conf


def _collect_metadata_artifact(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="collect_snakemake_events")
    return collect_metadata_artifact(conf)


with DAG(
    dag_id="bio_pgta_airflow",
    description="PGT-A Airflow-only metadata DAG with Snakemake 9 logger events",
    start_date=datetime(2026, 7, 1),
    schedule=None,
    catchup=False,
    is_paused_upon_creation=False,
    tags=["airflow-demo", "pgta", "snakemake9"],
) as dag:
    validate_request = PythonOperator(
        task_id="validate_request",
        python_callable=_validate_request,
    )
    prepare_pgta_config = PythonOperator(
        task_id="prepare_pgta_config",
        python_callable=_prepare_pgta_config,
    )
    run_snakemake9_task = PythonOperator(
        task_id="run_snakemake9_with_logger",
        python_callable=_run_snakemake9_with_logger,
    )
    collect_snakemake_events_task = PythonOperator(
        task_id="collect_snakemake_events",
        python_callable=_collect_snakemake_events,
    )
    collect_metadata_artifact_task = PythonOperator(
        task_id="collect_metadata_artifact",
        python_callable=_collect_metadata_artifact,
    )

    validate_request >> prepare_pgta_config >> run_snakemake9_task >> collect_snakemake_events_task >> collect_metadata_artifact_task
