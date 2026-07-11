from __future__ import annotations

from pathlib import Path
import unittest


class PgtaS9PredictContractTests(unittest.TestCase):
    def test_predict_command_uses_only_supported_wisecondorx_flags(self) -> None:
        rule_text = (
            Path(__file__).parents[1] / "rules" / "predict_workflow.smk"
        ).read_text(encoding="utf-8")

        self.assertNotIn("--cpus", rule_text)
        self.assertIn("--seed {params.seed}", rule_text)
        self.assertIn("_statistics.txt", rule_text)


if __name__ == "__main__":
    unittest.main()
