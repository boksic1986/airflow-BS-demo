"""Read-only UID-bound Kubernetes observations for the P0 terminal writer.

Inputs MUST come from frozen Master binding and the complete validated submission
journal/Worker manifest, not a browser or an arbitrary list inferred from logs.
This probe cannot prove that list's completeness or classify workflow failures.
It does not issue a seal, authorize resume, delete workloads, or change status.
Queries are observations, not an atomic cluster transaction: recheck at dispatch.
"""
import json
import re
import subprocess
import time


DNS = re.compile(r"[a-z0-9](?:[-a-z0-9.]{0,251}[a-z0-9])?\Z")
UID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
REASONS = frozenset({"BackoffLimitExceeded", "DeadlineExceeded", "PodFailurePolicy",
    "FailedIndexes", "MaxFailedIndexesExceeded", "CompletionsReached", "SuccessPolicy",
    "OOMKilled", "Error", "Completed", "ContainerCannotRun", "StartError",
    "Evicted", "NodeLost", "UnexpectedAdmissionError", "Shutdown"})


def _identity(value, pattern):
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError("invalid frozen workload identity")


def _object(value):
    if not isinstance(value, dict):
        raise ValueError("invalid workload object")
    return value


def _unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate workload JSON field")
        result[key] = value
    return result


def _reason(value):
    # Never publish arbitrary message/stderr fields as a structured cause.
    if value is None:
        return None
    return value if isinstance(value, str) and value in REASONS else "Unknown"


def _termination(value):
    value = _object(value)
    code, signal = value.get("exitCode"), value.get("signal")
    if (type(code) is not int or not 0 <= code <= 255
            or (signal is not None and (type(signal) is not int or not 0 <= signal <= 64))):
        raise ValueError("container termination evidence is invalid")
    return dict(exit_code=code, signal=signal, reason=_reason(value.get("reason")))


def _metadata(value, namespace):
    metadata = _object(value.get("metadata"))
    _identity(metadata.get("name"), DNS)
    _identity(metadata.get("uid"), UID)
    if metadata.get("namespace") != namespace or metadata.get("deletionTimestamp"):
        raise ValueError("workload namespace differs or deletion is pending")
    return metadata


def _job_state(value, namespace, name, uid, *, allow_active=False):
    if value is None:
        return "absent"
    metadata = _metadata(value, namespace)
    if value.get("kind") != "Job" or metadata["name"] != name or metadata["uid"] != uid:
        raise ValueError("Job identity differs from frozen binding")
    status = _object(value.get("status"))
    for field in ("active", "terminating"):
        if (type(status.get(field, 0)) is not int or status.get(field, 0) < 0
                or (status.get(field, 0) != 0 and not allow_active)):
            raise ValueError("Job is active or uncertain")
    conditions = status.get("conditions", [] if allow_active else None)
    if not isinstance(conditions, list) or any(not isinstance(c, dict) for c in conditions):
        raise ValueError("Job terminal conditions are unavailable")
    states = {c.get("type") for c in conditions if c.get("status") == "True"
              and c.get("type") in {"Complete", "Failed"}}
    if allow_active and not states:
        return "Active"  # Observation only, never permission to replace a Master.
    if any(status.get(field, 0) for field in ("active", "terminating")):
        raise ValueError("Job terminal condition conflicts with active count")
    if len(states) != 1:
        raise ValueError("Job is not unambiguously terminal")
    return states.pop()


