from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, Sample
from app.pipeline_registry import PipelineAdapter
from app.run_service import list_runs


def make_sessions():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_generic_run_routes_delegate_workflow_projection_to_registered_adapter(
    monkeypatch,
):
    sessions = make_sessions()
    with sessions.begin() as session:
        session.add(
            AnalysisRun(
                analysis_id="SYNTHETIC_001",
                pipeline_name="synthetic",
                dag_id="bio_synthetic",
                status="running",
                workdir="/runs/SYNTHETIC_001",
                params_json={"project_name": "Synthetic project"},
            )
        )
        session.add(
            Sample(
                analysis_id="SYNTHETIC_001",
                sample_id="S1",
                status="running",
                qc_status="unknown",
            )
        )

    adapter = PipelineAdapter(
        adapter_id="synthetic",
        project_run_detail=lambda **_: {"adapter_marker": "detail"},
        project_samples=lambda **_: {
            "items": [{"sample_id": "S1", "adapter_marker": "sample"}],
            "manifest": [],
        },
        project_workflows=lambda **_: {"SYNTHETIC_001": [{"id": "synthetic"}]},
        project_rule_context=lambda **_: {
            "pipeline_name": "synthetic",
            "pipeline_stage": "analysis",
        },
        project_progress=lambda payload, **_: {**payload, "adapter_marker": "progress"},
        project_dashboard_metadata=lambda **_: {
            "batch_no": "SYNTHETIC-BATCH",
            "display_status": "adapter-running",
        },
        project_dashboard_lifecycles=lambda **_: {
            "SYNTHETIC_001": {"delivery": {"status": "not_started"}}
        },
        sync_airflow_status=lambda **_: {"analysis_id": "SYNTHETIC_001", "adapter_marker": "sync"},
        get_log=lambda **_: {"adapter_marker": "log", "lines": []},
        list_logs=lambda **_: {"adapter_marker": "log-index", "items": []},
        list_artifacts=lambda **_: {"adapter_marker": "artifacts", "items": []},
    )
    definition = SimpleNamespace(pipeline_id="synthetic", adapter=adapter)
    settings = SimpleNamespace(auth_required=False)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: sessions)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_airflow_client", lambda: object())
    monkeypatch.setattr(main, "require_pipeline", lambda *args, **kwargs: definition)
    monkeypatch.setattr(main, "deployed_adapters", lambda *_: {"synthetic": adapter})
    monkeypatch.setattr(main, "_active_deployed_pipelines", lambda: ("synthetic",))

    client = TestClient(main.app)
    detail = client.get("/api/runs/SYNTHETIC_001")
    samples = client.get("/api/runs/SYNTHETIC_001/samples")
    progress = client.get("/api/runs/SYNTHETIC_001/progress")
    sync = client.post("/api/runs/SYNTHETIC_001/actions/sync-airflow")
    log = client.get("/api/runs/SYNTHETIC_001/logs")
    log_index = client.get("/api/runs/SYNTHETIC_001/logs/index")
    artifacts = client.get("/api/runs/SYNTHETIC_001/artifacts")
    dashboard = client.get("/api/dashboard/runs?pipeline=deployed")

    assert detail.status_code == 200, detail.text
    assert detail.json()["adapter_marker"] == "detail"
    assert samples.status_code == 200, samples.text
    assert samples.json()["items"][0]["adapter_marker"] == "sample"
    assert progress.status_code == 200, progress.text
    assert progress.json()["adapter_marker"] == "progress"
    assert sync.status_code == 200, sync.text
    assert sync.json()["adapter_marker"] == "sync"
    assert log.status_code == 200, log.text
    assert log.json()["adapter_marker"] == "log"
    assert log_index.status_code == 200, log_index.text
    assert log_index.json()["adapter_marker"] == "log-index"
    assert artifacts.status_code == 200, artifacts.text
    assert artifacts.json()["adapter_marker"] == "artifacts"
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["items"][0]["batch_no"] == "SYNTHETIC-BATCH"
    assert dashboard.json()["items"][0]["display_status"] == "adapter-running"
    assert dashboard.json()["items"][0]["lifecycle"]["delivery"]["status"] == "not_started"

    with sessions() as session:
        payload = list_runs(
            session=session,
            deployed_pipelines=("synthetic",),
            pipeline="deployed",
            workflow_projectors={"synthetic": adapter.project_workflows},
        )
    assert payload["items"][0]["workflow_summary"] == [{"id": "synthetic"}]
