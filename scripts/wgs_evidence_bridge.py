#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import yaml


SAFE_JSONL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,190}\.jsonl$")
MASTER_PYTHON = "/opt/python/3.11.9/bin/python3"
REMOTE_RULE_READER = r'''import base64,json,sys
from pathlib import Path
root=Path(sys.argv[1])
offsets=json.loads(sys.argv[2])
files=[]
if root.is_dir():
    for path in sorted(root.glob("*.jsonl")):
        if path.is_symlink() or not path.is_file():
            continue
        offset=int(offsets.get(path.name,0))
        size=path.stat().st_size
        if offset < 0 or size < offset:
            offset=0
        with path.open("rb") as handle:
            handle.seek(offset)
            data=handle.read()
        newline=data.rfind(b"\n")
        complete=data[:newline+1] if newline >= 0 else b""
        files.append({"name":path.name,"source_offset":offset,"next_offset":offset+len(complete),"data_base64":base64.b64encode(complete).decode("ascii")})
print(json.dumps({"files":files},sort_keys=True,separators=(",",":")))
'''


def _atomic_append(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _read_cursor(path: Path) -> dict[str, int]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for name, offset in value.items():
        if SAFE_JSONL_NAME.fullmatch(str(name)) and isinstance(offset, int) and offset >= 0:
            result[str(name)] = offset
    return result


def _apply_rule_chunks(
    output: Path, cursor_path: Path, chunks: list[dict]
) -> int:
    cursor = _read_cursor(cursor_path)
    total = 0
    raw_dir = output / "rule-status" / "raw"
    for chunk in chunks:
        name = str(chunk.get("name") or "")
        if SAFE_JSONL_NAME.fullmatch(name) is None:
            raise ValueError("remote Rule JSONL name is unsafe")
        source_offset = int(chunk.get("source_offset", -1))
        current_offset = cursor.get(name, 0)
        target = raw_dir / name
        if source_offset == 0 and current_offset != 0:
            current_offset = 0
            if target.exists():
                target.unlink()
        if source_offset != current_offset:
            raise ValueError("remote Rule JSONL offset does not match local cursor")
        try:
            data = base64.b64decode(str(chunk.get("data_base64") or ""), validate=True)
        except (ValueError, TypeError) as error:
            raise ValueError("remote Rule JSONL chunk is not valid base64") from error
        newline = data.rfind(b"\n")
        complete = data[: newline + 1] if newline >= 0 else b""
        next_offset = source_offset + len(complete)
        if int(chunk.get("next_offset", next_offset)) != next_offset:
            raise ValueError("remote Rule JSONL next offset is inconsistent")
        if complete:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("ab") as handle:
                handle.write(complete)
                handle.flush()
                os.fsync(handle.fileno())
            total += len(complete)
        cursor[name] = next_offset
    _atomic_json(cursor_path, cursor)
    return total


def pod_event(pod: dict, *, observed_at: str) -> dict:
    metadata = pod.get("metadata") or {}
    spec = pod.get("spec") or {}
    status = pod.get("status") or {}
    name = str(metadata.get("name") or "")
    version = str(metadata.get("resourceVersion") or "0")
    pod_hash = hashlib.sha256(name.encode()).hexdigest()[:24]
    containers = spec.get("containers") or []
    statuses = status.get("containerStatuses") or []
    container = containers[0] if containers else {}
    container_status = statuses[0] if statuses else {}
    return {
        "event_key": f"pod:{pod_hash}:{version}",
        "workload_role": "master",
        "observed_at_utc": observed_at,
        "pod_hash": pod_hash,
        "resource_version": version,
        "job": str((metadata.get("labels") or {}).get("job-name") or ""),
        "phase": str(status.get("phase") or "Unknown"),
        "node_name": str(spec.get("nodeName") or ""),
        "container": container,
        "container_status": container_status,
    }


def job_event(job: dict, *, observed_at: str) -> dict:
    metadata = job.get("metadata") or {}
    name = str(metadata.get("name") or "")
    version = str(metadata.get("resourceVersion") or "0")
    return {
        "event_key": f"job:{name}:{version}",
        "workload_role": "master",
        "observed_at_utc": observed_at,
        "job": name,
        "resource_version": version,
        "status": job.get("status") or {},
    }


def _project_snapshots(
    discovery: Path, output: Path, seen: set[str], *, master_job: str
) -> None:
    observed = datetime.now(timezone.utc).isoformat()
    for kind, mapper, target in (
        ("pods", pod_event, "pod-events.jsonl"),
        ("jobs", job_event, "job-events.jsonl"),
    ):
        for path in sorted((discovery / kind).glob("*.json")):
            source = json.loads(path.read_text(encoding="utf-8"))
            metadata = source.get("metadata") or {}
            source_job = (
                str(metadata.get("name") or "")
                if kind == "jobs"
                else str((metadata.get("labels") or {}).get("job-name") or "")
            )
            if source_job != master_job:
                continue
            payload = mapper(source, observed_at=observed)
            key = str(payload["event_key"])
            if key not in seen:
                _atomic_append(output / target, payload)
                seen.add(key)


def _kubectl(config: dict, namespace: str, *arguments: str) -> list[str]:
    kubernetes = config.get("kubernetes") or {}
    return [
        str(kubernetes["kubectl_bin"]),
        "--kubeconfig",
        str(kubernetes["kubeconfig"]),
        "-n",
        namespace,
        *arguments,
    ]


def _run_json(command: list[str], *, input_text: str | None = None) -> dict:
    completed = subprocess.run(
        command,
        check=True,
        input=input_text,
        capture_output=True,
        text=True,
    )
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise ValueError("kubectl response is not a JSON object")
    return value


def _master_pod(config: dict, namespace: str, master_job: str) -> tuple[str, str] | None:
    value = _run_json(
        _kubectl(
            config,
            namespace,
            "get",
            "pods",
            "-l",
            f"job-name={master_job}",
            "-o",
            "json",
        )
    )
    items = value.get("items") or []
    if not items:
        return None
    items = sorted(items, key=lambda item: str((item.get("metadata") or {}).get("creationTimestamp") or ""))
    pod = items[-1]
    return (
        str((pod.get("metadata") or {}).get("name") or ""),
        str((pod.get("status") or {}).get("phase") or "Unknown"),
    )


def _fetch_rule_chunks(
    config: dict,
    namespace: str,
    pod: str,
    source_dir: str,
    cursor: dict[str, int],
) -> list[dict]:
    value = _run_json(
        _kubectl(
            config,
            namespace,
            "exec",
            f"pod/{pod}",
            "--",
            MASTER_PYTHON,
            "-c",
            REMOTE_RULE_READER,
            source_dir,
            json.dumps(cursor, sort_keys=True, separators=(",", ":")),
        )
    )
    chunks = value.get("files") or []
    if not isinstance(chunks, list):
        raise ValueError("remote Rule JSONL response has invalid files")
    return chunks


def build_reader_job(master: dict, *, namespace: str, reader_name: str) -> dict:
    pod = ((master.get("spec") or {}).get("template") or {}).get("spec") or {}
    containers = pod.get("containers") or []
    if len(containers) != 1:
        raise ValueError("Master manifest must have one container")
    source_container = containers[0]
    mounts = source_container.get("volumeMounts") or []
    workspace_mount = next(
        (item for item in mounts if item.get("mountPath") == "/workspace"), None
    )
    if workspace_mount is None:
        raise ValueError("Master manifest has no /workspace mount")
    volumes = pod.get("volumes") or []
    workspace_volume = next(
        (item for item in volumes if item.get("name") == workspace_mount.get("name")),
        None,
    )
    claim = (workspace_volume or {}).get("persistentVolumeClaim") or {}
    claim_name = str(claim.get("claimName") or "")
    if not claim_name:
        raise ValueError("Master workspace PVC is missing")
    reader_pod = {
        "serviceAccountName": pod.get("serviceAccountName"),
        "restartPolicy": "Never",
        "containers": [
            {
                "name": "rule-reader",
                "image": source_container.get("image"),
                "command": ["/bin/sh", "-c", "sleep 300"],
                "volumeMounts": [
                    {
                        "name": "sfs-workspace",
                        "mountPath": "/workspace",
                        "readOnly": True,
                    }
                ],
            }
        ],
        "volumes": [
            {
                "name": "sfs-workspace",
                "persistentVolumeClaim": {
                    "claimName": claim_name,
                    "readOnly": True,
                },
            }
        ],
    }
    for key in ("imagePullSecrets", "nodeSelector", "tolerations", "securityContext"):
        if key in pod:
            reader_pod[key] = pod[key]
    if "securityContext" in source_container:
        reader_pod["containers"][0]["securityContext"] = source_container[
            "securityContext"
        ]
    return {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": reader_name,
            "namespace": namespace,
            "labels": {"wgs.biosan.cn/role": "rule-reader"},
        },
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": 300,
            "template": {
                "metadata": {"labels": {"wgs.biosan.cn/role": "rule-reader"}},
                "spec": reader_pod,
            },
        },
    }