def _terminated_pods(value, namespace, job_uid, *, diagnostics=None, allow_active=False):
    if (not isinstance(value, dict) or value.get("kind") not in {"List", "PodList"}
            or not isinstance(value.get("items"), list)
            or not isinstance(value.get("metadata"), dict)
            or value["metadata"].get("continue")
            or type(value['metadata'].get('remainingItemCount',0)) is not int
            or value['metadata'].get('remainingItemCount',0) != 0):
        raise ValueError("complete Pod inventory is unavailable")
    observed = {}
    for pod in value["items"]:
        pod = _object(pod)
        metadata = _metadata(pod, namespace)
        owners = metadata.get("ownerReferences")
        if not isinstance(owners, list) or any(not isinstance(o, dict) for o in owners):
            raise ValueError("Pod owner is unavailable")
        controllers = [o for o in owners if o.get("controller") is True]
        if (pod.get("kind") != "Pod" or job_uid is None or len(controllers) != 1
                or controllers[0].get("kind") != "Job" or controllers[0].get("uid") != job_uid
                or metadata["uid"] in observed):
            raise ValueError("Pod ownership differs or inventory is duplicated")
        status, spec = _object(pod.get("status")), _object(pod.get("spec"))
        if allow_active and status.get("phase") in {"Pending", "Running"}:
            if not isinstance(spec.get('containers'), list) or not spec['containers']:
                raise ValueError('active Pod container inventory is unavailable')
            observed[metadata['uid']] = None
            continue
        if status.get("phase") not in {"Succeeded", "Failed"}:
            raise ValueError("Pod is active or uncertain")
        exits, containers_observed = {}, []
        for names_key, states_key in (("containers", "containerStatuses"),
                ("initContainers", "initContainerStatuses"),
                ("ephemeralContainers", "ephemeralContainerStatuses")):
            containers, states = spec.get(names_key, []), status.get(states_key, [])
            if (not isinstance(containers, list) or not isinstance(states, list)
                    or any(not isinstance(c, dict) for c in containers + states)
                    or (names_key == "containers" and not containers)):
                raise ValueError("container inventory is unavailable")
            names = [c.get("name") for c in containers]
            actual_names = [c.get("name") for c in states]
            if (any(not isinstance(n, str) or not n for n in names + actual_names)
                    or len(set(names)) != len(names) or len(set(actual_names)) != len(actual_names)
                    or set(names) != set(actual_names)):
                raise ValueError("container state inventory is incomplete")
            for state in states:
                detail = _object(state.get("state"))
                terminated = _object(detail.get("terminated"))
                code = terminated.get("exitCode")
                if set(detail) != {"terminated"} or type(code) is not int or not 0 <= code <= 255:
                    raise ValueError("container is active or exit status is unknown")
                if names_key == "containers":
                    exits[state["name"]] = code
                if diagnostics is not None:
                    restarts = state.get("restartCount")
                    if restarts is not None and (type(restarts) is not int or restarts < 0):
                        raise ValueError("container restart evidence is invalid")
                    previous = _object(state.get("lastState", {}))
                    if previous and set(previous) != {"terminated"}:
                        raise ValueError("previous container termination is unknown")
                    containers_observed.append(dict(
                        kind={"containers": "main", "initContainers": "init",
                              "ephemeralContainers": "ephemeral"}[names_key],
                        name=state["name"], **_termination(terminated), restart_count=restarts,
                        previous_termination=_termination(previous["terminated"]) if previous else None))
        observed[metadata["uid"]] = exits
        if diagnostics is not None:
            diagnostics[metadata["uid"]] = dict(name=metadata["name"], phase=status["phase"],
                reason=_reason(status.get("reason")), containers=containers_observed)
    return observed


