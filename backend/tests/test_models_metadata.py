from sqlalchemy import UniqueConstraint

from app.models import (
    AnalysisRun,
    Artifact,
    Base,
    IntakeDiscovery,
    Pipeline,
    QcMetric,
    RunAction,
    Sample,
    SnakemakeRuleEvent,
)


def test_initial_biodemo_tables_are_declared() -> None:
    expected_tables = {
        "pipeline",
        "analysis_run",
        "sample",
        "snakemake_rule_event",
        "qc_metric",
        "artifact",
        "run_action",
        "intake_discovery",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_analysis_run_uses_unique_business_analysis_id() -> None:
    table = AnalysisRun.__table__

    unique_columns = {
        column.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
        for column in constraint.columns
    }

    assert "analysis_id" in unique_columns


def test_model_classes_map_to_expected_tables() -> None:
    assert Pipeline.__tablename__ == "pipeline"
    assert Sample.__tablename__ == "sample"
    assert SnakemakeRuleEvent.__tablename__ == "snakemake_rule_event"
    assert QcMetric.__tablename__ == "qc_metric"
    assert Artifact.__tablename__ == "artifact"
    assert RunAction.__tablename__ == "run_action"
    assert IntakeDiscovery.__tablename__ == "intake_discovery"
