import pytest

from app.models import AnalysisRun, RuleState
from app.workflow_phases import PINNED_WGS_PHASES, phase_for_rule, pinned_phase_definitions
from test_wgs_only_platform import make_client, login


@pytest.mark.parametrize("release", ["wgs-4.2.1-cc9bde3", "wgs-4.2.1-34bfcbf", "wgs-4.2.1-ebf1f4b", "wgs-4.2.3-bafd27c"])
def test_audited_release_rules_and_filters_share_exact_phases(tmp_path, monkeypatch, release):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    with sessions() as session:
        session.add(AnalysisRun(analysis_id="PHASE-RELEASE", pipeline_name="wgs", dag_id="bio_wgs",
                               workdir=str(tmp_path), attempt=1, status="running",
                               params_json={"pipeline_release_id": release}))
        for rule in ["pre_process_cleanFastq", "pre_process_mapping", "pre_process_Dedup", "pre_process_not_a_real_rule"]:
            session.add(RuleState(analysis_id="PHASE-RELEASE", attempt=1, rule_instance_id=rule,
                                  rule_name=rule, status="planned"))
        session.commit()
    headers = login(client, "viewer", "viewer-pass")
    page = client.get("/api/runs/PHASE-RELEASE/rules", headers=headers).json()
    assert {r["rule"]: r["phase"] for r in page["items"]} == {
        "pre_process_cleanFastq": "FASTQ QC", "pre_process_mapping": "Mapping",
        "pre_process_Dedup": "Duplicate marking", "pre_process_not_a_real_rule": "Unknown"}
    assert {row["phase"]: row["total"] for row in page["phase_summaries"]} == {
        "FASTQ QC": 1, "Mapping": 1, "Duplicate marking": 1, "Unknown": 1}
    filtered = client.get("/api/runs/PHASE-RELEASE/rules?phase=Mapping", headers=headers).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["rule"] == "pre_process_mapping"
    assert "Mapping" in {p["label"] for p in pinned_phase_definitions("wgs", release)}


@pytest.mark.parametrize("release", ["wgs-4.2.0-31de5fb", "wgs-4.2.1-not-audited", "wgs-4.2.1-ebf1f4b-unreviewed", "unavailable", "wgs-4.2.3-bafd27c-unreviewed"])
def test_unregistered_release_has_no_latest_mapping_fallback(release):
    assert phase_for_rule("pre_process_mapping", pipeline_name="wgs", release_id=release) == "Unknown"
    assert [p["label"] for p in pinned_phase_definitions("wgs", release)] == ["Unknown"]


def test_wgs_423_retains_422_additions_and_registers_fixed_source_changes():
    release = "wgs-4.2.3-bafd27c"
    additions = PINNED_WGS_PHASES["verified_rule_additions"][release]
    assert PINNED_WGS_PHASES["verified_equivalent_releases"][release] == "bafd27ce5f38e736aae516d5c00247e449872479"
    assert len(additions) == 18
    inherited = PINNED_WGS_PHASES["verified_rule_additions"]["wgs-4.2.2-441d5e7"]
    new_rules = {"limsQC": "QC", "QC_limsQC": "QC", "auto_qc": "QC", "QC_auto_qc": "QC",
                 "varid_txt2vcf": "SNV analysis", "SNV_varid_txt2vcf": "SNV analysis"}
    assert additions == {**inherited, **new_rules}
    for rule, expected in additions.items():
        assert phase_for_rule(rule, pipeline_name="wgs", release_id=release) == expected
    assert phase_for_rule("QC_new_unverified_rule", pipeline_name="wgs", release_id=release) == "Unknown"
    assert phase_for_rule("QC_auto_qc", pipeline_name="wgs", release_id="wgs-4.2.2-441d5e7") == "Unknown"
    assert PINNED_WGS_PHASES["verified_source_overrides"][release] == {
        "rule/QC.smk": "7f3473263c8662abfd420667b89b6b23e354b1f7",
        "rule/ROH.smk": "ceee94ac2b1ed73121ec18e3a182fde642b36acf",
        "rule/SMA.smk": "2d91062ce0d468eb5bbaedc32258e575e15bf94a",
        "rule/WGS_CS.smk": "98019846ea052f145c124eeb7f2da8544100b45a",
        "rule/WGS_IPMCH.smk": "e488c08d13bdd65a18c71f26b02fd51542fadf6c",
        "rule/WGS_MT.smk": "713c56540b010c2e804da0aceaa1d2cb39f3d2ff",
        "rule/WGS_SNV.smk": "5010e11c0d730324469f6a76d8c4d30c758cb4e8",
    }
