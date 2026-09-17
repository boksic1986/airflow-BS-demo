"""Exercise only the additive identity migration in a disposable database."""
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


def test_native_identity_migration_retains_legacy_rows_and_enforces_unique_uuid():
    path = Path(__file__).parents[1] / "alembic/versions/20260915_0025_onprem_project_identity.py"
    spec = importlib.util.spec_from_file_location("identity_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE analysis_run (id INTEGER PRIMARY KEY, analysis_id TEXT)"))
        conn.execute(text("INSERT INTO analysis_run (id, analysis_id) VALUES (1, 'SYN_OLD'), (2, 'SYN_OLD_2')"))
        migration.op = Operations(MigrationContext.configure(conn))
        migration.upgrade()
        assert conn.execute(text("SELECT analysis_id, onprem_project_uuid FROM analysis_run ORDER BY id")).all() == [
            ("SYN_OLD", None), ("SYN_OLD_2", None)]
        conn.execute(text("UPDATE analysis_run SET onprem_project_uuid='P1' WHERE id=1"))
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(text("UPDATE analysis_run SET onprem_project_uuid='P1' WHERE id=2"))
    engine.dispose()


def test_native_execution_migration_adds_history_without_changing_legacy_tables():
    from app.models import Base

    path = Path(__file__).parents[1] / "alembic/versions/20260915_0026_onprem_execution_snapshot.py"
    spec = importlib.util.spec_from_file_location("execution_snapshot_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    # Model dependency tables represent the existing pre-0026 installation.
    Base.metadata.create_all(engine, tables=[table for table in Base.metadata.sorted_tables
                                            if table.name != "wgs_onprem_execution_snapshot"])
    with engine.begin() as conn:
        sample_ddl = text("SELECT sql FROM sqlite_master WHERE type='table' AND name='sample'")
        before = conn.scalar(sample_ddl)
        migration.op = Operations(MigrationContext.configure(conn))
        migration.upgrade()
        assert conn.scalar(sample_ddl) == before
        conn.execute(text("INSERT INTO wgs_onprem_execution_snapshot VALUES "
            "('E1','SYN_RUN','OP1','private/E1',:hash,'{}','[]','synthetic',CURRENT_TIMESTAMP)"), {"hash": "a" * 64})
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(text("INSERT INTO wgs_onprem_execution_snapshot VALUES "
                    "('E2','SYN_RUN','OP1','private/E2',:hash,'{}','[]','synthetic',CURRENT_TIMESTAMP)"), {"hash": "b" * 64})
        assert conn.execute(text("SELECT execution_id FROM wgs_onprem_execution_snapshot")).scalars().all() == ["E1"]
    engine.dispose()
