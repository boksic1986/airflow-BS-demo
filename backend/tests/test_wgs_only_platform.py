from contextlib import contextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.auth_service import hash_password
from app.models import (
    AnalysisRun,
    AuditLog,
    Base,
    KubernetesWorkload,
    MasterSlot,
    ObserverRunState,
    RuleState,
    UserAccount,
)


def make_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


class FakeAirflowClient:
    def __init__(self) -> None:
        self.calls = []

    def trigger_dag_run(self, dag_id, *, dag_run_id=None, conf=None):
        self.calls.append((dag_id, dag_run_id, conf))
        return {"dag_run_id": dag_run_id}


def make_client(tmp_path, monkeypatch):
    (tmp_path / "READY").write_text("", encoding="utf-8")
    (tmp_path / "sampleinfo.tsv").write_text("sample_id\tfamily_id\nS1\tF1\n", encoding="utf-8")
    (tmp_path / "FASTQ.MD5SUMS").write_text("d41d8cd98f00b204e9800998ecf8427e  S1.R1.fastq.gz\n", encoding="utf-8")
    catalog = tmp_path / "wgs_releases.yaml"
    catalog.write_text(
        """\
schema_version: "1"
default_snapshot_id: wgs-v4.0.1-dev-136da1a-b10cd8af
snapshots:
  - snapshot_id: wgs-v4.0.1-dev-136da1a-b10cd8af
    pipeline: wgs
    version: V4.0.1
    server_path: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs
    source_commit: 136da1ad9e45ac1abcbeb3efa40bb2e2269b6ab9
    snapshot_manifest_sha256: b10cd8af1db19c313e15167c295d007d9eca246d03b2721592c4c0532a05696c
    rule_event_schema_version: "1"
    status: development
    execution_enabled: false
""",
        encoding="utf-8",
    )
    sessions = make_sessionmaker()
    settings = SimpleNamespace(
        deployed_pipelines=("wgs",),
        container_shared_root=str(tmp_path / "shared"),
        host_results_root=str(tmp_path / "results"),
        wgs_config_roots=[str(tmp_path)],
        wgs_validation_roots=[str(tmp_path)],
        session_cookie_secure=False,
        session_ttl_hours=8,
        auth_required=True,
        internal_service_token="internal-test-token",
        platform_environment="test",
        public_airflow_url="",
        wgs_release_catalog_path=str(catalog),
    )
    airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: sessions)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_airflow_client", lambda: airflow)
    with sessions() as session:
        session.add(UserAccount(username="viewer", password_hash=hash_password("viewer-pass"), role="viewer"))
        session.add(UserAccount(username="operator", password_hash=hash_password("operator-pass"), role="operator"))
        session.add(UserAccount(username="admin", password_hash=hash_password("admin-pass"), role="admin"))
        for number in range(1, 5):
            session.add(MasterSlot(slot_name=f"wgs-master-pool-{number:02d}"))
        session.commit()
    return TestClient(main.app), sessions, airflow


def login(client, username, password):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    csrf = response.json()["csrf_token"]
    return {"X-CSRF-Token": csrf}


def test_all_non_health_endpoints_require_login(tmp_path, monkeypatch):
    client, _, _ = make_client(tmp_path, monkeypatch)

    assert client.get("/api/health").status_code == 200
    assert client.get("/api/runs").status_code == 401


def test_viewer_is_read_only_and_operator_can_create_wgs(tmp_path, monkeypatch):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    viewer_headers = login(client, "viewer", "viewer-pass")

    denied = client.post(
        "/api/runs",
        headers=viewer_headers,
        json={"pipeline": "wgs", "project_name": "family-1", "execution_mode": "cce", "source_path": str(tmp_path)},
    )
    assert denied.status_code == 403

    client.post("/api/auth/logout", headers=viewer_headers)
    operator_headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=operator_headers,
        json={"pipeline": "wgs", "project_name": "family-1", "execution_mode": "cce", "source_path": str(tmp_path)},
    )
    assert created.status_code == 201, created.text
    assert created.json()["pipeline"] == "wgs"
    assert created.json()["execution_mode"] == "cce"
    assert created.json()["params"]["pipeline_snapshot_id"] == "wgs-v4.0.1-dev-136da1a-b10cd8af"
    assert created.json()["params"]["rule_event_schema_version"] == "1"
    with sessions() as session:
        assert session.scalar(select(AuditLog).where(AuditLog.action == "run.create")) is not None


