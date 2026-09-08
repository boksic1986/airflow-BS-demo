from pathlib import Path


def test_gatk_migration_is_additive_and_follows_0017() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260908_0018_gatk_cloud_manual.py"
    )
    text = path.read_text(encoding="utf-8")

    assert 'down_revision = "20260907_0017"' in text
    assert '"pipeline_submission_draft"' in text
    assert '"pipeline_stage_execution"' in text
    assert "wgs_stage_execution" not in text
