from pathlib import Path


DAG_PATH = Path(__file__).parents[1] / "bio_wgs.py"

EXPECTED_TASKS = {
    "validate_request",
    "prepare_wgs_batch",
    "input_transfer.acquire_obs_transfer_slot",
    "input_transfer.start_step1_upload",
    "input_transfer.wait_step1_upload",
    "input_transfer.release_obs_transfer_slot",
    "submit_step2_master",
    "start_step3_monitor",
    "wait_step3_analysis",
    "start_step4_publish",
    "wait_step4_publish",
    "result_transfer.acquire_obs_transfer_slot",
    "result_transfer.start_step5_download",
    "result_transfer.wait_step5_download",
    "result_transfer.release_obs_transfer_slot",
    "materialize_step6_results",
    "finalize_run",
    "release_leases",
}

FORBIDDEN = {
    "snapshot_fastq",
    "start_fastq_md5",
    "wait_fastq_md5",
    "verify_input_obs",
    "acquire_master_slot",
    "reconcile_rules_and_pods",
    "wait_linkage_complete",
    "verify_result_md5",
}


def test_single_cce_dag_declares_4_1_1_runtime_contract() -> None:
    text = DAG_PATH.read_text(encoding="utf-8")
    assert 'dag_id="bio_wgs"' in text
    assert "is_paused_upon_creation=True" in text
    assert "WGS_EXECUTION_ENABLED" in text
    assert "WGS_RUNTIME_ADAPTER_ENABLED" in text
    assert '"ssh"' in text
    assert '"-tt"' in text
    assert '"-F"' in text
    assert "WGS_SSH_CONFIG_PATH" in text
    assert "WGS_RUNNER_200_ALIAS" in text
    assert "SSHHook" not in text
    assert "wgs-runtime" in text
    assert 'mode="reschedule"' in text
    assert 'pool="wgs_obs_transfer"' in text
    assert 'pool="wgs_cce_runs"' in text
    assert '"step1_upload"' in text
    assert '"step2_master"' in text
    assert '"step3_monitor"' in text
    assert '"step4_publish"' in text
    assert '"step5_download"' in text
    assert '"step6_materialize"' in text
    assert 'execution_timeout=timedelta(minutes=2)' in text
    for name in FORBIDDEN:
        assert f'"{name}"' not in text


def test_runtime_dag_has_exact_topology_and_reschedule_sensors() -> None:
    import sys

    sys.path.insert(0, str(DAG_PATH.parent))
    from bio_wgs import dag

    assert {task.task_id for task in dag.tasks} == EXPECTED_TASKS
    sensors = {
        "input_transfer.wait_step1_upload",
        "wait_step3_analysis",
        "wait_step4_publish",
        "result_transfer.wait_step5_download",
    }
    assert all(dag.get_task(task_id).mode == "reschedule" for task_id in sensors)
    assert dag.max_active_runs == 4
    assert dag.is_paused_upon_creation is True
