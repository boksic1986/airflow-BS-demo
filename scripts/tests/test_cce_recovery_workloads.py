"""Synthetic native workload-query boundary checks; never query a cluster."""
from copy import deepcopy
import importlib
from types import SimpleNamespace

import pytest


def job(name, uid, state="Failed"):
    return dict(kind="Job", metadata=dict(name=name, namespace="test", uid=uid,
        labels={"cce.biosan.cn/run-id": "synthetic-run"}),
        status=dict(active=0, conditions=[dict(type=state, status="True")]))


def pod(name, uid, owner, code=1):
    job_name = name.removesuffix("-pod")
    return dict(kind="Pod", metadata=dict(name=name, namespace="test", uid=uid,
        labels={"cce.biosan.cn/run-id": "synthetic-run", "job-name": job_name},
        ownerReferences=[dict(kind="Job", name=job_name, uid=owner, controller=True)]),
        spec=dict(containers=[dict(name="main")]),
        status=dict(phase="Failed" if code else "Succeeded",
            containerStatuses=[dict(name="main", state=dict(terminated=dict(exitCode=code)))]))


@pytest.fixture
def cluster():
    objects = {
        ("job", "master"): job("master", "master-uid"),
        ("pods", "master"): dict(kind="PodList", metadata={},
            items=[pod("master-pod", "master-pod-uid", "master-uid")]),
        ("job", "worker"): job("worker", "worker-uid", "Complete"),
        ("pods", "worker"): dict(kind="PodList", metadata={},
            items=[pod("worker-pod", "worker-pod-uid", "worker-uid", 0)]),
        ("job", "not-created"): None,
        ("pods", "not-created"): dict(kind="PodList", metadata={}, items=[]),
    }
    calls = []
    def query(config, *args, timeout):
        assert config["kubernetes"]["namespace"] == "test"
        assert 0 < timeout <= 30
        calls.append(args)
        if args == ("job", "master"):
            return deepcopy(objects["job", "master"])
        selected = args in {
            ("jobs", "-l", "cce.biosan.cn/run-id=" + runtime.run_label, "--chunk-size=0"),
            ("pods", "-l", "cce.biosan.cn/run-id=" + runtime.run_label, "--chunk-size=0")}
        assert selected or args in {("jobs", "--chunk-size=0"), ("pods", "--chunk-size=0")}
        kind = "job" if args[0] == "jobs" else "pods"
        metadata, items = {}, []
        for (entry_kind, _), value in objects.items():
            if entry_kind != kind:
                continue
            if isinstance(value, Exception):
                raise ValueError("workload query unavailable") from None
            if kind == "pods":
                if value is None:
                    return None
                if value["metadata"].get("continue"):
                    metadata["continue"] = value["metadata"]["continue"]
                entries = value["items"]
            else:
                entries = [] if value is None else [value]
            items.extend(entry for entry in entries if not selected or
                entry["metadata"].get("labels", {}).get("cce.biosan.cn/run-id") == runtime.run_label)
        return deepcopy(dict(kind="JobList" if kind == "job" else "PodList",
            metadata=metadata, items=items))
    runtime = SimpleNamespace(_recovery_query=query, run_label="synthetic-run")
    return objects, calls, runtime


def probe(cluster, **override):
    module = importlib.import_module("scripts.cce_recovery_workloads")
    kwargs = dict(runtime=cluster[2], config={"kubernetes": {"namespace": "test"}},
        namespace="test", run_label="synthetic-run", master_job="master", master_job_uid="master-uid",
        master_pod_uid="master-pod-uid",
        workers=[dict(name="worker", uid="worker-uid"), dict(name="not-created", uid=None)])
    kwargs.update(override)
    return module.probe_bound_workloads(**kwargs)


def test_exact_terminal_objects_return_observations_not_recovery_authority(cluster):
    result = probe(cluster)
    assert result["master_job_uid"] == "master-uid"
    assert result["master_pod_uid"] == "master-pod-uid"
    assert result["master_container_exit_codes"] == {"main": 1}
    assert result["workers"] == [dict(name="worker", uid="worker-uid", job_state="Complete", pods=1),
                                 dict(name="not-created", uid=None, job_state="absent", pods=0)]
    assert not ({"sealed", "complete", "automatic_recovery_allowed", "worker_inventory_complete"} & result.keys())
    assert len(cluster[1]) == 5


@pytest.mark.parametrize("change", ["master_uid", "pod_uid", "pod_owner", "master_active",
    "master_succeeded", "master_missing", "master_pod_missing", "pod_running", "sidecar_running",
    "worker_uid", "worker_active", "orphan_pod", "terminating_pod", "unknown_pod_owner",
    "missing_pod_status", "empty_list_output", "paged_list", "unexpected_worker", "query_error"])
def test_uncertain_or_active_workload_never_produces_observation(cluster, change):
    objects = cluster[0]
    master = objects["job", "master"]
    master_pod = objects["pods", "master"]["items"][0]
    worker = objects["job", "worker"]
    worker_pod = objects["pods", "worker"]["items"][0]
    if change == "master_uid": master["metadata"]["uid"] = "replacement"
    elif change == "pod_uid": master_pod["metadata"]["uid"] = "replacement"
    elif change == "pod_owner": master_pod["metadata"]["ownerReferences"][0]["uid"] = "foreign"
    elif change == "master_active": master["status"]["active"] = 1
    elif change == "master_succeeded": master["status"]["conditions"][0]["type"] = "Complete"
    elif change == "master_missing": objects["job", "master"] = None
    elif change == "master_pod_missing": objects["pods", "master"]["items"] = []
    elif change == "pod_running": master_pod["status"]["phase"] = "Running"
    elif change == "sidecar_running":
        master_pod["spec"]["containers"].append(dict(name="sidecar"))
        master_pod["status"]["containerStatuses"].append(dict(name="sidecar", state=dict(running={})))
    elif change == "worker_uid": worker["metadata"]["uid"] = "replacement"
    elif change == "worker_active": worker["status"]["active"] = 1
    elif change == "orphan_pod":
        objects["job", "worker"] = None
        worker_pod["status"]["phase"] = "Running"
    elif change == "terminating_pod": worker_pod["metadata"]["deletionTimestamp"] = "synthetic"
    elif change == "unknown_pod_owner": worker_pod["metadata"]["ownerReferences"] = []
    elif change == "missing_pod_status": worker_pod["status"]["containerStatuses"] = []
    elif change == "empty_list_output": objects["pods", "worker"] = None
    elif change == "paged_list": objects["pods", "worker"]["metadata"]["continue"] = "next"
    elif change == "unexpected_worker": objects["job", "not-created"] = job("not-created", "unknown")
    else: objects["job", "worker"] = TimeoutError("private details must not escape")
    with pytest.raises(ValueError) as error:
        probe(cluster)
    assert "private details" not in str(error.value)


def test_absent_job_still_checks_uid_bound_residual_pods(cluster):
    cluster[0]["job", "worker"] = None
    result = probe(cluster)
    assert result["workers"][0] == dict(name="worker", uid="worker-uid", job_state="absent", pods=1)


@pytest.mark.parametrize("override", [dict(namespace="other"), dict(master_job="../master"),
    dict(workers=[dict(name="worker", uid="worker-uid"), dict(name="worker", uid="other")]),
    dict(workers=[dict(name="master", uid="master-uid")])])
def test_invalid_frozen_binding_is_rejected_before_queries(cluster, override):
    with pytest.raises(ValueError):
        probe(cluster, **deepcopy(override))
    assert cluster[1] == []
