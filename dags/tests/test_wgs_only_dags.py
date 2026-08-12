from pathlib import Path
import os
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_wgs_cce
import bio_wgs_intake_scan
import bio_wgs_onprem


def _context(conf):
    return {"dag_run": type("DagRun", (), {"conf": conf})()}


class WgsOnlyDagTests(unittest.TestCase):
    def test_cce_topology_has_project_level_disabled_stages_and_reschedule_sensors(self):
        dag = bio_wgs_cce.dag
        self.assertEqual(dag.dag_id, "bio_wgs_cce")
        self.assertEqual(dag.max_active_runs, 4)
        self.assertEqual(
            set(dag.task_ids),
            {
                "validate_request", "upload_to_obs", "verify_obs_upload", "cce_preflight",
                "acquire_master_slot", "launch_master", "wait_for_master", "publish_evidence",
                "download_results", "verify_results", "finalize_run",
            },
        )
        self.assertIs(dag.get_task("upload_to_obs").python_callable, bio_wgs_cce.execution_disabled)
        self.assertEqual(dag.get_task("upload_to_obs").pool, "wgs_obs_transfer")
        self.assertEqual(dag.get_task("acquire_master_slot").pool, "wgs_cce_runs")
        self.assertEqual(dag.get_task("wait_for_master").mode, "reschedule")
        self.assertEqual(dag.get_task("wait_for_master").poke_interval, 60)
        self.assertEqual(dag.get_task("wait_for_master").timeout, 172800)

    def test_cce_contract_rejects_wrong_mode_and_fails_closed_by_default(self):
        conf = {
            "analysis_id": "WGS_20260812_000001_A1B2C3", "pipeline": "wgs", "execution_mode": "cce",
            "attempt": 1, "workdir": "/data/airflow-demo/runs/WGS_20260812_000001_A1B2C3",
        }
        self.assertEqual(bio_wgs_cce.validate_request(**_context(conf))["analysis_id"], conf["analysis_id"])
        conf["execution_mode"] = "local"
        with self.assertRaisesRegex(ValueError, "execution_mode"):
            bio_wgs_cce.validate_request(**_context(conf))
        previous = os.environ.pop("WGS_EXECUTION_ENABLED", None)
        try:
            with self.assertRaisesRegex(RuntimeError, "WGS_EXECUTION_ENABLED"):
                bio_wgs_cce.execution_disabled(**_context(conf))
        finally:
            if previous is not None:
                os.environ["WGS_EXECUTION_ENABLED"] = previous

    def test_onprem_allows_local_or_sge_and_fails_closed_by_default(self):
        dag = bio_wgs_onprem.dag
        self.assertEqual(dag.dag_id, "bio_wgs_onprem")
        self.assertEqual(dag.get_task("wait_for_pipeline").mode, "reschedule")
        self.assertIs(dag.get_task("run_pipeline").python_callable, bio_wgs_onprem.execution_disabled)
        for mode in ("local", "sge"):
            conf = {
                "analysis_id": "WGS_20260812_000001_A1B2C3", "pipeline": "wgs", "execution_mode": mode,
                "attempt": 1, "workdir": "/data/airflow-demo/runs/WGS_20260812_000001_A1B2C3",
            }
            self.assertEqual(bio_wgs_onprem.validate_request(**_context(conf))["execution_mode"], mode)
        previous = os.environ.pop("WGS_EXECUTION_ENABLED", None)
        try:
            with self.assertRaisesRegex(RuntimeError, "WGS_EXECUTION_ENABLED"):
                bio_wgs_onprem.execution_disabled(**_context(conf))
        finally:
            if previous is not None:
                os.environ["WGS_EXECUTION_ENABLED"] = previous

    def test_intake_scanner_runs_only_wgs_every_ten_minutes(self):
        dag = bio_wgs_intake_scan.dag
        self.assertEqual(dag.dag_id, "bio_wgs_intake_scan")
        self.assertEqual(str(dag.timetable.summary), "*/10 * * * *")
        self.assertEqual(
            bio_wgs_intake_scan.build_scan_payload(**_context({})),
            {"pipelines": ["wgs"], "bootstrap": False, "max_samples": 200},
        )
