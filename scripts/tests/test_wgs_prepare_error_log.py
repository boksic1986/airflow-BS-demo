import importlib.util
from pathlib import Path
import sys

import pytest


@pytest.mark.parametrize("exit_code", [0, 1])
def test_prepare_keeps_full_output_without_long_command_in_error(tmp_path, monkeypatch, exit_code):
    spec = importlib.util.spec_from_file_location(
        "prepare_log_gate", Path(__file__).parents[1] / "wgs_runtime_gate.py"
    )
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    command = [sys.executable, "-c",
               "import sys; print('prepare output', flush=True); "
               "sys.stderr.write('root error\\n' + 'x' * 5000); "
               f"sys.exit({exit_code})", "long-argument-" * 300]
    monkeypatch.setattr(gate, "build_prepare_command", lambda payload: command)
    monkeypatch.setattr(gate, "_workdir", lambda payload: tmp_path)
    payload = {"generation": 2}
    previous = tmp_path / "prepare_analysis.generation-1.log"
    previous.write_text("previous execution")
    if exit_code:
        with pytest.raises(RuntimeError) as error:
            gate._run_logged_prepare(payload)
        assert "exit code 1" in str(error.value)
        assert "prepare_analysis.generation-2.log" in str(error.value)
        assert "long-argument" not in str(error.value)
    else:
        gate._run_logged_prepare(payload)
    log = tmp_path / "prepare_analysis.generation-2.log"
    assert log.read_text() == "prepare output\nroot error\n" + "x" * 5000
    assert log.stat().st_mode & 0o777 == 0o600
    assert previous.read_text() == "previous execution"
