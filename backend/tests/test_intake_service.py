from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import intake_service, main
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


class FailFirstAirflowClient(FakeAirflowClient):
    def trigger_dag_run(self, dag_id: str, *, dag_run_id: str | None = None, conf: dict | None = None) -> dict:
        self.trigger_calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf})
        if len(self.trigger_calls) == 1:
            raise RuntimeError("temporary Airflow handoff failure")
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


def write_pgta_manifest_config(
    tmp_path,
    *,
    data_root,
    inbox_root,
    global_auto_submit: bool = False,
    pgta_auto_submit: bool = False,
) -> str:
    config_path = tmp_path / "pgta-intake.yaml"
    data_root_text = str(data_root.resolve()).replace("\\", "/")
    inbox_root_text = str(inbox_root.resolve()).replace("\\", "/")
    config_path.write_text(
        f"""
version: 1
defaults:
  ready_rule: stable_fingerprint
  stable_scans: 2
  auto_submit: {str(global_auto_submit).lower()}
pipelines:
  pgta:
    enabled: true
    roots:
      - id: pgta_rawdata
        container_path: {data_root_text}
    intake:
      mode: manifest_ready
      inbox_root: {inbox_root_text}
      data_root: {data_root_text}
      stable_scans: 2
    auto_submit:
      enabled: {str(pgta_auto_submit).lower()}
      target: predict
      runtime_profile_id: pgta-s9-predict-v1
""",
        encoding="utf-8",
    )
    return str(config_path)


def write_pgta_manifest_request(*, data_root, inbox_root, request_id: str, operator: str = "operator-a") -> None:
    batch = data_root / "2026-06-08"
    batch.mkdir(parents=True, exist_ok=True)
    (batch / "S1_combined_R1.fastq.gz").write_text("r1\n", encoding="utf-8")
    (batch / "S1_combined_R2.fastq.gz").write_text("r2\n", encoding="utf-8")
    (inbox_root / f"{request_id}.samples.tsv").write_text(
        "project_id\tsource_batch\tsample_id\toperator\n"
        f"PGTA-DEMO\t2026-06-08\tS1\t{operator}\n",
        encoding="utf-8",
    )
    (inbox_root / f"{request_id}.READY").write_text("", encoding="utf-8")


def add_discovery(
    session_factory,
    *,
    pipeline: str,
    batch_id: str,
    ready_state: str,
    submit_state: str,
    last_seen_at: datetime,
    analysis_id: str | None = None,
) -> None:
    with session_factory() as session:
        session.add(
            IntakeDiscovery(
                pipeline_name=pipeline,
                root_path=f"/data/{pipeline}",
                batch_id=batch_id,
                fingerprint=f"fingerprint-{batch_id}",
                file_count=2,
                total_bytes=1024,
                ready_state=ready_state,
                submit_state=submit_state,
                analysis_id=analysis_id,
                last_seen_at=last_seen_at,
            )
        )
        session.commit()


