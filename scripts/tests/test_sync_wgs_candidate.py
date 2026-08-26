from pathlib import Path


def test_candidate_sync_is_copy_only_and_excludes_repository_state() -> None:
    source = (Path(__file__).parents[1] / "sync_wgs_candidate.sh").read_text(
        encoding="utf-8"
    )

    assert "unexpected WGS source root" in source
    assert "unexpected Airflow development root" in source
    assert "rsync -a" in source
    assert "--exclude='.git/'" in source
    assert "--exclude='prepare/config.yaml'" in source
    assert "--exclude='script/z1.upload.sh'" in source
    assert "--exclude='script/z3.save.sh'" in source
    assert "--exclude='script/z4.delete_tmp.sh'" in source
    assert "--exclude='script/z5.archive.sh'" in source
    assert "--exclude='script/z6.sendmail.sh'" in source
    assert "SOURCE_PROVENANCE.json" in source
    assert "SNAPSHOT_MANIFEST.sha256" in source
    assert 'execution_enabled": false' in source
    assert "/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1)" in source
    assert "3489b3958869e5cfab983aca1eb9c7f158c06dff" in source
    assert "source worktree must be clean" in source
    assert 'snapshot_id="wgs-v4.1.1-candidate-' in source
    assert "cce_pipeline_version=0.5.0" in source
    assert '"cce_pipeline_version": "${cce_pipeline_version}"' in source
    assert '"cce_pipeline_source_commit":' in source
    assert "cce_profile_id=wgs-4.1.1-r1" in source
    assert '"cce_profile_id": "${cce_profile_id}"' in source
    assert '"master_image_digest":' in source
    assert "source repository is copy-only" in source
