from __future__ import annotations

from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
import stat
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
import yaml

from app import main
from app.wgs_platform_service import _refresh_recovery_release
from app.wgs_release_catalog import load_wgs_release_catalog


INTERNAL_HEADERS = {"X-Airflow-Demo-Token": "release-test-token"}
CURRENT_RELEASE_ID = "wgs-4.2.0-1111111"
MANAGED_RELEASE_ID = "wgs-4.2.1-aaaaaaa"
MANAGED_RECEIPT_SHA256 = (
    "1b3d60dd4984207db9b7f71683245ec4f6cc1207136a4626c86301e177956bd8"
)


def _write_schema3_catalog(tmp_path: Path) -> Path:
    path = tmp_path / "catalog" / "wgs_releases.yaml"
    path.parent.mkdir()
    path.write_text(
        """schema_version: "3"
deployment_note: retain-root-metadata
release:
  release_id: wgs-4.2.0-1111111
  version: V4.2.0
  source_commit: 1111111111111111111111111111111111111111
  bs10610_repo_path: /mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0
  node200_repo_path: /bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0
  rule_event_schema_version: "1"
  owner_metadata: retained-release-metadata
""",
        encoding="utf-8",
    )
    path.chmod(0o640)
    return path


def _managed_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "cce-release.v1",
        "release": {
            "release_id": MANAGED_RELEASE_ID,
            "version": "V4.2.1",
            "source_commit": "a" * 40,
            "bs10610_repo_path": "/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.1",
            "node200_repo_path": "/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.1",
            "rule_event_schema_version": "1",
            "profile_id": "wgs-4.2.1",
            "profile_revision": "r2",
            "profile_sha256": "b" * 64,
            "cce_pipeline_version": "0.8.5",
            "node200_profile_path": "/bi/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs/wgs-4.2.1-r2.yaml",
            "pipeline_build_sha256": "c" * 64,
            "resource_manifest_sha256": "d" * 64,
        },
        "assets": {
            "release_id": "synthetic-cce-085",
            "asset_manifest_sha256": "e" * 64,
            "profile_id": "wgs-4.2.1",
            "profile_revision": "r2",
            "profile_sha256": "b" * 64,
            "source_commit": "a" * 40,
            "pipeline_build_sha256": "c" * 64,
            "resource_manifest_sha256": "d" * 64,
            "status": "PASS",
            "state_verified": True,
        },
    }
    payload["receipt_sha256"] = _receipt_sha256(payload)
    return payload


def _receipt_sha256(payload: dict[str, object]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    encoded = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _make_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: bool = True,
    auth_required: bool = True,
) -> tuple[TestClient, SimpleNamespace, dict[str, main.AuthenticatedUser]]:
    catalog = _write_schema3_catalog(tmp_path)
    settings = SimpleNamespace(
        auth_required=auth_required,
        internal_service_token="release-test-token",
        wgs_release_management_enabled=enabled,
        wgs_release_catalog_path=str(catalog),
    )
    actor = {
        "user": main.AuthenticatedUser(1, "release-admin", "admin", "csrf-token")
    }
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "get_sessionmaker", lambda: lambda: nullcontext(None))
    monkeypatch.setattr(
        main, "authenticate_session", lambda **_kwargs: actor["user"]
    )
    return TestClient(main.app), settings, actor


def _register(client: TestClient, payload: dict[str, object] | None = None):
    return client.post(
        "/api/wgs/releases",
        headers=INTERNAL_HEADERS,
        json=payload or _managed_payload(),
    )


def _activate(client: TestClient):
    return client.post(
        f"/api/wgs/releases/{MANAGED_RELEASE_ID}/activate",
        headers=INTERNAL_HEADERS,
        json={
            "receipt_sha256": MANAGED_RECEIPT_SHA256,
            "expected_current_release_id": CURRENT_RELEASE_ID,
        },
    )


