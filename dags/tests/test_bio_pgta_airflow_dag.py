import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_pgta_airflow


class BioPgtaAirflowDagTests(unittest.TestCase):
    def test_dag_id_and_task_order(self) -> None:
        dag = bio_pgta_airflow.dag

        self.assertEqual(dag.dag_id, "bio_pgta_airflow")
        self.assertFalse(dag.is_paused_upon_creation)
        self.assertEqual(
            set(dag.task_ids),
            {
                "validate_request",
                "prepare_pgta_config",
                "run_snakemake9_with_logger",
                "collect_snakemake_events",
                "collect_metadata_artifact",
            },
        )
        self.assertEqual(dag.get_task("validate_request").downstream_task_ids, {"prepare_pgta_config"})
        self.assertEqual(dag.get_task("prepare_pgta_config").downstream_task_ids, {"run_snakemake9_with_logger"})
        self.assertEqual(
            dag.get_task("run_snakemake9_with_logger").downstream_task_ids,
            {"collect_snakemake_events"},
        )
        self.assertEqual(dag.get_task("collect_snakemake_events").downstream_task_ids, {"collect_metadata_artifact"})


if __name__ == "__main__":
    unittest.main()
