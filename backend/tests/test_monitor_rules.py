from app.models import AnalysisRun, RuleState
from test_wgs_only_platform import make_client, login
import pytest


@pytest.mark.parametrize("pipeline,clean,map_rule,release", [
    ("gatk", "fastp_clean", "sentieon_mapping", "gatk-scmc-v7.6.0@bd04f6d"),
    ("wgs", "pre_process_cleanFastq", "mapping", "wgs-4.2.1-cc9bde3"),
])
def test_phase_summary_ignores_row_filters_but_preserves_attempt(tmp_path, monkeypatch, pipeline, clean, map_rule, release):
    from app import main
    from pathlib import Path

    client, sessions, _ = make_client(tmp_path, monkeypatch)
    main.get_settings().deployed_pipelines = ("wgs", "gatk")
    main.get_settings().pipeline_registry_path = str(Path(__file__).resolve().parents[2] / "config" / "pipelines.yaml")
    main.get_settings().gatk_runtime_request_root = str(tmp_path / "gatk-requests")
    main.get_settings().gatk_evidence_root = str(tmp_path / "gatk-evidence")
    with sessions() as session:
        session.add(AnalysisRun(analysis_id="SUMMARY", pipeline_name=pipeline, dag_id=f"bio_{pipeline}", workdir=str(tmp_path), attempt=2, status="running", params_json={"pipeline_release_id": release}))
        for attempt, instance, name, status, sample, family in [
            (1, "old", clean, "failed", "S0", "F0"),
            (2, "active", clean, "running", "S1", "F1"),
            (2, "done", clean, "success", "S2", "F2"),
            (2, "next", map_rule, "running", "S2", "F2"),
        ]:
            session.add(RuleState(analysis_id="SUMMARY", attempt=attempt, rule_instance_id=instance, rule_name=name, status=status, sample_id=sample, family_id=family))
        session.commit()
    headers = login(client, "viewer", "viewer-pass")
    for filters, expected_total in [
        ({}, 3), ({"status": "running"}, 2), ({"status": "success"}, 1),
        ({"status": "failed"}, 0), ({"phase": "Mapping"}, 1),
        ({"sample_id": "S1"}, 1), ({"family_id": "F1"}, 1),
        ({"rule": map_rule}, 1), ({"status": "running", "offset": 1}, 2),
    ]:
        response = client.get("/api/runs/SUMMARY/rules", params={"limit": 1, **filters}, headers=headers)
        assert response.status_code == 200
        page = response.json()
        assert page["total"] == expected_total
        assert page["filter_options"] == {"sample_ids": ["S1", "S2"], "family_ids": ["F1", "F2"]}
        assert len(page["items"]) == min(1, expected_total)
        if page["items"] and filters.get("status"):
            assert page["items"][0]["status"] == filters["status"]
        summaries = {item["phase"]: item for item in page["phase_summaries"]}
        assert set(summaries) == {"FASTQ QC", "Mapping"}
        assert [summaries["FASTQ QC"][key] for key in ("total", "running", "success", "failed", "status")] == [2, 1, 1, 0, "running"]
        assert [summaries["Mapping"][key] for key in ("total", "running", "success")] == [1, 1, 0]
    old = client.get("/api/runs/SUMMARY/rules?attempt=1&status=success", headers=headers).json()
    assert old["total"] == 0
    assert old["items"] == []
    assert old["filter_options"] == {"sample_ids": ["S0"], "family_ids": ["F0"]}
    assert [(item["phase"], item["total"], item["failed"]) for item in old["phase_summaries"]] == [("FASTQ QC", 1, 1)]


@pytest.mark.parametrize("states,expected", [(["canceled"], "canceled"), (["success", "cancelled"], "canceled"), (["running", "canceled"], "running"), (["planned", "canceled"], "planned"), (["failed", "canceled"], "failed")])
def test_phase_terminal_precedence(tmp_path, monkeypatch, states, expected):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    with sessions() as session:
        session.add(AnalysisRun(analysis_id="PHASE", pipeline_name="wgs", dag_id="bio_wgs", workdir=str(tmp_path), attempt=1, status="running", params_json={"pipeline_release_id": "wgs-4.2.1-cc9bde3"}))
        for i, status in enumerate(states):
            session.add(RuleState(analysis_id="PHASE", attempt=1, rule_instance_id=str(i), rule_name="mapping", status=status))
        session.commit()
    page = client.get("/api/runs/PHASE/rules?phase=Mapping&limit=1", headers=login(client, "viewer", "viewer-pass")).json()
    assert page["total"] == len(states)
    assert page["phase_summaries"][0]["status"] == expected
    assert page["items"][0]["phase"] == "Mapping"


