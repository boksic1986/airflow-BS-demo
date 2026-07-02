import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_pgta


class BioPgtaDagTests(unittest.TestCase):
    def test_dag_id_and_task_order(self) -> None:
        dag = bio_pgta.dag

        self.assertEqual(dag.dag_id, "bio_pgta")
        self.assertFalse(dag.is_paused_upon_creation)
        self.assertEqual(
            set(dag.task_ids),
            {"validate_request", "prepare_pgta_config", "run_metadata", "collect_metadata_artifact"},
        )
        self.assertTrue(dag.get_task("validate_request").downstream_task_ids == {"prepare_pgta_config"})
        self.assertTrue(dag.get_task("prepare_pgta_config").downstream_task_ids == {"run_metadata"})
        self.assertTrue(dag.get_task("run_metadata").downstream_task_ids == {"collect_metadata_artifact"})

    def test_collect_metadata_callable_returns_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            logs_dir = workdir / "logs"
            logs_dir.mkdir(parents=True)
            (logs_dir / "run_metadata.tsv").write_text("key\tvalue\n", encoding="utf-8")

            class DummyTaskInstance:
                def xcom_pull(self, task_ids: str):
                    self.task_ids = task_ids
                    return {"analysis_id": "PGTA_TEST", "workdir": str(workdir)}

            task_instance = DummyTaskInstance()
            artifact = bio_pgta._collect_metadata_artifact(ti=task_instance)

        self.assertEqual(task_instance.task_ids, "run_metadata")
        self.assertEqual(artifact["type"], "pgta_metadata")
        self.assertTrue(artifact["path"].endswith("run_metadata.tsv"))


if __name__ == "__main__":
    unittest.main()