def test_intake_status_returns_stable_server_page_and_total(monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    base_time = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
    for index in range(12):
        add_discovery(
            session_factory,
            pipeline="pgta" if index % 2 == 0 else "nipt_docker",
            batch_id=f"batch-{index:02d}",
            ready_state="observed",
            submit_state="not_submitted",
            last_seen_at=base_time + timedelta(minutes=index),
        )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)

    response = TestClient(main.app).get("/api/intake/status?limit=5&offset=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 12
    assert payload["limit"] == 5
    assert payload["offset"] == 5
    assert [item["batch_id"] for item in payload["items"]] == [
        "batch-06",
        "batch-05",
        "batch-04",
        "batch-03",
        "batch-02",
    ]
    assert [item["pipeline"] for item in payload["items"]] == [
        "pgta",
        "nipt_docker",
        "pgta",
        "nipt_docker",
        "pgta",
    ]
    assert all(item["last_seen_at"].startswith("2026-07-11T12:") for item in payload["items"])


def test_intake_status_filters_composite_state_pipeline_and_keyword(monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    seen_at = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
    records = [
        ("pgta", "pgta-bootstrap", "observed", "bootstrap", None),
        ("pgta", "pgta-observed", "observed", "not_submitted", None),
        ("nipt_docker", "nipt-ready", "ready", "not_submitted", None),
        ("nipt_docker", "nipt-submitted", "ready", "submitted", "NIPT_MATCH_001"),
        ("nipt_docker", "nipt-wildcard-decoy", "ready", "submitted", "NIPTXMATCHX001"),
        ("pgta", "pgta-error", "observed", "error", None),
        ("nipt_docker", "nipt-disabled", "disabled", "not_submitted", None),
        ("nipt_docker", "mixed-error-disabled", "disabled", "error", None),
    ]
    for index, (pipeline, batch_id, ready_state, submit_state, analysis_id) in enumerate(records):
        add_discovery(
            session_factory,
            pipeline=pipeline,
            batch_id=batch_id,
            ready_state=ready_state,
            submit_state=submit_state,
            analysis_id=analysis_id,
            last_seen_at=seen_at + timedelta(minutes=index),
        )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    client = TestClient(main.app)

    bootstrap = client.get("/api/intake/status?state=bootstrap&limit=10&offset=0").json()
    observed = client.get("/api/intake/status?state=observed&limit=10&offset=0").json()
    submitted = client.get(
        "/api/intake/status?pipeline=nipt_docker&state=submitted&keyword=match_001&limit=10&offset=0"
    ).json()
    error = client.get("/api/intake/status?state=error&limit=10&offset=0").json()
    disabled = client.get("/api/intake/status?state=disabled&limit=10&offset=0").json()

    assert [item["batch_id"] for item in bootstrap["items"]] == ["pgta-bootstrap"]
    assert [item["batch_id"] for item in observed["items"]] == ["pgta-observed"]
    assert [item["batch_id"] for item in submitted["items"]] == ["nipt-submitted"]
    assert submitted["total"] == 1
    assert [item["batch_id"] for item in error["items"]] == ["mixed-error-disabled", "pgta-error"]
    assert [item["batch_id"] for item in disabled["items"]] == ["nipt-disabled"]


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


def test_intake_scan_and_submit_requires_configured_internal_service_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main, "get_internal_service_token", lambda: "service-secret")
    client = TestClient(main.app)

    assert client.post(
        "/api/intake/scan-and-submit",
        json={"pipelines": ["pgta"]},
    ).status_code == 401


def test_intake_retries_created_run_without_creating_a_duplicate(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    nipt_root = tmp_path / "nipt" / "fastq"
    batch_dir = nipt_root / "FQ2026" / "stable-batch"
    write_nipt_clean_pair(batch_dir, "NIPT-DEMO-01")
    config_path = write_intake_config(
        tmp_path,
        nipt_root=nipt_root,
        global_auto_submit=True,
        nipt_auto_submit=True,
    )
    fake_airflow = FailFirstAirflowClient()
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
    client = TestClient(main.app, raise_server_exceptions=False)

    assert client.post("/api/intake/scan-and-submit", json={"pipelines": ["nipt_docker"]}).status_code == 200
    failed_submit = client.post("/api/intake/scan-and-submit", json={"pipelines": ["nipt_docker"]})
    assert failed_submit.status_code == 500
    with session_factory() as session:
        discovery = session.scalar(select(IntakeDiscovery))
        created_runs = session.scalars(select(AnalysisRun)).all()
        assert discovery is not None
        first_analysis_id = discovery.analysis_id
        assert discovery.submit_state == "created"
        assert len(created_runs) == 1

    retried = client.post("/api/intake/scan-and-submit", json={"pipelines": ["nipt_docker"]})

    assert retried.status_code == 200, retried.text
    assert retried.json()["items"][0]["analysis_id"] == first_analysis_id
    assert retried.json()["items"][0]["submit_state"] == "submitted"
    with session_factory() as session:
        assert len(session.scalars(select(AnalysisRun)).all()) == 1
    assert len(fake_airflow.trigger_calls) == 2


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


def test_pgta_manifest_error_is_previewed_read_only_then_persisted_without_stopping_scan(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    data_root = tmp_path / "rawdata"
    inbox_root = data_root / "pgta_crontab"
    inbox_root.mkdir(parents=True)
    manifest = inbox_root / "bad-request.samples.tsv"
    manifest.write_text(
        "project_id\tsource_batch\tsample_id\toperator\n"
        "PGTA-DEMO\t2026-06-08\tDUPLICATE\toperator-a\n"
        "PGTA-DEMO\t2026-06-08\tDUPLICATE\toperator-a\n",
        encoding="utf-8",
    )
    (inbox_root / "bad-request.READY").write_text("", encoding="utf-8")
    config_path = write_pgta_manifest_config(tmp_path, data_root=data_root, inbox_root=inbox_root)
    fake_airflow = FakeAirflowClient()
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            intake_config_path=config_path,
            input_scan_roots=[],
            pgta_input_scan_roots=[],
            nipt_input_scan_roots=[],
            container_shared_root=str(tmp_path / "shared"),
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    client = TestClient(main.app)

    preview = client.post("/api/intake/scan-preview", json={"pipelines": ["pgta"]})
    assert preview.status_code == 200, preview.text
    assert preview.json()["summary"]["errors"] == 1
    assert preview.json()["items"][0]["ready_state"] == "error"
    with session_factory() as session:
        assert session.scalars(select(IntakeDiscovery)).all() == []

    recorded = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})
    assert recorded.status_code == 200, recorded.text
    assert recorded.json()["items"][0]["submit_state"] == "error"
    assert "duplicate sample_id" in recorded.json()["items"][0]["last_error"]
    with session_factory() as session:
        rows = session.scalars(select(IntakeDiscovery)).all()
        assert len(rows) == 1
        assert rows[0].ready_state == "error"
        assert rows[0].stable_observation_count == 0
        assert "duplicate sample_id" in rows[0].last_error
    assert fake_airflow.trigger_calls == []


def test_pgta_submitted_manifest_becomes_error_if_request_fingerprint_changes(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    data_root = tmp_path / "rawdata"
    inbox_root = data_root / "pgta_crontab"
    inbox_root.mkdir(parents=True)
    request_id = "immutable-request"
    write_pgta_manifest_request(data_root=data_root, inbox_root=inbox_root, request_id=request_id)
    config_path = write_pgta_manifest_config(
        tmp_path,
        data_root=data_root,
        inbox_root=inbox_root,
        global_auto_submit=True,
        pgta_auto_submit=True,
    )
    fake_airflow = FakeAirflowClient()
    settings = SimpleNamespace(
        intake_config_path=config_path,
        input_scan_roots=[str(data_root)],
        pgta_input_scan_roots=[str(data_root)],
        nipt_input_scan_roots=[],
        container_shared_root=str(tmp_path / "shared"),
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    monkeypatch.setattr(intake_service, "_auto_pipeline_config", lambda **_: None)
    client = TestClient(main.app)

    assert client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]}).status_code == 200
    submitted = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})
    assert submitted.status_code == 200
    analysis_id = submitted.json()["items"][0]["analysis_id"]
    write_pgta_manifest_request(
        data_root=data_root,
        inbox_root=inbox_root,
        request_id=request_id,
        operator="operator-b",
    )

    changed = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})

    assert changed.status_code == 200
    item = changed.json()["items"][0]
    assert item["ready_state"] == "error"
    assert item["submit_state"] == "error"
    assert item["analysis_id"] == analysis_id
    assert item["reason"] == "manifest_changed_after_observation"
    assert len(fake_airflow.trigger_calls) == 1


