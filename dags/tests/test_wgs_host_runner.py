from pathlib import Path
import hashlib
import signal
import sys

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import wgs_host_runner
from wgs_host_runner import (
    _precalling_targets,
    _validate_wgs_config,
    build_snakemake_command,
    prepare_run,
    parse_forced_command,
    resolve_request_path,
)


def test_pre_calling_targets_use_config_sample_subset(tmp_path) -> None:
    sample_info = tmp_path / "samples.tsv"
    sample_info.write_text(
        "sample_id\n" + "\n".join(f"WGS-{index:02d}" for index in range(1, 17)) + "\n",
        encoding="utf-8",
    )
    config = tmp_path / "precalling.yaml"
    config.write_text(
        "sample_info: "
        + str(sample_info)
        + "\nsample:\n  - WGS-01\n  - WGS-02\n  - WGS-03\n",
        encoding="utf-8",
    )

    targets = _precalling_targets(config)

    assert len(targets) == 12
    assert {Path(target).name.split(".")[0] for target in targets} == {
        "WGS-01",
        "WGS-02",
        "WGS-03",
    }
    assert {Path(target).name for target in targets if target.endswith(".blk")} == {
        "WGS-01.blk",
        "WGS-02.blk",
        "WGS-03.blk",
    }


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
    assert "--dry-run" in command
    assert "--forceall" not in command
    assert "--reason" not in command
    assert "--stats" not in command
    assert "--cluster" not in command


