from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import BranchPythonOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

from pgta_metadata_runner import (
    build_pgta_config,
    collect_pgta_artifact,
    run_pgta_stage,
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


def _choose_pgta_path(**context):
    task_instance = context["ti"]
    conf = task_instance.xcom_pull(task_ids="prepare_pgta_config")
    params = conf.get("params") or {}
    if params.get("target") == "baseline_qc":
        rerun_stage = params.get("rerun_stage")
        if rerun_stage == "metadata":
            return "pgta_pipeline.run_pgta_metadata"
        if rerun_stage == "baseline_qc":
            return "pgta_pipeline.run_pgta_baseline_qc"
        return "pgta_pipeline.run_pgta_mapping"
    return "run_pgta_target"


def _run_pgta_stage(stage: str, upstream_task_ids: list[str], **context):
    task_instance = context["ti"]
    conf = None
    for upstream_task_id in upstream_task_ids:
        conf = task_instance.xcom_pull(task_ids=upstream_task_id)
        if conf:
            break
    if not conf:
        raise ValueError(f"No PGT-A configuration found for stage={stage}")
    artifact_path = run_pgta_stage(conf, stage)
    conf[f"{stage}_artifact_path"] = str(artifact_path)
    conf["artifact_path"] = str(artifact_path)
    return conf


def _collect_pgta_artifact(**context):
    task_instance = context["ti"]
    conf = (
        task_instance.xcom_pull(task_ids="pgta_pipeline.run_pgta_baseline_qc")
        or task_instance.xcom_pull(task_ids="run_pgta_target")
    )
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
    choose_pgta_path = BranchPythonOperator(
        task_id="choose_pgta_path",
        python_callable=_choose_pgta_path,
    )
    run_pgta_target_task = PythonOperator(
        task_id="run_pgta_target",
        python_callable=_run_pgta_target,
    )
    with TaskGroup(group_id="pgta_pipeline") as pgta_pipeline:
        run_pgta_mapping_task = PythonOperator(
            task_id="run_pgta_mapping",
            python_callable=_run_pgta_stage,
            op_kwargs={"stage": "mapping", "upstream_task_ids": ["prepare_pgta_config"]},
        )
        run_pgta_metadata_task = PythonOperator(
            task_id="run_pgta_metadata",
            python_callable=_run_pgta_stage,
            op_kwargs={"stage": "metadata", "upstream_task_ids": ["pgta_pipeline.run_pgta_mapping", "prepare_pgta_config"]},
            trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
        )
        run_pgta_baseline_qc_task = PythonOperator(
            task_id="run_pgta_baseline_qc",
            python_callable=_run_pgta_stage,
            op_kwargs={
                "stage": "baseline_qc",
                "upstream_task_ids": [
                    "pgta_pipeline.run_pgta_metadata",
                    "pgta_pipeline.run_pgta_mapping",
                    "prepare_pgta_config",
                ],
            },
            trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
        )
        run_pgta_mapping_task >> run_pgta_metadata_task >> run_pgta_baseline_qc_task
    collect_pgta_artifact_task = PythonOperator(
        task_id="collect_pgta_artifact",
        python_callable=_collect_pgta_artifact,
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    validate_request >> prepare_pgta_config >> choose_pgta_path
    choose_pgta_path >> run_pgta_target_task >> collect_pgta_artifact_task
    choose_pgta_path >> run_pgta_mapping_task
    choose_pgta_path >> run_pgta_metadata_task
    choose_pgta_path >> run_pgta_baseline_qc_task
    run_pgta_baseline_qc_task >> collect_pgta_artifact_task