def test_group_only_start_is_not_child_execution(tmp_path, monkeypatch):
    from app.models import RuleEventRaw
    from app.wgs_observer import _rebuild_rule_projection
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    with sessions() as session:
        session.add(AnalysisRun(analysis_id="GROUP", pipeline_name="wgs", dag_id="bio_wgs", workdir=str(tmp_path), attempt=1, status="running"))
        session.add(RuleEventRaw(analysis_id="GROUP", attempt=1, event_id="group", event_type="job_started", payload_json={"rule_instance_id": "child", "event": "job_started", "rule_name": "mapping", "group_member": True, "role": "master", "stream_id": "master", "timestamp": 1000}))
        session.flush()
        _rebuild_rule_projection(session, "GROUP", 1)
        session.commit()
    page = client.get("/api/runs/GROUP/rules", headers=login(client, "viewer", "viewer-pass")).json()
    assert page["items"][0]["started_at"] is None
    assert page["items"][0]["status"] == "planned"
    assert page["items"][0]["execution_group_members"] == []


def test_group_members_survive_pagination_and_keep_stream_identity(tmp_path, monkeypatch):
    from app.models import RuleEventRaw
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    members = [{"rule": "mapping", "snakemake_jobid": "1"}, {"rule": "Dedup", "snakemake_jobid": "2"}]
    with sessions() as session:
        session.add(AnalysisRun(analysis_id="MEMBERS", pipeline_name="wgs", dag_id="bio_wgs", workdir=str(tmp_path), attempt=1, status="running"))
        for stream in ["master", "worker"]:
            session.add(RuleState(analysis_id="MEMBERS", attempt=1, rule_instance_id=stream, rule_name="mapping", status="planned"))
            session.add(RuleEventRaw(analysis_id="MEMBERS", attempt=1, event_id=stream, event_type="rule_planned", payload_json={"rule_instance_id": stream, "group_member": True, "role": stream, "stream_id": stream, "execution_group": "same-group", "execution_group_members": members}))
        session.commit()
    headers = login(client, "viewer", "viewer-pass")
    first = client.get("/api/runs/MEMBERS/rules?limit=1", headers=headers).json()["items"][0]
    second = client.get("/api/runs/MEMBERS/rules?limit=1&offset=1", headers=headers).json()["items"][0]
    assert first["execution_group_members"] == second["execution_group_members"] == members
    assert first["execution_group"] != second["execution_group"]
    assert first["started_at"] is second["started_at"] is None


def test_current_attempt_default_history_and_exact_filters(tmp_path, monkeypatch):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "viewer", "viewer-pass")
    with sessions() as session:
        session.add(AnalysisRun(analysis_id="MONITOR", pipeline_name="wgs", dag_id="bio_wgs", workdir=str(tmp_path), attempt=2, status="success"))
        for attempt, instance, sample, family in [(1, "old", "S1", "F1"), (2, "new1", "S1", "F1"), (2, "new2", "F1", "F2")]:
            session.add(RuleState(analysis_id="MONITOR", attempt=attempt, rule_instance_id=instance, rule_name="mapping", sample_id=sample, family_id=family, status="running"))
        session.commit()
    current = client.get("/api/runs/MONITOR/rules?limit=1", headers=headers).json()
    assert current["total"] == 2
    assert current["attempt"] == 2
    assert current["attempts"] == [1, 2]
    assert current["items"][0]["attempt"] == 2
    assert current["items"][0]["status_inferred"] is True
    assert sum(item["total"] for item in current["phase_summaries"]) == 2
    assert client.get("/api/runs/MONITOR/rules?status=success", headers=headers).json()["total"] == 2
    old = client.get("/api/runs/MONITOR/rules?attempt=1", headers=headers).json()
    assert old["total"] == 1
    assert old["items"][0]["status"] == "running"
    assert old["items"][0]["status_inferred"] is False
    selected = client.get("/api/runs/MONITOR/rules?sample_id=S1&family_id=F1", headers=headers).json()
    assert selected["total"] == 1
    assert selected["items"][0]["rule_instance_id"] == "new1"
    assert client.get("/api/runs/MONITOR/rules?attempt=0", headers=headers).status_code == 422


def test_restarted_same_instance_does_not_keep_old_end_or_start(tmp_path, monkeypatch):
    from app.models import RuleEventRaw
    from app.wgs_observer import _rebuild_rule_projection
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    with sessions() as session:
        session.add(AnalysisRun(analysis_id="RETRY", pipeline_name="wgs", dag_id="bio_wgs", workdir=str(tmp_path), attempt=1, status="running"))
        for timestamp, event in [(1000, "job_started"), (1100, "job_error"), (1200, "job_started")]:
            session.add(RuleEventRaw(analysis_id="RETRY", attempt=1, event_id=str(timestamp), event_type=event, payload_json={"rule_instance_id": "child", "event": event, "rule_name": "mapping", "role": "worker", "stream_id": "worker", "timestamp": timestamp}))
        session.flush()
        _rebuild_rule_projection(session, "RETRY", 1)
        session.commit()
    item = client.get("/api/runs/RETRY/rules", headers=login(client, "viewer", "viewer-pass")).json()["items"][0]
    assert item["status"] == "running"
    assert item["ended_at"] is None
    assert item["started_at"].startswith("1970-01-01T00:20:00")
