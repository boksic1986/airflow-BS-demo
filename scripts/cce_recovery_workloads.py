"""Read-only UID-bound Kubernetes observations for the P0 terminal writer.

Inputs MUST come from frozen Master binding and the complete validated submission
journal/Worker manifest, not a browser or an arbitrary list inferred from logs.
This probe cannot prove that list's completeness or classify workflow failures.
It does not issue a seal, authorize resume, delete workloads, or change status.
Queries are observations, not an atomic cluster transaction: recheck at dispatch.
"""
import math
import re
import time


DNS = re.compile(r"[a-z0-9](?:[-a-z0-9.]{0,251}[a-z0-9])?\Z")
UID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
REASONS = frozenset({"BackoffLimitExceeded", "DeadlineExceeded", "PodFailurePolicy",
    "FailedIndexes", "MaxFailedIndexesExceeded", "CompletionsReached", "SuccessPolicy",
    "OOMKilled", "Error", "Completed", "ContainerCannotRun", "StartError",
    "Evicted", "NodeLost", "UnexpectedAdmissionError", "Shutdown"})


class InventoryMoved(ValueError):
    """Separately valid, bound observations changed between read-only queries."""


def _identity(value, pattern):
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError("invalid frozen workload identity")


def _object(value):
    if not isinstance(value, dict):
        raise ValueError("invalid workload object")
    return value


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


def _complete_list(value, kind):
    if (not isinstance(value, dict) or value.get("kind") not in {"List", kind + "List"}
            or not isinstance(value.get("items"), list)
            or not isinstance(value.get("metadata"), dict)
            or value["metadata"].get("continue")
            or type(value["metadata"].get("remainingItemCount", 0)) is not int
            or value["metadata"].get("remainingItemCount", 0) != 0):
        raise ValueError("complete live inventory is unavailable")
    return value["items"]


