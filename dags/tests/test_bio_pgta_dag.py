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
            {
                "validate_request",
                "prepare_pgta_config",
                "choose_pgta_path",
                "run_pgta_target",
                "pgta_pipeline.run_pgta_mapping",
                "pgta_pipeline.run_pgta_metadata",
                "pgta_pipeline.run_pgta_baseline_qc",
                "collect_pgta_artifact",
            },
        )
        self.assertTrue(dag.get_task("validate_request").downstream_task_ids == {"prepare_pgta_config"})
        self.assertTrue(dag.get_task("prepare_pgta_config").downstream_task_ids == {"choose_pgta_path"})
        self.assertTrue(
            dag.get_task("choose_pgta_path").downstream_task_ids
            == {
                "run_pgta_target",
                "pgta_pipeline.run_pgta_mapping",
                "pgta_pipeline.run_pgta_metadata",
                "pgta_pipeline.run_pgta_baseline_qc",
            }
        )
        self.assertTrue(dag.get_task("pgta_pipeline.run_pgta_mapping").downstream_task_ids == {"pgta_pipeline.run_pgta_metadata"})
        self.assertTrue(dag.get_task("pgta_pipeline.run_pgta_metadata").downstream_task_ids == {"pgta_pipeline.run_pgta_baseline_qc"})
        self.assertTrue(dag.get_task("pgta_pipeline.run_pgta_baseline_qc").downstream_task_ids == {"collect_pgta_artifact"})
        self.assertTrue(dag.get_task("run_pgta_target").downstream_task_ids == {"collect_pgta_artifact"})

    def test_collect_metadata_callable_returns_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            logs_dir = workdir / "logs"
            logs_dir.mkdir(parents=True)
            (logs_dir / "run_metadata.tsv").write_text("key\tvalue\n", encoding="utf-8")

            class DummyTaskInstance:
                def xcom_pull(self, task_ids: str):
                    self.task_ids = task_ids
                    if task_ids == "pgta_pipeline.run_pgta_baseline_qc":
                        return None
                    return {"analysis_id": "PGTA_TEST", "workdir": str(workdir)}

            task_instance = DummyTaskInstance()
            artifact = bio_pgta._collect_pgta_artifact(ti=task_instance)

        self.assertEqual(task_instance.task_ids, "run_pgta_target")
        self.assertEqual(artifact["type"], "pgta_metadata")
        self.assertTrue(artifact["path"].endswith("run_metadata.tsv"))

    def test_collect_baseline_callable_reads_staged_xcom(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "PGTA_TEST"
            baseline_dir = workdir / "qc" / "baseline"
            baseline_dir.mkdir(parents=True)
            (baseline_dir / "baseline_qc_summary.tsv").write_text("sample_id\tqc_decision\n", encoding="utf-8")

            class DummyTaskInstance:
                task_ids: str | None = None

                def xcom_pull(self, task_ids: str):
                    self.task_ids = task_ids
                    if task_ids == "pgta_pipeline.run_pgta_baseline_qc":
                        return {"analysis_id": "PGTA_TEST", "workdir": str(workdir), "params": {"target": "baseline_qc"}}
                    return None

            task_instance = DummyTaskInstance()
            artifact = bio_pgta._collect_pgta_artifact(ti=task_instance)

        self.assertEqual(task_instance.task_ids, "pgta_pipeline.run_pgta_baseline_qc")
        self.assertEqual(artifact["type"], "pgta_baseline_qc")
        self.assertTrue(artifact["path"].endswith("baseline_qc_summary.tsv"))

    def test_pgta_branching_only_stages_baseline_qc_and_controlled_rerun_stage(self) -> None:
        class DummyTaskInstance:
            def __init__(self, target: str, rerun_stage: str | None = None) -> None:
                self.target = target
                self.rerun_stage = rerun_stage

            def xcom_pull(self, task_ids: str):
                self.task_ids = task_ids
                params = {"target": self.target}
                if self.rerun_stage:
                    params["rerun_stage"] = self.rerun_stage
                return {"params": params}

        for target in ("metadata", "dryrun_cnv", "invalid_target"):
            task_instance = DummyTaskInstance(target)
            self.assertEqual(bio_pgta._choose_pgta_path(ti=task_instance), "run_pgta_target")
            self.assertEqual(task_instance.task_ids, "prepare_pgta_config")

        baseline_task_instance = DummyTaskInstance("baseline_qc")
        self.assertEqual(
            bio_pgta._choose_pgta_path(ti=baseline_task_instance),
            "pgta_pipeline.run_pgta_mapping",
        )

        self.assertEqual(
            bio_pgta._choose_pgta_path(ti=DummyTaskInstance("baseline_qc", "mapping")),
            "pgta_pipeline.run_pgta_mapping",
        )
        self.assertEqual(
            bio_pgta._choose_pgta_path(ti=DummyTaskInstance("baseline_qc", "metadata")),
            "pgta_pipeline.run_pgta_metadata",
        )
        self.assertEqual(
            bio_pgta._choose_pgta_path(ti=DummyTaskInstance("baseline_qc", "baseline_qc")),
            "pgta_pipeline.run_pgta_baseline_qc",
        )


if __name__ == "__main__":
    unittest.main()
