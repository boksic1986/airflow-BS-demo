from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class WgsOnlyDeploymentContractTests(unittest.TestCase):
    def test_wgs_only_compose_exposes_only_safe_airflow_contracts(self):
        compose_path = REPO_ROOT / "docker-compose.wgs.yaml"
        self.assertTrue(compose_path.is_file())
        compose = compose_path.read_text(encoding="utf-8")
        for dag in ("bio_wgs_cce.py", "bio_wgs_onprem.py", "bio_wgs_intake_scan.py"):
            self.assertIn(f"./dags/{dag}:/opt/airflow/dags/{dag}:ro", compose)
        for required in ("wgs_cce_runs 4", "wgs_obs_transfer 1", "DEPLOYED_PIPELINES: wgs", "INTAKE_SCAN_PIPELINES: wgs", 'WGS_EXECUTION_ENABLED: "false"'):
            self.assertIn(required, compose)
        for excluded in ("/var/run/docker.sock", "bio_nipt", "bio_pgta", "bio_wes", "NIPT_", "PGTA_", "WES_", "./pipelines", "./profiles", "KUBECONFIG", "OBS_"):
            self.assertNotIn(excluded, compose)

    def test_wgs_only_examples_keep_credentials_out_and_define_modes(self):
        env = (REPO_ROOT / ".env.wgs.example").read_text(encoding="utf-8")
        intake = (REPO_ROOT / "config" / "intake.wgs.yaml").read_text(encoding="utf-8")
        profiles = (REPO_ROOT / "config" / "pipeline_profiles.wgs.yaml").read_text(encoding="utf-8")
        self.assertNotIn("KUBECONFIG", env)
        self.assertNotIn("OBS_", env)
        self.assertIn("WGS_EXECUTION_ENABLED=false", env)
        self.assertIn("wgs:", intake)
        self.assertIn("*.wgs.yaml", intake)
        self.assertIn("wgs-cce-v1", profiles)
        self.assertIn("wgs-onprem-v1", profiles)
