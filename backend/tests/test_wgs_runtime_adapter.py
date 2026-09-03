from pathlib import Path
import stat

import pytest

from app.wgs_runtime_adapter import (
    build_stage_request,
    container_workdir_to_host,
    write_stage_request,
)


RELEASE_ID = "wgs-4.1.1-1656b5d"
WGS_COMMIT = "1656b5d7a6e2f24242c38149f6d1c92ac266cd37"


def _request(tmp_path: Path, *, stage: str = "step2_master") -> dict[str, object]:
    return build_stage_request(
        analysis_id="WGS_20260826_010203_A1B2C3",
        attempt=1,
        stage=stage,
        pipeline_release_id=RELEASE_ID,
        wgs_version="V4.1.1",
        wgs_source_commit=WGS_COMMIT,
        control_runtime_root="/sg2/14.hanjingjing/Cloud_WGS_Clinical/airflow-wgs/runtime",
        analysis_project_root="/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical",
        project_name="clinical-wgs",
        batch_no="BATCH-01",
        fq_path="/sg2/33.chenjiucheng/WGS_input/BATCH-01",
        sequencing_batch="20260902A",
        analysis_batch="20260902A",
        maintenance_action_id="step7-sfs-abcdef123456" if stage == "step7_cleanup" else None,
    )


def test_stage_request_v4_separates_control_and_analysis_roots(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path)

    assert request["schema_version"] == "wgs-runtime.request.v4"
    assert request["pipeline_release_id"] == RELEASE_ID
    assert request["wgs_version"] == "V4.1.1"
    assert request["wgs_source_commit"] == WGS_COMMIT
    assert request["analysis_batch"] == "20260902A"
    assert request["control_workdir"].endswith(
        "/runtime/runs/WGS_20260826_010203_A1B2C3/attempt-1"
    )
    assert request["analysis_project_root"] == "/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical"
    assert request["expected_batch_root"] == (
        "/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/BATCH-01"
    )
    assert "node200_workdir" not in request
    assert "bs10610_workdir" not in request
    assert "pipeline_snapshot_id" not in request
    assert "pipeline_snapshot_path" not in request
    assert "node200_pipeline_snapshot_path" not in request
    assert "cce_pipeline_version" not in request
    assert "cce_pipeline_wheel_sha256" not in request


@pytest.mark.parametrize(
    "stage",
    [
        "prepare",
        "step1_upload",
        "step2_master",
        "step3_monitor",
        "step4_publish",
        "step4_repair_cram",
        "step5_download",
        "step6_materialize",
        "step7_cleanup",
    ],
)
def test_request_accepts_only_wgs_step1_to_step6_stages(
    tmp_path: Path, stage: str
) -> None:
    assert _request(tmp_path, stage=stage)["stage"] == stage


def test_request_rejects_old_or_manual_stages(tmp_path: Path) -> None:
    for stage in ("validate_cce_bundle", "step0_reset", "step4_repair_vcf", "step8_cleanup"):
        with pytest.raises(ValueError, match="stage"):
            _request(tmp_path, stage=stage)


def test_step7_request_requires_admin_maintenance_action_identity(tmp_path: Path) -> None:
    request = _request(tmp_path, stage="step7_cleanup")
    assert request["maintenance_action_id"] == "step7-sfs-abcdef123456"
    with pytest.raises(ValueError, match="maintenance_action_id"):
        build_stage_request(
            analysis_id="WGS_20260826_010203_A1B2C3",
            attempt=1,
            stage="step7_cleanup",
            pipeline_release_id=RELEASE_ID,
            wgs_version="V4.1.1",
            wgs_source_commit=WGS_COMMIT,
            control_runtime_root="/sg2/runtime",
            analysis_project_root="/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical",
            project_name="clinical-wgs",
            batch_no="BATCH-01",
            fq_path="/sg2/input/BATCH-01",
        )


def test_request_is_atomically_registered_below_request_root(tmp_path: Path) -> None:
    request = _request(tmp_path, stage="step1_upload")
    path = write_stage_request(tmp_path / "requests", request)

    assert path == (
        tmp_path
        / "requests"
        / "WGS_20260826_010203_A1B2C3"
        / "attempt-1"
        / "step1_upload.json"
    )
    assert not path.with_suffix(".json.partial").exists()


def test_request_directory_is_writable_by_node200_shared_group(tmp_path: Path) -> None:
    request = _request(tmp_path, stage="prepare")
    shared_gid = 520
    path = write_stage_request(
        tmp_path / "requests",
        request,
        shared_gid=shared_gid,
    )

    assert path.parent.stat().st_gid == shared_gid
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o2770


def test_request_rejects_invalid_shared_group(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="group id"):
        write_stage_request(
            tmp_path / "requests",
            _request(tmp_path, stage="prepare"),
            shared_gid=0,
        )


def test_container_path_maps_only_below_approved_root() -> None:
    assert container_workdir_to_host(
        "/data/wgs-intake/BATCH-01",
        container_root="/data/wgs-intake",
        host_root="/mnt/biodevrwsg2/33.chenjiucheng/WGS_input",
    ) == "/mnt/biodevrwsg2/33.chenjiucheng/WGS_input/BATCH-01"

    with pytest.raises(ValueError, match="outside"):
        container_workdir_to_host(
            "/data/other/BATCH-01",
            container_root="/data/wgs-intake",
            host_root="/mnt/biodevrwsg2/33.chenjiucheng/WGS_input",
        )
