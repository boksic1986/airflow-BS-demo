from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.models import AnalysisRun
from app.workflow_catalog_service import _latest_run_payload
from app.workflow_phases import WGS_RULE_PHASES, phase_for_rule


WGS_RULE_PATTERN = re.compile(r"^\s*rule\s+([A-Za-z_][A-Za-z0-9_]*)\s*:")
WGS_PHASES = {"Pre-calling", "Variant analysis", "QC"}


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
    assert {phase_for_rule(rule, pipeline_name="wgs") for rule in declared_rules} <= WGS_PHASES
    assert {"mityCallflt", "mergeMTQC", "NormalizeVcf"} <= declared_rules
    assert {"CNVall", "MEIall", "Preall", "QCall", "ROHall", "SMAall", "CSall", "MTall", "REall", "SNVall", "SVall"} <= declared_rules
    assert phase_for_rule("all", pipeline_name="wgs", pipeline_stage="precalling") == "Pre-calling"
    assert phase_for_rule("all", pipeline_name="wgs", pipeline_stage="full") == "QC"


def test_wgs_mapping_overrides_the_pgta_mapping_phase_and_unknown_wgs_rules_stay_in_wgs() -> None:
    assert phase_for_rule("mapping", pipeline_name="wgs") == "Pre-calling"
    assert phase_for_rule("mapping", pipeline_name="pgta") == "Mapping"
    assert phase_for_rule("mapping") == "Mapping"
    assert phase_for_rule("unregistered_future_wgs_rule", pipeline_name="wgs") == "Variant analysis"


def test_workflow_catalog_uses_the_last_canceled_stage_for_an_intentionally_stopped_wgs_run() -> None:
    run = AnalysisRun(
        analysis_id="WGS_DRY_RUN_STOPPED",
        pipeline_name="wgs",
        status="failed",
        workdir="/tmp/wgs",
        current_stage="CNVcalling",
        params_json={"project_name": "WGS dry-run", "wgs_stage": "full"},
    )
    payload = _latest_run_payload(
        run,
        [
            {"label": "Pre-calling", "status": "canceled"},
            {"label": "Variant analysis", "status": "canceled"},
            {"label": "QC", "status": "pending"},
        ],
    )

    assert payload is not None
    assert payload["current_stage"] == "Variant analysis"
