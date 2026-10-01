"""UE-05 thin DAG bridge; backend fixtures prove the actual permit fences."""
import importlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class NativeCallbackObservationTests(unittest.TestCase):
    def setattr(self, target, name, value, raising=True):
        patched = patch.object(target, name, value, create=not raising)
        patched.start()
        self.addCleanup(patched.stop)

    def test_wgs_current_dag_native_callback_channel(self):
        _callback_case(self, "wgs")

    def test_gatk_current_dag_native_callback_channel(self):
        _callback_case(self, "gatk")


def _callback_case(monkeypatch, pipeline):
    module = importlib.import_module("bio_" + pipeline)
    aid = ("WGS" if pipeline == "wgs" else "GATK") + "_20260930_010203_A1B2C3"
    conf = dict(analysis_id=aid, pipeline=pipeline, attempt=1, execution_mode="cce", params={})
    tasks = [SimpleNamespace(task_id="wait_step3_analysis", state="success"),
             SimpleNamespace(task_id="wait_step4_publish", state="failed"),
             SimpleNamespace(task_id="wait_step6_materialize", state="skipped")]
    dag_run = SimpleNamespace(conf=conf, run_id="current-dag", get_task_instances=lambda: tasks)
    context = dict(dag_run=dag_run)
    posts, observations = [], []
    state = "failed"

    def api(path, **kwargs):
        if "/stage-status?" in path:
            stage = parse_qs(urlparse(path).query)["stage"][0]
            return dict(analysis_id=aid, attempt=1, stage=stage, generation=2,
                        execution_id="current-" + stage, request_hash="a" * 64,
                        stage_execution={"protocol": "cce.stage-execution.v1"})
        posts.append((path, kwargs["payload"]))
        return dict(released=True, lifecycle_status="draining")

    def observe(request_conf, stage, identity):
        assert request_conf == conf and identity["stage"] == stage
        assert identity["execution_id"] == "current-" + stage
        snapshot = dict(schema="cce.stage-execution.snapshot.v1",
            execution_ref=dict(protocol="cce.stage-execution.v1", pipeline=pipeline,
                analysis_id=aid, attempt=1, stage=stage, execution_id=identity["execution_id"],
                stage_generation=2, request_hash="a" * 64, registration_sha256="b" * 64),
            state=state if stage == "step4_publish" else "succeeded",
            evidence_ref="c" * 64, runtime_identity=None, compute_identity=None,
            observation_health="degraded" if state == "unknown" else "healthy")
        observations.append(snapshot)
        return snapshot

    monkeypatch.setattr(module, "_backend_json", api)
    monkeypatch.setattr(module, "_native_observe_stage", observe)
    monkeypatch.setattr(module, "_require_runtime_enabled", lambda: None, raising=False)
    monkeypatch.setattr(module, "_runtime_enabled", lambda: True, raising=False)
    module.report_dag_failure(context)
    assert posts[-1][1]["native_stage_observation"] == observations[-1]
    assert observations[-1]["execution_ref"]["stage"] == "step4_publish"
    assert "worker_observation" not in posts[-1][1]
    # Unknown remains evidence for backend rejection, never a fabricated failed ref.
    state = "unknown"
    module.report_dag_failure(context)
    assert posts[-1][1]["native_stage_observation"]["state"] == "unknown"
    if pipeline == "wgs":
        module.register_stage("release_result_transfer_slot", **context)
    else:
        module.release_stage("release_result_transfer_slot", **context)
    assert posts[-1][1]["native_stage_observation"]["execution_ref"]["stage"] == "step5_download"
    module.release_leases(**context)
    release = next(payload for path, payload in reversed(posts) if path.endswith("/stages/release_leases"))
    assert release["native_stage_observation"]["execution_ref"]["stage"] == "step4_publish"
    if pipeline == "wgs":
        assert posts[-1][1]["native_stage_observation"]["execution_ref"]["stage"] == "step3_monitor"

    # The existing Worker challenge is a second request with its own nonce proof.
    worker = importlib.import_module("cce_worker_wait")
    challenge = dict(nonce="d" * 32, execution_id="monitor", generation=2, request_hash="a" * 64)
    proof = dict(challenge, cce_recovery_evidence={"synthetic": "backend validates this proof"})
    poll_posts = []

    def poll_api(path, **kwargs):
        poll_posts.append(kwargs["payload"])
        if len(poll_posts) == 1:
            return dict(status="waiting", worker_probe=challenge,
                worker_wait_deadline=(datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat())
        return dict(status="delegated")

    monkeypatch.setattr(worker, "run_ssh", lambda *args, **kwargs:
        SimpleNamespace(returncode=0, stdout=json.dumps(proof), stderr=""))
    worker.poll_recovery(poll_api, pipeline=pipeline, conf=conf, dag_run_id="current-dag",
                         native_stage_observation=observations[-1])
    assert poll_posts[0]["native_stage_observation"] == observations[-1]
    assert "worker_observation" not in poll_posts[0]
    assert poll_posts[1]["worker_observation"] == proof
    assert "native_stage_observation" not in poll_posts[1]
