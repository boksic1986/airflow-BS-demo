"""Split WGS OBS upload and download ownership.

Revision ID: 20260907_0016
Revises: 20260906_0015
"""

from alembic import op


revision = "20260907_0016"
down_revision = "20260906_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO obs_transfer_lease (slot_name)
        VALUES ('wgs-obs-upload-01'), ('wgs-obs-download-01')
        ON CONFLICT (slot_name) DO NOTHING
        """
    )


def downgrade() -> None:
    # The rows are intentionally retained. Older code ignores them, while
    # deleting a row that still carries ownership would be unsafe.
    pass
