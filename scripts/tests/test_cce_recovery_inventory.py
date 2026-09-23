"""Complete current-context submission inventory; synthetic records only."""
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path

import pytest
from scripts.tests.test_cce_recovery_workloads import cluster, job, pod


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def journal(records):
    lines = [encode(row) for row in records]
    digest = hashlib.sha256(b"").hexdigest()
    for line in lines:
        digest = hashlib.sha256(digest.encode() + line).hexdigest()
    raw = b"".join(lines)
    return raw, encode(dict(bytes=len(raw), records=len(lines), sha256=digest))


@pytest.fixture
def inputs():
    context = dict(schema="snakemake.kubernetes.submit-context.v1", pipeline="wgs",
        analysis_id="synthetic-analysis", attempt="1", execution_id="synthetic-submit",
        generation=1, request_hash="a" * 64, run_id="synthetic-run", namespace="test",
        master_job_uid="master-uid", master_pod_uid="master-pod-uid")
    rows = []
    for name, admitted in [("admitted", True), ("rejected", False)]:
        common = dict(context, schema="snakemake.kubernetes.submit-event.v1",
            worker_name=name, worker_uid=None, job_attempt=1,
            spec_sha256="b" * 64, submission_token=("c" if admitted else "d") * 64)
        rows.append(dict(common, event="INTENT", request_count=0))
        for count in range(1, 2 if admitted else 4):
            rows.append(dict(common, event="CREATE_REQUESTED", request_count=count))
        rows.append(dict(common, event="CREATED" if admitted else "FAILED",
            request_count=1 if admitted else 3, worker_uid="admitted-uid" if admitted else None))
    failure = dict(context, schema="snakemake.kubernetes.executor-failure.v1",
        automatic_recovery_allowed=False, requires_master_terminal=True,
        failures=[dict(worker_name="rejected", worker_uid=None,
            category="WORKER_CREATE_ADMISSION_TIMEOUT", creation_state="ABSENT",
            request_count=3, retryable=True, exhausted=True)])
    manifest = [dict(schema_version=2, external_jobid="admitted", kubernetes_uid="admitted-uid",
        attempt=1, workload_kind="rule", rule_names=["synthetic_rule"], submitted_epoch=1)]
    return context, rows, failure, manifest


def parse(inputs, **overrides):
    context, rows, failure, manifest = inputs
    raw, checkpoint = journal(rows)
    kwargs = dict(expected_context=context, journal_bytes=raw, checkpoint_bytes=checkpoint,
        candidate_bytes=encode(failure), manifest_bytes=b"".join(encode(row) for row in manifest))
    kwargs.update(overrides)
    return importlib.import_module("scripts.cce_recovery_inventory").validate_submission_inventory(**kwargs)


def test_all_intents_and_admitted_manifest_form_one_uid_bound_inventory(inputs):
    result = parse(inputs)
    assert result["workers"] == [dict(name="admitted", uid="admitted-uid"), dict(name="rejected", uid=None)]
    assert result["executor_failure_count"] == 1
    assert result["journal_sha256"] == hashlib.sha256(journal(inputs[1])[0]).hexdigest()
    assert "sealed" not in result and "automatic_recovery_allowed" not in result


@pytest.mark.parametrize("change", ["truncated", "checkpoint", "foreign_context", "repeated_intent",
    "unresolved", "request_jump", "changed_token", "changed_uid", "failure_missing", "failure_extra",
    "failure_count", "unknown_outcome", "rule_failure_category", "manifest_missing", "manifest_extra",
    "manifest_uid", "manifest_attempt", "manifest_partial", "duplicate_key", "created_without_request"])
def test_missing_changed_or_unresolved_inventory_fails_closed(inputs, change):
    context, rows, failure, manifest = inputs
    kwargs = {}
    if change == "truncated": kwargs["journal_bytes"] = journal(rows)[0][:-1]
    elif change == "checkpoint": kwargs["checkpoint_bytes"] = encode(dict(bytes=0, records=0, sha256="a" * 64))
    elif change == "foreign_context": rows[1]["execution_id"] = "foreign"
    elif change == "repeated_intent": rows.append(deepcopy(rows[0]))
    elif change == "unresolved": rows.pop()
    elif change == "request_jump": rows[1]["request_count"] = 2
    elif change == "changed_token": rows[-1]["submission_token"] = "e" * 64
    elif change == "changed_uid": rows[-1]["worker_uid"] = "unexpected"
    elif change == "failure_missing": failure["failures"] = []
    elif change == "failure_extra": failure["failures"].append(deepcopy(failure["failures"][0]))
    elif change == "failure_count": failure["failures"][0]["request_count"] = 2
    elif change == "unknown_outcome": failure["failures"][0]["creation_state"] = "UNKNOWN"
    elif change == "rule_failure_category": failure["failures"][0]["category"] = "RULE_FAILED"
    elif change == "manifest_missing": manifest.clear()
    elif change == "manifest_extra": manifest.append(dict(manifest[0], external_jobid="untracked"))
    elif change == "manifest_uid": manifest[0]["kubernetes_uid"] = "foreign"
    elif change == "manifest_attempt": manifest[0]["attempt"] = 2
    elif change == "manifest_partial": kwargs["manifest_bytes"] = encode(manifest[0])[:-1]
    elif change == "duplicate_key": kwargs["checkpoint_bytes"] = b'{"bytes":0,"bytes":1}'
    else: rows.pop(1)
    with pytest.raises(ValueError):
        parse(inputs, **kwargs)


