#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pandas as pd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prepare.config_loader import (  # noqa: E402
    DEFAULT_PREPARE_CONFIG,
    analysis_name,
    dump_yaml,
    load_analysis_template,
    load_prepare_config,
    version_code,
)
from prepare.cce import build_cce_batch_config, write_cce_steps  # noqa: E402
from prepare.keywords import generate_keyword_file, validate_english_keywords  # noqa: E402
from prepare.metadata import build_metadata_provider  # noqa: E402
from prepare.pending import create_raw_links, select_analysis_samples, update_pending  # noqa: E402
from prepare.pipeline import (  # noqa: E402
    build_analysis_config,
    copy_pipeline_snapshot,
    generate_upload_scripts,
    replace_staging_paths,
    write_zdfs_sampleinfo,
)
from prepare.runtime import normalize_run_mode, write_step1  # noqa: E402
from prepare.sampleinfo import SAMPLEINFO_COLUMNS, generate_sampleinfo, write_sampleinfo  # noqa: E402
from prepare.samplelists import (  # noqa: E402
    SamplelistRepository,
    load_batch_samples,
    parse_batches,
    read_reanalysis_samples,
)
from script.runtime_overlay import load_runtime_overlay  # noqa: E402


def _path_option(value: str | None, default: str) -> str:
    return str(Path(value or default).expanduser().resolve())


def _validate_sampleinfo_args(args: argparse.Namespace) -> None:
    if args.reanalysis:
        if args.batch:
            raise ValueError("重分析模式禁止使用 --batch")
        if not args.samplelist:
            raise ValueError("重分析模式必须使用 --samplelist")
    else:
        if not args.batch:
            raise ValueError("普通模式必须使用 --batch")
        if args.samplelist:
            raise ValueError("普通模式的样本来自批次 Samplelist 目录，不使用 --samplelist")


def run_sampleinfo(
    args: argparse.Namespace,
    prepare_config: Dict[str, Any] | None = None,
    provider=None,
) -> Path:
    config = prepare_config or load_prepare_config(args.prepare_config)
    template = load_analysis_template(config, args.config_template)
    _validate_sampleinfo_args(args)
    platform = args.platform or config["defaults"]["platform"]
    samplelist_dir = _path_option(args.samplelist_dir, config["defaults"]["samplelist_dir"])
    sequence_rows = None
    if args.reanalysis:
        sequence_rows = read_reanalysis_samples(args.samplelist)
        sample_ids = sequence_rows["sampleId"].tolist()
    else:
        batches = parse_batches(args.batch)
        sequence_rows = load_batch_samples(
            samplelist_dir,
            batches,
            platform,
            config["samplelist"]["filename_glob"],
            config["samplelist"]["panel"],
            config["samplelist"].get("excluded_project_codes", []),
        )
        sample_ids = list(dict.fromkeys(sequence_rows["sampleId"].astype(str).tolist()))
    provider = provider or build_metadata_provider(config, args.metadata_source, args.test)
    frame = generate_sampleinfo(
        sample_ids,
        provider,
        args.analysis_batch,
        template["version"],
        sequence_rows=sequence_rows,
        reanalysis=args.reanalysis,
    )
    if args.reanalysis and not frame.empty:
        missing_batch = frame["上机批次"].astype(str).str.strip() == ""
        if missing_batch.any():
            missing_samples = ",".join(frame.loc[missing_batch, "样本编号"].astype(str))
            raise ValueError(
                "重分析 samplelist 缺少以下生成样本的上机批次，请补充为“样本编号,上机批次”："
                + missing_samples
            )
    if frame.empty:
        raise RuntimeError("没有可写入的有效样本，不生成空 sampleinfo")
    batch_name = analysis_name(args.analysis_batch, platform, template["version"])
    output = Path(args.outpath).expanduser().resolve() / "sampleinfo" / f"{batch_name}.sampleinfo.txt"
    if output.exists():
        raise FileExistsError(f"sampleinfo 已存在，拒绝覆盖: {output}")
    write_sampleinfo(frame, output)
    print(f"sampleinfo 已生成：{output}")
    return output


