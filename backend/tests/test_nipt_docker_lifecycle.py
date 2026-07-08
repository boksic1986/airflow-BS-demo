from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.models import AnalysisRun, Base, QcMetric, RunAction, Sample


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
        self.state = "success"

    def trigger_dag_run(self, dag_id: str, *, dag_run_id: str | None = None, conf: dict | None = None) -> dict:
        self.trigger_calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf})
        return {"dag_run_id": dag_run_id or "manual__from_airflow"}

    def get_dag_run(self, dag_id: str, dag_run_id: str) -> dict:
        return {
            "dag_id": dag_id,
            "dag_run_id": dag_run_id,
            "state": self.state,
            "start_date": "2026-07-08T10:00:00+00:00",
            "end_date": "2026-07-08T10:01:00+00:00",
        }


def patch_backend(monkeypatch, session_factory, shared_root, airflow_client: FakeAirflowClient | None = None):
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(
            input_scan_roots=[],
            pgta_input_scan_roots=[],
            nipt_input_scan_roots=[],
            container_shared_root=str(shared_root),
            nipt_allow_heavy_run=False,
            nipt_docker_cores=40,
        ),
    )
    monkeypatch.setattr(main, "get_sessionmaker", lambda: session_factory)
    if airflow_client is not None:
        monkeypatch.setattr(main, "get_airflow_client", lambda: airflow_client)


def write_nipt_clean_pair(batch_dir, sample_id: str) -> tuple[str, str]:
    batch_dir.mkdir(parents=True, exist_ok=True)
    r1 = batch_dir / f"{sample_id}.R1.clean.fastq.gz"
    r2 = batch_dir / f"{sample_id}.R2.clean.fastq.gz"
    r1.write_text("r1\n", encoding="utf-8")
    r2.write_text("r2\n", encoding="utf-8")
    return str(r1.resolve()), str(r2.resolve())


