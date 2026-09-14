"""Immutable WGS selected membership and safe preparation review by attempt."""
from alembic import op
import sqlalchemy as sa

revision = "20260914_0022"
down_revision = "20260912_0021"
branch_labels = None
depends_on = None
ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table("wgs_attempt_sample_scope",
        sa.Column("id", ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("analysis_id", sa.String(128), sa.ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt", sa.Integer, nullable=False), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("receipt_schema", sa.String(128), nullable=False), sa.Column("receipt_sha256", sa.String(64), nullable=False),
        sa.Column("candidate_count", sa.Integer, nullable=False), sa.Column("selected_count", sa.Integer, nullable=False),
        sa.Column("pending_count", sa.Integer, nullable=False), sa.Column("excluded_count", sa.Integer, nullable=False),
        sa.Column("provenance_json", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("analysis_id", "attempt", name="uq_wgs_attempt_sample_scope"))
    op.create_index("ix_wgs_attempt_sample_scope_analysis", "wgs_attempt_sample_scope", ["analysis_id", "attempt"])
    op.create_table("wgs_attempt_sample_member",
        sa.Column("id", ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("scope_id", ID_TYPE, sa.ForeignKey("wgs_attempt_sample_scope.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sample_id", sa.String(128), nullable=False), sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("safe_snapshot_json", sa.JSON, nullable=False),
        sa.UniqueConstraint("scope_id", "sample_id", name="uq_wgs_attempt_sample_member"))
    op.create_index("ix_wgs_attempt_member_decision", "wgs_attempt_sample_member", ["scope_id", "decision"])


def downgrade():
    raise RuntimeError("WGS attempt scope history is retained; restore code without downgrading revision 0022")
