from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from app.input_scanner import ensure_allowed_path


FASTQ_RE = re.compile(
    r"^(?P<sample>.+?)(?:[_.-])R(?P<read>[12])(?:[_.-][^.]+)?\.(?:fastq|fq)\.gz$",
    re.IGNORECASE,
)
PROGRESS_RE = re.compile(
    r"(?P<percent>\d+(?:\.\d+)?)%\s+"
    r"(?P<speed>\d+(?:\.\d+)?)(?P<speed_unit>[KMGT]?i?B)/s\s+"
    r"(?P<done>\d+(?:\.\d+)?)(?P<done_unit>[KMGT]?i?B)/"
    r"(?P<total>\d+(?:\.\d+)?)(?P<total_unit>[KMGT]?i?B)\s+"
    r"(?P<eta>(?:\d+h)?(?:\d+m)?(?:\d+s)?)"
)


class SnapshotChangedError(ValueError):
    pass


def build_fastq_snapshot(
    *,
    fq_path: str,
    allowed_link_roots: list[str],
    allowed_fastq_roots: list[str],
    manifest_path: Path,
) -> dict:
    link_dir = ensure_allowed_path(fq_path, allowed_link_roots)
    if not link_dir.is_dir():
        raise ValueError("fq_path must be a controlled FASTQ link directory")
    files: list[dict] = []
    pairs: dict[str, set[str]] = {}
    for link in sorted(link_dir.iterdir(), key=lambda item: item.name):
        if not link.is_symlink():
            if FASTQ_RE.match(link.name):
                raise ValueError(f"FASTQ entry must be a symbolic link: {link.name}")
            continue
        match = FASTQ_RE.match(link.name)
        if match is None:
            continue
        target = ensure_allowed_path(link.resolve(strict=True), allowed_fastq_roots)
        if not target.is_file():
            raise ValueError(f"FASTQ link target is not a regular file: {link.name}")
        stat = target.stat()
        sample_id = match.group("sample")
        read = f"R{match.group('read')}"
        if read in pairs.setdefault(sample_id, set()):
            raise ValueError(f"duplicate {read} for sample {sample_id}")
        pairs[sample_id].add(read)
        files.append(
            {
                "logical_name": link.name,
                "resolved_path": str(target),
                "sample_id": sample_id,
                "read": read,
                "device": int(stat.st_dev),
                "inode": int(stat.st_ino),
                "size": int(stat.st_size),
                "mtime_ns": int(stat.st_mtime_ns),
            }
        )
    if not files:
        raise ValueError("fq_path contains no supported FASTQ symbolic links")
    incomplete = sorted(sample for sample, reads in pairs.items() if reads != {"R1", "R2"})
    if incomplete:
        raise ValueError(f"FASTQ pair is incomplete for samples: {', '.join(incomplete)}")
    payload = {
        "schema_version": "1",
        "fq_path": str(link_dir),
        "file_count": len(files),
        "sample_count": len(pairs),
        "total_bytes": sum(item["size"] for item in files),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    payload["manifest_sha256"] = _manifest_sha256(payload)
    _atomic_json(manifest_path, payload)
    return payload


def verify_fastq_snapshot(manifest_path: Path) -> dict:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("manifest_sha256") != _manifest_sha256(payload):
        raise SnapshotChangedError("source snapshot changed: input manifest integrity check failed")
    for item in payload.get("files", []):
        path = Path(str(item["resolved_path"]))
        try:
            stat = path.stat()
        except OSError as error:
            raise SnapshotChangedError(f"source snapshot changed: {item['logical_name']} is unavailable") from error
        current = (int(stat.st_dev), int(stat.st_ino), int(stat.st_size), int(stat.st_mtime_ns))
        expected = (int(item["device"]), int(item["inode"]), int(item["size"]), int(item["mtime_ns"]))
        if current != expected:
            raise SnapshotChangedError(f"source snapshot changed: {item['logical_name']}")
    return payload


def parse_obsutil_progress(line: str) -> dict[str, int | float] | None:
    match = PROGRESS_RE.search(line.replace("\r", "").replace("\n", ""))
    if match is None:
        return None
    return {
        "percent": float(match.group("percent")),
        "speed_bps": _bytes(float(match.group("speed")), match.group("speed_unit")),
        "bytes_transferred": _bytes(float(match.group("done")), match.group("done_unit")),
        "bytes_total": _bytes(float(match.group("total")), match.group("total_unit")),
        "eta_seconds": _duration_seconds(match.group("eta")),
    }


def write_transfer_progress(spool_path: Path, payload: dict) -> None:
    required = {"analysis_id", "attempt", "transfer_id", "transfer_type", "direction", "status"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"transfer progress missing fields: {', '.join(missing)}")
    safe = dict(payload)
    safe["heartbeat_at"] = str(safe.get("heartbeat_at") or datetime.now(timezone.utc).isoformat())
    _atomic_json(spool_path, safe)


def _manifest_sha256(payload: dict) -> str:
    canonical = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _bytes(value: float, unit: str) -> int:
    units = {"B": 1, "KB": 1000, "MB": 1000**2, "GB": 1000**3, "TB": 1000**4,
             "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}
    return int(round(value * units[unit]))


def _duration_seconds(value: str) -> int:
    match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", value)
    if match is None:
        return 0
    hours, minutes, seconds = (int(item or 0) for item in match.groups())
    return hours * 3600 + minutes * 60 + seconds
