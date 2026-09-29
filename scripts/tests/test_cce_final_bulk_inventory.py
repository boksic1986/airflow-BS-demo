"""UE-03: one large synthetic inventory across the real platform consumers.

The pinned native ``_recovery_query`` parses synthetic kubectl transport bytes.
Native FINAL, lineage, storage, and lock authentication have other fixtures.
"""

import copy
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from cce_pipeline.assets import cce_batch_runtime as native
from scripts import cce_paired_runtime as paired
from scripts import cce_recovery_failure as failure
from scripts import cce_recovery_inventory as inventory
from scripts import cce_recovery_workloads as workloads


class _Cluster:
    namespace = "synthetic-ns"
    run_label = "synthetic-run"
    master_name = "master"
    master_uid = "master-uid"

    def __init__(self):
        self.calls = []
        self.config = {"kubernetes": {"kubectl_bin": "kubectl",
            "kubeconfig": "synthetic-kubeconfig", "namespace": self.namespace}}
        self.master = None  # TTL reclamation: persisted FINAL remains authoritative.
        self.workers = [dict(name=f"worker-{number}", uid=f"worker-uid-{number}",
            namespace=self.namespace, terminal_state="SUCCEEDED") for number in range(275)]
        self.active_worker = False
        self.active_on_namespace_round = None
        self.foreign_owner_reference = False
        self.namespace_rounds = 0
        self.lock_mutated = False
        self.runtime = native

    def _job(self, name, uid, state, *, label=None):
        status = ({"active": 1} if state == "Active" else
            {"conditions": [{"type": state, "status": "True"}]})
        return {"kind": "Job", "metadata": {"name": name, "uid": uid,
            "namespace": self.namespace, "resourceVersion": "1",
            "labels": {"cce.biosan.cn/run-id": label or self.run_label}},
            "status": status}

    def _pod(self, name, uid, job, job_uid, *, active=False, label=None):
        status = ({"phase": "Running"} if active else {"phase": "Succeeded",
            "containerStatuses": [{"name": "worker", "state": {
                "terminated": {"exitCode": 0}}}]})
        return {"kind": "Pod", "metadata": {"name": name, "uid": uid,
            "namespace": self.namespace,
            "labels": {"cce.biosan.cn/run-id": label or self.run_label,
                       "job-name": job},
            "ownerReferences": [{"kind": "Job", "name": job, "uid": job_uid,
                                 "controller": True}]},
            "spec": {"containers": [{"name": "worker"}]}, "status": status}

    def _objects(self):
        jobs = [self.master] if self.master is not None else []
        pods = []
        if self.active_worker:
            worker = self.workers[0]
            jobs.append(self._job(worker["name"], worker["uid"], "Active"))
            pods.append(self._pod("active-worker-pod", "active-pod-uid",
                worker["name"], worker["uid"], active=True))
        # This live, unrelated batch shares the namespace but not the run ID.
        unrelated = self._job("other-batch", "other-uid", "Active", label="other-run")
        unrelated_pod = self._pod("other-pod", "other-pod-uid", "other-batch",
            "other-uid", active=True, label="other-run")
        if self.foreign_owner_reference:
            unrelated_pod["metadata"]["ownerReferences"].append({
                "kind": "Job", "name": self.workers[0]["name"],
                "uid": self.workers[0]["uid"], "controller": False})
        return jobs, pods, unrelated, unrelated_pod

    def transport(self, command, *, check, capture, timeout):
        assert command[:6] == ["kubectl", "--kubeconfig", "synthetic-kubeconfig",
                               "-n", self.namespace, "get"]
        assert check is False and capture is True
        assert timeout is not None and 0 < timeout <= 30
        assert command[-2:] == ["-o", "json"]
        exact = command[-3] == "--ignore-not-found"
        args = tuple(command[6:-3] if exact else command[6:-2])
        self.calls.append(args)
        if args == ("job", self.master_name):
            assert exact
            payload = b"" if self.master is None else json.dumps(self.master).encode("utf-8")
            return subprocess.CompletedProcess(command, 0, payload, b"")
        assert not exact
        assert args[0] in {"jobs", "pods"}, f"unexpected read-only query: {args!r}"
        if args == ("jobs", "--chunk-size=0"):
            self.namespace_rounds += 1
            if self.namespace_rounds == self.active_on_namespace_round:
                self.active_worker = True
        jobs, pods, unrelated, unrelated_pod = self._objects()
        if args in {("jobs", "--chunk-size=0"), ("pods", "--chunk-size=0")}:
            items = jobs + [unrelated] if args[0] == "jobs" else pods + [unrelated_pod]
        elif args == (args[0], "-l", f"cce.biosan.cn/run-id={self.run_label}", "--chunk-size=0"):
            items = jobs if args[0] == "jobs" else pods
        else:
            raise AssertionError(f"unexpected read-only query: {args!r}")
        payload = json.dumps({"kind": "JobList" if args[0] == "jobs" else "PodList",
            "metadata": {}, "items": items}).encode("utf-8")
        return subprocess.CompletedProcess(command, 0, payload, b"")

    def final_args(self, state):
        return dict(runtime=self.runtime, config=self.config,
            namespace=self.namespace, run_label=self.run_label,
            master_job=self.master_name, master_job_uid=self.master_uid,
            master_state=state, workers=self.workers)


