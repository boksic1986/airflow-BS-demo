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
schema_version: "2"
default_snapshot_id: wgs-v4.1.1-candidate-3489b39-11111111
snapshots:
  - snapshot_id: wgs-v4.1.1-candidate-3489b39-11111111
    pipeline: wgs
    version: V4.1.1
    server_path: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs-v4.1.1-candidate-3489b39-11111111
    source_commit: 3489b3958869e5cfab983aca1eb9c7f158c06dff
    snapshot_manifest_sha256: f95dddf3592c0b3b5e75b60e00e5359d5f9f607bbb7759b27107612e725ad91e
    rule_event_schema_version: "1"
    cce_pipeline_version: 0.5.0
    cce_pipeline_source_commit: 70a9a737c62865f232ed0b49f682aa7c9a69e467
    cce_pipeline_wheel_sha256: 43a4ab478e8b8810b1691bb755e54336b0bc8fd86a16d4fed9be3783036e1756
    cce_profile_id: wgs-4.1.1-r1
    cce_profile_sha256: 19a7cc76cfc086c032c5e2329310d4ff90cd67e5cb52632bfb98f1b4fea59276
    master_image_digest: sha256:815d70a6105b08b8fc6031a425cfed5ced8773e4d66c18ad98502b9a61ffeecc
    status: {status}
    execution_enabled: {str(execution_enabled).lower()}
""",
        encoding="utf-8",
    )
    return path


def test_catalog_selects_the_server_development_snapshot(tmp_path: Path) -> None:
    snapshot = load_snapshot_catalog(write_catalog(tmp_path)).default_development()

    assert snapshot.snapshot_id == "wgs-v4.1.1-candidate-3489b39-11111111"
    assert snapshot.server_path.endswith("/development/wgs-v4.1.1-candidate-3489b39-11111111")
    assert snapshot.source_commit == "3489b3958869e5cfab983aca1eb9c7f158c06dff"
    assert snapshot.snapshot_manifest_sha256 == "f95dddf3592c0b3b5e75b60e00e5359d5f9f607bbb7759b27107612e725ad91e"
    assert snapshot.rule_event_schema_version == "1"
    assert snapshot.cce_pipeline_version == "0.5.0"
    assert snapshot.cce_pipeline_source_commit == "70a9a737c62865f232ed0b49f682aa7c9a69e467"
    assert snapshot.cce_pipeline_wheel_sha256 == "43a4ab478e8b8810b1691bb755e54336b0bc8fd86a16d4fed9be3783036e1756"
    assert snapshot.cce_profile_id == "wgs-4.1.1-r1"
    assert snapshot.master_image_digest.startswith("sha256:")
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


def test_catalog_rejects_missing_cce_runtime_provenance(tmp_path: Path) -> None:
    path = write_catalog(tmp_path)
    payload = path.read_text(encoding="utf-8").replace(
        "    cce_pipeline_source_commit: 70a9a737c62865f232ed0b49f682aa7c9a69e467\n",
        "",
    )
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match="cce-pipeline source commit"):
        load_snapshot_catalog(path)


def test_checked_in_catalog_pins_the_final_4_1_1_runtime_contract() -> None:
    catalog = load_snapshot_catalog(
        Path(__file__).resolve().parents[2] / "config" / "wgs_releases.yaml"
    )
    snapshot = catalog.default_development()

    assert snapshot.snapshot_id.startswith("wgs-v4.1.1-candidate-3489b39-")
    assert snapshot.source_commit == "3489b3958869e5cfab983aca1eb9c7f158c06dff"
    assert snapshot.rule_event_schema_version == "1"
    assert snapshot.cce_pipeline_version == "0.5.0"
    assert snapshot.cce_pipeline_source_commit == "70a9a737c62865f232ed0b49f682aa7c9a69e467"
    assert snapshot.cce_profile_id == "wgs-4.1.1-r1"
    assert snapshot.cce_profile_sha256 == "19a7cc76cfc086c032c5e2329310d4ff90cd67e5cb52632bfb98f1b4fea59276"
    assert snapshot.master_image_digest == "sha256:815d70a6105b08b8fc6031a425cfed5ced8773e4d66c18ad98502b9a61ffeecc"
    assert snapshot.execution_enabled is False