def _reader_name(master_job: str) -> str:
    digest = hashlib.sha256(master_job.encode("utf-8")).hexdigest()[:20]
    return f"wgs-rule-reader-{digest}"


def _final_reader_chunks(
    config: dict,
    namespace: str,
    master_manifest: Path,
    master_job: str,
    source_dir: str,
    cursor: dict[str, int],
) -> list[dict]:
    master = yaml.safe_load(master_manifest.read_text(encoding="utf-8"))
    reader_name = _reader_name(master_job)
    manifest = build_reader_job(master, namespace=namespace, reader_name=reader_name)
    subprocess.run(
        _kubectl(config, namespace, "apply", "-f", "-"),
        check=True,
        input=yaml.safe_dump(manifest, sort_keys=False),
        text=True,
        capture_output=True,
    )
    try:
        subprocess.run(
            _kubectl(
                config,
                namespace,
                "wait",
                "--for=condition=Ready",
                "pod",
                "-l",
                f"job-name={reader_name}",
                "--timeout=180s",
            ),
            check=True,
            capture_output=True,
            text=True,
        )
        reader = _master_pod(config, namespace, reader_name)
        if reader is None or not reader[0]:
            raise RuntimeError("Rule reader Pod was not created")
        return _fetch_rule_chunks(
            config, namespace, reader[0], source_dir, cursor
        )
    finally:
        subprocess.run(
            _kubectl(
                config,
                namespace,
                "delete",
                "job",
                reader_name,
                "--ignore-not-found=true",
                "--wait=false",
            ),
            check=False,
            capture_output=True,
            text=True,
        )


