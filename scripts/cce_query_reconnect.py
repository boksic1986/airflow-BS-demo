"""Finite query-only budget for the registered monitor (no activation here).

The trusted caller owns the current-execution lock and persists these fields in
its existing stage JSON. Save must complete durably before a retry is issued.
Only the paired runtime's typed read-only query error is accepted; this helper
must not wrap a stage, command submission, CREATE/START or a transfer operation.
"""
from copy import deepcopy
import math
import time


DELAYS = (30, 60, 120, 240, 300, 300)
RETRYABLE = {"TRANSPORT", "SERVICE"}
PHASES = {"healthy", "waiting", "querying", "observing", "blocked", "exhausted"}
SCOPE_KEYS = {"pipeline", "analysis_id", "attempt", "stage", "execution_id", "generation", "request_hash"}


class QueryReconnectStopped(RuntimeError):
    """Monitor stopped; not evidence of remote workflow failure."""


class QueryReconnect:
    def __init__(self, *, scope, deadline, load, save, error_type,
                 now=time.time, sleep=time.sleep):
        if (not isinstance(scope, dict) or set(scope) != SCOPE_KEYS
                or scope["pipeline"] not in {"wgs", "gatk"} or scope["stage"] != "step3_monitor"
                or any(type(scope[k]) is not int or scope[k] < 1 for k in ("attempt", "generation"))
                or any(not isinstance(scope[k], str) or not scope[k] for k in
                       ("analysis_id", "execution_id", "request_hash"))
                or not _number(deadline) or not isinstance(error_type, type)
                or not issubclass(error_type, Exception)):
            raise ValueError("invalid reconnect owner")
        self.scope, self.deadline = deepcopy(scope), deadline
        self.load, self.save, self.error_type = load, save, error_type
        self.now, self.sleep = now, sleep
        self.observed = False

    def _state(self):
        value = self.load()
        if value is None:
            return dict(version=1, scope=deepcopy(self.scope), deadline=self.deadline,
                phase="healthy", retries_used=0, first_error_at=None, last_error_at=None,
                last_success_at=None, next_retry_at=None, reason=None)
        if (not isinstance(value, dict) or type(value.get("version")) is not int or value["version"] != 1
                or not isinstance(value.get("scope"), dict) or value["scope"] != self.scope
                or any(type(value["scope"].get(k)) is not type(v) for k, v in self.scope.items())
                or not _number(value.get("deadline"))
                or value["deadline"] != self.deadline or value.get("phase") not in PHASES
                or type(value.get("retries_used")) is not int or not 0 <= value["retries_used"] <= 6
                or any(value.get(k) is not None and not _number(value[k]) for k in
                       ("first_error_at", "last_error_at", "last_success_at", "next_retry_at"))
                or value["phase"] == "waiting" and (value.get("next_retry_at") is None or value["retries_used"] >= len(DELAYS))
                or value["phase"] in {"waiting", "querying", "observing"} and value.get("first_error_at") is None
                or value["phase"] == "querying" and value["retries_used"] == 0
                or value["phase"] == "healthy" and (value["retries_used"] != 0 or any(
                    value.get(k) is not None for k in ("first_error_at", "last_error_at", "next_retry_at", "reason")))
                or value.get("reason") not in {None, "TRANSPORT", "SERVICE", "FORBIDDEN", "AUTHENTICATION",
                    "INVALID_QUERY", "INVALID_RESPONSE", "QUERY_FAILED", "LOCAL_COMMAND",
                    "non_retryable", "deadline", "retry_limit"}):
            raise ValueError("invalid reconnect state; manual reconciliation required")
        return deepcopy(value)

    def _save(self, state):
        self.save(deepcopy(state))  # Failure stops before any further request.

    def _stop(self, state, phase, reason):
        state.update(phase=phase, reason=reason, next_retry_at=None)
        self._save(state)
        raise QueryReconnectStopped(f"query reconnect {phase}: {reason}")

    def _remaining(self, state):
        remaining = self.deadline - self.now()
        if remaining <= 0:
            self._stop(state, "exhausted", "deadline")
        return remaining

    def _schedule(self, state):
        self._remaining(state)
        if state["retries_used"] >= len(DELAYS):
            self._stop(state, "exhausted", "retry_limit")
        state.update(phase="waiting", next_retry_at=self.now() + DELAYS[state["retries_used"]])
        self._save(state)

    def run(self, query):
        """query(timeout) is one typed read-only GET, never an entire monitor."""
        self.observed = False
        state = self._state()
        if state["phase"] in {"blocked", "exhausted"}:
            raise QueryReconnectStopped(f"query reconnect {state['phase']}: {state['reason']}")
        if state["phase"] == "querying":
            # A crashed process may have sent the reserved retry. Never refund.
            self._schedule(state)
        while True:
            self._remaining(state)
            if state["phase"] == "waiting":
                delay = state["next_retry_at"] - self.now()
                if delay > 0:
                    self.sleep(min(delay, self._remaining(state)))
                    continue
                state.update(phase="querying", retries_used=state["retries_used"] + 1, next_retry_at=None)
                self._save(state)
            try:
                result = query(min(30, self._remaining(state)))
            except self.error_type as error:
                code = getattr(error, "code", "QUERY_FAILED")
                if state["phase"] == "healthy":
                    state.update(retries_used=0, first_error_at=self.now())
                state["last_error_at"] = self.now()
                state["reason"] = code if code in RETRYABLE else "non_retryable"
                if code not in RETRYABLE:
                    # Preserve only native fixed classifications, never stderr.
                    reason = code if code in {"FORBIDDEN", "AUTHENTICATION", "INVALID_QUERY",
                        "INVALID_RESPONSE", "QUERY_FAILED", "LOCAL_COMMAND"} else "non_retryable"
                    self._stop(state, "blocked", reason)
                self._schedule(state)
                continue
            self._remaining(state)  # A late response cannot outlive the original deadline.
            if state["phase"] != "healthy":
                state.update(phase="observing", next_retry_at=None)
                self._save(state)
            self.observed = True
            return result

    def confirmed(self):
        """Caller verified the whole current-Master observation, not a partial GET."""
        state = self._state()
        if not self.observed or state["phase"] in {"blocked", "exhausted"}:
            raise ValueError("authoritative current observation required")
        self._remaining(state)
        state.update(phase="healthy", retries_used=0, first_error_at=None,
            last_error_at=None, next_retry_at=None, reason=None, last_success_at=self.now())
        self._save(state)
        self.observed = False


def _number(value):
    return type(value) in {int, float} and math.isfinite(value)
