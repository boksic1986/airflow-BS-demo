import pytest

from app.models import AnalysisRun, RuleState
from app.workflow_phases import phase_for_rule, pinned_phase_definitions
from test_wgs_only_platform import make_client, login


@pytest.mark.parametrize("release", ["wgs-4.2.1-cc9bde3", "wgs-4.2.1-34bfcbf"])
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
    filtered = client.get("/api/runs/PHASE-RELEASE/rules?phase=Mapping", headers=headers).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["rule"] == "pre_process_mapping"
    assert "Mapping" in {p["label"] for p in pinned_phase_definitions("wgs", release)}


@pytest.mark.parametrize("release", ["wgs-4.2.0-31de5fb", "wgs-4.2.1-not-audited", "unavailable"])
def test_unregistered_release_has_no_latest_mapping_fallback(release):
    assert phase_for_rule("pre_process_mapping", pipeline_name="wgs", release_id=release) == "Unknown"
    assert [p["label"] for p in pinned_phase_definitions("wgs", release)] == ["Unknown"]
