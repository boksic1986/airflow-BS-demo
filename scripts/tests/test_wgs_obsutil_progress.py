from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).parents[1] / "wgs_obsutil_progress.py"


def test_node200_wrapper_uses_supported_wgs_python() -> None:
    assert SCRIPT.read_text(encoding="utf-8").splitlines()[0] == (
        "#!/bi/software/mamba/envs/WGS/bin/python3.11"
    )


def test_wrapper_preserves_output_and_writes_redacted_progress(tmp_path: Path) -> None:
    fake = tmp_path / "fake_obsutil.py"
    fake.write_text(
        "import sys, time\n"
        "sys.stdout.write('25.00% 10.00MB/s 25MB/100MB 7s\\r')\n"
        "sys.stdout.flush(); time.sleep(.05)\n"
        "sys.stdout.write('100.00% 20.00MB/s 100MB/100MB 0s\\n')\n",
        encoding="utf-8",
    )
    progress = tmp_path / "progress"
    env = {
        **os.environ,
        "WGS_REAL_OBSUTIL_BIN": sys.executable,
        "WGS_TRANSFER_PROGRESS_ROOT": str(progress),
        "WGS_TRANSFER_ANALYSIS_ID": "WGS_20260902_120000_A1B2C3",
        "WGS_TRANSFER_ATTEMPT": "1",
        "WGS_TRANSFER_STAGE": "step1_upload",
        "WGS_TRANSFER_DIRECTION": "upload",
    }
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(fake), "cp", "/secret/patient.fastq.gz", "obs://secret/prefix"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "25.00%" in completed.stdout
    payloads = [json.loads(path.read_text()) for path in progress.glob("*.json")]
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["schema_version"] == "wgs-runtime.transfer-progress.v1"
    assert payload["state"] == "success"
    assert payload["bytes_done"] == payload["bytes_total"] == 100 * 1024 * 1024
    serialized = json.dumps(payload)
    assert "patient.fastq.gz" not in serialized
    assert "obs://" not in serialized
    assert "/secret" not in serialized