def sync_rule_events_once(
    *,
    operator_config: Path,
    namespace: str,
    master_job: str,
    master_manifest: Path,
    source_dir: str,
    output: Path,
    terminal: bool,
) -> int:
    config = yaml.safe_load(operator_config.read_text(encoding="utf-8"))
    cursor_path = output / ".rule-cursor.json"
    cursor = _read_cursor(cursor_path)
    master = _master_pod(config, namespace, master_job)
    chunks: list[dict] = []
    if master is not None and master[0] and master[1] == "Running":
        chunks = _fetch_rule_chunks(
            config, namespace, master[0], source_dir, cursor
        )
    elif terminal:
        chunks = _final_reader_chunks(
            config,
            namespace,
            master_manifest,
            master_job,
            source_dir,
            cursor,
        )
    return _apply_rule_chunks(output, cursor_path, chunks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--master-job", required=True)
    parser.add_argument("--master-manifest", type=Path, required=True)
    parser.add_argument("--rule-source-dir", required=True)
    parser.add_argument("--terminal", action="store_true")
    args = parser.parse_args()
    sync_rule_events_once(
        operator_config=args.operator_config,
        namespace=args.namespace,
        master_job=args.master_job,
        master_manifest=args.master_manifest,
        source_dir=args.rule_source_dir,
        output=args.output,
        terminal=args.terminal,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