def test_controlled_batch_is_idempotent_and_ready_change_is_blocked(tmp_path, monkeypatch):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    body = {"pipeline": "wgs", "project_name": "family-1", "execution_mode": "cce", "source_path": str(tmp_path)}

    first = client.post("/api/runs", headers=headers, json=body)
    second = client.post("/api/runs", headers=headers, json=body)
    assert second.status_code == 201
    assert second.json()["analysis_id"] == first.json()["analysis_id"]
    with sessions() as session:
        assert len(session.scalars(select(AnalysisRun)).all()) == 1

    (tmp_path / "sampleinfo.tsv").write_text("sample_id\tfamily_id\nS1\tF1\nS2\tF1\n", encoding="utf-8")
    changed = client.post("/api/runs", headers=headers, json=body)
    assert changed.status_code == 400
    assert "changed after READY" in changed.text


def test_only_wgs_and_three_execution_modes_are_accepted_but_execution_is_disabled(tmp_path, monkeypatch):
    client, _, airflow = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")

    rejected = client.post(
        "/api/runs",
        headers=headers,
        json={"pipeline": "nipt_docker", "project_name": "old", "execution_mode": "local", "source_path": str(tmp_path)},
    )
    assert rejected.status_code == 422

    for mode in ("cce", "sge", "local"):
        created = client.post(
            "/api/runs",
            headers=headers,
            json={"pipeline": "wgs", "project_name": f"wgs-{mode}", "execution_mode": mode, "source_path": str(tmp_path)},
        )
        analysis_id = created.json()["analysis_id"]
        submitted = client.post(f"/api/runs/{analysis_id}/actions/submit", headers=headers)
        assert submitted.status_code == 409, submitted.text
    assert airflow.calls == []


def test_admin_manages_users_but_operator_cannot(tmp_path, monkeypatch):
    client, _, _ = make_client(tmp_path, monkeypatch)
    operator_headers = login(client, "operator", "operator-pass")
    assert client.get("/api/users", headers=operator_headers).status_code == 403
    client.post("/api/auth/logout", headers=operator_headers)

    admin_headers = login(client, "admin", "admin-pass")
    created = client.post(
        "/api/users",
        headers=admin_headers,
        json={"username": "new-viewer", "password": "long-enough-password", "role": "viewer"},
    )
    assert created.status_code == 201, created.text
    assert "new-viewer" in {item["username"] for item in client.get("/api/users", headers=admin_headers).json()["items"]}


def test_wgs_detail_rules_and_pods_are_database_only_authenticated_reads(tmp_path, monkeypatch):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "viewer", "viewer-pass")
    with sessions() as session:
        run = AnalysisRun(
            analysis_id="WGS_MONITOR_1",
            pipeline_name="wgs",
            dag_id="bio_wgs_cce",
            execution_mode="cce",
            workdir=str(tmp_path),
            status="running",
            params_json={
                "pipeline_snapshot_id": "wgs-v4.0.1-dev-136da1a-b10cd8af",
                "rule_event_schema_version": "1",
            },
        )
        session.add(run)
        session.add(ObserverRunState(analysis_id=run.analysis_id, attempt=1, pipeline_snapshot_id=run.params_json["pipeline_snapshot_id"], run_label="wgs392-0123456789abcdef", relative_evidence_path="WGS_MONITOR_1/attempt-1", status="healthy"))
        session.add(RuleState(analysis_id=run.analysis_id, attempt=1, rule_instance_id="0123456789abcdef", rule_name="mapping", status="running"))
        session.add(KubernetesWorkload(analysis_id=run.analysis_id, attempt=1, event_id="pod:10", pod_hash="abc", job_name="mapping-7", phase="Failed", reason="OOMKilled", exit_code=137, node_name="node-1", message="worker failed", resources_json={"memory": "1Gi"}))
        session.commit()

    detail = client.get("/api/runs/WGS_MONITOR_1", headers=headers)
    rules = client.get("/api/runs/WGS_MONITOR_1/rules", headers=headers)
    pods = client.get("/api/runs/WGS_MONITOR_1/pods", headers=headers)

    assert detail.status_code == 200
    assert detail.json()["pipeline_snapshot_id"] == "wgs-v4.0.1-dev-136da1a-b10cd8af"
    assert detail.json()["rule_event_schema_version"] == "1"
    assert detail.json()["observer"]["status"] == "healthy"
    assert rules.json()["items"][0]["rule"] == "mapping"
    assert pods.json()["items"][0] == {
        "attempt": 1,
        "pod_hash": "abc",
        "job_name": "mapping-7",
        "phase": "Failed",
        "reason": "OOMKilled",
        "exit_code": 137,
        "image_id": None,
        "node_name": "node-1",
        "message": "worker failed",
        "resources": {"memory": "1Gi"},
        "observed_at": None,
        "updated_at": pods.json()["items"][0]["updated_at"],
    }
    assert client.get("/api/runs/UNKNOWN/pods", headers=headers).status_code == 404
