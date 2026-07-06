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


def insert_pgta_run(
    session_factory,
    tmp_path,
    *,
    status_value: str = "created",
    target: str = "metadata",
    selected_count: int = 1,
) -> str:
    analysis_id = "PGTA_20260703_010000_TEST01"
    workdir = tmp_path / "shared" / "runs" / analysis_id
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True)
    manifest = config_dir / "samples.selected.tsv"
    lines = ["sample_id\tR1\tR2\tsource_dir"]
    for index in range(1, selected_count + 1):
        lines.append(f"G{index}\t/data/R{index}_1.fq.gz\t/data/R{index}_2.fq.gz\t/data")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
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
                    "selected_count": selected_count,
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


def test_submit_allows_dryrun_cnv_target(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(session_factory, tmp_path, target="dryrun_cnv")
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/submit")

    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert fake_airflow.calls[0]["conf"]["params"]["target"] == "dryrun_cnv"


def test_submit_allows_invalid_target_failure_smoke(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(session_factory, tmp_path, target="invalid_target")
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/submit")

    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert fake_airflow.calls[0]["conf"]["params"]["target"] == "invalid_target"


def test_submit_allows_baseline_qc_target_with_two_samples(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(session_factory, tmp_path, target="baseline_qc", selected_count=2)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/submit")

    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert fake_airflow.calls[0]["conf"]["params"]["target"] == "baseline_qc"
    assert fake_airflow.calls[0]["conf"]["params"]["selected_count"] == 2


def test_submit_rejects_baseline_qc_target_with_one_sample(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(session_factory, tmp_path, target="baseline_qc", selected_count=1)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/submit")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert "baseline_qc requires at least 2 selected samples" in response.json()["detail"]["message"]
    assert fake_airflow.calls == []


def test_submit_rejects_uncontrolled_target(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    analysis_id = insert_pgta_run(session_factory, tmp_path, target="real_cnv")
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(f"/api/runs/{analysis_id}/actions/submit")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert "Unsupported PGT-A target" in response.json()["detail"]["message"]
    assert fake_airflow.calls == []
