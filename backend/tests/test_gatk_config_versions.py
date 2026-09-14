from pathlib import Path

import pytest

from app.gatk_submission_service import _source_paths


def make_project(tmp_path, version):
    source = tmp_path / f"WES_20260911A_T7_V{version}_hg38"
    source.mkdir()
    (source / "WES_20260911A_T7.sampleinfo.txt").write_text("synthetic")
    (source / "sample2hospitalBarCode.txt").write_text("synthetic")
    return source


@pytest.mark.parametrize("version", ["7.6.0", "7.6.1", "7.6.99", "7.7.0", "7.7.99"])
def test_config_matches_project_version(tmp_path, version):
    source = make_project(tmp_path, version)
    config = source / f"config.V{version}_hg38.yaml"
    config.write_text("{}")
    assert _source_paths(source)[1] == config


def test_does_not_fallback_to_other_version(tmp_path):
    source = make_project(tmp_path, "7.7.1")
    (source / "config.V7.6.0_hg38.yaml").write_text("{}")
    with pytest.raises(ValueError):
        _source_paths(source)


@pytest.mark.parametrize("version", ["7.5.0", "7.8.0", "8.0.0"])
def test_unsupported_versions_rejected(tmp_path, version):
    source = make_project(tmp_path, version)
    (source / "config.V7.6.0_hg38.yaml").write_text("{}")
    with pytest.raises(ValueError):
        _source_paths(source)


def test_config_symlink_rejected(tmp_path):
    source = make_project(tmp_path, "7.7.1")
    outside = tmp_path / "outside.yaml"
    outside.write_text("{}")
    (source / "config.V7.7.1_hg38.yaml").symlink_to(outside)
    with pytest.raises(ValueError):
        _source_paths(source)


@pytest.mark.parametrize("name", ["WES_20260911A_T7_hg38.sampleinfo.txt", "WES_20260911A_T7.sampleinfo.SCMC.txt"])
def test_runtime_sampleinfo_names(tmp_path, name):
    source = make_project(tmp_path, "7.7.1")
    (source / "WES_20260911A_T7.sampleinfo.txt").unlink()
    (source / name).write_text("synthetic")
    (source / "config.V7.7.1_hg38.yaml").write_text("{}")
    assert _source_paths(source)[0].name == name
