"""add T7 scan-only intake and WGS Step4 maintenance records

Revision ID: 20260829_0011
Revises: 20260827_0010
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260829_0011"
down_revision = "20260827_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "wgs_intake_batch",
        "manifest_sha256",
        new_column_name="eligible_fingerprint",
        existing_type=sa.String(length=64),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "wgs_intake_batch",
        "ready_mtime_ns",
        new_column_name="barcode_stat_mtime_ns",
        existing_type=sa.BigInteger(),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "wgs_intake_batch",
        "analysis_id",
        existing_type=sa.String(length=128),
        existing_nullable=False,
        nullable=True,
    )
    op.drop_constraint(
        "wgs_intake_batch_analysis_id_fkey",
        "wgs_intake_batch",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "wgs_intake_batch_analysis_id_fkey",
        "wgs_intake_batch",
        "analysis_run",
        ["analysis_id"],
        ["analysis_id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "wgs_intake_batch",
        sa.Column("chip_id", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "wgs_intake_batch",
        sa.Column("sequencing_batch", sa.String(length=16), nullable=True),
    )
    op.add_column("wgs_intake_batch", sa.Column("barcode_stat_size", sa.BigInteger()))
    op.add_column(
        "wgs_intake_batch",
        sa.Column("eligible_pair_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "wgs_intake_batch",
        sa.Column("excluded_addon_pair_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "wgs_intake_batch",
        sa.Column("pair_issue_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("wgs_intake_batch", sa.Column("observed_fingerprint", sa.String(length=64)))
    op.add_column(
        "wgs_intake_batch",
        sa.Column("state", sa.String(length=64), nullable=False, server_default="bootstrap_ignored"),
    )
    op.add_column("wgs_intake_batch", sa.Column("last_error", sa.Text()))
    op.add_column(
        "wgs_intake_batch",
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        "wgs_intake_batch",
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column("wgs_intake_batch", sa.Column("ready_at", sa.DateTime(timezone=True)))
    op.add_column(
        "wgs_intake_batch",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        """
        UPDATE wgs_intake_batch
        SET chip_id = regexp_replace(source_path, '^.*/', ''),
            sequencing_batch = COALESCE(
                substring(regexp_replace(source_path, '^.*/', '') FROM '\\d+th_(\\d{8}[A-Z])_'),
                'UNKNOWN'
            ),
            observed_fingerprint = eligible_fingerprint
        """
    )
    op.alter_column("wgs_intake_batch", "chip_id", existing_type=sa.String(length=256), nullable=False)
    op.alter_column("wgs_intake_batch", "sequencing_batch", existing_type=sa.String(length=16), nullable=False)
    op.create_unique_constraint("uq_wgs_intake_batch_chip_id", "wgs_intake_batch", ["chip_id"])
    op.create_index("ix_wgs_intake_batch_state", "wgs_intake_batch", ["state"])
    op.create_index(
        "ix_wgs_intake_batch_sequencing_batch",
        "wgs_intake_batch",
        ["sequencing_batch"],
    )

    op.create_table(
        "wgs_intake_scanner_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("scan_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("scan_interval_seconds", sa.Integer(), nullable=False, server_default="1800"),
        sa.Column("auto_dispatch_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("bootstrap_started_at", sa.DateTime(timezone=True)),
        sa.Column("bootstrap_completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_scan_started_at", sa.DateTime(timezone=True)),
        sa.Column("last_scan_completed_at", sa.DateTime(timezone=True)),
        sa.Column("next_scan_at", sa.DateTime(timezone=True)),
        sa.Column("last_scan_duration_ms", sa.BigInteger()),
        sa.Column("last_status", sa.String(length=32), nullable=False, server_default="never_run"),
        sa.Column("last_counts_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("last_error", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "wgs_maintenance_action",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("action_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column(
            "analysis_id",
            sa.String(length=128),
            sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("linkage_group", sa.String(length=32), nullable=False, server_default="cram"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="requested"),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("source_dag_run_id", sa.String(length=256)),
        sa.Column("maintenance_dag_run_id", sa.String(length=256)),
        sa.Column("evidence_path", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "analysis_id",
            "attempt",
            "action_type",
            name="uq_wgs_maintenance_action_attempt_type",
        ),
    )
    op.create_index(
        "ix_wgs_maintenance_action_analysis",
        "wgs_maintenance_action",
        ["analysis_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_wgs_maintenance_action_analysis", table_name="wgs_maintenance_action")
    op.drop_table("wgs_maintenance_action")
    op.drop_table("wgs_intake_scanner_state")
    op.drop_index("ix_wgs_intake_batch_sequencing_batch", table_name="wgs_intake_batch")
    op.drop_index("ix_wgs_intake_batch_state", table_name="wgs_intake_batch")
    op.drop_constraint("uq_wgs_intake_batch_chip_id", "wgs_intake_batch", type_="unique")
    op.execute("DELETE FROM wgs_intake_batch WHERE analysis_id IS NULL")
    op.drop_constraint(
        "wgs_intake_batch_analysis_id_fkey",
        "wgs_intake_batch",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "wgs_intake_batch_analysis_id_fkey",
        "wgs_intake_batch",
        "analysis_run",
        ["analysis_id"],
        ["analysis_id"],
        ondelete="CASCADE",
    )
    for column in (
        "updated_at",
        "ready_at",
        "last_scanned_at",
        "first_seen_at",
        "last_error",
        "state",
        "observed_fingerprint",
        "pair_issue_count",
        "excluded_addon_pair_count",
        "eligible_pair_count",
        "barcode_stat_size",
        "sequencing_batch",
        "chip_id",
    ):
        op.drop_column("wgs_intake_batch", column)
    op.alter_column(
        "wgs_intake_batch",
        "analysis_id",
        existing_type=sa.String(length=128),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "wgs_intake_batch",
        "barcode_stat_mtime_ns",
        new_column_name="ready_mtime_ns",
        existing_type=sa.BigInteger(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "wgs_intake_batch",
        "eligible_fingerprint",
        new_column_name="manifest_sha256",
        existing_type=sa.String(length=64),
        existing_nullable=True,
        nullable=False,
    )
