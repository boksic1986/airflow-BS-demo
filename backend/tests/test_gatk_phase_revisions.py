import pytest

from app.workflow_phases import GATK_PHASE_RELEASES, phase_for_rule, pinned_phase_definitions


@pytest.mark.parametrize("revision", ["bd04f6d", "r2", "r3", "r4", "r5"])
def test_verified_gatk_releases_share_rule_and_summary_phases(revision):
    release = f"gatk-scmc-v7.6.0@{revision}"
    definitions = {row["label"] for row in pinned_phase_definitions("gatk", release)}
    for rule, expected in [("fastp_clean", "FASTQ QC"),
                           ("sentieon_mapping", "Mapping"),
                           ("gatk_haplotype_caller", "Small variant calling")]:
        assert phase_for_rule(rule, pipeline_name="gatk", release_id=release) == expected
        assert expected in definitions
    assert phase_for_rule("new_unverified_rule", pipeline_name="gatk", release_id=release) == "Unknown"


@pytest.mark.parametrize("revision", ["r4", "r5"])
def test_revision_uses_audited_unchanged_r3_workflow_blob(revision):
    source_blob = "1cf9fe6f1672e919517bd1392bb2fd4496eab702"
    assert GATK_PHASE_RELEASES[f"gatk-scmc-v7.6.0@{revision}"] == source_blob
    assert GATK_PHASE_RELEASES["gatk-scmc-v7.6.0@r3"] == source_blob


@pytest.mark.parametrize("revision", ["unverified", "r5-unverified", "r6"])
def test_unverified_gatk_release_is_not_silently_classified(revision):
    release = f"gatk-scmc-v7.6.0@{revision}"
    assert phase_for_rule("fastp_clean", pipeline_name="gatk", release_id=release) == "Unknown"
    assert [row["label"] for row in pinned_phase_definitions("gatk", release)] == ["Unknown"]
