from pathlib import Path
import unittest


class NiptS9ImageContractTests(unittest.TestCase):
    def test_wrapper_restores_airflow_control_directory_ownership_after_analysis_chown(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        wrapper = (repo_root / "nipt_s9_image" / "run_nipt_s9.sh").read_text(encoding="utf-8")

        capture = "control_owner=\"$(stat -c '%u:%g' \"$workflow_workdir/logs\")\""
        bulk_chown = 'chown -R "$chown_uid_gid" "$workflow_workdir"'
        restore = 'chown -R "$control_owner" "$workflow_workdir/$control_dir"'
        self.assertIn(capture, wrapper)
        self.assertIn(bulk_chown, wrapper)
        self.assertIn(restore, wrapper)
        self.assertLess(wrapper.index(bulk_chown), wrapper.index(restore))
        self.assertNotIn("--forceall", wrapper)

    def test_build_script_records_both_runtime_inventories_and_atomic_oci_archive(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        build_script = (repo_root / "scripts" / "build_nipt_s9_image.sh").read_text(encoding="utf-8")

        self.assertIn("snakemake9-packages.json", build_script)
        self.assertIn("analysis-python-packages.txt", build_script)
        self.assertIn("software-versions.txt", build_script)
        self.assertIn("software-manifests.sha256", build_script)
        self.assertIn("NIPT_S9_SKIP_BUILD", build_script)
        self.assertIn('archive_partial="$archive.partial"', build_script)
        self.assertIn('mv "$archive_partial" "$archive"', build_script)


if __name__ == "__main__":
    unittest.main()
