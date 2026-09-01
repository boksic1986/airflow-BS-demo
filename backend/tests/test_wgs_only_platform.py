from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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
    WgsIntakeBatch,
    WgsIntakeScannerState,
    WgsMaintenanceAction,
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
   release_id: wgs-4.1.1-1656b5d
   version: V4.1.1
   source_commit: 1656b5d7a6e2f24242c38149f6d1c92ac266cd37
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
        wgs_transfer_spool_root=str(tmp_path / "runtime" / "transfer-progress"),
        wgs_runtime_bs_root=str(tmp_path / "runtime"),
        wgs_runtime_node200_root=str(tmp_path / "node200-runtime"),
        wgs_results_host_root=str(tmp_path / "results"),
        wgs_binding_root=str(tmp_path / "bindings"),
        wgs_intake_container_root=str(tmp_path),
        wgs_intake_host_root=str(tmp_path),
        wgs_intake_node200_root=str(tmp_path),
        wgs_t7_fastq_root="/bi/fastq/T7_Fastq",
        wgs_intake_scan_enabled=True,
        wgs_intake_scan_interval_seconds=1800,
        wgs_auto_dispatch_enabled=False,
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


def test_wgs_t7_intake_endpoints_are_read_only_and_do_not_expose_sample_ids(tmp_path, monkeypatch):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    observed_at = datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc)
    with sessions() as session:
        session.add(
            WgsIntakeBatch(
                source_path="/bi/fastq/T7_Fastq/2201th_20260821B_E250208844",
                chip_id="2201th_20260821B_E250208844",
                sequencing_batch="20260821B",
                state="ready",
                eligible_pair_count=17,
                excluded_addon_pair_count=5,
                pair_issue_count=0,
                eligible_fingerprint="a" * 64,
                observed_fingerprint="a" * 64,
                first_seen_at=observed_at,
                last_scanned_at=observed_at,
                ready_at=observed_at,
            )
        )
        session.add(
            WgsIntakeScannerState(
                id=1,
                first_scan_at=observed_at,
                last_scan_at=observed_at,
                last_scanned_directory_count=1830,
            )
        )
        session.commit()

    login(client, "viewer", "viewer-pass")
    response = client.get("/api/intake/status?pipeline=wgs&state=ready&limit=10&offset=0")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"] == [
        {
            "pipeline": "wgs",
            "chip_id": "2201th_20260821B_E250208844",
            "batch_id": "2201th_20260821B_E250208844",
            "sequencing_batch": "20260821B",
            "ready_state": "ready",
            "submit_state": "disabled",
            "analysis_id": None,
            "eligible_pair_count": 17,
            "excluded_addon_pair_count": 5,
            "pair_issue_count": 0,
            "last_error": None,
            "last_seen_at": "2026-08-29T08:30:00+00:00",
        }
    ]
    assert "source_path" not in response.text
    assert "eligible_fingerprint" not in response.text

    dashboard = client.get(
        "/api/intake/status?pipeline=deployed&view=pending&limit=10&offset=0"
    )
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["total"] == 1
    assert dashboard.json()["items"][0]["chip_id"] == "2201th_20260821B_E250208844"

    scanner = client.get("/api/intake/scanner-state")
    assert scanner.status_code == 200, scanner.text
    assert scanner.json() == {
        "scanner": "wgs-intake-scanner",
        "root": "/bi/fastq/T7_Fastq",
        "enabled": True,
        "schedule_seconds": 1800,
        "auto_dispatch_enabled": False,
        "first_scan_at": "2026-08-29T08:30:00+00:00",
        "last_scan_at": "2026-08-29T08:30:00+00:00",
        "last_scanned_directory_count": 1830,
        "last_error": None,
    }