def _load_input_sampleinfo(path: Path | str) -> pd.DataFrame:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"sampleinfo 不存在: {source}")
    frame = pd.read_csv(source, sep="\t", dtype=str, keep_default_na=False).fillna("")
    required_columns = SAMPLEINFO_COLUMNS[:-3]
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"sampleinfo 缺少列：{','.join(missing)}")
    for column in SAMPLEINFO_COLUMNS[-3:]:
        if column not in frame.columns:
            frame[column] = ""
    batches = [value for value in frame["分析批次"].astype(str).str.strip().unique() if value]
    if len(batches) != 1:
        raise ValueError(f"sampleinfo 的分析批次必须且只能有一个非空值，实际为：{','.join(batches)}")
    return frame[SAMPLEINFO_COLUMNS]


def _safe_empty_analysis_dir(path: Path) -> None:
    if not path.exists():
        return
    if not path.is_dir() or any(path.iterdir()):
        raise FileExistsError(f"分析目录已存在，拒绝覆盖: {path}")
    path.rmdir()


def _print_pending_notices(pending: pd.DataFrame, pending_path: Path) -> None:
    if pending.empty:
        return
    for _, row in pending.iterrows():
        sample_id = str(row.get("样本编号", "")).strip() or "."
        order_id = str(row.get("订单编号", "")).strip() or "."
        reason = str(row.get("pending_reason", "")).strip() or "未记录原因"
        print(f"提示：样本 {sample_id}（订单 {order_id}）已进入 pending：{reason}")
    print(f"提示：pending 文件已更新：{pending_path}（本次写入 {len(pending)} 个样本）")


