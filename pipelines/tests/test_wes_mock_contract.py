from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class WesMockContractTests(unittest.TestCase):
    def test_wes_mock_snakefile_defines_minimal_rule_chain_with_logs(self) -> None:
        snakefile = REPO_ROOT / "pipelines" / "wes" / "workflow" / "Snakefile"

        text = snakefile.read_text(encoding="utf-8")

        for rule in ("all", "fastp", "bwa_mem", "markdup", "final_summary"):
            self.assertIn(f"rule {rule}:", text)
        self.assertIn('"logs", "rules", "fastp"', text)
        self.assertIn('"logs", "rules", "bwa_mem"', text)
        self.assertIn('"logs", "rules", "markdup"', text)
        self.assertIn('"logs", "rules", "final_summary"', text)
        self.assertNotIn("--forceall", text)

    def test_qsub_profile_is_mock_safe_and_limited(self) -> None:
        profile = REPO_ROOT / "profiles" / "qsub" / "config.yaml"

        text = profile.read_text(encoding="utf-8")

        self.assertIn("executor: cluster-generic", text)
        self.assertIn("jobs: 2", text)
        self.assertIn("rerun-incomplete: true", text)
        self.assertIn("AIRFLOW_DEMO_QSUB_MODE=mock", text)
        self.assertIn("${{AIRFLOW_DEMO_QSUB_PYTHON:-python}}", text)
        self.assertIn("pipelines/common/qsub_submit.py", text)
        self.assertNotIn("forceall", text.lower())

    def test_snakemake_runner_image_pins_required_dependencies(self) -> None:
        dockerfile = REPO_ROOT / "snakemake_runner" / "Dockerfile"
        requirements = REPO_ROOT / "snakemake_runner" / "requirements.txt"

        dockerfile_text = dockerfile.read_text(encoding="utf-8")
        requirements_text = requirements.read_text(encoding="utf-8")

        self.assertIn("FROM python:3.12-slim", dockerfile_text)
        self.assertIn("COPY pip.conf /etc/pip.conf", dockerfile_text)
        self.assertIn("snakemake==9.23.1", requirements_text)
        self.assertIn("snakemake-executor-plugin-cluster-generic==1.0.9", requirements_text)

    def test_compose_defines_run_only_snakemake_runner_service(self) -> None:
        compose = REPO_ROOT / "docker-compose.yaml"

        text = compose.read_text(encoding="utf-8")

        self.assertIn("snakemake-runner:", text)
        self.assertIn("image: ${SNAKEMAKE_RUNNER_IMAGE:-airflow-demo/snakemake-runner:0.1.0}", text)
        self.assertIn("context: ./snakemake_runner", text)
        self.assertIn("./shared:/data/airflow-demo", text)
        self.assertIn(".:/app:ro", text)
        self.assertIn("target: /app/.snakemake", text)
        self.assertNotIn("12960:", text)

    def test_airflow_project_image_pins_snakemake_runtime_for_wes_dag(self) -> None:
        dockerfile = REPO_ROOT / "airflow_image" / "Dockerfile"
        requirements = REPO_ROOT / "airflow_image" / "requirements.txt"
        compose = REPO_ROOT / "docker-compose.yaml"

        dockerfile_text = dockerfile.read_text(encoding="utf-8")
        requirements_text = requirements.read_text(encoding="utf-8")
        compose_text = compose.read_text(encoding="utf-8")

        self.assertIn("FROM apache/airflow:2.9.3-python3.11", dockerfile_text)
        self.assertIn("COPY pip.conf /etc/pip.conf", dockerfile_text)
        self.assertIn("/opt/airflow/snakemake-venv/bin/pip", dockerfile_text)
        self.assertIn('PATH="/opt/airflow/snakemake-venv/bin:${PATH}"', dockerfile_text)
        self.assertNotIn("RUN pip install", dockerfile_text)
        self.assertIn("snakemake==9.23.1", requirements_text)
        self.assertIn("snakemake-executor-plugin-cluster-generic==1.0.9", requirements_text)
        self.assertIn("image: ${AIRFLOW_IMAGE:-airflow-demo/airflow:0.1.0}", compose_text)
        self.assertIn("context: ./airflow_image", compose_text)
        self.assertIn("./pipelines:/opt/airflow/pipelines:ro", compose_text)
        self.assertIn("./profiles:/opt/airflow/profiles:ro", compose_text)

    def test_airflow_uid_matches_fengxian_shared_owner_by_default(self) -> None:
        compose = REPO_ROOT / "docker-compose.yaml"
        env_example = REPO_ROOT / ".env.example"
        runbook = REPO_ROOT / "docs" / "11_DEPLOYMENT_RUNBOOK.md"

        compose_text = compose.read_text(encoding="utf-8")
        env_text = env_example.read_text(encoding="utf-8")
        runbook_text = runbook.read_text(encoding="utf-8")

        self.assertIn('user: "${AIRFLOW_UID:-1005}:0"', compose_text)
        self.assertIn("AIRFLOW_UID=1005", env_text)
        self.assertIn("AIRFLOW_UID=$(id -u)", runbook_text)
        self.assertNotIn("AIRFLOW_UID=50000", env_text)


if __name__ == "__main__":
    unittest.main()
