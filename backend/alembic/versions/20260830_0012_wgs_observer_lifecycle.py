"""split WGS scanner baseline from event-driven run monitoring

Revision ID: 20260830_0012
Revises: 20260829_0011
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260830_0012"
down_revision = "20260829_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wgs_intake_scanner_state",
        sa.Column("first_scan_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "wgs_intake_scanner_state",
        sa.Column("last_scan_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "wgs_intake_scanner_state",
        sa.Column(
            "last_scanned_directory_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.execute(
        """
        UPDATE wgs_intake_scanner_state
        SET first_scan_at = bootstrap_started_at,
            last_scan_at = last_scan_completed_at,
            last_scanned_directory_count = COALESCE(
                NULLIF(last_counts_json ->> 'scanned', '')::integer,
                0
            )
        """
    )
    for column in (
        "root_path",
        "scan_enabled",
        "scan_interval_seconds",
        "auto_dispatch_enabled",
        "bootstrap_started_at",
        "bootstrap_completed_at",
        "last_scan_started_at",
        "last_scan_completed_at",
        "next_scan_at",
        "last_scan_duration_ms",
        "last_status",
        "last_counts_json",
        "updated_at",
    ):
        op.drop_column("wgs_intake_scanner_state", column)

    op.alter_column(
        "observer_run_state",
        "status",
        new_column_name="monitoring_health",
        existing_type=sa.String(length=64),
        existing_nullable=False,
    )
    op.add_column(
        "observer_run_state",
        sa.Column(
            "lifecycle_status",
            sa.String(length=32),
            nullable=False,
            server_default="stopped",
        ),
    )
    op.add_column(
        "observer_run_state",
        sa.Column("activated_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "observer_run_state",
        sa.Column("deactivated_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        """
        UPDATE observer_run_state
        SET monitoring_health = CASE
                WHEN monitoring_health IN ('healthy', 'degraded', 'error')
                    THEN monitoring_health
                ELSE 'healthy'
            END,
            lifecycle_status = 'stopped',
            deactivated_at = COALESCE(updated_at, now())
        """
    )
    op.create_index(
        "ix_observer_run_state_lifecycle",
        "observer_run_state",
        ["lifecycle_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_observer_run_state_lifecycle", table_name="observer_run_state"
    )
    op.drop_column("observer_run_state", "deactivated_at")
    op.drop_column("observer_run_state", "activated_at")
    op.drop_column("observer_run_state", "lifecycle_status")
    op.alter_column(
        "observer_run_state",
        "monitoring_health",
        new_column_name="status",
        existing_type=sa.String(length=64),
        existing_nullable=False,
    )

    op.add_column(
        "wgs_intake_scanner_state",
        sa.Column("root_path", sa.Text(), nullable=False, server_default="/bi/fastq/T7_Fastq"),
    )
    op.add_column(
        "wgs_intake_scanner_state",
        sa.Column("scan_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "wgs_intake_scanner_state",
        sa.Column("scan_interval_seconds", sa.Integer(), nullable=False, server_default="1800"),
    )
    op.add_column(
        "wgs_intake_scanner_state",
        sa.Column("auto_dispatch_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("wgs_intake_scanner_state", sa.Column("bootstrap_started_at", sa.DateTime(timezone=True)))
    op.add_column("wgs_intake_scanner_state", sa.Column("bootstrap_completed_at", sa.DateTime(timezone=True)))
    op.add_column("wgs_intake_scanner_state", sa.Column("last_scan_started_at", sa.DateTime(timezone=True)))
    op.add_column("wgs_intake_scanner_state", sa.Column("last_scan_completed_at", sa.DateTime(timezone=True)))
    op.add_column("wgs_intake_scanner_state", sa.Column("next_scan_at", sa.DateTime(timezone=True)))
    op.add_column("wgs_intake_scanner_state", sa.Column("last_scan_duration_ms", sa.BigInteger()))
    op.add_column(
        "wgs_intake_scanner_state",
        sa.Column("last_status", sa.String(length=32), nullable=False, server_default="never_run"),
    )
    op.add_column(
        "wgs_intake_scanner_state",
        sa.Column("last_counts_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.add_column(
        "wgs_intake_scanner_state",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        """
        UPDATE wgs_intake_scanner_state
        SET bootstrap_started_at = first_scan_at,
            bootstrap_completed_at = first_scan_at,
            last_scan_started_at = last_scan_at,
            last_scan_completed_at = last_scan_at,
            last_counts_json = json_build_object(
                'scanned', last_scanned_directory_count
            )
        """
    )
    op.drop_column("wgs_intake_scanner_state", "last_scanned_directory_count")
    op.drop_column("wgs_intake_scanner_state", "last_scan_at")
    op.drop_column("wgs_intake_scanner_state", "first_scan_at")
