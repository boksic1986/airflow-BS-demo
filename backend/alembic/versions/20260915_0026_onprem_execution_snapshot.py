"""Retain native input scopes across edits/resumes without replacing Sample."""
from alembic import op
import sqlalchemy as sa

revision = "20260915_0026"
down_revision = "20260915_0025"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("wgs_onprem_execution_snapshot",
        sa.Column("execution_id", sa.String(128), sa.ForeignKey("wgs_stage_execution.execution_id"), primary_key=True),
        sa.Column("analysis_id", sa.String(128), sa.ForeignKey("analysis_run.analysis_id"), nullable=False),
        sa.Column("operation_id", sa.String(36), nullable=False),
        sa.Column("snapshot_path", sa.Text(), nullable=False),
        sa.Column("manifest_hash", sa.String(64), nullable=False),
        sa.Column("file_refs_json", sa.JSON(), nullable=False),
        sa.Column("sample_scope_json", sa.JSON(), nullable=False),
        sa.Column("registered_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("analysis_id", "operation_id", name="uq_wgs_onprem_execution_operation"))


def downgrade():
    raise RuntimeError("Retain native execution snapshots; disable registration instead of deleting history")
