"""Real Airflow import contract; run in a fresh process for each global default."""
import runpy
from pathlib import Path

from airflow.configuration import conf


def test_gatk_inherits_global_concurrency():
    dag = runpy.run_path(str(Path(__file__).parents[1] / "bio_gatk.py"))["dag"]
    assert dag.max_active_runs == conf.getint("core", "max_active_runs_per_dag")


def test_master_submission_does_not_take_a_gatk_exclusive_pool():
    dag = runpy.run_path(str(Path(__file__).parents[1] / "bio_gatk.py"))["dag"]
    assert dag.get_task("submit_step2_master").pool == "default_pool"
    assert dag.get_task("acquire_input_transfer_slot").pool == "wgs_obs_upload"
    assert dag.get_task("acquire_result_transfer_slot").pool == "wgs_obs_download"
    assert dag.get_task("acquire_input_transfer_slot").mode == "reschedule"
    assert dag.get_task("acquire_result_transfer_slot").mode == "reschedule"


if __name__ == "__main__":
    test_gatk_inherits_global_concurrency()
    test_master_submission_does_not_take_a_gatk_exclusive_pool()
    print("PASS: inherited concurrency and directional transfer pools")
