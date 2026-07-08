from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, IntakeDiscovery


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


def write_intake_config(tmp_path, *, nipt_root, global_auto_submit: bool, nipt_auto_submit: bool) -> str:
    config_path = tmp_path / "intake.yaml"
    nipt_root_text = str(nipt_root.resolve()).replace("\\", "/")
    config_path.write_text(
        f"""
version: 1
defaults:
  ready_rule: stable_fingerprint
  stable_scans: 2
  auto_submit: {str(global_auto_submit).lower()}
pipelines:
  nipt_docker:
    enabled: true
    roots:
      - id: nipt_fastq
        container_path: {nipt_root_text}
    file_flavor: clean_fastq
    r1_pattern: "*.R1.clean.fastq.gz"
    r2_pattern: "*.R2.clean.fastq.gz"
    ignore_patterns: ["002/*.adapter.fastq.gz"]
    auto_submit:
      enabled: {str(nipt_auto_submit).lower()}
      run_mode: mount_smoke
""",
        encoding="utf-8",
    )
    return str(config_path)


def test_intake_scan_and_submit_waits_for_stable_batch_then_submits_once(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    nipt_root = tmp_path / "nipt" / "fastq"
    batch_dir = nipt_root / "FQ2026" / "260414_TPNB500380AR_1065_AH32CCBGY2"
    write_nipt_clean_pair(batch_dir, "NIPT26040207.A06")
    config_path = write_intake_config(tmp_path, nipt_root=nipt_root, global_auto_submit=True, nipt_auto_submit=True)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            intake_config_path=config_path,
            input_scan_roots=[],
            pgta_input_scan_roots=[],
            nipt_input_scan_roots=[],
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
    assert second.status_code == 200, second.text
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


def test_intake_scan_and_submit_respects_auto_submit_disabled(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    nipt_root = tmp_path / "nipt" / "fastq"
    batch_dir = nipt_root / "FQ2026" / "260414_TPNB500380AR_1065_AH32CCBGY2"
    write_nipt_clean_pair(batch_dir, "NIPT26040207.A06")
    config_path = write_intake_config(tmp_path, nipt_root=nipt_root, global_auto_submit=False, nipt_auto_submit=False)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            intake_config_path=config_path,
            input_scan_roots=[],
            pgta_input_scan_roots=[],
            nipt_input_scan_roots=[],
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

    assert first.status_code == 200
    assert first.json()["items"][0]["ready_state"] == "observed"
    assert second.status_code == 200
    blocked = second.json()["items"][0]
    assert blocked["ready_state"] == "ready"
    assert blocked["submit_state"] == "not_submitted"
    assert blocked["analysis_id"] is None
    assert blocked["auto_submit_enabled"] is False
    assert blocked["reason"] == "auto_submit_disabled"
    assert fake_airflow.trigger_calls == []

    with session_factory() as session:
        discoveries = session.scalars(select(IntakeDiscovery)).all()
        runs = session.scalars(select(AnalysisRun)).all()
    assert len(discoveries) == 1
    assert discoveries[0].ready_state == "ready"
    assert discoveries[0].submit_state == "not_submitted"
    assert runs == []


def test_intake_scan_preview_is_read_only_and_reports_disabled_submit(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    nipt_root = tmp_path / "nipt" / "fastq"
    batch_dir = nipt_root / "FQ2026" / "260414_TPNB500380AR_1065_AH32CCBGY2"
    write_nipt_clean_pair(batch_dir, "NIPT26040207.A06")
    config_path = write_intake_config(tmp_path, nipt_root=nipt_root, global_auto_submit=False, nipt_auto_submit=False)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            intake_config_path=config_path,
            input_scan_roots=[],
            pgta_input_scan_roots=[],
            nipt_input_scan_roots=[],
            container_shared_root=str(shared_root),
            nipt_allow_heavy_run=False,
            nipt_docker_cores=40,
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)
    observed = client.post("/api/intake/scan-and-submit", json={"pipelines": ["nipt_docker"], "bootstrap": False})
    assert observed.status_code == 200

    with session_factory() as session:
        discovery_count = len(session.scalars(select(IntakeDiscovery)).all())
        run_count = len(session.scalars(select(AnalysisRun)).all())
    before_trigger_count = len(fake_airflow.trigger_calls)

    preview = client.post("/api/intake/scan-preview", json={"pipelines": ["nipt_docker"], "max_samples": 200})

    assert preview.status_code == 200
    payload = preview.json()
    assert payload["summary"]["stable_ready"] == 1
    assert payload["summary"]["would_create"] == 0
    assert payload["summary"]["would_submit"] == 0
    item = payload["items"][0]
    assert item["batch_id"] == "FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2"
    assert item["existing_ready_state"] == "observed"
    assert item["would_transition_to"] == "ready"
    assert item["would_create_run"] is False
    assert item["would_submit"] is False
    assert item["auto_submit_enabled"] is False
    assert item["reason"] == "auto_submit_disabled"

    with session_factory() as session:
        assert len(session.scalars(select(IntakeDiscovery)).all()) == discovery_count
        assert len(session.scalars(select(AnalysisRun)).all()) == run_count
    assert len(fake_airflow.trigger_calls) == before_trigger_count
