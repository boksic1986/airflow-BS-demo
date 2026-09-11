from app.models import AnalysisRun, RuleState
from test_wgs_only_platform import make_client, login


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
