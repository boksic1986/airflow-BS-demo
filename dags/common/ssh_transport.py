"""Bounded OpenSSH connection retries for trusted, fixed runner commands.

This layer never decides whether a remote command ran or grants a new dispatch.
Only a complete, known pre-session diagnostic permits sending the same command
again. Callers retain registration, exact observation and business deadlines.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import math
import re
import subprocess
import time
from typing import Sequence


LOG = logging.getLogger(__name__)
_RECONNECT_DELAYS = (5.0, 10.0)
_PRE_SESSION = (
    r"Connection timed out during banner exchange",
    r"ssh: connect to host \S+ port \d+: (?:Connection timed out|Connection refused|No route to host)",
    r"(?:kex_exchange_identification|ssh_exchange_identification): (?:read: Connection reset(?: by peer)?|Connection closed by remote host)",
)
_TRAILER = (
    r"(?:Connection (?:closed|reset) by \S+ port \d+|"
    r"Connection to \S+ port \d+ timed out)"
)


def pre_session_failure(result: subprocess.CompletedProcess[str]) -> bool:
    """Require exit 255, truly empty stdout and an entirely allowlisted stderr."""
    if result.returncode != 255 or result.stdout:
        return False
    lines = [line.strip() for line in (result.stderr or "").splitlines() if line.strip()]
    return bool(lines) and any(
        re.fullmatch(pattern, line) for line in lines for pattern in _PRE_SESSION
    ) and all(
        any(re.fullmatch(pattern, line) for pattern in (*_PRE_SESSION, _TRAILER))
        for line in lines
    )


@dataclass
class SSHCallBudget:
    """One invocation window, also shared across WGS request-visibility checks."""

    deadline_monotonic: float
    pre_session_failures: int = 0

    @classmethod
    def start(cls, timeout_seconds: float, deadline_epoch: float | None = None) -> "SSHCallBudget":
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("SSH timeout must be positive and finite")
        remaining = float(timeout_seconds)
        if deadline_epoch is not None:
            if not math.isfinite(deadline_epoch):
                raise ValueError("SSH deadline must be finite")
            remaining = min(remaining, deadline_epoch - time.time())
        return cls(time.monotonic() + max(remaining, 0.0))

    def remaining(self) -> float:
        return self.deadline_monotonic - time.monotonic()


def run_ssh(
    command: Sequence[str], *, timeout_seconds: float,
    deadline_epoch: float | None = None, budget: SSHCallBudget | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one fixed command with a single total budget and safe reconnects.

    A supplied budget keeps the same deadline and pre-session failure count over
    a caller's separate request-visibility attempts. Command timeout and a
    lost response are passed to the caller without a replay decision here.
    """
    if not command or command[0] != "ssh":
        raise ValueError("trusted SSH command is required")
    limit = SSHCallBudget.start(timeout_seconds, deadline_epoch)
    if budget is None:
        budget = limit
    else:
        budget.deadline_monotonic = min(budget.deadline_monotonic, limit.deadline_monotonic)
    # CLI options override SSH config defaults. The caller retains its fixed
    # config, alias, restricted command and exact identity arguments.
    fixed_command = [
        "ssh", "-o", "ConnectTimeout=30", "-o", "ConnectionAttempts=1",
        *command[1:],
    ]
    while True:
        if budget.pre_session_failures >= 3:
            raise subprocess.SubprocessError("SSH pre-session connection attempts exhausted")
        remaining = budget.remaining()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(fixed_command, timeout_seconds)
        result = subprocess.run(
            fixed_command, check=False, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=remaining,
        )
        if not pre_session_failure(result):
            return result
        budget.pre_session_failures += 1
        if budget.pre_session_failures >= 3:
            return result
        delay = _RECONNECT_DELAYS[budget.pre_session_failures - 1]
        if budget.remaining() <= delay:
            return result
        LOG.warning(
            "SSH connection failed before a session; reconnecting (%s/3) in %ss",
            budget.pre_session_failures + 1, delay,
        )
        time.sleep(delay)
