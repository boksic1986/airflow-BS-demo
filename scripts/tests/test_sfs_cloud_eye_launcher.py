from pathlib import Path


def test_sfs_collector_launcher_is_bounded_and_deduplicated() -> None:
    source = (
        Path(__file__).parents[1] / "start_sfs_cloud_eye_collector.sh"
    ).read_text(encoding="utf-8")
    assert "flock -n" in source
    assert "kill -0" in source
    assert "--interval-seconds 60" in source
    assert "sfs-cloud-eye.error.log" in source
    assert "sfs_api.credentials" not in source
    assert "SFS_CLOUD_EYE_CREDENTIALS:?" in source
    assert "HWC_PROJECT_ID:?" in source
    assert "SFS_CLOUD_EYE_RESOURCE_ID:?" in source
    assert "credentials must use mode 600" in source
    assert "10485760" in source
