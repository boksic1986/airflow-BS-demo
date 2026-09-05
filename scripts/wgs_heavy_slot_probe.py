#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any


def contend(*, quota: Any, contenders: int, run_label: str) -> dict[str, Any]:
    barrier = threading.Barrier(contenders)

    def acquire(index: int):
        barrier.wait()
        try:
            return quota.acquire(
                run_label=run_label,
                job_name=f"t206-heavy-probe-{index:02d}",
            )
        except RuntimeError:
            return None

    claims = []
    released = 0
    try:
        with ThreadPoolExecutor(max_workers=contenders) as executor:
            claims = [
                claim
                for claim in executor.map(acquire, range(contenders))
                if claim is not None
            ]
    finally:
        for claim in claims:
            if quota.release(claim):
                released += 1
    slots = {claim.lease_name for claim in claims}
    return {
        "schema_version": "wgs-heavy-slot-probe.v1",
        "contenders": contenders,
        "acquired": len(claims),
        "waiting": contenders - len(claims),
        "unique_slots": len(slots),
        "released": released,
        "slots": sorted(slots),
    }


def _holders(api: Any, namespace: str, names: tuple[str, ...]) -> dict[str, str]:
    result = {}
    for name in names:
        lease = api.read_namespaced_lease(name, namespace)
        holder = str(getattr(lease.spec, "holder_identity", "") or "")
        if holder:
            result[name] = holder
    return result


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".partial"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exercise the WGS heavy-I/O Lease quota without analysis work."
    )
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--contenders", type=int, default=26)
    parser.add_argument("--run-label", default="t206-heavy-slot-probe")
    parser.add_argument("--kubeconfig")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.contenders != args.limit + 1:
        raise SystemExit("probe requires exactly limit + 1 contenders")

    from kubernetes import client, config
    from snakemake_executor_plugin_kubernetes.heavy_io_quota import (
        HeavySlotQuota,
        lease_names,
    )

    if args.kubeconfig:
        config.load_kube_config(config_file=args.kubeconfig)
    else:
        config.load_incluster_config()
    coordination = client.CoordinationV1Api()
    quota = HeavySlotQuota(
        api=coordination,
        batch_api=client.BatchV1Api(),
        core_api=client.CoreV1Api(),
        namespace=args.namespace,
        limit=args.limit,
        mode="enforce",
    )
    quota.ensure_leases()
    names = lease_names(args.limit)
    occupied = _holders(coordination, args.namespace, names)
    if occupied:
        raise SystemExit(
            "heavy-slot probe requires an idle quota: "
            + ", ".join(sorted(occupied))
        )
    result = contend(
        quota=quota,
        contenders=args.contenders,
        run_label=args.run_label,
    )
    remaining = _holders(coordination, args.namespace, names)
    result["remaining_holders"] = remaining
    result["passed"] = (
        result["acquired"] == args.limit
        and result["waiting"] == 1
        and result["unique_slots"] == args.limit
        and result["released"] == args.limit
        and not remaining
    )
    if args.output:
        _write_json(Path(args.output), result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
