"""Validate a bound submission snapshot before read-only workload reconciliation.

Input bytes must come from a trusted, immutable runtime evidence scope. Hashes
and the producer checkpoint detect inconsistency, NOT authenticity or finality.
A future trusted Master summary must bind the FINAL journal/manifest digests;
an earlier internally consistent snapshot is not proof of complete execution.
This module neither emits a terminal seal nor authorizes automatic recovery.
"""
import hashlib
import json
import re

from scripts.cce_recovery_workloads import DNS, UID, probe_bound_workloads


IDENTITY = ("pipeline", "analysis_id", "attempt", "execution_id", "generation",
            "request_hash", "run_id", "namespace", "master_job_uid", "master_pod_uid")
LIMIT = 16 * 1024 * 1024


def _require(condition):
    if not condition:
        raise ValueError("incomplete or inconsistent submission inventory")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("invalid inventory JSON constant")


def _json(raw):
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("invalid submission inventory JSON") from None
    _require(isinstance(value, dict))
    return value


def _lines(raw):
    _require(not raw or raw.endswith(b"\n"))
    lines = raw.splitlines(keepends=True)
    _require(len(lines) <= 65536)
    return lines


def _text(value, pattern=None):
    return (isinstance(value, str) and 0 < len(value) <= 256
            and value == value.strip()
            and (pattern is None or pattern.fullmatch(value) is not None))


def _bound(value, schema, expected):
    _require(value.get("schema") == schema)
    _require(all(type(value.get(k)) is type(expected[k]) and value[k] == expected[k]
                 for k in IDENTITY))


def _control_inventory(failures, workers):
    """Control observations must refer to admitted work, never invent submissions."""
    for failure in failures:
        _require(isinstance(failure, dict))
        name, uid = failure.get("worker_name"), failure.get("worker_uid")
        _require(_text(name, DNS) and name in workers and "worker_uid" in failure)
        worker = workers[name]
        _require(worker["state"] in {"CREATED", "ADOPTED"} and worker["uid"] is not None
                 and (uid is None or (type(uid) is str and uid == worker["uid"]))
                 and failure.get("category") == "HEAVY_SLOT_API_UNAVAILABLE"
                 and failure.get("phase") == "heavy_slot_refresh"
                 and failure.get("transient_reason") == "CONNECTION_REFUSED"
                 and failure.get("retry_scope") == "same_operation"
                 and failure.get("creation_state") == "UNKNOWN"
                 and failure.get("retryable") is True and failure.get("exhausted") is True
                 and type(failure.get("operation_attempts")) is int
                 and 1 <= failure["operation_attempts"] <= 3)
        if failure.get("operation") == "read_namespaced_lease":
            _require(failure.get("resource_kind") == "Lease"
                     and _text(failure.get("resource_name"), DNS)
                     and "label_selector" in failure and failure["label_selector"] is None)
        else:
            _require(failure.get("operation") == "list_namespaced_pod"
                     and failure.get("resource_kind") == "Pod"
                     and "resource_name" in failure and failure["resource_name"] is None
                     and failure.get("label_selector") == f"job-name={name}")


