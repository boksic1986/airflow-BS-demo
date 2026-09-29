#!/usr/bin/env python3
"""Run frozen GATK Step4/5 after a successful Master Job was TTL-reclaimed.

This restricted entrypoint does not replace the Master or infer success from
Airflow state. The frozen runtime must prove native success for the original
Master UID before either downstream stage is invoked.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

import yaml

import gatk_runtime_gate as gate


STAGES = {"step4_publish", "step5_download"}
NAME = re.compile(r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?")
RUN_LABEL = re.compile(r"cce-run-[0-9a-f]{16}")


class DownstreamGuardError(RuntimeError):
    """A fixed, privacy-safe refusal to run a downstream stage."""


def _frozen_runtime(bundle: Path) -> Any:
    source = bundle / "cce_batch_runtime.py"
    if source.is_symlink() or not source.is_file():
        raise DownstreamGuardError("frozen GATK runtime is unavailable")
    spec = importlib.util.spec_from_file_location("gatk_frozen_downstream_runtime", source)
    if spec is None or spec.loader is None:
        raise DownstreamGuardError("frozen GATK runtime cannot be loaded")
    runtime = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runtime
    try:
        spec.loader.exec_module(runtime)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return runtime


def _plain_stage(bundle: Path, stage: str) -> None:
    script = bundle / gate.STAGE_SCRIPTS[stage]
    if script.is_symlink() or not script.is_file():
        raise DownstreamGuardError("frozen GATK stage script is unavailable")
    subprocess.run(["bash", str(script)], check=True)


def _inventory_is_terminal(
    runtime: Any, config: dict[str, Any], run_label: str, run_id: str
) -> None:
    for label_key, value in (
        ("cce.biosan.cn/run-id", run_label),
        ("cce-pipeline/run-id", run_id),
    ):
        selector = f"{label_key}={value}"
        for kind in ("jobs", "pods"):
            if label_key == "cce.biosan.cn/run-id":
                listing = runtime._recovery_query(config, kind, "-l", selector, "--chunk-size=0")
            else:
                listing = runtime._kubectl_json(
                    config, kind, "-l", selector, "--chunk-size=0", timeout=30
                )
            metadata = listing.get("metadata") if isinstance(listing, dict) else None
            if (
                not isinstance(listing, dict)
                or listing.get("kind") not in {"List", "JobList" if kind == "jobs" else "PodList"}
                or not isinstance(metadata, dict)
                or metadata.get("continue")
                or type(metadata.get("remainingItemCount", 0)) is not int
                or metadata.get("remainingItemCount", 0) != 0
                or not isinstance(listing.get("items"), list)
            ):
                raise DownstreamGuardError("GATK run inventory is unavailable or incomplete")
            for item in listing["items"]:
                if not isinstance(item, dict):
                    raise DownstreamGuardError("GATK run inventory is invalid")
                item_meta = item.get("metadata") or {}
                status = item.get("status") or {}
                if not isinstance(item_meta, dict) or not isinstance(status, dict):
                    raise DownstreamGuardError("GATK run inventory is invalid")
                if (
                    not item_meta.get("uid")
                    or item_meta.get("namespace") != config["kubernetes"]["namespace"]
                    or (item_meta.get("labels") or {}).get(label_key) != value
                ):
                    raise DownstreamGuardError("GATK run inventory identity changed")
                if item_meta.get("deletionTimestamp"):
                    raise DownstreamGuardError("GATK run has a terminating workload")
                if kind == "pods":
                    if status.get("phase") not in {"Succeeded", "Failed"}:
                        raise DownstreamGuardError("GATK run has an active Pod")
                else:
                    conditions = status.get("conditions") or []
                    terminal = any(
                        isinstance(condition, dict)
                        and condition.get("status") == "True"
                        and condition.get("type") in {"Complete", "Failed"}
                        for condition in conditions
                    )
                    if int(status.get("active") or 0) or not terminal:
                        raise DownstreamGuardError("GATK run has an active or unknown Job")


def _batch_lock_owned(
    runtime: Any, config: dict[str, Any], contract: dict[str, Any]
) -> None:
    identity = contract["identity"]
    lock = runtime._recovery_query(config, "configmap", runtime._batch_lock_name(contract))
    if not isinstance(lock, dict) or lock.get("data") != {
        "project": str(identity["project"]),
        "batch": str(identity["batch"]),
        "run_id": str(identity["run_id"]),
    }:
        raise DownstreamGuardError("GATK batch lock no longer belongs to this run")


def _delete_own_reader(runtime: Any, config: dict[str, Any], name: str, uid: str) -> None:
    current = runtime._recovery_query(config, "job", name)
    if current is None:
        return
    if (current.get("metadata") or {}).get("uid") != uid:
        raise DownstreamGuardError("GATK evidence reader identity changed")
    namespace = str(config["kubernetes"]["namespace"])
    if not NAME.fullmatch(namespace) or not NAME.fullmatch(name):
        raise DownstreamGuardError("GATK evidence reader name is unsafe")
    options = {
        "apiVersion": "v1",
        "kind": "DeleteOptions",
        "propagationPolicy": "Foreground",
        "preconditions": {"uid": uid},
    }
    path = f"/apis/batch/v1/namespaces/{namespace}/jobs/{name}"
    result = runtime._run(
        runtime._kubectl(config, "delete", "--raw", path, "-f", "-"),
        check=False,
        capture=True,
        timeout=30,
        input_bytes=json.dumps(options, sort_keys=True).encode("utf-8"),
    )
    if result.returncode:
        raise DownstreamGuardError("GATK evidence reader cleanup failed")
    deadline = time.monotonic() + 30
    while True:
        current = runtime._recovery_query(config, "job", name)
        if current is None:
            return
        if (current.get("metadata") or {}).get("uid") != uid:
            raise DownstreamGuardError("GATK evidence reader identity changed")
        if time.monotonic() >= deadline:
            raise DownstreamGuardError("GATK evidence reader deletion is unconfirmed")
        time.sleep(2)


def _reader_document(
    runtime: Any, bundle: Path, contract: dict[str, Any],
    stage: str, generation: int, request_hash: str,
) -> dict[str, Any]:
    reader = runtime._reader_job(bundle, contract)
    run_id = str(contract["identity"]["run_id"])
    digest = hashlib.sha256(
        f"{run_id}/{stage}/{generation}/{request_hash}".encode("utf-8")
    ).hexdigest()[:24]
    name = "cce-evidence-" + digest
    metadata = reader["metadata"]
    metadata["name"] = name
    metadata.setdefault("labels", {})["app.kubernetes.io/name"] = name
    metadata.setdefault("annotations", {}).update({
        "cce-pipeline/action": "evidence-reader",
        "cce-pipeline/downstream-stage": stage,
        "cce-pipeline/downstream-generation": str(generation),
        "cce-pipeline/downstream-request-hash": request_hash,
    })
    template = reader["spec"]["template"]
    template.setdefault("metadata", {}).setdefault("labels", {})[
        "app.kubernetes.io/name"
    ] = name
    pod_spec = template["spec"]
    containers = pod_spec.get("containers")
    if (not isinstance(containers, list) or len(containers) != 1
            or pod_spec.get("initContainers") or pod_spec.get("ephemeralContainers")):
        raise DownstreamGuardError("GATK evidence reader has unexpected containers")
    container = containers[0]
    volumes = {item.get("name"): item for item in pod_spec.get("volumes", [])}
    selected_mounts = []
    selected_volumes = []
    for path in ("/workspace", "/tmp"):
        matches = [item for item in container.get("volumeMounts", [])
                   if item.get("mountPath") == path]
        if len(matches) != 1 and (path == "/workspace" or matches):
            raise DownstreamGuardError("GATK evidence reader workspace mount is invalid")
        if not matches:
            continue
        mount = matches[0]
        volume = volumes.get(mount.get("name"))
        if not isinstance(volume, dict):
            raise DownstreamGuardError("GATK evidence reader volume is unavailable")
        if path == "/workspace":
            pvc = volume.get("persistentVolumeClaim")
            if not isinstance(pvc, dict) or not pvc.get("claimName"):
                raise DownstreamGuardError("GATK evidence reader has no SFS PVC")
            pvc["readOnly"] = True
            mount["readOnly"] = True
        elif not isinstance(volume.get("emptyDir"), dict):
            raise DownstreamGuardError("GATK evidence reader tmp must be emptyDir")
        selected_mounts.append(mount)
        selected_volumes.append(volume)
    container["volumeMounts"] = selected_mounts
    container.pop("env", None)
    container.pop("envFrom", None)
    pod_spec["volumes"] = selected_volumes
    pod_spec.pop("serviceAccountName", None)
    pod_spec["automountServiceAccountToken"] = False
    return reader


def _reader_uid(job: Any, reader: dict[str, Any], namespace: str) -> str:
    metadata = job.get("metadata") if isinstance(job, dict) else None
    expected = reader["metadata"]
    if (
        not isinstance(metadata, dict)
        or metadata.get("name") != expected["name"]
        or metadata.get("namespace", namespace) != namespace
        or metadata.get("deletionTimestamp")
        or not metadata.get("uid")
        or any((metadata.get("labels") or {}).get(key) != value
               for key, value in (expected.get("labels") or {}).items())
        or any((metadata.get("annotations") or {}).get(key) != value
               for key, value in (expected.get("annotations") or {}).items())
    ):
        raise DownstreamGuardError("GATK evidence reader identity is unverified")
    spec = job.get("spec") or {}
    expected_spec = reader["spec"]
    observed_pod = (spec.get("template") or {}).get("spec") or {}
    expected_pod = expected_spec["template"]["spec"]
    observed_containers = observed_pod.get("containers") or []
    expected_container = expected_pod["containers"][0]
    if (
        spec.get("activeDeadlineSeconds") != expected_spec.get("activeDeadlineSeconds")
        or spec.get("ttlSecondsAfterFinished") != expected_spec.get("ttlSecondsAfterFinished")
        or observed_pod.get("automountServiceAccountToken") is not False
        or observed_pod.get("initContainers")
        or observed_pod.get("ephemeralContainers")
        or len(observed_containers) != 1
        or observed_containers[0].get("image") != expected_container.get("image")
        or observed_containers[0].get("command") != expected_container.get("command")
        or observed_containers[0].get("volumeMounts") != expected_container.get("volumeMounts")
        or observed_pod.get("volumes") != expected_pod.get("volumes")
    ):
        raise DownstreamGuardError("GATK evidence reader specification changed")
    return str(metadata["uid"])


def _read_native_terminal(
    runtime: Any, bundle: Path, contract: dict[str, Any], config: dict[str, Any], uid: str,
    stage: str, generation: int, request_hash: str,
) -> None:
    identity = contract["identity"]
    run_id = str(identity["run_id"])
    mirror = bundle / "evidence" / run_id / "mirror"
    terminal_path = mirror / "RUN_COMPLETE.json"
    if terminal_path.is_symlink():
        raise DownstreamGuardError("GATK native terminal evidence is unsafe")
    if (mirror / "RUN_FAILED.json").exists() or (mirror / "RUN_FAILED.json").is_symlink():
        raise DownstreamGuardError("GATK native failure evidence is present")
    if not terminal_path.is_file():
        reader = _reader_document(runtime, bundle, contract, stage, generation, request_hash)
        name = str(reader["metadata"]["name"])
        namespace = str(config["kubernetes"]["namespace"])
        created_uid = None
        try:
            current = runtime._recovery_query(config, "job", name)
            if current is None:
                try:
                    runtime._create_job_from_document(config, reader)
                except Exception:
                    # A lost create response may mean the Job exists. Query this
                    # same identity once; never submit a new name or retry create.
                    pass
                current = runtime._recovery_query(config, "job", name)
            created_uid = _reader_uid(current, reader, namespace)
            pod = runtime._wait_pod(config, name, created_uid)
            evidence_dir = f"{contract['paths']['run_dir']}/evidence/{run_id}"
            evidence, error = runtime._read_pod_evidence(
                config,
                pod,
                evidence_dir,
                completion_specs=runtime._workflow_completion_specs(contract),
                include_jobs=False,
                timeout=60,
            )
            terminal = evidence.get("RUN_COMPLETE.json") if isinstance(evidence, dict) else None
            exits = terminal.get("exit_codes") if isinstance(terminal, dict) else None
            if (
                error
                or not isinstance(terminal, dict)
                or terminal.get("job_uid") != uid
                or terminal.get("state") != "SUCCEEDED"
                or not isinstance(exits, dict)
                or any(type(exits.get(key)) is not int or exits[key] != 0
                       for key in ("preflight", "analysis", "final_dryrun"))
                or not isinstance(evidence.get("_files_present"), list)
                or "RUN_FAILED.json" in evidence["_files_present"]
                or evidence.get("RUN_FAILED.json") is not None
                or not isinstance(evidence.get("START_CONFIRMED.json"), dict)
                or evidence["START_CONFIRMED.json"].get("job_uid") != uid
                or not isinstance(evidence.get("workflow-completion.json"), dict)
            ):
                raise DownstreamGuardError("GATK SFS has no verified native success")
            if not runtime._write_mirror_evidence(
                bundle, run_id, evidence,
                project=str(identity["project"]), batch=str(identity["batch"]),
            ):
                raise DownstreamGuardError("GATK native evidence mirror was not written")
        finally:
            if created_uid is not None:
                _delete_own_reader(runtime, config, name, created_uid)
    native = runtime._recovery_native_success(bundle, contract, uid)
    if not isinstance(native, dict) or native.get("job_uid") != uid or native.get("state") != "SUCCEEDED":
        raise DownstreamGuardError("GATK native workflow success is unverified")


def run_stage(
    analysis_id: str, attempt: int, stage: str, generation: int, request_hash: str
) -> None:
    if stage not in STAGES or not re.fullmatch(r"[0-9a-f]{64}", request_hash):
        raise DownstreamGuardError("invalid GATK downstream request")
    _, payload = gate._load(analysis_id, attempt, stage, generation)
    if payload.get("request_hash") != request_hash:
        raise DownstreamGuardError("GATK downstream request hash changed")
    canonical_request = {key: value for key, value in payload.items() if key != "request_hash"}
    actual_hash = hashlib.sha256(
        json.dumps(canonical_request, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if actual_hash != request_hash:
        raise DownstreamGuardError("GATK downstream request body changed")
    bundle = gate._bundle(payload)
    binding = gate._load_binding(payload)
    run_id = f"{analysis_id}-a{attempt}"
    if binding.get("run_id") != run_id or binding.get("cce_bundle") != str(bundle):
        raise DownstreamGuardError("GATK downstream bundle identity changed")
    manifest = yaml.safe_load((bundle / "master-job.yaml").read_text(encoding="utf-8"))
    contract = yaml.safe_load((bundle / "BATCH_RUNTIME.yaml").read_text(encoding="utf-8"))
    metadata = manifest.get("metadata") if isinstance(manifest, dict) else None
    identity = contract.get("identity") if isinstance(contract, dict) else None
    kubernetes = contract.get("kubernetes") if isinstance(contract, dict) else None
    if (not isinstance(metadata, dict) or not isinstance(identity, dict)
            or not isinstance(kubernetes, dict) or identity.get("run_id") != run_id
            or kubernetes.get("namespace") != binding.get("namespace")
            or kubernetes.get("master_job") != binding.get("master_job")
            or metadata.get("name") != binding.get("master_job")
            or metadata.get("namespace", binding.get("namespace")) != binding.get("namespace")
            or (metadata.get("labels") or {}).get("cce.biosan.cn/run-id") != binding.get("run_label")
            or RUN_LABEL.fullmatch(str(binding.get("run_label") or "")) is None):
        raise DownstreamGuardError("GATK downstream frozen identity changed")
    annotations = metadata.get("annotations") or {}
    if annotations.get("cce-pipeline/handoff-version") != "2":
        # Legacy bundles retain their original live-Job-only behavior.
        _plain_stage(bundle, stage)
        return
    runtime = _frozen_runtime(bundle)
    native_contract, config, modules = runtime._load(bundle, None)
    if native_contract != contract or config["kubernetes"]["namespace"] != binding["namespace"]:
        raise DownstreamGuardError("GATK downstream runtime contract changed")
    # Match the frozen CLI's protection decision. The legacy absent-Job path
    # is valid only where no paired deployment writer owns the bundle.
    if runtime.writer_for_bundle(runtime, bundle, contract, config) is not None:
        raise DownstreamGuardError("GATK protected downstream requires its native writer")
    handoff = runtime._read_master_handoff(bundle, contract)
    frozen_binding = runtime._handoff_binding(bundle, contract)
    uid = str((handoff or {}).get("job_uid") or "")
    if (
        not isinstance(handoff, dict)
        or handoff.get("schema_version") != 2
        or handoff.get("run_id") != run_id
        or handoff.get("job_name") != binding["master_job"]
        or not uid
        or not handoff.get("pod_uid")
        or any(handoff.get(key) != frozen_binding.get(key)
               for key in ("attempt", "execution_generation", "request_hash",
                           "config_sha256", "manifest_sha256", "files_sha256"))
    ):
        raise DownstreamGuardError("GATK original Master handoff is unverified")
    master = runtime._recovery_query(config, "job", binding["master_job"])
    if master is not None:
        active, complete, failed = runtime._job_flags(master)
        if (master.get("metadata") or {}).get("uid") != uid or active or not complete or failed:
            raise DownstreamGuardError("GATK live Master conflicts with frozen handoff")
        _plain_stage(bundle, stage)
        return
    _batch_lock_owned(runtime, config, contract)
    _inventory_is_terminal(runtime, config, str(binding["run_label"]), run_id)
    _read_native_terminal(
        runtime, bundle, contract, config, uid,
        stage, generation, request_hash,
    )
    _batch_lock_owned(runtime, config, contract)
    _inventory_is_terminal(runtime, config, str(binding["run_label"]), run_id)
    if runtime._recovery_query(config, "job", binding["master_job"]) is not None:
        raise DownstreamGuardError("GATK Master identity changed before downstream")
    if stage == "step4_publish":
        runtime.step4(
            bundle, contract, config, modules,
            args=argparse.Namespace(repair_linkage_group=None, confirm=None,
                                    publish_timeout_seconds=7200, publish_poll_seconds=30),
            master_bundle=bundle, expected_master_uid=uid,
        )
    else:
        runtime.step5(
            argparse.Namespace(verify_existing=False, logs_only=False),
            bundle, contract, config, modules,
            master_bundle=bundle, expected_master_uid=uid,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis_id")
    parser.add_argument("attempt", type=int)
    parser.add_argument("stage", choices=sorted(STAGES))
    parser.add_argument("generation", type=int)
    parser.add_argument("request_hash")
    args = parser.parse_args()
    try:
        run_stage(args.analysis_id, args.attempt, args.stage, args.generation, args.request_hash)
    except DownstreamGuardError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
    except Exception as error:
        message = str(error)
        if args.stage == "step4_publish" and gate.STEP4_EXPORT_PENDING in message:
            print(gate.STEP4_EXPORT_PENDING, file=sys.stderr)
        else:
            print(f"GATK downstream failed: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
