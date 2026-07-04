from __future__ import annotations

from pathlib import Path


def ensure_under_root(path: str | Path, root: str | Path, *, label: str = "path") -> Path:
    resolved_path = Path(path).resolve()
    resolved_root = Path(root).resolve()
    if resolved_path != resolved_root and not resolved_path.is_relative_to(resolved_root):
        raise ValueError(f"{label} must be under {resolved_root}: {resolved_path}")
    return resolved_path


def ensure_directory(path: str | Path) -> Path:
    resolved_path = Path(path).resolve()
    resolved_path.mkdir(parents=True, exist_ok=True)
    return resolved_path


def count_nonempty_lines(path: str | Path) -> int:
    target = Path(path)
    if not target.is_file():
        return 0
    return sum(1 for line in target.read_text(encoding="utf-8").splitlines() if line.strip())
