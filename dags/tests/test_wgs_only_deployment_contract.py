from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


class WgsOnlyDeploymentContractTests(unittest.TestCase):
    def test_frontend_release_discards_legacy_static_assets(self):
        dockerfile = (
            REPO_ROOT / "frontend" / "Dockerfile.release"
        ).read_text(encoding="utf-8")
        cleanup = "RUN rm -rf /usr/share/nginx/html/*"
        copy = "COPY dist /usr/share/nginx/html"

        self.assertIn(cleanup, dockerfile)
        self.assertLess(dockerfile.index(cleanup), dockerfile.index(copy))

    def test_wgs_only_compose_exposes_only_safe_airflow_contracts(self):
        compose_path = REPO_ROOT / "docker-compose.wgs.yaml"
        self.assertTrue(compose_path.is_file())
        compose = compose_path.read_text(encoding="utf-8")
        self.assertIn("./dags/bio_wgs.py:/opt/airflow/dags/bio_wgs.py:ro", compose)
        for dag in ("bio_wgs_cce.py", "bio_wgs_onprem.py", "bio_wgs_intake_scan.py"):
            self.assertNotIn(f"./dags/{dag}:/opt/airflow/dags/{dag}:ro", compose)
            self.assertFalse((REPO_ROOT / "dags" / dag).exists())
        for required in ("wgs_cce_runs 4", "wgs_obs_transfer 1", "DEPLOYED_PIPELINES: wgs", 'WGS_EXECUTION_ENABLED: "${WGS_EXECUTION_ENABLED:-false}"', 'WGS_RUNTIME_ADAPTER_ENABLED: "${WGS_RUNTIME_ADAPTER_ENABLED:-false}"', 'WGS_INTAKE_SCAN_ENABLED: "${WGS_INTAKE_SCAN_ENABLED:-true}"', 'WGS_AUTO_DISPATCH_ENABLED: "${WGS_AUTO_DISPATCH_ENABLED:-false}"', "WGS_SSH_CONFIG_PATH"):
            self.assertIn(required, compose)
        self.assertIn(
            'PLATFORM_ENVIRONMENT: "${PLATFORM_ENVIRONMENT:-Demo}"', compose
        )
        self.assertIn(
            'WGS_RUNTIME_BS_ROOT: ${WGS_RUNTIME_BS_ROOT:-/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime}',
            compose,
        )
        self.assertIn(
            "AIRFLOW__WEBSERVER__SECRET_KEY: ${AIRFLOW_WEBSERVER_SECRET_KEY:?set AIRFLOW_WEBSERVER_SECRET_KEY}",
            compose,
        )
        self.assertIn('${WGS_RUNNER_200_ALIAS:-wgs-node200}', compose)
        self.assertNotIn("AIRFLOW_CONN_WGS_RUNNER_200", compose)
        self.assertIn('${WGS_RUNTIME_HOST_ROOT:?set WGS_RUNTIME_HOST_ROOT}:/data/wgs-runtime', compose)
        self.assertIn('/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime', compose)
        for excluded in ("/var/run/docker.sock", "bio_nipt", "bio_pgta", "bio_wes", "NIPT_", "PGTA_", "WES_", "./pipelines", "./profiles", "KUBECONFIG", "OBS_"):
            self.assertNotIn(excluded, compose)

    def test_wgs_only_examples_keep_credentials_out_and_define_modes(self):
        env = (REPO_ROOT / ".env.wgs.example").read_text(encoding="utf-8")
        intake = (REPO_ROOT / "config" / "intake.wgs.yaml").read_text(encoding="utf-8")
        profiles = (REPO_ROOT / "config" / "pipeline_profiles.wgs.yaml").read_text(encoding="utf-8")
        self.assertNotIn("KUBECONFIG", env)
        self.assertNotIn("OBS_", env)
        self.assertIn("WGS_EXECUTION_ENABLED=false", env)
        self.assertIn("WGS_RUNTIME_UID=1000", env)
        self.assertIn("PLATFORM_ENVIRONMENT=Demo", env)
        self.assertIn(
            "WGS_RUNTIME_BS_ROOT=/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime",
            env,
        )
        self.assertIn("AIRFLOW_WEBSERVER_SECRET_KEY=<CHANGE_ME_LOCAL_ONLY>", env)
        self.assertIn("WGS_RUNNER_200_HOST=172.17.61.200", env)
        self.assertIn("WGS_RUNNER_200_ALIAS=wgs-node200", env)
        self.assertIn("wgs:", intake)
        self.assertIn("mode: t7_scan_only", intake)
        self.assertIn("root: /bi/fastq/T7_Fastq", intake)
        self.assertIn("interval_seconds: 1800", intake)
        self.assertIn("auto_dispatch_enabled: false", intake)
        self.assertIn("wgs-cce-v1", profiles)
        self.assertIn("wgs-onprem-v1", profiles)

    def test_backend_writes_wgs_roots_as_the_runtime_owner(self):
        payload = yaml.safe_load(
            (REPO_ROOT / "docker-compose.wgs.yaml").read_text(encoding="utf-8")
        )

        self.assertEqual(
            payload["services"]["backend"]["user"],
            "${WGS_RUNTIME_UID:?set WGS_RUNTIME_UID}:${WGS_RUNTIME_SHARED_GID:-520}",
        )

    def test_scanner_and_run_observer_are_isolated_unprivileged_services(self):
        compose_path = REPO_ROOT / "docker-compose.wgs.yaml"
        payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        observer = payload["services"]["wgs-run-observer"]
        scanner = payload["services"]["wgs-intake-scanner"]

        self.assertEqual(
            scanner["command"][-1],
            "${WGS_INTAKE_SCAN_INTERVAL_SECONDS:-600}",
        )

        for service in (observer, scanner):
            rendered = str(service)
            self.assertNotIn("ports", service)
            self.assertNotEqual(service.get("network_mode"), "host")
            self.assertFalse(service.get("privileged", False))
            self.assertNotIn("cap_add", service)
            for forbidden in ("KUBECONFIG", "OBS_", "SSH_", "docker.sock"):
                self.assertNotIn(forbidden, rendered)
            self.assertEqual(
                service["logging"],
                {"driver": "json-file", "options": {"max-size": "20m", "max-file": "3"}},
            )

        observer_rendered = str(observer)
        self.assertIn("/data/wgs-evidence:ro", observer_rendered)
        for forbidden in (
            "WGS_BINDING_ROOT",
            "WGS_TRANSFER_SPOOL_ROOT",
            "WGS_RUNTIME_ROOT",
            "WGS_T7_FASTQ_ROOT",
            "/config/wgs-bindings",
            "/data/wgs-runtime",
            "/bi/fastq/T7_Fastq",
        ):
            self.assertNotIn(forbidden, observer_rendered)
        self.assertEqual(
            observer["command"],
            ["python", "-m", "app.wgs_observer_cli", "--evidence-root", "/data/wgs-evidence", "--interval", "5"],
        )

        scanner_rendered = str(scanner)
        self.assertIn(
            "${WGS_T7_FASTQ_HOST_ROOT:-/bi/fastq/T7_Fastq}:/bi/fastq/T7_Fastq:ro",
            scanner["volumes"],
        )
        for forbidden in ("/data/wgs-evidence", "/config/wgs-bindings", "/data/wgs-runtime"):
            self.assertNotIn(forbidden, scanner_rendered)
        self.assertEqual(scanner["environment"]["WGS_INTAKE_SCAN_ENABLED"], "${WGS_INTAKE_SCAN_ENABLED:-true}")
        self.assertEqual(scanner["environment"]["WGS_INTAKE_SCAN_INTERVAL_SECONDS"], "${WGS_INTAKE_SCAN_INTERVAL_SECONDS:-600}")
        self.assertEqual(scanner["environment"]["WGS_AUTO_DISPATCH_ENABLED"], "${WGS_AUTO_DISPATCH_ENABLED:-false}")
        self.assertEqual(scanner["environment"]["WGS_BACKEND_INTERNAL_URL"], "http://backend:8000")
        self.assertEqual(
            payload["services"]["backend"]["environment"]["WGS_AUTO_DISPATCH_NOT_BEFORE"],
            "${WGS_AUTO_DISPATCH_NOT_BEFORE:-}",
        )

    def test_all_long_lived_wgs_services_have_bounded_docker_logs(self):
        payload = yaml.safe_load(
            (REPO_ROOT / "docker-compose.wgs.yaml").read_text(encoding="utf-8")
        )
        expected = {
            "driver": "json-file",
            "options": {"max-size": "20m", "max-file": "3"},
        }
        for service_name in (
            "postgres",
            "redis",
            "backend",
            "wgs-run-observer",
            "platform-node-probe",
            "platform-metrics-collector",
            "wgs-intake-scanner",
            "airflow-api-server",
            "airflow-scheduler",
            "airflow-worker",
            "frontend-nginx",
        ):
            self.assertEqual(
                payload["services"][service_name].get("logging"),
                expected,
                service_name,
            )

    def test_platform_node_probe_owns_ssh_and_collector_owns_database(self):
        payload = yaml.safe_load(
            (REPO_ROOT / "docker-compose.wgs.yaml").read_text(encoding="utf-8")
        )
        probe = payload["services"]["platform-node-probe"]
        collector = payload["services"]["platform-metrics-collector"]

        self.assertNotIn("DATABASE_URL", probe.get("environment", {}))
        self.assertEqual(
            probe["user"],
            "${AIRFLOW_UID:-1000}:${WGS_RUNTIME_SHARED_GID:-520}",
        )
        self.assertNotIn("ports", probe)
        self.assertFalse(probe.get("privileged", False))
        self.assertIn("/opt/platform-metrics/ssh:ro", str(probe["volumes"]))
        self.assertIn("/data/wgs-runtime", str(probe["volumes"]))
        self.assertIn("PLATFORM_NODE_METRICS_SPOOL", collector["environment"])
        self.assertNotIn("PLATFORM_NODE_EXPORTER_TARGETS", collector["environment"])
        self.assertNotIn("/opt/platform-metrics/ssh", str(collector.get("volumes", [])))

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
