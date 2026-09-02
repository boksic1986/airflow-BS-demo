from pathlib import Path

import pytest

from app.wgs_release_catalog import load_wgs_release_catalog


RELEASE_ID = "wgs-4.2.0-7879718"
WGS_COMMIT = "78797181ee0582bea3167385c243616017f092ce"


def write_catalog(tmp_path: Path, **overrides: str) -> Path:
    values = {
        "release_id": RELEASE_ID,
        "version": "V4.2.0",
        "source_commit": WGS_COMMIT,
        "bs10610_repo_path": "/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0",
        "node200_repo_path": "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0",
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
    assert release.version == "V4.2.0"
    assert release.source_commit == WGS_COMMIT
    assert release.bs10610_repo_path.endswith("/project/wgs-4.2.0")
    assert release.node200_repo_path.endswith("/project/wgs-4.2.0")
    assert release.rule_event_schema_version == "1"
    assert not hasattr(release, "cce_pipeline_version")
    assert not hasattr(release, "snapshot_manifest_sha256")


def test_catalog_rejects_old_snapshot_or_multiple_release_shape(tmp_path: Path) -> None:
    path = tmp_path / "wgs_releases.yaml"
    path.write_text('schema_version: "2"\nsnapshots: []\n', encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version must be 3"):
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
            write_catalog(tmp_path, release_id="wgs-4.2.0-deadbee")
        )


def test_checked_in_catalog_pins_current_wgs_repository_only() -> None:
    catalog = load_wgs_release_catalog(
        Path(__file__).resolve().parents[2] / "config" / "wgs_releases.yaml"
    )

    assert catalog.release.release_id == RELEASE_ID
    assert catalog.release.source_commit == WGS_COMMIT
    assert catalog.release.bs10610_repo_path == (
        "/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0"
    )
    assert catalog.release.node200_repo_path == (
        "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0"
    )
