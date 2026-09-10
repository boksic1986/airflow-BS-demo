#!/bi/software/mamba/envs/WGS/bin/python3.11
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
import xml.etree.ElementTree as ET


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


def _checkpoint_root(arguments: list[str]) -> Path | None:
    for index, argument in enumerate(arguments):
        if argument.startswith("-cpd="):
            value = argument.split("=", 1)[1]
            return Path(value) if value else None
        if argument == "-cpd" and index + 1 < len(arguments):
            return Path(arguments[index + 1])
    return None


def _completed(value: str | None) -> bool:
    return str(value or "").strip().lower() == "true"


def _checkpoint_progress(root: Path, direction: str) -> tuple[int, int] | None:
    """Return the most advanced valid checkpoint without exposing its content."""
    if direction not in {"upload", "download"}:
        return None
    try:
        if not root.is_dir() or root.is_symlink():
            return None
        candidates: list[tuple[int, int]] = []
        for path in root.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                document = ET.parse(path).getroot()
                if direction == "upload":
                    total_text = document.findtext("./FileInfo/Size")
                    parts = document.findall("./UploadParts/UploadPart")
                    done = sum(
                        int(part.findtext("PartSize") or 0)
                        for part in parts
                        if _completed(part.findtext("IsCompleted"))
                    )
                else:
                    total_text = document.findtext("./ObjectInfo/Size")
                    parts = document.findall("./DownloadParts/DownloadPart")
                    done = sum(
                        max(
                            0,
                            int(part.findtext("RangeEnd") or -1)
                            - int(part.findtext("RangeStart") or 0)
                            + 1,
                        )
                        for part in parts
                        if _completed(part.findtext("IsCompleted"))
                    )
                total = int(total_text or 0)
                if total > 0 and 0 <= done <= total:
                    candidates.append((done, total))
            except (ET.ParseError, OSError, TypeError, ValueError):
                # obsutil rewrites checkpoint XML in place. A partial read must
                # not interrupt the real transfer or regress the last snapshot.
                continue
        return max(candidates, key=lambda value: value[0]) if candidates else None
    except OSError:
        return None


