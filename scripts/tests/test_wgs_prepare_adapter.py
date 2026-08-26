import importlib.util
import json
from pathlib import Path

import pytest


def load_module():
    path = Path(__file__).parents[1] / "wgs_prepare_adapter.py"
    spec = importlib.util.spec_from_file_location("wgs_prepare_adapter", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_validate_sampleinfo_requires_exact_snapshot_samples(tmp_path: Path) -> None:
    module = load_module()
    manifest = tmp_path / "input-manifest.json"
    manifest.write_text(json.dumps({"files": [
        {"sample_id": "S1", "read": "R1"}, {"sample_id": "S1", "read": "R2"},
        {"sample_id": "S2", "read": "R1"}, {"sample_id": "S2", "read": "R2"},
    ]}), encoding="utf-8")
    sampleinfo = tmp_path / "sampleinfo.tsv"
    sampleinfo.write_text("样本编号\t家系编号\nS1\tF1\nS2\tF1\n", encoding="utf-8")
    summary = module.validate_sampleinfo(manifest, sampleinfo, tmp_path / "summary.json")
    assert summary == {"sample_ids": ["S1", "S2"], "family_ids": ["F1"]}

    sampleinfo.write_text("样本编号\t家系编号\nS1\tF1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sample set"):
        module.validate_sampleinfo(manifest, sampleinfo, tmp_path / "summary.json")


def test_prepare_adapter_invokes_candidate_cce_mode_without_upstream_write() -> None:
    source = (Path(__file__).parents[1] / "wgs_prepare_adapter.py").read_text(encoding="utf-8")
    assert '"analysis"' in source
    assert '"--run-mode"' in source
    assert '"cce"' in source
    assert '"--run-id"' in source
    assert '"--fastq-root"' in source
    assert "FASTQ.MD5SUMS" not in source
    assert "--cce-fastq-md5-manifest" not in source
    assert "Step1_upload" not in source
    assert '"cce-bundle"' in source
    assert "WGS_PREPARE_CONFIG_PATH" in source
    assert "os.replace" in source
