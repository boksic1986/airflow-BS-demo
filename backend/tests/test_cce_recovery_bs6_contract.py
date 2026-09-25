"""Actual bs6 candidate bytes; synthetic terminal is contract scaffolding only.

These checks cannot authorize recovery or establish complete Master history.
Fixtures are produced externally from the hash-pinned wheel without networking.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

from app.cce_recovery_evidence import validate_recovery_evidence
from scripts.cce_recovery_inventory import validate_submission_inventory


WHEEL_SHA256 = "f9671d22ed02ec5a3edf0af861e116c0ea7dc9de816de6e07926fa869e2bb546"
# Actual wheel-generated consumer-fixtures-v1; do not regenerate pins at runtime.
MANIFEST_SHA256 = "a22a6d55de4947f0884c16c21d102222cd41c9c3f6a59159a4a9bd6c392fb038"
PROVENANCE_SHA256 = "b36fab5298a58bc8e749a82a35ccc37816ebda485a3757f91ead68afbf73ce9d"
FILES = ("context.json", "submit-events.ndjson", "journal-state.json",
         "executor-failure.json", "jobs.ndjson")


@pytest.fixture(params=["wgs-admission", "gatk-admission", "wgs-guard", "gatk-guard"])
def bs6(request):
    root = os.environ.get("CCE_BS6_FIXTURE_ROOT")
    if not root:
        pytest.skip("requires hash-pinned actual bs6 producer fixtures")
    root = Path(root)
    assert hashlib.sha256(Path("/bs6.whl").read_bytes()).hexdigest() == WHEEL_SHA256
    assert hashlib.sha256((root / "fixture-provenance.json").read_bytes()).hexdigest() == PROVENANCE_SHA256
    manifest = (root / "SHA256SUMS").read_bytes()
    assert hashlib.sha256(manifest).hexdigest() == MANIFEST_SHA256
    checksums = {}
    for line in manifest.decode("ascii").splitlines():
        digest, name = line.split("  ", 1)
        assert name not in checksums
        checksums[name] = digest
    raw = {}
    for name in FILES:
        raw[name] = (root / request.param / name).read_bytes()
        assert hashlib.sha256(raw[name]).hexdigest() == checksums[request.param + "/" + name]
    context, candidate = (json.loads(raw[name]) for name in (FILES[0], FILES[3]))
    assert context["pipeline"] == candidate["pipeline"] == request.param.split("-")[0]
    assert candidate["automatic_recovery_allowed"] is False
    assert candidate["requires_master_terminal"] is True
    assert raw[FILES[4]] == b""
    assert len(candidate["failures"]) == 1
    failure = candidate["failures"][0]
    if request.param.endswith("guard"):
        assert failure["category"] == "WORKER_SUBMIT_GUARD_FAILED"
        assert failure["creation_state"] == "UNKNOWN" and failure["retryable"] is False
    else:
        assert failure["category"] == "WORKER_CREATE_ADMISSION_TIMEOUT"
        assert failure["creation_state"] == "ABSENT" and failure["retryable"] is True
    return request.param, raw, context, candidate


def test_bs6_candidate_alone_is_not_recovery_permission(bs6):
    _, _, context, candidate = bs6
    with pytest.raises(ValueError, match="schema"):
        validate_recovery_evidence(expected_context=context, candidate=candidate, terminal=None)


def test_bs6_candidate_category_under_synthetic_terminal_contract(bs6):
    scope, _, context, candidate = bs6
    digest = hashlib.sha256(json.dumps(candidate, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    terminal = dict(context, schema="cce.master-terminal.v1", sealed=True, complete=True,
        plugin_failure_sha256=digest, worker_inventory_complete=True,
        worker_ownership_verified=True, submissions_reconciled=True,
        master_state="failed", master_pod_state="terminated", exit_code=1,
        fatal_source="executor_submission", executor_failure_count=1, rule_failure_count=0,
        other_failure_count=0, active_worker_jobs=0, active_worker_pods=0, unresolved_submissions=0)
    if scope.endswith("guard"):
        with pytest.raises(ValueError, match="allowlisted"):
            validate_recovery_evidence(expected_context=context, candidate=candidate, terminal=terminal)
    else:
        result = validate_recovery_evidence(expected_context=context, candidate=candidate, terminal=terminal)
        assert result["category"] == "worker_create_admission_timeout"
        assert result["source_execution_id"] == context["execution_id"]
        assert "automatic_recovery_allowed" not in result


def test_bs6_inventory_accepts_resolved_admission_but_not_guard_uncertainty(bs6):
    scope, raw, context, _ = bs6
    kwargs = dict(expected_context=context, journal_bytes=raw[FILES[1]],
        checkpoint_bytes=raw[FILES[2]], candidate_bytes=raw[FILES[3]], manifest_bytes=raw[FILES[4]])
    if scope.endswith("guard"):
        with pytest.raises(ValueError, match="inventory"):
            validate_submission_inventory(**kwargs)
    else:
        result = validate_submission_inventory(**kwargs)
        assert result["executor_failure_count"] == 1
        assert len(result["workers"]) == 1 and result["workers"][0]["uid"] is None
        assert "sealed" not in result and "automatic_recovery_allowed" not in result