def test_release_writes_require_enabled_authenticated_admin_and_csrf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, settings, actor = _make_client(tmp_path, monkeypatch, enabled=False)
    payload = _managed_payload()

    disabled = _register(client, payload)
    assert disabled.status_code == 409
    assert disabled.json()["detail"]["code"] == "WGS_RELEASE_MANAGEMENT_DISABLED"

    settings.wgs_release_management_enabled = True
    settings.auth_required = False
    unauthenticated_mode = _register(client, payload)
    assert unauthenticated_mode.status_code == 409
    assert unauthenticated_mode.json()["detail"]["code"] == (
        "WGS_RELEASE_MANAGEMENT_REQUIRES_AUTH"
    )

    settings.auth_required = True
    missing_csrf = client.post("/api/wgs/releases", json=payload)
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["detail"]["code"] == "CSRF_REQUIRED"

    actor["user"] = main.AuthenticatedUser(2, "release-operator", "operator", "csrf-token")
    not_admin = client.post(
        "/api/wgs/releases", headers={"X-CSRF-Token": "csrf-token"}, json=payload
    )
    assert not_admin.status_code == 403


def test_registration_rejects_binding_and_receipt_mismatches_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, settings, _ = _make_client(tmp_path, monkeypatch)
    catalog_path = Path(settings.wgs_release_catalog_path)
    original = catalog_path.read_bytes()
    variants = []
    for field in (
        "profile_id",
        "profile_revision",
        "cce_pipeline_version",
        "node200_profile_path",
    ):
        empty_release_field = _managed_payload()
        empty_release_field["release"][field] = ""
        if field in {"profile_id", "profile_revision"}:
            empty_release_field["assets"][field] = ""
        empty_release_field["receipt_sha256"] = _receipt_sha256(
            empty_release_field
        )
        variants.append(empty_release_field)
    empty_asset_release_id = _managed_payload()
    empty_asset_release_id["assets"]["release_id"] = " "
    empty_asset_release_id["receipt_sha256"] = _receipt_sha256(
        empty_asset_release_id
    )
    variants.append(empty_asset_release_id)
    wrong_source = _managed_payload()
    wrong_source["assets"]["source_commit"] = "f" * 40
    wrong_source["receipt_sha256"] = _receipt_sha256(wrong_source)
    variants.append(wrong_source)
    wrong_profile = _managed_payload()
    wrong_profile["assets"]["profile_sha256"] = "f" * 64
    wrong_profile["receipt_sha256"] = _receipt_sha256(wrong_profile)
    variants.append(wrong_profile)
    wrong_digest = _managed_payload()
    wrong_digest["receipt_sha256"] = "0" * 64
    variants.append(wrong_digest)

    for payload in variants:
        response = _register(client, payload)
        assert response.status_code == 422, response.text
    assert catalog_path.read_bytes() == original


def test_registration_upgrades_legacy_catalog_without_activation_or_metadata_loss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, settings, _ = _make_client(tmp_path, monkeypatch)
    catalog_path = Path(settings.wgs_release_catalog_path)
    assert _managed_payload()["receipt_sha256"] == MANAGED_RECEIPT_SHA256

    registered = _register(client)

    assert registered.status_code == 200, registered.text
    assert registered.json() == {
        "status": "registered",
        "release_id": MANAGED_RELEASE_ID,
        "receipt_sha256": MANAGED_RECEIPT_SHA256,
        "active": False,
        "replayed": False,
    }
    raw = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == "4"
    assert raw["current_release_id"] == CURRENT_RELEASE_ID
    assert raw["deployment_note"] == "retain-root-metadata"
    assert raw["releases"][0]["owner_metadata"] == "retained-release-metadata"
    assert stat.S_IMODE(catalog_path.stat().st_mode) == 0o640
    catalog = load_wgs_release_catalog(catalog_path)
    assert catalog.release.release_id == CURRENT_RELEASE_ID
    assert catalog.by_id(MANAGED_RELEASE_ID).profile_sha256 == "b" * 64

    listing = client.get("/api/wgs/releases", headers=INTERNAL_HEADERS)
    assert listing.status_code == 200, listing.text
    assert listing.json()["current"]["release_id"] == CURRENT_RELEASE_ID
    assert [row["release_id"] for row in listing.json()["candidates"]] == [
        MANAGED_RELEASE_ID
    ]
    assert listing.json()["candidates"][0]["receipt_sha256"] == (
        MANAGED_RECEIPT_SHA256
    )


