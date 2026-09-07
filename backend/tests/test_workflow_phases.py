from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.workflow_phases import WGS_RULE_PHASES, phase_for_rule, wgs_phase_for_rule


WGS_RULE_PATTERN = re.compile(r"^\s*rule\s+([A-Za-z_][A-Za-z0-9_]*)\s*:")
WGS_PHASES = {"Pre-calling", "Variant analysis", "QC", "Cloud delivery"}


def _declared_wgs_rules() -> set[str] | None:
    root = Path(__file__).resolve().parents[2] / "pipelines" / "wgs_s9"
    if not root.is_dir():
        return None
    return {
        match.group(1)
        for path in [*root.rglob("*.smk"), *root.glob("*.Snakefile")]
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := WGS_RULE_PATTERN.match(line))
    }


def test_wgs_rule_classifier_exhaustively_covers_repo_owned_snakemake_catalog() -> None:
    declared_rules = _declared_wgs_rules()
    if declared_rules is None:
        pytest.skip("repo-owned WGS catalog is outside the backend-only image context")

    assert declared_rules == set(WGS_RULE_PHASES) | {"all"}
    assert {wgs_phase_for_rule(rule) for rule in declared_rules} <= WGS_PHASES
    assert {"mityCallflt", "mergeMTQC", "NormalizeVcf"} <= declared_rules
    assert {"CNVall", "MEIall", "Preall", "QCall", "ROHall", "SMAall", "CSall", "MTall", "REall", "SNVall", "SVall"} <= declared_rules
    assert wgs_phase_for_rule("all", pipeline_stage="precalling") == "Pre-calling"
    assert wgs_phase_for_rule("all", pipeline_stage="full") == "QC"


def test_wgs_mapping_and_unknown_rules_stay_in_the_wgs_projection() -> None:
    assert wgs_phase_for_rule("mapping") == "Pre-calling"
    assert phase_for_rule("mapping") == "Pipeline"
    assert wgs_phase_for_rule("unregistered_future_wgs_rule") == "Variant analysis"


@pytest.mark.parametrize(
    ("rule", "phase"),
    [
        ("pre_process_cleanFastq", "Pre-calling"),
        ("pre_process_Haplotyper", "Pre-calling"),
        ("SNV_GVCFtyper", "Variant analysis"),
        ("CNV_call_sample", "Variant analysis"),
        ("MT_mityCall", "Variant analysis"),
        ("QC_mergeQC", "QC"),
        ("cloud_package_results", "Cloud delivery"),
        ("cloud_finalize_delivery", "Cloud delivery"),
    ],
)
def test_wgs_411_module_rule_names_map_to_their_production_phase(rule: str, phase: str) -> None:
    assert wgs_phase_for_rule(rule) == phase
