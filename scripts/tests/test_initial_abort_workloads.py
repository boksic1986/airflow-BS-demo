"""INITIAL_ABORTED live observations with synthetic Kubernetes transport only."""
from copy import deepcopy

import pytest

from scripts import cce_recovery_workloads as workloads
from test_cce_recovery_workloads import cluster, job, pod


@pytest.fixture
def empty_initial_cluster(cluster):
    # Retain the existing query fixture and exercise the real complete inventory.
    cluster[0].clear()
    cluster[0]["job", "master"] = None
    return cluster


def probe(cluster):
    return workloads.probe_initial_workloads(
        runtime=cluster[2], config={"kubernetes": {"namespace": "test"}},
        namespace="test", run_label="synthetic-run", master_job="master",
        master_job_uid="master-uid")


def test_initial_abort_observes_complete_absence_without_compute_final(empty_initial_cluster):
    assert probe(empty_initial_cluster) == {
        "master": None, "master_state": "INITIAL_ABORTED", "workers": [],
        "workers_inactive": True,
    }
    assert empty_initial_cluster[1] == [
        ("jobs", "-l", "cce.biosan.cn/run-id=synthetic-run", "--chunk-size=0"),
        ("pods", "-l", "cce.biosan.cn/run-id=synthetic-run", "--chunk-size=0"),
        ("jobs", "--chunk-size=0"), ("pods", "--chunk-size=0"),
        ("job", "master"),
    ]


def test_initial_abort_rejects_late_terminal_master(empty_initial_cluster):
    # Even a terminal old UID cannot count as complete absence before takeover.
    empty_initial_cluster[0]["job", "master"] = job("master", "master-uid")
    with pytest.raises(ValueError):
        probe(empty_initial_cluster)


def test_initial_abort_rejects_unlabelled_orphan_pod(empty_initial_cluster):
    orphan = pod("master-pod", "orphan-pod-uid", "master-uid")
    del orphan["metadata"]["labels"]["cce.biosan.cn/run-id"]
    empty_initial_cluster[0]["pods", "master"] = {
        "kind": "PodList", "metadata": {}, "items": [orphan],
    }
    with pytest.raises(ValueError):
        probe(empty_initial_cluster)


def test_initial_abort_replay_observes_only_verified_active_replacement(empty_initial_cluster):
    replacement = job("master", "replacement-uid")
    replacement["metadata"]["resourceVersion"] = "1"
    replacement["status"] = {"active": 1, "conditions": []}
    active_pod = pod("master-pod", "replacement-pod-uid", "replacement-uid")
    active_pod["status"] = {
        "phase": "Running", "containerStatuses": [{
            "name": "main", "state": {"running": {}},
        }],
    }
    empty_initial_cluster[0]["job", "master"] = deepcopy(replacement)
    empty_initial_cluster[0]["pods", "master"] = {
        "kind": "PodList", "metadata": {}, "items": [active_pod],
    }
    kwargs = dict(
        runtime=empty_initial_cluster[2], config={"kubernetes": {"namespace": "test"}},
        namespace="test", run_label="synthetic-run", master_job="master",
        master_job_uid="master-uid", replacement_job=replacement)
    assert workloads.probe_initial_workloads(**kwargs) == {
        "master": replacement, "master_state": "INITIAL_ABORTED", "workers": [],
        "workers_inactive": True,
    }
    # A later read of the same new UID must still match the verified version.
    empty_initial_cluster[0]["job", "master"]["metadata"]["resourceVersion"] = "2"
    with pytest.raises(ValueError):
        workloads.probe_initial_workloads(**kwargs)


def test_initial_abort_replay_rejects_old_uid_pod_without_labels_or_original_owner_name(empty_initial_cluster):
    replacement = job("master", "replacement-uid")
    replacement["metadata"]["resourceVersion"] = "1"
    replacement["status"] = {"active": 1, "conditions": []}
    empty_initial_cluster[0]["job", "master"] = deepcopy(replacement)
    old_pod = pod("renamed-old-pod", "late-old-pod-uid", "master-uid")
    old_pod["metadata"]["labels"] = {}
    empty_initial_cluster[0]["pods", "renamed-old"] = {
        "kind": "PodList", "metadata": {}, "items": [old_pod],
    }
    with pytest.raises(ValueError):
        workloads.probe_initial_workloads(
            runtime=empty_initial_cluster[2], config={"kubernetes": {"namespace": "test"}},
            namespace="test", run_label="synthetic-run", master_job="master",
            master_job_uid="master-uid", replacement_job=replacement)