def _public_file(arguments: list[str], plan_path: Path | None) -> dict[str, object] | None:
    if plan_path is None:
        return None
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    entries = plan.get("entries") if isinstance(plan, dict) else None
    if not isinstance(entries, list):
        return None
    normalized_arguments = [
        argument.replace("\\", "/").removesuffix(".partial").rstrip("/")
        for argument in arguments
    ]
    matches: list[tuple[str, int]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        relative = str(entry.get("relative_path") or "").replace("\\", "/").lstrip("/")
        if not relative or relative.startswith("../") or "/../" in f"/{relative}/":
            continue
        display_name = Path(relative).name
        if any(
            value.endswith(f"/{relative}")
            or value == relative
            or value.rsplit("/", 1)[-1] == display_name
            for value in normalized_arguments
        ):
            try:
                matches.append((relative, int(entry.get("size_bytes") or 0)))
            except (TypeError, ValueError):
                continue
    if len(matches) != 1 or matches[0][1] < 0:
        return None
    relative, size = matches[0]
    return {
        "file_key": hashlib.sha256(relative.encode("utf-8")).hexdigest(),
        "display_name": Path(relative).name,
        "bytes_total": size,
    }


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
    direction = os.environ.get("WGS_TRANSFER_DIRECTION")
    checkpoint_root = _checkpoint_root(arguments)
    plan_text = os.environ.get("WGS_TRANSFER_PLAN_PATH", "").strip()
    public_file = _public_file(arguments, Path(plan_text) if plan_text else None)
    started_at = datetime.now(timezone.utc).isoformat()
    state = {
        "schema_version": SCHEMA,
        "analysis_id": os.environ.get("WGS_TRANSFER_ANALYSIS_ID"),
        "attempt": int(os.environ.get("WGS_TRANSFER_ATTEMPT", "1")),
        "stage": os.environ.get("WGS_TRANSFER_STAGE"),
        "direction": direction,
        "transfer_id": _identity(arguments),
        "state": "running",
        "bytes_total": int(public_file["bytes_total"]) if public_file else 0,
        "bytes_done": 0,
        "files_total": 1,
        "files_done": 0,
        "current_file": None,
        "speed_bytes_per_second": 0,
        "eta_seconds": None,
        "heartbeat_at": started_at,
        "started_at": started_at,
        "ended_at": None,
        "monitoring_health": "healthy",
        "source": "obsutil-checkpoint" if public_file else "obsutil-stream",
        "checkpoint_observed": False,
        "checksum_status": "pending",
    }
    if public_file:
        state.update(
            file_key=public_file["file_key"],
            display_name=public_file["display_name"],
        )
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
    stop_monitor = threading.Event()

    def monitor_checkpoint() -> None:
        nonlocal public_file
        try:
            interval = max(
                0.02,
                float(os.environ.get("WGS_TRANSFER_CHECKPOINT_POLL_SECONDS", "0.25")),
            )
        except ValueError:
            interval = 0.25
        while not stop_monitor.wait(interval):
            if public_file is None:
                candidate = _public_file(
                    arguments, Path(plan_text) if plan_text else None
                )
                if candidate is not None:
                    with lock:
                        public_file = candidate
                        state.update(
                            file_key=candidate["file_key"],
                            display_name=candidate["display_name"],
                            bytes_total=int(candidate["bytes_total"]),
                            source="obsutil-checkpoint",
                        )
                        publish()
            if checkpoint_root is None:
                continue
            observed = _checkpoint_progress(checkpoint_root, str(direction or ""))
            if observed is None:
                continue
            done, checkpoint_total = observed
            with lock:
                expected_total = int(state.get("bytes_total") or 0)
                if expected_total and checkpoint_total != expected_total:
                    state["monitoring_health"] = "degraded"
                    publish()
                    continue
                total = expected_total or checkpoint_total
                state.update(
                    bytes_done=max(int(state.get("bytes_done") or 0), min(done, total)),
                    bytes_total=total,
                    eta_seconds=None,
                    heartbeat_at=datetime.now(timezone.utc).isoformat(),
                    checkpoint_observed=True,
                    source="obsutil-checkpoint",
                )
                publish()

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
        threading.Thread(target=monitor_checkpoint, daemon=True),
    ]
    for thread in threads: thread.start()
    returncode = process.wait()
    stop_monitor.set()
    for thread in threads: thread.join()
    with lock:
        if public_file is None:
            public_file = _public_file(
                arguments, Path(plan_text) if plan_text else None
            )
            if public_file is not None:
                state.update(
                    file_key=public_file["file_key"],
                    display_name=public_file["display_name"],
                    bytes_total=int(public_file["bytes_total"]),
                    source="obsutil-checkpoint",
                )
        if checkpoint_root is not None:
            observed = _checkpoint_progress(checkpoint_root, str(direction or ""))
            if observed is not None:
                done, checkpoint_total = observed
                expected_total = int(state.get("bytes_total") or 0)
                if not expected_total or expected_total == checkpoint_total:
                    total = expected_total or checkpoint_total
                    state["bytes_total"] = total
                    state["bytes_done"] = max(
                        int(state.get("bytes_done") or 0), min(done, total)
                    )
                    state["checkpoint_observed"] = True
                    state["source"] = "obsutil-checkpoint"
        state["state"] = "success" if returncode == 0 else "failed"
        if returncode == 0:
            state["files_done"] = 1
            if state["bytes_total"]:
                state["bytes_done"] = state["bytes_total"]
            if "-vmd5" in arguments and "-vlength" in arguments:
                state["checksum_status"] = "verified"
        else:
            state["checksum_status"] = "failed"
        ended_at = datetime.now(timezone.utc).isoformat()
        state["heartbeat_at"] = ended_at
        state["ended_at"] = ended_at
        publish()
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
