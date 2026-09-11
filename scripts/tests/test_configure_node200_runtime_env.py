import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_configurator():
    spec = importlib.util.spec_from_file_location(
        "configure_node200_runtime_env_test",
        ROOT / "configure_node200_runtime_env.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runtime_env_update_is_atomic_and_preserves_execution_gates(tmp_path: Path) -> None:
    configurator = load_configurator()
    target = tmp_path / "runtime.env"
    target.write_text(
        "WGS_EXECUTION_ENABLED=false\n"
        "WGS_AUTO_DISPATCH_ENABLED=false\n"
        "WGS_REPO_ROOT=/old/wgs\n"
        "WGS_RELEASE_ROOTS_JSON={broken}\n",
        encoding="utf-8",
    )

    configurator.update_runtime_env(target)

    values = {}
    for line in target.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    assert values["WGS_EXECUTION_ENABLED"] == "false"
    assert values["WGS_AUTO_DISPATCH_ENABLED"] == "false"
    assert values["WGS_ANALYSIS_PROJECT_NODE200_ROOT"] == (
        "/sg2/50.ctapa/project/HWcloud/WGS_Clinical"
    )
    assert values["WGS_PYTHON"].endswith("/envs/nipttest/bin/python")
    assert values["CCE_PIPELINE_BIN"].endswith("/envs/nipttest/bin/cce-pipeline")
    assert values["WGS_TRANSFER_ADAPTER"] == "obsutil"
    release_roots = json.loads(values["WGS_RELEASE_ROOTS_JSON"].strip("'"))
    assert release_roots["wgs-4.2.0-b067c72"].endswith("/wgs-4.2.0")
    assert release_roots["wgs-4.1.1-1656b5d"].endswith("/wgs-4.1.1")
