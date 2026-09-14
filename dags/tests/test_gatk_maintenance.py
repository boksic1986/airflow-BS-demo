from types import SimpleNamespace
import bio_gatk_maintenance as maintenance


def test_maintenance_is_explicit_and_disconnected():
    assert set(maintenance.dag.task_dict) == {'step7_cleanup','wait_step7_cleanup'}
    assert maintenance.dag.catchup is False
    assert maintenance.dag.get_task('step7_cleanup').upstream_task_ids == set()
    assert maintenance.dag.get_task('wait_step7_cleanup').upstream_task_ids == {'step7_cleanup'}


def test_invalid_identity_is_rejected():
    try:
        maintenance._identity({'dag_run':SimpleNamespace(conf={'pipeline':'gatk','attempt':1})})
    except ValueError:
        return
    raise AssertionError('missing exact admin action must fail closed')


if __name__ == '__main__':
    test_maintenance_is_explicit_and_disconnected()
    test_invalid_identity_is_rejected()
    print('PASS GATK maintenance topology and authorization contract')
