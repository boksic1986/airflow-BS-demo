"""Master failure evidence retains causes, never infers recovery eligibility."""
from copy import deepcopy
import json

import pytest

from scripts.tests.test_cce_recovery_workloads import cluster, pod, probe


def test_backoff_limit_preserves_master_and_container_failure_without_permission(cluster):
    objects = cluster[0]
    condition = objects["job", "master"]["status"]["conditions"][0]
    condition.update(reason="BackoffLimitExceeded", message="private diagnostic text")
    status = objects["pods", "master"]["items"][0]["status"]["containerStatuses"][0]
    status.update(restartCount=0)
    status["state"]["terminated"].update(reason="Error", signal=0, message="private container text")
    result = probe(cluster)
    assert result["master_job_condition"] == dict(type="Failed", reason="BackoffLimitExceeded")
    assert result["master_pods"]["master-pod-uid"]["containers"] == [dict(
        kind="main", name="main", exit_code=1, reason="Error", signal=0,
        restart_count=0, previous_termination=None)]
    assert result["master_container_exit_codes"] == {"main": 1}
    assert not ({"sealed", "complete", "automatic_recovery_allowed", "fatal_source"} & result.keys())
    assert "private" not in json.dumps(result)


def test_prior_master_pod_and_container_restart_failure_are_not_discarded(cluster):
    objects = cluster[0]
    prior = pod("prior-master", "prior-master-uid", "master-uid", 137)
    prior["status"]["containerStatuses"][0]["state"]["terminated"].update(reason="OOMKilled", signal=9)
    objects["pods", "master"]["items"].append(prior)
    current = objects["pods", "master"]["items"][0]["status"]["containerStatuses"][0]
    current.update(restartCount=2, lastState=dict(terminated=dict(exitCode=137, reason="OOMKilled", signal=9)))
    result = probe(cluster)
    assert set(result["master_pods"]) == {"master-pod-uid", "prior-master-uid"}
    assert result["master_pods"]["prior-master-uid"]["containers"][0]["reason"] == "OOMKilled"
    current_result = result["master_pods"]["master-pod-uid"]["containers"][0]
    assert current_result["restart_count"] == 2
    assert current_result["previous_termination"] == dict(exit_code=137, reason="OOMKilled", signal=9)
    assert result["master_container_exit_codes"] == {"main": 1}


def test_missing_and_unknown_reasons_do_not_become_normal_exit_or_expose_text(cluster):
    current = cluster[0]["pods", "master"]["items"][0]
    current["status"]["containerStatuses"][0]["state"]["terminated"]["reason"] = "private arbitrary text"
    result = probe(cluster)
    assert result["master_job_condition"]["reason"] is None
    container = result["master_pods"]["master-pod-uid"]["containers"][0]
    assert container["reason"] == "Unknown" and container["restart_count"] is None
    assert container["signal"] is None and "private" not in json.dumps(result)


def test_master_init_and_ephemeral_container_failures_are_recorded(cluster):
    current = cluster[0]["pods", "master"]["items"][0]
    for spec_key, status_key, name in [("initContainers", "initContainerStatuses", "init"),
                                     ("ephemeralContainers", "ephemeralContainerStatuses", "debug")]:
        current["spec"][spec_key] = [dict(name=name)]
        current["status"][status_key] = [dict(name=name, restartCount=0,
            state=dict(terminated=dict(exitCode=137, reason="OOMKilled", signal=9)))]
    containers = probe(cluster)["master_pods"]["master-pod-uid"]["containers"]
    assert [(c["kind"], c["reason"]) for c in containers] == [
        ("main", None), ("init", "OOMKilled"), ("ephemeral", "OOMKilled")]


@pytest.mark.parametrize("change", ["restarts", "previous_exit", "conflicting_conditions"])
def test_malformed_master_history_is_not_a_clean_failure(cluster, change):
    current = cluster[0]["pods", "master"]["items"][0]["status"]["containerStatuses"][0]
    if change == "restarts":
        current["restartCount"] = True
    elif change == "previous_exit":
        current["lastState"] = dict(terminated=dict(exitCode=True))
    else:
        conditions = cluster[0]["job", "master"]["status"]["conditions"]
        conditions.append(dict(deepcopy(conditions[0]), reason="DeadlineExceeded"))
    with pytest.raises(ValueError):
        probe(cluster)
