from __future__ import annotations

import csv
import json
import os
import shlex
from pathlib import Path
from typing import Any

import yaml

from common.paths import count_nonempty_lines, ensure_directory, ensure_under_root
from common.progress_events import emit_progress_event, parse_snakemake_output_for_events
from common.subprocess_utils import run_command_to_logs


DEFAULT_SHARED_ROOT = Path(os.getenv("CONTAINER_SHARED_ROOT", "/data/airflow-demo"))
DEFAULT_NIPT_PIPELINE_ROOT = Path(os.getenv("NIPT_CONTAINER_ROOT", "/opt/pipelines/NIPT"))
DEFAULT_HOST_NIPT_PIPELINE_ROOT = Path(os.getenv("NIPT_PIPELINE_ROOT", "/home/jiucheng/pipelines/NIPT"))
DEFAULT_HOST_SHARED_ROOT = Path(os.getenv("HOST_SHARED_ROOT", "/home/jiucheng/project/airflow-demo/shared"))
DEFAULT_DOCKER_IMAGE = os.getenv("NIPT_DOCKER_IMAGE", "172.17.61.235:2333/niptpro/niptpro:1.0.11")
DEFAULT_FETAL_IMAGE = os.getenv("NIPT_FETAL_IMAGE", "172.17.61.235:2333/niptpro/pytorch:biosan")
DEFAULT_DOCKER_NETWORK = os.getenv("NIPT_DOCKER_NETWORK", "nipt_analysis_test_net")
DEFAULT_OWNER = os.getenv("NIPT_DOCKER_OWNER", "6708:520")
SUPPORTED_TEMPLATES = {"run1", "run2"}
SUPPORTED_RUN_MODES = {"mount_smoke", "full_run"}


def validate_nipt_conf(
    conf: dict[str, Any],
    *,
    shared_root: Path = DEFAULT_SHARED_ROOT,
    allow_heavy_run: bool | None = None,
) -> dict[str, Any]:
    analysis_id = str(conf.get("analysis_id") or "").strip()
    pipeline = str(conf.get("pipeline") or "").strip()
    mode = str(conf.get("mode") or "new").strip()
    workdir = Path(str(conf.get("workdir") or "")).resolve()
    sample_sheet_path = Path(str(conf.get("sample_sheet_path") or "")).resolve()
    params = dict(conf.get("params") or {})
    input_mode = str(params.get("input_mode") or ("nipt_docker_template" if params.get("template_id") else "nipt_docker_scan")).strip()
    template_id = str(params.get("template_id") or "").strip()
    source_batch_dir = str(params.get("source_batch_dir") or "").strip()
    run_mode = str(params.get("run_mode") or "mount_smoke").strip()
    cores = int(params.get("cores") or os.getenv("NIPT_DOCKER_CORES", "40"))

    if not analysis_id:
        raise ValueError("analysis_id is required.")
    if pipeline != "nipt_docker":
        raise ValueError("pipeline must be nipt_docker.")
    if mode != "new":
        raise ValueError("NIPT Docker v1 only supports mode=new.")
    if input_mode not in {"nipt_docker_template", "nipt_docker_scan"}:
        raise ValueError("NIPT Docker input_mode must be nipt_docker_template or nipt_docker_scan.")
    if input_mode == "nipt_docker_template" and template_id not in SUPPORTED_TEMPLATES:
        supported = ", ".join(sorted(SUPPORTED_TEMPLATES))
        raise ValueError(f"Unsupported NIPT template: {template_id}. Supported templates: {supported}.")
    if input_mode == "nipt_docker_scan" and not source_batch_dir:
        raise ValueError("NIPT Docker scan runs require params.source_batch_dir.")
    if run_mode not in SUPPORTED_RUN_MODES:
        supported = ", ".join(sorted(SUPPORTED_RUN_MODES))
        raise ValueError(f"Unsupported NIPT run_mode: {run_mode}. Supported modes: {supported}.")
    heavy_allowed = _env_bool("NIPT_ALLOW_HEAVY_RUN", default=False) if allow_heavy_run is None else allow_heavy_run
    if run_mode == "full_run" and not heavy_allowed:
        raise ValueError("NIPT full_run is disabled by NIPT_ALLOW_HEAVY_RUN=false; use mount_smoke.")
    if cores < 1 or cores > 40:
        raise ValueError("NIPT Docker cores must be between 1 and 40.")

    shared_root = shared_root.resolve()
    ensure_under_root(workdir, shared_root, label="workdir")
    ensure_under_root(sample_sheet_path, workdir, label="sample_sheet_path")
    if not sample_sheet_path.is_file():
        raise FileNotFoundError(f"NIPT sample manifest does not exist: {sample_sheet_path}")

    normalized_params = {
        **params,
        "input_mode": input_mode,
        "run_mode": run_mode,
        "cores": cores,
    }
    if input_mode == "nipt_docker_template":
        normalized_params["template_id"] = template_id
    else:
        normalized_params.pop("template_id", None)
        normalized_params["source_batch_dir"] = source_batch_dir
    return {
        "analysis_id": analysis_id,
        "pipeline": pipeline,
        "mode": mode,
        "workdir": str(workdir),
        "sample_sheet_path": str(sample_sheet_path),
        "email_to": conf.get("email_to"),
        "backend_event_url": conf.get("backend_event_url"),
        "params": normalized_params,
    }


