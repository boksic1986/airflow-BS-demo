from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
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
    RunAttempt,
    RunStageState,
    Sample,
    UserAccount,
    WgsIntakeBatch,
    WgsIntakeScannerState,
    WgsMaintenanceAction,
)
from app.wgs_orchestration_service import build_fastq_snapshot, fastq_source_fingerprint
from app.wgs_sample_projection import _qc_status


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
        self.runs = {}

    def trigger_dag_run(self, dag_id, *, dag_run_id=None, conf=None):
        self.calls.append((dag_id, dag_run_id, conf))
        payload = {"dag_run_id": dag_run_id, "conf": conf}
        self.runs[(dag_id, dag_run_id)] = payload
        return payload

    def get_dag_run(self, dag_id, dag_run_id):
        return self.runs.get((dag_id, dag_run_id))


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
    project_catalog = tmp_path / "wgs_projects.yaml"
    project_catalog.write_text(
        """schema_version: "1"
projects:
  - project_id: WGS_Clinical
    display_name: WGS Clinical
    project_name: WGS_Clinical
    platforms:
      - platform_id: T7Hg38V4.1.1
        display_name: T7 WGS
    fastq_roots:
      - root_id: T7_Fastq
        display_name: T7 FASTQ root
        node200_path: /bi/fastq/T7_Fastq
    editable_config:
      use_reference: {type: boolean, default: false}
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
        wgs_project_catalog_path=str(project_catalog),
        wgs_submission_draft_root=str(tmp_path / "runtime" / "submission-drafts"),
        wgs_submission_draft_ttl_hours=24,
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


def test_wgs_submission_draft_is_server_catalogued_and_does_not_create_run(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("WGS_SUBMISSION_PREVIEW_ENABLED", "true")
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    projects = client.get("/api/wgs/projects", headers=headers)
    assert projects.status_code == 200
    assert projects.json()["items"][0]["project_id"] == "WGS_Clinical"
    assert "node200_path" not in str(projects.json())

    created = client.post(
        "/api/wgs/submission-drafts",
        headers=headers,
        json={
            "project_id": "WGS_Clinical",
            "platform": "T7Hg38V4.1.1",
            "sequencing_batch": "20260901A",
            "analysis_batch": "WGS_20260901A_T7Hg38V4.1.1",
            "fastq_root_id": "T7_Fastq",
            "use_reference": False,
        },
    )
    assert created.status_code == 202, created.text
    assert created.json()["status"] == "queued"
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 0
    disabled = client.post(
        f"/api/wgs/submission-drafts/{created.json()['draft_id']}/submit",
        headers={**headers, "Idempotency-Key": "draft-submit-1"},
    )
    assert disabled.status_code == 409
    assert disabled.json()["detail"]["code"] == "WGS_EXECUTION_DISABLED"
    forged = client.post(
        "/api/wgs/submission-drafts",
        headers=headers,
        json={
            "project_id": "WGS_Clinical",
            "platform": "T7Hg38V4.1.1",
            "sequencing_batch": "20260901A",
            "analysis_batch": "WGS_20260901A_T7Hg38V4.1.1",
            "fastq_root_id": "T7_Fastq",
            "use_reference": False,
            "path": "/arbitrary/server/path",
        },
    )
    assert forged.status_code == 422


def test_staged_wgs_run_rejects_stage_two_fields_and_uses_canonical_id(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    client, sessions, airflow = make_client(tmp_path, monkeypatch)
    viewer_headers = login(client, "viewer", "viewer-pass")
    request = {
        "project_id": "WGS_Clinical",
        "platform": "T7Hg38V4.1.1",
        "batch": "20260901A",
        "fastq_root_id": "T7_Fastq",
    }
    assert client.post("/api/wgs/runs", headers=viewer_headers, json=request).status_code == 403
    operator_headers = login(client, "operator", "operator-pass")
    assert client.post(
        "/api/wgs/runs",
        headers=operator_headers,
        json={**request, "use_reference": "ref"},
    ).status_code == 422

    created = client.post("/api/wgs/runs", headers=operator_headers, json=request)
    assert created.status_code == 201, created.text
    analysis_id = created.json()["analysis_id"]
    assert airflow.calls[0][1] == f"{analysis_id}-a1"
    assert airflow.calls[0][2]["params"]["submission_phase"] == "preparing_sampleinfo"
    assert client.post(
        f"/api/runs/{analysis_id}/actions/approve-wgs-config",
        headers=operator_headers,
        json={"use_reference": "ref", "resource_set": "default"},
    ).status_code == 409
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 1


def test_wgs_submission_draft_final_submit_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("WGS_SUBMISSION_PREVIEW_ENABLED", "true")
    client, sessions, airflow = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/wgs/submission-drafts",
        headers=headers,
        json={
            "project_id": "WGS_Clinical",
            "platform": "T7Hg38V4.1.1",
            "sequencing_batch": "20260901A",
            "analysis_batch": "WGS_20260901A_T7Hg38V4.1.1",
            "fastq_root_id": "T7_Fastq",
            "use_reference": False,
        },
    )
    assert created.status_code == 202, created.text
    draft_id = created.json()["draft_id"]
    source_fingerprint = fastq_source_fingerprint(build_fastq_snapshot(
        fq_path=str(tmp_path),
        allowed_link_roots=[str(tmp_path)],
        allowed_fastq_roots=[str(tmp_path / "fastq-source")],
        manifest_path=tmp_path / "draft-preview-manifest.json",
    ))
    preview = client.post(
        f"/api/internal/wgs/submission-drafts/{draft_id}/complete",
        headers={**headers, "X-Internal-Service-Token": "internal-test-token"},
        json={
            "prepared_fq_path": str(tmp_path),
            "samples": [{
                "sample_id": "S1",
                "family_id": "F1",
                "r1_filename": "S1_R1.fastq.gz",
                "r2_filename": "S1_R2.fastq.gz",
            }],
            "families": [{"family_id": "F1", "sample_count": 1}],
            "resolved_config": {"profile_id": "wgs-4.1.1", "resource_set": "production"},
            "source_fingerprint": source_fingerprint,
        },
    )
    assert preview.status_code == 200, preview.text
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    submit_headers = {**headers, "Idempotency-Key": "same-browser-submit"}
    first = client.post(f"/api/wgs/submission-drafts/{draft_id}/submit", headers=submit_headers)
    second = client.post(f"/api/wgs/submission-drafts/{draft_id}/submit", headers=submit_headers)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["analysis_id"] == first.json()["analysis_id"]
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 1
    assert len(airflow.calls) == 1


def test_wgs_submission_retry_recovers_db_bound_run_after_airflow_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("WGS_SUBMISSION_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    client, sessions, airflow = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/wgs/submission-drafts",
        headers=headers,
        json={
            "project_id": "WGS_Clinical",
            "platform": "T7Hg38V4.1.1",
            "sequencing_batch": "20260901A",
            "analysis_batch": "WGS_20260901A_T7Hg38V4.1.1",
            "fastq_root_id": "T7_Fastq",
            "use_reference": False,
        },
    )
    draft_id = created.json()["draft_id"]
    source_fingerprint = fastq_source_fingerprint(build_fastq_snapshot(
        fq_path=str(tmp_path),
        allowed_link_roots=[str(tmp_path)],
        allowed_fastq_roots=[str(tmp_path / "fastq-source")],
        manifest_path=tmp_path / "draft-preview-manifest.json",
    ))
    completed = client.post(
        f"/api/internal/wgs/submission-drafts/{draft_id}/complete",
        headers={**headers, "X-Internal-Service-Token": "internal-test-token"},
        json={
            "prepared_fq_path": str(tmp_path),
            "samples": [{"sample_id": "S1", "family_id": "F1"}],
            "families": [{"family_id": "F1", "sample_count": 1}],
            "resolved_config": {},
            "source_fingerprint": source_fingerprint,
        },
    )
    assert completed.status_code == 200
    original_trigger = airflow.trigger_dag_run
    airflow.trigger_dag_run = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Airflow unavailable"))
    with pytest.raises(RuntimeError, match="Airflow unavailable"):
        client.post(
            f"/api/wgs/submission-drafts/{draft_id}/submit",
            headers={**headers, "Idempotency-Key": "recover-submit"},
        )
    with sessions() as session:
        runs = session.scalars(select(AnalysisRun)).all()
        assert len(runs) == 1
        assert runs[0].status == "created"
    airflow.trigger_dag_run = original_trigger
    recovered = client.post(
        f"/api/wgs/submission-drafts/{draft_id}/submit",
        headers={**headers, "Idempotency-Key": "recover-submit"},
    )
    assert recovered.status_code == 200, recovered.text
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 1
    assert len(airflow.calls) == 1


def test_wgs_submission_retry_recovers_after_airflow_created_before_response(tmp_path, monkeypatch):
    monkeypatch.setenv("WGS_SUBMISSION_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    client, sessions, airflow = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/wgs/submission-drafts",
        headers=headers,
        json={
            "project_id": "WGS_Clinical",
            "platform": "T7Hg38V4.1.1",
            "sequencing_batch": "20260901A",
            "analysis_batch": "WGS_20260901A_T7Hg38V4.1.1",
            "fastq_root_id": "T7_Fastq",
            "use_reference": False,
        },
    )
    draft_id = created.json()["draft_id"]
    source_fingerprint = fastq_source_fingerprint(build_fastq_snapshot(
        fq_path=str(tmp_path),
        allowed_link_roots=[str(tmp_path)],
        allowed_fastq_roots=[str(tmp_path / "fastq-source")],
        manifest_path=tmp_path / "draft-preview-manifest.json",
    ))
    completed = client.post(
        f"/api/internal/wgs/submission-drafts/{draft_id}/complete",
        headers={**headers, "X-Internal-Service-Token": "internal-test-token"},
        json={
            "prepared_fq_path": str(tmp_path),
            "samples": [{"sample_id": "S1", "family_id": "F1"}],
            "families": [{"family_id": "F1", "sample_count": 1}],
            "resolved_config": {},
            "source_fingerprint": source_fingerprint,
        },
    )
    assert completed.status_code == 200
    original_trigger = airflow.trigger_dag_run

    def created_then_lost(*args, **kwargs):
        original_trigger(*args, **kwargs)
        raise RuntimeError("Airflow response lost")

    airflow.trigger_dag_run = created_then_lost
    with pytest.raises(RuntimeError, match="response lost"):
        client.post(
            f"/api/wgs/submission-drafts/{draft_id}/submit",
            headers={**headers, "Idempotency-Key": "response-lost-submit"},
        )
    airflow.trigger_dag_run = original_trigger
    recovered = client.post(
        f"/api/wgs/submission-drafts/{draft_id}/submit",
        headers={**headers, "Idempotency-Key": "response-lost-submit"},
    )
    assert recovered.status_code == 200, recovered.text
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 1
    assert len(airflow.calls) == 1


def test_wgs_submission_draft_is_fail_closed_without_preview_contract(tmp_path, monkeypatch):
    client, sessions, airflow = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    response = client.post(
        "/api/wgs/submission-drafts",
        headers=headers,
        json={
            "project_id": "WGS_Clinical",
            "platform": "T7Hg38V4.1.1",
            "sequencing_batch": "20260901A",
            "analysis_batch": "WGS_20260901A_T7Hg38V4.1.1",
            "fastq_root_id": "T7_Fastq",
            "use_reference": False,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WGS_DRAFT_PREVIEW_DISABLED"
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 0
    assert airflow.calls == []


def test_step7_cleanup_is_admin_only_and_disabled_by_default(tmp_path, monkeypatch):
    client, _, airflow = make_client(tmp_path, monkeypatch)
    viewer_headers = login(client, "viewer", "viewer-pass")
    viewer = client.post(
        "/api/runs/WGS_STEP7/actions/cleanup-step7",
        headers=viewer_headers,
        json={"batch_confirmation": "WGS_BATCH"},
    )
    assert viewer.status_code == 403
    client.post("/api/auth/logout", headers=viewer_headers)

    operator_headers = login(client, "operator", "operator-pass")
    operator = client.post(
        "/api/runs/WGS_STEP7/actions/cleanup-step7",
        headers=operator_headers,
        json={"batch_confirmation": "WGS_BATCH"},
    )
    assert operator.status_code == 403
    client.post("/api/auth/logout", headers=operator_headers)

    admin_headers = login(client, "admin", "admin-pass")
    admin = client.post(
        "/api/runs/WGS_STEP7/actions/cleanup-step7",
        headers=admin_headers,
        json={"batch_confirmation": "WGS_BATCH"},
    )
    assert admin.status_code == 409
    assert admin.json()["detail"]["code"] == "WGS_RUNTIME_DISABLED"
    assert airflow.calls == []


def test_internal_step7_cannot_bypass_admin_maintenance_action(tmp_path, monkeypatch):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id="WGS_20260901_010203_ABCDEF",
                pipeline_name="wgs",
                dag_id="bio_wgs",
                execution_mode="cce",
                attempt=1,
                status="success",
                workdir=str(tmp_path / "results" / "run"),
                params_json={
                    "pipeline_release_id": "wgs-4.1.1-1656b5d",
                    "wgs_version": "V4.1.1",
                    "wgs_source_commit": "1656b5d7a6e2f24242c38149f6d1c92ac266cd37",
                    "project_name": "WGS_Clinical",
                    "batch_no": "WGS_20260901A_T7Hg38V4.1.1",
                    "fq_path": str(tmp_path),
                },
            )
        )
        session.commit()
    response = client.post(
        "/api/internal/wgs/runs/WGS_20260901_010203_ABCDEF/stages/step7_cleanup",
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
        json={
            "attempt": 1,
            "adapter": "wgs-runtime-200",
            "command": "wgs-runtime WGS_20260901_010203_ABCDEF 1 step7_cleanup",
            "maintenance_action_id": "step7-sfs-forged",
        },
    )
    assert response.status_code == 400
    assert "active admin maintenance action" in response.json()["detail"]["message"]

    with sessions() as session:
        for stage in ("step5_download", "step6_materialize"):
            session.add(
                RunStageState(
                    analysis_id="WGS_20260901_010203_ABCDEF",
                    attempt=1,
                    stage_code=stage,
                    stage_label=stage,
                    stage_status="success",
                    progress_source="test",
                )
            )
        session.add(
            WgsMaintenanceAction(
                action_id="step7-sfs-abcdef123456",
                analysis_id="WGS_20260901_010203_ABCDEF",
                attempt=1,
                action_type="cleanup_step7_sfs",
                linkage_group="sfs",
                status="queued",
                requested_by="admin",
            )
        )
        session.commit()
    accepted = client.post(
        "/api/internal/wgs/runs/WGS_20260901_010203_ABCDEF/stages/step7_cleanup",
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
        json={
            "attempt": 1,
            "adapter": "wgs-runtime-200",
            "command": "wgs-runtime WGS_20260901_010203_ABCDEF 1 step7_cleanup",
            "maintenance_action_id": "step7-sfs-abcdef123456",
        },
    )
    assert accepted.status_code == 200, accepted.text
    with sessions() as session:
        stage = session.scalar(
            select(RunStageState).where(RunStageState.stage_code == "step7_cleanup")
        )
        assert stage.stage_status == "accepted"
        assert stage.stage_label == "Cleaning WGS SFS workspace"


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
                event_id="step3:cce-master-test",
                pod_hash="master-success",
                job_name="cce-master-test",
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
            "submission_preview_enabled": False,
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
    assert request["schema_version"] == "wgs-runtime.request.v4"
    assert request["analysis_project_root"] == str(tmp_path / "results")
    assert request["expected_batch_root"].endswith("/results/BATCH-001")
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
                "master_job": "cce-master-0123456789abcdef0123",
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
                    "master_job": "cce-master-0123456789abcdef0123",
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
    pods_response = client.get(f"/api/runs/{analysis_id}/pods", headers=headers)
    assert pods_response.status_code == 200
    assert [item["job_name"] for item in pods_response.json()["items"]] == [
        "cce-master-0123456789abcdef0123"
    ]


def test_finalize_run_records_immutable_business_completion_time(tmp_path, monkeypatch):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=headers,
        json={
            "pipeline": "wgs",
            "project_name": "clinical-wgs",
            "execution_mode": "cce",
            "batch_no": "BATCH-FINISH",
            "fq_path": str(tmp_path),
        },
    ).json()
    analysis_id = created["analysis_id"]
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    internal = {"X-Airflow-Demo-Token": "internal-test-token"}
    marker = (
        tmp_path
        / "runtime"
        / "runner-requests"
        / analysis_id
        / "attempt-1"
        / "step6_materialize.status.json"
    )
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step6_materialize",
                "status": "success",
            }
        ),
        encoding="utf-8",
    )
    body = {"attempt": 1, "adapter": "wgs-runtime-200", "command": "control"}

    first = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/finalize_run",
        headers=internal,
        json=body,
    )
    assert first.status_code == 200, first.text
    with sessions() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        assert run.ended_at is not None
        assert run.pipeline_finished_at == run.ended_at
        first_finished_at = run.pipeline_finished_at

    second = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/finalize_run",
        headers=internal,
        json=body,
    )
    assert second.status_code == 200, second.text
    with sessions() as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id))
        assert run.pipeline_finished_at == first_finished_at
        assert run.ended_at == first_finished_at


def test_finalize_run_reconciles_same_attempt_after_control_plane_failure(
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
            "batch_no": "BATCH-FINISH-RECOVERY",
            "fq_path": str(tmp_path),
        },
    ).json()
    analysis_id = created["analysis_id"]
    failed_at = datetime(2026, 9, 1, 9, 45, tzinfo=timezone.utc)
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        run.status = "failed"
        run.ended_at = failed_at
        run.pipeline_finished_at = failed_at
        run.error_summary = "stale control-plane failure"
        samples = session.scalars(
            select(Sample).where(Sample.analysis_id == analysis_id)
        ).all()
        if not samples:
            samples = [
                Sample(
                    analysis_id=analysis_id,
                    sample_id="S1",
                    status="failed",
                    qc_status="unknown",
                )
            ]
            session.add_all(samples)
        for sample in samples:
            sample.status = "failed"
        session.commit()
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    marker = (
        tmp_path
        / "runtime"
        / "runner-requests"
        / analysis_id
        / "attempt-1"
        / "step6_materialize.status.json"
    )
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step6_materialize",
                "status": "success",
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/finalize_run",
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
        json={"attempt": 1, "adapter": "wgs-runtime-200", "command": "control"},
    )

    assert response.status_code == 200, response.text
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        samples = session.scalars(
            select(Sample).where(Sample.analysis_id == analysis_id)
        ).all()
        assert run.status == "success"
        assert run.error_summary is None
        assert run.progress_percent == 100
        assert run.pipeline_finished_at != failed_at
        assert run.ended_at == run.pipeline_finished_at
        assert {sample.status for sample in samples} == {"success"}


def test_finalize_run_rejects_step6_marker_from_another_attempt(tmp_path, monkeypatch):
    client, _, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "operator", "operator-pass")
    created = client.post(
        "/api/runs",
        headers=headers,
        json={
            "pipeline": "wgs",
            "project_name": "clinical-wgs",
            "execution_mode": "cce",
            "batch_no": "BATCH-FINISH-IDENTITY",
            "fq_path": str(tmp_path),
        },
    ).json()
    analysis_id = created["analysis_id"]
    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    marker = (
        tmp_path / "runtime" / "runner-requests" / analysis_id / "attempt-1"
        / "step6_materialize.status.json"
    )
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 2,
                "stage": "step6_materialize",
                "status": "success",
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/finalize_run",
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
        json={"attempt": 1, "adapter": "wgs-runtime-200", "command": "control"},
    )

    assert response.status_code == 400
    assert "Step6 materialization is not complete" in response.text


def test_wgs_samples_endpoint_returns_safe_manifest_and_backend_state_matrix(
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
            "batch_no": "WGS_20260904A_T7Hg38V4.1.1",
            "fq_path": str(tmp_path),
        },
    ).json()
    analysis_id = created["analysis_id"]
    batch_root = tmp_path / "results" / "WGS_20260904A_T7Hg38V4.1.1"
    batch_root.mkdir(parents=True)
    (batch_root / "sampleinfo.tsv").write_text(
        "\t".join(
            [
                "姓名", "送检医院", "样本编号", "数据编号", "样本类型",
                "家系编号", "家系关系", "收样日期", "预计报告日期",
            ]
        )
        + "\n"
        + "\t".join(
            [
                "PRIVATE NAME", "PRIVATE HOSPITAL", "SAMPLE-1", "DATA-1-WGS",
                "全血", "FAMILY-1", "先证者", "2026-09-01", "2026-09-20",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    qc_dir = batch_root / "07_QC"
    qc_dir.mkdir()
    (qc_dir / "WGS_20260904A_T7Hg38V4.1.1.QCstat.tsv").write_text(
        "Sample_ID\t是否通过质控\tClean_Q30%\tMapped_Reads%\tAverage_Depth\t>=20X\tcontamination\n"
        "SAMPLE-1\t通过\t92.1\t99.2\t35.4\t98.5\t0.002\n",
        encoding="utf-8",
    )
    # Production keeps the batch summary beside per-sample QCstat files.  The
    # extra file must not make the controlled batch projection disappear.
    (qc_dir / "DATA-1-WGS.deduped.bam.1.QCstat.tsv").write_text(
        "Sample_ID\t是否通过质控\tAverage_Depth\n"
        "SAMPLE-1\t通过\t35.4\n",
        encoding="utf-8",
    )
    binding = (
        tmp_path / "runtime" / "runs" / analysis_id / "attempt-1"
        / "batch-binding.json"
    )
    binding.parent.mkdir(parents=True)
    binding.write_text(
        json.dumps(
            {
                "analysis_id": analysis_id,
                "attempt": 1,
                "batch_root": str(batch_root),
                "run_id": f"{analysis_id}-a1",
            }
        ),
        encoding="utf-8",
    )
    with sessions() as session:
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="SAMPLE-1",
                family_id="FAMILY-1",
                status="running",
                qc_status="unknown",
                metadata_json={
                    "data_id": "DATA-1-WGS",
                    "family_relation": "先证者",
                },
            )
        )
        session.add_all(
            [
                RuleState(
                    analysis_id=analysis_id,
                    attempt=1,
                    rule_instance_id="rule-1",
                    rule_name="mapping",
                    sequence=1,
                    phase="Mapping",
                    sample_id="SAMPLE-1",
                    status="success",
                ),
                RuleState(
                    analysis_id=analysis_id,
                    attempt=1,
                    rule_instance_id="rule-2",
                    rule_name="QualCal",
                    sequence=2,
                    phase="Variant analysis",
                    sample_id="SAMPLE-1",
                    status="running",
                ),
            ]
        )
        session.commit()

    response = client.get(f"/api/runs/{analysis_id}/samples", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["manifest"] == [
        {
            "sample_id": "SAMPLE-1",
            "data_id": "DATA-1-WGS",
            "sample_type": "全血",
            "family_id": "FAMILY-1",
            "family_relation": "先证者",
            "received_date": "2026-09-01",
            "estimated_report_date": "2026-09-20",
        }
    ]
    assert "PRIVATE NAME" not in response.text
    assert "PRIVATE HOSPITAL" not in response.text
    assert payload["items"][0] | {
        "current_rule": "QualCal",
        "completed_rules": 1,
        "total_rules": 2,
        "progress_percent": 50,
        "status": "running",
        "qc_status": "pass",
    } == payload["items"][0]
    assert payload["items"][0]["qc_metrics"]["average_depth"] == "35.4"
    artifacts = client.get(f"/api/runs/{analysis_id}/artifacts", headers=headers)
    assert artifacts.status_code == 200, artifacts.text
    qc_artifact = next(
        item for item in artifacts.json()["items"] if item["key"] == "wgs_qcstat"
    )
    assert qc_artifact["path"] == (
        "07_QC/WGS_20260904A_T7Hg38V4.1.1.QCstat.tsv"
    )


def test_wgs_qc_free_text_exception_is_warning_not_unknown():
    assert _qc_status("CNV数量偏高") == "warn"
    assert _qc_status("") == "unknown"


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


def test_step4_stage_registration_recovers_known_master_completion_race(
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
    failed_at = datetime(2026, 9, 1, 8, 26, tzinfo=timezone.utc)
    status_dir = tmp_path / "runtime" / "runner-requests" / analysis_id / "attempt-1"
    status_dir.mkdir(parents=True)
    (status_dir / "step4_publish.status.json").write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step4_publish",
                "status": "failed",
                "message": "RuntimeError: Step4 requires a successful Master Job",
            }
        ),
        encoding="utf-8",
    )
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        run.status = "failed"
        run.current_stage = "step4_publish"
        run.ended_at = failed_at
        run.pipeline_finished_at = failed_at
        run.error_summary = "Step4 requires a successful Master Job"
        session.commit()

    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    response = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/step4_publish",
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
        json={
            "attempt": 1,
            "adapter": "wgs-runtime-200",
            "command": f"wgs-runtime {analysis_id} 1 step4_publish",
        },
    )

    assert response.status_code == 200, response.text
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        assert run.status == "publishing"
        assert run.current_stage == "step4_publish"
        assert run.ended_at is None
        assert run.pipeline_finished_at is None
        assert run.error_summary is None
        recovery = session.scalar(
            select(AuditLog).where(
                AuditLog.analysis_id == analysis_id,
                AuditLog.action == "run.step4_publish_recovered",
            )
        )
        assert recovery is not None
        assert recovery.username == "airflow-internal"


def test_step5_stage_registration_recovers_failed_projection_after_step4_success(
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
    failed_at = datetime(2026, 9, 1, 8, 26, tzinfo=timezone.utc)
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        run.status = "failed"
        run.current_stage = "step4_publish"
        run.ended_at = failed_at
        run.pipeline_finished_at = failed_at
        run.error_summary = "stale Step4 control-plane failure"
        session.commit()
    status_dir = tmp_path / "runtime" / "runner-requests" / analysis_id / "attempt-1"
    status_dir.mkdir(parents=True)
    (status_dir / "step4_publish.status.json").write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step4_publish",
                "status": "success",
                "updated_at": (failed_at + timedelta(minutes=1)).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    response = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/step5_download",
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
        json={
            "attempt": 1,
            "adapter": "wgs-runtime-200",
            "command": f"wgs-runtime {analysis_id} 1 step5_download",
        },
    )

    assert response.status_code == 200, response.text
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        assert run.status == "downloading"
        assert run.current_stage == "step5_download"
        assert run.ended_at is None
        assert run.pipeline_finished_at is None
        assert run.error_summary is None
        recovery = session.scalar(
            select(AuditLog).where(
                AuditLog.analysis_id == analysis_id,
                AuditLog.action == "run.step5_download_recovered",
            )
        )
        assert recovery is not None
        assert recovery.username == "airflow-internal"


def test_step5_stage_registration_does_not_hide_a_real_step5_failure(
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
    failed_at = datetime(2026, 9, 1, 9, 45, tzinfo=timezone.utc)
    status_dir = tmp_path / "runtime" / "runner-requests" / analysis_id / "attempt-1"
    status_dir.mkdir(parents=True)
    (status_dir / "step4_publish.status.json").write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step4_publish",
                "status": "success",
            }
        ),
        encoding="utf-8",
    )
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        run.status = "failed"
        run.current_stage = "step5_download"
        run.ended_at = failed_at
        run.pipeline_finished_at = failed_at
        run.error_summary = "result download failed"
        session.commit()

    monkeypatch.setenv("WGS_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    response = client.post(
        f"/api/internal/wgs/runs/{analysis_id}/stages/step5_download",
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
        json={
            "attempt": 1,
            "adapter": "wgs-runtime-200",
            "command": f"wgs-runtime {analysis_id} 1 step5_download",
        },
    )

    assert response.status_code == 200, response.text
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        assert run.status == "failed"
        assert run.current_stage == "step5_download"
        assert run.ended_at.replace(tzinfo=timezone.utc) == failed_at
        assert run.pipeline_finished_at.replace(tzinfo=timezone.utc) == failed_at
        assert run.error_summary == "result download failed"
        assert session.scalar(
            select(AuditLog).where(
                AuditLog.analysis_id == analysis_id,
                AuditLog.action == "run.step5_download_recovered",
            )
        ) is None


def test_step4_terminal_failure_is_projected_to_business_run(tmp_path, monkeypatch):
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
    status_dir = tmp_path / "runtime" / "runner-requests" / analysis_id / "attempt-1"
    status_dir.mkdir(parents=True)
    (status_dir / "step4_publish.status.json").write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "step4_publish",
                "status": "failed",
                "message": "ANALYSIS_COMPLETE is invalid",
                "updated_at": "2026-09-01T09:45:07+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")

    response = client.get(
        f"/api/internal/wgs/runs/{analysis_id}/stage-status",
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
        params={"attempt": 1, "stage": "step4_publish"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["failed"] is True
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        assert run.status == "failed"
        assert run.current_stage == "step4_publish"
        assert run.error_summary == "ANALYSIS_COMPLETE is invalid"
        assert run.ended_at == datetime(2026, 9, 1, 9, 45, 7)
        assert run.pipeline_finished_at == datetime(2026, 9, 1, 9, 45, 7)


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


def test_prepare_sampleinfo_stage_status_imports_preview_samples(
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
    with sessions.begin() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        run.params_json = {
            **dict(run.params_json or {}),
            "submission_mode": "three_stage",
            "submission_phase": "preparing_sampleinfo",
        }

    sampleinfo = (
        tmp_path
        / "results"
        / "sampleinfo"
        / "WGS_20260825A_T7Hg38V4.1.1.sampleinfo.txt"
    )
    sampleinfo.parent.mkdir(parents=True)
    sampleinfo.write_text(
        "样本编号\t数据编号\t家系编号\t家系关系\t样本类型\t性别\t上机批次\n"
        "SAMPLE-1\tDATA-1\tFAMILY-1\t先证者\t外周血\t男\t20260825A\n",
        encoding="utf-8",
    )
    status_path = (
        tmp_path
        / "runtime"
        / "runner-requests"
        / analysis_id
        / "attempt-1"
        / "prepare_sampleinfo.status.json"
    )
    status_path.parent.mkdir(parents=True)
    status_path.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "prepare_sampleinfo",
                "status": "success",
                "message": "",
                "updated_at": "2026-09-03T08:29:28Z",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")

    response = client.get(
        f"/api/internal/wgs/runs/{analysis_id}/stage-status",
        params={"attempt": 1, "stage": "prepare_sampleinfo"},
        headers={"X-Airflow-Demo-Token": "internal-test-token"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["ready"] is True
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        samples = list(
            session.scalars(
                select(Sample).where(Sample.analysis_id == analysis_id)
            )
        )
        assert run.params_json["submission_phase"] == "config_review"
        assert [(item.sample_id, item.family_id, item.status) for item in samples] == [
            ("SAMPLE-1", "FAMILY-1", "pending")
        ]


def test_prepare_analysis_status_waits_for_final_sampleinfo_nfs_visibility(
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
    with sessions.begin() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        run.params_json = {
            **dict(run.params_json or {}),
            "submission_mode": "three_stage",
            "submission_phase": "preparing_analysis",
        }

    batch_name = "WGS_20260825A_T7Hg38V4.1.1"
    binding = (
        tmp_path
        / "runtime"
        / "runs"
        / analysis_id
        / "attempt-1"
        / "batch-binding.json"
    )
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
                    "batch_root": str(tmp_path / "results" / batch_name),
                    "resolved_runtime": {"cce_pipeline_version": "0.8.1"},
                }
        ),
        encoding="utf-8",
    )
    status_path = (
        tmp_path
        / "runtime"
        / "runner-requests"
        / analysis_id
        / "attempt-1"
        / "prepare_analysis.status.json"
    )
    status_path.parent.mkdir(parents=True)
    status_path.write_text(
        json.dumps(
            {
                "schema_version": "wgs-runtime.stage-status.v1",
                "analysis_id": analysis_id,
                "attempt": 1,
                "stage": "prepare_analysis",
                "status": "success",
                "message": "",
                "updated_at": "2026-09-04T01:07:08Z",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WGS_RUNTIME_ADAPTER_ENABLED", "true")
    internal = {"X-Airflow-Demo-Token": "internal-test-token"}

    waiting = client.get(
        f"/api/internal/wgs/runs/{analysis_id}/stage-status",
        params={"attempt": 1, "stage": "prepare_analysis"},
        headers=internal,
    )

    assert waiting.status_code == 200, waiting.text
    assert waiting.json()["status"] == "success"
    assert waiting.json()["ready"] is False
    assert waiting.json()["artifact_pending"] is True
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        assert run.params_json["submission_phase"] == "preparing_analysis"

    final_sampleinfo = tmp_path / "results" / batch_name / "sampleinfo.tsv"
    final_sampleinfo.parent.mkdir(parents=True)
    final_sampleinfo.write_text(
        "样本编号\t数据编号\t家系编号\t家系关系\t样本类型\t性别\t上机批次\n"
        "SAMPLE-1\tDATA-1\tFAMILY-1\t先证者\t外周血\t男\t20260825A\n",
        encoding="utf-8",
    )

    ready = client.get(
        f"/api/internal/wgs/runs/{analysis_id}/stage-status",
        params={"attempt": 1, "stage": "prepare_analysis"},
        headers=internal,
    )

    assert ready.status_code == 200, ready.text
    assert ready.json()["ready"] is True
    assert ready.json()["artifact_pending"] is False
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        assert run.params_json["submission_phase"] == "execution_review"
        samples = list(
            session.scalars(
                select(Sample).where(Sample.analysis_id == analysis_id)
            )
        )
        assert [item.sample_id for item in samples] == ["SAMPLE-1"]


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


def test_run_detail_does_not_show_observer_from_an_older_attempt(
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
            "batch_no": "BATCH-OBSERVER-RETRY",
            "fq_path": str(tmp_path),
        },
    ).json()
    analysis_id = created["analysis_id"]
    with sessions() as session:
        run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.analysis_id == analysis_id)
        )
        session.add(
            ObserverRunState(
                analysis_id=analysis_id,
                attempt=1,
                pipeline_release_id=run.params_json["pipeline_release_id"],
                run_label="cce-run-0123456789abcdef",
                relative_evidence_path=f"{analysis_id}/attempt-1",
                lifecycle_status="stopped",
                monitoring_health="degraded",
                last_error="old attempt evidence error",
            )
        )
        run.attempt = 2
        session.add(
            RunAttempt(
                analysis_id=analysis_id,
                attempt=2,
                execution_mode="cce",
                status="created",
            )
        )
        session.commit()

    detail = client.get(f"/api/runs/{analysis_id}", headers=headers)

    assert detail.status_code == 200, detail.text
    assert detail.json()["observer"] is None


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
        session.add(RuleState(analysis_id=run.analysis_id, attempt=1, rule_instance_id="late", rule_name="QCall", phase="QC", sequence=20, family_id="F2", status="running"))
        session.add(RuleState(analysis_id=run.analysis_id, attempt=1, rule_instance_id="early", rule_name="mapping", phase="Pre-calling", sequence=2, sample_id="W1", family_id="F1", status="success"))
        session.add(KubernetesWorkload(analysis_id=run.analysis_id, attempt=1, event_id="step3:wgs-master-0123456789abcdef0123", pod_hash="abc", job_name="wgs-master-0123456789abcdef0123", phase="Failed", reason="OOMKilled", exit_code=137, node_name="node-1", message="master failed", resources_json={"memory": "1Gi"}))
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
    assert [item["rule"] for item in rules.json()["items"]] == ["mapping", "QCall"]
    assert rules.json()["items"][0]["phase_order"] == 10
    assert rules.json()["items"][0]["family_id"] == "F1"
    assert [item["key"] for item in rules.json()["phases"]] == ["pre_calling", "variant_analysis", "qc", "cloud_delivery"]
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


def test_wgs_sample_projection_excludes_clinical_fields_and_server_paths(tmp_path, monkeypatch):
    client, sessions, _ = make_client(tmp_path, monkeypatch)
    headers = login(client, "viewer", "viewer-pass")
    analysis_id = "WGS_SAFE_SAMPLES"
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id=analysis_id,
                pipeline_name="wgs",
                dag_id="bio_wgs",
                execution_mode="cce",
                workdir=str(tmp_path / analysis_id),
                status="running",
                params_json={"batch_no": "WGS_20260901A_T7Hg38V4.1.1"},
            )
        )
        session.add(
            Sample(
                analysis_id=analysis_id,
                sample_id="WGS001",
                family_id="F001",
                sample_type="blood",
                sex="female",
                fq1="/private/fastq/WGS001-WGS.R1.fq.gz",
                fq2="/private/fastq/WGS001-WGS.R2.fq.gz",
                status="running",
                metadata_json={
                    "data_id": "D001",
                    "family_relation": "proband",
                    "sequencing_batch": "20260901A",
                    "pending_source": "historical_pending",
                    "pending_reason": "previously deferred",
                    "name": "private name",
                    "birth_date": "2000-01-01",
                    "hospital": "private hospital",
                    "doctor": "private doctor",
                    "clinical_complaint": "private complaint",
                    "keywords": "private keywords",
                },
            )
        )
        session.commit()

    response = client.get(f"/api/runs/{analysis_id}/samples", headers=headers)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item == {
        "sample_id": "WGS001",
        "data_id": "D001",
        "family_id": "F001",
        "family_relation": "proband",
        "current_stage": None,
        "current_rule": None,
        "completed_rules": 0,
        "total_rules": 0,
        "progress_percent": None,
        "status": "running",
        "elapsed_seconds": None,
        "qc_status": "unknown",
        "qc_metrics": {},
    }
    assert response.json()["manifest"] == []
    assert "/private/fastq" not in response.text
    assert "private name" not in response.text