def _live_inventory(*, runtime, config, namespace, run_label, bound, master_job,
                    timeout_seconds, allow_active_workers=False,
                    query_deadline_monotonic=None, reconnect_transient=False,
                    allow_active_master=False, forbidden_uids=()):
    """One native-query inventory round, shared by recovery and final release.

    The namespace lists detect bound objects with changed labels. The run-label
    lists detect additional objects claiming this run. Neither a 404 nor a
    single label list alone proves that a reclaimed Worker is gone.
    """
    deadline = time.monotonic() + timeout_seconds
    if query_deadline_monotonic is not None:
        deadline = min(deadline, query_deadline_monotonic)

    def query(*arguments):
        delay = 2
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("workload query budget exhausted")
            try:
                value = runtime._recovery_query(config, *arguments, timeout=min(30, remaining))
            except runtime.RecoveryQueryError as error:
                if not reconnect_transient or error.code not in {'TRANSPORT', 'SERVICE'}:
                    raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError("workload query budget exhausted") from error
                time.sleep(min(delay, remaining))
                delay = 5
                continue
            if time.monotonic() >= deadline:
                raise ValueError("workload query budget exhausted")
            return value

    selector = "cce.biosan.cn/run-id=" + run_label
    run_jobs = _complete_list(query("jobs", "-l", selector, "--chunk-size=0"), "Job")
    run_pods = _complete_list(query("pods", "-l", selector, "--chunk-size=0"), "Pod")
    all_jobs = _complete_list(query("jobs", "--chunk-size=0"), "Job")
    all_pods = _complete_list(query("pods", "--chunk-size=0"), "Pod")
    exact_master = query("job", master_job)
    bound_uids = {record["uid"] for record in bound.values() if record["uid"] is not None}

    def indexed_jobs(items, *, selected):
        indexed = {}
        for item in items:
            item = _object(item)
            metadata = _object(item.get("metadata"))
            name, uid = metadata.get("name"), metadata.get("uid")
            _identity(name, DNS)
            _identity(uid, UID)
            if item.get("kind") != "Job" or metadata.get("namespace") != namespace:
                raise ValueError("namespace Job inventory is malformed")
            if uid in forbidden_uids:
                raise ValueError("forbidden old Master UID remains in live Job inventory")
            labels = metadata.get("labels", {})
            if not isinstance(labels, dict):
                raise ValueError("Job labels are invalid")
            owners = metadata.get("ownerReferences", [])
            if not isinstance(owners, list) or any(not isinstance(o, dict) for o in owners):
                raise ValueError("Job owner references are invalid")
            related = (name in bound or uid in bound_uids
                       or labels.get("cce.biosan.cn/run-id") == run_label
                       or any(o.get("name") in bound or o.get("uid") in bound_uids
                              for o in owners))
            if not related and not selected:
                continue
            if (item.get("kind") != "Job" or name not in bound
                    or uid != bound[name]["uid"]
                    or labels.get("cce.biosan.cn/run-id") != run_label
                    or name in indexed):
                raise ValueError("unbound or conflicting live Job exists")
            _metadata(item, namespace)
            indexed[name] = item
        return indexed

    def indexed_pods(items, *, selected):
        grouped = {name: [] for name in bound}
        seen_uids = set()
        for item in items:
            item = _object(item)
            metadata = _object(item.get("metadata"))
            _identity(metadata.get("name"), DNS)
            uid = metadata.get("uid")
            _identity(uid, UID)
            if item.get("kind") != "Pod" or metadata.get("namespace") != namespace:
                raise ValueError("namespace Pod inventory is malformed")
            labels = metadata.get("labels", {})
            if not isinstance(labels, dict):
                raise ValueError("Pod labels are invalid")
            owners = metadata.get("ownerReferences", [])
            if not isinstance(owners, list) or any(not isinstance(o, dict) for o in owners):
                raise ValueError("Pod owner references are invalid")
            if any(owner.get("uid") in forbidden_uids for owner in owners):
                raise ValueError("forbidden old Master UID remains in live Pod inventory")
            controllers = [o for o in owners if o.get("controller") is True]
            related = (labels.get("cce.biosan.cn/run-id") == run_label
                       or labels.get("job-name") in bound
                       or any(o.get("name") in bound or o.get("uid") in bound_uids
                              for o in owners))
            if not related and not selected:
                continue
            if (item.get("kind") != "Pod" or len(controllers) != 1
                    or controllers[0].get("kind") != "Job"
                    or controllers[0].get("name") not in bound
                    or controllers[0].get("uid") != bound[controllers[0]["name"]]["uid"]
                    or labels.get("cce.biosan.cn/run-id") != run_label
                    or labels.get("job-name", controllers[0]["name"]) != controllers[0]["name"]
                    or uid in seen_uids):
                raise ValueError("unbound or conflicting live Pod exists")
            _metadata(item, namespace)
            seen_uids.add(uid)
            grouped[controllers[0]["name"]].append(item)
        return grouped

    labelled_jobs = indexed_jobs(run_jobs, selected=True)
    namespace_jobs = indexed_jobs(all_jobs, selected=False)
    labelled_pods = indexed_pods(run_pods, selected=True)
    namespace_pods = indexed_pods(all_pods, selected=False)
    pod_states = {}
    for name, record in bound.items():
        labelled_job, namespace_job = labelled_jobs.get(name), namespace_jobs.get(name)
        if (labelled_job is None) != (namespace_job is None):
            raise InventoryMoved("bound Job changed between complete live inventories")
        allow_active = (allow_active_master if name == master_job else allow_active_workers)
        labelled_state = _job_state(labelled_job, namespace, name, record["uid"],
                                    allow_active=allow_active)
        namespace_state = _job_state(namespace_job, namespace, name, record["uid"],
                                     allow_active=allow_active)
        if labelled_state != namespace_state:
            if labelled_state in {"Complete", "Failed"}:
                raise ValueError("bound Job terminal evidence conflicts")
            raise InventoryMoved("bound Job changed between complete live inventories")
        if allow_active_master and name == master_job and labelled_job is not None:
            version = labelled_job["metadata"].get("resourceVersion")
            if (not isinstance(version, str) or not version
                    or version != namespace_job["metadata"].get("resourceVersion")):
                raise InventoryMoved("replacement Master version changed between complete live inventories")
        labelled_observed = _terminated_pods(
            {"kind": "PodList", "metadata": {}, "items": labelled_pods[name]},
            namespace, record["uid"], allow_active=allow_active)
        namespace_observed = _terminated_pods(
            {"kind": "PodList", "metadata": {}, "items": namespace_pods[name]},
            namespace, record["uid"], allow_active=allow_active)
        if labelled_observed != namespace_observed:
            if any(labelled_observed[uid] is not None
                   and labelled_observed[uid] != namespace_observed[uid]
                   for uid in set(labelled_observed) & set(namespace_observed)):
                raise ValueError("bound Pod terminal evidence conflicts")
            raise InventoryMoved("bound Pod changed between complete live inventories")
        pod_states[name] = namespace_observed
    namespace_master = namespace_jobs.get(master_job)
    if (exact_master is None) != (namespace_master is None):
        raise InventoryMoved("Master changed after complete live inventory")
    if exact_master is not None:
        exact_state = _job_state(exact_master, namespace, master_job,
                                 bound[master_job]["uid"], allow_active=allow_active_master)
        if exact_master.get("metadata", {}).get("labels", {}).get(
                "cce.biosan.cn/run-id") != run_label:
            raise ValueError("Master differs from complete live inventory")
        namespace_state = _job_state(namespace_master, namespace, master_job,
                                     bound[master_job]["uid"], allow_active=allow_active_master)
        if exact_state != namespace_state:
            raise ValueError("Master terminal evidence conflicts")
        if (allow_active_master and exact_master["metadata"].get("resourceVersion")
                != namespace_master["metadata"].get("resourceVersion")):
            raise InventoryMoved("replacement Master version changed after complete live inventory")
    return namespace_jobs, namespace_pods, pod_states, exact_master


