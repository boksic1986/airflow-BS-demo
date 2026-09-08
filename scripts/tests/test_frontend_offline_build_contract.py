from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class FrontendOfflineBuildContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_builder_base_is_lockfile_bound(self) -> None:
        dockerfile = self.read("frontend/Dockerfile.builder-base")

        self.assertIn("ARG NODE_IMAGE=node:22-bookworm", dockerfile)
        self.assertIn("COPY package.json package-lock.json ./", dockerfile)
        self.assertIn("RUN npm ci", dockerfile)
        self.assertIn("io.airflow-demo.frontend.lock-sha256", dockerfile)
        self.assertIn("io.airflow-demo.frontend.node-major", dockerfile)

    def test_offline_source_build_reuses_dependencies(self) -> None:
        dockerfile = self.read("frontend/Dockerfile.offline-build")

        self.assertIn("ARG FRONTEND_BUILDER_IMAGE", dockerfile)
        self.assertIn("FROM ${FRONTEND_BUILDER_IMAGE} AS source", dockerfile)
        self.assertIn("RUN npm test -- --run", dockerfile)
        self.assertIn("RUN npm run build", dockerfile)
        self.assertNotIn("npm ci", dockerfile)

    def test_bs_build_is_network_isolated_and_never_pulls(self) -> None:
        script = self.read("scripts/build_frontend_offline.sh")

        self.assertGreaterEqual(script.count("--network none"), 3)
        self.assertGreaterEqual(script.count("--pull=false"), 3)
        self.assertNotIn("docker pull", script)
        self.assertIn("io.airflow-demo.frontend.lock-sha256", script)
        self.assertIn("Dockerfile.runtime-overlay", script)
        self.assertIn("FRONTEND_SOURCE_COMMIT", script)
        self.assertIn("nginx-1.30.3-local-contract", script)
        self.assertNotIn("t233-contract", script)

    def test_runtime_overlay_removes_previous_static_assets(self) -> None:
        dockerfile = self.read("frontend/Dockerfile.runtime-overlay")

        remove_index = dockerfile.index("RUN rm -rf /usr/share/nginx/html/*")
        copy_index = dockerfile.index("COPY dist/ /usr/share/nginx/html/")
        self.assertLess(remove_index, copy_index)

    def test_one_time_builder_export_records_checksums(self) -> None:
        script = self.read("scripts/build_frontend_builder_base.sh")

        self.assertIn("Dockerfile.builder-base", script)
        self.assertIn("docker save", script)
        self.assertIn("sha256sum", script)
        self.assertIn('(cd "${OUTPUT_DIR}" && sha256sum "${ARCHIVE_BASENAME}"', script)
        self.assertIn("FRONTEND_SOURCE_COMMIT", script)
        self.assertNotIn("docker pull", script)


if __name__ == "__main__":
    unittest.main()
