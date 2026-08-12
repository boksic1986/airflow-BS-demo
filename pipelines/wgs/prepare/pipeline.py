from __future__ import annotations

import copy
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from .config_loader import dump_yaml
from .runtime import batch_execution_config


ZDFS_EXCLUDED_PROJECTS = {"Q0079", "Q0080", "Q0081", "Q0082"}


def _copy_item(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=True)
    else:
        shutil.copy2(source, destination)


def _project_relative(value: str, project_root: Path) -> Path | None:
    if value.startswith("/projectDir/"):
        return Path(value.removeprefix("/projectDir/"))
    path = Path(value).expanduser()
    if path.is_absolute():
        try:
            return path.resolve().relative_to(project_root.resolve())
        except ValueError:
            return None
    return None


def copy_pipeline_snapshot(project_root: Path | str, template: Dict[str, Any], destination: Path | str) -> Path:
    root = Path(project_root).resolve()
    pipeline = Path(destination)
    pipeline.mkdir(parents=True, exist_ok=True)
    for relative in (Path("WGS_pipe.smk"), Path("rule"), Path("cfg")):
        source = root / relative
        if not source.exists():
            raise FileNotFoundError(f"pipeline 必需源文件不存在: {source}")
        _copy_item(source, pipeline / relative)
    # These helpers are imported while the Snakefile is parsed.  They are part
    # of the immutable runtime contract rather than a batch-specific script
    # path, so make them explicit snapshot members.
    for relative in (
        Path("script/runtime_overlay.py"),
        Path("script/performance_benchmark.py"),
    ):
        source = root / relative
        if not source.is_file():
            raise FileNotFoundError(f"pipeline runtime helper is missing: {source}")
        _copy_item(source, pipeline / relative)
    for key, value in template.get("src", {}).items():
        if not isinstance(value, str):
            continue
        relative = _project_relative(value, root)
        if relative is None:
            continue
        source = root / relative
        if not source.exists():
            raise FileNotFoundError(f"config src.{key} 指向的仓库文件不存在: {source}")
        _copy_item(source, pipeline / relative)
    return pipeline


