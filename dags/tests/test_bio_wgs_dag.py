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
                "wgs_pipeline.variant_analysis",
                "wgs_pipeline.collect_qc",
                "collect_wgs_artifacts",
            },
        )
        self.assertEqual(dag.get_task("wgs_pipeline.pre_calling").pool, "wgs_full")
        self.assertEqual(
            dag.get_task("prepare_wgs_run").downstream_task_ids,
            {"wgs_pipeline.pre_calling"},
        )
        self.assertEqual(
            dag.get_task("wgs_pipeline.variant_analysis").downstream_task_ids,
            {"wgs_pipeline.collect_qc"},
        )


if __name__ == "__main__":
    unittest.main()
