"""Compose the actual Task1 producer with Resume; Kubernetes alone is synthetic."""
import importlib.util
import copy
import json
import os
from pathlib import Path

import pytest

from scripts import wgs_resume

# The producer is a separately pinned, read-only source mount during acceptance.
if not os.environ.get("CCE_PIPELINE_SOURCE"):
    pytest.skip("requires pinned Task1 producer source", allow_module_level=True)
from cce_pipeline.assets import cce_batch_runtime as runtime
source = Path(os.environ["CCE_PIPELINE_SOURCE"])
spec = importlib.util.spec_from_file_location("p02_handoff_fixture", source / "tests/test_master_handoff.py")
producer_tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer_tests)
handoff = producer_tests.handoff


@pytest.mark.parametrize("confirm", [True, False])
def test_resume_consumes_real_confirmation_not_the_start_file(handoff, confirm):
    h = handoff
    h.exists = True
    h.confirm = confirm
    h.lose_response = True
    runtime._write_master_handoff(h.bundle, h.contract, job_name="master",
                                 job_uid="master-uid", state="JOB_CREATED")
    if confirm:
        wgs_resume._finish_handoff(runtime, h.bundle, h.contract, h.config, h.job)
        before = (h.starts, h.copies)
        wgs_resume._finish_handoff(runtime, h.bundle, h.contract, h.config, h.job)
        assert before == (h.starts, h.copies)
        assert runtime._read_master_handoff(h.bundle, h.contract)["state"] == "START_CONFIRMED"
    else:
        for _ in range(2):
            with pytest.raises(RuntimeError, match="handoff_timeout"):
                wgs_resume._finish_handoff(runtime, h.bundle, h.contract, h.config, h.job)
        record = runtime._read_master_handoff(h.bundle, h.contract)
        assert record["state"] == "START_SENT" and record["deadline_epoch"] == 1600
    assert h.starts == 1 and h.creates == 0


def test_v2_failed_master_is_blocked_before_old_evidence_or_job_is_changed(tmp_path, monkeypatch):
    # Until the next-generation recovery view is bound, Task1 must not delete
    # the old Master only to discover that the old handoff refuses its new UID.
    from scripts.tests.test_wgs_resume import frozen
    fixture = frozen.__wrapped__(tmp_path)
    bundle, binding, manifest, state, native, payload, _ = fixture
    manifest["metadata"]["annotations"] = {"cce-pipeline/handoff-version": "2"}
    import yaml
    import copy
    (bundle / "master-job.yaml").write_text(yaml.safe_dump(manifest))
    state["job"].update(copy.deepcopy(manifest))
    state["job"]["metadata"].update(uid="old-uid", resourceVersion="10")
    monkeypatch.setattr(wgs_resume, "_delete_master", lambda *a: state["deletes"].append(a))
    with pytest.raises(RuntimeError, match="recovery view"):
        wgs_resume.resume_master(payload=payload, binding=binding, runtime=native)
    assert not state["deletes"] and not state["submits"]
    assert not Path(payload["control_workdir"]).exists()


@pytest.mark.parametrize("change", [None, "old_uid", "failed_stage", "no_confirmation", "no_completion", "conflicting_failure", "malformed_failure"])
def test_native_success_requires_bound_confirmation_and_workflow_completion(handoff, monkeypatch, change):
    h = handoff
    producer_tests.launch(h)
    confirmation = copy.deepcopy(h.confirmed)
    monkeypatch.setattr(runtime, "_master_input_context", lambda: confirmation)
    terminal = runtime._bind_master_terminal({"schema_version":1, "state":"SUCCEEDED",
        "started_epoch":1000, "finished_epoch":1100,
        "exit_codes":{"preflight":0, "analysis":0, "final_dryrun":0}})
    evidence = {"START_CONFIRMED.json":confirmation, "RUN_COMPLETE.json":terminal,
        "workflow-completion.json":{"required":[{"path":"ANALYSIS_COMPLETE", "content":json.dumps({
            "schema_version":1, "status":"PASS", **h.contract["identity"]})}]}}
    if change == "old_uid": terminal["job_uid"] = "old-uid"
    elif change == "failed_stage": terminal["exit_codes"]["final_dryrun"] = 1
    elif change == "no_confirmation": evidence.pop("START_CONFIRMED.json")
    elif change == "no_completion": evidence.pop("workflow-completion.json")
    elif change in {"conflicting_failure", "malformed_failure"}: evidence["RUN_FAILED.json"] = dict(terminal, state="FAILED")
    assert runtime._write_mirror_evidence(h.bundle, "RUN", evidence, project="MOCK", batch="BATCH")
    if change == "malformed_failure":
        import hashlib
        mirror = runtime._mirror_dir(h.bundle, "RUN")
        (mirror / "RUN_FAILED.json").write_bytes(b"[]")
        marker = mirror / "MIRROR_COMPLETE.json"
        value = json.loads(marker.read_bytes())
        for entry in value["files"]:
            if entry["name"] == "RUN_FAILED.json":
                entry.update(size=2, sha256=hashlib.sha256(b"[]").hexdigest())
        marker.write_text(json.dumps(value))
    before = (h.creates, h.starts, h.copies)
    if change is None:
        result = runtime._recovery_native_success(h.bundle, h.contract, "master-uid")
        assert result["state"] == "SUCCEEDED" and result["job_uid"] == "master-uid"
    else:
        with pytest.raises(RuntimeError):
            runtime._recovery_native_success(h.bundle, h.contract, "master-uid")
    assert (h.creates, h.starts, h.copies) == before  # Reader never starts a helper Job.
