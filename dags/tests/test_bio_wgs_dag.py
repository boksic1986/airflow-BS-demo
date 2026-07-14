import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_wgs


class BioWgsDagTests(unittest.TestCase):
    def test_dag_exposes_controlled_wgs_stages(self) -> None:
        dag = bio_wgs.dag

        self.assertEqual(dag.dag_id, "bio_wgs")
        self.assertEqual(dag.max_active_runs, 1)
        self.assertEqual(
            set(dag.task_ids),
            {
                "validate_request",
                "prepare_wgs_run",
                "wgs_pipeline.pre_calling",
                "choose_wgs_path",
                "wgs_pipeline.variant_analysis",
                "wgs_pipeline.collect_qc",
                "collect_wgs_artifacts",
            },
        )
        self.assertEqual(dag.get_task("wgs_pipeline.pre_calling").pool, "wgs_full")
        self.assertEqual(dag.get_task("wgs_pipeline.pre_calling").ssh_conn_id, "wgs_host")
        self.assertEqual(dag.get_task("wgs_pipeline.variant_analysis").ssh_conn_id, "wgs_host")
        self.assertEqual(dag.get_task("wgs_pipeline.collect_qc").ssh_conn_id, "wgs_host")
        self.assertEqual(
            dag.get_task("wgs_pipeline.pre_calling").command,
            "wgs-run {{ dag_run.conf['analysis_id'] }} pre_calling",
        )
        self.assertEqual(
            dag.get_task("prepare_wgs_run").downstream_task_ids,
            {"wgs_pipeline.pre_calling"},
        )
        self.assertEqual(
            dag.get_task("choose_wgs_path").downstream_task_ids,
            {"wgs_pipeline.variant_analysis", "collect_wgs_artifacts"},
        )
        self.assertEqual(dag.get_task("collect_wgs_artifacts").trigger_rule, "none_failed_min_one_success")

    def test_precalling_mode_branches_directly_to_collect(self) -> None:
        context = {"dag_run": type("DagRun", (), {"conf": {"params": {"wgs_stage": "precalling"}}})()}

        self.assertEqual(bio_wgs._choose_wgs_path(**context), "collect_wgs_artifacts")

    def test_full_mode_runs_variant_analysis(self) -> None:
        context = {"dag_run": type("DagRun", (), {"conf": {"params": {"wgs_stage": "full"}}})()}

        self.assertEqual(bio_wgs._choose_wgs_path(**context), "wgs_pipeline.variant_analysis")


if __name__ == "__main__":
    unittest.main()
