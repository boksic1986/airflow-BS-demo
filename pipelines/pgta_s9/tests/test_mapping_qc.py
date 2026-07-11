from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "collect_mapping_qc.py"
SPEC = importlib.util.spec_from_file_location("pgta_s9_collect_mapping_qc", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PgtaS9MappingQcTests(unittest.TestCase):
    def test_stats_value_ignores_samtools_comment_column(self) -> None:
        stats = "SN\tbases mapped (cigar):\t247289585\t# more accurate\n"

        self.assertEqual(MODULE._stats_value(stats, "bases mapped (cigar)"), 247289585.0)


if __name__ == "__main__":
    unittest.main()
