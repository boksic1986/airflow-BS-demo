"""W423 synthetic ingest/API frames; accepted CCE producers are separate evidence."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models import AnalysisRun, RuleEventRaw
from app.wgs_observer import ingest_bound_pipeline_evidence_once
from test_wgs_only_platform import make_client, login


@pytest.mark.parametrize("pipeline", ["wgs", "gatk"])
def test_group_event_frames_reach_rules_api(tmp_path, monkeypatch, pipeline):
    from app import main

    client, sessions, _ = make_client(tmp_path, monkeypatch)
    settings = main.get_settings()
    settings.deployed_pipelines = ("wgs", "gatk")
    settings.pipeline_registry_path = str(Path(__file__).resolve().parents[2] / "config/pipelines.yaml")
    settings.gatk_runtime_request_root = str(tmp_path / "gatk-requests")
    settings.gatk_evidence_root = str(tmp_path / "gatk-evidence")
    aid = f"GROUP_RELEASE_{pipeline}"
    release = "wgs-4.2.1-cc9bde3" if pipeline == "wgs" else "gatk-scmc-v7.6.0@r3"
    root = tmp_path / "synthetic-evidence"
    directory = root / aid / "attempt-2"
    raw = directory / "rule-status/raw/worker.jsonl"
    raw.parent.mkdir(parents=True)
    with sessions() as session:
        session.add(AnalysisRun(analysis_id=aid, pipeline_name=pipeline, dag_id=f"bio_{pipeline}",
                                workdir=str(tmp_path), attempt=2, status="running",
                                params_json={"pipeline_release_id": release}))
        session.commit()
    names = ["mapping", "Dedup"] if pipeline == "wgs" else ["sentieon_mapping", "gatk_mark_duplicates"]
    members = [{"rule": name, "snakemake_jobid": str(index + 1)} for index,name in enumerate(names)]
    label = "cce-run-1111111111111111"
    def event(kind, timestamp, **fields):
        return {"schema_version":"1", "event":kind, "timestamp":timestamp,
                "run_label":label, "attempt":"attempt-2", "role":"worker",
                "stream_id":"worker-a", **fields}
    def ingest(events):
        with raw.open("a") as stream:
            stream.writelines(json.dumps(value)+"\n" for value in events)
        result = ingest_bound_pipeline_evidence_once(session_factory=sessions, analysis_id=aid,
            attempt=2, pipeline_release_id=release, run_label=label,
            evidence_root=root, evidence_directory=directory)
        assert result["errors"] == 0
        return result
    headers = login(client,"viewer","viewer-pass")
    def page():
        response = client.get(f"/api/runs/{aid}/rules?status=&limit=20",headers=headers)
        assert response.status_code == 200
        return response.json()
    planned = [event("rule_planned",1.0,role="master",stream_id="master-a",
                     rule_instance_id=f"rule-{index}",rule_name=name,job_id=str(index+1),
                     group_member=True, execution_group="group-01",execution_group_members=members)
               for index,name in enumerate(names)]
    assert ingest(planned)["events_ingested"] == 2
    waiting = page()
    assert waiting["total"] == 2
    assert all(item["status"] == "planned" and item["started_at"] is None
               and item["execution_group"] and item["timing_provenance"] == "group_only"
               for item in waiting["items"])
    # An early unnamed start joins only its stream/job's later declaration.
    started = [event("job_started",2.0,job_id="1"),
               event("job_info",2.1,job_id="1",rule_instance_id="rule-0",
                     rule_name=names[0],group_member=False)]
    assert ingest(started)["events_ingested"] == 2
    running = page()
    rows = {item["rule"]:item for item in running["items"]}
    assert rows[names[0]]["status"] == "running"
    started_at = datetime.fromisoformat(rows[names[0]]["started_at"])
    # SQLite fixtures return naive UTC; production timestamps may include UTC.
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    assert started_at.timestamp() == 2
    assert rows[names[1]]["status"] == "planned" and rows[names[1]]["started_at"] is None
    assert ingest(started)["events_ingested"] == 0
    ended = [event("job_finished",3.0,job_id="1"),
             event("job_info",3.1,job_id="2",rule_instance_id="rule-1",rule_name=names[1],group_member=False),
             event("job_started",4.0,job_id="2"),event("job_error",5.0,job_id="2",message="synthetic failure")]
    assert ingest(ended)["events_ingested"] == 4
    terminal = page()
    rows = {item["rule"]:item for item in terminal["items"]}
    assert rows[names[0]]["status"] == "success" and rows[names[0]]["elapsed_seconds"] == 1
    assert rows[names[1]]["status"] == "failed" and rows[names[1]]["elapsed_seconds"] == 1
    assert rows[names[1]]["message"] == "synthetic failure"
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(RuleEventRaw).where(RuleEventRaw.analysis_id==aid)) == 8
    export = os.environ.get("GROUP_RULE_FRAME_EXPORT")
    if export:
        Path(export, f"{pipeline}-group-frames.json").write_text(json.dumps(
            {"source":"synthetic-ingest-api", "waiting":waiting,"running":running,"terminal":terminal},
            sort_keys=True)+"\n")
