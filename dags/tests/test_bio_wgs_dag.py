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


if __name__ == "__main__":
    unittest.main()
