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
from pathlib import Path

from scripts.cce_recovery_workloads import DNS, UID, probe_bound_workloads, probe_final_workloads


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
                                  checkpoint_bytes, candidate_bytes, manifest_bytes,
                                  final_snapshot=False):
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
    _require(bool(lines) or final_snapshot is True)
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

    candidate = _json(candidate_bytes) if candidate_bytes else {}
    control = candidate.get("schema") == "snakemake.kubernetes.executor-control-failure.v1"
    if candidate_bytes:
        _bound(candidate, "snakemake.kubernetes.executor-control-failure.v1" if control
               else "snakemake.kubernetes.executor-failure.v1", context)
        failures = candidate.get("failures")
        _require(candidate.get("automatic_recovery_allowed") is False
                 and candidate.get("requires_master_terminal") is True
                 and isinstance(failures, list) and bool(failures))
    else:
        _require(final_snapshot is True and not failed)
        failures = []
    if control:
        _require(not failed)  # Mixed control/submission failures require manual review.
        _control_inventory(failures, workers)
    else:
        _require(len(failures) == len(failed) and (bool(failed) or final_snapshot is True))
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


def validate_final_submission_snapshot(snapshot):
    """Consume a native hash-bound FINAL snapshot, never an arbitrary journal.

    The caller must first authenticate its native terminal/bundle binding. This
    validates contents only; live inventories and dispatcher/lock proof remain
    mandatory before replacement. No automatic recovery authority is emitted.
    """
    def encoded(value):
        return (json.dumps(value, sort_keys=True, separators=(",", ":"))+"\n").encode()

    _require(isinstance(snapshot, dict) and type(snapshot.get('schema_version')) is int
             and snapshot['schema_version'] == 1 and len(encoded(snapshot)) <= LIMIT)
    master, phases = snapshot.get('master'), snapshot.get('phases')
    _require(isinstance(master, dict) and isinstance(phases, dict)
             and set(phases) == {'preflight', 'analysis'})
    recovery = master.get('recovery_context')
    _require(isinstance(recovery, dict) and isinstance(snapshot.get('manifest'), str))
    manifest = [_json(line) for line in _lines(snapshot['manifest'].encode())]
    workers, seen = [], set()
    for phase, value in phases.items():
        _require(isinstance(value, dict) and type(value.get('started')) is bool)
        if not value['started']:
            _require(value == {'started':False})
            continue
        context = value.get('context')
        _require(isinstance(context, dict))
        expected = {'pipeline':recovery['pipeline'], 'analysis_id':recovery['analysis_id'],
            'attempt':str(master['attempt']), 'execution_id':recovery['execution_id']+':'+phase,
            'generation':master['execution_generation'], 'request_hash':master['request_hash'],
            'run_id':master['run_id'], 'master_job_uid':master['job_uid'], 'master_pod_uid':master['pod_uid']}
        _require(all(type(context.get(k)) is type(v) and context[k] == v for k,v in expected.items()))
        _require(type(value.get('exit_code')) is int and 0 <= value['exit_code'] <= 255
                 and isinstance(value.get('journal'),str) and isinstance(value.get('candidates'),dict)
                 and isinstance(value.get('terminals'),dict))
        rows = [_json(line) for line in _lines(value['journal'].encode())]
        names = {row.get('worker_name') for row in rows}
        _require(not names & seen)
        phase_manifest = [row for row in manifest if row.get('external_jobid') in names]
        candidates = value['candidates']
        _require(set(candidates) <= {'executor-failure.json','executor-control-failure.json'} and len(candidates) <= 1)
        result = validate_submission_inventory(expected_context=context, journal_bytes=value['journal'].encode(),
            checkpoint_bytes=encoded(value['checkpoint']),
            candidate_bytes=encoded(next(iter(candidates.values()))) if candidates else b'',
            manifest_bytes=b''.join(encoded(row) for row in phase_manifest), final_snapshot=True)
        seen.update(names)
        admitted_uids = {w['uid'] for w in result['workers'] if w['uid'] is not None}
        _require(set(value['terminals']) <= admitted_uids)
        for worker in result['workers']:
            terminal = value['terminals'].get(worker['uid'])
            if terminal is not None:
                admitted = next(row for row in rows if row['worker_name']==worker['name'] and row['event'] in {'CREATED','ADOPTED'})
                bound = {'schema_version':1, 'context_sha256':hashlib.sha256(encoded(context)).hexdigest(),
                    'run_id':context['run_id'], 'attempt':context['attempt'],
                    'execution_generation':context['generation'], 'master_uid':context['master_job_uid'],
                    'namespace':context['namespace'], 'job_name':worker['name'], 'job_uid':worker['uid'],
                    'job_attempt':admitted['job_attempt'], 'submission_identity':admitted['submission_token']}
                _require(isinstance(terminal,dict) and set(terminal)==set(bound)|{'terminal_state','reason','observed_at'}
                         and all(type(terminal.get(k)) is type(v) and terminal[k]==v for k,v in bound.items())
                         and terminal.get('terminal_state') in {'SUCCEEDED','FAILED'}
                         and type(terminal.get('observed_at')) is int and terminal['observed_at'] > 0
                         and _text(terminal.get('reason'),UID))
            workers.append({**worker, 'namespace':context['namespace'],
                            'terminal_state':terminal['terminal_state'] if terminal else None})
    _require(all(row.get('external_jobid') in seen for row in manifest))
    _require(len(workers) <= 4096 and len({w['uid'] for w in workers if w['uid']}) == sum(bool(w['uid']) for w in workers))
    return workers


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


