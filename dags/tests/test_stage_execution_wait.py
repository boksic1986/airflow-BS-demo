"""UE-04 DAG client checks with synthetic, exact native execution snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from airflow.exceptions import AirflowFailException

from common import stage_execution
from common.stage_execution import (
    DispatchUncertain,
    StageWaitExpired,
    observe_stage,
    submit_and_await,
    submit_stage,
)


REF = {
    "protocol": "cce.stage-execution.v1",
    "pipeline": "wgs",
    "analysis_id": "WGS_20260930_010203_A1B2C3",
    "attempt": 1,
    "stage": "step2_master",
    "execution_id": "wse_1234567890abcdef12345678",
    "stage_generation": 1,
    "request_hash": "a" * 64,
    "registration_sha256": "b" * 64,
}
GATK_REF = {
    **REF, "pipeline": "gatk", "analysis_id": "GATK_SYNTHETIC",
    "stage": "step6_materialize", "execution_id": "GATK_SYNTHETIC-a1-step6_materialize-g1",
}


def snapshot(state: str, *, ref: dict | None = None) -> dict:
    return {
        "schema": "cce.stage-execution.snapshot.v1",
        "execution_ref": dict(ref or REF),
        "state": state,
        "evidence_ref": "receipt123" if state == "succeeded" else None,
        "runtime_identity": None,
        "compute_identity": None,
        "observation_health": "degraded" if state == "unknown" else "healthy",
    }


class StageExecutionWaitTests(unittest.TestCase):
    def test_migrated_dags_import_in_airflow(self) -> None:
        from airflow.models import DagBag

        root = Path(__file__).resolve().parents[1]
        for name in ("bio_wgs", "bio_gatk"):
            with self.subTest(dag=name):
                bag = DagBag(dag_folder=str(root / f"{name}.py"),
                             include_examples=False, safe_mode=False)
                self.assertEqual({}, bag.import_errors)
                self.assertIn(name, bag.dags)

    def test_lost_dispatch_reply_observes_exact_identity_without_resubmitting(self) -> None:
        calls: list[str] = []

        def dispatch(ref: dict) -> dict:
            self.assertEqual(ref, REF)
            calls.append("dispatch")
            raise DispatchUncertain("SSH reply lost")

        def observe(ref: dict) -> dict:
            self.assertEqual(ref, REF)
            calls.append("observe")
            return snapshot("running")

        result = submit_stage(
            execution_ref=REF, dispatch=dispatch, observe=observe, deadline=None
        )
        self.assertEqual(result["state"], "running")
        self.assertEqual(calls, ["dispatch", "observe"])

    def test_snapshot_identity_and_unknown_cannot_become_success(self) -> None:
        bad = {**REF, "execution_id": "wse_wrong"}
        with self.assertRaisesRegex(ValueError, "identity"):
            observe_stage(execution_ref=REF, observe=lambda _ref: snapshot("succeeded", ref=bad))
        unknown = observe_stage(execution_ref=REF, observe=lambda _ref: snapshot("unknown"))
        self.assertEqual(unknown["state"], "unknown")

    def test_native_success_can_have_nullable_evidence_reference(self) -> None:
        native_valid = snapshot("succeeded")
        native_valid["evidence_ref"] = None
        self.assertEqual(observe_stage(
            execution_ref=REF, observe=lambda _ref: native_valid,
        )["state"], "succeeded")

    def test_native_token_grammar_accepts_registered_colon_identity(self) -> None:
        colon_ref = {**REF, "execution_id": "GATK:stage1"}
        result = observe_stage(
            execution_ref=colon_ref,
            observe=lambda _ref: snapshot("accepted", ref=colon_ref),
        )
        self.assertEqual(result["state"], "accepted")

    def test_malformed_native_compute_identity_is_rejected(self) -> None:
        bad = snapshot("succeeded")
        bad["compute_identity"] = {"compute_generation": "2", "master_uid": "uid123"}
        with self.assertRaisesRegex(ValueError, "compute identity"):
            observe_stage(execution_ref=REF, observe=lambda _ref: bad)

    def test_marked_dispatch_uses_exact_native_submit_fence(self) -> None:
        import bio_gatk
        import bio_wgs

        for module, ref in ((bio_wgs, REF), (bio_gatk, GATK_REF)):
            with self.subTest(pipeline=ref["pipeline"]):
                conf = {"analysis_id": ref["analysis_id"], "attempt": ref["attempt"]}
                completed = SimpleNamespace(returncode=0, stdout=json.dumps(
                    snapshot("accepted", ref=ref)))
                with patch.object(module.subprocess, "run", return_value=completed) as runner:
                    self.assertEqual(module._native_dispatch_stage(conf, ref["stage"], ref),
                                     snapshot("accepted", ref=ref))
                command = runner.call_args.args[0]
                self.assertEqual(command[-7:], [
                    "--native-submit", ref["analysis_id"], str(ref["attempt"]),
                    ref["stage"], ref["execution_id"],
                    str(ref["stage_generation"]), ref["request_hash"],
                ])

    def test_wgs_uncertain_ssh_submit_is_sent_once(self) -> None:
        import bio_wgs

        completed = SimpleNamespace(
            returncode=255, stdout="",
            stderr="client_loop: send disconnect: Broken pipe",
        )
        conf = {"analysis_id": REF["analysis_id"], "attempt": 1}
        with patch.object(bio_wgs.subprocess, "run", return_value=completed) as runner, \
             patch.object(bio_wgs.time, "sleep", side_effect=AssertionError("submit retried")):
            with self.assertRaises(DispatchUncertain):
                bio_wgs._native_dispatch_stage(conf, REF["stage"], REF)
        self.assertEqual(runner.call_count, 1)

    def test_retry_before_first_native_submit_can_launch_exact_ref(self) -> None:
        import bio_wgs

        ref = {**REF, "stage": "step1_upload"}
        registered = {
            "analysis_id": ref["analysis_id"], "attempt": 1,
            "stage": ref["stage"], "execution_id": ref["execution_id"],
            "generation": ref["stage_generation"],
            "request_hash": ref["request_hash"],
            "stage_execution": {"protocol": ref["protocol"]},
        }
        conf = {"analysis_id": ref["analysis_id"], "attempt": 1}
        context = {
            "dag_run": SimpleNamespace(conf=conf, run_id="synthetic"),
            "ti": SimpleNamespace(try_number=2),
        }
        dispatches: list[dict] = []
        with patch.object(bio_wgs, "register_stage", return_value=registered), \
             patch.object(bio_wgs, "_native_observe_stage", return_value=snapshot("unknown", ref=ref)), \
             patch.object(bio_wgs, "_native_dispatch_stage", side_effect=lambda *_args:
                          dispatches.append(dict(registered)) or snapshot("accepted", ref=ref)):
            result = bio_wgs.run_stage_on_200("step1_upload", **context)
        self.assertEqual(result["state"], "accepted")
        self.assertEqual(len(dispatches), 1)

    def test_submit_and_await_requires_observed_success_and_keeps_one_dispatch(self) -> None:
        states = iter(("accepted", "running", "unknown", "succeeded"))
        calls: list[str] = []

        def dispatch(_ref: dict) -> dict:
            calls.append("dispatch")
            return snapshot(next(states))

        def observe(_ref: dict) -> dict:
            calls.append("observe")
            return snapshot(next(states))

        with patch.object(stage_execution.time, "sleep", return_value=None):
            result = submit_and_await(
                execution_ref=REF, dispatch=dispatch, observe=observe,
                deadline=None, poll_interval=0,
            )
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(calls, ["dispatch", "observe", "observe", "observe"])

    def test_wait_deadline_does_not_turn_unknown_into_failure(self) -> None:
        with patch.object(stage_execution.time, "time", return_value=100.0):
            with self.assertRaises(StageWaitExpired):
                submit_and_await(
                    execution_ref=REF,
                    dispatch=lambda _ref: snapshot("unknown"),
                    observe=lambda _ref: snapshot("unknown"),
                    deadline=99.0,
                    poll_interval=0,
                )

    def test_wgs_step2_wait_preserves_handshake_and_pool(self) -> None:
        import bio_wgs

        self.assertEqual(bio_wgs.dag.get_task("submit_step2_master").pool, "wgs_cce_runs")
        self.assertNotIn("wait_step2_master", {task.task_id for task in bio_wgs.dag.tasks})
        self.assertIn("submit_step2_master", bio_wgs.dag.get_task(
            "start_step3_monitor").upstream_task_ids)

        registered = {
            "analysis_id": REF["analysis_id"], "attempt": 1,
            "stage": "step2_master", "execution_id": REF["execution_id"],
            "generation": 1, "request_hash": REF["request_hash"],
            "stage_execution": {"protocol": REF["protocol"]},
        }
        conf = {"analysis_id": REF["analysis_id"], "attempt": 1}
        context = {"dag_run": SimpleNamespace(conf=conf, run_id="synthetic")}
        observations = iter((snapshot("unknown"), snapshot("running"), snapshot("succeeded")))
        dispatches: list[dict] = []

        def dispatch(*_args, **_kwargs):
            dispatches.append(dict(registered))
            return snapshot("accepted")

        with patch.object(bio_wgs, "register_stage", return_value=dict(registered)), \
             patch.object(bio_wgs, "_native_observe_stage", side_effect=lambda *_a, **_kw: next(observations)), \
             patch.object(bio_wgs, "_native_dispatch_stage", side_effect=dispatch), \
             patch.object(stage_execution.time, "sleep", return_value=None):
            result = bio_wgs.run_stage_on_200("step2_master", **context)
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(len(dispatches), 1)

    def test_wgs_step6_acceptance_does_not_finalize(self) -> None:
        import bio_wgs

        self.assertIn("wait_step6_materialize", bio_wgs.dag.get_task(
            "finalize_run").upstream_task_ids)
        self.assertIn("materialize_step6_results", bio_wgs.dag.get_task(
            "wait_step6_materialize").upstream_task_ids)
        ref = {**REF, "stage": "step6_materialize"}
        conf = {"analysis_id": ref["analysis_id"], "attempt": ref["attempt"]}
        context = {
            "dag_run": SimpleNamespace(conf=conf, run_id="synthetic"),
            "ti": SimpleNamespace(xcom_pull=lambda **_kw: snapshot("accepted", ref=ref)),
        }
        status = {
            "ready": True, "failed": False, "retry_no": 0,
            "analysis_id": ref["analysis_id"], "attempt": ref["attempt"],
            "stage": "step6_materialize",
            "stage_execution": {"protocol": ref["protocol"]},
            "execution_id": ref["execution_id"],
            "generation": ref["stage_generation"],
            "request_hash": ref["request_hash"],
        }
        with patch.object(bio_wgs, "_require_runtime_enabled"), \
             patch.object(bio_wgs, "_stage_query_json", return_value=status), \
             patch.object(bio_wgs, "_native_observe_stage", return_value=snapshot("running", ref=ref)):
            self.assertFalse(bio_wgs.stage_ready("step6_materialize", **context))
        with patch.object(bio_wgs, "_require_runtime_enabled"), \
             patch.object(bio_wgs, "_stage_query_json", side_effect=[
                 {**status, "generation": 2, "retry_no": 1},
                 status,
             ]), \
             patch.object(bio_wgs, "_native_observe_stage", return_value=snapshot("succeeded", ref=ref)):
            self.assertFalse(bio_wgs.stage_ready("step6_materialize", **context))
            self.assertTrue(bio_wgs.stage_ready("step6_materialize", **context))

    def test_wgs_marked_sensor_without_submit_xcom_observes_exact_native_ref(self) -> None:
        import bio_wgs

        ref = {**REF, "stage": "step1_upload"}
        conf = {"analysis_id": ref["analysis_id"], "attempt": ref["attempt"]}
        context = {
            "dag_run": SimpleNamespace(conf=conf, run_id="synthetic"),
            "ti": SimpleNamespace(xcom_pull=lambda **_kw: None),
        }
        status = {
            "analysis_id": ref["analysis_id"], "attempt": ref["attempt"],
            "stage": ref["stage"], "execution_id": ref["execution_id"],
            "generation": ref["stage_generation"],
            "request_hash": ref["request_hash"],
            "stage_execution": {"protocol": ref["protocol"]},
            "ready": True, "failed": False, "retry_no": 0,
        }
        with patch.object(bio_wgs, "_require_runtime_enabled"), \
             patch.object(bio_wgs, "_stage_query_json", return_value=status), \
             patch.object(bio_wgs, "_native_observe_stage", side_effect=[
                 snapshot("running", ref=ref), snapshot("succeeded", ref=ref),
             ]) as observe:
            self.assertFalse(bio_wgs.stage_ready(ref["stage"], **context))
            self.assertTrue(bio_wgs.stage_ready(ref["stage"], **context))
            self.assertEqual(observe.call_count, 2)
            self.assertTrue(all(call.args[2]["request_hash"] == ref["request_hash"]
                                for call in observe.call_args_list))

    def test_wgs_finalize_reused_step6_requires_fresh_exact_native_terminal(self) -> None:
        import bio_wgs

        ref = {**REF, "stage": "step6_materialize"}
        conf = {"analysis_id": ref["analysis_id"], "attempt": ref["attempt"],
                "params": {"orchestration_contract_version": 2}}
        context = {
            "dag_run": SimpleNamespace(conf=conf, run_id="synthetic-resume"),
            "ti": SimpleNamespace(xcom_pull=lambda **_kw: None),
        }
        current = {
            "ready": True, "status": "success", "failed": False,
            "analysis_id": ref["analysis_id"], "attempt": ref["attempt"],
            "stage": "step6_materialize",
            "stage_execution": {"protocol": ref["protocol"]},
            "execution_id": ref["execution_id"],
            "generation": ref["stage_generation"],
            "request_hash": ref["request_hash"],
        }
        with patch.object(bio_wgs, "_require_runtime_enabled"), \
             patch.object(bio_wgs, "_stage_query_json", return_value=current), \
             patch.object(bio_wgs, "_native_observe_stage", return_value=snapshot("unknown", ref=ref)), \
             patch.object(bio_wgs, "_backend_json") as backend:
            with self.assertRaisesRegex(AirflowFailException, "Step6 native terminal"):
                bio_wgs.register_stage("finalize_run", **context)
            backend.assert_not_called()
        with patch.object(bio_wgs, "_require_runtime_enabled"), \
             patch.object(bio_wgs, "_stage_query_json", return_value=current), \
             patch.object(bio_wgs, "_native_observe_stage", return_value=snapshot("succeeded", ref=ref)) as observe, \
             patch.object(bio_wgs, "_backend_json", return_value={"status": "success"}) as backend:
            bio_wgs.register_stage("finalize_run", **context)
            observe.assert_called_once()
            self.assertEqual(backend.call_args.kwargs["payload"]["worker_observation"],
                             snapshot("succeeded", ref=ref))

    def test_wgs_finalize_unmarked_v2_step6_preserves_existing_receipt_path(self) -> None:
        import bio_wgs

        conf = {"analysis_id": REF["analysis_id"], "attempt": 1,
                "params": {"orchestration_contract_version": 2}}
        context = {"dag_run": SimpleNamespace(conf=conf, run_id="synthetic-legacy"),
                   "ti": SimpleNamespace(xcom_pull=lambda **_kw: None)}
        with patch.object(bio_wgs, "_require_runtime_enabled"), \
             patch.object(bio_wgs, "_stage_query_json", return_value={
                 "stage_execution": None, "ready": True, "status": "success",
             }), \
             patch.object(bio_wgs, "_native_observe_stage",
                          side_effect=AssertionError("unmarked Step6 must not native-observe")), \
             patch.object(bio_wgs, "_backend_json", return_value={"status": "success"}) as backend:
            bio_wgs.register_stage("finalize_run", **context)
            self.assertNotIn("worker_observation", backend.call_args.kwargs["payload"])

    def test_wgs_retried_native_stage_reattaches_while_maintenance_keeps_retry_gate(self) -> None:
        import bio_wgs

        conf = {"analysis_id": REF["analysis_id"], "attempt": 1}
        dag_run = SimpleNamespace(conf=conf, run_id="synthetic")
        ti = SimpleNamespace(try_number=2)
        with patch.object(bio_wgs, "_require_runtime_enabled"), \
             patch.object(bio_wgs, "_backend_json", return_value={"status": "registered"}) as backend:
            bio_wgs.register_stage("step2_master", dag_run=dag_run, ti=ti)
            self.assertNotIn("force_new_generation", backend.call_args.kwargs["payload"])
            conf.update(maintenance_mode="repair_step4", repair_group="cram",
                        continue_after_repair=True)
            bio_wgs.register_stage("step4_publish", dag_run=dag_run, ti=ti)
            self.assertIs(backend.call_args.kwargs["payload"]["force_new_generation"], True)

    def test_wgs_opted_publish_retains_recovery_dispatch_path(self) -> None:
        import bio_wgs

        conf = {"analysis_id": REF["analysis_id"], "attempt": 1}
        dag_run = SimpleNamespace(conf=conf, run_id="synthetic")
        registered = {
            "stage_execution": {"protocol": REF["protocol"]},
            "generation": 1, "execution_id": REF["execution_id"],
        }
        with patch.object(bio_wgs, "register_stage", return_value=registered), \
             patch.object(bio_wgs, "_native_observe_stage", side_effect=AssertionError("wrong path")), \
             patch("cce_publish_dispatch.enabled", return_value=True), \
             patch("cce_publish_dispatch.start_publish", return_value={"status": "accepted"}) as publish:
            self.assertEqual(bio_wgs.run_stage_on_200("step4_publish", dag_run=dag_run),
                             {"status": "accepted"})
            publish.assert_called_once()

    def test_gatk_submit_and_sensor_share_native_snapshot(self) -> None:
        import bio_gatk

        self.assertIn("wait_step2_master", bio_gatk.dag.get_task(
            "start_step3_monitor").upstream_task_ids)
        self.assertIn("wait_step6_materialize", bio_gatk.dag.get_task(
            "finalize_run").upstream_task_ids)
        registered = {
            "analysis_id": GATK_REF["analysis_id"], "attempt": 1,
            "stage": GATK_REF["stage"], "execution_id": GATK_REF["execution_id"],
            "generation": 1, "request_hash": GATK_REF["request_hash"],
            "stage_execution": {"protocol": GATK_REF["protocol"]},
        }
        conf = {"analysis_id": GATK_REF["analysis_id"], "attempt": 1}
        dag_run = SimpleNamespace(conf=conf, run_id="synthetic")
        observed = iter((snapshot("unknown", ref=GATK_REF),
                         snapshot("unknown", ref=GATK_REF),
                         snapshot("succeeded", ref=GATK_REF)))
        dispatches: list[dict] = []
        with patch.object(bio_gatk, "register_stage", return_value=dict(registered)), \
             patch.object(bio_gatk, "_native_observe_stage", side_effect=lambda *_a, **_kw: next(observed)), \
             patch.object(bio_gatk, "_native_dispatch_stage", side_effect=lambda *_a, **_kw:
                          dispatches.append(dict(registered)) or snapshot("accepted", ref=GATK_REF)):
            submitted = bio_gatk.run_stage("step6_materialize", dag_run=dag_run)
            self.assertEqual(submitted["state"], "accepted")
            ti = SimpleNamespace(xcom_pull=lambda **_kw: submitted)
            with patch.object(bio_gatk, "_backend_json", side_effect=[
                {**registered, "status": "accepted", "ready": False, "failed": False},
                {**registered, "status": "success", "ready": True, "failed": False},
            ]):
                self.assertFalse(bio_gatk.stage_ready("step6_materialize", dag_run=dag_run, ti=ti))
                self.assertTrue(bio_gatk.stage_ready("step6_materialize", dag_run=dag_run, ti=ti))
        self.assertEqual(len(dispatches), 1)


if __name__ == "__main__":
    unittest.main()
