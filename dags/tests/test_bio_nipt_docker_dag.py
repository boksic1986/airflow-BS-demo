import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_nipt_docker


class BioNiptDockerDagTests(unittest.TestCase):
    def test_dag_id_and_task_order(self) -> None:
        dag = bio_nipt_docker.dag

        self.assertEqual(dag.dag_id, "bio_nipt_docker")
        self.assertFalse(dag.is_paused_upon_creation)
        self.assertEqual(
            set(dag.task_ids),
            {"validate_request", "prepare_nipt_docker_run", "run_nipt_docker", "collect_nipt_artifacts"},
        )
        self.assertEqual(dag.get_task("validate_request").downstream_task_ids, {"prepare_nipt_docker_run"})
        self.assertEqual(dag.get_task("prepare_nipt_docker_run").downstream_task_ids, {"run_nipt_docker"})
        self.assertEqual(dag.get_task("run_nipt_docker").downstream_task_ids, {"collect_nipt_artifacts"})

    def test_collect_nipt_artifacts_callable_returns_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "NIPT_TEST"
            reports_dir = workdir / "reports"
            logs_dir = workdir / "logs"
            config_dir = workdir / "config"
            reports_dir.mkdir(parents=True)
            logs_dir.mkdir(parents=True)
            config_dir.mkdir(parents=True)
            (reports_dir / "qc_summary.tsv").write_text(
                "sample_id\tmetric_name\tmetric_value\tmetric_numeric\tthreshold\tstatus\n"
                "NC-20260414.A01\tQ30\t93.2\t93.2\t>=85\tpass\n",
                encoding="utf-8",
            )
            (logs_dir / "snakemake.stdout.log").write_text("stdout\n", encoding="utf-8")
            (logs_dir / "snakemake.stderr.log").write_text("", encoding="utf-8")
            (config_dir / "nipt_docker_compose.yml").write_text("services: {}\n", encoding="utf-8")
            (config_dir / "nipt_run_config.yaml").write_text("chip_name: demo\n", encoding="utf-8")

            class DummyTaskInstance:
                def xcom_pull(self, task_ids: str):
                    self.task_ids = task_ids
                    return {"analysis_id": "NIPT_TEST", "workdir": str(workdir)}

            task_instance = DummyTaskInstance()
            artifact = bio_nipt_docker._collect_nipt_artifacts(ti=task_instance)

        self.assertEqual(task_instance.task_ids, "run_nipt_docker")
        self.assertEqual(artifact["type"], "nipt_docker_summary")
        self.assertTrue(artifact["qc_path"].endswith("reports/qc_summary.tsv"))
        self.assertEqual(artifact["qc_metric_count"], 1)
        self.assertTrue(artifact["compose_path"].endswith("config/nipt_docker_compose.yml"))


if __name__ == "__main__":
    unittest.main()
