"""Record provenance for deterministic handoff logical transaction time."""
from alembic import op
import sqlalchemy as sa

revision = "20260914_0024"
down_revision = "20260914_0023"
branch_labels = None
depends_on = None

def upgrade():
    # Deliberately nullable: existing rows cannot be reinterpreted without
    # authenticated source evidence and remain explicitly unknown.
    op.add_column("sample_reference_operation", sa.Column("logical_time_source", sa.String(64)))

def downgrade():
    raise RuntimeError("Logical-time provenance must be retained; restore code without downgrading revision 0024")
