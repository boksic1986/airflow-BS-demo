#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any


METRICS = (
    "used_capacity_percent",
    "used_capacity",
    "data_read_io_bytes",
    "data_write_io_bytes",
    "total_io_bytes",
    "iops",
    "client_connections",
)


def read_credentials(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8").strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = {}
        for line in text.splitlines():
            if "=" in line:
                key, item = line.split("=", 1)
            elif ":" in line:
                key, item = line.split(":", 1)
            else:
                continue
            value[key.strip().lower()] = item.strip().strip('"\'')
    ak = str(value.get("ak") or value.get("access_key") or "").strip()
    sk = str(value.get("sk") or value.get("secret_key") or "").strip()
    if len(ak) != 20 or len(sk) < 32:
        raise ValueError("SFS Cloud Eye credential file is invalid")
    return ak, sk


def query_metrics(*, ak: str, sk: str, project_id: str, endpoint: str,
                  resource_id: str, now: datetime | None = None) -> tuple[str, dict[str, float]]:
    import requests
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkcore.sdk_request import SdkRequest

    end = now or datetime.now(timezone.utc)
    start = end - timedelta(minutes=10)
    values: dict[str, float] = {}
    latest_timestamp = 0
    for metric in METRICS:
        request = SdkRequest(
            method="GET",
            schema="https",
            host=endpoint,
            resource_path=f"/V1.0/{project_id}/metric-data",
            query_params=[
                ("namespace", "SYS.EFS"),
                ("metric_name", metric),
                ("dim.0", f"efs_instance_id,{resource_id}"),
                ("from", int(start.timestamp() * 1000)),
                ("to", int(end.timestamp() * 1000)),
                ("period", 1),
                ("filter", "average"),
            ],
            header_params={"Content-Type": "application/json"},
        )
        BasicCredentials(ak, sk, project_id).sign_request(request)
        response = requests.get(
            f"https://{request.host}{request.uri}",
            headers=request.header_params,
            timeout=20,
        )
        response.raise_for_status()
        datapoints = response.json().get("datapoints") or []
        if not datapoints:
            continue
        point = max(datapoints, key=lambda item: int(item.get("timestamp") or 0))
        value = point.get("average")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values[metric] = float(value)
            latest_timestamp = max(latest_timestamp, int(point.get("timestamp") or 0))
    if not values:
        raise RuntimeError("SFS Cloud Eye returned no recent metric datapoints")
    observed = (
        datetime.fromtimestamp(latest_timestamp / 1000, timezone.utc)
        if latest_timestamp
        else end
    )
    return observed.isoformat(), values


def build_spool(*, source_updated_at: str, values: dict[str, float]) -> dict[str, Any]:
    current = {
        "capacity_used_percent": values.get("used_capacity_percent"),
        "capacity_used_bytes": values.get("used_capacity"),
        "read_bps": values.get("data_read_io_bytes"),
        "write_bps": values.get("data_write_io_bytes"),
        "total_bps": values.get("total_io_bytes"),
        "iops": values.get("iops"),
        "client_connections": values.get("client_connections"),
    }
    return {
        "schema_version": "platform-cloud-metrics.v1",
        "items": [{
            "resource_key": "sfs-turbo-clinical",
            "resource_type": "sfs",
            "display_name": "sfs-turbo-clinical",
            "source_updated_at": source_updated_at,
            "current": current,
        }],
    }


def write_spool(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".partial"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def collect_once(args: argparse.Namespace) -> None:
    required = {
        "credentials": args.credentials,
        "project_id": args.project_id,
        "resource_id": args.resource_id,
        "output": args.output,
    }
    missing = [name for name, value in required.items() if not str(value or "").strip()]
    if missing:
        raise ValueError(
            "SFS Cloud Eye configuration is incomplete: " + ", ".join(missing)
        )
    ak, sk = read_credentials(Path(args.credentials))
    observed_at, values = query_metrics(
        ak=ak,
        sk=sk,
        project_id=args.project_id,
        endpoint=args.endpoint,
        resource_id=args.resource_id,
    )
    write_spool(Path(args.output), build_spool(source_updated_at=observed_at, values=values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write an SFS-only Cloud Eye metrics spool")
    parser.add_argument("--credentials", default=os.getenv("SFS_CLOUD_EYE_CREDENTIALS"))
    parser.add_argument("--project-id", default=os.getenv("HWC_PROJECT_ID"))
    parser.add_argument("--endpoint", default=os.getenv("SFS_CLOUD_EYE_ENDPOINT", "ces.cn-east-3.myhuaweicloud.com"))
    parser.add_argument("--resource-id", default=os.getenv("SFS_CLOUD_EYE_RESOURCE_ID"))
    parser.add_argument("--output", default=os.getenv("PLATFORM_CLOUD_METRICS_SPOOL"))
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    while True:
        try:
            collect_once(args)
        except Exception:
            if args.once:
                raise
            # The consumer marks the last atomic snapshot stale after three
            # minutes. Retry silently instead of generating one log per cycle.
            pass
        if args.once:
            return 0
        time.sleep(max(30, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
