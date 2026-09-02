import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_wgs


class BioWgsDagTests(unittest.TestCase):
    def test_dag_exposes_single_release_agnostic_cce_orchestration(self) -> None:
        dag = bio_wgs.dag

        self.assertEqual(dag.dag_id, "bio_wgs")
        self.assertEqual(dag.max_active_runs, 4)
        self.assertTrue(dag.is_paused_upon_creation)
        self.assertEqual(
            set(dag.task_ids),
            {
                "validate_request",
                "prepare_wgs_batch",
                "input_transfer.acquire_obs_transfer_slot",
                "input_transfer.start_step1_upload",
                "input_transfer.wait_step1_upload",
                "input_transfer.release_obs_transfer_slot",
                "submit_step2_master",
                "start_step3_monitor",
                "wait_step3_analysis",
                "start_step4_publish",
                "wait_step4_publish",
                "result_transfer.acquire_obs_transfer_slot",
                "result_transfer.start_step5_download",
                "result_transfer.wait_step5_download",
                "result_transfer.release_obs_transfer_slot",
                "materialize_step6_results",
                "finalize_run",
                "release_leases",
            },
        )
        self.assertEqual(dag.get_task("submit_step2_master").pool, "wgs_cce_runs")
        for task_id in (
            "input_transfer.acquire_obs_transfer_slot",
            "input_transfer.wait_step1_upload",
            "wait_step3_analysis",
            "wait_step4_publish",
            "result_transfer.acquire_obs_transfer_slot",
            "result_transfer.wait_step5_download",
        ):
            self.assertEqual(dag.get_task(task_id).mode, "reschedule")

    def test_validate_requires_server_bound_release_identity(self) -> None:
        conf = {
            "analysis_id": "WGS_20260827_123456_A1B2C3",
            "pipeline": "wgs",
            "execution_mode": "cce",
            "attempt": 1,
            "workdir": "/data/wgs-results/runs/WGS_20260827_123456_A1B2C3",
            "params": {
                "project_name": "clinical-wgs",
                "batch_no": "BATCH-1",
                "fq_path": "/data/wgs-intake/BATCH-1",
                "pipeline_release_id": "wgs-4.1.1-1656b5d",
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
            },
        }
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        self.assertEqual(
            bio_wgs.validate_request(**context)["analysis_id"], conf["analysis_id"]
        )
        del conf["params"]["pipeline_release_id"]
        with self.assertRaisesRegex(ValueError, "pipeline_release_id"):
            bio_wgs.validate_request(**context)

    def test_step4_maintenance_mode_reuses_same_dag_without_running_step1_to_step3(self) -> None:
        conf = {
            "maintenance_mode": "repair_step4",
            "repair_group": "cram",
            "continue_after_repair": True,
        }

        self.assertFalse(bio_wgs.stage_should_run("prepare", conf))
        self.assertFalse(bio_wgs.stage_should_run("step3_monitor", conf))
        self.assertTrue(bio_wgs.stage_should_run("step4_publish", conf))
        self.assertTrue(bio_wgs.stage_should_run("step5_download", conf))
        self.assertEqual(
            bio_wgs.effective_runner_stage("step4_publish", conf),
            "step4_repair_cram",
        )
        conf["continue_after_repair"] = False
        self.assertFalse(bio_wgs.stage_should_run("step5_download", conf))
        self.assertFalse(bio_wgs.stage_should_run("step6_materialize", conf))

    def test_maintenance_validation_rejects_any_non_cram_group(self) -> None:
        conf = {
            "analysis_id": "WGS_20260827_123456_A1B2C3",
            "pipeline": "wgs",
            "execution_mode": "cce",
            "attempt": 1,
            "workdir": "/data/wgs-results/runs/WGS_20260827_123456_A1B2C3",
            "maintenance_mode": "repair_step4",
            "repair_group": "vcf",
            "continue_after_repair": False,
            "params": {
                "project_name": "clinical-wgs",
                "batch_no": "BATCH-1",
                "fq_path": "/data/wgs-intake/BATCH-1",
                "pipeline_release_id": "wgs-4.1.1-1656b5d",
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
            },
        }
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}

        with self.assertRaisesRegex(ValueError, "cram"):
            bio_wgs.validate_request(**context)

    def test_step7_cleanup_reuses_only_the_step4_maintenance_slot(self) -> None:
        conf = {
            "maintenance_mode": "cleanup_step7",
            "maintenance_action_id": "step7-sfs-abcdef123456",
            "analysis_id": "WGS_20260901_010203_A1B2C3",
            "pipeline": "wgs",
            "execution_mode": "cce",
            "attempt": 1,
            "workdir": "/data/wgs-results/WGS_20260901_010203_A1B2C3",
            "params": {
                "project_name": "WGS_Clinical",
                "batch_no": "WGS_20260901A_T7Hg38V4.1.1",
                "fq_path": "/data/wgs-intake/BATCH",
                "pipeline_release_id": "wgs-4.1.1-2499749",
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68",
            },
        }
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        self.assertEqual(bio_wgs.validate_request(**context), conf)
        self.assertFalse(bio_wgs.stage_should_run("step3_monitor", conf))
        self.assertTrue(bio_wgs.stage_should_run("step4_publish", conf))
        self.assertFalse(bio_wgs.stage_should_run("step5_download", conf))
        self.assertEqual(
            bio_wgs.effective_runner_stage("step4_publish", conf),
            "step7_cleanup",
        )

    def test_step3_runner_activates_observer_only_after_node200_accepts(self) -> None:
        calls = []
        conf = {"analysis_id": "WGS_20260830_010203_A1B2C3", "attempt": 1}
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        original_backend = bio_wgs._backend_json
        original_run = bio_wgs.subprocess.run
        original_enabled = bio_wgs._require_runtime_enabled
        try:
            bio_wgs._require_runtime_enabled = lambda: None
            bio_wgs._backend_json = lambda path, **kwargs: calls.append(
                (path, kwargs.get("method"), kwargs.get("payload"))
            ) or {"status": "registered"}
            bio_wgs.subprocess.run = lambda *args, **kwargs: type(
                "Completed", (), {"returncode": 0, "stdout": "", "stderr": ""}
            )()
            result = bio_wgs.run_stage_on_200("step3_monitor", **context)
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs.subprocess.run = original_run
            bio_wgs._require_runtime_enabled = original_enabled

        assert result["runner_status"] == "accepted"
        assert calls[-1] == (
            "/api/internal/wgs/runs/WGS_20260830_010203_A1B2C3/observer/activate",
            "POST",
            {"attempt": 1},
        )

    def test_step3_terminal_status_requests_observer_drain(self) -> None:
        calls = []
        conf = {"analysis_id": "WGS_20260830_010203_A1B2C3", "attempt": 1}
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        original_backend = bio_wgs._backend_json
        original_enabled = bio_wgs._require_runtime_enabled
        try:
            bio_wgs._require_runtime_enabled = lambda: None

            def backend(path, **kwargs):
                calls.append((path, kwargs.get("method"), kwargs.get("payload")))
                if path.endswith("stage-status?attempt=1&stage=step3_monitor"):
                    return {"ready": True, "failed": False, "status": "success"}
                return {"lifecycle_status": "draining"}

            bio_wgs._backend_json = backend
            assert bio_wgs.stage_ready("step3_monitor", **context) is True
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs._require_runtime_enabled = original_enabled

        assert calls[-1] == (
            "/api/internal/wgs/runs/WGS_20260830_010203_A1B2C3/observer/deactivate",
            "POST",
            {"attempt": 1},
        )

    def test_stage_start_waits_past_stale_failed_status_from_previous_generation(self) -> None:
        calls = []
        conf = {"analysis_id": "WGS_20260830_010203_A1B2C3", "attempt": 1}
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        original_backend = bio_wgs._backend_json
        original_run = bio_wgs.subprocess.run
        original_enabled = bio_wgs._require_runtime_enabled
        original_sleep = bio_wgs.time.sleep
        try:
            bio_wgs._require_runtime_enabled = lambda: None
            responses = iter(
                [
                    {
                        "status": "registered",
                        "registered_at": "2026-09-02T01:00:00+00:00",
                    },
                    {
                        "status": "failed",
                        "failed": True,
                        "updated_at": "2026-09-01T08:26:13+00:00",
                    },
                    {
                        "status": "accepted",
                        "failed": False,
                        "updated_at": "2026-09-02T01:00:01+00:00",
                    },
                ]
            )

            def backend(path, **kwargs):
                calls.append(path)
                return next(responses)

            bio_wgs._backend_json = backend
            bio_wgs.subprocess.run = lambda *args, **kwargs: type(
                "Completed", (), {"returncode": 0, "stdout": "", "stderr": ""}
            )()
            bio_wgs.time.sleep = lambda _seconds: None
            result = bio_wgs.run_stage_on_200("step4_publish", **context)
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs.subprocess.run = original_run
            bio_wgs._require_runtime_enabled = original_enabled
            bio_wgs.time.sleep = original_sleep

        assert result["runner_status"] == "accepted"
        assert len([path for path in calls if "stage-status" in path]) == 2

    def test_release_leases_always_requests_final_observer_drain(self) -> None:
        calls = []
        context = {
            "dag_run": type(
                "DagRun",
                (),
                {"conf": {"analysis_id": "WGS_20260830_010203_A1B2C3", "attempt": 1}},
            )()
        }
        original_backend = bio_wgs._backend_json
        original_runtime = bio_wgs._runtime_enabled
        try:
            bio_wgs._runtime_enabled = lambda: True

            def backend(path, **kwargs):
                calls.append((path, kwargs.get("method"), kwargs.get("payload")))
                if path.endswith("observer/deactivate"):
                    return {"lifecycle_status": "draining"}
                return {"released": True}

            bio_wgs._backend_json = backend
            result = bio_wgs.release_leases(**context)
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs._runtime_enabled = original_runtime

        assert result == {"released": True, "observer_lifecycle_status": "draining"}
        assert calls[0][0].endswith("/observer/deactivate")
        assert calls[-1][0].endswith("/stages/release_leases")


if __name__ == "__main__":
    unittest.main()
