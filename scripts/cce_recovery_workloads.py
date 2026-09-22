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


def _metadata(value, namespace):
    metadata = _object(value.get("metadata"))
    _identity(metadata.get("name"), DNS)
    _identity(metadata.get("uid"), UID)
    if metadata.get("namespace") != namespace or metadata.get("deletionTimestamp"):
        raise ValueError("workload namespace differs or deletion is pending")
    return metadata


def _job_state(value, namespace, name, uid):
    if value is None:
        return "absent"
    metadata = _metadata(value, namespace)
    if value.get("kind") != "Job" or metadata["name"] != name or metadata["uid"] != uid:
        raise ValueError("Job identity differs from frozen binding")
    status = _object(value.get("status"))
    for field in ("active", "terminating"):
        if type(status.get(field, 0)) is not int or status.get(field, 0) != 0:
            raise ValueError("Job is active or uncertain")
    conditions = status.get("conditions")
    if not isinstance(conditions, list) or any(not isinstance(c, dict) for c in conditions):
        raise ValueError("Job terminal conditions are unavailable")
    states = {c.get("type") for c in conditions if c.get("status") == "True"
              and c.get("type") in {"Complete", "Failed"}}
    if len(states) != 1:
        raise ValueError("Job is not unambiguously terminal")
    return states.pop()


def _terminated_pods(value, namespace, job_uid):
    if (not isinstance(value, dict) or value.get("kind") not in {"List", "PodList"}
            or not isinstance(value.get("items"), list)
            or not isinstance(value.get("metadata"), dict)
            or value["metadata"].get("continue")):
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
        if status.get("phase") not in {"Succeeded", "Failed"}:
            raise ValueError("Pod is active or uncertain")
        exits = {}
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
        observed[metadata["uid"]] = exits
    return observed


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
    pods = _terminated_pods(query("pods", master_job), namespace, master_job_uid)
    if master_pod_uid not in pods:
        raise ValueError("bound Master Pod terminal state is unavailable")
    observations = []
    for name, uid in bound:
        state = _job_state(query("job", name), namespace, name, uid)
        pods_for_job = _terminated_pods(query("pods", name), namespace, uid)
        observations.append(dict(name=name, uid=uid, job_state=state, pods=len(pods_for_job)))
    return dict(master_job_uid=master_job_uid, master_pod_uid=master_pod_uid,
        master_container_exit_codes=pods[master_pod_uid], workers=observations)
