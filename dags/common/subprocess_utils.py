from __future__ import annotations

from pathlib import Path
import subprocess


def run_command_to_logs(
    command: list[str],
    *,
    cwd: str | Path,
    stdout_path: str | Path,
    stderr_path: str | Path,
    env: dict[str, str] | None = None,
) -> dict[str, str | int]:
    stdout = Path(stdout_path)
    stderr = Path(stderr_path)
    stdout.parent.mkdir(parents=True, exist_ok=True)
    stderr.parent.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    stdout.write_text(completed.stdout or "", encoding="utf-8")
    stderr.write_text(completed.stderr or "", encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}. See {stderr}")
    return {"return_code": completed.returncode, "stdout_path": str(stdout), "stderr_path": str(stderr)}
