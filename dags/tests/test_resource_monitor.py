import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.resource_monitor import ResourceMonitor, _process_tree


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


def test_resource_monitor_can_read_an_explicit_proc_root(tmp_path) -> None:
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.2)"])
    monitor = ResourceMonitor(
        root_pid=process.pid,
        samples_path=tmp_path / "explicit-proc.jsonl",
        summary_path=tmp_path / "explicit-proc-summary.json",
        interval_seconds=0.05,
        proc_root=Path("/proc"),
        source="docker_container_host_procfs",
    )
    monitor.start()
    process.wait(timeout=5)
    summary = monitor.stop(return_code=process.returncode)

    assert summary["proc_root"] == "/proc"
    assert summary["source"] == "docker_container_host_procfs"
    assert summary["peak_rss_bytes"] > 0


def test_process_tree_ignores_process_that_exits_during_scan(tmp_path, monkeypatch) -> None:
    proc_root = tmp_path / "proc"
    root_stat = proc_root / "100" / "stat"
    child_stat = proc_root / "101" / "stat"
    root_stat.parent.mkdir(parents=True)
    child_stat.parent.mkdir(parents=True)
    root_stat.write_text("100 (root) S 0 0 0\n", encoding="utf-8")
    child_stat.write_text("101 (child) S 100 0 0\n", encoding="utf-8")
    original_read_text = Path.read_text

    def flaky_read_text(path: Path, *args, **kwargs):
        if path == child_stat:
            raise ProcessLookupError("process exited during procfs scan")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", flaky_read_text)

    assert _process_tree(100, proc_root=proc_root) == [100]
