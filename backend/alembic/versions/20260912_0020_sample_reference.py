"""Add the independent sample-reference audit store.

Revision ID: 20260912_0020
Revises: 20260908_0019
"""

from alembic import op
import sqlalchemy as sa


revision = "20260912_0020"
down_revision = "20260908_0019"
branch_labels = None
depends_on = None

ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "sample_reference_source",
        sa.Column("id", ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("next_generation", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "latest_reserved_generation",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("latest_applied_generation", sa.Integer()),
        sa.Column("last_good_generation", sa.Integer()),
        sa.Column("last_good_content_hash", sa.String(length=64)),
        sa.Column("last_good_at", sa.DateTime(timezone=True)),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "sync_status", sa.String(length=32), nullable=False, server_default="never"
        ),
        sa.Column("sync_reason", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_sample_reference_source_type_status",
        "sample_reference_source",
        ["source_type", "sync_status"],
    )
    op.create_table(
        "sample_reference_snapshot",
        sa.Column("id", ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column(
            "source_id",
            sa.String(length=128),
            sa.ForeignKey("sample_reference_source.source_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("diagnostic_code", sa.String(length=64)),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_id",
            "generation",
            name="uq_sample_reference_snapshot_generation",
        ),
    )
    op.create_index(
        "ix_sample_reference_snapshot_source_status",
        "sample_reference_snapshot",
        ["source_id", "status"],
    )
    op.create_table(
        "sample_reference",
        sa.Column("id", ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column(
            "source_id",
            sa.String(length=128),
            sa.ForeignKey("sample_reference_source.source_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("record_key", sa.String(length=64), nullable=False),
        sa.Column("sample_id", sa.String(length=128), nullable=False),
        sa.Column("family_id", sa.String(length=128)),
        sa.Column("order_number_masked", sa.String(length=32)),
        sa.Column("sequencing_batch", sa.String(length=128)),
        sa.Column("analysis_batch", sa.String(length=128)),
        sa.Column("data_id", sa.String(length=128)),
        sa.Column("pending", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(length=64)),
        sa.Column("content_version", sa.String(length=64), nullable=False),
        sa.Column("last_good_generation", sa.Integer(), nullable=False),
        sa.Column("last_good_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "present_in_latest_complete",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "needs_review", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("conflict_reason", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_id", "record_key", name="uq_sample_reference_source_record"
        ),
    )
    op.create_index(
        "ix_sample_reference_sample_source",
        "sample_reference",
        ["sample_id", "source_id", "record_key"],
    )
    op.create_index(
        "ix_sample_reference_family", "sample_reference", ["family_id"]
    )
    op.create_index(
        "ix_sample_reference_order", "sample_reference", ["order_number_masked"]
    )
    op.create_index(
        "ix_sample_reference_batches",
        "sample_reference",
        ["sequencing_batch", "analysis_batch"],
    )
    op.create_index(
        "ix_sample_reference_membership",
        "sample_reference",
        ["present_in_latest_complete", "pending"],
    )


def downgrade() -> None:
    # A no-op downgrade would stamp 0019 while leaving tables that its next
    # upgrade tries to create. Refuse before DDL or Alembic revision mutation.
    raise RuntimeError(
        "Sample-reference audit schema cannot be downgraded; use source-only rollback "
        "and retain revision 20260912_0020 and its audit data."
    )
