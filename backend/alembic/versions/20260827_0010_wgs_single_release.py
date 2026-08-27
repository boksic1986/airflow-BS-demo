"""replace WGS development snapshot identity with one published release

Revision ID: 20260827_0010
Revises: 20260826_0009
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260827_0010"
down_revision = "20260826_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "observer_run_state",
        "pipeline_snapshot_id",
        new_column_name="pipeline_release_id",
        existing_type=sa.String(length=256),
        existing_nullable=False,
    )
    op.execute(
        """
        UPDATE analysis_run
        SET params_json = (params_json - 'pipeline_snapshot_id' - 'source_commit'
                           - 'snapshot_manifest_sha256')
                          || jsonb_build_object(
                               'pipeline_release_id', params_json->>'pipeline_snapshot_id',
                               'wgs_source_commit', params_json->>'source_commit'
                             )
        WHERE pipeline_name = 'wgs'
          AND params_json ? 'pipeline_snapshot_id'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE analysis_run
        SET params_json = (params_json - 'pipeline_release_id' - 'wgs_source_commit')
                          || jsonb_build_object(
                               'pipeline_snapshot_id', params_json->>'pipeline_release_id',
                               'source_commit', params_json->>'wgs_source_commit'
                             )
        WHERE pipeline_name = 'wgs'
          AND params_json ? 'pipeline_release_id'
        """
    )
    op.alter_column(
        "observer_run_state",
        "pipeline_release_id",
        new_column_name="pipeline_snapshot_id",
        existing_type=sa.String(length=256),
        existing_nullable=False,
    )
