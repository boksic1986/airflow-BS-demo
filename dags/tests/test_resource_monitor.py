import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.resource_monitor import ResourceMonitor


def test_resource_monitor_writes_samples_and_summary(tmp_path) -> None:
    process = subprocess.Popen([sys.executable, "-c", "import time; data=bytearray(2_000_000); time.sleep(0.3)"])
    monitor = ResourceMonitor(
        root_pid=process.pid,
        samples_path=tmp_path / "resource_samples.jsonl",
        summary_path=tmp_path / "resource_summary.json",
        interval_seconds=0.05,
    )
    monitor.start()
    process.wait(timeout=5)
    time.sleep(0.06)
    summary = monitor.stop(return_code=process.returncode)

    assert summary["sample_count"] >= 1
    assert summary["peak_rss_bytes"] > 0
    assert summary["peak_pss_bytes"] is None or summary["peak_pss_bytes"] > 0
    assert summary["complete"] is True
    samples = [json.loads(line) for line in (tmp_path / "resource_samples.jsonl").read_text(encoding="utf-8").splitlines()]
    assert samples
    assert (tmp_path / "resource_summary.json").is_file()
