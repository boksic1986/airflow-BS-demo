from contextlib import contextmanager
import json
from pathlib import Path
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
    ObsTransferLease,
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
    fastq_source = tmp_path / "fastq-source"
    fastq_source.mkdir()
    for read in ("R1", "R2"):
        target = fastq_source / f"S1_{read}.fastq.gz"
        target.write_bytes(read.encode())
        (tmp_path / target.name).symlink_to(target)
    catalog = tmp_path / "wgs_releases.yaml"
    catalog.write_text(
        """\
 schema_version: "3"
 release:
   release_id: wgs-4.1.1-1778fca
   version: V4.1.1
   source_commit: 1778fcabd99b5253aa90cd410112dc2f78e0c51a
   bs10610_repo_path: /mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1
   node200_repo_path: /bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1
   rule_event_schema_version: "1"
""",
        encoding="utf-8",
    )
    sessions = make_sessionmaker()
    settings = SimpleNamespace(
        deployed_pipelines=("wgs",),
        container_shared_root=str(tmp_path / "shared"),
        host_results_root=str(tmp_path / "results"),
        wgs_config_roots=[str(tmp_path)],
        wgs_fastq_roots=[str(fastq_source)],
        wgs_validation_roots=[str(tmp_path)],
        session_cookie_secure=False,
        session_ttl_hours=8,
        auth_required=True,
        internal_service_token="internal-test-token",
        platform_environment="test",
        public_airflow_url="",
        wgs_release_catalog_path=str(catalog),
        wgs_runtime_request_root=str(tmp_path / "runtime" / "runner-requests"),
        wgs_runtime_bs_root=str(tmp_path / "runtime"),
        wgs_runtime_node200_root=str(tmp_path / "node200-runtime"),
        wgs_results_host_root=str(tmp_path / "results"),
        wgs_binding_root=str(tmp_path / "bindings"),
        wgs_intake_container_root=str(tmp_path),
        wgs_intake_host_root=str(tmp_path),
        wgs_intake_node200_root=str(tmp_path),
    )
    airflow = FakeAirflowClient()
    monkeypatch.setattr(main, "get_sessionmaker", lambda: sessions)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_airflow_client", lambda: airflow)
    with sessions() as session:
        session.add(UserAccount(username="viewer", password_hash=hash_password("viewer-pass"), role="viewer"))
        session.add(UserAccount(username="operator", password_hash=hash_password("operator-pass"), role="operator"))
        session.add(UserAccount(username="admin", password_hash=hash_password("admin-pass"), role="admin"))
        session.add(ObsTransferLease(slot_name="wgs-obs-transfer-01"))
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
        json={"pipeline": "wgs", "project_name": "family-1", "execution_mode": "cce", "batch_no": "BATCH-001", "fq_path": str(tmp_path)},
    )
    assert denied.status_code == 403

    client.post("/api/auth/logout", headers=viewer_headers)
    operator_headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=operator_headers,
        json={"pipeline": "wgs", "project_name": "family-1", "execution_mode": "cce", "batch_no": "BATCH-001", "fq_path": str(tmp_path)},
    )
    assert created.status_code == 201, created.text
    assert created.json()["pipeline"] == "wgs"
    assert created.json()["execution_mode"] == "cce"
    assert created.json()["params"]["pipeline_release_id"] == "wgs-4.1.1-1778fca"
    assert created.json()["params"]["wgs_version"] == "V4.1.1"
    assert created.json()["params"]["wgs_source_commit"] == "1778fcabd99b5253aa90cd410112dc2f78e0c51a"
    assert "pipeline_snapshot_id" not in created.json()["params"]
    assert created.json()["params"]["rule_event_schema_version"] == "1"
    with sessions() as session:
        assert session.scalar(select(AuditLog).where(AuditLog.action == "run.create")) is not None


def test_wgs_create_run_rejects_client_supplied_release_identity(tmp_path, monkeypatch):
    client, _, _ = make_client(tmp_path, monkeypatch)
    operator_headers = login(client, "operator", "operator-pass")

    response = client.post(
        "/api/runs",
        headers=operator_headers,
        json={
            "pipeline": "wgs",
            "project_name": "clinical-wgs",
            "batch_no": "BATCH-FORGED",
            "fq_path": str(tmp_path),
            "pipeline_release_id": "wgs-forged",
        },
    )

    assert response.status_code == 422