def probe_initial_workloads(*, runtime, config, namespace, run_label, master_job,
                            master_job_uid, timeout_seconds=120, replacement_job=None):
    """Observe complete absence after native no-START proof was validated.

    Empty live inventories do not establish no-START or compute FINAL. The
    caller retains that separate native proof and rechecks before exact CAS.
    Even a terminal old Master or Pod is a residual object, not permission to
    replace it through this initial-submission branch. A created/submitting
    replay may observe only its separately verified replacement UID/version;
    STARTED recovery uses the existing selected observer instead.
    """
    for value in (namespace, run_label, master_job):
        _identity(value, DNS)
    _identity(master_job_uid, UID)
    if config.get("kubernetes", {}).get("namespace") != namespace:
        raise ValueError("configured namespace differs from frozen binding")
    if type(timeout_seconds) is not int or not 0 < timeout_seconds <= 120:
        raise ValueError("invalid workload query budget")
    selected_uid = master_job_uid
    if replacement_job is not None:
        replacement_job = _object(replacement_job)
        metadata = _metadata(replacement_job, namespace)
        labels = metadata.get("labels", {})
        version = metadata.get("resourceVersion")
        if (replacement_job.get("kind") != "Job" or metadata["name"] != master_job
                or metadata["uid"] == master_job_uid
                or not isinstance(labels, dict)
                or labels.get("cce.biosan.cn/run-id") != run_label
                or not isinstance(version, str) or not version):
            raise ValueError("replacement Master differs from verified binding")
        selected_uid = metadata["uid"]
    jobs, pods, _, master = _live_inventory(
        runtime=runtime, config=config, namespace=namespace, run_label=run_label,
        bound={master_job: {"uid": selected_uid}}, master_job=master_job,
        timeout_seconds=timeout_seconds, allow_active_master=replacement_job is not None,
        forbidden_uids=(master_job_uid,) if replacement_job is not None else ())
    if replacement_job is None:
        if master is not None or jobs or any(pods.values()):
            raise ValueError("initial submission workloads are not absent")
    elif master is None or master["metadata"].get("resourceVersion") != version:
        raise ValueError("replacement Master differs from verified version")
    return {"master": master, "master_state": "INITIAL_ABORTED", "workers": [],
            "workers_inactive": True}