def test_pgta_submitted_discovery_is_not_downgraded_by_later_manifest_parse_error(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    data_root = tmp_path / "rawdata"
    inbox_root = data_root / "pgta_crontab"
    inbox_root.mkdir(parents=True)
    request_id = "submitted-request"
    write_pgta_manifest_request(data_root=data_root, inbox_root=inbox_root, request_id=request_id)
    manifest = inbox_root / f"{request_id}.samples.tsv"
    original_manifest = manifest.read_text(encoding="utf-8")
    config_path = write_pgta_manifest_config(
        tmp_path,
        data_root=data_root,
        inbox_root=inbox_root,
        global_auto_submit=True,
        pgta_auto_submit=True,
    )
    fake_airflow = FakeAirflowClient()
    settings = SimpleNamespace(
        intake_config_path=config_path,
        input_scan_roots=[str(data_root)],
        pgta_input_scan_roots=[str(data_root)],
        nipt_input_scan_roots=[],
        container_shared_root=str(tmp_path / "shared"),
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    monkeypatch.setattr(intake_service, "_auto_pipeline_config", lambda **_: None)
    client = TestClient(main.app)

    assert client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]}).status_code == 200
    submitted = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})
    analysis_id = submitted.json()["items"][0]["analysis_id"]
    manifest.write_text(original_manifest + "not-a-tab-separated-row\n", encoding="utf-8")

    warning = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})

    assert warning.status_code == 200
    item = warning.json()["items"][0]
    assert item["ready_state"] == "ready"
    assert item["submit_state"] == "submitted"
    assert item["analysis_id"] == analysis_id
    assert item["reason"] == "submitted_manifest_validation_warning"
    assert "tab-separated columns" in item["last_error"]
    assert len(fake_airflow.trigger_calls) == 1

    manifest.write_text(original_manifest, encoding="utf-8")
    recovered = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})

    assert recovered.status_code == 200
    recovered_item = recovered.json()["items"][0]
    assert recovered_item["submit_state"] == "submitted"
    assert recovered_item["analysis_id"] == analysis_id
    assert recovered_item["last_error"] is None
    assert len(fake_airflow.trigger_calls) == 1

    with session_factory() as session:
        discovery = session.scalar(select(IntakeDiscovery))
        assert discovery is not None
        discovery.fingerprint = "legacy-parser-error-fingerprint"
        discovery.ready_state = "error"
        discovery.submit_state = "error"
        discovery.last_error = "legacy parser rejected a blank line"
        discovery.stable_observation_count = 0
        session.commit()

    repaired_legacy_state = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})

    assert repaired_legacy_state.status_code == 200
    repaired_item = repaired_legacy_state.json()["items"][0]
    assert repaired_item["ready_state"] == "ready"
    assert repaired_item["submit_state"] == "submitted"
    assert repaired_item["analysis_id"] == analysis_id
    assert repaired_item["last_error"] is None
    assert repaired_item["reason"] == "submitted_manifest_recovered"
    assert len(fake_airflow.trigger_calls) == 1