def test_controlled_batch_is_idempotent_and_source_change_needs_review(tmp_path, monkeypatch):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    body = {"pipeline": "wgs", "project_name": "family-1", "execution_mode": "cce", "batch_no": "BATCH-001", "fq_path": str(tmp_path)}

    first = client.post("/api/runs", headers=headers, json=body)
    second = client.post("/api/runs", headers=headers, json=body)
    assert second.status_code == 201
    assert second.json()["analysis_id"] == first.json()["analysis_id"]
    with sessions() as session:
        assert len(session.scalars(select(AnalysisRun)).all()) == 1

    (tmp_path / "fastq-source" / "S1_R1.fastq.gz").write_bytes(b"changed")
    changed = client.post(f"/api/runs/{first.json()['analysis_id']}/actions/revalidate", headers=headers)
    assert changed.status_code == 200
    assert changed.json()["status"] == "needs_review"
    issues = client.get(f"/api/runs/{first.json()['analysis_id']}/validation-issues", headers=headers)
    assert issues.json()["items"][0]["code"] == "WGS_INPUT_INVALID"


def test_current_release_api_is_read_only_and_execution_is_disabled(tmp_path, monkeypatch):
    client, _, airflow = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")

    release = client.get("/api/wgs/release", headers=headers)
    assert release.status_code == 200
    assert release.json() == {
        "release_id": "wgs-4.1.1-1778fca",
        "version": "V4.1.1",
        "source_commit": "1778fcabd99b5253aa90cd410112dc2f78e0c51a",
        "execution_enabled": False,
        "runtime_adapter_enabled": False,
    }

    rejected = client.post(
        "/api/runs",
        headers=headers,
        json={"pipeline": "nipt_docker", "project_name": "old", "execution_mode": "local", "batch_no": "OLD", "fq_path": str(tmp_path)},
    )
    assert rejected.status_code == 422

    created = client.post(
        "/api/runs", headers=headers,
        json={"pipeline": "wgs", "project_name": "wgs-cce", "execution_mode": "cce", "batch_no": "BATCH-C", "fq_path": str(tmp_path)},
    )
    analysis_id = created.json()["analysis_id"]
    submitted = client.post(f"/api/runs/{analysis_id}/actions/submit", headers=headers)
    assert submitted.status_code == 409, submitted.text
    for mode in ("sge", "local"):
        assert client.post("/api/runs", headers=headers, json={"pipeline": "wgs", "project_name": mode, "execution_mode": mode, "batch_no": mode, "fq_path": str(tmp_path)}).status_code == 422
    assert airflow.calls == []