def test_step4_repair_is_fixed_to_cram_idempotent_and_blocked_by_runtime_gates(tmp_path, monkeypatch):
    client, sessions, airflow = make_client(tmp_path, monkeypatch)
    operator_headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=operator_headers,
        json={
            "pipeline": "wgs",
            "project_name": "WGS_Clinical",
            "execution_mode": "cce",
            "batch_no": "20260821B",
            "fq_path": str(tmp_path),
        },
    ).json()
    analysis_id = created["analysis_id"]
    with sessions() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        run.status = "failed"
        run.current_stage = "step4_publish"
        run.dag_run_id = f"manual__{analysis_id}__a1"
        run.params_json = {
            **run.params_json,
            "resolved_runtime": {
                "repair_groups": {"cram": {"target": "linkage/cram"}},
            },
        }
        session.commit()

    detail = client.get(f"/api/runs/{analysis_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["step4_repair"] == {
        "linkage_group": "cram",
        "available": False,
        "reason": "runtime_unavailable",
        "latest_action": None,
    }

    blocked = client.post(f"/api/runs/{analysis_id}/actions/repair-step4", headers=operator_headers)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "WGS_RUNTIME_DISABLED"
    with sessions() as session:
        assert session.scalars(select(WgsMaintenanceAction)).all() == []
    assert airflow.calls == []

    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    missing_master = client.post(
        f"/api/runs/{analysis_id}/actions/repair-step4", headers=operator_headers
    )
    assert missing_master.status_code == 409
    assert "master" in missing_master.json()["detail"]["message"]
    assert airflow.calls == []
    with sessions() as session:
        session.add(
            KubernetesWorkload(
                analysis_id=analysis_id,
                attempt=1,
                event_id="step3:wgs-master-test",
                pod_hash="master-success",
                job_name="wgs-master-test",
                phase="Succeeded",
            )
        )
        session.commit()
    accepted = client.post(f"/api/runs/{analysis_id}/actions/repair-step4", headers=operator_headers)
    assert accepted.status_code == 202, accepted.text
    repeated = client.post(f"/api/runs/{analysis_id}/actions/repair-step4", headers=operator_headers)
    assert repeated.status_code == 202, repeated.text
    assert repeated.json()["action_id"] == accepted.json()["action_id"]
    assert len(airflow.calls) == 1
    dag_id, dag_run_id, conf = airflow.calls[0]
    assert dag_id == "bio_wgs"
    assert dag_run_id.startswith(f"maintenance__{analysis_id}__a1__step4_cram__")
    assert conf["maintenance_mode"] == "repair_step4"
    assert conf["repair_group"] == "cram"
    assert conf["attempt"] == 1
    assert conf["continue_after_repair"] is True
    assert "confirm" not in conf
    assert "path" not in conf


def test_viewer_cannot_request_step4_repair(tmp_path, monkeypatch):
    client, _, _ = make_client(tmp_path, monkeypatch)
    viewer_headers = login(client, "viewer", "viewer-pass")

    response = client.post(
        "/api/runs/WGS_20260829_000000_A1B2C3/actions/repair-step4",
        headers=viewer_headers,
    )

    assert response.status_code == 403


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
    assert created.json()["params"]["pipeline_release_id"] == "wgs-4.1.1-1656b5d"
    assert created.json()["params"]["wgs_version"] == "V4.1.1"
    assert created.json()["params"]["wgs_source_commit"] == "1656b5d7a6e2f24242c38149f6d1c92ac266cd37"
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
        "release_id": "wgs-4.1.1-1656b5d",
        "version": "V4.1.1",
        "source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
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


def test_disabled_execution_gate_blocks_wgs_resume(tmp_path, monkeypatch):
    client, sessions, airflow = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=headers,
        json={
            "pipeline": "wgs",
            "project_name": "wgs-cce",
            "execution_mode": "cce",
            "batch_no": "BATCH-RESUME-BLOCKED",
            "fq_path": str(tmp_path),
        },
    ).json()
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(
                AnalysisRun.analysis_id == created["analysis_id"]
            )
        )
        run.status = "failed"
        session.commit()

    response = client.post(
        f"/api/runs/{created['analysis_id']}/actions/resume",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WGS_EXECUTION_DISABLED"
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    adapter_blocked = client.post(
        f"/api/runs/{created['analysis_id']}/actions/resume",
        headers=headers,
    )
    assert adapter_blocked.status_code == 409
    assert adapter_blocked.json()["detail"]["code"] == "WGS_RUNTIME_DISABLED"
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(
                AnalysisRun.analysis_id == created["analysis_id"]
            )
        )
        assert run.attempt == 1
        assert run.status == "failed"
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
    assert request["pipeline_release_id"] == "wgs-4.1.1-1656b5d"
    assert request["wgs_source_commit"] == "1656b5d7a6e2f24242c38149f6d1c92ac266cd37"
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

    binding_path = (
        tmp_path
        / "runtime"
        / "runs"
        / analysis_id
        / "attempt-1"
        / "batch-binding.json"
    )
    binding_path.parent.mkdir(parents=True)
    binding_path.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.batch-binding.v2",
                "analysis_id": analysis_id,
                "attempt": 1,
                "pipeline_release_id": "wgs-4.1.1-1656b5d",
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
                "master_job": "wgs-master-0123456789abcdef0123",
                "namespace": "snakemake-ns",
                "resolved_runtime": {"cce_pipeline_version": "0.8.1"},
            }
        ),
        encoding="utf-8",
    )
    status_path = request_path.with_name("step3_monitor.status.json")
    status_path.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step3_monitor",
                    "status": "running",
                    "updated_at": "2026-08-30T02:00:00Z",
                    "message": "running",
                    "monitoring_health": "healthy",
                    "master_job": "wgs-master-0123456789abcdef0123",
                    "namespace": "snakemake-ns",
                    "run_label": "cce-run-0123456789abcdef",
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


