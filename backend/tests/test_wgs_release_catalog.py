from pathlib import Path

import pytest

from app.wgs_release_catalog import load_wgs_release_catalog


RELEASE_ID = "wgs-4.1.1-6c98281"
WGS_COMMIT = "6c982817614db6a1157b6f287427ddf01ac91827"


def write_catalog(tmp_path: Path, **overrides: str) -> Path:
    values = {
        "release_id": RELEASE_ID,
        "version": "V4.1.1",
        "source_commit": WGS_COMMIT,
        "bs10610_repo_path": "/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1",
        "node200_repo_path": "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1",
        "rule_event_schema_version": "1",
        **overrides,
    }
    path = tmp_path / "wgs_releases.yaml"
    path.write_text(
        "schema_version: \"3\"\n"
        "release:\n"
        + "".join(f"  {key}: {value}\n" for key, value in values.items()),
        encoding="utf-8",
    )
    return path


def test_catalog_loads_one_shared_wgs_release_without_cce_gate(tmp_path: Path) -> None:
    release = load_wgs_release_catalog(write_catalog(tmp_path)).release

    assert release.release_id == RELEASE_ID
    assert release.version == "V4.1.1"
    assert release.source_commit == WGS_COMMIT
    assert release.bs10610_repo_path.endswith("/project/wgs-4.1.1")
    assert release.node200_repo_path.endswith("/project/wgs-4.1.1")
    assert release.rule_event_schema_version == "1"
    assert release.cce_pipeline_version is None
    assert not hasattr(release, "snapshot_manifest_sha256")


def test_schema4_catalog_selects_current_and_resolves_historical_release(tmp_path: Path) -> None:
    path = tmp_path / "wgs_releases.yaml"
    path.write_text(
        """schema_version: "4"
current_release_id: wgs-4.2.0-b067c72
releases:
  - release_id: wgs-4.2.0-b067c72
    version: V4.2.0
    source_commit: b067c72eed795e59b724b13324b0d380ae8b7e94
    bs10610_repo_path: /mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0
    node200_repo_path: /bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0
    rule_event_schema_version: "1"
    profile_id: wgs-4.2.0
    profile_revision: r1
    profile_sha256: c6dea31fb06f8a1c0ac242cea8fa990486d631f877d64a6f8d25b67dadfa8511
    node200_profile_path: /bi/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs/wgs-4.2.0-r1.yaml
    cce_pipeline_version: 0.8.3
    pipeline_build_sha256: 71695b2a3ab1d83bab68454b1785d2b6791b26c6f57f5ecceda465975788b7f6
    resource_manifest_sha256: 89ea682efe61f6a0202c41b01cdc10de2355dcc496834a61513d357d86a2b049
  - release_id: wgs-4.1.1-6c98281
    version: V4.1.1
    source_commit: 6c982817614db6a1157b6f287427ddf01ac91827
    bs10610_repo_path: /mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1
    node200_repo_path: /bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1
    rule_event_schema_version: "1"
""",
        encoding="utf-8",
    )

    catalog = load_wgs_release_catalog(path)

    assert catalog.release.release_id == "wgs-4.2.0-b067c72"
    assert catalog.release.profile_id == "wgs-4.2.0"
    assert catalog.release.cce_pipeline_version == "0.8.3"
    assert catalog.release.node200_profile_path.endswith("/wgs-4.2.0-r1.yaml")
    assert catalog.release.pipeline_build_sha256 == (
        "71695b2a3ab1d83bab68454b1785d2b6791b26c6f57f5ecceda465975788b7f6"
    )
    assert catalog.by_id("wgs-4.1.1-6c98281").version == "V4.1.1"
    with pytest.raises(ValueError, match="not cataloged"):
        catalog.by_id("wgs-4.0.0-deadbee")



def test_catalog_rejects_old_snapshot_or_multiple_release_shape(tmp_path: Path) -> None:
    path = tmp_path / "wgs_releases.yaml"
    path.write_text('schema_version: "2"\nsnapshots: []\n', encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version must be 3 or 4"):
        load_wgs_release_catalog(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("release_id", "../../wgs", "release_id"),
        ("source_commit", "ade88f9", "source_commit"),
        ("bs10610_repo_path", "/tmp/wgs", "BS10610"),
        ("node200_repo_path", "/tmp/wgs", "node200"),
        ("rule_event_schema_version", "2", "Rule event"),
    ],
)
def test_catalog_rejects_invalid_release_contract(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        load_wgs_release_catalog(write_catalog(tmp_path, **{field: value}))


def test_catalog_rejects_release_id_that_does_not_match_commit(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="release_id commit prefix"):
        load_wgs_release_catalog(
            write_catalog(tmp_path, release_id="wgs-4.1.1-deadbee")
        )


def test_checked_in_catalog_pins_421_and_retains_frozen_history() -> None:
    catalog = load_wgs_release_catalog(
        Path(__file__).resolve().parents[2] / "config" / "wgs_releases.yaml"
    )

    assert catalog.release.release_id == "wgs-4.2.1-cc9bde3"
    assert catalog.release.source_commit == "cc9bde3c8ee6ad1cd2f85cf5d2ef49c5611ac081"
    assert catalog.release.bs10610_repo_path == (
        "/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0"
    )
    assert catalog.release.node200_repo_path == (
        "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0"
    )
    assert catalog.release.profile_sha256 == (
        "44d7398fd8fb1123220f15a0cef6480289a845c49f97b23b0231c30de9bd74ab"
    )
    assert catalog.release.version == 'V4.2.1'
    assert catalog.by_id('wgs-4.2.0-31de5fb').profile_revision == 'r2'
    assert catalog.by_id(RELEASE_ID).source_commit == WGS_COMMIT
