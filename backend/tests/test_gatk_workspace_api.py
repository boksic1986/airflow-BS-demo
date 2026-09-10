from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, KubernetesWorkload, RuleState, RunStageState, Sample
from app.pipeline_registry_service import clear_pipeline_registry_cache


class _StaleClearedAirflowTimeline:
    def list_task_instances(self, dag_id: str, dag_run_id: str) -> dict:
        assert dag_id == "bio_gatk"
        assert dag_run_id == "GATK_20260908_120000_A1B2C3-a1"
        return {
            "task_instances": [
                {
                    "task_id": "wait_step3_analysis",
                    "state": "up_for_reschedule",
                    "start_date": "2026-09-08T12:10:00Z",
                },
                {
                    "task_id": "wait_step6_materialize",
                    "state": None,
                    "start_date": "2026-09-08T12:20:00Z",
                    "end_date": "2026-09-08T12:20:00Z",
                },
            ]
        }


def _settings(tmp_path: Path) -> SimpleNamespace:
    registry = tmp_path / "pipelines.yaml"
    registry.write_text(
        """version: 1
pipelines:
  wgs:
    display_name: WGS
    dag_id: bio_wgs
    version: 4.1.1
    adapter: wgs
    enabled: true
    submit_enabled: true
    capabilities: [submit, rules, qc, artifacts]
    execution_targets: [cce, local, sge]
  gatk:
    display_name: GATK Cloud
    dag_id: bio_gatk
    version: 7.6.0
    adapter: gatk
    enabled: true
    submit_enabled: true
    capabilities: [submit, rules, artifacts]
    execution_targets: [cce]
""",
        encoding="utf-8",
    )
    return SimpleNamespace(
        deployed_pipelines=("wgs", "gatk"),
        pipeline_registry_path=str(registry),
        wgs_heavy_slot_limit=25,
        wgs_heavy_slot_mode="monitor-only",
        wgs_evidence_root=str(tmp_path / "evidence"),
        gatk_runtime_request_root=str(tmp_path / "runtime" / "requests"),
        gatk_evidence_root=str(tmp_path / "evidence"),
    )


def test_gatk_workspace_rules_and_pods_use_generic_run_projection(
    tmp_path: Path, monkeypatch,
) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    analysis_id = "GATK_20260908_120000_A1B2C3"
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="gatk",
                dag_id="bio_gatk",
                status="running",
                current_stage="step3_monitor",
                progress_percent=0,
                attempt=1,
                dag_run_id=f"{analysis_id}-a1",
                workdir="/runtime/gatk/GATK_20260908_120000_A1B2C3",
                params_json={
                    "project_name": "WES_Clinical",
                    "batch": "20260908A",
                    "runtime_profile_id": "gatk-scmc-v7.6.0",
                    "runtime_profile_revision": "bd04f6d",
                },
            )
        )
        session.add(Sample(analysis_id=analysis_id, sample_id="SCMC001", status="running"))
        session.add(
            RunStageState(
                analysis_id=analysis_id,
                attempt=1,
                stage_code="step3_monitor",
                stage_label="Run GATK analysis",
                stage_status="running",
                progress_available=True,
                progress_percent=38,
                completed_units=70,
                total_units=184,
                unit="rules",
                progress_source="gatk-runtime",
            )
        )
        session.add(
            RuleState(
                analysis_id=analysis_id,
                attempt=1,
                rule_instance_id="mapping:SCMC001",
                rule_name="sentieon_mapping",
                sample_id="SCMC001",
                phase="Mapping",
                status="running",
            )
        )
        session.add(
            KubernetesWorkload(
                analysis_id=analysis_id,
                attempt=1,
                event_id="pod:opaque:42",
                pod_hash="opaque",
                job_name="gatk-worker",
                phase="Running",
            )
        )
        session.commit()

    monkeypatch.setattr(main, "get_sessionmaker", lambda: sessions)
    monkeypatch.setattr(main, "get_settings", lambda: _settings(tmp_path))
    monkeypatch.setattr(main, "get_airflow_client", lambda: _StaleClearedAirflowTimeline())
    clear_pipeline_registry_cache()
    client = TestClient(main.app)

    workspace = client.get(f"/api/runs/{analysis_id}/workspace")
    dashboard = client.get("/api/dashboard/runs?pipeline=gatk")
    rules = client.get(f"/api/runs/{analysis_id}/rules")
    pods = client.get(f"/api/runs/{analysis_id}/pods")

    assert workspace.status_code == 200
    assert workspace.json()["progress"]["stage_label"] == "Run GATK analysis"
    assert workspace.json()["progress"]["progress_percent"] == 38
    assert workspace.json()["progress"]["current_rule"] == "sentieon_mapping"
    assert workspace.json()["progress"]["orchestration_stages"][-1]["label"] == "Finalize"
    assert rules.status_code == 200
    assert rules.json()["items"][0]["phase"] == "Mapping"
    assert [item["label"] for item in rules.json()["phases"]] == [
        "FASTQ QC",
        "Mapping",
        "MarkDuplicates",
        "GATK",
        "chrM realignment",
        "Delivery",
    ]
    assert pods.status_code == 200
    assert pods.json()["items"][0]["job_name"] == "gatk-worker"
    assert dashboard.status_code == 200
    dashboard_run = dashboard.json()["items"][0]
    assert dashboard_run["current_stage_label"] == "Run GATK analysis"
    assert dashboard_run["current_airflow_task"] is None
    assert dashboard_run["percent"] == 38
    assert dashboard_run["stage_progress"] == {
        "available": True,
        "percent": 38,
        "completed_units": 70,
        "total_units": 184,
        "unit": "rules",
        "current_item": None,
        "speed_bps": None,
        "eta_seconds": None,
        "source": "gatk-runtime",
        "updated_at": dashboard_run["stage_progress"]["updated_at"],
    }