def test_step3_stage_registration_recovers_same_failed_attempt_and_audits(
    tmp_path, monkeypatch
):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=headers,
        json={
            "pipeline": "wgs",
            "project_name": "WGS_Clinical",
            "execution_mode": "cce",
            "batch_no": "WGS_20260825A_T7Hg38V4.1.1",
            "fq_path": str(tmp_path),
        },
    ).json()
    analysis_id = created["analysis_id"]
    failed_at = datetime(2026, 9, 1, 4, 24, tzinfo=timezone.utc)
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        run.status = "failed"
        run.current_stage = "step3_monitor"
        run.ended_at = failed_at
        run.pipeline_finished_at = failed_at
        run.error_summary = "monitor API returned HTTP 500"
        session.commit()

    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    response = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/step3_monitor",
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
        json={
            "attempt": 1,
            "adapter": "wgs-runtime-200",
            "command": f"wgs-runtime {analysis_id} 1 step3_monitor",
        },
    )

    assert response.status_code == 200, response.text
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        assert run.status == "running"
        assert run.current_stage == "step3_monitor"
        assert run.ended_at is None
        assert run.pipeline_finished_at is None
        assert run.error_summary is None
        recovery = session.scalar(
            select(AuditLog).where(
                AuditLog.analysis_id == analysis_id,
                AuditLog.action == "run.step3_monitor_recovered",
            )
        )
        assert recovery is not None
        assert recovery.username == "airflow-internal"


def test_step3_stage_status_api_treats_accepted_as_transitional(
    tmp_path, monkeypatch
):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=headers,
        json={
            "pipeline": "wgs",
            "project_name": "WGS_Clinical",
            "execution_mode": "cce",
            "batch_no": "WGS_20260825A_T7Hg38V4.1.1",
            "fq_path": str(tmp_path),
        },
    ).json()
    analysis_id = created["analysis_id"]
    runtime = tmp_path / "runtime"
    binding = runtime / "runs" / analysis_id / "attempt-1" / "batch-binding.json"
    binding.parent.mkdir(parents=True)
    binding.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.batch-binding.v2",
                "analysis_id": analysis_id,
                "attempt": 1,
                "pipeline_release_id": "wgs-4.1.1-1656b5d",
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
                "master_job": "cce-master-0123456789abcdef0123",
                "namespace": "snakemake-ns",
                "resolved_runtime": {"cce_pipeline_version": "0.8.1"},
            }
        ),
        encoding="utf-8",
    )
    status_path = (
        runtime
        / "runner-requests"
        / analysis_id
        / "attempt-1"
        / "step3_monitor.status.json"
    )
    status_path.parent.mkdir(parents=True)
    status_path.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step3_monitor",
                "status": "accepted",
                "message": "",
                "updated_at": "2026-09-01T04:24:41Z",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")

    response = client.get(
        f"/api/internal/wgs/runs/{analysis_id}/stage-status",
        params={"attempt": 1, "stage": "step3_monitor"},
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "accepted"
    assert response.json()["ready"] is False
    assert response.json()["failed"] is False


def test_internal_step3_observer_activation_and_drain_are_exposed_in_run_detail(
    tmp_path, monkeypatch
):
    client, _, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=headers,
        json={
            "pipeline": "wgs",
            "project_name": "clinical-wgs",
            "execution_mode": "cce",
            "batch_no": "BATCH-OBSERVER",
            "fq_path": str(tmp_path),
        },
    ).json()
    analysis_id = created["analysis_id"]
    internal = {"X-Airflow-Demo-Token": "internal-test-token"}

    activated = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/observer/activate",
        headers=internal,
        json={"attempt": 1},
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["lifecycle_status"] == "active"
    detail = client.get(f"/api/runs/{analysis_id}", headers=headers).json()
    assert detail["observer"]["lifecycle_status"] == "active"
    assert detail["observer"]["monitoring_health"] == "healthy"

    drained = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/observer/deactivate",
        headers=internal,
        json={"attempt": 1},
    )
    assert drained.status_code == 200, drained.text
    assert drained.json()["lifecycle_status"] == "draining"


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
                "pipeline_release_id": "wgs-4.1.1-1656b5d",
                "wgs_version": "V4.1.1",
                "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
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
    assert detail.json()["pipeline_release_id"] == "wgs-4.1.1-1656b5d"
    assert detail.json()["wgs_version"] == "V4.1.1"
    assert detail.json()["wgs_source_commit"].startswith("1656b5d")
    assert detail.json()["resolved_runtime"] is None
    assert "pipeline_snapshot_id" not in detail.json()
    assert detail.json()["rule_event_schema_version"] == "1"
    assert detail.json()["observer"]["monitoring_health"] == "healthy"
    assert detail.json()["observer"]["lifecycle_status"] == "stopped"
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
