from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "bio_gatk.py"


def test_gatk_dag_keeps_project_level_step1_to_step6_graph() -> None:
    text = SOURCE.read_text(encoding="utf-8")

    assert 'dag_id="bio_gatk"' in text
    for task_id in (
        "validate_request",
        "prepare_gatk_contract",
        "start_step1_upload",
        "submit_step2_master",
        "start_step3_monitor",
        "start_step4_publish",
        "start_step5_download",
        "materialize_step6_results",
        "finalize_run",
    ):
        assert f'"{task_id}"' in text
    assert "bio_wgs" not in text
    assert "intake" not in text.lower()


def test_gatk_dag_uses_shared_transfer_lease_contract() -> None:
    text = SOURCE.read_text(encoding="utf-8")

    assert "acquire_input_transfer_slot" in text
    assert "acquire_result_transfer_slot" in text
    assert "release_leases" in text
    assert "gatk-runtime-200" in text
    assert 'str(registered["generation"])' in text


def test_gatk_release_leaf_preserves_upstream_failure() -> None:
    text = SOURCE.read_text(encoding="utf-8")

    assert "def _upstream_failure_task_ids" in text
    assert "upstream tasks failed after leases were released" in text
    assert "python_callable=release_leases" in text
