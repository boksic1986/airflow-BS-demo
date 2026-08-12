"""add WGS observer cursors and incremental Kubernetes evidence

Revision ID: 20260812_0007
Revises: 20260812_0006
Create Date: 2026-08-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260812_0007"
down_revision = "20260812_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_cursor",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.String(128),
            sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("file_identity", sa.String(256)),
        sa.Column("byte_offset", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("line_number", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("observed_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("observed_mtime_ns", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "analysis_id",
            "attempt",
            "relative_path",
            name="uq_evidence_cursor_file",
        ),
    )
    op.create_index(
        "ix_evidence_cursor_analysis", "evidence_cursor", ["analysis_id"]
    )
    op.create_table(
        "observer_run_state",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.String(128),
            sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("pipeline_snapshot_id", sa.String(256), nullable=False),
        sa.Column("run_label", sa.String(128), nullable=False),
        sa.Column("relative_evidence_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="pending"),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "analysis_id", "attempt", name="uq_observer_run_state_attempt"
        ),
    )
    op.create_index(
        "ix_observer_run_state_analysis", "observer_run_state", ["analysis_id"]
    )

    op.add_column(
        "kubernetes_workload", sa.Column("resource_version", sa.String(128))
    )
    op.add_column(
        "kubernetes_workload", sa.Column("observed_at", sa.DateTime(timezone=True))
    )
    op.add_column("kubernetes_workload", sa.Column("node_name", sa.String(256)))
    op.add_column("kubernetes_workload", sa.Column("message", sa.Text()))
    op.add_column("kubernetes_workload", sa.Column("job_status_json", sa.JSON()))


def downgrade() -> None:
    op.drop_column("kubernetes_workload", "job_status_json")
    op.drop_column("kubernetes_workload", "message")
    op.drop_column("kubernetes_workload", "node_name")
    op.drop_column("kubernetes_workload", "observed_at")
    op.drop_column("kubernetes_workload", "resource_version")
    op.drop_table("observer_run_state")
    op.drop_table("evidence_cursor")
