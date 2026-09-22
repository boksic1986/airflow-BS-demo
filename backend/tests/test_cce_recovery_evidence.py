"""Draft producer/wrapper contract checks, not live producer acceptance.

All identities are synthetic. The wrapper seal is a proposed runtime contract;
no current Master is assumed to emit it. Missing support must remain disabled.
"""
import hashlib
import importlib
import json

import pytest


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


@pytest.fixture(params=["wgs", "gatk"])
def evidence(request):
    identity = dict(pipeline=request.param, analysis_id="SYNTHETIC_RECOVERY", attempt="1",
        execution_id="execution-one", generation=1, request_hash="a" * 64,
        run_id="synthetic-native", namespace="synthetic", master_job_uid="master-one",
        master_pod_uid="master-pod-one")
    context = dict(identity, schema="snakemake.kubernetes.submit-context.v1")
    candidate = dict(identity, schema="snakemake.kubernetes.executor-failure.v1",
        observed_epoch=1, automatic_recovery_allowed=False, requires_master_terminal=True,
        failures=[dict(worker_name="synthetic-worker", worker_uid=None,
            category="WORKER_CREATE_ADMISSION_TIMEOUT", creation_state="ABSENT",
            request_count=3, retryable=True, exhausted=True)])
    terminal = dict(identity, schema="cce.master-terminal.v1", sealed=True, complete=True,
        plugin_failure_sha256=digest(candidate), master_state="failed",
        master_pod_state="terminated", exit_code=1, fatal_source="executor_submission",
        executor_failure_count=1, rule_failure_count=0, other_failure_count=0,
        worker_inventory_complete=True, worker_ownership_verified=True,
        submissions_reconciled=True, active_worker_jobs=0, active_worker_pods=0,
        unresolved_submissions=0)
    return context, candidate, terminal


def validate(evidence):
    context, candidate, terminal = evidence
    return importlib.import_module("app.cce_recovery_evidence").validate_recovery_evidence(
        expected_context=context, candidate=candidate, terminal=terminal)


@pytest.mark.parametrize("category", ["WORKER_CREATE_TRANSPORT", "WORKER_CREATE_ADMISSION_TIMEOUT"])
def test_only_bound_complete_quiescent_evidence_yields_candidate(evidence, category):
    context, candidate, terminal = evidence
    candidate["failures"][0]["category"] = category
    terminal["plugin_failure_sha256"] = digest(candidate)
    result = validate(evidence)
    assert result["source_execution_id"] == context["execution_id"]
    assert result["source_master_uid"] == context["master_job_uid"]
    assert result["attempt"] == 1
    assert result["evidence_sha256"] == digest(terminal)
    assert "automatic_recovery_allowed" not in result


@pytest.mark.parametrize("field,value", [
    ("sealed", False), ("complete", False), ("master_state", "running"),
    ("master_pod_state", "running"), ("exit_code", 0), ("exit_code", True),
    ("fatal_source", "rule"), ("rule_failure_count", 1), ("other_failure_count", 1),
    ("worker_inventory_complete", False), ("worker_ownership_verified", False),
    ("submissions_reconciled", False), ("active_worker_jobs", 1),
    ("active_worker_pods", 1), ("unresolved_submissions", 1),
    ("executor_failure_count", 2), ("generation", 2), ("master_job_uid", "old-master"),
])
def test_incomplete_conflicting_live_or_foreign_terminal_is_rejected(evidence, field, value):
    evidence[2][field] = value
    with pytest.raises(ValueError):
        validate(evidence)


@pytest.mark.parametrize("field,value", [
    ("category", "WORKER_CREATE_REJECTED"), ("category", "MISSING_FASTQ"),
    ("category", "WORKER_SUBMIT_GUARD_FAILED"),
    ("category", "OOM"), ("creation_state", "UNKNOWN"), ("creation_state", "CONFLICT"),
    ("retryable", False), ("exhausted", False), ("request_count", 0),
])
def test_plugin_candidate_alone_never_bypasses_terminal_contract(evidence, field, value):
    _, candidate, terminal = evidence
    candidate["failures"][0][field] = value
    terminal["plugin_failure_sha256"] = digest(candidate)
    with pytest.raises(ValueError):
        validate(evidence)


def test_changed_or_missing_evidence_cannot_be_read_as_no_rule_failure(evidence):
    evidence[1]["observed_epoch"] = 2  # same identity, changed contents after seal
    with pytest.raises(ValueError, match="digest"):
        validate(evidence)
    evidence[2]["plugin_failure_sha256"] = digest(evidence[1])
    del evidence[2]["rule_failure_count"]
    with pytest.raises(ValueError):
        validate(evidence)


def test_mixed_fatal_categories_are_rejected(evidence):
    _, candidate, terminal = evidence
    candidate["failures"].append(dict(candidate["failures"][0], category="WORKER_CREATE_TRANSPORT"))
    terminal["executor_failure_count"] = 2
    terminal["plugin_failure_sha256"] = digest(candidate)
    with pytest.raises(ValueError):
        validate(evidence)


def test_candidate_cannot_grant_recovery_itself(evidence):
    evidence[1]["automatic_recovery_allowed"] = True
    evidence[2]["plugin_failure_sha256"] = digest(evidence[1])
    with pytest.raises(ValueError):
        validate(evidence)
