"""Configuration-only publication keeps historical source and receipt identities."""
import hashlib
import json

import pytest
import yaml

from app.wgs_release_catalog import parse_wgs_release, load_wgs_release_catalog
from app.wgs_release_management import WgsReleaseRegistration, register_wgs_release
from app.wgs_runtime_adapter import build_stage_request


def release(release_id="wgs-4.2.2-aaaaaaa"):
    return dict(release_id=release_id, version="V4.2.2", source_commit="a" * 40,
        bs10610_repo_path="/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.2",
        node200_repo_path="/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.2",
        rule_event_schema_version="1", profile_id="wgs-4.2.2", profile_revision="r3",
        profile_sha256="b" * 64, cce_pipeline_version="0.8.7",
        node200_profile_path="/bi/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs/r3.yaml",
        pipeline_build_sha256="c" * 64, resource_manifest_sha256="d" * 64)


def test_config_revision_registers_without_replacing_historical_release(tmp_path):
    old = release()
    new = release("wgs-4.2.2-aaaaaaa-permissions")
    new["profile_sha256"] = "e" * 64
    path = tmp_path / "catalog.yaml"
    path.write_text(yaml.safe_dump(dict(schema_version="4", current_release_id=old["release_id"], releases=[old])))
    assets = {k: new[k] for k in ("profile_id", "profile_revision", "profile_sha256", "source_commit", "pipeline_build_sha256", "resource_manifest_sha256")}
    assets.update(release_id="synthetic-permissions", asset_manifest_sha256="f" * 64, status="PASS", state_verified=True)
    receipt = dict(schema_version="cce-release.v1", release=new, assets=assets)
    receipt["receipt_sha256"] = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    register_wgs_release(path, WgsReleaseRegistration.model_validate(receipt))
    catalog = load_wgs_release_catalog(path)
    assert catalog.release.release_id == old["release_id"]
    assert catalog.by_id(old["release_id"]).profile_sha256 == "b" * 64
    assert catalog.by_id(new["release_id"]).profile_sha256 == "e" * 64


@pytest.mark.parametrize("suffix", ["", "-permissions"])
def test_runtime_accepts_legacy_and_config_revision_identity(suffix):
    identity = "wgs-4.2.2-aaaaaaa" + suffix
    request = build_stage_request(analysis_id="WGS_20260927_010203_A1B2C3", attempt=1,
        stage="prepare_analysis", pipeline_release_id=identity, wgs_version="V4.2.2",
        wgs_source_commit="a" * 40, control_runtime_root="/synthetic/runtime",
        analysis_project_root="/synthetic/projects", project_name="WGS_Clinical",
        batch_no="SYNTHETIC", fq_path="/synthetic/fastq")
    assert request["pipeline_release_id"] == identity
    assert parse_wgs_release(release(identity)).source_commit == "a" * 40


@pytest.mark.parametrize("identity", ["wgs-4.2.2-bbbbbbb-permissions", "wgs-4.2.2-aaaaaaa-../other", "wgs-4.2.2-aaaaaaa-", "wgs-4.2.2-aaaaaaa-" + "x" * 65])
def test_config_revision_rejects_wrong_source_or_unsafe_identity(identity):
    with pytest.raises(ValueError):
        parse_wgs_release(release(identity))
