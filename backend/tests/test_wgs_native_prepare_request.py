import pytest

from app.wgs_runtime_adapter import build_stage_request


def request(frozen):
    return build_stage_request(
        analysis_id="WGS_20260915_010203_A1B2C3", attempt=1, stage="prepare_analysis",
        pipeline_release_id="wgs-4.2.1-cc9bde3", wgs_version="V4.2.1",
        wgs_source_commit="c" * 40,
        control_runtime_root="/synthetic/runtime", analysis_project_root="/synthetic/project",
        project_name="SYNTHETIC", batch_no="20260915A", fq_path="/synthetic/fastq",
        prepare_execution=frozen,
        profile_id="wgs-4.2.1", profile_revision="r1", profile_sha256="a" * 64,
        node200_profile_path="/synthetic/profile.yaml", cce_pipeline_version="0.8.4",
        pipeline_build_sha256="b" * 64, resource_manifest_sha256="d" * 64,
    )


@pytest.mark.parametrize("mode,target", [("cce", "cce"), ("local", "node-96"), ("sge", "sge-default")])
def test_frozen_native_request_preserves_choice_without_cloud_runtime_requirements(mode, target):
    frozen = {"attempt": 1, "mode": mode, "target": target, "revision": 2}
    payload = request(frozen)
    assert payload["prepare_execution"] == frozen
    assert ("cce_pipeline_version" in payload) == (mode == "cce")
    assert ("node200_profile_path" in payload) == (mode == "cce")
    frozen["target"] = "changed-after-request"
    assert payload["prepare_execution"]["target"] == target


def test_prepare_request_rejects_frozen_choice_from_another_attempt():
    with pytest.raises(ValueError, match="execution"):
        request({"attempt": 2, "mode": "local", "target": "node-96", "revision": 2})