class RecoveryCapability:
    """Internal adapter capability, NOT JSON/API input or recovery policy.

    Task4 supplies authenticated storage/dispatcher and exact lock-owner mapping
    callbacks. This consumer independently verifies native bytes and live work;
    callbacks cannot assert Worker finality in place of those checks.
    """
    def __init__(self, *, bundle, expected_job_uid, context, authorize, verify_lock, platform_execution=None):
        _require(callable(authorize) and callable(verify_lock) and _text(expected_job_uid,UID))
        self.bundle=Path(bundle)
        _require(self.bundle.is_absolute() and self.bundle.resolve(strict=True)==self.bundle)
        self.expected_job_uid=expected_job_uid
        self.context=_json(json.dumps(context))
        self.platform_execution=_json(json.dumps(platform_execution)) if platform_execution is not None else None
        self.authorize=authorize
        self.verify_lock=verify_lock
        self._scope=None

    def bind(self,runtime,contract,config,*,run_label,pipeline,analysis_id,attempt,action):
        _require(type(attempt) is int and attempt>0 and _text(run_label,DNS))
        original=runtime._handoff_binding(self.bundle,contract)
        runtime._validate_recovery_context(self.context,contract,attempt,original['execution_generation']+1)
        _require(original['attempt']==attempt and self.context['pipeline']==pipeline
                 and self.context['analysis_id']==analysis_id and self.context['action']==action)
        if self.platform_execution is not None:
            runtime._validate_platform_execution(self.platform_execution,contract,attempt,self.context)
        else:
            _require('platform_execution' not in original)
        self.runtime,self.contract,self.config,self.run_label=runtime,contract,config,run_label
        self.original=original

    def _authorized(self):
        value=self.runtime._recovery_final_evidence(self.bundle,self.contract,self.expected_job_uid)
        terminal=value['terminal']
        _require(terminal['recovery_context']['pipeline']==self.context['pipeline']
                 and terminal['recovery_context']['analysis_id']==self.context['analysis_id']
                 and terminal['execution_generation']+1==self.context['generation'])
        facts={'context':dict(self.context),'old_job_uid':self.expected_job_uid,
            'old_request_hash':terminal['request_hash'],'config_digest':terminal['config_sha256'],
            'native_directory':value['snapshot']['canonical_directory'],'run_id':terminal['run_id']}
        proof=self.authorize(facts)
        _require(isinstance(proof,dict) and type(proof.get('writers_protocol')) is int and proof['writers_protocol']==2
                 and proof.get('dispatcher_inactive') is True
                 and proof.get('native_directory')==facts['native_directory']
                 and (terminal['state']=='SUCCEEDED' or proof.get('recovery_allowed') is True))
        scope={k:proof.get(k) for k in ('native_directory','canonical_directory','writers_protocol')}
        _require(self._scope is None or self._scope==scope)
        context={'writers_protocol':2,'canonical_directory':scope['canonical_directory'],
            'pipeline':self.context['pipeline'],'analysis_id':self.context['analysis_id'],
            'attempt':str(terminal['attempt']),'run_id':terminal['run_id'],
            'config_digest':terminal['config_sha256'],'generation':self.context['generation'],
            'action':self.context['action'],'master_uid':''}
        self.runtime._directory_lock_identity(self.contract,context)  # Validates canonical storage form.
        self._scope,self._lock_context=scope,context
        return value

    def inspect(self):
        value=self._authorized()
        workers=validate_final_submission_snapshot(value['snapshot'])
        observation=probe_final_workloads(runtime=self.runtime,config=self.config,
            namespace=self.contract['kubernetes']['namespace'],run_label=self.run_label,
            master_job=self.contract['kubernetes']['master_job'],master_job_uid=self.expected_job_uid,
            master_state=value['terminal']['state'],workers=workers)
        return {**value,'observation':observation}

    def lock_context(self,master_uid=''):
        self._authorized()
        return {**self._lock_context,'master_uid':master_uid}

    def claim(self,journal,save_journal,*,master_uid=''):
        def proof(current,operation):
            # Native CAS invokes this immediately before changing an existing owner.
            value=self._authorized() if master_uid else self.inspect()
            mapped=self.verify_lock(current,operation,{'context':dict(self.context),
                'terminal':value['terminal'],'lock_context':self.lock_context(master_uid)})
            _require(isinstance(mapped,dict))
            if master_uid:
                job=self.runtime._recovery_query(self.config,'job',self.contract['kubernetes']['master_job'])
                _require(isinstance(job,dict) and job.get('kind')=='Job'
                         and job.get('metadata',{}).get('uid')==master_uid
                         and not job['metadata'].get('deletionTimestamp'))
                annotations=job['metadata'].get('annotations',{})
                _require(annotations.get('cce-pipeline/recovery-context')==json.dumps(self.context,sort_keys=True)
                         and annotations.get('cce-pipeline/execution-generation')==str(self.context['generation']))
                states={c.get('type') for c in job.get('status',{}).get('conditions',[]) if c.get('status')=='True'}
                _require(len(states & {'Complete','Failed'})<=1)
                return {**mapped,'bound_master_uid':master_uid,
                    'master_state':'FAILED' if 'Failed' in states else 'SUCCEEDED' if 'Complete' in states else 'ACTIVE',
                    'evidence_sha256':value['terminal']['submission_snapshot_sha256']}
            return {**mapped,'inventory_complete':True,'workers_inactive':True,'dispatcher_inactive':True,
                'master_state':value['terminal']['state'],'recovery_allowed':value['terminal']['state']=='FAILED',
                'evidence_sha256':value['terminal']['submission_snapshot_sha256']}
        if master_uid:self._authorized()
        else:self.inspect()
        self.runtime._claim_batch_lock(self.contract,self.config,lock_context=self.lock_context(master_uid),
            journal=journal,save_journal=save_journal,verify=proof)
