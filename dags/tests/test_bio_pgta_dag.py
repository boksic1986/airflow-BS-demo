import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_pgta


class BioPgtaDagTests(unittest.TestCase):
    def test_dag_id_and_task_order(self) -> None:
        dag = bio_pgta.dag

        self.assertEqual(dag.dag_id, "bio_pgta")
        self.assertEqual(
            set(dag.task_ids),
            {"validate_request", "prepare_pgta_config", "run_metadata", "collect_metadata_artifact"},
        )
        self.assertTrue(dag.get_task("validate_request").downstream_task_ids == {"prepare_pgta_config"})
        self.assertTrue(dag.get_task("prepare_pgta_config").downstream_task_ids == {"run_metadata"})
        self.assertTrue(dag.get_task("run_metadata").downstream_task_ids == {"collect_metadata_artifact"})


if __name__ == "__main__":
    unittest.main()
