import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bio_intake_scan


class BioIntakeScanDagTests(unittest.TestCase):
    def test_dag_id_and_task(self) -> None:
        dag = bio_intake_scan.dag

        self.assertEqual(dag.dag_id, "bio_intake_scan")
        self.assertEqual(set(dag.task_ids), {"scan_and_submit"})
        self.assertTrue(dag.is_paused_upon_creation)

    def test_run_intake_scan_posts_configured_payload(self) -> None:
        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"items":[]}'

        class DummyDagRun:
            conf = {"pipelines": ["nipt_docker"], "bootstrap": True, "max_samples": 12}

        with patch.dict(os.environ, {"BACKEND_BASE_URL": "http://backend:8000", "INTAKE_SCAN_TIMEOUT_SECONDS": "5"}):
            with patch("bio_intake_scan.urlopen", return_value=DummyResponse()) as mocked_urlopen:
                result = bio_intake_scan.run_intake_scan(dag_run=DummyDagRun())

        self.assertEqual(result, {"items": []})
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://backend:8000/api/intake/scan-and-submit")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"pipelines": ["nipt_docker"], "bootstrap": True, "max_samples": 12})


if __name__ == "__main__":
    unittest.main()
