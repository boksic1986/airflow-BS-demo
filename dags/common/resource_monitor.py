from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
from typing import Any


class ResourceMonitor:
    def __init__(
        self,
        *,
        root_pid: int,
        samples_path: Path,
        summary_path: Path,
        interval_seconds: float = 5.0,
        proc_root: Path = Path("/proc"),
        source: str = "procfs_process_tree",
    ) -> None:
        self.root_pid = int(root_pid)
        self.samples_path = Path(samples_path)
        self.summary_path = Path(summary_path)
        self.interval_seconds = max(0.02, float(interval_seconds))
        self.proc_root = Path(proc_root)
        self.source = str(source)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_monotonic: float | None = None
        self._samples: list[dict[str, Any]] = []
        self._last_io: dict[int, tuple[int, int]] = {}
        self._read_bytes = 0
        self._write_bytes = 0

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("ResourceMonitor has already started.")
        self.samples_path.parent.mkdir(parents=True, exist_ok=True)
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        self._started_monotonic = time.monotonic()
        self._thread = threading.Thread(target=self._run, name=f"resource-monitor-{self.root_pid}", daemon=True)
        self._thread.start()

    def stop(self, *, return_code: int | None = None) -> dict[str, Any]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(2.0, self.interval_seconds * 2))
        if not self._samples:
            self._record_sample()
        wall_seconds = max(0.0, time.monotonic() - (self._started_monotonic or time.monotonic()))
        pss_values = [item["pss_bytes"] for item in self._samples if item.get("pss_bytes") is not None]
        rss_values = [int(item.get("rss_bytes") or 0) for item in self._samples]
        cpu_values = [float(item.get("cpu_seconds") or 0.0) for item in self._samples]
        summary = {
            "root_pid": self.root_pid,
            "wall_seconds": round(wall_seconds, 3),
            "peak_pss_bytes": max(pss_values) if pss_values else None,
            "peak_rss_bytes": max(rss_values) if rss_values else 0,
            "read_bytes": self._read_bytes,
            "write_bytes": self._write_bytes,
            "cpu_seconds": round(max(cpu_values) if cpu_values else 0.0, 3),
            "sample_count": len(self._samples),
            "interval_seconds": self.interval_seconds,
            "return_code": return_code,
            "complete": return_code is not None,
            "source": self.source,
            "proc_root": str(self.proc_root),
            "samples_path": str(self.samples_path),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        self.summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary

    def _run(self) -> None:
        while not self._stop.is_set():
            self._record_sample()
            self._stop.wait(self.interval_seconds)

    def _record_sample(self) -> None:
        pids = _process_tree(self.root_pid, proc_root=self.proc_root)
        rss_bytes = 0
        pss_bytes = 0
        pss_available = False
        cpu_seconds = 0.0
        for pid in pids:
            metrics = _read_process_metrics(pid, proc_root=self.proc_root)
            if metrics is None:
                continue
            rss_bytes += int(metrics["rss_bytes"])
            if metrics["pss_bytes"] is not None:
                pss_bytes += int(metrics["pss_bytes"])
                pss_available = True
            cpu_seconds += float(metrics["cpu_seconds"])
            read_bytes = int(metrics["read_bytes"])
            write_bytes = int(metrics["write_bytes"])
            previous = self._last_io.get(pid)
            if previous is None:
                self._read_bytes += read_bytes
                self._write_bytes += write_bytes
            else:
                self._read_bytes += max(0, read_bytes - previous[0])
                self._write_bytes += max(0, write_bytes - previous[1])
            self._last_io[pid] = (read_bytes, write_bytes)
        sample = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "root_pid": self.root_pid,
            "process_count": len(pids),
            "rss_bytes": rss_bytes,
            "pss_bytes": pss_bytes if pss_available else None,
            "cpu_seconds": round(cpu_seconds, 3),
            "read_bytes": self._read_bytes,
            "write_bytes": self._write_bytes,
        }
        self._samples.append(sample)
        with self.samples_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sample, sort_keys=True) + "\n")


def _process_tree(root_pid: int, *, proc_root: Path = Path("/proc")) -> list[int]:
    proc = Path(proc_root)
    if not proc.is_dir():
        return []
    parents: dict[int, int] = {}
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8")
            tail = stat.rsplit(")", 1)[1].strip().split()
            parents[int(entry.name)] = int(tail[1])
        except (FileNotFoundError, IndexError, PermissionError, ValueError):
            continue
    selected = {int(root_pid)}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in selected and pid not in selected:
                selected.add(pid)
                changed = True
    return sorted(pid for pid in selected if pid in parents or (proc / str(pid)).exists())


def _read_process_metrics(pid: int, *, proc_root: Path = Path("/proc")) -> dict[str, int | float | None] | None:
    proc_dir = Path(proc_root) / str(pid)
    try:
        stat = (proc_dir / "stat").read_text(encoding="utf-8")
        tail = stat.rsplit(")", 1)[1].strip().split()
        ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        cpu_seconds = (int(tail[11]) + int(tail[12])) / ticks
        rss_bytes, pss_bytes = _read_smaps_rollup(proc_dir)
        read_bytes, write_bytes = _read_io(proc_dir)
        return {
            "rss_bytes": rss_bytes,
            "pss_bytes": pss_bytes,
            "cpu_seconds": cpu_seconds,
            "read_bytes": read_bytes,
            "write_bytes": write_bytes,
        }
    except (FileNotFoundError, IndexError, PermissionError, ProcessLookupError, ValueError):
        return None


def _read_smaps_rollup(proc_dir: Path) -> tuple[int, int | None]:
    rss_kib = 0
    pss_kib: int | None = None
    try:
        for line in (proc_dir / "smaps_rollup").read_text(encoding="utf-8").splitlines():
            if line.startswith("Rss:"):
                rss_kib = int(line.split()[1])
            elif line.startswith("Pss:"):
                pss_kib = int(line.split()[1])
    except (FileNotFoundError, PermissionError, ValueError):
        try:
            for line in (proc_dir / "status").read_text(encoding="utf-8").splitlines():
                if line.startswith("VmRSS:"):
                    rss_kib = int(line.split()[1])
                    break
        except (FileNotFoundError, PermissionError, ValueError):
            pass
    return rss_kib * 1024, pss_kib * 1024 if pss_kib is not None else None


def _read_io(proc_dir: Path) -> tuple[int, int]:
    values = {"read_bytes": 0, "write_bytes": 0}
    try:
        for line in (proc_dir / "io").read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition(":")
            if key in values:
                values[key] = int(value.strip())
    except (FileNotFoundError, PermissionError, ValueError):
        pass
    return values["read_bytes"], values["write_bytes"]