def test_adoption_uses_the_same_uid_and_complete_manifest(inputs):
    inputs[1][2]["event"] = "ADOPTED"
    assert parse(inputs)["workers"][0] == dict(name="admitted", uid="admitted-uid")


@pytest.fixture
def control_inputs(inputs):
    context, rows, candidate, manifest = inputs
    rows[:] = rows[:3]  # Successful CREATE only: control faults are not submit events.
    candidate["schema"] = "snakemake.kubernetes.executor-control-failure.v1"
    candidate["failures"] = [dict(category="HEAVY_SLOT_API_UNAVAILABLE",
        phase="heavy_slot_refresh", operation="list_namespaced_pod", resource_kind="Pod",
        resource_name=None, label_selector="job-name=admitted", worker_name="admitted",
        worker_uid="admitted-uid", transient_reason="CONNECTION_REFUSED",
        operation_attempts=3, retry_scope="same_operation", retryable=True,
        exhausted=True, creation_state="UNKNOWN")]
    return inputs


@pytest.mark.parametrize("uid", [None, "admitted-uid"])
def test_control_candidate_keeps_admitted_uid_without_fabricating_submit_failure(control_inputs, uid):
    control_inputs[2]["failures"][0]["worker_uid"] = uid
    result = parse(control_inputs)
    assert result["workers"] == [dict(name="admitted", uid="admitted-uid")]
    assert result["executor_failure_count"] == 1
    assert [row["event"] for row in control_inputs[1]] == ["INTENT", "CREATE_REQUESTED", "CREATED"]


@pytest.mark.parametrize("change", ["foreign_uid", "unknown_worker", "missing_manifest",
    "unresolved", "mixed_submit_failure", "namespace_scan", "write", "wrong_kind"])
def test_control_candidate_cannot_skip_inventory_or_expand_query(control_inputs, change):
    _, rows, candidate, manifest = control_inputs
    fault = candidate["failures"][0]
    if change == "foreign_uid": fault["worker_uid"] = "other-uid"
    elif change == "unknown_worker": fault["worker_name"] = "untracked"
    elif change == "missing_manifest": manifest.clear()
    elif change == "unresolved": rows.pop()
    elif change == "mixed_submit_failure": rows.append(dict(rows[-1], event="FAILED"))
    elif change == "namespace_scan": fault["label_selector"] = None
    elif change == "write": fault["operation"] = "replace_namespaced_lease"
    else: fault["resource_kind"] = "Lease"
    with pytest.raises(ValueError):
        parse(control_inputs)


@pytest.mark.parametrize("active", [False, True])
def test_validated_inventory_drives_every_exact_worker_query(inputs, cluster, active):
    objects, calls, runtime = cluster
    objects["job", "admitted"] = job("admitted", "admitted-uid", "Complete")
    objects["pods", "admitted"] = dict(kind="PodList", metadata={},
        items=[pod("admitted-pod", "admitted-pod-uid", "admitted-uid", 0)])
    objects["job", "rejected"] = None
    objects["pods", "rejected"] = dict(kind="PodList", metadata={}, items=[])
    if active:
        objects["job", "admitted"]["status"]["active"] = 1
    context, rows, failure, manifest = inputs
    raw, checkpoint = journal(rows)
    module = importlib.import_module("scripts.cce_recovery_inventory")
    kwargs = dict(runtime=runtime, config={"kubernetes": {"namespace": "test"}},
        master_job="master", expected_context=context, journal_bytes=raw,
        checkpoint_bytes=checkpoint, candidate_bytes=encode(failure),
        manifest_bytes=b"".join(encode(row) for row in manifest))
    if active:
        with pytest.raises(ValueError):
            module.probe_submission_inventory(**kwargs)
    else:
        result = module.probe_submission_inventory(**kwargs)
        assert result["observation"]["workers"] == [
            dict(name="admitted", uid="admitted-uid", job_state="Complete", pods=1),
            dict(name="rejected", uid=None, job_state="absent", pods=0)]
        assert len(calls) == 6


@pytest.mark.parametrize("pipeline", ["wgs", "gatk"])
def test_actual_bs5_compatible_producer_journal(pipeline):
    root = os.environ.get("CCE_PRODUCER_FIXTURE_ROOT")
    if not root:
        pytest.skip("requires external producer fixture, not a fabricated positive sample")
    scope = Path(root) / (pipeline + "-admission")
    context = json.loads((scope / "submit-context.json").read_bytes())
    module = importlib.import_module("scripts.cce_recovery_inventory")
    result = module.validate_submission_inventory(expected_context=context,
        journal_bytes=(scope / "submit-events.ndjson").read_bytes(),
        checkpoint_bytes=(scope / "journal-state.json").read_bytes(),
        candidate_bytes=(scope / "executor-failure.json").read_bytes(), manifest_bytes=b"")
    assert result["workers"] == [dict(name="snakejob-synthetic-" + pipeline, uid=None)]