def _assert_query_rounds(cluster, rounds):
    expected = {
        ("jobs", "-l", f"cce.biosan.cn/run-id={cluster.run_label}", "--chunk-size=0"),
        ("pods", "-l", f"cce.biosan.cn/run-id={cluster.run_label}", "--chunk-size=0"),
        ("jobs", "--chunk-size=0"),
        ("pods", "--chunk-size=0"),
        ("job", cluster.master_name),
    }
    assert Counter(cluster.calls) == Counter({query: rounds for query in expected})


@pytest.fixture
def cluster(monkeypatch):
    source = os.environ.get("CCE_PLUGIN_SOURCE")
    digest = os.environ.get("CCE_NATIVE_QUERY_SHA256")
    assert source, "CCE_PLUGIN_SOURCE must identify the pinned native source root"
    assert digest and re.fullmatch(r"[0-9a-f]{64}", digest), (
        "CCE_NATIVE_QUERY_SHA256 must pin the native module's SHA-256")
    root = Path(source)
    assert root.is_absolute(), "CCE_PLUGIN_SOURCE must be an absolute path"
    root = root.resolve(strict=True)
    imported = Path(native.__file__)
    assert imported.is_absolute(), "native runtime source path must be absolute"
    actual = imported.resolve(strict=True)
    expected = {root / "src" / "cce_pipeline" / "assets" / "cce_batch_runtime.py",
                root / "cce_pipeline" / "assets" / "cce_batch_runtime.py"}
    assert actual in {path.resolve(strict=True) for path in expected if path.is_file()}, (
        f"native runtime imported from unexpected source: {actual}")
    assert hashlib.sha256(actual.read_bytes()).hexdigest() == digest, (
        f"native runtime source SHA-256 differs: {actual}")
    value = _Cluster()
    monkeypatch.setattr(native, "_run", value.transport)
    return value


def _failed_final(cluster, selected):
    platform = {"pipeline": "wgs", "analysis_id": "synthetic-analysis",
        "attempt": 1, "stage": "step3_monitor", "execution_id": "platform-exec",
        "generation": 8, "request_hash": "b" * 64}
    native = {"namespace": cluster.namespace, "job_name": cluster.master_name,
        "job_uid": cluster.master_uid}
    context = {"schema": "snakemake.kubernetes.submit-context.v1",
        "pipeline": "wgs", "analysis_id": "synthetic-analysis"}
    zero = {"submission": 0, "control": 0, "rule": 0, "other": 0}
    audit = lambda counts: {"schema": "cce.master-failure-summary.v1",
        "context": context, "closed": True, "complete": True,
        "workflow_started": 1, "counts": counts,
        "shutdown": {"scheduler": 0, "workflow": 0}}
    candidate = {"failures": [{"category": "WORKER_CREATE_ADMISSION_TIMEOUT"}]}
    phases = {"preflight": {"started": True, "context": context,
        "failure_summary": audit(zero), "exit_code": 0, "candidates": {}},
        "analysis": {"started": True, "context": context,
        "failure_summary": audit({**zero, "submission": 1}),
        "exit_code": 1, "candidates": {"executor-failure.json": candidate}}}
    terminal = {"state": "FAILED", "submission_inventory_complete": True,
        "platform_execution": platform, "failed_stage": "analysis", "exit_code": 1,
        "submission_snapshot_sha256": "a" * 64}
    result = {"terminal": terminal,
        "snapshot": {"master": {**native, "platform_execution": platform}, "phases": phases}}
    binding = {"schema_version": 2, "selected_bundle": str(selected),
        "platform_execution": platform, "native": native}
    return result, binding


def _collect_failed(cluster, monkeypatch, selected):
    result, binding = _failed_final(cluster, selected)
    monkeypatch.setattr(native, "_recovery_final_evidence",
                        lambda *args: copy.deepcopy(result))
    monkeypatch.setattr(failure, "lineage_workers", lambda *args: cluster.workers)
    return failure.collect_failure_evidence(runtime=cluster.runtime, selected=selected,
        contract={"kubernetes": {"namespace": cluster.namespace}},
        config=cluster.config,
        run_label=cluster.run_label, binding=binding)


