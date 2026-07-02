"""initial biodemo schema

Revision ID: 20260702_0001
Revises:
Create Date: 2026-07-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260702_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("dag_id", sa.String(length=256), nullable=False),
        sa.Column("version", sa.String(length=128), nullable=True),
        sa.Column("runner_type", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_pipeline_name"),
    )

    op.create_table(
        "analysis_run",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("pipeline_name", sa.String(length=128), nullable=False),
        sa.Column("dag_id", sa.String(length=256), nullable=False),
        sa.Column("dag_run_id", sa.String(length=256), nullable=True),
        sa.Column("parent_analysis_id", sa.String(length=128), nullable=True),
        sa.Column("mode", sa.String(length=64), nullable=False, server_default=sa.text("'new'")),
        sa.Column("status", sa.String(length=64), nullable=False, server_default=sa.text("'submitted'")),
        sa.Column("sample_sheet_path", sa.Text(), nullable=True),
        sa.Column("workdir", sa.Text(), nullable=False),
        sa.Column("params_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("airflow_url", sa.Text(), nullable=True),
        sa.Column("submitted_by", sa.String(length=128), nullable=True),
        sa.Column("email_to", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.UniqueConstraint("analysis_id", name="uq_analysis_run_analysis_id"),
    )
    op.create_index("ix_analysis_run_pipeline_status", "analysis_run", ["pipeline_name", "status"])

    op.create_table(
        "sample",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("sample_id", sa.String(length=128), nullable=False),
        sa.Column("family_id", sa.String(length=128), nullable=True),
        sa.Column("sample_type", sa.String(length=64), nullable=True),
        sa.Column("sex", sa.String(length=32), nullable=True),
        sa.Column("fq1", sa.Text(), nullable=True),
        sa.Column("fq2", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=64), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("qc_status", sa.String(length=64), nullable=False, server_default=sa.text("'unknown'")),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("analysis_id", "sample_id", name="uq_sample_analysis_sample"),
    )
    op.create_index("ix_sample_analysis_id", "sample", ["analysis_id"])
    op.create_index("ix_sample_sample_id", "sample", ["sample_id"])

    op.create_table(
        "snakemake_rule_event",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("rule", sa.String(length=256), nullable=False),
        sa.Column("sample_id", sa.String(length=128), nullable=True),
        sa.Column("wildcards_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("snakemake_jobid", sa.String(length=128), nullable=True),
        sa.Column("qsub_jobid", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("stdout_path", sa.Text(), nullable=True),
        sa.Column("stderr_path", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("return_code", sa.Integer(), nullable=True),
        sa.Column("resources_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("analysis_id", "rule", "sample_id", "snakemake_jobid", name="uq_rule_event_job"),
    )
    op.create_index("ix_rule_event_analysis_id", "snakemake_rule_event", ["analysis_id"])
    op.create_index("ix_rule_event_rule", "snakemake_rule_event", ["rule"])
    op.create_index("ix_rule_event_sample_id", "snakemake_rule_event", ["sample_id"])

    op.create_table(
        "qc_metric",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("sample_id", sa.String(length=128), nullable=True),
        sa.Column("metric_name", sa.String(length=256), nullable=False),
        sa.Column("metric_value", sa.Text(), nullable=True),
        sa.Column("metric_numeric", sa.Numeric(), nullable=True),
        sa.Column("threshold", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column("source_file", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_qc_metric_analysis_id", "qc_metric", ["analysis_id"])
    op.create_index("ix_qc_metric_sample_id", "qc_metric", ["sample_id"])

    op.create_table(
        "artifact",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=128), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=256), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_artifact_analysis_id", "artifact", ["analysis_id"])

    op.create_table(
        "run_action",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("result_status", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_run_action_analysis_id", "run_action", ["analysis_id"])


def downgrade() -> None:
    op.drop_index("ix_run_action_analysis_id", table_name="run_action")
    op.drop_table("run_action")
    op.drop_index("ix_artifact_analysis_id", table_name="artifact")
    op.drop_table("artifact")
    op.drop_index("ix_qc_metric_sample_id", table_name="qc_metric")
    op.drop_index("ix_qc_metric_analysis_id", table_name="qc_metric")
    op.drop_table("qc_metric")
    op.drop_index("ix_rule_event_sample_id", table_name="snakemake_rule_event")
    op.drop_index("ix_rule_event_rule", table_name="snakemake_rule_event")
    op.drop_index("ix_rule_event_analysis_id", table_name="snakemake_rule_event")
    op.drop_table("snakemake_rule_event")
    op.drop_index("ix_sample_sample_id", table_name="sample")
    op.drop_index("ix_sample_analysis_id", table_name="sample")
    op.drop_table("sample")
    op.drop_index("ix_analysis_run_pipeline_status", table_name="analysis_run")
    op.drop_table("analysis_run")
    op.drop_table("pipeline")
