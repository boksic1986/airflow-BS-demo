import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_wes_qsub


class BioWesQsubDagTests(unittest.TestCase):
    def test_dag_id_and_task_order(self) -> None:
        dag = bio_wes_qsub.dag

        self.assertEqual(dag.dag_id, "bio_wes_qsub")
        self.assertFalse(dag.is_paused_upon_creation)
        self.assertEqual(
            set(dag.task_ids),
            {"validate_request", "prepare_wes_config", "run_wes_qsub", "collect_wes_artifacts"},
        )
        self.assertEqual(dag.get_task("validate_request").downstream_task_ids, {"prepare_wes_config"})
        self.assertEqual(dag.get_task("prepare_wes_config").downstream_task_ids, {"run_wes_qsub"})
        self.assertEqual(dag.get_task("run_wes_qsub").downstream_task_ids, {"collect_wes_artifacts"})

    def test_collect_wes_artifacts_callable_returns_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "WES_TEST"
            reports_dir = workdir / "reports"
            events_dir = workdir / "logs" / "events"
            qsub_dir = workdir / "logs" / "qsub"
            reports_dir.mkdir(parents=True)
            events_dir.mkdir(parents=True)
            qsub_dir.mkdir(parents=True)
            (reports_dir / "final_summary.tsv").write_text("sample_id\tstatus\nS001\tmock_success\n", encoding="utf-8")
            (events_dir / "snakemake_events.jsonl").write_text('{"event":"qsub_success"}\n', encoding="utf-8")
            (qsub_dir / "fastp.S001.o").write_text("ok\n", encoding="utf-8")
            (qsub_dir / "fastp.S001.e").write_text("", encoding="utf-8")

            class DummyTaskInstance:
                def xcom_pull(self, task_ids: str):
                    self.task_ids = task_ids
                    return {"analysis_id": "WES_TEST", "workdir": str(workdir)}

            task_instance = DummyTaskInstance()
            artifact = bio_wes_qsub._collect_wes_artifacts(ti=task_instance)

        self.assertEqual(task_instance.task_ids, "run_wes_qsub")
        self.assertEqual(artifact["type"], "wes_mock_summary")
        self.assertTrue(artifact["path"].endswith("final_summary.tsv"))
        self.assertEqual(artifact["event_count"], 1)
        self.assertEqual(artifact["qsub_log_count"], 2)


if __name__ == "__main__":
    unittest.main()
