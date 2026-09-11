from pathlib import Path

import pytest
import yaml

from test_wgs_runtime_gate import load_gate


@pytest.fixture
def frozen_config(tmp_path, monkeypatch):
    gate = load_gate()
    root = tmp_path / "runs"
    work = root / "analysis" / "attempt-5"
    work.mkdir(parents=True)
    config = tmp_path / "operator.yaml"
    config.write_text(yaml.safe_dump({
        "paths": {"repository_root": "/old", "sfs_root": "/approved/sfs"},
        "kubernetes": {"namespace": "approved"},
        "obs": {"endpoint": "private.example", "sdk_attach_crc64": True},
    }))
    monkeypatch.setattr(gate, "CCE_OPERATOR_CONFIG", str(config))
    monkeypatch.setattr(gate, "RUNTIME_RUN_ROOT", str(root))
    monkeypatch.setattr(gate, "WGS_REPO_ROOT", tmp_path / "release")
    payload = {"analysis_id": "analysis", "attempt": 5, "control_workdir": str(work)}
    frozen = gate._release_operator_config(payload, materialize=True)
    bundle = tmp_path / "cce"
    bundle.mkdir()
    pointer = bundle / "CCE_OPERATOR_CONFIG_PATH"
    pointer.write_text(str(frozen))
    return gate, payload, {"cce_bundle": str(bundle)}, frozen, pointer


def test_step7_accepts_unchanged_current_attempt_frozen_config(frozen_config):
    gate, payload, binding, frozen, _ = frozen_config
    before = frozen.read_bytes()
    assert gate._step7_compat_operator_config(payload, binding) is None
    assert frozen.read_bytes() == before


@pytest.mark.parametrize("change", ["namespace", "sfs_root", "other_attempt", "symlink", "missing"])
def test_step7_rejects_unapproved_frozen_config(frozen_config, change):
    gate, payload, binding, frozen, pointer = frozen_config
    if change in ("namespace", "sfs_root"):
        config = yaml.safe_load(frozen.read_text())
        if change == "namespace":
            config["kubernetes"]["namespace"] = "other"
        else:
            config["paths"]["sfs_root"] = "/other/sfs"
        frozen.write_text(yaml.safe_dump(config))
    elif change == "other_attempt":
        other = frozen.parents[2] / "attempt-4" / "release-runtime" / "cce-operator.yaml"
        other.parent.mkdir(parents=True)
        other.write_bytes(frozen.read_bytes())
        pointer.write_text(str(other))
    elif change == "symlink":
        other = frozen.with_suffix(".original")
        frozen.rename(other)
        frozen.symlink_to(other)
    else:
        frozen.unlink()
    with pytest.raises(RuntimeError, match="not approved|changed"):
        gate._step7_compat_operator_config(payload, binding)