def _capability(cluster, monkeypatch, terminal, tmp_path):
    cap = inventory.RecoveryCapability.__new__(inventory.RecoveryCapability)
    cap.runtime = cluster.runtime
    cap.contract = {"kubernetes": {"namespace": cluster.namespace,
        "master_job": cluster.master_name}}
    cap.config = cluster.config
    cap.run_label = cluster.run_label
    cap.expected_job_uid = cluster.master_uid
    cap.bundle = tmp_path
    cap.history_bundles = ()
    cap.context = {"pipeline": "wgs", "analysis_id": "synthetic-analysis"}
    cap._lock_context = {"master_uid": ""}
    cap.compute_deadline = None
    native_terminal = dict(terminal)
    native_terminal.setdefault("state", str(terminal.get("master_state", "FAILED")).upper())
    cap._authorized = lambda: {"terminal": native_terminal, "snapshot": {}}
    cap.verify_lock = lambda *args: {"object_uid": "lock-uid", "resource_version": "1"}
    monkeypatch.setattr(inventory, "lineage_workers", lambda *args: cluster.workers)
    return cap


def _release_registered_final(cluster, monkeypatch, tmp_path, *, missing_lock=False):
    selected = tmp_path / "selected"
    monkeypatch.setattr(paired, "_registered_request",
        lambda payload, gate, pipeline: (tmp_path / "step6_materialize.json", b"registered"))
    monkeypatch.setattr(paired, "_read_registered", lambda path: b"registered")
    monkeypatch.setattr(paired, "_exclusive", lambda path: nullcontext())
    monkeypatch.setattr(paired, "_inactive_dispatcher", lambda *args: None)
    monkeypatch.setattr(paired, "_source_history", lambda *args: ())
    monkeypatch.setattr(inventory, "lineage_workers", lambda *args: cluster.workers)
    writer = SimpleNamespace(context={}, validate=lambda: None,
                             journal={}, save_journal=lambda value: None)
    checks = Counter()
    def materialized(*args):
        checks["materialized_checks"] += 1
    monkeypatch.setattr(native, "_require_materialized", materialized)
    monkeypatch.setattr(native, "_recovery_final_evidence", lambda *args: {
        "terminal": {"state": "SUCCEEDED", "submission_snapshot_sha256": "c" * 64},
        "snapshot": {}})
    monkeypatch.setattr(native, "_directory_lock_identity", lambda *args:
        ("lock", {"run": "synthetic"}, {"master_uid": cluster.master_uid}))
    def release(*args, verify, release_query_deadline=None, **kwargs):
        checks["release_calls"] += 1
        assert release_query_deadline is not None
        if missing_lock:
            raise RuntimeError("directory lock missing; release outcome unknown")
        proof = verify({"metadata": {"uid": "lock-uid", "resourceVersion": "1"}}, "release")
        assert proof["evidence_sha256"] == "c" * 64
        checks["verified_release_proofs"] += 1
        cluster.lock_mutated = True
    monkeypatch.setattr(native, "_release_batch_lock", release)
    gate = SimpleNamespace(_request_path=lambda analysis_id, attempt, stage:
        tmp_path / f"{stage}.json")
    paired._release_registered_writer(
        {"analysis_id": "synthetic-analysis", "attempt": 1},
        {"run_label": cluster.run_label}, gate, "wgs", cluster.runtime, tmp_path,
        selected, cluster.master_uid,
        {"identity": {}, "kubernetes": {"namespace": cluster.namespace,
                           "master_job": cluster.master_name}},
        cluster.config, writer)
    return checks


def test_reclaimed_inventory_consumers_share_bounded_queries(cluster, monkeypatch, tmp_path):
    """275 reclaimed Workers cost one fixed inventory round per consumer."""
    selected = tmp_path / "selected"
    failure_proof = _collect_failed(cluster, monkeypatch, selected)
    assert failure_proof["terminal"]["active_worker_jobs"] == 0
    assert failure_proof["terminal"]["active_worker_pods"] == 0
    _assert_query_rounds(cluster, 1)
    assert cluster.namespace_rounds == 1

    cluster.calls.clear()
    cap = _capability(cluster, monkeypatch, failure_proof["terminal"], tmp_path)
    assert cap.inspect()["observation"]["workers_inactive"] is True
    _assert_query_rounds(cluster, 1)

    cluster.calls.clear()
    checks = _release_registered_final(cluster, monkeypatch, tmp_path)
    assert cluster.lock_mutated is True
    assert checks == Counter(materialized_checks=2, release_calls=1, verified_release_proofs=1)
    _assert_query_rounds(cluster, 2)  # Pre-release and fresh release-CAS rounds.


