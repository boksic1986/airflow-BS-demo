from alembic import command
from alembic.config import Config
from pathlib import Path
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine, MetaData, select, text, inspect
from sqlalchemy.orm import Session

from app.models import Base, WgsIntakeBatch, WgsSamplelistSource, WgsSamplelistObservation


def _alembic_config():
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    return config


def _set_migration_database(monkeypatch, path):
    url = f"sqlite:///{path.as_posix()}"
    monkeypatch.setattr("app.config.get_settings", lambda: SimpleNamespace(database_url=url))
    return url


def test_additive_migration_preserves_legacy_and_refuses_destructive_downgrade(tmp_path, monkeypatch):
    url = _set_migration_database(monkeypatch, tmp_path / "migration.sqlite")
    engine = create_engine(url)
    metadata = MetaData()
    for name, table in Base.metadata.tables.items():
        if not name.startswith("wgs_samplelist_"):
            table.to_metadata(metadata)
    batch = metadata.tables["wgs_intake_batch"]
    for constraint in list(batch.constraints):
        if constraint.name == "uq_wgs_intake_scoped_batch":
            batch.constraints.remove(constraint)
    for name in ("discovery_mode", "project_id", "platform_id", "root_id", "source_identity", "source_version", "bound_directory_identity", "reason_code"):
        batch._columns.remove(batch.c[name])
    batch.c.source_path.nullable = batch.c.chip_id.nullable = False
    metadata.create_all(engine)
    with engine.begin() as connection:
        for number in (1, 2):
            connection.execute(batch.insert().values(source_path=f"/synthetic/{number}", chip_id=f"SYN{number}", sequencing_batch="20990101A"))
    config = _alembic_config()
    command.stamp(config, "20260912_0020")
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with Session(engine) as session:
        legacy = session.scalars(select(WgsIntakeBatch)).all()
        assert len(legacy) == 2
        assert all(row.project_id is None and row.discovery_mode == "t7_scan_only" for row in legacy)
        row = WgsIntakeBatch(project_id="SYN", platform_id="T7", root_id="SYN", sequencing_batch="20990102B", discovery_mode="samplelist_batches", state="waiting_sequencing")
        session.add(row)
        session.add(WgsSamplelistSource(source_identity="a" * 64, baseline_complete=True))
        session.flush()
        session.add(WgsSamplelistObservation(source_identity="a" * 64, file_identity="b" * 64, is_baseline=True))
        session.commit()
        assert row.id is not None
    with pytest.raises(RuntimeError, match="retained"):
        command.downgrade(config, "20260912_0020")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260912_0021"
        assert connection.scalar(text("SELECT count(*) FROM wgs_intake_batch")) == 3
        assert connection.scalar(text("SELECT count(*) FROM wgs_samplelist_observation")) == 1
    uniques = inspect(engine).get_unique_constraints("wgs_intake_batch")
    assert {tuple(row["column_names"]) for row in uniques} >= {("chip_id",), ("source_path",), ("project_id", "platform_id", "sequencing_batch")}


def test_postgresql_additive_ddl_compiles(monkeypatch, capsys):
    from types import SimpleNamespace
    monkeypatch.setattr("app.config.get_settings", lambda: SimpleNamespace(database_url="postgresql://offline:offline@invalid/offline"))
    command.upgrade(_alembic_config(), "20260912_0020:20260912_0021", sql=True)
    ddl = capsys.readouterr().out
    assert "CREATE TABLE wgs_samplelist_source" in ddl
    assert "DROP TABLE" not in ddl
