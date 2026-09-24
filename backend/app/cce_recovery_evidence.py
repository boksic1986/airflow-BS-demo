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
CONTROL_SCHEMA = "snakemake.kubernetes.executor-control-failure.v1"


def _control_failure(failure):
    name = failure.get("worker_name")
    uid = failure.get("worker_uid")
    if (failure.get("category") != "HEAVY_SLOT_API_UNAVAILABLE"
            or failure.get("phase") != "heavy_slot_refresh"
            or failure.get("transient_reason") != "CONNECTION_REFUSED"
            or failure.get("retry_scope") != "same_operation"
            or failure.get("creation_state") != "UNKNOWN"
            or failure.get("retryable") is not True or failure.get("exhausted") is not True
            or type(failure.get("operation_attempts")) is not int
            or not 1 <= failure["operation_attempts"] <= 3
            or not isinstance(name, str) or len(name) > 63
            or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", name)
            or "worker_uid" not in failure
            or (uid is not None and (not isinstance(uid, str) or not uid.strip()
                                    or uid != uid.strip() or len(uid) > 256))):
        raise ValueError("control failure is not an allowlisted read candidate")
    operation = failure.get("operation")
    resource = failure.get("resource_name")
    if operation == "read_namespaced_lease":
        valid = (failure.get("resource_kind") == "Lease"
                 and isinstance(resource, str) and len(resource) <= 253
                 and re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", resource)
                 and "label_selector" in failure and failure["label_selector"] is None)
    elif operation == "list_namespaced_pod":
        valid = (failure.get("resource_kind") == "Pod"
                 and "resource_name" in failure and resource is None
                 and failure.get("label_selector") == f"job-name={name}")
    else:
        valid = False
    if not valid:
        raise ValueError("control failure requires an exact Lease GET or Worker Pod LIST")


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
    control = isinstance(candidate, dict) and candidate.get("schema") == CONTROL_SCHEMA
    _bound(candidate, CONTROL_SCHEMA if control else "snakemake.kubernetes.executor-failure.v1", expected_context)
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
            or terminal.get("fatal_source") != ("executor_control" if control else "executor_submission")):
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
        if control:
            _control_failure(failure)
            categories.add("HEAVY_SLOT_API_UNAVAILABLE")
            continue
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
                category="heavy_slot_api_unavailable" if control else CATEGORIES[next(iter(categories))],
                evidence_sha256=_digest(terminal))


def validate_schema2_recovery_evidence(*, binding, evidence, expected_platform):
    """Consume only the authenticated monitor receipt, not browser-uploaded data.

    The restricted reader has revalidated native FINAL and complete live work.
    Native phase identity intentionally differs from the platform producer row.
    Dispatch must still repeat quiescence and current-control checks.
    """
    if (not isinstance(binding,dict) or type(binding.get('schema_version')) is not int
            or binding['schema_version'] != 2 or not isinstance(evidence,dict)
            or type(evidence.get('schema_version')) is not int or evidence['schema_version'] != 2
            or _digest(evidence.get('binding')) != _digest(binding)
            or _digest(binding.get('platform_execution')) != _digest(expected_platform)):
        raise ValueError('automatic evidence differs from schema2 Master binding')
    native = binding.get('native')
    phase = evidence.get('phase')
    if (not isinstance(native,dict) or phase not in {'preflight','analysis'}
            or type(native.get('attempt')) is not int or native['attempt'] != expected_platform['attempt']
            or not isinstance(native.get('recovery_context'),dict)):
        raise ValueError('invalid native recovery identity')
    recovery = native['recovery_context']
    if (recovery.get('pipeline') != expected_platform['pipeline']
            or recovery.get('analysis_id') != expected_platform['analysis_id']
            or not isinstance(recovery.get('execution_id'),str)):
        raise ValueError('native recovery belongs to another analysis')
    context = dict(schema='snakemake.kubernetes.submit-context.v1',
        pipeline=recovery['pipeline'],analysis_id=recovery['analysis_id'],attempt=str(native['attempt']),
        execution_id=recovery['execution_id']+':'+phase,generation=native.get('execution_generation'),
        request_hash=native.get('request_hash'),run_id=native.get('run_id'),namespace=native.get('namespace'),
        master_job_uid=native.get('job_uid'),master_pod_uid=native.get('pod_uid'))
    terminal = evidence.get('terminal')
    if (not isinstance(terminal,dict) or not isinstance(terminal.get('submission_snapshot_sha256'),str)
            or not re.fullmatch(r'[a-f0-9]{64}',terminal['submission_snapshot_sha256'])):
        raise ValueError('native FINAL snapshot digest is required')
    result = validate_recovery_evidence(expected_context=context,candidate=evidence.get('candidate'),terminal=terminal)
    return dict(result,evidence_key=f"native-final/{native['job_uid']}/{phase}",
        native_binding_sha256=_digest(binding))
