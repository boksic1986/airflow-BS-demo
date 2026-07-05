from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, RunAction, Sample


def make_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


class FakeAirflowClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trigger_dag_run(self, dag_id: str, *, dag_run_id: str | None = None, conf: dict | None = None) -> dict:
        self.calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf})
        return {"dag_run_id": dag_run_id or "manual__from_airflow"}


def _patch_backend(monkeypatch, session_factory, shared_root):
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            input_scan_roots=[],
            container_shared_root=str(shared_root),
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)


def test_create_wes_mock_run_records_fixed_samples_and_manifest(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    _patch_backend(monkeypatch, session_factory, shared_root)
    client = TestClient(main.app)

    response = client.post(
        "/api/runs",
        json={
            "pipeline": "wes_qsub",
            "project_name": "WES mock smoke",
            "target": "final_summary",
            "email_to": "demo@example.com",
            "note": "mock WES only",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["analysis_id"].startswith("WES_")
    assert payload["pipeline"] == "wes_qsub"
    assert payload["dag_id"] == "bio_wes_qsub"
    assert payload["dag_run_id"] is None
    assert payload["status"] == "created"
    assert payload["sample_count"] == 2

    manifest = shared_root / "runs" / payload["analysis_id"] / "config" / "samples.selected.tsv"
    request_json = shared_root / "runs" / payload["analysis_id"] / "config" / "request.json"
    assert manifest.read_text(encoding="utf-8").splitlines() == [
        "sample_id\tinput",
        "S001\tpipelines/wes/mock_data/S001.input.txt",
        "S002\tpipelines/wes/mock_data/S002.input.txt",
    ]
    assert request_json.exists()

    detail = client.get(f"/api/runs/{payload['analysis_id']}")
    assert detail.status_code == 200
    assert detail.json()["params"]["input_mode"] == "mock_wes"
    assert detail.json()["params"]["target"] == "final_summary"

    samples = client.get(f"/api/runs/{payload['analysis_id']}/samples")
    assert samples.status_code == 200
    assert [item["sample_id"] for item in samples.json()["items"]] == ["S001", "S002"]


def test_submit_created_wes_run_triggers_bio_wes_qsub(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    _patch_backend(monkeypatch, session_factory, shared_root)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)
    created = client.post(
        "/api/runs",
        json={"pipeline": "wes_qsub", "project_name": "WES mock smoke", "target": "final_summary"},
    ).json()

    response = client.post(f"/api/runs/{created['analysis_id']}/actions/submit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "submitted"
    assert payload["dag_id"] == "bio_wes_qsub"
    assert payload["dag_run_id"] == f"manual__{created['analysis_id']}"
    assert fake_airflow.calls == [
        {
            "dag_id": "bio_wes_qsub",
            "dag_run_id": f"manual__{created['analysis_id']}",
            "conf": {
                "analysis_id": created["analysis_id"],
                "pipeline": "wes_qsub",
                "mode": "new",
                "sample_sheet_path": str(shared_root / "runs" / created["analysis_id"] / "config" / "samples.selected.tsv"),
                "workdir": str(shared_root / "runs" / created["analysis_id"]),
                "email_to": None,
                "params": {
                    "project_name": "WES mock smoke",
                    "target": "final_summary",
                    "input_mode": "mock_wes",
                    "selected_count": 2,
                    "max_jobs": 2,
                    "note": None,
                },
                "backend_event_url": "http://backend:8000/api/events/snakemake",
            },
        }
    ]


def test_reanalyze_resume_reuses_wes_workdir_and_writes_action(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    analysis_id = _insert_wes_run(session_factory, shared_root, status_value="success")
    _patch_backend(monkeypatch, session_factory, shared_root)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(
        f"/api/runs/{analysis_id}/actions/reanalyze",
        json={"mode": "resume", "reason": "rerun after checking logs"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"] == analysis_id
    assert payload["mode"] == "resume"
    assert payload["status"] == "submitted"
    assert payload["new_dag_run_id"].startswith(f"manual__{analysis_id}__resume__")
    assert fake_airflow.calls[0]["dag_id"] == "bio_wes_qsub"
    assert fake_airflow.calls[0]["conf"]["mode"] == "resume"
    assert fake_airflow.calls[0]["conf"]["workdir"] == str(shared_root / "runs" / analysis_id)
    with session_factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        action = session.scalar(select(RunAction).where(RunAction.analysis_id == analysis_id))
    assert run.status == "submitted"
    assert run.mode == "resume"
    assert action.action == "resume"


def test_reanalyze_rerun_rule_passes_allowed_rule_and_sample(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    analysis_id = _insert_wes_run(session_factory, shared_root, status_value="failed")
    _patch_backend(monkeypatch, session_factory, shared_root)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(
        f"/api/runs/{analysis_id}/actions/reanalyze",
        json={"mode": "rerun_rule", "rule": "fastp", "sample_id": "S001", "reason": "selected rule smoke"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "rerun_rule"
    conf = fake_airflow.calls[0]["conf"]
    assert conf["mode"] == "rerun_rule"
    assert conf["params"]["rule"] == "fastp"
    assert conf["params"]["sample_id"] == "S001"


def test_reanalyze_rejects_unsafe_or_unsupported_modes(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    analysis_id = _insert_wes_run(session_factory, shared_root, status_value="success")
    _patch_backend(monkeypatch, session_factory, shared_root)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    for request_json in (
        {"mode": "forceall"},
        {"mode": "clone_new"},
        {"mode": "rerun_rule", "rule": "haplotypecaller", "sample_id": "S001"},
        {"mode": "rerun_rule", "rule": "fastp", "sample_id": "S999"},
    ):
        response = client.post(f"/api/runs/{analysis_id}/actions/reanalyze", json=request_json)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "VALIDATION_ERROR"

    assert fake_airflow.calls == []


def _insert_wes_run(session_factory, shared_root, *, status_value: str) -> str:
    analysis_id = "WES_20260705_010000_TEST01"
    workdir = shared_root / "runs" / analysis_id
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True)
    manifest = config_dir / "samples.selected.tsv"
    manifest.write_text(
        "sample_id\tinput\nS001\tpipelines/wes/mock_data/S001.input.txt\nS002\tpipelines/wes/mock_data/S002.input.txt\n",
        encoding="utf-8",
    )
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wes_qsub",
                dag_id="bio_wes_qsub",
                dag_run_id=f"manual__{analysis_id}",
                mode="new",
                status=status_value,
                sample_sheet_path=str(manifest),
                workdir=str(workdir),
                params_json={
                    "project_name": "WES mock smoke",
                    "target": "final_summary",
                    "input_mode": "mock_wes",
                    "selected_count": 2,
                    "max_jobs": 2,
                    "note": None,
                },
                email_to=None,
            )
        )
        for sample_id in ("S001", "S002"):
            session.add(
                Sample(
                    analysis_id=analysis_id,
                    sample_id=sample_id,
                    fq1=f"pipelines/wes/mock_data/{sample_id}.input.txt",
                    fq2=None,
                    metadata_json={"input_mode": "mock_wes"},
                    status="pending",
                    qc_status="unknown",
                )
            )
        session.commit()
    return analysis_id