def probe_final_workloads(*, runtime, config, namespace, run_label, master_job,
                          master_job_uid, master_state, workers, timeout_seconds=120,
                          allow_active_workers=False):
    """Reconcile FINAL native inventory against full live lists and exact names.

    Absence only counts after a successful GET and requires a persisted exact
    Worker terminal. This read-only observation is not dispatch authorization.
    """
    for name in (namespace,run_label,master_job):_identity(name,DNS)
    _identity(master_job_uid,UID)
    if (master_state not in {'FAILED','SUCCEEDED'} or config.get('kubernetes',{}).get('namespace') != namespace
            or not isinstance(workers,list) or len(workers)>4096
            or type(timeout_seconds) is not int or not 0 < timeout_seconds <= 300):
        raise ValueError('invalid final workload binding')
    bound={master_job:{'uid':master_job_uid,'terminal_state':master_state}}
    for worker in workers:
        worker=_object(worker)
        _identity(worker.get('name'),DNS)
        if worker.get('uid') is not None:_identity(worker['uid'],UID)
        if (worker['name'] in bound or 'uid' not in worker or worker.get('namespace') != namespace
                or worker.get('terminal_state') not in {None,'SUCCEEDED','FAILED'}):
            raise ValueError('inconsistent final Worker inventory')
        bound[worker['name']]=worker
    deadline=time.monotonic()+timeout_seconds
    def query(*args):
        if time.monotonic() >= deadline:raise ValueError('workload query budget exhausted')
        return runtime._recovery_query(config,*args)
    def full_list(value,kind):
        if (not isinstance(value,dict) or value.get('kind') not in {'List',kind+'List'}
                or not isinstance(value.get('items'),list) or not isinstance(value.get('metadata'),dict)
                or value['metadata'].get('continue')
                or type(value['metadata'].get('remainingItemCount',0)) is not int
                or value['metadata'].get('remainingItemCount',0)!=0):
            raise ValueError('complete live inventory is unavailable')
        return value['items']
    listed={}
    for item in full_list(query('jobs','-l','cce.biosan.cn/run-id='+run_label,'--chunk-size=0'),'Job'):
        metadata=_metadata(_object(item),namespace)
        name=metadata['name']
        if (item.get('kind')!='Job' or name not in bound or name in listed
                or metadata['uid']!=bound[name]['uid']
                or metadata.get('labels',{}).get('cce.biosan.cn/run-id')!=run_label):
            raise ValueError('unbound live Job exists')
        listed[name]=metadata['uid']
    grouped={name:[] for name in bound}
    for item in full_list(query('pods','-l','cce.biosan.cn/run-id='+run_label,'--chunk-size=0'),'Pod'):
        metadata=_metadata(_object(item),namespace)
        owners=metadata.get('ownerReferences')
        if not isinstance(owners,list) or any(not isinstance(o,dict) for o in owners):
            raise ValueError('unbound live Pod exists')
        owners=[o for o in owners if o.get('controller') is True]
        if (len(owners)!=1 or owners[0].get('kind')!='Job' or owners[0].get('name') not in bound
                or owners[0].get('uid')!=bound[owners[0]['name']]['uid']):
            raise ValueError('unbound live Pod exists')
        grouped[owners[0]['name']].append(item)
    observations=[]
    master=None
    for name,worker in bound.items():
        job=query('job',name)
        allow_active = allow_active_workers and name != master_job
        state=_job_state(job,namespace,name,worker['uid'],allow_active=allow_active)
        if (job is not None and (name not in listed
                or job['metadata'].get('labels',{}).get('cce.biosan.cn/run-id')!=run_label)):
            raise ValueError('Job differs from complete live inventory; recheck required')
        if job is None and name in listed:raise ValueError('Job inventory changed; recheck required')
        listed_pods=_terminated_pods({'kind':'PodList','metadata':{},'items':grouped[name]},namespace,worker['uid'],allow_active=allow_active)
        pods=_terminated_pods(query('pods','-l','job-name='+name,'--chunk-size=0'),namespace,worker['uid'],allow_active=allow_active)
        if listed_pods != pods:raise ValueError('Pod inventory changed or run label differs')
        expected=worker.get('terminal_state')
        if state=='absent':
            if pods or (worker['uid'] is not None and expected is None):
                raise ValueError('reclaimed workload lacks terminal proof or still owns Pods')
        elif expected is not None and state != ('Complete' if expected=='SUCCEEDED' else 'Failed'):
            raise ValueError('live and persisted terminal states conflict')
        if name==master_job:master=job
        else:observations.append({'name':name,'uid':worker['uid'],'job_state':state,'pods':len(pods),
            **({'active_pods':sum(v is None for v in pods.values())} if allow_active_workers else {})})
    active_jobs=sum(w['job_state']=='Active' for w in observations)
    active_pods=sum(w.get('active_pods',0) for w in observations)
    return {'master':master,'master_state':master_state,'workers':observations,
        'workers_inactive':not (active_jobs or active_pods),
        **({'active_worker_jobs':active_jobs,'active_worker_pods':active_pods} if allow_active_workers else {})}