def run_analysis(args: argparse.Namespace, prepare_config: Dict[str, Any] | None = None) -> Path | None:
    args.run_mode = normalize_run_mode(args.run_mode)
    config = prepare_config or load_prepare_config(args.prepare_config)
    template = load_analysis_template(config, args.config_template)
    source_sampleinfo = Path(args.sampleinfo).expanduser().resolve()
    source_frame = _load_input_sampleinfo(source_sampleinfo)
    source_frame["version"] = source_frame["version"].where(
        source_frame["version"].astype(str).str.strip() != "",
        version_code(template["version"]),
    )
    analysis_batch = str(source_frame.iloc[0]["分析批次"]).strip()
    platform = args.platform or config["defaults"]["platform"]
    batch_name = analysis_name(analysis_batch, platform, template["version"])
    output_root = Path(args.outpath).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    if args.run_mode == "cce":
        for label in (
            "run_id", "pipeline_release", "cce_master", "cce_fastq_dir",
            "cce_fastq_md5_manifest",
        ):
            if not getattr(args, label, None):
                raise ValueError(f"CCE mode requires --{label.replace('_', '-')}")
        final_dir = output_root / f"{batch_name}-{args.run_id}"
    else:
        final_dir = output_root / batch_name
    _safe_empty_analysis_dir(final_dir)

    samplelist_dir = _path_option(args.samplelist_dir, config["defaults"]["samplelist_dir"])
    repository = SamplelistRepository(
        samplelist_dir,
        config["samplelist"].get("filename_glob", "Samplelist_*.txt"),
    )
    selection = select_analysis_samples(
        source_frame,
        repository,
        _path_option(args.fastq_root, config["defaults"]["fastq_root"]),
        _path_option(args.basecount_dir, config["defaults"]["basecount_dir"]),
        config["defaults"]["fastq_ready_flag"],
        config["data_check"],
        skip_data_check=args.skip_data_check,
        source_sampleinfo=str(source_sampleinfo),
    )
    for warning in selection.warnings:
        print(warning)
    pending_path = output_root / "prepare" / "pending_samples.tsv"
    if selection.kept.empty:
        update_pending(pending_path, selection.pending, [])
        _print_pending_notices(selection.pending, pending_path)
        print("所有订单均未满足阻断检查，已写入统一 pending；不创建分析目录。")
        return None

    staging = Path(tempfile.mkdtemp(prefix=f".{batch_name}.", dir=output_root))
    staged_zdfs = staging / ".zdfs.sampleinfo.txt"
    final_sampleinfo = final_dir / (
        "sampleinfo.tsv" if args.run_mode == "cce" else f"{batch_name}.sampleinfo.txt"
    )
    staged_sampleinfo = staging / final_sampleinfo.name
    try:
        prepare_python = config["runtime"]["python"]
        for directory in ("raw", "log", "tmp"):
            (staging / directory).mkdir(parents=True, exist_ok=True)
        write_sampleinfo(selection.kept, staged_sampleinfo)
        if args.run_mode != "cce":
            for warning in create_raw_links(staging / "raw", selection.links):
                print(warning.replace(str(staging), str(final_dir)))
            pipeline_dir = copy_pipeline_snapshot(config["project_root"], template, staging / "pipeline")
        else:
            pipeline_dir = Path(config["project_root"])
        source_config = build_analysis_config(
            template,
            staging,
            pipeline_dir,
            staged_sampleinfo,
            staging / "raw",
            batch_name,
            config["resource_root"],
            args.use_reference,
            args.test,
            selection.kept,
            args.run_mode,
        )
        if args.run_mode == "cce":
            staging_config = build_cce_batch_config(
                source_config,
                Path(config["project_root"]) / "cfg" / "cce" / "config.full.template.yaml",
                batch=batch_name,
                run_id=args.run_id,
                pipeline_release=args.pipeline_release,
                owner=args.cce_owner,
                fastq_dir=args.cce_fastq_dir,
                workflow_target=args.workflow_target,
            )
            md5_source = Path(args.cce_fastq_md5_manifest).expanduser()
            if md5_source.is_symlink() or not md5_source.is_file():
                raise ValueError("CCE FASTQ MD5 manifest must be a direct file")
            shutil.copyfile(md5_source, staging / "FASTQ.MD5SUMS")
        else:
            staging_config = source_config
        dump_yaml(staging_config, staging / "config.yaml")

        if args.run_mode != "cce":
            keyword_output = staging / config["keywords"]["output_name"]
            database = staging_config.get("database", {})
            generate_keyword_file(
                pipeline_dir / "script" / "b1.hpo2gene.py",
                database.get("hp2gene", ""),
                database.get("hpoPhenotype2Genes", ""),
                keyword_output,
                python_executable=prepare_python,
                display_dir=final_dir,
            )
            validate_english_keywords(selection.kept, keyword_output, staging / config["keywords"]["validation_report"])
        write_zdfs_sampleinfo(selection.kept, staged_zdfs)
        if args.run_mode == "cce":
            write_cce_steps(
                staging,
                run_root=staging_config["run"]["root"],
                run_id=args.run_id,
                master=args.cce_master,
                namespace=args.cce_namespace,
                kubectl_bin=args.cce_kubectl_bin,
                kubeconfig=args.cce_kubeconfig,
                repository_root=args.cce_repository_root,
                evidence_root=args.cce_evidence_root,
                pipeline_dir=(
                    "/workspace/wgs/pipelines/3.9.3/"
                    f"{args.pipeline_release}"
                ),
                workflow_target=args.workflow_target,
            )
        else:
            generate_upload_scripts(
                staging,
                pipeline_dir,
                staging / "config.yaml",
                staged_sampleinfo,
                args.test,
                python_executable=prepare_python,
                display_analysis_dir=final_dir,
            )
            effective_runtime = load_runtime_overlay(
                staging_config, Path(config["project_root"])
            )
            write_step1(
                staging / "Step1_run.sh",
                final_dir,
                args.run_mode,
                config,
                effective_runtime,
                fastq_sources=[spec.source for spec in selection.links],
            )
        replace_staging_paths(staging, staging, final_dir)

        update_pending(pending_path, selection.pending, selection.kept["样本编号"].tolist())
        _print_pending_notices(selection.pending, pending_path)
        os.replace(staging, final_dir)
        final_dir.chmod(0o755)
        zdfs_dir = output_root / "sampleinfo"
        zdfs_dir.mkdir(parents=True, exist_ok=True)
        zdfs_target = zdfs_dir / f"{batch_name}.sampleinfo.郑大附三.txt"
        os.replace(final_dir / staged_zdfs.name, zdfs_target)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    print(f"分析目录已生成：{final_dir}")
    return final_dir


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--outpath", required=True)
    parser.add_argument("--platform", default=None)
    parser.add_argument("--samplelist-dir", default=None)
    parser.add_argument("--prepare-config", default=str(DEFAULT_PREPARE_CONFIG))
    parser.add_argument("--config-template", default=None)
    parser.add_argument("-test", "--test", action="store_true")
    parser.add_argument("-ref", "--use-reference", choices=["all", "ref", "no"], default="all")


