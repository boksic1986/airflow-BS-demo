from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class BsSharedDeploymentContractTests(unittest.TestCase):
    def test_compose_reuses_one_nipt_and_wgs_control_plane(self) -> None:
        compose = (REPO_ROOT / "docker-compose.bs-nipt.yaml").read_text(encoding="utf-8")

        self.assertIn("name: ${COMPOSE_PROJECT_NAME:-airflow-nipt}", compose)
        self.assertIn("DEPLOYED_PIPELINES: nipt_docker,wgs", compose)
        self.assertIn("NIPT_AIRFLOW_POOL: bs_heavy_analysis", compose)
        self.assertIn("WGS_AIRFLOW_POOL: bs_heavy_analysis", compose)
        self.assertIn("airflow pools set bs_heavy_analysis 1", compose)
        self.assertIn("./dags/bio_nipt_docker.py:/opt/airflow/dags/bio_nipt_docker.py:ro", compose)
        self.assertIn("./dags/bio_wgs.py:/opt/airflow/dags/bio_wgs.py:ro", compose)
        self.assertNotIn("airflow-wgs", compose)
        self.assertNotIn("13958", compose)
        self.assertNotIn("13959", compose)

    def test_example_env_reuses_the_accepted_compose_project(self) -> None:
        example = (REPO_ROOT / ".env.bs-nipt.example").read_text(encoding="utf-8")

        self.assertIn("COMPOSE_PROJECT_NAME=airflow-nipt", example)
        self.assertIn("WGS_PROJECT_ROOT=", example)
        self.assertIn("WGS_RESULTS_HOST_ROOT=", example)

    def test_preflight_uses_the_same_default_project_name(self) -> None:
        preflight = (REPO_ROOT / "scripts" / "bs_nipt_preflight.sh").read_text(encoding="utf-8")

        self.assertIn('COMPOSE_PROJECT_NAME:-airflow-nipt', preflight)
        self.assertNotIn("airflow-bs-control", preflight)

    def test_nginx_allows_the_operator_workstation_subnet(self) -> None:
        nginx = (REPO_ROOT / "frontend" / "nginx.bs-nipt.conf").read_text(encoding="utf-8")

        self.assertEqual(nginx.count("allow 172.20.8.0/24;"), 2)
        self.assertEqual(nginx.count("deny all;"), 2)


if __name__ == "__main__":
    unittest.main()