def test_registration_is_idempotent_but_same_id_changed_receipt_conflicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _, _ = _make_client(tmp_path, monkeypatch)
    assert _register(client).status_code == 200

    replay = _register(client)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True

    changed = _managed_payload()
    changed["assets"]["asset_manifest_sha256"] = "f" * 64
    changed["receipt_sha256"] = _receipt_sha256(changed)
    conflict = _register(client, changed)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "WGS_RELEASE_CONFLICT"


def test_activation_requires_registered_receipt_and_current_compare_and_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, settings, _ = _make_client(tmp_path, monkeypatch)
    assert _register(client).status_code == 200
    wrong_current = client.post(
        f"/api/wgs/releases/{MANAGED_RELEASE_ID}/activate",
        headers=INTERNAL_HEADERS,
        json={
            "receipt_sha256": MANAGED_RECEIPT_SHA256,
            "expected_current_release_id": "wgs-4.1.1-2222222",
        },
    )
    assert wrong_current.status_code == 409
    assert wrong_current.json()["detail"]["code"] == "WGS_RELEASE_ACTIVATION_CONFLICT"
    wrong_receipt = client.post(
        f"/api/wgs/releases/{MANAGED_RELEASE_ID}/activate",
        headers=INTERNAL_HEADERS,
        json={
            "receipt_sha256": "0" * 64,
            "expected_current_release_id": CURRENT_RELEASE_ID,
        },
    )
    assert wrong_receipt.status_code == 409

    activated = _activate(client)

    assert activated.status_code == 200, activated.text
    assert activated.json()["previous_current_release_id"] == CURRENT_RELEASE_ID
    assert activated.json()["current_release_id"] == MANAGED_RELEASE_ID
    catalog = load_wgs_release_catalog(settings.wgs_release_catalog_path)
    assert catalog.release.release_id == MANAGED_RELEASE_ID
    assert catalog.by_id(CURRENT_RELEASE_ID).version == "V4.2.0"


def test_cce_recovery_keeps_recorded_release_params_after_new_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, settings, _ = _make_client(tmp_path, monkeypatch)
    assert _register(client).status_code == 200
    assert _activate(client).status_code == 200
    original = {
        "pipeline_release_id": CURRENT_RELEASE_ID,
        "wgs_version": "V4.2.0",
        "profile_id": "wgs-4.2.0",
        "profile_sha256": "9" * 64,
        "resolved_runtime": {"master": "frozen"},
    }
    run = SimpleNamespace(execution_mode="cce", params_json=deepcopy(original))

    assert _refresh_recovery_release(run=run, settings=settings) == {}
    assert run.params_json == original


def test_cce_missing_or_unknown_recorded_release_fails_closed_and_local_still_refreshes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, settings, _ = _make_client(tmp_path, monkeypatch)
    assert _register(client).status_code == 200
    assert _activate(client).status_code == 200

    for release_id in (None, "wgs-4.2.0-2222222"):
        params = {"wgs_version": "V4.2.0"}
        if release_id is not None:
            params["pipeline_release_id"] = release_id
        run = SimpleNamespace(execution_mode="cce", params_json=params)
        with pytest.raises(ValueError, match="recorded pipeline release"):
            _refresh_recovery_release(run=run, settings=settings)

    local = SimpleNamespace(
        execution_mode="local",
        params_json={
            "pipeline_release_id": CURRENT_RELEASE_ID,
            "wgs_version": "V4.2.1",
            "profile_id": "old-profile",
        },
    )
    audit = _refresh_recovery_release(run=local, settings=settings)
    assert audit == {
        "previous_release_id": CURRENT_RELEASE_ID,
        "pipeline_release_id": MANAGED_RELEASE_ID,
    }
    assert local.params_json["profile_id"] == "wgs-4.2.1"
