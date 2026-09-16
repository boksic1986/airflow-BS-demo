"""Nullable unique identity for opt-in native project registration."""
from alembic import op
import sqlalchemy as sa

revision = "20260915_0025"
down_revision = "20260914_0024"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("analysis_run", sa.Column("onprem_project_uuid", sa.String(36), nullable=True))
    op.create_index("uq_analysis_run_onprem_project_uuid", "analysis_run", ["onprem_project_uuid"], unique=True)


def downgrade():
    raise RuntimeError("Retain native project identity; disable registration or restore code without deleting identities")
