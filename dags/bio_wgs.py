from __future__ import annotations

from datetime import datetime, timedelta
import os
import re
from typing import Any

from airflow import DAG
from airflow.operators.python import BranchPythonOperator
from airflow.operators.python import PythonOperator
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule


ANALYSIS_ID_RE = re.compile(r"^WGS_[0-9]{8}_[0-9]{6}_[A-F0-9]{6}$")


def _validate_request(**context) -> dict[str, Any]:
    conf = dict(context["dag_run"].conf or {})
    analysis_id = str(conf.get("analysis_id") or "")
    if conf.get("pipeline") != "wgs":
        raise ValueError("pipeline must be wgs.")
    if not ANALYSIS_ID_RE.fullmatch(analysis_id):
        raise ValueError("analysis_id is not a generated WGS identifier.")
    params = dict(conf.get("params") or {})
    if params.get("wgs_stage") not in {"precalling", "full"}:
        raise ValueError("params.wgs_stage must be precalling or full.")
    return conf


def _host_task(
    *,
    task_id: str,
    stage: str,
    timeout_hours: int,
    pool: str | None = None,
    trigger_rule: str = TriggerRule.ALL_SUCCESS,
) -> SSHOperator:
    return SSHOperator(
        task_id=task_id,
        ssh_conn_id="wgs_host",
        command=f"wgs-run {{{{ dag_run.conf['analysis_id'] }}}} {stage}",
        cmd_timeout=None,
        conn_timeout=10,
        banner_timeout=30,
        get_pty=False,
        execution_timeout=timedelta(hours=timeout_hours),
        pool=pool,
        trigger_rule=trigger_rule,
    )


def _choose_wgs_path(**context) -> str:
    params = dict((context["dag_run"].conf or {}).get("params") or {})
    if params.get("wgs_stage") == "precalling":
        return "collect_wgs_artifacts"
    return "wgs_pipeline.variant_analysis"


with DAG(
    dag_id="bio_wgs",
    description="WGS Snakemake 9 workflow executed on the BS10610 host through a restricted SSH gate",
    start_date=datetime(2026, 7, 14),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    tags=["airflow-demo", "wgs", "snakemake9", "host-runner"],
) as dag:
    validate_request = PythonOperator(task_id="validate_request", python_callable=_validate_request)
    prepare_wgs_run = _host_task(task_id="prepare_wgs_run", stage="prepare", timeout_hours=1)

    with TaskGroup(group_id="wgs_pipeline"):
        pre_calling = _host_task(
            task_id="pre_calling",
            stage="pre_calling",
            timeout_hours=48,
            pool=os.getenv("WGS_AIRFLOW_POOL", "wgs_full"),
        )
        variant_analysis = _host_task(
            task_id="variant_analysis",
            stage="variant_analysis",
            timeout_hours=72,
            pool=os.getenv("WGS_AIRFLOW_POOL", "wgs_full"),
        )
        collect_qc = _host_task(
            task_id="collect_qc",
            stage="collect_qc",
            timeout_hours=12,
            pool=os.getenv("WGS_AIRFLOW_POOL", "wgs_full"),
        )
        variant_analysis >> collect_qc

    choose_wgs_path = BranchPythonOperator(task_id="choose_wgs_path", python_callable=_choose_wgs_path)

    collect_wgs_artifacts = _host_task(
        task_id="collect_wgs_artifacts",
        stage="collect_artifacts",
        timeout_hours=1,
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    validate_request >> prepare_wgs_run >> pre_calling
    pre_calling >> choose_wgs_path
    choose_wgs_path >> variant_analysis
    choose_wgs_path >> collect_wgs_artifacts
    collect_qc >> collect_wgs_artifacts
