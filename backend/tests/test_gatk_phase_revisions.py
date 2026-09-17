import pytest

from app.workflow_phases import phase_for_rule, pinned_phase_definitions


@pytest.mark.parametrize("revision", ["bd04f6d", "r2", "r3"])
def test_verified_gatk_releases_share_rule_and_summary_phases(revision):
    release = f"gatk-scmc-v7.6.0@{revision}"
    definitions = {row["label"] for row in pinned_phase_definitions("gatk", release)}
    for rule, expected in [("fastp_clean", "FASTQ QC"),
                           ("sentieon_mapping", "Mapping"),
                           ("gatk_haplotype_caller", "Small variant calling")]:
        assert phase_for_rule(rule, pipeline_name="gatk", release_id=release) == expected
        assert expected in definitions
    assert phase_for_rule("new_unverified_rule", pipeline_name="gatk", release_id=release) == "Unknown"


def test_unverified_gatk_release_is_not_silently_classified():
    release = "gatk-scmc-v7.6.0@unverified"
    assert phase_for_rule("fastp_clean", pipeline_name="gatk", release_id=release) == "Unknown"
    assert [row["label"] for row in pinned_phase_definitions("gatk", release)] == ["Unknown"]
