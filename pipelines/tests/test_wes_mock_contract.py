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
        self.assertIn("/biosoftware/miniconda/envs/snakemake_env/bin/python", text)
        self.assertIn("pipelines/common/qsub_submit.py", text)
        self.assertNotIn("forceall", text.lower())


if __name__ == "__main__":
    unittest.main()
