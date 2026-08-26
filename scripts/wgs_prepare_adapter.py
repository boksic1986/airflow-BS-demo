#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest must be a JSON object")
    return value


def validate_sampleinfo(manifest: Path, sampleinfo: Path, output: Path) -> dict:
    expected = {str(item["sample_id"]) for item in _load(manifest).get("files", [])}
    with sampleinfo.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows or "样本编号" not in rows[0] or "家系编号" not in rows[0]:
        raise ValueError("sampleinfo is missing required WGS columns")
    actual = {str(row["样本编号"]).strip() for row in rows if str(row["样本编号"]).strip()}
    if actual != expected:
        raise ValueError("sampleinfo sample set does not match FASTQ snapshot")
    families = sorted({str(row["家系编号"]).strip() for row in rows if str(row["家系编号"]).strip()})
    if not families:
        raise ValueError("sampleinfo has no family metadata")
    summary = {"sample_ids": sorted(actual), "family_ids": families}
    _atomic_text(output, json.dumps(summary, sort_keys=True, ensure_ascii=False) + "\n")
    return summary


def _prepare_config(snapshot: Path) -> Path:
    config = Path(os.environ["WGS_PREPARE_CONFIG_PATH"]).resolve()
    if not config.is_file() or config == snapshot / "prepare" / "config.yaml" or snapshot in config.parents:
        raise ValueError("WGS prepare config must be a host-only file outside the pipeline snapshot")
    return config


def run_upstream_sampleinfo(request: dict) -> Path:
    snapshot = Path(str(request["pipeline_snapshot_path"])).resolve()
    workdir = Path(str(request["workdir"])).resolve()
    config = _prepare_config(snapshot)
    command = [
        str(snapshot / "prepare" / "prepare_wgs_batch.py"),
        "sampleinfo",
        "--batch",
        str(request["batch_no"]),
        "--analysis-batch",
        str(request["batch_no"]),
        "--outpath",
        str(workdir / "prepare"),
        "--prepare-config",
        str(config),
    ]
    subprocess.run(command, check=True)
    generated = sorted((workdir / "prepare" / "sampleinfo").glob("*.sampleinfo.txt"))
    if len(generated) != 1:
        raise ValueError("WGS prepare did not create exactly one sampleinfo")
    target = workdir / "config" / "sampleinfo.tsv"
    _atomic_text(target, generated[0].read_text(encoding="utf-8"))
    return target


def build_cce_bundle(request: dict) -> Path:
    snapshot = Path(str(request["pipeline_snapshot_path"])).resolve()
    workdir = Path(str(request["workdir"])).resolve()
    config = _prepare_config(snapshot)
    sampleinfo = workdir / "config" / "sampleinfo.tsv"
    summary = _load(workdir / "config" / "sample-summary.json")
    manifest = _load(workdir / "config" / "input-manifest.json")
    if not sampleinfo.is_file() or not summary.get("sample_ids"):
        raise ValueError("sampleinfo and validated sample summary are required")
    output = workdir / "prepare-analysis"
    run_id = f"{request['analysis_id']}-a{int(request['attempt'])}"
    command = [
        str(snapshot / "prepare" / "prepare_wgs_batch.py"),
        "analysis",
        "--sampleinfo",
        str(sampleinfo),
        "--outpath",
        str(output),
        "--prepare-config",
        str(config),
        "--fastq-root",
        str(manifest["fq_path"]),
        "--run-mode",
        "cce",
        "--run-id",
        run_id,
    ]
    subprocess.run(command, check=True)
    generated = [
        path
        for path in output.iterdir()
        if path.is_dir() and path.name not in {"sampleinfo", "prepare", ".archive"}
    ]
    if len(generated) != 1:
        raise ValueError("WGS prepare did not create exactly one CCE analysis directory")
    target = workdir / "cce-bundle"
    if target.exists():
        raise FileExistsError("CCE bundle already exists")
    os.replace(generated[0], target)
    for relative in ("config.yaml", "sampleinfo.tsv", "cce/config.yaml"):
        if not (target / relative).is_file():
            raise ValueError(f"CCE bundle is missing {relative}")
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["sampleinfo", "validate", "bundle"])
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    request = _load(args.request)
    workdir = Path(str(request["workdir"]))
    manifest = workdir / "config" / "input-manifest.json"
    if args.command == "sampleinfo":
        run_upstream_sampleinfo(request)
    elif args.command == "validate":
        validate_sampleinfo(
            manifest,
            workdir / "config" / "sampleinfo.tsv",
            workdir / "config" / "sample-summary.json",
        )
    else:
        build_cce_bundle(request)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
