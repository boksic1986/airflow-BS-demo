#!/usr/bin/env python3
"""Transparent obsutil wrapper with redacted, request-scoped progress evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading


SCHEMA = "wgs-runtime.transfer-progress.v1"
PROGRESS_RE = re.compile(
    rb"(?P<pct>\d+(?:\.\d+)?)%\s+(?P<speed>\d+(?:\.\d+)?(?:B|KB|MB|GB|TB)/s)\s+"
    rb"(?P<done>\d+(?:\.\d+)?(?:B|KB|MB|GB|TB))/(?P<total>\d+(?:\.\d+)?(?:B|KB|MB|GB|TB))"
)
UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}


def _bytes(value: bytes) -> int:
    text = value.decode("ascii").upper()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(B|KB|MB|GB|TB)", text)
    if match is None:
        raise ValueError("unsupported size")
    return int(float(match.group(1)) * UNITS[match.group(2)])


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".partial")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _identity(arguments: list[str]) -> str:
    # Hashing preserves restart identity without persisting source/OBS paths.
    return hashlib.sha256("\0".join(arguments).encode("utf-8", "surrogateescape")).hexdigest()[:24]


def main() -> int:
    real = os.environ.get("WGS_REAL_OBSUTIL_BIN", "").strip()
    root = os.environ.get("WGS_TRANSFER_PROGRESS_ROOT", "").strip()
    if not real:
        print("WGS_REAL_OBSUTIL_BIN is not configured", file=sys.stderr)
        return 127
    arguments = sys.argv[1:]
    if not arguments:
        return subprocess.call([real])
    progress_path = Path(root) / f"{_identity(arguments)}.json" if root else None
    state = {
        "schema_version": SCHEMA,
        "analysis_id": os.environ.get("WGS_TRANSFER_ANALYSIS_ID"),
        "attempt": int(os.environ.get("WGS_TRANSFER_ATTEMPT", "1")),
        "stage": os.environ.get("WGS_TRANSFER_STAGE"),
        "direction": os.environ.get("WGS_TRANSFER_DIRECTION"),
        "transfer_id": _identity(arguments),
        "state": "running",
        "bytes_total": 0,
        "bytes_done": 0,
        "files_total": 1,
        "files_done": 0,
        "current_file": None,
        "speed_bytes_per_second": 0,
        "eta_seconds": None,
        "heartbeat_at": datetime.now(timezone.utc).isoformat(),
        "monitoring_health": "healthy",
        "source": "obsutil-stream",
    }
    lock = threading.Lock()

    def publish() -> None:
        if progress_path is None:
            return
        try:
            _atomic_json(progress_path, dict(state))
        except OSError:
            state["monitoring_health"] = "degraded"

    publish()
    process = subprocess.Popen([real, *arguments], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def pump(source, destination) -> None:
        buffer = b""
        while True:
            chunk = source.read(4096)
            if not chunk:
                break
            destination.buffer.write(chunk)
            destination.buffer.flush()
            buffer += chunk
            parts = re.split(rb"[\r\n]+", buffer)
            buffer = parts.pop() if parts else b""
            for line in parts:
                match = PROGRESS_RE.search(line)
                if match is None:
                    continue
                try:
                    done = _bytes(match.group("done")); total = _bytes(match.group("total"))
                    speed = _bytes(match.group("speed")[:-2])
                    with lock:
                        state.update(
                            bytes_done=min(done, total), bytes_total=total,
                            speed_bytes_per_second=speed,
                            eta_seconds=max(0, int((total - done) / speed)) if speed else None,
                            heartbeat_at=datetime.now(timezone.utc).isoformat(),
                        )
                        publish()
                except (ValueError, OSError):
                    with lock:
                        state["monitoring_health"] = "degraded"

    threads = [
        threading.Thread(target=pump, args=(process.stdout, sys.stdout), daemon=True),
        threading.Thread(target=pump, args=(process.stderr, sys.stderr), daemon=True),
    ]
    for thread in threads: thread.start()
    returncode = process.wait()
    for thread in threads: thread.join()
    with lock:
        state["state"] = "success" if returncode == 0 else "failed"
        if returncode == 0:
            state["files_done"] = 1
            if state["bytes_total"]:
                state["bytes_done"] = state["bytes_total"]
        state["heartbeat_at"] = datetime.now(timezone.utc).isoformat()
        publish()
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
