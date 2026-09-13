"""Add batch-only Samplelist intake without adopting or relabeling legacy rows."""
from alembic import op
import sqlalchemy as sa

revision = "20260912_0021"
down_revision = "20260912_0020"
branch_labels = None
depends_on = None
ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    with op.batch_alter_table("wgs_intake_batch") as batch:
        batch.alter_column("source_path", existing_type=sa.Text(), nullable=True)
        batch.alter_column("chip_id", existing_type=sa.String(256), nullable=True)
        batch.add_column(sa.Column("discovery_mode", sa.String(32), nullable=False, server_default="t7_scan_only"))
        for name, size in (("project_id", 128), ("platform_id", 64), ("root_id", 128),
                           ("source_identity", 64), ("source_version", 64),
                           ("bound_directory_identity", 128), ("reason_code", 64)):
            batch.add_column(sa.Column(name, sa.String(size), nullable=True))
        batch.create_unique_constraint("uq_wgs_intake_scoped_batch", ["project_id", "platform_id", "sequencing_batch"])
    op.create_table("wgs_samplelist_source",
        sa.Column("source_identity", sa.String(64), primary_key=True),
        sa.Column("baseline_complete", sa.Boolean(), nullable=False),
        sa.Column("first_scan_at", sa.DateTime(timezone=True)),
        sa.Column("last_scan_at", sa.DateTime(timezone=True)),
        sa.Column("reason_code", sa.String(64)))
    op.create_table("wgs_samplelist_observation",
        sa.Column("id", ID_TYPE, primary_key=True, autoincrement=True),
        sa.Column("source_identity", sa.String(64), sa.ForeignKey("wgs_samplelist_source.source_identity"), nullable=False),
        sa.Column("file_identity", sa.String(64), nullable=False),
        sa.Column("is_baseline", sa.Boolean(), nullable=False),
        sa.Column("observed_version", sa.String(64)),
        sa.Column("observation_token", sa.String(64)),
        sa.Column("stable_count", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason_code", sa.String(64)),
        sa.UniqueConstraint("source_identity", "file_identity", name="uq_wgs_samplelist_file"))


def downgrade():
    raise RuntimeError("AF05 audit schema is retained; restore code without downgrading revision 0021")
