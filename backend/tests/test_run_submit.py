from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, RunAction


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def insert_pgta_run(session_factory, tmp_path, *, status_value: str = "created", target: str = "metadata") -> str:
    analysis_id = "PGTA_20260703_010000_TEST01"
    workdir = tmp_path / "shared" / "runs" / analysis_id
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True)
    manifest = config_dir / "samples.selected.tsv"
    manifest.write_text("sample_id\tR1\tR2\tsource_dir\nG1\t/data/R1.fq.gz\t/data/R2.fq.gz\t/data\n", encoding="utf-8")
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="pgta",
                dag_id="bio_pgta",
                dag_run_id=None,
                mode="new",
                status=status_value,
                sample_sheet_path=str(manifest),
                workdir=str(workdir),
                params_json={
                    "target": target,
                    "rawdata_root": "/data/project/CNV/PGT-A/rawdata/demo",
                    "input_mode": "server_path_scan",
                    "selected_count": 1,
                },
                email_to="demo@example.com",
            )
        )
        session.commit()
    return analysis_id


class FakeAirflowClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trigger_dag_run(self, dag_id: str, *, dag_run_id: str | None = None, conf: dict | None = None) -> dict:
        self.calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf})
        return {"dag_run_id": dag_run_id or "manual__from_airflow"}


def test_submit_created_pgta_run_triggers_airflow_and_updates_db(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(session_factory, tmp_path)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(airflow_base_url="http://airflow-api-server:8080"),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/submit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"] == analysis_id
    assert payload["status"] == "submitted"
    assert payload["dag_id"] == "bio_pgta"
    assert payload["dag_run_id"] == f"manual__{analysis_id}"
    assert fake_airflow.calls == [
        {
            "dag_id": "bio_pgta",
            "dag_run_id": f"manual__{analysis_id}",
            "conf": {
                "analysis_id": analysis_id,
                "pipeline": "pgta",
                "mode": "new",
                "sample_sheet_path": str(tmp_path / "shared" / "runs" / analysis_id / "config" / "samples.selected.tsv"),
                "workdir": str(tmp_path / "shared" / "runs" / analysis_id),
                "email_to": "demo@example.com",
                "params": {
                    "target": "metadata",
                    "rawdata_root": "/data/project/CNV/PGT-A/rawdata/demo",
                    "input_mode": "server_path_scan",
                    "selected_count": 1,
                },
            },
        }
    ]
    with session_factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        actions = session.scalars(select(RunAction).where(RunAction.analysis_id == analysis_id)).all()
    assert run.status == "submitted"
    assert run.dag_run_id == f"manual__{analysis_id}"
    assert actions[0].action == "submit"
    assert actions[0].result_status == "accepted"


def test_submit_rejects_runs_that_are_not_created(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(session_factory, tmp_path, status_value="submitted")
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/submit")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert "status=created" in response.json()["detail"]["message"]
    assert fake_airflow.calls == []


def test_submit_rejects_non_metadata_target(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(session_factory, tmp_path, target="dryrun_cnv")
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/submit")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert "target=metadata" in response.json()["detail"]["message"]
    assert fake_airflow.calls == []
