"""Draft internal producer/wrapper contract, not automatic recovery authority.

Only a trusted runtime reader may supply these objects from controlled, bound
evidence paths. A caller-uploaded seal/hash is NOT authentication. The Master
wrapper must cumulatively account for all failures, submit intents AND admitted
manifest entries before sealing; an empty rule-event list is not completeness.
No current release is assumed to emit this terminal schema. No route is wired.
"""
import hashlib
import json
import re


IDENTITY = ("pipeline", "analysis_id", "attempt", "execution_id", "generation",
            "request_hash", "run_id", "namespace", "master_job_uid", "master_pod_uid")
CATEGORIES = {"WORKER_CREATE_TRANSPORT": "worker_create_transport_interrupted",
              "WORKER_CREATE_ADMISSION_TIMEOUT": "worker_create_admission_timeout"}


def _digest(value):
    try:
        content = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("invalid recovery evidence content") from error
    return hashlib.sha256(content).hexdigest()


def _context(value):
    if not isinstance(value, dict) or value.get("schema") != "snakemake.kubernetes.submit-context.v1":
        raise ValueError("invalid frozen recovery context")
    for key in IDENTITY:
        field = value.get(key)
        if key == "generation":
            if type(field) is not int or field < 0:
                raise ValueError("invalid context generation")
        elif not isinstance(field, str) or not field or field != field.strip() or len(field) > 256:
            raise ValueError("missing or invalid frozen context identity")
    if (value["pipeline"] not in {"wgs", "gatk"}
            or not re.fullmatch(r"[1-9][0-9]*", value["attempt"])
            or not re.fullmatch(r"[a-f0-9]{64}", value["request_hash"])):
        raise ValueError("invalid frozen pipeline, attempt or request hash")


def _bound(value, schema, expected):
    if not isinstance(value, dict) or value.get("schema") != schema:
        raise ValueError("missing or unsupported recovery evidence schema")
    if any(type(value.get(key)) is not type(expected[key]) or value[key] != expected[key]
           for key in IDENTITY):
        raise ValueError("recovery evidence identity differs")


def validate_recovery_evidence(*, expected_context, candidate, terminal):
    """Return validated source metadata only, never dispatch or reserve a budget.

terminal is produced by the trusted wrapper AFTER observing the exact Master
Job failed/Pod exited and fully reconciling all submitted/possibly-created work.
Each assertion is mandatory. Dispatch must independently recheck current state.
"""
    _context(expected_context)
    _bound(candidate, "snakemake.kubernetes.executor-failure.v1", expected_context)
    _bound(terminal, "cce.master-terminal.v1", expected_context)
    if candidate.get("automatic_recovery_allowed") is not False or candidate.get("requires_master_terminal") is not True:
        raise ValueError("plugin candidate cannot authorize recovery")
    if terminal.get("plugin_failure_sha256") != _digest(candidate):
        raise ValueError("plugin evidence digest differs from terminal seal")
    for key in ("sealed", "complete", "worker_inventory_complete",
                "worker_ownership_verified", "submissions_reconciled"):
        if terminal.get(key) is not True:
            raise ValueError("incomplete terminal/worker evidence")
    if (terminal.get("master_state") != "failed" or terminal.get("master_pod_state") != "terminated"
            or type(terminal.get("exit_code")) is not int or terminal["exit_code"] <= 0
            or terminal.get("fatal_source") != "executor_submission"):
        raise ValueError("Master termination is not a classified executor failure")
    for key in ("rule_failure_count", "other_failure_count", "active_worker_jobs",
                "active_worker_pods", "unresolved_submissions"):
        if type(terminal.get(key)) is not int or terminal[key] != 0:
            raise ValueError("conflicting, unresolved or active execution evidence")
    failures = candidate.get("failures")
    if not isinstance(failures, list) or not failures:
        raise ValueError("missing executor failures")
    if type(terminal.get("executor_failure_count")) is not int or terminal["executor_failure_count"] != len(failures):
        raise ValueError("incomplete cumulative executor failure summary")
    categories = set()
    for failure in failures:
        if not isinstance(failure, dict):
            raise ValueError("invalid executor failure")
        category = failure.get("category")
        if (not isinstance(category, str) or category not in CATEGORIES
                or failure.get("creation_state") != "ABSENT"
                or failure.get("retryable") is not True or failure.get("exhausted") is not True
                or type(failure.get("request_count")) is not int or failure["request_count"] < 1
                or not isinstance(failure.get("worker_name"), str) or not failure["worker_name"].strip()
                or "worker_uid" not in failure or failure["worker_uid"] is not None):
            raise ValueError("executor failure is not a resolved allowlisted candidate")
        categories.add(category)
    if len(categories) != 1:
        raise ValueError("multiple fatal root causes require manual review")
    return dict(pipeline=expected_context["pipeline"], analysis_id=expected_context["analysis_id"],
                attempt=int(expected_context["attempt"]), source_execution_id=expected_context["execution_id"],
                source_master_uid=expected_context["master_job_uid"],
                category=CATEGORIES[next(iter(categories))], evidence_sha256=_digest(terminal))
