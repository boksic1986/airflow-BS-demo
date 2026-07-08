from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import Base, IntakeDiscovery


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
        self.trigger_calls: list[dict] = []

    def trigger_dag_run(self, dag_id: str, *, dag_run_id: str | None = None, conf: dict | None = None) -> dict:
        self.trigger_calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf})
        return {"dag_run_id": dag_run_id}


def write_nipt_clean_pair(batch_dir, sample_id: str) -> tuple[str, str]:
    batch_dir.mkdir(parents=True, exist_ok=True)
    r1 = batch_dir / f"{sample_id}.R1.clean.fastq.gz"
    r2 = batch_dir / f"{sample_id}.R2.clean.fastq.gz"
    r1.write_text("r1\n", encoding="utf-8")
    r2.write_text("r2\n", encoding="utf-8")
    return str(r1.resolve()), str(r2.resolve())


def test_intake_scan_and_submit_waits_for_stable_batch_then_submits_once(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    nipt_root = tmp_path / "nipt" / "fastq"
    batch_dir = nipt_root / "FQ2026" / "260414_TPNB500380AR_1065_AH32CCBGY2"
    write_nipt_clean_pair(batch_dir, "NIPT26040207.A06")
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            input_scan_roots=[],
            pgta_input_scan_roots=[],
            nipt_input_scan_roots=[str(nipt_root)],
            container_shared_root=str(shared_root),
            nipt_allow_heavy_run=False,
            nipt_docker_cores=40,
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    first = client.post("/api/intake/scan-and-submit", json={"pipelines": ["nipt_docker"], "bootstrap": False})
    second = client.post("/api/intake/scan-and-submit", json={"pipelines": ["nipt_docker"], "bootstrap": False})
    third = client.post("/api/intake/scan-and-submit", json={"pipelines": ["nipt_docker"], "bootstrap": False})

    assert first.status_code == 200
    assert first.json()["items"][0]["ready_state"] == "observed"
    assert first.json()["items"][0]["analysis_id"] is None
    assert second.status_code == 200
    submitted = second.json()["items"][0]
    assert submitted["ready_state"] == "ready"
    assert submitted["submit_state"] == "submitted"
    assert submitted["analysis_id"].startswith("NIPT_")
    assert third.json()["items"][0]["analysis_id"] == submitted["analysis_id"]
    assert len(fake_airflow.trigger_calls) == 1
    assert fake_airflow.trigger_calls[0]["dag_id"] == "bio_nipt_docker"
    assert fake_airflow.trigger_calls[0]["conf"]["params"]["input_mode"] == "nipt_docker_scan"

    with session_factory() as session:
        rows = session.scalars(select(IntakeDiscovery)).all()
    assert len(rows) == 1
    assert rows[0].pipeline_name == "nipt_docker"
    assert rows[0].batch_id == "FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2"
    assert rows[0].submit_state == "submitted"
