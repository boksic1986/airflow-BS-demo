import importlib.util
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260907_0016_wgs_directional_obs_transfer.py"
)


def _migration_module():
    spec = importlib.util.spec_from_file_location("wgs_migration_0016", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_directional_lease_migration_follows_execution_dispatch_head() -> None:
    migration = _migration_module()

    assert migration.revision == "20260907_0016"
    assert migration.down_revision == "20260906_0015"


def test_upgrade_creates_both_directional_rows_idempotently() -> None:
    migration = _migration_module()
    statements: list[str] = []
    migration.op = type("FakeOp", (), {"execute": statements.append})()

    migration.upgrade()

    sql = " ".join(statements)
    assert "wgs-obs-upload-01" in sql
    assert "wgs-obs-download-01" in sql
    assert "ON CONFLICT" in sql


def test_downgrade_retains_directional_rows_without_destructive_sql() -> None:
    migration = _migration_module()
    statements: list[str] = []
    migration.op = type("FakeOp", (), {"execute": statements.append})()

    migration.downgrade()

    assert statements == []
