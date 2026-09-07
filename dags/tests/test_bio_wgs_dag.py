import unittest
from unittest.mock import patch
from io import BytesIO
from pathlib import Path
import sys
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_wgs


class BioWgsDagTests(unittest.TestCase):
    def test_dag_failure_callback_reports_only_root_failed_tasks(self) -> None:
        task_instances = [
            type("TI", (), {"task_id": "prepare_wgs_sampleinfo", "state": "failed"})(),
            type("TI", (), {"task_id": "wait_prepare_wgs_sampleinfo", "state": "upstream_failed"})(),
            type("TI", (), {"task_id": "release_leases", "state": "failed"})(),
        ]
        dag_run = type(
            "DagRun",
            (),
            {
                "conf": {
                    "analysis_id": "WGS_20260907_044653_9C8591",
                    "attempt": 1,
                },
                "get_task_instances": lambda self: task_instances,
            },
        )()
        calls = []
        original_backend = bio_wgs._backend_json
        try:
            bio_wgs._backend_json = lambda path, **kwargs: calls.append(
                (path, kwargs.get("method"), kwargs.get("payload"))
            ) or {"status": "failed"}
            bio_wgs.report_dag_failure({"dag_run": dag_run})
        finally:
            bio_wgs._backend_json = original_backend

        self.assertEqual(
            calls,
            [
                (
                    "/api/internal/wgs/runs/WGS_20260907_044653_9C8591/dag-terminal",
                    "POST",
                    {
                        "attempt": 1,
                        "status": "failed",
                        "failed_task_ids": ["prepare_wgs_sampleinfo"],
                    },
                )
            ],
        )

    def test_dag_has_business_failure_projection_callback(self) -> None:
        self.assertIs(bio_wgs.dag.on_failure_callback, bio_wgs.report_dag_failure)

    def test_dag_exposes_single_release_agnostic_cce_orchestration(self) -> None:
        dag = bio_wgs.dag

        self.assertEqual(dag.dag_id, "bio_wgs")
        self.assertEqual(dag.max_active_runs, 4)
        self.assertTrue(dag.is_paused_upon_creation)
        self.assertEqual(
            set(dag.task_ids),
            {
                "validate_request",
                "prepare_wgs_sampleinfo",
                "wait_prepare_wgs_sampleinfo",
                "wait_wgs_config_approval",
                "prepare_wgs_analysis",
                "wait_prepare_wgs_analysis",
                "wait_wgs_execution_approval",
                "wait_execution_commit",
                "choose_execution_target",
                "input_transfer.acquire_obs_transfer_slot",
                "input_transfer.start_step1_upload",
                "input_transfer.wait_step1_upload",
                "input_transfer.release_obs_transfer_slot",
                "choose_after_step1",
                "finalize_step1_canary",
                "submit_step2_master",
                "start_step3_monitor",
                "wait_step3_analysis",
                "choose_after_step3",
                "finalize_step3_dryrun",
                "start_step4_publish",
                "wait_step4_publish",
                "result_transfer.acquire_obs_transfer_slot",
                "result_transfer.start_step5_download",
                "result_transfer.wait_step5_download",
                "result_transfer.release_obs_transfer_slot",
                "materialize_step6_results",
                "wait_step6_materialize",
                "finalize_run",
                "release_leases",
                "local_execution.start_local_wgs",
                "local_execution.wait_local_wgs",
                "local_execution.finalize_local_wgs",
                "sge_execution.submit_sge_wgs",
            },
        )
        self.assertEqual(dag.get_task("submit_step2_master").pool, "wgs_cce_runs")
        self.assertEqual(
            dag.get_task("input_transfer.acquire_obs_transfer_slot").pool,
            "wgs_obs_upload",
        )
        self.assertEqual(
            dag.get_task("input_transfer.start_step1_upload").pool,
            "wgs_obs_upload",
        )
        self.assertEqual(
            dag.get_task("result_transfer.acquire_obs_transfer_slot").pool,
            "wgs_obs_download",
        )
        self.assertEqual(
            dag.get_task("result_transfer.start_step5_download").pool,
            "wgs_obs_download",
        )
        self.assertEqual(dag.get_task("start_step3_monitor").pool, "default_pool")
        self.assertEqual(dag.get_task("wait_step3_analysis").pool, "default_pool")
        for task_id in (
            "wait_prepare_wgs_sampleinfo",
            "wait_wgs_config_approval",
            "wait_prepare_wgs_analysis",
            "wait_wgs_execution_approval",
            "wait_execution_commit",
            "input_transfer.acquire_obs_transfer_slot",
            "input_transfer.wait_step1_upload",
            "wait_step3_analysis",
            "wait_step4_publish",
            "result_transfer.acquire_obs_transfer_slot",
            "result_transfer.wait_step5_download",
            "wait_step6_materialize",
        ):
            self.assertEqual(dag.get_task(task_id).mode, "reschedule")

        self.assertEqual(
            dag.get_task("choose_execution_target").downstream_task_ids,
            {
                "input_transfer.acquire_obs_transfer_slot",
                "local_execution.start_local_wgs",
                "sge_execution.submit_sge_wgs",
            },
        )
        self.assertEqual(
            dag.get_task("input_transfer.acquire_obs_transfer_slot").upstream_task_ids,
            {"choose_execution_target"},
        )
        self.assertNotIn(
            "input_transfer.start_step1_upload",
            dag.get_task("local_execution.start_local_wgs").downstream_task_ids,
        )
        self.assertEqual(
            dag.get_task("local_execution.start_local_wgs").downstream_task_ids,
            {"local_execution.wait_local_wgs"},
        )
        self.assertEqual(
            dag.get_task("local_execution.wait_local_wgs").downstream_task_ids,
            {"local_execution.finalize_local_wgs"},
        )
        self.assertNotIn(
            "input_transfer.start_step1_upload",
            dag.get_task("sge_execution.submit_sge_wgs").downstream_task_ids,
        )

        self.assertEqual(
            {task.task_id for task in dag.get_task("finalize_run").upstream_list},
            {"wait_step6_materialize"},
        )
        self.assertEqual(
            dag.get_task("choose_after_step1").downstream_task_ids,
            {"finalize_step1_canary", "submit_step2_master"},
        )
        self.assertEqual(
            dag.get_task("release_leases").upstream_task_ids,
            {
                "finalize_run",
                "finalize_step1_canary",
                "finalize_step3_dryrun",
                "local_execution.finalize_local_wgs",
                "sge_execution.submit_sge_wgs",
            },
        )
        self.assertEqual(
            dag.get_task("choose_after_step3").downstream_task_ids,
            {"finalize_step3_dryrun", "start_step4_publish"},
        )
        self.assertEqual(
            dag.get_task("wait_step4_publish").upstream_task_ids,
            {"start_step4_publish"},
        )
        self.assertEqual(
            dag.get_task("input_transfer.release_obs_transfer_slot").trigger_rule,
            "all_done",
        )
        self.assertEqual(
            dag.get_task("result_transfer.release_obs_transfer_slot").trigger_rule,
            "all_done",
        )
        self.assertEqual(
            dag.get_task("choose_after_step1").upstream_task_ids,
            {
                "input_transfer.wait_step1_upload",
                "input_transfer.release_obs_transfer_slot",
            },
        )
        self.assertEqual(
            dag.get_task("materialize_step6_results").upstream_task_ids,
            {
                "result_transfer.wait_step5_download",
                "result_transfer.release_obs_transfer_slot",
            },
        )

    def test_step1_canary_is_fail_closed_and_branches_before_master(self) -> None:
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
                "validation_scope": "step1_only",
            },
        }
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}

        with patch.dict("os.environ", {"WGS_STEP1_CANARY_ENABLED": "false"}):
            with self.assertRaisesRegex(ValueError, "Step1 canary is disabled"):
                bio_wgs.validate_request(**context)
        with patch.dict(
            "os.environ",
            {
                "WGS_STEP1_CANARY_ENABLED": "true",
                "WGS_CONTRACT_V2_ENABLED": "false",
            },
        ):
            with self.assertRaisesRegex(ValueError, "contract v2"):
                bio_wgs.validate_request(**context)
        with patch.dict(
            "os.environ",
            {
                "WGS_STEP1_CANARY_ENABLED": "true",
                "WGS_CONTRACT_V2_ENABLED": "true",
            },
        ):
            self.assertEqual(bio_wgs.validate_request(**context), conf)
            self.assertEqual(
                bio_wgs.choose_after_step1(**context), "finalize_step1_canary"
            )

        conf["params"].pop("validation_scope")
        self.assertEqual(
            bio_wgs.choose_after_step1(**context), "submit_step2_master"
        )

    def test_execution_commit_sensor_reads_latest_database_choice(self) -> None:
        conf = {
            "analysis_id": "WGS_20260906_123456_A1B2C3",
            "attempt": 2,
            "params": {"submission_mode": "three_stage"},
        }
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        calls = []
        with patch.object(
            bio_wgs,
            "_sensor_backend_json",
            side_effect=lambda path, **kwargs: calls.append((path, kwargs))
            or {"committed": True, "desired_target": "node-97"},
        ):
            self.assertTrue(bio_wgs.execution_commit_ready(**context))
        self.assertEqual(
            calls,
            [
                (
                    "/api/internal/wgs/runs/WGS_20260906_123456_A1B2C3/execution-commit",
                    {"method": "POST", "payload": {"attempt": 2}},
                )
            ],
        )

    def test_execution_branch_uses_committed_target_and_is_mutually_exclusive(self) -> None:
        conf = {
            "analysis_id": "WGS_20260906_123456_A1B2C3",
            "attempt": 1,
            "params": {"submission_mode": "three_stage"},
        }
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        targets = {
            "cce": "input_transfer.acquire_obs_transfer_slot",
            "node-97": "local_execution.start_local_wgs",
            "node-96": "local_execution.start_local_wgs",
            "sge-default": "sge_execution.submit_sge_wgs",
        }
        for target, expected_task in targets.items():
            with self.subTest(target=target), patch.object(
                bio_wgs,
                "_backend_json",
                return_value={"committed": True, "desired_target": target},
            ):
                self.assertEqual(
                    bio_wgs.choose_execution_target(**context), expected_task
                )

    def test_node97_runner_registers_local_stage_and_uses_restricted_ssh(self) -> None:
        conf = {
            "analysis_id": "WGS_20260907_123456_A1B2C3",
            "attempt": 1,
            "params": {"submission_mode": "three_stage"},
        }
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        completed = type(
            "Completed", (), {"returncode": 0, "stdout": '{"status":"accepted"}\n', "stderr": ""}
        )()
        with patch.object(
            bio_wgs,
            "_backend_json",
            side_effect=[{"status": "registered"}, {"lifecycle_status": "active"}],
        ) as backend, patch.object(
            bio_wgs.subprocess, "run", return_value=completed
        ) as run, patch.dict(
            "os.environ",
            {
                "WGS_EXECUTION_ENABLED": "true",
                "WGS_RUNTIME_ADAPTER_ENABLED": "true",
                "WGS_LOCAL_NODE97_ENABLED": "true",
                "WGS_RUNNER_NODE97_ALIAS": "wgs-node97",
                "WGS_RUNNER_NODE97_COMMAND": "/opt/wgs-local/forced-command.sh",
            },
            clear=False,
        ):
            result = bio_wgs.run_stage_on_node97(**context)

        self.assertEqual(result["runner_status"], "accepted")
        self.assertEqual(
            backend.call_args_list[0].args[0],
            "/api/internal/wgs/runs/WGS_20260907_123456_A1B2C3/stages/local_analysis",
        )
        self.assertEqual(
            backend.call_args_list[0].kwargs["payload"]["adapter"],
            "wgs-runtime-node97",
        )
        command = run.call_args.args[0]
        self.assertIn("wgs-node97", command)
        self.assertEqual(
            command[-4:],
            ["wgs-local-runtime", conf["analysis_id"], "1", "local_analysis"],
        )

    def test_step3_dryrun_is_gated_and_branches_after_master(self) -> None:
        conf = {
            "analysis_id": "WGS_20260906_123456_A1B2C3",
            "pipeline": "wgs",
            "execution_mode": "cce",
            "attempt": 1,
            "workdir": "/data/wgs-results/runs/WGS_20260906_123456_A1B2C3",
            "params": {
                "project_name": "clinical-wgs",
                "batch_no": "BATCH-DRYRUN",
                "fq_path": "/data/wgs-intake/BATCH-DRYRUN",
                "pipeline_release_id": "wgs-4.1.1-1656b5d",
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
                "validation_scope": "step3_dryrun",
            },
        }
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}

        with patch.dict(
            "os.environ",
            {
                "WGS_STEP3_DRYRUN_CANARY_ENABLED": "false",
                "WGS_CONTRACT_V2_ENABLED": "true",
            },
        ):
            with self.assertRaisesRegex(ValueError, "Step3 dry-run canary is disabled"):
                bio_wgs.validate_request(**context)
        with patch.dict(
            "os.environ",
            {
                "WGS_STEP3_DRYRUN_CANARY_ENABLED": "true",
                "WGS_CONTRACT_V2_ENABLED": "true",
            },
        ):
            self.assertEqual(bio_wgs.validate_request(**context), conf)
            self.assertEqual(bio_wgs.choose_after_step1(**context), "submit_step2_master")
            self.assertEqual(
                bio_wgs.choose_after_step3(**context), "finalize_step3_dryrun"
            )

        conf["params"].pop("validation_scope")
        self.assertEqual(bio_wgs.choose_after_step3(**context), "start_step4_publish")

    def test_node97_full_canary_is_gated_and_uses_normal_terminal_path(self) -> None:
        conf = {
            "analysis_id": "WGS_20260907_123456_A1B2C3",
            "pipeline": "wgs",
            "execution_mode": "cce",
            "attempt": 1,
            "workdir": "/data/wgs-results/runs/WGS_20260907_123456_A1B2C3",
            "params": {
                "project_name": "clinical-wgs",
                "batch_no": "WGS_20260825A_NODE97_FULL_CANARY_T7Hg38V4.1.1",
                "fq_path": "/data/wgs-intake/.node97-full-fastq",
                "pipeline_release_id": "wgs-4.1.1-1656b5d",
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
                "validation_scope": "node97_full",
            },
        }
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}

        with patch.dict(
            "os.environ",
            {
                "WGS_NODE97_FULL_CANARY_ENABLED": "false",
                "WGS_CONTRACT_V2_ENABLED": "true",
            },
        ):
            with self.assertRaisesRegex(ValueError, "node97 full canary is disabled"):
                bio_wgs.validate_request(**context)
        with patch.dict(
            "os.environ",
            {
                "WGS_NODE97_FULL_CANARY_ENABLED": "true",
                "WGS_CONTRACT_V2_ENABLED": "true",
            },
        ):
            self.assertEqual(bio_wgs.validate_request(**context), conf)
            self.assertEqual(bio_wgs.choose_after_step1(**context), "submit_step2_master")
            self.assertEqual(bio_wgs.choose_after_step3(**context), "start_step4_publish")

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

    def test_runner_retries_boundedly_when_registered_request_is_not_yet_visible(
        self,
    ) -> None:
        calls = []
        sleeps = []
        conf = {"analysis_id": "WGS_20260903_111456_397777", "attempt": 1}
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        missing_request = type(
            "Completed",
            (),
            {
                "returncode": 1,
                "stdout": "",
                "stderr": (
                    "FileNotFoundError: [Errno 2] No such file or directory: "
                    "'/sg2/runtime/runner-requests/WGS_20260903_111456_397777/"
                    "attempt-1/step3_monitor.json'"
                ),
            },
        )()
        accepted = type(
            "Completed",
            (),
            {"returncode": 0, "stdout": '{"status":"running"}', "stderr": ""},
        )()
        replies = iter((missing_request, accepted))
        original_backend = bio_wgs._backend_json
        original_run = bio_wgs.subprocess.run
        original_sleep = bio_wgs.time.sleep
        original_enabled = bio_wgs._require_runtime_enabled
        try:
            bio_wgs._require_runtime_enabled = lambda: None
            bio_wgs._backend_json = lambda path, **kwargs: calls.append(path) or {
                "status": "registered"
            }
            bio_wgs.subprocess.run = lambda *args, **kwargs: next(replies)
            bio_wgs.time.sleep = lambda seconds: sleeps.append(seconds)
            result = bio_wgs.run_stage_on_200("step3_monitor", **context)
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs.subprocess.run = original_run
            bio_wgs.time.sleep = original_sleep
            bio_wgs._require_runtime_enabled = original_enabled

        self.assertEqual(result["runner_status"], "accepted")
        self.assertEqual(sleeps, [1.0])
        self.assertTrue(calls[-1].endswith("/observer/activate"))

    def test_stage_registration_retries_only_while_predecessor_receipt_is_pending(
        self,
    ) -> None:
        calls = []
        sleeps = []
        conf = {"analysis_id": "WGS_20260905_210104_739143", "attempt": 4}
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        replies = iter(
            (
                bio_wgs.BackendStagePredecessorPending("step2 pending"),
                bio_wgs.BackendStagePredecessorPending("step2 pending"),
                {"status": "registered", "generation": 2},
            )
        )
        original_backend = bio_wgs._backend_json
        original_sleep = bio_wgs.time.sleep
        original_enabled = bio_wgs._require_runtime_enabled

        def backend(path, **kwargs):
            calls.append((path, kwargs))
            reply = next(replies)
            if isinstance(reply, Exception):
                raise reply
            return reply

        try:
            bio_wgs._require_runtime_enabled = lambda: None
            bio_wgs._backend_json = backend
            bio_wgs.time.sleep = lambda seconds: sleeps.append(seconds)
            result = bio_wgs.register_stage("step3_monitor", **context)
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs.time.sleep = original_sleep
            bio_wgs._require_runtime_enabled = original_enabled

        self.assertEqual(result["generation"], 2)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [5.0, 5.0])

    def test_backend_json_preserves_predecessor_pending_error_code(self) -> None:
        response = HTTPError(
            "http://backend:8000/api/internal/wgs/test",
            409,
            "Conflict",
            {},
            BytesIO(
                b'{"detail":{"code":"WGS_STAGE_PREDECESSOR_PENDING",'
                b'"message":"step2 receipt is not visible"}}'
            ),
        )

        with patch.object(bio_wgs, "urlopen", side_effect=response):
            with self.assertRaisesRegex(
                bio_wgs.BackendStagePredecessorPending,
                "step2 receipt is not visible",
            ):
                bio_wgs._backend_json("/api/internal/wgs/test")

    def test_stage_sensor_reschedules_on_transient_backend_500(self) -> None:
        response = HTTPError(
            "http://backend:8000/api/internal/wgs/test",
            500,
            "Internal Server Error",
            {},
            BytesIO(b""),
        )

        with patch.object(bio_wgs, "urlopen", side_effect=response):
            self.assertIsNone(
                bio_wgs._sensor_backend_json("/api/internal/wgs/test")
            )

    def test_runner_failure_preserves_remote_stdout_and_ssh_stderr(self) -> None:
        conf = {"analysis_id": "WGS_20260903_062828_0858DC", "attempt": 1}
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        original_register = bio_wgs.register_stage
        original_run = bio_wgs.subprocess.run
        try:
            bio_wgs.register_stage = lambda *_args, **_kwargs: {"status": "registered"}
            bio_wgs.subprocess.run = lambda *args, **kwargs: type(
                "Completed",
                (),
                {
                    "returncode": 1,
                    "stdout": "ValueError: unsupported WGS prepare stage\n",
                    "stderr": "Connection to 172.17.61.200 closed.\n",
                },
            )()
            with self.assertRaisesRegex(
                RuntimeError,
                "unsupported WGS prepare stage.*Connection to 172.17.61.200 closed",
            ):
                bio_wgs.run_stage_on_200("prepare_sampleinfo", **context)
        finally:
            bio_wgs.register_stage = original_register
            bio_wgs.subprocess.run = original_run

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

    def test_stage_sensor_reschedules_when_backend_transport_is_temporarily_unavailable(
        self,
    ) -> None:
        conf = {"analysis_id": "WGS_20260903_111456_397777", "attempt": 1}
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        original_urlopen = bio_wgs.urlopen
        original_enabled = bio_wgs._require_runtime_enabled
        try:
            bio_wgs._require_runtime_enabled = lambda: None

            def timeout(*_args, **_kwargs):
                raise TimeoutError("backend restart")

            bio_wgs.urlopen = timeout
            assert bio_wgs.stage_ready("step3_monitor", **context) is False
        finally:
            bio_wgs.urlopen = original_urlopen
            bio_wgs._require_runtime_enabled = original_enabled

    def test_submission_gate_reschedules_when_backend_transport_is_temporarily_unavailable(
        self,
    ) -> None:
        conf = {
            "analysis_id": "WGS_20260903_111829_1D58E1",
            "attempt": 6,
            "params": {"submission_mode": "three_stage"},
        }
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        original_backend = bio_wgs._backend_json
        try:
            bio_wgs._backend_json = lambda *_args, **_kwargs: (_ for _ in ()).throw(
                bio_wgs.BackendTransportUnavailable("backend DNS unavailable")
            )
            for gate in ("config", "execution"):
                with self.subTest(gate=gate):
                    self.assertFalse(bio_wgs.submission_gate_ready(gate, **context))
        finally:
            bio_wgs._backend_json = original_backend

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
                    },
                    {
                        "status": "failed",
                        "failed": True,
                        "retry_no": 0,
                    },
                    {
                        "status": "accepted",
                        "failed": False,
                        "retry_no": 1,
                    },
                ]
            )

            def backend(path, **kwargs):
                calls.append(path)
                return next(responses)

            bio_wgs._backend_json = backend
            bio_wgs.subprocess.run = lambda *args, **kwargs: type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": '{"status": "accepted", "retry_no": 1}\n',
                    "stderr": "",
                },
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

    def test_failed_synchronous_stage_waits_for_terminal_runtime_projection(self) -> None:
        calls = []
        conf = {"analysis_id": "WGS_20260907_044653_9C8591", "attempt": 2}
        context = {"dag_run": type("DagRun", (), {"conf": conf})()}
        original_backend = bio_wgs._backend_json
        original_run = bio_wgs.subprocess.run
        original_enabled = bio_wgs._require_runtime_enabled
        original_sleep = bio_wgs.time.sleep
        try:
            bio_wgs._require_runtime_enabled = lambda: None
            responses = iter(
                [
                    {"status": "registered", "generation": 1},
                    {"status": "pending", "failed": False, "retry_no": None},
                    {"status": "failed", "failed": True, "retry_no": 0},
                ]
            )

            def backend(path, **kwargs):
                calls.append(path)
                return next(responses)

            bio_wgs._backend_json = backend
            bio_wgs.subprocess.run = lambda *args, **kwargs: type(
                "Completed",
                (),
                {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "runtime stage failed",
                },
            )()
            bio_wgs.time.sleep = lambda _seconds: None
            with self.assertRaisesRegex(
                RuntimeError, "restricted node200 WGS stage failed"
            ):
                bio_wgs.run_stage_on_200("step2_master", **context)
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs.subprocess.run = original_run
            bio_wgs._require_runtime_enabled = original_enabled
            bio_wgs.time.sleep = original_sleep

        assert len([path for path in calls if "stage-status" in path]) == 2

    def test_step5_start_waits_past_stale_failed_status_from_previous_generation(self) -> None:
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
                    {"status": "registered"},
                    {"status": "failed", "failed": True, "retry_no": 0},
                    {"status": "running", "failed": False, "retry_no": 1},
                ]
            )

            def backend(path, **kwargs):
                calls.append(path)
                return next(responses)

            bio_wgs._backend_json = backend
            bio_wgs.subprocess.run = lambda *args, **kwargs: type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": '{"status": "accepted", "retry_no": 1}\n',
                    "stderr": "",
                },
            )()
            bio_wgs.time.sleep = lambda _seconds: None
            result = bio_wgs.run_stage_on_200("step5_download", **context)
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs.subprocess.run = original_run
            bio_wgs._require_runtime_enabled = original_enabled
            bio_wgs.time.sleep = original_sleep

        assert result["runner_status"] == "accepted"
        assert len([path for path in calls if "stage-status" in path]) == 2

    def test_step3_start_waits_past_stale_failed_status_from_previous_generation(self) -> None:
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
                    {"status": "registered"},
                    {"status": "failed", "failed": True, "retry_no": 0},
                    {"status": "running", "failed": False, "retry_no": 2},
                    {"status": "observer-active"},
                ]
            )

            def backend(path, **kwargs):
                calls.append(path)
                return next(responses)

            bio_wgs._backend_json = backend
            bio_wgs.subprocess.run = lambda *args, **kwargs: type(
                "Completed",
                (),
                {
                    "returncode": 0,
                    "stdout": '{"status": "accepted", "retry_no": 2}\n',
                    "stderr": "",
                },
            )()
            bio_wgs.time.sleep = lambda _seconds: None
            result = bio_wgs.run_stage_on_200("step3_monitor", **context)
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs.subprocess.run = original_run
            bio_wgs._require_runtime_enabled = original_enabled
            bio_wgs.time.sleep = original_sleep

        assert result["runner_status"] == "accepted"
        assert len([path for path in calls if "stage-status" in path]) == 2
        assert calls[-1].endswith("/observer/activate")

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

    def test_release_leases_fails_closed_when_backend_retains_a_lease(self) -> None:
        context = {
            "dag_run": type(
                "DagRun",
                (),
                {"conf": {"analysis_id": "WGS_20260907_010203_A1B2C3", "attempt": 1}},
            )()
        }
        original_backend = bio_wgs._backend_json
        original_runtime = bio_wgs._runtime_enabled
        try:
            bio_wgs._runtime_enabled = lambda: True

            def backend(path, **kwargs):
                if path.endswith("observer/deactivate"):
                    return {"lifecycle_status": "draining"}
                return {
                    "released": False,
                    "retained": True,
                    "reason": "transfer_not_terminal",
                }

            bio_wgs._backend_json = backend
            with self.assertRaisesRegex(RuntimeError, "transfer_not_terminal"):
                bio_wgs.release_leases(**context)
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs._runtime_enabled = original_runtime

    def test_directional_release_task_fails_closed_when_evidence_is_not_terminal(
        self,
    ) -> None:
        context = {
            "dag_run": type(
                "DagRun",
                (),
                {"conf": {"analysis_id": "WGS_20260907_010203_A1B2C3", "attempt": 1}},
            )()
        }
        original_backend = bio_wgs._backend_json
        original_enabled = bio_wgs._require_runtime_enabled
        try:
            bio_wgs._require_runtime_enabled = lambda: None
            bio_wgs._backend_json = lambda *args, **kwargs: {
                "released": False,
                "retained": True,
                "reason": "transfer_not_terminal",
            }
            with self.assertRaisesRegex(RuntimeError, "transfer_not_terminal"):
                bio_wgs.register_stage("release_input_transfer_slot", **context)
        finally:
            bio_wgs._backend_json = original_backend
            bio_wgs._require_runtime_enabled = original_enabled


if __name__ == "__main__":
    unittest.main()
