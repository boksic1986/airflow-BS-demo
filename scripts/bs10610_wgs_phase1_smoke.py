#!/usr/bin/env python3
from __future__ import annotations

import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener


def env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def call(opener, base: str, path: str, *, method: str = "GET", payload=None, csrf: str = ""):
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    if csrf:
        headers["X-CSRF-Token"] = csrf
    request = Request(base + path, method=method, headers=headers, data=data)
    try:
        with opener.open(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except HTTPError as error:
        body = error.read().decode()
        return error.code, json.loads(body) if body else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--base-url", default="http://172.17.106.10:12959/api")
    args = parser.parse_args()
    values = env_file(args.env_file)
    intake_root = Path(values["WGS_INTAKE_HOST_ROOT"])
    fastq_root = Path(values["WGS_FASTQ_HOST_ROOT"])
    source = fastq_root / "T139_SMOKE"
    intake = intake_root / "T139_SMOKE"
    source.mkdir(parents=True, exist_ok=True)
    intake.mkdir(parents=True, exist_ok=True)
    for read in ("R1", "R2"):
        target = source / f"T139_S1_{read}.fastq.gz"
        target.write_bytes(f"synthetic-{read}\n".encode())
        link = intake / target.name
        if link.is_symlink() or link.exists():
            if link.resolve() != target.resolve():
                raise RuntimeError(f"unexpected existing smoke link: {link}")
        else:
            link.symlink_to(target)

    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    status, login = call(opener, args.base_url, "/auth/login", method="POST", payload={
        "username": values.get("PLATFORM_ADMIN_USERNAME", "admin"),
        "password": values["PLATFORM_ADMIN_PASSWORD"],
    })
    if status != 200:
        raise RuntimeError(f"login failed with HTTP {status}")
    csrf = str(login["csrf_token"])
    status, run = call(opener, args.base_url, "/runs", method="POST", csrf=csrf, payload={
        "pipeline": "wgs", "execution_mode": "cce", "project_name": "T139 synthetic smoke",
        "batch_no": "T139_SMOKE", "fq_path": "/data/wgs-intake/T139_SMOKE",
    })
    if status != 201:
        raise RuntimeError(f"create failed with HTTP {status}: {run}")
    analysis_id = str(run["analysis_id"])
    workdir = Path(values["WGS_RESULTS_HOST_ROOT"]) / "runs" / analysis_id / "config"
    required = [workdir / "input-manifest.json"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"generated workdir contract is incomplete: {missing}")
    forbidden = [workdir / "sampleinfo.tsv", workdir / "config.yaml"]
    unexpected = [str(path) for path in forbidden if path.exists()]
    if unexpected:
        raise RuntimeError(f"Airflow must not generate WGS prepare files: {unexpected}")
    status, _ = call(opener, args.base_url, f"/runs/{analysis_id}/actions/submit", method="POST", csrf=csrf)
    if status != 409:
        raise RuntimeError(f"execution gate expected HTTP 409, received {status}")
    print(json.dumps({"analysis_id": analysis_id, "create_status": 201, "submit_status": 409, "generated": [path.name for path in required], "forbidden_prepare_files": "absent", "real_cce_started": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
