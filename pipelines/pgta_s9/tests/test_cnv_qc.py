from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SPEC = importlib.util.spec_from_file_location("pgta_s9_cnv_qc", SCRIPTS_DIR / "cnv_qc.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PgtaS9CnvQcTests(unittest.TestCase):
    def test_load_primary_array_flattens_wisecondorx_sample_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            npz_path = Path(tmpdir) / "sample.npz"
            sample = {
                "1": np.arange(150, dtype=np.int32),
                "2": np.arange(80, dtype=np.int32),
                "23": np.arange(20, dtype=np.int32),
            }
            np.savez(npz_path, binsize=1_000_000, sample=sample, quality={})

            key, values = MODULE.load_primary_array(npz_path)

            self.assertEqual(key, "sample_dict_chr1_22")
            self.assertEqual(values.size, 230)
            self.assertEqual(float(values.sum()), 14_335.0)


if __name__ == "__main__":
    unittest.main()
