"""Regression check: auxiliary DAGs must not register the main DAG twice."""

import os
from pathlib import Path
import unittest

from airflow.models import DagBag


class DagDiscoveryTests(unittest.TestCase):
    def test_main_dags_have_one_discovery_owner(self):
        dag_folder = os.environ.get(
            "DAGS_ROOT", str(Path(__file__).resolve().parents[1])
        )
        bag = DagBag(dag_folder=dag_folder, include_examples=False, safe_mode=False)

        self.assertEqual({}, bag.import_errors)
        self.assertEqual("bio_wgs.py", Path(bag.dags["bio_wgs"].fileloc).name)
        self.assertEqual("bio_gatk.py", Path(bag.dags["bio_gatk"].fileloc).name)


if __name__ == "__main__":
    unittest.main()
