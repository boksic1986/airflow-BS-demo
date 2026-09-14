"""Add immutable registered handoff history, retaining published 0020 tables."""
from alembic import op
import sqlalchemy as sa

revision = "20260914_0023"
down_revision = "20260914_0022"
branch_labels = None
depends_on = None
ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

def upgrade():
    op.add_column("sample_reference_source",sa.Column("registration_key",sa.String(64)))
    op.add_column("sample_reference",sa.Column("reason_codes",sa.JSON,nullable=False,server_default="[]"))
    op.add_column("sample_reference",sa.Column("origin_batch",sa.String(128)))
    op.add_column("sample_reference",sa.Column("destination_batch",sa.String(128)))
    op.create_table("sample_reference_operation",
        sa.Column("id",ID_TYPE,primary_key=True,autoincrement=True),
        sa.Column("source_id",sa.String(128),sa.ForeignKey("sample_reference_source.source_id",ondelete="RESTRICT"),nullable=False),
        sa.Column("operation_id",sa.String(36),nullable=False),sa.Column("sequence",sa.Integer,nullable=False),
        sa.Column("intent_hash",sa.String(64),nullable=False),sa.Column("commit_hash",sa.String(64),nullable=False),
        sa.Column("pending_hash",sa.String(64),nullable=False),sa.Column("execution_key",sa.String(64),nullable=False),
        sa.Column("request_hash",sa.String(64),nullable=False),sa.Column("previous_operation_id",sa.String(36)),
        sa.Column("mode",sa.String(16),nullable=False),sa.Column("cloud_key",sa.String(64)),
        sa.Column("analysis_id",sa.String(128),sa.ForeignKey("analysis_run.analysis_id",ondelete="RESTRICT")),
        sa.Column("attempt",sa.Integer),sa.Column("generation",sa.Integer),sa.Column("producer_commit",sa.String(40),nullable=False),
        sa.Column("completed_at",sa.DateTime(timezone=True),nullable=False),sa.Column("imported_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("source_id","operation_id",name="uq_reference_operation_id"),
        sa.UniqueConstraint("source_id","sequence",name="uq_reference_operation_sequence"),
        sa.UniqueConstraint("source_id","execution_key",name="uq_reference_operation_execution"))
    op.create_table("sample_reference_history",
        sa.Column("id",ID_TYPE,primary_key=True,autoincrement=True),
        sa.Column("operation_pk",ID_TYPE,sa.ForeignKey("sample_reference_operation.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("role",sa.String(32),nullable=False),sa.Column("row_number",sa.Integer,nullable=False),
        sa.Column("record_key",sa.String(64),nullable=False),sa.Column("resolved_key",sa.String(64)),
        sa.Column("safe_json",sa.JSON,nullable=False),
        sa.UniqueConstraint("operation_pk","role","row_number",name="uq_reference_history_row"))
    op.create_index("ix_reference_history_key","sample_reference_history",["record_key","resolved_key"])

def downgrade():
    raise RuntimeError("Reference history must be retained; restore code without downgrading revision 0023")
