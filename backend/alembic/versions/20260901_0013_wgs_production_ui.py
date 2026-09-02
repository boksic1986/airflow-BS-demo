"""WGS production stage, draft, rule, and resource projections.

Revision ID: 20260901_0013
Revises: 20260830_0012
"""

from alembic import op
import os
import sqlalchemy as sa


revision = "20260901_0013"
down_revision = "20260830_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rule_state", sa.Column("sequence", sa.BigInteger(), nullable=True))
    op.add_column("rule_state", sa.Column("phase", sa.String(length=128), nullable=True))
    op.add_column("rule_state", sa.Column("snakemake_jobid", sa.String(length=128), nullable=True))
    op.add_column("rule_state", sa.Column("family_id", sa.String(length=128), nullable=True))
    op.add_column("rule_state", sa.Column("wildcards_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    op.add_column("rule_state", sa.Column("message", sa.Text(), nullable=True))
    op.add_column("rule_state", sa.Column("log_paths_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))

    op.create_table(
        "run_stage_state",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("analysis_id", sa.String(length=128), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("stage_code", sa.String(length=64), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=True),
        sa.Column("stage_label", sa.String(length=128), nullable=False),
        sa.Column("stage_status", sa.String(length=64), nullable=False),
        sa.Column("progress_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("progress_percent", sa.Integer(), nullable=True),
        sa.Column("completed_units", sa.BigInteger(), nullable=True),
        sa.Column("total_units", sa.BigInteger(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("current_item", sa.Text(), nullable=True),
        sa.Column("speed_bps", sa.BigInteger(), nullable=True),
        sa.Column("eta_seconds", sa.BigInteger(), nullable=True),
        sa.Column("progress_source", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("evidence_key", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "attempt", "stage_code", name="uq_run_stage_state_identity"),
    )
    op.create_index("ix_run_stage_state_analysis", "run_stage_state", ["analysis_id", "attempt"])

    op.create_table(
        "wgs_submission_draft",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("draft_id", sa.String(length=128), nullable=False),
        sa.Column("owner_username", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("sequencing_batch", sa.String(length=64), nullable=False),
        sa.Column("analysis_batch", sa.String(length=128), nullable=False),
        sa.Column("fastq_root_id", sa.String(length=128), nullable=False),
        sa.Column("fastq_path", sa.Text(), nullable=False),
        sa.Column("use_reference", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("preview_json", sa.JSON(), nullable=False),
        sa.Column("resolved_config_json", sa.JSON(), nullable=False),
        sa.Column("private_workdir", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("analysis_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_run.analysis_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_wgs_submission_draft_owner_status", "wgs_submission_draft", ["owner_username", "status"])
    op.create_index("ix_wgs_submission_draft_expiry", "wgs_submission_draft", ["expires_at"])

    op.create_table(
        "platform_resource_snapshot",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("resource_key", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_json", sa.JSON(), nullable=False),
        sa.Column("history_json", sa.JSON(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_key"),
    )
    op.create_index("ix_platform_resource_snapshot_type", "platform_resource_snapshot", ["resource_type"])


def downgrade() -> None:
    if os.getenv("ALLOW_WGS_PRODUCTION_UI_DOWNGRADE") != "true":
        raise RuntimeError(
            "20260901_0013 downgrade deletes WGS submission drafts, stage state, "
            "and platform resource snapshots; set ALLOW_WGS_PRODUCTION_UI_DOWNGRADE=true "
            "only for an approved rollback"
        )
    op.drop_index("ix_platform_resource_snapshot_type", table_name="platform_resource_snapshot")
    op.drop_table("platform_resource_snapshot")
    op.drop_index("ix_wgs_submission_draft_expiry", table_name="wgs_submission_draft")
    op.drop_index("ix_wgs_submission_draft_owner_status", table_name="wgs_submission_draft")
    op.drop_table("wgs_submission_draft")
    op.drop_index("ix_run_stage_state_analysis", table_name="run_stage_state")
    op.drop_table("run_stage_state")
    op.drop_column("rule_state", "log_paths_json")
    op.drop_column("rule_state", "message")
    op.drop_column("rule_state", "wildcards_json")
    op.drop_column("rule_state", "family_id")
    op.drop_column("rule_state", "snakemake_jobid")
    op.drop_column("rule_state", "phase")
    op.drop_column("rule_state", "sequence")
