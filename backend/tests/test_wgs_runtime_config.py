from pathlib import Path

import pytest

from app.config import get_settings
from app.wgs_project_catalog import load_wgs_projects


CONTRACT_PATH = Path(__file__).parents[2] / "config" / "wgs_stage_contract.yaml"


def _base_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite://")
    monkeypatch.setenv("AIRFLOW_API_PASSWORD", "test-only")
    monkeypatch.setenv("WGS_STAGE_CONTRACT_PATH", str(CONTRACT_PATH))
    for name in (
        "WGS_INTAKE_SCAN_ENABLED",
        "WGS_AUTO_DISPATCH_ENABLED",
        "WGS_HEAVY_SLOT_LIMIT",
        "WGS_HEAVY_SLOT_MODE",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()


def test_wgs_settings_fail_closed_and_use_stage_contract_heavy_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_environment(monkeypatch)

    settings = get_settings()

    assert settings.wgs_intake_scan_enabled is False
    assert settings.wgs_heavy_slot_limit == 25
    assert settings.wgs_heavy_slot_mode == "enforce"


@pytest.mark.parametrize(
    ("name", "value"),
    (("WGS_HEAVY_SLOT_LIMIT", "24"), ("WGS_HEAVY_SLOT_MODE", "monitor-only")),
)
def test_wgs_settings_reject_heavy_io_environment_drift(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    _base_environment(monkeypatch)
    monkeypatch.setenv(name, value)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="does not match WGS stage contract"):
        get_settings()


def test_wgs_project_fastq_root_requires_explicit_control_plane_path(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "projects.yaml"
    catalog.write_text(
        """\
schema_version: "1"
projects:
  - project_id: WGS_Clinical
    platforms:
      - platform_id: T7
    fastq_roots:
      - root_id: T7_Fastq
        node200_path: /bi/fastq/T7_Fastq
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="control_plane_path"):
        load_wgs_projects(catalog)


def test_wgs_intake_requires_environment_and_yaml_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _base_environment(monkeypatch)
    project_catalog = tmp_path / "projects.yaml"
    project_catalog.write_text(
        """\
schema_version: "1"
projects:
  - project_id: WGS_Clinical
    platforms:
      - platform_id: T7
    fastq_roots:
      - root_id: T7_Fastq
        node200_path: /bi/fastq/T7_Fastq
        control_plane_path: /bi/fastq/T7_Fastq
""",
        encoding="utf-8",
    )
    intake = tmp_path / "intake.yaml"
    intake.write_text(
        """\
version: 2
pipelines:
  wgs:
    enabled: true
    intake:
      project_id: WGS_Clinical
      root_id: T7_Fastq
      scheduled_scan_enabled: false
      interval_seconds: 1800
      auto_dispatch_enabled: false
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("INTAKE_CONFIG_PATH", str(intake))
    monkeypatch.setenv("WGS_PROJECT_CATALOG_PATH", str(project_catalog))
    monkeypatch.setenv("WGS_INTAKE_SCAN_ENABLED", "true")
    get_settings.cache_clear()

    disabled = get_settings()

    assert disabled.wgs_intake_scan_enabled is False
    assert disabled.wgs_intake_scan_interval_seconds == 1800

    intake.write_text(
        intake.read_text(encoding="utf-8").replace(
            "scheduled_scan_enabled: false", "scheduled_scan_enabled: true"
        ),
        encoding="utf-8",
    )
    get_settings.cache_clear()

    assert get_settings().wgs_intake_scan_enabled is True