def test_internal_runtime_uses_4_1_1_stages_and_releases_transfer_lease(
    tmp_path, monkeypatch
):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=headers,
        json={
            "pipeline": "wgs",
            "project_name": "clinical-wgs",
            "execution_mode": "cce",
            "batch_no": "BATCH-001",
            "fq_path": str(tmp_path),
        },
    ).json()
    analysis_id = created["analysis_id"]
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    internal = {"X-Airflow-Demo-Token": "internal-test-token"}
    body = {
        "attempt": 1,
        "adapter": "wgs-runtime-200",
        "command": f"wgs-runtime {analysis_id} 1 prepare",
    }

    prepared = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/prepare",
        headers=internal,
        json=body,
    )
    assert prepared.status_code == 200, prepared.text
    request_path = Path(prepared.json()["request_path"])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request["schema_version"] == "wgs-runtime.request.v3"
    assert request["project_name"] == "clinical-wgs"
    assert request["pipeline_release_id"] == "wgs-4.1.1-1778fca"
    assert request["wgs_source_commit"] == "1778fcabd99b5253aa90cd410112dc2f78e0c51a"
    assert "node200_pipeline_snapshot_path" not in request

    acquire = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/acquire_input_transfer_slot",
        headers=internal,
        json={**body, "command": "control"},
    )
    assert acquire.status_code == 200
    released = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/release_input_transfer_slot",
        headers=internal,
        json={**body, "command": "control"},
    )
    assert released.status_code == 200
    with sessions() as session:
        lease = session.scalar(select(ObsTransferLease))
        assert lease.analysis_id is None

    status_path = request_path.with_name("step3_monitor.status.json")
    status_path.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step3_monitor",
                "status": "running",
                "message": "running",
                "master": {"master_state": "RUNNING", "percent": 12.5},
            }
        ),
        encoding="utf-8",
    )
    status_response = client.get(
        f"/api/internal/wgs/runs/{analysis_id}/stage-status",
        params={"attempt": 1, "stage": "step3_monitor"},
        headers=internal,
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "running"
    assert status_response.json()["master"]["percent"] == 12.5


def test_prepare_reports_release_unavailable_without_silent_rebinding(
    tmp_path, monkeypatch
):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=headers,
        json={
            "pipeline": "wgs",
            "project_name": "clinical-wgs",
            "execution_mode": "cce",
            "batch_no": "BATCH-OLD",
            "fq_path": str(tmp_path),
        },
    ).json()
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(
                AnalysisRun.analysis_id == created["analysis_id"]
            )
        )
        run.params_json = {
            **run.params_json,
            "pipeline_release_id": "wgs-4.1.1-deadbee",
            "wgs_source_commit": "d" * 40,
        }
        session.commit()
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")

    response = client.post(
        f"/api/internal/wgs/runs/{created['analysis_id']}/stages/prepare",
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
        json={
            "attempt": 1,
            "adapter": "wgs-runtime-200",
            "command": f"wgs-runtime {created['analysis_id']} 1 prepare",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WGS_RELEASE_UNAVAILABLE"


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
                "pipeline_release_id": "wgs-4.1.1-1778fca",
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1778fcabd99b5253aa90cd410112dc2f78e0c51a",
                "rule_event_schema_version": "1",
            },
        )
        session.add(run)
        session.add(ObserverRunState(analysis_id=run.analysis_id, attempt=1, pipeline_release_id=run.params_json["pipeline_release_id"], run_label="wgs392-0123456789abcdef", relative_evidence_path="WGS_MONITOR_1/attempt-1", status="healthy"))
        session.add(RuleState(analysis_id=run.analysis_id, attempt=1, rule_instance_id="0123456789abcdef", rule_name="mapping", status="running"))
        session.add(KubernetesWorkload(analysis_id=run.analysis_id, attempt=1, event_id="pod:10", pod_hash="abc", job_name="wgs-master-0123456789abcdef0123", phase="Failed", reason="OOMKilled", exit_code=137, node_name="node-1", message="master failed", resources_json={"memory": "1Gi"}))
        session.add(KubernetesWorkload(analysis_id=run.analysis_id, attempt=1, event_id="pod:11", pod_hash="worker", job_name="mapping-7", phase="Failed", reason="OOMKilled", exit_code=137, node_name="node-2", message="worker hidden", resources_json={"memory": "2Gi"}))
        session.commit()

    detail = client.get("/api/runs/WGS_MONITOR_1", headers=headers)
    rules = client.get("/api/runs/WGS_MONITOR_1/rules", headers=headers)
    pods = client.get("/api/runs/WGS_MONITOR_1/pods", headers=headers)

    assert detail.status_code == 200
    assert detail.json()["pipeline_release_id"] == "wgs-4.1.1-1778fca"
    assert detail.json()["wgs_version"] == "V4.1.1"
    assert detail.json()["wgs_source_commit"].startswith("1778fca")
    assert detail.json()["resolved_runtime"] is None
    assert "pipeline_snapshot_id" not in detail.json()
    assert detail.json()["rule_event_schema_version"] == "1"
    assert detail.json()["observer"]["status"] == "healthy"
    assert rules.json()["items"][0]["rule"] == "mapping"
    assert len(pods.json()["items"]) == 1
    assert pods.json()["items"][0] == {
        "attempt": 1,
        "pod_hash": "abc",
        "job_name": "wgs-master-0123456789abcdef0123",
        "phase": "Failed",
        "reason": "OOMKilled",
        "exit_code": 137,
        "image_id": None,
        "node_name": "node-1",
        "message": "master failed",
        "resources": {"memory": "1Gi"},
        "observed_at": None,
        "updated_at": pods.json()["items"][0]["updated_at"],
    }
    assert client.get("/api/runs/UNKNOWN/pods", headers=headers).status_code == 404