def test_pgta_manifest_validation_error_can_recover_before_a_run_exists(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    data_root = tmp_path / "rawdata"
    inbox_root = data_root / "pgta_crontab"
    inbox_root.mkdir(parents=True)
    request_id = "correctable-request"
    batch = data_root / "2026-06-08"
    batch.mkdir(parents=True)
    (batch / "S1_combined_R1.fastq.gz").write_text("r1\n", encoding="utf-8")
    (batch / "S1_combined_R2.fastq.gz").write_text("r2\n", encoding="utf-8")
    manifest = inbox_root / f"{request_id}.samples.tsv"
    manifest.write_text(
        "project_id\tsource_batch\tsample_id\toperator\n"
        "PGTA-DEMO   2026-06-08   S1   jiucheng\n",
        encoding="utf-8",
    )
    (inbox_root / f"{request_id}.READY").write_text("", encoding="utf-8")
    config_path = write_pgta_manifest_config(
        tmp_path,
        data_root=data_root,
        inbox_root=inbox_root,
        global_auto_submit=True,
        pgta_auto_submit=True,
    )
    fake_airflow = FakeAirflowClient()
    settings = SimpleNamespace(
        intake_config_path=config_path,
        input_scan_roots=[str(data_root)],
        pgta_input_scan_roots=[str(data_root)],
        nipt_input_scan_roots=[],
        container_shared_root=str(tmp_path / "shared"),
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    monkeypatch.setattr(intake_service, "_auto_pipeline_config", lambda **_: None)
    client = TestClient(main.app)

    failed = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})
    assert failed.status_code == 200
    assert failed.json()["items"][0]["submit_state"] == "error"

    manifest.write_text(
        "project_id\tsource_batch\tsample_id\toperator\n"
        "PGTA-DEMO\t2026-06-08\tS1\tjiucheng\n",
        encoding="utf-8",
    )
    observed = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})
    submitted = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})

    assert observed.status_code == 200
    assert observed.json()["items"][0]["reason"] == "corrected_manifest_observed"
    assert observed.json()["items"][0]["stable_observation_count"] == 1
    assert submitted.status_code == 200
    item = submitted.json()["items"][0]
    assert item["submit_state"] == "submitted"
    assert item["analysis_id"].startswith("PGTA_")
    assert len(fake_airflow.trigger_calls) == 1


def test_pgta_manifest_recovers_created_run_after_crash_before_discovery_link(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    data_root = tmp_path / "rawdata"
    inbox_root = data_root / "pgta_crontab"
    inbox_root.mkdir(parents=True)
    request_id = "crash-recovery-request"
    write_pgta_manifest_request(data_root=data_root, inbox_root=inbox_root, request_id=request_id)
    config_path = write_pgta_manifest_config(
        tmp_path,
        data_root=data_root,
        inbox_root=inbox_root,
        global_auto_submit=True,
        pgta_auto_submit=True,
    )
    fake_airflow = FakeAirflowClient()
    settings = SimpleNamespace(
        intake_config_path=config_path,
        input_scan_roots=[str(data_root)],
        pgta_input_scan_roots=[str(data_root)],
        nipt_input_scan_roots=[],
        container_shared_root=str(tmp_path / "shared"),
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(main, "get_airflow_client", lambda: fake_airflow)
    monkeypatch.setattr(intake_service, "_auto_pipeline_config", lambda **_: None)
    client = TestClient(main.app)
    assert client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]}).status_code == 200

    real_create = intake_service.create_pgta_run

    def create_then_crash(**kwargs):
        real_create(**kwargs)
        raise RuntimeError("simulated crash after run commit")

    monkeypatch.setattr(intake_service, "create_pgta_run", create_then_crash)
    crashing_client = TestClient(main.app, raise_server_exceptions=False)
    assert crashing_client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]}).status_code == 500
    monkeypatch.setattr(intake_service, "create_pgta_run", real_create)

    recovered = client.post("/api/intake/scan-and-submit", json={"pipelines": ["pgta"]})

    assert recovered.status_code == 200
    assert recovered.json()["items"][0]["submit_state"] == "submitted"
    with session_factory() as session:
        runs = session.scalars(select(AnalysisRun)).all()
        assert len(runs) == 1
        assert runs[0].params_json["intake_request_id"] == request_id
    assert len(fake_airflow.trigger_calls) == 1