def test_create_nipt_docker_scan_run_records_fastqs_and_manifest(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    nipt_root = tmp_path / "nipt" / "fastq"
    batch_dir = nipt_root / "FQ2026" / "260414_TPNB500380AR_1065_AH32CCBGY2"
    r1, r2 = write_nipt_clean_pair(batch_dir, "NIPT26040207.A06")
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
    client = TestClient(main.app)

    response = client.post(
        "/api/runs",
        json={
            "pipeline": "nipt_docker",
            "project_name": "NIPT scanned batch smoke",
            "rawdata_root": str(batch_dir),
            "selected_samples": [
                {
                    "sample_id": "NIPT26040207.A06",
                    "r1": r1,
                    "r2": r2,
                    "source_dir": str(batch_dir.resolve()),
                    "discovery_method": "nipt_docker_clean_scan",
                }
            ],
            "run_mode": "mount_smoke",
            "cores": 40,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["analysis_id"].startswith("NIPT_")
    assert payload["sample_count"] == 1

    manifest = shared_root / "runs" / payload["analysis_id"] / "config" / "samples.selected.tsv"
    assert manifest.read_text(encoding="utf-8").splitlines() == [
        "sample_id\tlibrary\tindex\tR1\tR2\tsource_dir\tcomment",
        f"NIPT26040207.A06\tNIPT26040207\tA06\t{r1}\t{r2}\t{batch_dir.resolve()}\tNIPT",
    ]

    detail = client.get(f"/api/runs/{payload['analysis_id']}")
    assert detail.status_code == 200
    params = detail.json()["params"]
    assert params["input_mode"] == "nipt_docker_scan"
    assert params["chip_name"] == "260414_TPNB500380AR_1065_AH32CCBGY2"
    assert params["source_batch_dir"] == str(batch_dir.resolve())
    assert params["input_file_flavor"] == "clean"
    assert "source_fingerprint" in params
    assert "template_id" not in params

    samples = client.get(f"/api/runs/{payload['analysis_id']}/samples").json()["items"]
    assert samples[0]["sample_id"] == "NIPT26040207.A06"
    assert samples[0]["fq1"] == r1
    assert samples[0]["fq2"] == r2


def test_create_nipt_docker_template_run_records_samples_and_manifest(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    patch_backend(monkeypatch, session_factory, shared_root)
    client = TestClient(main.app)

    response = client.post(
        "/api/runs",
        json={
            "pipeline": "nipt_docker",
            "project_name": "NIPT docker run1 smoke",
            "template_id": "run1",
            "run_mode": "mount_smoke",
            "cores": 40,
            "note": "template smoke only",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["analysis_id"].startswith("NIPT_")
    assert payload["pipeline"] == "nipt_docker"
    assert payload["dag_id"] == "bio_nipt_docker"
    assert payload["dag_run_id"] is None
    assert payload["status"] == "created"
    assert payload["sample_count"] == 96

    manifest = shared_root / "runs" / payload["analysis_id"] / "config" / "samples.selected.tsv"
    request_json = shared_root / "runs" / payload["analysis_id"] / "config" / "request.json"
    assert manifest.read_text(encoding="utf-8").splitlines()[0] == "sample_id\tlibrary\tindex\tcomment"
    assert request_json.read_text(encoding="utf-8").count('"pipeline": "nipt_docker"') == 1

    detail = client.get(f"/api/runs/{payload['analysis_id']}")
    assert detail.status_code == 200
    assert detail.json()["params"]["template_id"] == "run1"
    assert detail.json()["params"]["run_mode"] == "mount_smoke"
    assert detail.json()["params"]["chip_name"] == "260414_TPNB500380AR_1065_AH32CCBGY2"

    samples = client.get(f"/api/runs/{payload['analysis_id']}/samples")
    assert samples.status_code == 200
    sample_items = samples.json()["items"]
    assert sample_items[0]["sample_id"] == "NC-20260414.A01"
    assert sample_items[0]["metadata"]["template_id"] == "run1"


def test_create_nipt_docker_rejects_full_run_when_disabled(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    patch_backend(monkeypatch, session_factory, tmp_path / "shared")
    client = TestClient(main.app)

    response = client.post(
        "/api/runs",
        json={
            "pipeline": "nipt_docker",
            "project_name": "NIPT full run should be guarded",
            "template_id": "run1",
            "run_mode": "full_run",
            "cores": 40,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"
    assert "NIPT full_run is disabled" in response.json()["detail"]["message"]


def test_submit_nipt_docker_run_triggers_bio_nipt_docker(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    fake_airflow = FakeAirflowClient()
    patch_backend(monkeypatch, session_factory, shared_root, fake_airflow)
    client = TestClient(main.app)
    created = client.post(
        "/api/runs",
        json={
            "pipeline": "nipt_docker",
            "project_name": "NIPT docker run2 smoke",
            "template_id": "run2",
            "run_mode": "mount_smoke",
            "cores": 40,
        },
    ).json()

    response = client.post(f"/api/runs/{created['analysis_id']}/actions/submit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "submitted"
    assert payload["dag_id"] == "bio_nipt_docker"
    assert payload["dag_run_id"] == f"manual__{created['analysis_id']}"
    assert fake_airflow.trigger_calls == [
        {
            "dag_id": "bio_nipt_docker",
            "dag_run_id": f"manual__{created['analysis_id']}",
            "conf": {
                "analysis_id": created["analysis_id"],
                "pipeline": "nipt_docker",
                "mode": "new",
                    "sample_sheet_path": str(shared_root / "runs" / created["analysis_id"] / "config" / "samples.selected.tsv"),
                    "workdir": str(shared_root / "runs" / created["analysis_id"]),
                    "email_to": None,
                    "backend_event_url": "http://backend:8000/api/events/snakemake",
                    "params": {
                    "project_name": "NIPT docker run2 smoke",
                    "template_id": "run2",
                    "run_mode": "mount_smoke",
                    "input_mode": "nipt_docker_template",
                    "selected_count": 72,
                    "chip_name": "260422_TPNB500380AR_1070_AH33KYBGY2",
                    "cores": 40,
                    "note": None,
                },
            },
        }
    ]
    with session_factory() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == created["analysis_id"]))
        action = session.scalar(select(RunAction).where(RunAction.analysis_id == created["analysis_id"]))
        samples = session.scalars(select(Sample).where(Sample.analysis_id == created["analysis_id"])).all()
    assert run.status == "submitted"
    assert action.action == "submit"
    assert {sample.status for sample in samples} == {"running"}


def test_sync_success_imports_nipt_qc_metrics_and_artifacts(tmp_path, monkeypatch) -> None:
    session_factory = make_test_sessionmaker()
    shared_root = tmp_path / "shared"
    fake_airflow = FakeAirflowClient()
    patch_backend(monkeypatch, session_factory, shared_root, fake_airflow)
    client = TestClient(main.app)
    created = client.post(
        "/api/runs",
        json={
            "pipeline": "nipt_docker",
            "project_name": "NIPT docker run1 smoke",
            "template_id": "run1",
            "run_mode": "mount_smoke",
            "cores": 40,
        },
    ).json()
    analysis_id = created["analysis_id"]
    client.post(f"/api/runs/{analysis_id}/actions/submit")
    workdir = shared_root / "runs" / analysis_id
    (workdir / "logs" / "snakemake.stdout.log").write_text("nipt smoke stdout\n", encoding="utf-8")
    (workdir / "logs" / "snakemake.stderr.log").write_text("", encoding="utf-8")
    reports_dir = workdir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "qc_summary.tsv").write_text(
        "\n".join(
            [
                "sample_id\tmetric_name\tmetric_value\tmetric_numeric\tthreshold\tstatus",
                "NC-20260414.A01\tQ30\t93.2\t93.2\t>=85\tpass",
                "NC-20260414.A01\tunique_mapping_rate\t87.5\t87.5\t>=70\tpass",
                "NC-20260414.A01\tfetal_fraction\t0.083\t0.083\t>=0.04\tpass",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (workdir / "config" / "nipt_docker_compose.yml").write_text("services: {}\n", encoding="utf-8")
    (workdir / "config" / "nipt_run_config.yaml").write_text("chip_name: demo\n", encoding="utf-8")

    response = client.post(f"/api/runs/{analysis_id}/actions/sync-airflow")
    artifacts = client.get(f"/api/runs/{analysis_id}/artifacts")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    with session_factory() as session:
        metrics = session.scalars(select(QcMetric).where(QcMetric.analysis_id == analysis_id)).all()
        sample = session.scalar(select(Sample).where(Sample.analysis_id == analysis_id, Sample.sample_id == "NC-20260414.A01"))
    assert {(metric.sample_id, metric.metric_name, metric.status) for metric in metrics} >= {
        ("NC-20260414.A01", "Q30", "pass"),
        ("NC-20260414.A01", "unique_mapping_rate", "pass"),
        ("NC-20260414.A01", "fetal_fraction", "pass"),
    }
    assert sample.qc_status == "pass"
    artifact_keys = {item["key"] for item in artifacts.json()["items"]}
    assert {"nipt_qc_summary", "nipt_docker_compose", "nipt_run_config"} <= artifact_keys
    assert "wes_qc_summary" not in artifact_keys