def _add_sampleinfo(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--batch")
    parser.add_argument("--analysis-batch", required=True)
    parser.add_argument("--reanalysis", action="store_true")
    parser.add_argument("--samplelist", help="重分析输入文件，每行格式为：样本编号,上机批次")
    parser.add_argument("--metadata-source", choices=["hybrid", "http"], default="hybrid")


def _add_analysis(parser: argparse.ArgumentParser, include_sampleinfo: bool = True) -> None:
    if include_sampleinfo:
        parser.add_argument("--sampleinfo", required=True)
    parser.add_argument("--basecount-dir", default=None)
    parser.add_argument("--fastq-root", default=None)
    parser.add_argument("--skip-data-check", action="store_true")
    parser.add_argument("--run-mode", choices=["sge", "local", "cce", "k8s"], default="sge")
    parser.add_argument("--run-id")
    parser.add_argument("--pipeline-release")
    parser.add_argument("--cce-master")
    parser.add_argument(
        "--cce-fastq-dir",
        help="Read-only OBS CSI path below /obs-data containing the batch FASTQ files",
    )
    parser.add_argument(
        "--cce-fastq-md5-manifest",
        help="Local MD5SUMS file uploaded with config and sampleinfo",
    )
    parser.add_argument(
        "--workflow-target",
        choices=["cloud_wgs_all", "cloud_sentieon_stage_all"],
        default="cloud_wgs_all",
    )
    parser.add_argument("--cce-owner", default="33.chenjiucheng")
    parser.add_argument("--cce-namespace", default="snakemake-ns")
    parser.add_argument("--cce-kubectl-bin", default="/home/chenjc/.local/bin/kubectl")
    parser.add_argument("--cce-kubeconfig", default="/home/chenjc/.kube/bioinfo-cce.yaml")
    parser.add_argument(
        "--cce-repository-root",
        default="/mnt/biodevrwbi/33.chenjiucheng/project/wgs-3.9.3-cloud",
    )
    parser.add_argument(
        "--cce-evidence-root",
        default="/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/wgs393-unified-runtime",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="准备 WGS sampleinfo、分析目录和运行配置")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    sampleinfo_parser = subparsers.add_parser("sampleinfo", help="只生成 sampleinfo")
    _add_common(sampleinfo_parser)
    _add_sampleinfo(sampleinfo_parser)
    analysis_parser = subparsers.add_parser("analysis", help="根据 sampleinfo 生成分析目录")
    _add_common(analysis_parser)
    _add_analysis(analysis_parser)
    all_parser = subparsers.add_parser("all", help="生成 sampleinfo 和分析目录")
    _add_common(all_parser)
    _add_sampleinfo(all_parser)
    _add_analysis(all_parser, include_sampleinfo=False)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        config = load_prepare_config(args.prepare_config)
        if args.subcommand == "sampleinfo":
            run_sampleinfo(args, config)
        elif args.subcommand == "analysis":
            run_analysis(args, config)
        else:
            sampleinfo_path = run_sampleinfo(args, config)
            args.sampleinfo = str(sampleinfo_path)
            run_analysis(args, config)
    except (FileNotFoundError, FileExistsError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"错误：{exc}\n")


if __name__ == "__main__":
    main()
