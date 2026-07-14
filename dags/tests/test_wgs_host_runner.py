from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wgs_host_runner import (
    _validate_wgs_config,
    build_snakemake_command,
    prepare_run,
    parse_forced_command,
    resolve_request_path,
)


def test_forced_command_accepts_only_generated_analysis_id_and_stage() -> None:
    assert parse_forced_command("wgs-run WGS_20260714_123456_A1B2C3 pre_calling") == (
        "WGS_20260714_123456_A1B2C3",
        "pre_calling",
    )

    for command in (
        "bash -c id",
        "wgs-run ../../etc/passwd pre_calling",
        "wgs-run WGS_20260714_123456_A1B2C3 arbitrary",
        "wgs-run WGS_20260714_123456_A1B2C3 pre_calling;id",
    ):
        with pytest.raises(ValueError):
            parse_forced_command(command)


def test_request_path_is_fixed_below_results_root(tmp_path) -> None:
    request = resolve_request_path(
        "WGS_20260714_123456_A1B2C3",
        results_root=tmp_path,
    )

    assert request == tmp_path / "runs" / "WGS_20260714_123456_A1B2C3" / "config" / "wgs_runner_request.json"


def test_snakemake9_command_has_logger_and_no_removed_flags(tmp_path) -> None:
    workdir = tmp_path / "run"
    (workdir / "config").mkdir(parents=True)
    (workdir / "config" / "targets.resolved.txt").write_text("01_SNV/demo.flt.tsv\n", encoding="utf-8")
    request = {
        "analysis_id": "WGS_20260714_123456_A1B2C3",
        "host_workdir": str(workdir),
        "precalling_config_path": str(tmp_path / "pre.yaml"),
        "downstream_config_path": str(tmp_path / "down.yaml"),
        "targets_path": str(tmp_path / "targets.txt"),
        "backend_event_url": "http://172.17.106.10:13959/api/events/snakemake",
    }
    command = build_snakemake_command(
        request,
        stage="variant_analysis",
        snakemake_bin=Path("/opt/wgs-s9/bin/snakemake"),
        pipeline_root=Path("/opt/airflow-wgs/pipelines/wgs_s9"),
        cores=96,
    )

    joined = " ".join(command)
    assert command[0] == "/opt/wgs-s9/bin/snakemake"
    assert "--executor local" in joined
    assert "--logger airflow-demo" in joined
    assert "--rerun-incomplete" in command
    assert "--show-failed-logs" in command
    assert "--forceall" not in command
    assert "--reason" not in command
    assert "--stats" not in command
    assert "--cluster" not in command


def test_wgs_config_rejects_fastq_directory_outside_approved_roots(tmp_path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    sample_info = allowed / "samples.tsv"
    sample_info.write_text("sample_id\nWGS-01\n", encoding="utf-8")
    outside_fastq = tmp_path / "outside-fastq"
    outside_fastq.mkdir()

    with pytest.raises(ValueError, match="fastqDir is outside approved roots"):
        _validate_wgs_config(
            {"sample_info": str(sample_info), "fastqDir": str(outside_fastq)},
            roots=(allowed.resolve(),),
            fastq_roots=(allowed.resolve(),),
        )


def test_prepare_rejects_modified_run_local_config(tmp_path, monkeypatch) -> None:
    workdir = tmp_path / "runs" / "WGS_20260714_123456_A1B2C3"
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True)
    sample_info = tmp_path / "samples.tsv"
    sample_info.write_text("sample_id\nWGS-01\n", encoding="utf-8")
    fastq_dir = tmp_path / "fastq"
    fastq_dir.mkdir()
    config_path = config_dir / "wgs.precalling.requested.yaml"
    config_path.write_text(f"sample_info: {sample_info}\nfastqDir: {fastq_dir}\n", encoding="utf-8")
    downstream_path = config_dir / "wgs.downstream.requested.yaml"
    downstream_path.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    targets_path = config_dir / "targets.requested.txt"
    targets_path.write_text("00_PreCalling/WGS-01.g.vcf.gz\n", encoding="utf-8")
    monkeypatch.setenv("WGS_CONFIG_ROOTS", str(tmp_path))
    monkeypatch.setenv("WGS_FASTQ_ROOTS", str(tmp_path))
    request = {
        "analysis_id": "WGS_20260714_123456_A1B2C3",
        "host_workdir": str(workdir),
        "precalling_config_path": str(config_path),
        "downstream_config_path": str(downstream_path),
        "targets_path": str(targets_path),
        "input_sha256": {
            "precalling_config": "0" * 64,
            "downstream_config": "0" * 64,
            "targets": "0" * 64,
        },
    }

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        prepare_run(request)