def probe_final_workloads(*, runtime, config, namespace, run_label, master_job,
                          master_job_uid, master_state, workers, timeout_seconds=120,
                          allow_active_workers=False, query_deadline_monotonic=None,
                          reconnect_transient=False):
    """Reconcile FINAL native inventory against full live lists and exact names.

    Absence only counts after a successful GET and requires a persisted exact
    Worker terminal. This read-only observation is not dispatch authorization.
    """
    for name in (namespace,run_label,master_job):_identity(name,DNS)
    _identity(master_job_uid,UID)
    if (master_state not in {'FAILED','SUCCEEDED'} or config.get('kubernetes',{}).get('namespace') != namespace
            or not isinstance(workers,list) or len(workers)>4096
            or type(timeout_seconds) is not int or not 0 < timeout_seconds <= 120):
        raise ValueError('invalid final workload binding')
    if (query_deadline_monotonic is not None and
            (type(query_deadline_monotonic) not in {int, float}
             or not math.isfinite(query_deadline_monotonic))):
        raise ValueError('invalid final workload query deadline')
    bound={master_job:{'uid':master_job_uid,'terminal_state':master_state}}
    for worker in workers:
        worker=_object(worker)
        _identity(worker.get('name'),DNS)
        if worker.get('uid') is not None:_identity(worker['uid'],UID)
        if (worker['name'] in bound or 'uid' not in worker or worker.get('namespace') != namespace
                or worker.get('terminal_state') not in {None,'SUCCEEDED','FAILED'}):
            raise ValueError('inconsistent final Worker inventory')
        bound[worker['name']]=worker
    jobs, _, pods, master = _live_inventory(
        runtime=runtime, config=config, namespace=namespace, run_label=run_label,
        bound=bound, master_job=master_job, timeout_seconds=timeout_seconds,
        allow_active_workers=allow_active_workers,
        query_deadline_monotonic=query_deadline_monotonic,
        reconnect_transient=reconnect_transient)
    observations=[]
    for name,worker in bound.items():
        job=master if name==master_job else jobs.get(name)
        allow_active = allow_active_workers and name != master_job
        state=_job_state(job,namespace,name,worker['uid'],allow_active=allow_active)
        bound_pods=pods[name]
        expected=worker.get('terminal_state')
        if state=='absent':
            if bound_pods or (worker['uid'] is not None and expected is None):
                raise ValueError('reclaimed workload lacks terminal proof or still owns Pods')
        elif expected is not None and state != ('Complete' if expected=='SUCCEEDED' else 'Failed'):
            raise ValueError('live and persisted terminal states conflict')
        if name!=master_job:
            observations.append({'name':name,'uid':worker['uid'],'job_state':state,'pods':len(bound_pods),
                **({'active_pods':sum(v is None for v in bound_pods.values())}
                   if allow_active_workers else {})})
    active_jobs=sum(w['job_state']=='Active' for w in observations)
    active_pods=sum(w.get('active_pods',0) for w in observations)
    return {'master':master,'master_state':master_state,'workers':observations,
        'workers_inactive':not (active_jobs or active_pods),
        **({'active_worker_jobs':active_jobs,'active_worker_pods':active_pods} if allow_active_workers else {})}


def probe_bound_workloads(*, runtime, config, namespace, run_label, master_job,
                          master_job_uid, master_pod_uid, workers, timeout_seconds=120):
    """Return only live observations for supplied identities, or fail closed."""
    for value in (namespace, run_label, master_job):
        _identity(value, DNS)
    for value in (master_job_uid, master_pod_uid):
        _identity(value, UID)
    if config.get("kubernetes", {}).get("namespace") != namespace:
        raise ValueError("configured namespace differs from frozen binding")
    if type(timeout_seconds) is not int or not 0 < timeout_seconds <= 120:
        raise ValueError("invalid workload query budget")
    if not isinstance(workers, list) or len(workers) > 4096:
        raise ValueError("invalid bound Worker inventory")
    bound = {master_job: {"uid": master_job_uid}}
    for worker in workers:
        worker = _object(worker)
        name, uid = worker.get("name"), worker.get("uid")
        _identity(name, DNS)
        if "uid" not in worker or name in bound:
            raise ValueError("missing or repeated bound Worker identity")
        if uid is not None:
            _identity(uid, UID)
        bound[name] = {"uid": uid}
    jobs, pod_items, pod_states, master = _live_inventory(
        runtime=runtime, config=config, namespace=namespace, run_label=run_label,
        bound=bound, master_job=master_job, timeout_seconds=timeout_seconds)
    if _job_state(master, namespace, master_job, master_job_uid) != "Failed":
        raise ValueError("bound Master is not a terminal failed Job")
    failed_conditions = [c for c in master["status"]["conditions"]
                         if c.get("type") == "Failed" and c.get("status") == "True"]
    if len(failed_conditions) != 1:
        raise ValueError("Master failure condition is ambiguous")
    master_pods = {}
    pods = _terminated_pods(
        {"kind": "PodList", "metadata": {}, "items": pod_items[master_job]},
        namespace, master_job_uid, diagnostics=master_pods)
    if master_pod_uid not in pods:
        raise ValueError("bound Master Pod terminal state is unavailable")
    observations = []
    for name, worker in bound.items():
        if name != master_job:
            state = _job_state(jobs.get(name), namespace, name, worker["uid"])
            observations.append(dict(name=name, uid=worker["uid"], job_state=state,
                                     pods=len(pod_states[name])))
    return dict(master_job_uid=master_job_uid, master_pod_uid=master_pod_uid,
        master_container_exit_codes=pods[master_pod_uid], workers=observations,
        master_job_condition=dict(type="Failed", reason=_reason(failed_conditions[0].get("reason"))),
        master_pods=master_pods)
