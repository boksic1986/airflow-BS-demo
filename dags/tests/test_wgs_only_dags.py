from pathlib import Path
import os
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_wgs


def _context(conf):
    return {"dag_run": type("DagRun", (), {"conf": conf})()}


class WgsOnlyDagTests(unittest.TestCase):
    def test_release_leaf_reports_upstream_failures(self):
        task_instances = [
            type("TaskInstance", (), {"task_id": "prepare_wgs_batch", "state": "failed"})(),
            type("TaskInstance", (), {"task_id": "release_leases", "state": "running"})(),
        ]
        dag_run = type(
            "DagRun", (), {"get_task_instances": lambda _self: task_instances}
        )()
        task_instance = type(
            "CurrentTask", (), {"task_id": "release_leases", "get_dagrun": lambda _self: dag_run}
        )()

        self.assertEqual(
            bio_wgs._upstream_failure_task_ids({"ti": task_instance}),
            ["prepare_wgs_batch"],
        )

    def test_single_cce_contract_rejects_wrong_mode_and_fails_closed(self):
        conf = {
            "analysis_id": "WGS_20260812_000001_A1B2C3",
            "pipeline": "wgs",
            "execution_mode": "cce",
            "attempt": 1,
            "workdir": "/data/wgs-results/runs/WGS_20260812_000001_A1B2C3",
            "params": {
                "project_name": "clinical-wgs",
                "batch_no": "BATCH-1",
                "fq_path": "/data/wgs-intake/BATCH-1",
                "pipeline_release_id": "wgs-4.1.1-1656b5d",
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
            },
        }
        self.assertEqual(bio_wgs.validate_request(**_context(conf))["analysis_id"], conf["analysis_id"])
        conf["execution_mode"] = "local"
        with self.assertRaisesRegex(ValueError, "execution_mode"):
            bio_wgs.validate_request(**_context(conf))

        conf["execution_mode"] = "cce"
        previous_execution = os.environ.pop("WGS_EXECUTION_ENABLED", None)
        previous_adapter = os.environ.pop("WGS_RUNTIME_ADAPTER_ENABLED", None)
        try:
            with self.assertRaisesRegex(RuntimeError, "disabled"):
                bio_wgs.register_stage("prepare_wgs_batch", **_context(conf))
        finally:
            if previous_execution is not None:
                os.environ["WGS_EXECUTION_ENABLED"] = previous_execution
            if previous_adapter is not None:
                os.environ["WGS_RUNTIME_ADAPTER_ENABLED"] = previous_adapter

    def test_only_one_wgs_dag_is_published_by_compose(self):
        compose = (Path(__file__).resolve().parents[2] / "docker-compose.wgs.yaml").read_text(encoding="utf-8")
        self.assertIn("./dags/bio_wgs.py:/opt/airflow/dags/bio_wgs.py:ro", compose)
        self.assertNotIn("./dags/bio_wgs_cce.py:/opt/airflow/dags", compose)
        self.assertNotIn("./dags/bio_wgs_onprem.py:/opt/airflow/dags", compose)
        self.assertNotIn("./dags/bio_wgs_intake_scan.py:/opt/airflow/dags", compose)

    def test_node200_runner_uses_forced_tty_and_checked_ssh_config(self):
        source = (Path(__file__).resolve().parents[1] / "bio_wgs.py").read_text(encoding="utf-8")
        self.assertIn('"-tt"', source)
        self.assertIn('"-F"', source)
        self.assertIn("WGS_SSH_CONFIG_PATH", source)
        self.assertIn("/home/chenjc/.config/airflow-wgs/forced-command.sh", source)
        self.assertNotIn("SSHHook", source)