@pytest.mark.parametrize("outcome", ["reconnect", "budget", "missing_lock"])
def test_final_release_reconnect_does_not_repeat_materialization_or_cas(
        cluster, monkeypatch, tmp_path, outcome):
    """A typed CAS-proof read retry shares the original preflight deadline."""
    clock = {"now": 0.0}
    if outcome != "missing_lock":
        real_transport = cluster.transport
        attempts = Counter()
        def transport(command, *, check, capture, timeout):
            query = tuple(command[6:-3] if command[-3] == "--ignore-not-found"
                          else command[6:-2])
            if query == ("jobs", "-l", f"cce.biosan.cn/run-id={cluster.run_label}", "--chunk-size=0"):
                attempts["labelled_jobs"] += 1
                if attempts["labelled_jobs"] == 2:
                    if outcome == "budget":
                        clock["now"] = 121
                    return subprocess.CompletedProcess(command, 1, b"", b"connection reset by peer")
            value = real_transport(command, check=check, capture=capture, timeout=timeout)
            if outcome == "budget" and query == ("job", cluster.master_name):
                clock["now"] = 100  # Preflight consumed the shared window.
            return value
        monkeypatch.setattr(native, "_run", transport)
    if outcome == "budget":
        fake_time = SimpleNamespace(monotonic=lambda: clock["now"], time=lambda: 1000 + clock["now"],
                                    sleep=lambda seconds: clock.__setitem__("now", clock["now"] + seconds))
        monkeypatch.setattr(paired, "time", fake_time)
        monkeypatch.setattr(workloads, "time", fake_time)
    if outcome == "reconnect":
        checks = _release_registered_final(cluster, monkeypatch, tmp_path)
        assert attempts["labelled_jobs"] == 3  # Preflight, CAS transient, fresh CAS read.
        assert checks == Counter(materialized_checks=2, release_calls=1, verified_release_proofs=1)
        assert cluster.lock_mutated is True
        _assert_query_rounds(cluster, 2)
    else:
        with pytest.raises((ValueError, RuntimeError), match=(
                "budget exhausted" if outcome == "budget" else "lock missing")):
            _release_registered_final(cluster, monkeypatch, tmp_path,
                                      missing_lock=outcome == "missing_lock")
        assert cluster.lock_mutated is False


def test_active_bulk_observation_cannot_authorize_replacement(cluster, monkeypatch, tmp_path):
    cluster.master = cluster._job(cluster.master_name, cluster.master_uid, "Failed")
    cluster.active_worker = True
    cluster.workers[0]["terminal_state"] = None
    proof = _collect_failed(cluster, monkeypatch, tmp_path / "selected")
    assert proof["terminal"]["active_worker_jobs"] == 1
    assert proof["terminal"]["active_worker_pods"] == 1
    _assert_query_rounds(cluster, 1)
    cap = _capability(cluster, monkeypatch, proof["terminal"], tmp_path)
    with pytest.raises(ValueError):
        cap.inspect()
    cluster.active_worker = False
    cluster.workers[0]["terminal_state"] = "SUCCEEDED"
    cluster.calls.clear()
    renewed = _collect_failed(cluster, monkeypatch, tmp_path / "selected")
    assert renewed["terminal"]["active_worker_jobs"] == 0
    assert renewed["terminal"]["active_worker_pods"] == 0
    _assert_query_rounds(cluster, 1)

    # A namespace Pod with a foreign label still conflicts if any ownerRef
    # claims a bound Worker, even when that reference is not its controller.
    cluster.foreign_owner_reference = True
    cluster.calls.clear()
    with pytest.raises(ValueError, match="unbound or conflicting live Pod"):
        _collect_failed(cluster, monkeypatch, tmp_path / "selected")
    _assert_query_rounds(cluster, 1)


def test_inventory_is_refreshed_at_cas(cluster, monkeypatch, tmp_path):
    """A worker appearing after preflight cannot inherit its stale proof."""
    cap = _capability(cluster, monkeypatch,
        {"state": "FAILED", "submission_snapshot_sha256": "a" * 64}, tmp_path)
    cluster.active_on_namespace_round = 2
    def claim(*args, verify, **kwargs):
        verify({"metadata": {"uid": "lock-uid", "resourceVersion": "1"}}, "takeover")
        cluster.lock_mutated = True
    monkeypatch.setattr(native, "_claim_batch_lock", claim)
    with pytest.raises(ValueError):
        cap.claim({}, lambda value: None)
    assert cluster.namespace_rounds == 2
    _assert_query_rounds(cluster, 2)
    assert cluster.lock_mutated is False
