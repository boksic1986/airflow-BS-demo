from pathlib import Path

import pytest

from app.wgs_release_catalog import load_snapshot_catalog


def write_catalog(
    tmp_path: Path,
    *,
    status: str = "development",
    execution_enabled: bool = False,
) -> Path:
    path = tmp_path / "wgs_releases.yaml"
    path.write_text(
        f"""\
schema_version: "1"
default_snapshot_id: wgs-v4.0.1-dev-136da1a-b10cd8af
snapshots:
  - snapshot_id: wgs-v4.0.1-dev-136da1a-b10cd8af
    pipeline: wgs
    version: V4.0.1
    server_path: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs
    source_commit: 136da1ad9e45ac1abcbeb3efa40bb2e2269b6ab9
    snapshot_manifest_sha256: b10cd8af1db19c313e15167c295d007d9eca246d03b2721592c4c0532a05696c
    rule_event_schema_version: "1"
    status: {status}
    execution_enabled: {str(execution_enabled).lower()}
""",
        encoding="utf-8",
    )
    return path


def test_catalog_selects_the_server_development_snapshot(tmp_path: Path) -> None:
    snapshot = load_snapshot_catalog(write_catalog(tmp_path)).default_development()

    assert snapshot.snapshot_id == "wgs-v4.0.1-dev-136da1a-b10cd8af"
    assert snapshot.server_path == "/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs"
    assert snapshot.source_commit == "136da1ad9e45ac1abcbeb3efa40bb2e2269b6ab9"
    assert snapshot.snapshot_manifest_sha256 == "b10cd8af1db19c313e15167c295d007d9eca246d03b2721592c4c0532a05696c"
    assert snapshot.rule_event_schema_version == "1"
    assert snapshot.execution_enabled is False


def test_catalog_rejects_execution_enabled_development_snapshot(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="execution must remain disabled"):
        load_snapshot_catalog(write_catalog(tmp_path, execution_enabled=True))


def test_catalog_rejects_snapshot_outside_airflow_development_root(tmp_path: Path) -> None:
    path = write_catalog(tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs",
            "/mnt/biodevrwbi/33.chenjiucheng/project/wgs",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Airflow development root"):
        load_snapshot_catalog(path)
