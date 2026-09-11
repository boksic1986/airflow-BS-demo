import pytest
from app.workflow_phases import phase_for_rule


@pytest.mark.parametrize("pipeline,release,rule,expected", [
    ("wgs", "wgs-4.2.1-cc9bde3", "pre_process_mapping", "Mapping"),
    ("wgs", "wgs-4.2.1-cc9bde3", "pre_process_gvcf_calling", "Small variant calling"),
    ("wgs", "wgs-4.2.1-cc9bde3", "SNV_vep", "SNV analysis"),
    ("wgs", "wgs-4.2.1-cc9bde3", "CNV_call_sample", "CNV analysis"),
    ("wgs", "wgs-4.2.1-cc9bde3", "CNV_invented", "Unknown"),
    ("wgs", "unsupported", "mapping", "Unknown"),
    ("gatk", "gatk-scmc-v7.6.0@bd04f6d", "gatk_bqsr", "Base recalibration"),
    ("gatk", "gatk-scmc-v7.6.0@bd04f6d", "gatk_haplotype_caller", "Small variant calling"),
    ("gatk", "gatk-scmc-v7.6.0@bd04f6d", "gatk_genotype", "Genotyping"),
    ("gatk", "gatk-scmc-v7.6.0@bd04f6d", "gatk_mity", "Mitochondrial analysis"),
    ("gatk", "gatk-scmc-v7.6.0@bd04f6d", "gatk_invented", "Unknown"),
    ("gatk", "unsupported", "gatk_bqsr", "Unknown"),
])
def test_release_pinned_biological_phases(pipeline, release, rule, expected):
    assert phase_for_rule(rule, pipeline_name=pipeline, release_id=release) == expected
