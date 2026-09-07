from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260907_0017_wgs_lifecycle_status.py"
)


def test_lifecycle_migration_extends_directional_lease_head():
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260907_0017"' in source
    assert 'down_revision = "20260907_0016"' in source
    assert '"wgs_lifecycle_status"' in source
    assert '"kind", "scope_type", "scope_key"' in source
    assert "cannot be downgraded destructively" in source
