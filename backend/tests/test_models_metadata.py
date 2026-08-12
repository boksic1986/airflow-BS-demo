from sqlalchemy import UniqueConstraint

from app.models import (
    AnalysisRun,
    Artifact,
    Base,
    EvidenceCursor,
    IntakeDiscovery,
    KubernetesWorkload,
    ObserverRunState,
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


def test_t112_operational_timestamps_and_progress_snapshots_are_declared() -> None:
    columns = AnalysisRun.__table__.columns

    assert "submitted_at" in columns
    assert "progress_percent" in columns
    assert "current_stage" in columns
    assert "progress_updated_at" in columns

    intake_columns = IntakeDiscovery.__table__.columns
    assert "source_manifest_path" in intake_columns
    assert "last_error" in intake_columns
    assert "stable_observation_count" in intake_columns
    assert "state_changed_at" in intake_columns
    assert "archived_at" in intake_columns
    assert "archive_reason" in intake_columns
    assert "archive_path" in intake_columns


def test_model_classes_map_to_expected_tables() -> None:
    assert Pipeline.__tablename__ == "pipeline"
    assert Sample.__tablename__ == "sample"
    assert SnakemakeRuleEvent.__tablename__ == "snakemake_rule_event"
    assert QcMetric.__tablename__ == "qc_metric"
    assert Artifact.__tablename__ == "artifact"
    assert RunAction.__tablename__ == "run_action"
    assert IntakeDiscovery.__tablename__ == "intake_discovery"


def test_wgs_observer_cursor_tables_and_identity_constraints_are_declared() -> None:
    assert {"evidence_cursor", "observer_run_state"}.issubset(Base.metadata.tables.keys())

    cursor_unique_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in EvidenceCursor.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    observer_unique_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in ObserverRunState.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("analysis_id", "attempt", "relative_path") in cursor_unique_sets
    assert ("analysis_id", "attempt") in observer_unique_sets


def test_kubernetes_workload_has_incremental_observation_fields() -> None:
    columns = KubernetesWorkload.__table__.columns

    assert "resource_version" in columns
    assert "observed_at" in columns
    assert "node_name" in columns
    assert "message" in columns
    assert "job_status_json" in columns