def test_runner_rejects_real_execution_when_gate_defaults_false(tmp_path, monkeypatch) -> None:
    workdir = tmp_path / "run"
    (workdir / "config").mkdir(parents=True)
    (workdir / "config" / "targets.resolved.txt").write_text(
        "01_SNV/demo.flt.tsv\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("WGS_ALLOW_EXECUTION", raising=False)

    with pytest.raises(ValueError, match="dry-run"):
        build_snakemake_command(
            {
                "analysis_id": "WGS_20260714_123456_A1B2C3",
                "host_workdir": str(workdir),
                "wgs_dry_run": False,
            },
            stage="variant_analysis",
            snakemake_bin=Path("/opt/wgs-s9/bin/snakemake"),
            pipeline_root=Path("/opt/airflow-wgs/pipelines/wgs_s9"),
        )


def test_terminate_process_group_targets_exact_child_session_and_waits(monkeypatch) -> None:
    kill_calls = []
    wait_calls = []

    class FakeProcess:
        pid = 4321

        def wait(self, timeout=None):
            wait_calls.append(timeout)
            return -signal.SIGTERM

    monkeypatch.setattr(wgs_host_runner.os, "killpg", lambda pgid, signum: kill_calls.append((pgid, signum)))

    return_code = wgs_host_runner._terminate_process_group(
        FakeProcess(),
        signal_number=signal.SIGTERM,
    )

    assert kill_calls == [(4321, signal.SIGTERM)]
    assert wait_calls
    assert return_code == -signal.SIGTERM


def test_stream_process_keyboard_interrupt_terminates_new_process_group(tmp_path, monkeypatch) -> None:
    popen_kwargs = {}
    kill_calls = []
    wait_calls = []

    class FakeProcess:
        pid = 9876
        stdout = None
        stderr = None

        def wait(self, timeout=None):
            wait_calls.append(timeout)
            return -signal.SIGTERM

    class InterruptingMonitor:
        def __init__(self, **kwargs):
            pass

        def start(self):
            raise KeyboardInterrupt

        def stop(self, **kwargs):
            pass

    def fake_popen(command, **kwargs):
        popen_kwargs.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(wgs_host_runner.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(wgs_host_runner, "ResourceMonitor", InterruptingMonitor)
    monkeypatch.setattr(wgs_host_runner.os, "killpg", lambda pgid, signum: kill_calls.append((pgid, signum)))

    with pytest.raises(KeyboardInterrupt):
        wgs_host_runner._stream_process(
            ["/bin/bash", "-lc", "sleep 60"],
            cwd=tmp_path,
            env={},
            stdout_path=tmp_path / "stdout.log",
            stderr_path=tmp_path / "stderr.log",
            stage="pre_calling",
        )

    assert popen_kwargs["start_new_session"] is True
    assert kill_calls == [(9876, signal.SIGTERM)]
    assert wait_calls


def test_stream_process_sigterm_terminates_new_process_group(tmp_path, monkeypatch) -> None:
    kill_calls = []
    installed_handlers = {}

    class FakeProcess:
        pid = 8765
        stdout = None
        stderr = None

        def wait(self, timeout=None):
            return -signal.SIGTERM

    class TerminatingMonitor:
        def __init__(self, **kwargs):
            pass

        def start(self):
            installed_handlers[signal.SIGTERM](signal.SIGTERM, None)

        def stop(self, **kwargs):
            pass

    def fake_signal(signum, handler):
        previous = installed_handlers.get(signum, signal.SIG_DFL)
        installed_handlers[signum] = handler
        return previous

    monkeypatch.setattr(wgs_host_runner.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())
    monkeypatch.setattr(wgs_host_runner, "ResourceMonitor", TerminatingMonitor)
    monkeypatch.setattr(wgs_host_runner.os, "killpg", lambda pgid, signum: kill_calls.append((pgid, signum)))
    monkeypatch.setattr(wgs_host_runner.signal, "getsignal", lambda _signum: signal.SIG_DFL)
    monkeypatch.setattr(wgs_host_runner.signal, "signal", fake_signal)

    with pytest.raises(SystemExit) as caught:
        wgs_host_runner._stream_process(
            ["/bin/bash", "-lc", "sleep 60"],
            cwd=tmp_path,
            env={},
            stdout_path=tmp_path / "stdout.log",
            stderr_path=tmp_path / "stderr.log",
            stage="pre_calling",
        )

    assert caught.value.code == 128 + signal.SIGTERM
    assert kill_calls == [(8765, signal.SIGTERM)]
    assert installed_handlers[signal.SIGTERM] == signal.SIG_DFL


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


def test_prepare_links_only_historical_batch_context(tmp_path, monkeypatch) -> None:
    workdir = tmp_path / "runs" / "WGS_20260714_123456_A1B2C3"
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True)
    sample_info = tmp_path / "samples.tsv"
    sample_info.write_text("sample_id\nWGS-NEW\nWGS-HIST\n", encoding="utf-8")
    fastq_dir = tmp_path / "fastq"
    fastq_dir.mkdir()
    source_root = tmp_path / "source-run"
    source_precalling = source_root / "00_PreCalling"
    source_precalling.mkdir(parents=True)
    (source_precalling / "WGS-NEW.blk").write_text("stale-new", encoding="utf-8")
    (source_precalling / "WGS-HIST.blk").write_text("history", encoding="utf-8")
    (source_precalling / "WGS-HIST.log").write_text("history log", encoding="utf-8")
    source_qc = source_root / "07_QC"
    source_qc.mkdir()
    (source_qc / "WGS-HIST.template.json").write_text("{}", encoding="utf-8")
    precalling = config_dir / "wgs.precalling.requested.yaml"
    downstream = config_dir / "wgs.downstream.requested.yaml"
    targets = config_dir / "targets.requested.txt"
    precalling.write_text(
        f"sample_info: {sample_info}\nfastqDir: {fastq_dir}\nsample:\n  - WGS-NEW\n",
        encoding="utf-8",
    )
    downstream.write_text(
        f"sample_info: {sample_info}\nfastqDir: {fastq_dir}\nsample:\n  - WGS-NEW\n  - WGS-HIST\n",
        encoding="utf-8",
    )
    targets.write_text("01_SNV/demo.flt.tsv\n", encoding="utf-8")
    env_script = tmp_path / "env.sh"
    env_script.write_text("true\n", encoding="utf-8")
    snakemake = tmp_path / "snakemake"
    snakemake.write_text("#!/bin/sh\n", encoding="utf-8")
    pipeline_root = tmp_path / "pipeline"
    pipeline_root.mkdir()
    for name in ("WGS_pipeline_fastq2vcf.Snakefile", "WGS_pipeline.Snakefile"):
        (pipeline_root / name).write_text("rule all:\n    input: []\n", encoding="utf-8")
    monkeypatch.setattr(wgs_host_runner, "DEFAULT_ENV_SCRIPT", env_script)
    monkeypatch.setattr(wgs_host_runner, "DEFAULT_SNAKEMAKE_BIN", snakemake)
    monkeypatch.setattr(wgs_host_runner, "DEFAULT_PIPELINE_ROOT", pipeline_root)
    monkeypatch.setenv("WGS_CONFIG_ROOTS", str(tmp_path))
    monkeypatch.setenv("WGS_FASTQ_ROOTS", str(tmp_path))
    monkeypatch.setenv("WGS_PRECALLING_SOURCE_ROOTS", str(tmp_path))
    monkeypatch.setenv("WGS_QC_SOURCE_ROOTS", str(tmp_path))
    request = {
        "analysis_id": "WGS_20260714_123456_A1B2C3",
        "pipeline": "wgs",
        "wgs_stage": "full",
        "host_workdir": str(workdir),
        "precalling_config_path": str(precalling),
        "downstream_config_path": str(downstream),
        "targets_path": str(targets),
        "source_analysis_root": str(source_root),
        "input_sha256": {
            "precalling_config": hashlib.sha256(precalling.read_bytes()).hexdigest(),
            "downstream_config": hashlib.sha256(downstream.read_bytes()).hexdigest(),
            "targets": hashlib.sha256(targets.read_bytes()).hexdigest(),
        },
    }

    prepare_run(request)

    assert (workdir / "00_PreCalling" / "WGS-HIST.blk").is_symlink()
    assert (workdir / "00_PreCalling" / "WGS-HIST.log").is_symlink()
    assert not (workdir / "00_PreCalling" / "WGS-NEW.blk").exists()
    resolved_downstream = yaml.safe_load(
        (workdir / "config" / "wgs.downstream.resolved.yaml").read_text(encoding="utf-8")
    )
    assert resolved_downstream["fastqDir"] == str(workdir.resolve())


def test_prepare_recovers_historical_blk_beside_resolved_precalling_link(tmp_path, monkeypatch) -> None:
    workdir = tmp_path / "runs" / "WGS_20260714_123456_A1B2C3"
    config_dir = workdir / "config"
    config_dir.mkdir(parents=True)
    sample_info = tmp_path / "samples.tsv"
    sample_info.write_text("sample_id\nWGS-NEW\nWGS-HIST\n", encoding="utf-8")
    fastq_dir = tmp_path / "fastq"
    fastq_dir.mkdir()
    upstream = tmp_path / "upstream" / "00_PreCalling"
    upstream.mkdir(parents=True)
    (upstream / "WGS-HIST.g.vcf.gz").write_text("gvcf", encoding="utf-8")
    (upstream / "WGS-HIST.blk").write_text("blocks", encoding="utf-8")
    (upstream / "WGS-HIST.log").write_text("block log", encoding="utf-8")
    upstream_qc = upstream.parent / "07_QC"
    upstream_qc.mkdir()
    (upstream_qc / "WGS-HIST.template.json").write_text("{}", encoding="utf-8")
    source_root = tmp_path / "source-run"
    source_precalling = source_root / "00_PreCalling"
    source_precalling.mkdir(parents=True)
    (source_precalling / "WGS-HIST.g.vcf.gz").symlink_to(upstream / "WGS-HIST.g.vcf.gz")
    precalling = config_dir / "wgs.precalling.requested.yaml"
    downstream = config_dir / "wgs.downstream.requested.yaml"
    targets = config_dir / "targets.requested.txt"
    precalling.write_text(
        f"sample_info: {sample_info}\nfastqDir: {fastq_dir}\nsample:\n  - WGS-NEW\n",
        encoding="utf-8",
    )
    downstream.write_text(
        f"sample_info: {sample_info}\nfastqDir: {fastq_dir}\nsample:\n  - WGS-NEW\n  - WGS-HIST\n",
        encoding="utf-8",
    )
    targets.write_text("01_SNV/demo.flt.tsv\n", encoding="utf-8")
    env_script = tmp_path / "env.sh"
    env_script.write_text("true\n", encoding="utf-8")
    snakemake = tmp_path / "snakemake"
    snakemake.write_text("#!/bin/sh\n", encoding="utf-8")
    pipeline_root = tmp_path / "pipeline"
    pipeline_root.mkdir()
    for name in ("WGS_pipeline_fastq2vcf.Snakefile", "WGS_pipeline.Snakefile"):
        (pipeline_root / name).write_text("rule all:\n    input: []\n", encoding="utf-8")
    monkeypatch.setattr(wgs_host_runner, "DEFAULT_ENV_SCRIPT", env_script)
    monkeypatch.setattr(wgs_host_runner, "DEFAULT_SNAKEMAKE_BIN", snakemake)
    monkeypatch.setattr(wgs_host_runner, "DEFAULT_PIPELINE_ROOT", pipeline_root)
    monkeypatch.setenv("WGS_CONFIG_ROOTS", str(tmp_path))
    monkeypatch.setenv("WGS_FASTQ_ROOTS", str(tmp_path))
    monkeypatch.setenv("WGS_PRECALLING_SOURCE_ROOTS", str(tmp_path))
    monkeypatch.setenv("WGS_QC_SOURCE_ROOTS", str(tmp_path))
    request = {
        "analysis_id": "WGS_20260714_123456_A1B2C3",
        "pipeline": "wgs",
        "wgs_stage": "full",
        "host_workdir": str(workdir),
        "precalling_config_path": str(precalling),
        "downstream_config_path": str(downstream),
        "targets_path": str(targets),
        "source_analysis_root": str(source_root),
        "input_sha256": {
            "precalling_config": hashlib.sha256(precalling.read_bytes()).hexdigest(),
            "downstream_config": hashlib.sha256(downstream.read_bytes()).hexdigest(),
            "targets": hashlib.sha256(targets.read_bytes()).hexdigest(),
        },
    }

    prepare_run(request)
    prepare_run(request)

    assert (workdir / "00_PreCalling" / "WGS-HIST.g.vcf.gz").resolve() == (
        upstream / "WGS-HIST.g.vcf.gz"
    ).resolve()
    assert (workdir / "00_PreCalling" / "WGS-HIST.blk").resolve() == (
        upstream / "WGS-HIST.blk"
    ).resolve()
    assert (workdir / "00_PreCalling" / "WGS-HIST.log").resolve() == (
        upstream / "WGS-HIST.log"
    ).resolve()
    assert (workdir / "07_QC" / "WGS-HIST.template.json").resolve() == (
        upstream_qc / "WGS-HIST.template.json"
    ).resolve()
