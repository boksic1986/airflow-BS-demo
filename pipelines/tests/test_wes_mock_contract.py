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


if __name__ == "__main__":
    unittest.main()