def _replace_prefix(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {key: _replace_prefix(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_prefix(item, old, new) for item in value]
    if isinstance(value, str):
        return value.replace(old, new)
    return value


def _rewrite_group(group: Dict[str, Any], root: str) -> Dict[str, Any]:
    return _replace_prefix(group, "/projectDir", root)


def build_runtime_metadata(sampleinfo: pd.DataFrame) -> Dict[str, Any]:
    family_probands: Dict[str, List[str]] = defaultdict(list)
    family_members: Dict[str, List[str]] = defaultdict(list)
    for _, row in sampleinfo.iterrows():
        family = str(row.get("家系编号", ""))
        if not family:
            continue
        data_id = str(row.get("数据编号", ""))
        family_members[family].append(data_id)
        if row.get("家系关系") == "先证者":
            family_probands[family].append(data_id)
    for family, members in family_members.items():
        if not family_probands[family] and members:
            family_probands[family].append(members[0])

    panel: List[str] = []
    sample: List[str] = []
    phenotype: Dict[str, str] = {}
    pedigree_members: Dict[str, List[str]] = defaultdict(list)
    pedigree_relations: Dict[str, List[str]] = defaultdict(list)
    trio2proband: Dict[str, str] = {}
    sample2pedigree: List[str] = []
    hospital_lists: Dict[str, List[str]] = defaultdict(list)
    bkw_proband_only: List[str] = []

    for _, row in sampleinfo.iterrows():
        data_id = str(row.get("数据编号", ""))
        sample.append(data_id)
        panel.append(str(row.get("检测方法", "")))
        phenotype[data_id] = str(row.get("英文关键词", "")).replace("|", ",")
        family = str(row.get("家系编号", ""))
        relation = str(row.get("家系关系", ""))
        hospital = str(row.get("送检医院", ""))
        item_code = str(row.get("项目编号", ""))
        doctor = str(row.get("送检医生", ""))
        count = int(row.get("家系人数", 1)) if str(row.get("家系人数", "")).isdigit() else 1
        if family:
            for proband in family_probands[family]:
                if relation != "先证者" or data_id == proband:
                    pedigree_id = f"{family}_{proband}"
                    pedigree_members[pedigree_id].append(data_id)
                    pedigree_relations[pedigree_id].append(relation)
                    sample2pedigree.append(f"{data_id}:{pedigree_id}")
                    if relation == "先证者" and data_id == proband:
                        trio2proband[pedigree_id] = data_id
        if count == 1 and hospital == "上海市儿科医学研究所" and item_code not in ZDFS_EXCLUDED_PROJECTS:
            hospital_lists["SHEYsampleList"].append(f"{family}_{data_id}")
        elif count > 1 and relation == "先证者" and not re.search(r"[A-Z]$", family):
            family_data_id = f"{family}_{data_id}"
            if hospital == "上海汉春医疗科技有限公司":
                hospital_lists["SHHCsampleList"].append(family_data_id)
            elif hospital == "上海市新华医院":
                hospital_lists["SHXHsampleList"].append(family_data_id)
            elif hospital == "郑州大学第三附属医院" and item_code not in ZDFS_EXCLUDED_PROJECTS:
                hospital_lists["ZDFSsampleList"].append(family_data_id)
            elif hospital == "上海市儿科医学研究所" and item_code not in ZDFS_EXCLUDED_PROJECTS:
                hospital_lists["SHEYsampleList"].append(family_data_id)
            elif hospital == "山东山大附属生殖医院有限公司":
                hospital_lists["SDSZsampleList"].append(family_data_id)
        if hospital == "上海汉春医疗科技有限公司":
            hospital_lists["SHHCsampleList"].append(data_id)
        elif hospital == "上海市新华医院":
            hospital_lists["SHXHsampleList"].append(data_id)
        elif hospital == "郑州大学第三附属医院" and item_code not in ZDFS_EXCLUDED_PROJECTS:
            hospital_lists["ZDFSsampleList"].append(data_id)
        elif hospital == "中国医学科学院北京协和医院" and doctor == "吴老师":
            hospital_lists["BJXHsampleList"].append(data_id)
        elif hospital == "上海市儿科医学研究所" and item_code not in ZDFS_EXCLUDED_PROJECTS:
            hospital_lists["SHEYsampleList"].append(data_id)
        elif hospital == "山东山大附属生殖医院有限公司":
            hospital_lists["SDSZsampleList"].append(data_id)
        if hospital == "北京金域医学检验实验室有限公司":
            hospital_lists["BKWsampleList"].append(data_id)
            if str(row.get("家系人数", "")) == "1":
                bkw_proband_only.append(f"{family}_{data_id}")

    pedigree: List[str] = []
    trio: List[str] = []
    trio_pair: List[str] = []
    mt_pedigree: List[str] = []
    cs: List[str] = []
    bkw_pedigree: List[str] = []
    bkw_samples = set(hospital_lists["BKWsampleList"])
    for pedigree_id, members in pedigree_members.items():
        if len(members) <= 1:
            continue
        relations = set(pedigree_relations[pedigree_id])
        proband = trio2proband.get(pedigree_id, "")
        pedigree.append(pedigree_id)
        if bkw_samples.intersection(members):
            bkw_pedigree.append(pedigree_id)
        has_trio = {"先证者", "父亲", "母亲"}.issubset(relations)
        has_spouse = bool({"丈夫", "妻子"}.intersection(relations))
        if has_trio:
            trio.append(pedigree_id)
            trio_pair.append(f"{pedigree_id}:{proband}")
        if "先证者" in relations and ({"母亲", "丈夫", "妻子"}.intersection(relations)):
            mt_pedigree.append(pedigree_id)
        if "先证者" in relations and (has_spouse or has_trio):
            cs.append(pedigree_id)
        if has_trio and has_spouse:
            cs.append(pedigree_id + "_1")

    def unique(values: Iterable[str]) -> List[str]:
        return sorted({value for value in values if value})

    sample_dict = {
        "sample": unique(sample),
        "pedigree": unique(pedigree),
        "sample2pedigree": unique(sample2pedigree),
        "trio": unique(trio),
        "trioPair": unique(trio_pair),
        "CS": unique(cs),
        "mtPedigreeList": unique(mt_pedigree),
        "SHHCsampleList": unique(hospital_lists["SHHCsampleList"]),
        "ZDFSsampleList": unique(hospital_lists["ZDFSsampleList"]),
        "BJXHsampleList": unique(hospital_lists["BJXHsampleList"]),
        "SHEYsampleList": unique(hospital_lists["SHEYsampleList"]),
        "SHXHsampleList": unique(hospital_lists["SHXHsampleList"]),
        "SDSZsampleList": unique(hospital_lists["SDSZsampleList"]),
        "BKWsampleList": unique(hospital_lists["BKWsampleList"]),
        "BKWpedigree": unique(bkw_pedigree),
        "BKWprobandonly": unique(bkw_proband_only),
    }
    return {"panel": unique(panel), "phenotype": phenotype, **sample_dict}


def build_analysis_config(
    template: Dict[str, Any],
    analysis_dir: Path | str,
    pipeline_dir: Path | str,
    sampleinfo_path: Path | str,
    raw_dir: Path | str,
    batch_name: str,
    resource_root: Path | str,
    use_reference: str,
    test: bool,
    sampleinfo: pd.DataFrame,
    executor: str,
) -> Dict[str, Any]:
    config = copy.deepcopy(template)
    analysis = str(Path(analysis_dir))
    pipeline = str(Path(pipeline_dir))
    resources = str(Path(resource_root))
    config["src"] = _rewrite_group(config.get("src", {}), pipeline)
    config["biosoft"] = _rewrite_group(config.get("biosoft", {}), pipeline)
    for key in ("mail_cfg", "qc_cfg"):
        if isinstance(config.get(key), str):
            config[key] = config[key].replace("/projectDir", pipeline)
    for group in ("genome", "bed", "database", "cnv_native"):
        config[group] = _rewrite_group(config.get(group, {}), resources)
    for protected in (
        "images",
        "containers",
        "container_tools",
        "workloads",
        "runtime",
        "runtime_binds",
        "sentieon_license_secret",
    ):
        config.pop(protected, None)
    config["execution"] = batch_execution_config(executor)
    config["workflow"] = {
        "schema_version": 3,
        "snakefile": "WGS_pipe.smk",
        "target": "full_wgs_acceptance_all",
    }
    config.update(
        {
            "fastqDir": str(Path(raw_dir)),
            "workDir": analysis,
            "sample_info": str(Path(sampleinfo_path)),
            "new_sample_info": str(Path(sampleinfo_path)),
            "batch": batch_name,
            "use_reference": use_reference,
        }
    )
    config["fastqPath"] = str(Path(raw_dir))
    for key in ("webPath", "clinicalPath", "SHHCPath", "newWebPath", "qcClinicalPath"):
        if test and isinstance(config.get(key), str):
            config[key] = config[key] + "_test"
    if test and config.get("newWebPath2test"):
        config["newWebPath2"] = config["newWebPath2test"]
    if config.get("newWebPath"):
        config["newSampleinfoPath"] = str(Path(config["newWebPath"]) / "sampleinfo")
    config.pop("VariantTypeSet", None)
    config.update(build_runtime_metadata(sampleinfo))
    keyword_name = config.get("database", {}).get("keyWords2GeneFile", "phenotype_key_word_gene_list.txt")
    if not os.path.isabs(str(keyword_name)):
        config["database"]["keyWords2GeneFile"] = str(Path(analysis_dir) / str(keyword_name))
    return config


def write_zdfs_sampleinfo(sampleinfo: pd.DataFrame, path: Path | str) -> None:
    selected = sampleinfo[
        (sampleinfo["送检医院"] == "郑州大学第三附属医院")
        & (~sampleinfo["项目编号"].isin(ZDFS_EXCLUDED_PROJECTS))
    ]
    selected[["样本条码", "家系编号", "家系名", "姓名", "数据编号"]].to_csv(
        path, sep="\t", index=False, encoding="utf-8"
    )


def generate_upload_scripts(
    analysis_dir: Path | str,
    pipeline_dir: Path | str,
    config_path: Path | str,
    sampleinfo_path: Path | str,
    test: bool,
    python_executable: Path | str = sys.executable,
    display_analysis_dir: Path | str | None = None,
) -> None:
    upload_all = Path(pipeline_dir) / "script" / "uploadAll.py"
    command = [str(python_executable), str(upload_all), "--config", str(config_path), "--sampleinfo", str(sampleinfo_path)]
    if test:
        command.append("--test")
    completed = subprocess.run(command, cwd=analysis_dir, capture_output=True, text=True)
    display = str(Path(display_analysis_dir)) if display_analysis_dir is not None else str(Path(analysis_dir))
    for content, stream in ((completed.stdout, sys.stdout), (completed.stderr, sys.stderr)):
        if content:
            rendered = content.replace(str(Path(analysis_dir)), display)
            print(rendered, end="" if rendered.endswith("\n") else "\n", file=stream)
    completed.check_returncode()


def replace_staging_paths(analysis_dir: Path | str, staging_root: Path | str, final_root: Path | str) -> None:
    staging = str(Path(staging_root))
    final = str(Path(final_root))
    config_path = Path(analysis_dir) / "config.yaml"
    from .config_loader import load_yaml

    config = _replace_prefix(load_yaml(config_path), staging, final)
    dump_yaml(config, config_path)
    unnormalized_sampleinfo_dir = final + "/../sampleinfo"
    sampleinfo_dir = str(Path(final).parent / "sampleinfo")
    for path in Path(analysis_dir).glob("*.sh"):
        text = path.read_text(encoding="utf-8")
        text = text.replace(staging, final).replace(unnormalized_sampleinfo_dir, sampleinfo_dir)
        path.write_text(text, encoding="utf-8")