def probe_bound_workloads(*, runtime, config, namespace, master_job,
                          master_job_uid, master_pod_uid, workers, timeout_seconds=120):
    """Return only live observations for supplied identities, or fail closed."""
    for value in (namespace, master_job):
        _identity(value, DNS)
    for value in (master_job_uid, master_pod_uid):
        _identity(value, UID)
    if config.get("kubernetes", {}).get("namespace") != namespace:
        raise ValueError("configured namespace differs from frozen binding")
    if type(timeout_seconds) is not int or not 0 < timeout_seconds <= 300:
        raise ValueError("invalid workload query budget")
    if not isinstance(workers, list) or len(workers) > 4096:
        raise ValueError("invalid bound Worker inventory")
    names = {master_job}
    bound = []
    for worker in workers:
        worker = _object(worker)
        name, uid = worker.get("name"), worker.get("uid")
        _identity(name, DNS)
        if "uid" not in worker or name in names:
            raise ValueError("missing or repeated bound Worker identity")
        if uid is not None:
            _identity(uid, UID)
        names.add(name)
        bound.append((name, uid))
    deadline = time.monotonic() + timeout_seconds

    def query(kind, name):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError("workload query budget exhausted")
        arguments = (["get", "job", name, "--ignore-not-found", "-o", "json"] if kind == "job"
            else ["get", "pods", "-l", "job-name=" + name, "--chunk-size=0", "-o", "json"])
        try:
            result = subprocess.run(runtime._kubectl(config, *arguments), capture_output=True,
                text=True, timeout=min(30, remaining), check=False)
            if result.returncode:
                raise ValueError("workload query failed")
            if kind == "job" and not result.stdout.strip():
                return None  # Successful exact-name --ignore-not-found, not a transport error.
            if len(result.stdout) > 4 * 1024 * 1024:
                raise ValueError("workload response exceeds limit")
            return _object(json.loads(result.stdout, object_pairs_hook=_unique_json))
        except (OSError, subprocess.SubprocessError, ValueError, TypeError):
            raise ValueError("workload query unavailable or invalid") from None

    master = query("job", master_job)
    if _job_state(master, namespace, master_job, master_job_uid) != "Failed":
        raise ValueError("bound Master is not a terminal failed Job")
    failed_conditions = [c for c in master["status"]["conditions"]
                         if c.get("type") == "Failed" and c.get("status") == "True"]
    if len(failed_conditions) != 1:
        raise ValueError("Master failure condition is ambiguous")
    master_pods = {}
    pods = _terminated_pods(query("pods", master_job), namespace, master_job_uid,
                            diagnostics=master_pods)
    if master_pod_uid not in pods:
        raise ValueError("bound Master Pod terminal state is unavailable")
    observations = []
    for name, uid in bound:
        state = _job_state(query("job", name), namespace, name, uid)
        pods_for_job = _terminated_pods(query("pods", name), namespace, uid)
        observations.append(dict(name=name, uid=uid, job_state=state, pods=len(pods_for_job)))
    return dict(master_job_uid=master_job_uid, master_pod_uid=master_pod_uid,
        master_container_exit_codes=pods[master_pod_uid], workers=observations,
        master_job_condition=dict(type="Failed", reason=_reason(failed_conditions[0].get("reason"))),
        master_pods=master_pods)
