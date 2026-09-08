from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, KubernetesWorkload, RuleState, RunStageState, Sample
from app.pipeline_registry_service import clear_pipeline_registry_cache


def _settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        deployed_pipelines=("wgs", "gatk"),
        pipeline_registry_path=str(Path(__file__).parents[2] / "config" / "pipelines.yaml"),
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
                progress_percent=25,
                attempt=1,
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
                progress_percent=25,
                completed_units=1,
                total_units=4,
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
    clear_pipeline_registry_cache()
    client = TestClient(main.app)

    workspace = client.get(f"/api/runs/{analysis_id}/workspace")
    rules = client.get(f"/api/runs/{analysis_id}/rules")
    pods = client.get(f"/api/runs/{analysis_id}/pods")

    assert workspace.status_code == 200
    assert workspace.json()["progress"]["stage_label"] == "Run GATK analysis"
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
