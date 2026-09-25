"""Read the fixed P0 evidence pair from an adapter-controlled generation scope.

Internal only: root, relative_dir and expected_context must come from the trusted
adapter's frozen binding, never from a browser request or from the evidence being
read. Path confinement is not authentication of the runtime writer. No current
adapter is wired until its Master/monitor lineage and terminal producer exist.
"""
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from app.cce_recovery_evidence import validate_recovery_evidence


MAX_BYTES = 1024 * 1024
FILES = ("executor-failure.json", "master-terminal.json")
CANDIDATES = (FILES[0], "executor-control-failure.json")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate recovery evidence key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-finite recovery evidence value")


def _fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read(directory_fd, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_BYTES:
            raise ValueError("unsafe recovery evidence file")
        data = bytearray()
        while True:
            chunk = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise ValueError("recovery evidence exceeds size limit")
        if _fingerprint(os.fstat(fd)) != _fingerprint(info):
            raise ValueError("recovery evidence changed during read")
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_object,
                           parse_constant=_reject_constant)
        if not isinstance(value, dict):
            raise ValueError("recovery evidence must be an object")
        return value, _fingerprint(info)
    finally:
        os.close(fd)


def read_recovery_evidence(*, root, relative_dir, expected_context):
    """Read and validate only this scope; return metadata, not dispatch authority."""
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts or root == Path(root.anchor):
        raise ValueError("invalid controlled recovery root")
    if (not isinstance(relative_dir, str) or not relative_dir
            or any(not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", part)
                   for part in relative_dir.split("/"))):
        raise ValueError("invalid recovery evidence scope")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ValueError("safe recovery reads unavailable on this platform")
    fd = None
    try:
        fd = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY)
        for part in (*root.parts[1:], *PurePosixPath(relative_dir).parts):
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        # A second fatal source is not a fallback. Include directory mutation in
        # the snapshot so concurrent creation/removal cannot hide mixed causes.
        directory_fingerprint = _fingerprint(os.fstat(fd))
        present = []
        for name in CANDIDATES:
            try:
                os.stat(name, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            present.append(name)
        if len(present) != 1:
            raise ValueError("exactly one recovery candidate source required")
        files = (present[0], FILES[1])
        records = [_read(fd, name) for name in files]
        expected_schema = ("snakemake.kubernetes.executor-failure.v1" if files[0] == FILES[0]
                           else "snakemake.kubernetes.executor-control-failure.v1")
        if records[0][0].get("schema") != expected_schema:
            raise ValueError("recovery candidate filename/schema differs")
        for name, (_, fingerprint) in zip(files, records):
            if _fingerprint(os.stat(name, dir_fd=fd, follow_symlinks=False)) != fingerprint:
                raise ValueError("recovery evidence pair changed during read")
        if _fingerprint(os.fstat(fd)) != directory_fingerprint:
            raise ValueError("recovery evidence scope changed during read")
        result = validate_recovery_evidence(expected_context=expected_context,
            candidate=records[0][0], terminal=records[1][0])
        return dict(result, evidence_key=f"{relative_dir}/{FILES[1]}")
    except (OSError, UnicodeError, RecursionError) as error:
        # Do not expose arbitrary host paths or parser excerpts to callers.
        raise ValueError("recovery evidence unavailable or unsafe") from error
    finally:
        if fd is not None:
            os.close(fd)
