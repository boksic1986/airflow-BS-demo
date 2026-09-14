"""Run with Airflow installed: cleanup success cannot bypass failed stages."""
import runpy
from pathlib import Path


def test_cleanup_does_not_unblock_execution():
    namespace = runpy.run_path(str(Path(__file__).parents[1] / 'bio_gatk.py'))
    dag = namespace['dag']
    for next_task, prerequisite in (
        ('submit_step2_master', 'wait_step1_upload'),
        ('materialize_step6_results', 'wait_step5_download'),
    ):
        task = dag.get_task(next_task)
        assert prerequisite in task.upstream_task_ids
        assert task.trigger_rule == 'all_success'
    assert dag.get_task('release_input_transfer_slot').trigger_rule == 'all_done'
    assert dag.get_task('release_result_transfer_slot').trigger_rule == 'all_done'


if __name__ == '__main__':
    test_cleanup_does_not_unblock_execution()
    print('PASS: successful cleanup cannot bypass stage-success dependencies')
