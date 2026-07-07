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


def _patch_backend(monkeypatch, session_factory, shared_root) -> None:
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            input_scan_roots=[],
            container_shared_root=str(shared_root),
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)


def test_reanalyze_pgta_resume_reuses_failed_baseline_workdir_and_writes_action(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    analysis_id = _insert_pgta_run(session_factory, shared_root, status_value="failed", target="baseline_qc")
    _patch_backend(monkeypatch, session_factory, shared_root)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    response = client.post(
        f"/api/runs/{analysis_id}/actions/reanalyze",
        json={"mode": "resume", "reason": "controlled 64-core resume"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"] == analysis_id
    assert payload["mode"] == "resume"
    assert payload["status"] == "submitted"
    assert payload["new_dag_run_id"].startswith(f"manual__{analysis_id}__resume__")
    assert fake_airflow.calls[0]["dag_id"] == "bio_pgta"
    conf = fake_airflow.calls[0]["conf"]
    assert conf["analysis_id"] == analysis_id
    assert conf["pipeline"] == "pgta"
    assert conf["mode"] == "resume"
    assert conf["workdir"] == str(shared_root / "runs" / analysis_id)
    assert conf["sample_sheet_path"] == str(shared_root / "runs" / analysis_id / "config" / "samples.selected.tsv")
    assert conf["params"]["target"] == "baseline_qc"
    assert conf["params"]["selected_count"] == 2

    with session_factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        action = session.scalar(select(RunAction).where(RunAction.analysis_id == analysis_id))
        samples = session.scalars(select(Sample).where(Sample.analysis_id == analysis_id).order_by(Sample.sample_id)).all()
    assert run.status == "submitted"
    assert run.mode == "resume"
    assert run.dag_run_id == payload["new_dag_run_id"]
    assert run.error_summary is None
    assert run.ended_at is None
    assert action.action == "resume"
    assert action.result_status == "accepted"
    assert action.payload_json["reason"] == "controlled 64-core resume"
    assert [sample.status for sample in samples] == ["running", "running"]


def test_reanalyze_pgta_resume_rejects_active_or_unsupported_requests(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    running_id = _insert_pgta_run(session_factory, shared_root, status_value="running", target="baseline_qc")
    success_id = _insert_pgta_run(session_factory, shared_root, status_value="success", target="baseline_qc", suffix="SUCCESS")
    metadata_failed_id = _insert_pgta_run(session_factory, shared_root, status_value="failed", target="metadata", suffix="META")
    _patch_backend(monkeypatch, session_factory, shared_root)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    requests = [
        (running_id, {"mode": "resume"}, "already active"),
        (success_id, {"mode": "resume"}, "failed or terminated"),
        (metadata_failed_id, {"mode": "resume"}, "baseline_qc"),
        (metadata_failed_id, {"mode": "rerun_rule", "rule": "mapping", "sample_id": "G1"}, "Unsupported PGT-A reanalysis mode"),
        (metadata_failed_id, {"mode": "clone_new"}, "Unsupported PGT-A reanalysis mode"),
        (metadata_failed_id, {"mode": "forceall"}, "Unsupported PGT-A reanalysis mode"),
    ]
    for analysis_id, request_json, expected_message in requests:
        response = client.post(f"/api/runs/{analysis_id}/actions/reanalyze", json=request_json)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
        assert expected_message in response.json()["detail"]["message"]

    assert fake_airflow.calls == []


def _insert_pgta_run(
    session_factory,
    shared_root,
    *,
    status_value: str,
    target: str,
    suffix: str = "TEST01",
) -> str:
    analysis_id = f"PGTA_20260706_162150_{suffix}"
    workdir = shared_root / "runs" / analysis_id
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True)
    manifest = config_dir / "samples.selected.tsv"
    manifest.write_text(
        "sample_id\tR1\tR2\tsource_dir\n"
        "G10\t/data/project/CNV/PGT-A/rawdata/G10_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/G10_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/G10\n"
        "G11\t/data/project/CNV/PGT-A/rawdata/G11_R1.fastq.gz\t/data/project/CNV/PGT-A/rawdata/G11_R2.fastq.gz\t/data/project/CNV/PGT-A/rawdata/G11\n",
        encoding="utf-8",
    )
    with session_factory() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="pgta",
                dag_id="bio_pgta",
                dag_run_id=f"manual__{analysis_id}",
                mode="new",
                status=status_value,
                sample_sheet_path=str(manifest),
                workdir=str(workdir),
                params_json={
                    "project_name": "PGT-A baseline smoke",
                    "target": target,
                    "rawdata_root": "/data/project/CNV/PGT-A/rawdata/demo",
                    "input_mode": "server_path_scan",
                    "selected_count": 2,
                },
                error_summary="previous failure",
                email_to=None,
            )
        )
        for sample_id in ("G10", "G11"):
            session.add(
                Sample(
                    analysis_id=analysis_id,
                    sample_id=sample_id,
                    fq1=f"/data/project/CNV/PGT-A/rawdata/{sample_id}_R1.fastq.gz",
                    fq2=f"/data/project/CNV/PGT-A/rawdata/{sample_id}_R2.fastq.gz",
                    metadata_json={"input_mode": "server_path_scan"},
                    status=status_value,
                    qc_status="unknown",
                )
            )
        session.commit()
    return analysis_id
