from pathlib import Path
import unittest

import yaml


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

    def test_observer_is_read_only_unprivileged_and_has_no_external_credentials(self):
        compose_path = REPO_ROOT / "docker-compose.wgs.yaml"
        payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        observer = payload["services"]["wgs-observer"]
        rendered = str(observer)

        self.assertNotIn("ports", observer)
        self.assertNotEqual(observer.get("network_mode"), "host")
        self.assertFalse(observer.get("privileged", False))
        self.assertNotIn("cap_add", observer)
        for forbidden in ("KUBECONFIG", "OBS_", "SSH_", "docker.sock"):
            self.assertNotIn(forbidden, rendered)
        self.assertEqual(observer["environment"]["WGS_EXECUTION_ENABLED"], "false")
        volumes = observer["volumes"]
        self.assertTrue(any("/data/wgs-evidence:ro" in item for item in volumes))
        self.assertTrue(any("/config/wgs-bindings:ro" in item for item in volumes))
        self.assertTrue(any("/config/wgs_releases.yaml:ro" in item for item in volumes))
        command = " ".join(observer["command"])
        self.assertIn("--binding-root /config/wgs-bindings", command)
        self.assertIn("--catalog /config/wgs_releases.yaml", command)

    def test_bs10610_network_and_host_binding_are_immutable_contracts(self):
        payload = yaml.safe_load((REPO_ROOT / "docker-compose.wgs.yaml").read_text(encoding="utf-8"))
        network = payload["networks"]["wgs-platform"]
        self.assertTrue(network["external"])
        self.assertEqual(network["name"], "nipt_analysis_test_net")
        self.assertEqual(
            payload["services"]["frontend-nginx"]["ports"],
            ["${BS_HOST_IP:-172.17.106.10}:${FRONTEND_PORT:-12959}:80"],
        )
        for name, service in payload["services"].items():
            if name != "frontend-nginx":
                self.assertNotIn("ports", service)

        preflight = (REPO_ROOT / "scripts" / "check_wgs_docker_network.py").read_text(encoding="utf-8")
        self.assertIn('EXPECTED_SUBNET = "192.168.199.0/24"', preflight)
        self.assertIn('EXPECTED_GATEWAY = "192.168.199.1"', preflight)
