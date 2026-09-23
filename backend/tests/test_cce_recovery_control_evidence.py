"""Agreed control-candidate contract; terminal scaffolding is synthetic only."""
import json

import pytest

from test_cce_recovery_evidence import digest, evidence, validate
from test_cce_recovery_reader import read


@pytest.fixture
def control(evidence):
    _, candidate, terminal = evidence
    candidate["schema"] = "snakemake.kubernetes.executor-control-failure.v1"
    candidate["failures"] = [dict(category="HEAVY_SLOT_API_UNAVAILABLE",
        phase="heavy_slot_refresh", operation="read_namespaced_lease",
        resource_kind="Lease", resource_name="synthetic-lease", label_selector=None,
        worker_name="synthetic-worker", worker_uid=None,
        transient_reason="CONNECTION_REFUSED", operation_attempts=3,
        retry_scope="same_operation", retryable=True, exhausted=True,
        creation_state="UNKNOWN")]
    terminal["fatal_source"] = "executor_control"
    terminal["plugin_failure_sha256"] = digest(candidate)
    return evidence


@pytest.mark.parametrize("operation", ["read_namespaced_lease", "list_namespaced_pod"])
def test_bound_control_failure_requires_separate_complete_terminal(control, operation):
    candidate, terminal = control[1:]
    if operation == "list_namespaced_pod":
        candidate["failures"][0].update(operation=operation, resource_kind="Pod",
            resource_name=None, label_selector="job-name=synthetic-worker")
    terminal["plugin_failure_sha256"] = digest(candidate)
    assert validate(control)["category"] == "heavy_slot_api_unavailable"
    terminal["active_worker_jobs"] = 1
    with pytest.raises(ValueError):
        validate(control)
    terminal["active_worker_jobs"] = 0
    terminal["worker_inventory_complete"] = False
    with pytest.raises(ValueError):
        validate(control)


@pytest.mark.parametrize("change", [
    {"operation": "replace_namespaced_lease"}, {"transient_reason": "HTTP_500"},
    {"operation_attempts": True}, {"operation_attempts": 4},
    {"label_selector": "job-name=another-worker"}, {"retry_scope": "new_operation"},
    {"creation_state": "ABSENT"}, {"worker_name": "../worker"},
])
def test_control_candidate_cannot_widen_read_retry_contract(control, change):
    control[1]["failures"][0].update(change)
    control[2]["plugin_failure_sha256"] = digest(control[1])
    with pytest.raises(ValueError):
        validate(control)


def test_control_file_is_selected_only_when_single_stable_candidate(tmp_path, control, monkeypatch):
    from app import cce_recovery_reader as reader
    root = tmp_path / "controlled"
    scope = root / "execution-one"
    scope.mkdir(parents=True)
    candidate_file = scope / "executor-control-failure.json"
    candidate_file.write_text(json.dumps(control[1]))
    (scope / "master-terminal.json").write_text(json.dumps(control[2]))
    saved = root, scope, control[0]
    assert read(saved)["category"] == "heavy_slot_api_unavailable"
    other = scope / "executor-failure.json"
    other.write_text("{}")
    with pytest.raises(ValueError):
        read(saved)
    other.unlink()
    original = reader._read
    def concurrent_candidate(fd, name):
        result = original(fd, name)
        if name == "master-terminal.json":
            other.write_text("{}")
        return result
    monkeypatch.setattr(reader, "_read", concurrent_candidate)
    with pytest.raises(ValueError):
        read(saved)


def test_control_schema_cannot_masquerade_as_submission_file(tmp_path, control):
    root = tmp_path / "controlled"
    scope = root / "execution-one"
    scope.mkdir(parents=True)
    (scope / "executor-failure.json").write_text(json.dumps(control[1]))
    (scope / "master-terminal.json").write_text(json.dumps(control[2]))
    with pytest.raises(ValueError):
        read((root, scope, control[0]))