def validate_submission_inventory(*, expected_context, journal_bytes,
                                  checkpoint_bytes, candidate_bytes, manifest_bytes):
    """Derive every intended/admitted Worker from one internally consistent snapshot."""
    context = expected_context
    _require(isinstance(context, dict)
             and context.get("schema") == "snakemake.kubernetes.submit-context.v1")
    for key in IDENTITY:
        value = context.get(key)
        _require((type(value) is int and value >= 0) if key == "generation" else _text(value))
    _require(context["pipeline"] in {"wgs", "gatk"}
             and re.fullmatch(r"[1-9][0-9]*", context["attempt"]) is not None
             and re.fullmatch(r"[a-f0-9]{64}", context["request_hash"]) is not None
             and _text(context["namespace"], DNS)
             and _text(context["master_job_uid"], UID)
             and _text(context["master_pod_uid"], UID))
    for raw in (journal_bytes, checkpoint_bytes, candidate_bytes, manifest_bytes):
        _require(type(raw) is bytes and len(raw) <= LIMIT)
    lines = _lines(journal_bytes)
    _require(bool(lines))
    digest = hashlib.sha256(b"").hexdigest()
    for line in lines:
        digest = hashlib.sha256(digest.encode() + line).hexdigest()
    checkpoint = _json(checkpoint_bytes)
    _require(type(checkpoint.get("bytes")) is int and type(checkpoint.get("records")) is int)
    _require(checkpoint == dict(bytes=len(journal_bytes), records=len(lines), sha256=digest))

    workers, failed = {}, []
    for line in lines:
        row = _json(line)
        _bound(row, "snakemake.kubernetes.submit-event.v1", context)
        name, uid, event = row.get("worker_name"), row.get("worker_uid"), row.get("event")
        count, attempt = row.get("request_count"), row.get("job_attempt")
        _require(_text(name, DNS) and "worker_uid" in row
                 and (uid is None or _text(uid, UID))
                 and type(count) is int and 0 <= count <= 3
                 and type(attempt) is int and attempt >= 1
                 and _text(row.get("submission_token"))
                 and isinstance(row.get("spec_sha256"), str)
                 and re.fullmatch(r"[a-f0-9]{64}", row["spec_sha256"]) is not None)
        frozen = (attempt, row["submission_token"], row["spec_sha256"])
        if event == "INTENT":
            _require(name not in workers and count == 0 and uid is None and len(workers) < 4096)
            workers[name] = dict(frozen=frozen, count=0, uid=None, state="INTENT")
            continue
        _require(name in workers)
        worker = workers[name]
        _require(worker["frozen"] == frozen and worker["state"] != "FAILED")
        if event == "CREATE_REQUESTED":
            _require(worker["state"] in {"INTENT", "CREATE_REQUESTED"}
                     and count == worker["count"] + 1 and uid is None)
        elif event in {"CREATED", "ADOPTED"}:
            _require(worker["count"] > 0 and count == worker["count"] and uid is not None)
            _require(worker["state"] == "CREATE_REQUESTED"
                     or (event == "ADOPTED" and worker["state"] in {"CREATED", "ADOPTED"}
                         and uid == worker["uid"]))
        elif event == "FAILED":
            _require(worker["count"] > 0 and count == worker["count"] and uid == worker["uid"])
            failed.append(row)
        else:
            raise ValueError("unsupported submission inventory event")
        worker.update(count=count, uid=uid, state=event)

    candidate = _json(candidate_bytes)
    control = candidate.get("schema") == "snakemake.kubernetes.executor-control-failure.v1"
    _bound(candidate, "snakemake.kubernetes.executor-control-failure.v1" if control
           else "snakemake.kubernetes.executor-failure.v1", context)
    failures = candidate.get("failures")
    _require(candidate.get("automatic_recovery_allowed") is False
             and candidate.get("requires_master_terminal") is True
             and isinstance(failures, list) and bool(failures))
    if control:
        _require(not failed)  # Mixed control/submission failures require manual review.
        _control_inventory(failures, workers)
    else:
        _require(len(failures) == len(failed) and bool(failed))
    for failure, row in zip(failures, failed):
        _require(isinstance(failure, dict))
        _require(all(k in failure and type(failure[k]) is type(row[k]) and failure[k] == row[k]
                     for k in ("worker_name", "worker_uid", "request_count")))
        _require(failure.get("category") in ("WORKER_CREATE_ADMISSION_TIMEOUT", "WORKER_CREATE_TRANSPORT")
                 and failure.get("creation_state") == "ABSENT" and failure["worker_uid"] is None
                 and failure.get("retryable") is True and failure.get("exhausted") is True)
    _require(all(w["state"] in {"CREATED", "ADOPTED", "FAILED"} for w in workers.values()))

    admitted = {n: w for n, w in workers.items() if w["uid"] is not None}
    seen = set()
    for line in _lines(manifest_bytes):
        row = _json(line)
        name, uid = row.get("external_jobid"), row.get("kubernetes_uid")
        _require(_text(name, DNS) and name in admitted and name not in seen
                 and type(row.get("schema_version")) is int and row["schema_version"] == 2
                 and type(row.get("attempt")) is int and row["attempt"] == admitted[name]["frozen"][0]
                 and uid == admitted[name]["uid"])
        seen.add(name)
    _require(seen == set(admitted))
    return dict(workers=[dict(name=n, uid=w["uid"]) for n, w in workers.items()],
                executor_failure_count=len(failures), journal_sha256=hashlib.sha256(journal_bytes).hexdigest(),
                manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest())


def probe_submission_inventory(*, runtime, config, master_job, expected_context,
                               journal_bytes, checkpoint_bytes, candidate_bytes,
                               manifest_bytes, timeout_seconds=120):
    """Reconcile all validated intents, never a caller-chosen subset of Workers."""
    inventory = validate_submission_inventory(expected_context=expected_context,
        journal_bytes=journal_bytes, checkpoint_bytes=checkpoint_bytes,
        candidate_bytes=candidate_bytes, manifest_bytes=manifest_bytes)
    observation = probe_bound_workloads(runtime=runtime, config=config,
        namespace=expected_context["namespace"], master_job=master_job,
        master_job_uid=expected_context["master_job_uid"], master_pod_uid=expected_context["master_pod_uid"],
        workers=inventory["workers"], timeout_seconds=timeout_seconds)
    return dict(inventory=inventory, observation=observation)