def prepare_nipt_docker_run(
    conf: dict[str, Any],
    *,
    nipt_pipeline_root: Path = DEFAULT_NIPT_PIPELINE_ROOT,
    host_nipt_pipeline_root: Path = DEFAULT_HOST_NIPT_PIPELINE_ROOT,
    host_shared_root: Path = DEFAULT_HOST_SHARED_ROOT,
    docker_image: str = DEFAULT_DOCKER_IMAGE,
    fetal_image: str = DEFAULT_FETAL_IMAGE,
    docker_network: str = DEFAULT_DOCKER_NETWORK,
    owner: str = DEFAULT_OWNER,
) -> dict[str, Any]:
    workdir = Path(conf["workdir"])
    config_dir = ensure_directory(workdir / "config")
    ensure_directory(workdir / "logs")
    ensure_directory(workdir / "reports")
    ensure_directory(workdir / "tmp")

    params = dict(conf.get("params") or {})
    input_mode = str(params.get("input_mode") or "nipt_docker_template")
    template_id = str(params.get("template_id") or "")
    run_mode = str(params["run_mode"])
    chip_name = str(params.get("chip_name") or _default_chip_name(template_id))
    cores = int(params["cores"])
    host_workdir = _host_workdir(workdir=workdir, host_shared_root=host_shared_root)
    source_batch_dir = Path(str(params.get("source_batch_dir") or ""))
    host_input_batch_dir = None
    if input_mode == "nipt_docker_scan":
        host_input_batch_dir = _host_nipt_path(
            container_path=source_batch_dir,
            nipt_pipeline_root=nipt_pipeline_root,
            host_nipt_pipeline_root=host_nipt_pipeline_root,
        )
    else:
        template_root = nipt_pipeline_root / f"nipt_docker_test_{template_id}"
        if not template_root.exists():
            raise FileNotFoundError(f"NIPT template directory not found: {template_root}")
        source_batch_dir = template_root

    run_config_path = config_dir / "nipt_run_config.yaml"
    chip_samplesheet_path = workdir / f"{chip_name}.csv"
    _write_chip_samplesheet(Path(conf["sample_sheet_path"]), chip_samplesheet_path)
    container_config_path = f"/workdir/analysis/NIPTPro/{chip_name}/config/nipt_run_config.yaml"
    run_config = _nipt_run_config(
        analysis_id=str(conf["analysis_id"]),
        chip_name=chip_name,
        input_mode=input_mode,
        run_mode=run_mode,
        cores=cores,
        sample_sheet_path=conf["sample_sheet_path"],
        source_batch_dir=str(source_batch_dir),
        host_workdir=str(host_workdir),
        container_chip_dir=f"/workdir/analysis/NIPTPro/{chip_name}",
        container_fastq_dir="/input_batch" if input_mode == "nipt_docker_scan" else str(source_batch_dir),
    )
    if input_mode == "nipt_docker_template":
        run_config["template_id"] = template_id
    run_config_path.write_text(yaml.safe_dump(run_config, sort_keys=False), encoding="utf-8")

    compose = generate_nipt_compose(
        analysis_id=str(conf["analysis_id"]),
        run_mode=run_mode,
        workdir=workdir,
        host_workdir=host_workdir,
        nipt_pipeline_root=nipt_pipeline_root,
        host_nipt_pipeline_root=host_nipt_pipeline_root,
        chip_name=chip_name,
        template_id=template_id or None,
        input_mode=input_mode,
        host_input_batch_dir=host_input_batch_dir,
        container_config_path=container_config_path,
        cores=cores,
        docker_image=docker_image,
        fetal_image=fetal_image,
        docker_network=docker_network,
        owner=owner,
    )
    compose_path = config_dir / "nipt_docker_compose.yml"
    compose_path.write_text(yaml.safe_dump(compose, sort_keys=False), encoding="utf-8")
    (config_dir / "nipt_airflow_request.json").write_text(
        json.dumps({**conf, "compose_path": str(compose_path), "run_config_path": str(run_config_path)}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {**conf, "compose_path": str(compose_path), "run_config_path": str(run_config_path)}


def generate_nipt_compose(
    *,
    analysis_id: str,
    run_mode: str,
    workdir: Path,
    host_workdir: Path,
    nipt_pipeline_root: Path,
    host_nipt_pipeline_root: Path,
    chip_name: str,
    cores: int,
    docker_image: str,
    fetal_image: str,
    docker_network: str,
    owner: str,
    template_id: str | None = None,
    input_mode: str = "nipt_docker_template",
    host_input_batch_dir: Path | None = None,
    container_config_path: str = "/code/NIPTPro_pipeline/niptplus/config.yaml",
) -> dict[str, Any]:
    container_name = f"NIPTPro_{analysis_id}"
    mount_smoke_command = [
        "-lc",
        " && ".join(
            [
                "test -r /code/NIPTPro_pipeline/niptplus/Snakefile",
                "test -r /code/NIPTPro_pipeline/niptplus/config.yaml",
                "test -d /refdir/index",
                "test -d /workdir/analysis/NIPTPro",
                "test -r /workdir/analysis/NIPTPro/%s/%s.csv" % (shlex.quote(chip_name), shlex.quote(chip_name)),
                "test -d /input_batch" if input_mode == "nipt_docker_scan" else "test -d /template",
                f"echo mount_smoke_ok {shlex.quote(analysis_id)} {shlex.quote(chip_name)}",
            ]
        ),
    ]
    full_run_command = [
        "/code/NIPTPro_pipeline/niptplus/scripts/run_niptplus_docker_entrypoint.sh",
        container_config_path,
        f"/workdir/analysis/NIPTPro/{chip_name}",
        str(cores),
        owner,
    ]
    command = mount_smoke_command if run_mode == "mount_smoke" else full_run_command
    volumes = [
        f"{host_nipt_pipeline_root / 'niptplus'}:/code/NIPTPro_pipeline/niptplus:ro",
        f"{host_nipt_pipeline_root / 'locale'}:/locale:ro",
        f"{host_nipt_pipeline_root / 'refdir'}:/refdir:ro",
        f"{host_workdir}:/workdir/analysis/NIPTPro/{chip_name}",
        "/var/run/docker.sock:/var/run/docker.sock",
    ]
    if input_mode == "nipt_docker_scan":
        if host_input_batch_dir is None:
            raise ValueError("host_input_batch_dir is required for NIPT Docker scan runs.")
        volumes.append(f"{host_input_batch_dir}:/input_batch:ro")
    else:
        template_value = str(template_id or "")
        if template_value not in SUPPORTED_TEMPLATES:
            raise ValueError(f"Unsupported NIPT template: {template_value}.")
        volumes.append(f"{host_nipt_pipeline_root / f'nipt_docker_test_{template_value}'}:/template:ro")
    return {
        "services": {
            "runner": {
                "image": docker_image,
                "container_name": container_name,
                "working_dir": "/code/NIPTPro_pipeline/niptplus",
                "user": "0:0",
                "shm_size": "37gb",
                "mem_limit": "60g",
                "environment": {
                    "NIPTPRO_FETAL_RATIO_DOCKER_IMAGE": fetal_image,
                    "AIRFLOW_DEMO_ANALYSIS_ID": analysis_id,
                    "AIRFLOW_DEMO_RUN_MODE": run_mode,
                },
                "volumes": volumes,
                "entrypoint": "/bin/bash",
                "command": command,
                "networks": [docker_network],
            }
        },
        "networks": {docker_network: {"external": True}},
    }


def run_nipt_docker(conf: dict[str, Any]) -> dict[str, str | int]:
    workdir = Path(conf["workdir"])
    logs_dir = ensure_directory(workdir / "logs")
    compose_path = Path(conf["compose_path"])
    run_mode = str((conf.get("params") or {}).get("run_mode") or "mount_smoke")
    analysis_id = str(conf.get("analysis_id") or workdir.name)
    backend_event_url = conf.get("backend_event_url")
    event_rule = "nipt_mount_smoke" if run_mode == "mount_smoke" else "nipt_full_run"
    stdout_path = logs_dir / "snakemake.stdout.log"
    stderr_path = logs_dir / "snakemake.stderr.log"
    command = _docker_run_command(compose_path)
    (logs_dir / "nipt_docker.command.txt").write_text(shlex.join(command) + "\n", encoding="utf-8")
    emit_progress_event(
        analysis_id=analysis_id,
        workdir=workdir,
        backend_event_url=str(backend_event_url) if backend_event_url else None,
        event="pipeline_step_started",
        rule=event_rule,
        status="running",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        message=f"NIPT Docker {run_mode} started.",
    )
    try:
        result = run_command_to_logs(
            command,
            cwd=workdir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            env=os.environ.copy(),
        )
        if run_mode == "mount_smoke":
            _write_mount_smoke_qc(conf)
        else:
            parse_snakemake_output_for_events(
                analysis_id=analysis_id,
                workdir=workdir,
                backend_event_url=str(backend_event_url) if backend_event_url else None,
                stdout_text=stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else "",
                stderr_text=stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else "",
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )
            write_nipt_qc_summary_from_outputs(workdir)
    except Exception as exc:
        emit_progress_event(
            analysis_id=analysis_id,
            workdir=workdir,
            backend_event_url=str(backend_event_url) if backend_event_url else None,
            event="pipeline_step_failed",
            rule=event_rule,
            status="failed",
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            message=str(exc),
            return_code=1,
        )
        raise
    emit_progress_event(
        analysis_id=analysis_id,
        workdir=workdir,
        backend_event_url=str(backend_event_url) if backend_event_url else None,
        event="pipeline_step_finished",
        rule=event_rule,
        status="success",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        message=f"NIPT Docker {run_mode} completed.",
        return_code=0,
    )
    return result


def _docker_run_command(compose_path: Path) -> list[str]:
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    service = dict(((compose.get("services") or {}).get("runner")) or {})
    if not service:
        raise ValueError(f"NIPT compose artifact has no runner service: {compose_path}")

    command = ["docker", "run", "--rm"]
    container_name = str(service.get("container_name") or "").strip()
    if container_name:
        command.extend(["--name", container_name])
    network = _first_value(service.get("networks"))
    if network:
        command.extend(["--network", network])
    working_dir = str(service.get("working_dir") or "").strip()
    if working_dir:
        command.extend(["--workdir", working_dir])
    user = str(service.get("user") or "").strip()
    if user:
        command.extend(["--user", user])
    shm_size = str(service.get("shm_size") or "").strip()
    if shm_size:
        command.extend(["--shm-size", shm_size])
    mem_limit = str(service.get("mem_limit") or "").strip()
    if mem_limit:
        command.extend(["--memory", mem_limit])
    for key, value in sorted((service.get("environment") or {}).items()):
        command.extend(["-e", f"{key}={value}"])
    for volume in service.get("volumes") or []:
        command.extend(["-v", str(volume)])
    entrypoint = str(service.get("entrypoint") or "").strip()
    if entrypoint:
        command.extend(["--entrypoint", entrypoint])
    image = str(service.get("image") or "").strip()
    if not image:
        raise ValueError(f"NIPT compose artifact has no runner image: {compose_path}")
    command.append(image)
    service_command = service.get("command") or []
    if isinstance(service_command, str):
        command.append(service_command)
    else:
        command.extend(str(item) for item in service_command)
    return command


def collect_nipt_artifacts(conf: dict[str, Any]) -> dict[str, str | int]:
    workdir = Path(conf["workdir"])
    qc_path = workdir / "reports" / "qc_summary.tsv"
    compose_path = workdir / "config" / "nipt_docker_compose.yml"
    run_config_path = workdir / "config" / "nipt_run_config.yaml"
    if not qc_path.is_file():
        raise FileNotFoundError(f"NIPT QC summary artifact was not generated: {qc_path}")
    if not compose_path.is_file():
        raise FileNotFoundError(f"NIPT compose artifact was not generated: {compose_path}")
    if not run_config_path.is_file():
        raise FileNotFoundError(f"NIPT config artifact was not generated: {run_config_path}")
    return {
        "type": "nipt_docker_summary",
        "label": "NIPT Docker QC summary",
        "qc_path": str(qc_path),
        "qc_metric_count": max(count_nonempty_lines(qc_path) - 1, 0),
        "compose_path": str(compose_path),
        "run_config_path": str(run_config_path),
    }


def write_nipt_qc_summary_from_outputs(workdir: Path) -> Path:
    mapping_qc = workdir / "CNV" / "mappingQC.csv"
    if not mapping_qc.is_file():
        raise FileNotFoundError(f"NIPT mapping QC output was not generated: {mapping_qc}")
    fetal_ratios = _read_fetal_ratios(workdir)
    rows: list[list[str]] = [["sample_id", "metric_name", "metric_value", "metric_numeric", "threshold", "status"]]
    with mapping_qc.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sample_id = _normalize_nipt_sample_id(row.get("Sample"))
            if not sample_id:
                continue
            q30 = _number(row.get("Q30"))
            unique_mapping = _number(row.get("uniqueMappedRC%"))
            pcr_dup = _number(row.get("PCRdup%"))
            chr_y = _number(row.get("chrY%"))
            gender = str(row.get("Gender") or "").strip()
            rows.extend(
                [
                    _metric_row(sample_id, "read_count", row.get("read_count"), None, "reported", "unknown"),
                    _metric_row(sample_id, "Q30", row.get("Q30"), q30, ">=85", _pass_warn(q30, warn_min=85)),
                    _metric_row(sample_id, "unique_mapping_rate", row.get("uniqueMappedRC%"), unique_mapping, ">=70", _pass_warn(unique_mapping, warn_min=70)),
                    _metric_row(sample_id, "pcr_duplication_rate", row.get("PCRdup%"), pcr_dup, "<=20", _pass_warn_inverse(pcr_dup, warn_max=20)),
                    _metric_row(sample_id, "chrY_percent", row.get("chrY%"), chr_y, None, "unknown"),
                    _metric_row(sample_id, "gender", gender, None, None, "unknown"),
                ]
            )
            fetal_ratio = fetal_ratios.get(sample_id)
            if fetal_ratio is not None:
                rows.append(_metric_row(sample_id, "fetal_fraction", str(fetal_ratio), fetal_ratio, ">=0.04", _pass_warn(fetal_ratio, warn_min=0.04)))
    reports_dir = ensure_directory(workdir / "reports")
    qc_path = reports_dir / "qc_summary.tsv"
    qc_path.write_text("\n".join("\t".join(cell for cell in row) for row in rows) + "\n", encoding="utf-8")
    return qc_path


def _write_mount_smoke_qc(conf: dict[str, Any]) -> None:
    workdir = Path(conf["workdir"])
    reports_dir = ensure_directory(workdir / "reports")
    sample_ids = _sample_ids(Path(conf["sample_sheet_path"])) or [str(conf["analysis_id"])]
    qc_path = reports_dir / "qc_summary.tsv"
    qc_path.write_text(
        "\n".join(
            [
                "sample_id\tmetric_name\tmetric_value\tmetric_numeric\tthreshold\tstatus",
                *[
                    f"{sample_id}\tnipt_mount_smoke\tpass\t\timage/mount/config readable\tpass"
                    for sample_id in sample_ids
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _sample_ids(path: Path) -> list[str]:
    if not path.is_file():
        return []
    sample_ids: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            sample_id = str(row.get("sample_id") or "").strip()
            if sample_id:
                sample_ids.append(sample_id)
    return sample_ids


def _write_chip_samplesheet(manifest_path: Path, chip_samplesheet_path: Path) -> None:
    rows: list[list[str]] = [["library", "index", "comment"]]
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            sample_id = str(row.get("sample_id") or "").strip()
            library = str(row.get("library") or "").strip()
            index = str(row.get("index") or "").strip()
            if (not library or not index) and "." in sample_id:
                library, index = sample_id.rsplit(".", 1)
            comment = str(row.get("comment") or "NIPT").strip() or "NIPT"
            if library and index:
                rows.append([library, index, comment])
    chip_samplesheet_path.write_text("\n".join(",".join(cell for cell in row) for row in rows) + "\n", encoding="utf-8")


def _nipt_run_config(
    *,
    analysis_id: str,
    chip_name: str,
    input_mode: str,
    run_mode: str,
    cores: int,
    sample_sheet_path: str,
    source_batch_dir: str,
    host_workdir: str,
    container_chip_dir: str,
    container_fastq_dir: str,
) -> dict[str, Any]:
    base_config_path = DEFAULT_NIPT_PIPELINE_ROOT / "niptplus" / "config.yaml"
    if base_config_path.is_file():
        config = yaml.safe_load(base_config_path.read_text(encoding="utf-8")) or {}
    else:
        config = {}
    params = dict(config.get("params") or {})
    params.update(
        {
            "chip_name": chip_name,
            "map_threads": min(4, cores),
            "aneuscreen_threads": min(10, cores),
        }
    )
    input_section = dict(config.get("input") or {})
    input_section.update(
        {
            "samplesheet": f"{container_chip_dir}/{chip_name}.csv",
            "fastq_dir": container_fastq_dir,
            "result_dir": container_chip_dir,
        }
    )
    config.update(
        {
            "analysis_id": analysis_id,
            "input_mode": input_mode,
            "run_mode": run_mode,
            "source_batch_dir": source_batch_dir,
            "host_workdir": host_workdir,
            "sample_sheet_path": sample_sheet_path,
            "params": params,
            "input": input_section,
        }
    )
    return config


def _read_fetal_ratios(workdir: Path) -> dict[str, float]:
    ratios: dict[str, float] = {}
    for path in workdir.rglob("*.model.predict.csv"):
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                sample_id = _normalize_nipt_sample_id(row.get("sample"))
                ratio = _number(row.get("fetal_ratio"))
                if sample_id and ratio is not None:
                    ratios[sample_id] = ratio
    return ratios


def _normalize_nipt_sample_id(value: str | None) -> str | None:
    sample = str(value or "").strip()
    if not sample:
        return None
    for suffix in (".R1.clean.fastq.gz", ".R2.clean.fastq.gz", ".clean.fastq.gz", ".fastq.gz", ".fq.gz"):
        if sample.endswith(suffix):
            sample = sample[: -len(suffix)]
            break
    return sample


def _metric_row(
    sample_id: str,
    metric_name: str,
    metric_value: str | None,
    metric_numeric: float | None,
    threshold: str | None,
    status: str,
) -> list[str]:
    numeric = "" if metric_numeric is None else str(metric_numeric)
    return [sample_id, metric_name, str(metric_value or "").strip(), numeric, threshold or "", status]


def _number(value: str | None) -> float | None:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return None


def _pass_warn(value: float | None, *, warn_min: float) -> str:
    if value is None:
        return "unknown"
    return "pass" if value >= warn_min else "warn"


def _pass_warn_inverse(value: float | None, *, warn_max: float) -> str:
    if value is None:
        return "unknown"
    return "pass" if value <= warn_max else "warn"


def _default_chip_name(template_id: str) -> str:
    if template_id == "run1":
        return "260414_TPNB500380AR_1065_AH32CCBGY2"
    if template_id == "run2":
        return "260422_TPNB500380AR_1070_AH33KYBGY2"
    raise ValueError(f"Unsupported NIPT template: {template_id}.")


def _host_nipt_path(*, container_path: Path, nipt_pipeline_root: Path, host_nipt_pipeline_root: Path) -> Path:
    resolved_container = container_path.resolve()
    resolved_root = nipt_pipeline_root.resolve()
    try:
        relative = resolved_container.relative_to(resolved_root)
    except ValueError:
        return container_path
    return host_nipt_pipeline_root / relative


def _host_workdir(*, workdir: Path, host_shared_root: Path) -> Path:
    parts = workdir.resolve().parts
    if "runs" in parts:
        suffix = Path(*parts[parts.index("runs") :])
        return host_shared_root / suffix
    return host_shared_root / "runs" / workdir.name


def _first_value(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return str(value[0])
    if isinstance(value, dict) and value:
        return str(next(iter(value.keys())))
    if isinstance(value, str) and value:
        return value
    return None


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
