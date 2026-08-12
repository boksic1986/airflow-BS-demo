"""Load one fixed runtime profile without polluting the batch contract."""

from __future__ import annotations

import copy
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Mapping

import yaml


PROTECTED_RUNTIME_KEYS = {
    "images",
    "workloads",
    "containers",
    "container_tools",
    "container_resources",
    "runtime",
    "runtime_binds",
    "apptainer",
    "shell",
    "sentieon_license_secret",
}
EXECUTOR_ALIASES = {
    "k8s": "cce",
    "cce_kubernetes": "cce",
    "direct_apptainer": "local",
}


def normalize_executor(value: object) -> str:
    executor = str(value or "").strip().lower()
    executor = EXECUTOR_ALIASES.get(executor, executor)
    if executor not in {"sge", "local", "cce"}:
        raise ValueError("execution.executor must be sge, local, or cce")
    return executor


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"runtime config must be a mapping: {path}")
    return value


def _merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _set_dotted_path(config: Dict[str, Any], dotted_key: str, value: str) -> None:
    parts = dotted_key.split(".")
    if len(parts) < 2 or parts[0] not in {
        "reference",
        "database",
        "cnv_native",
        "container_resources",
    }:
        raise ValueError(f"unsupported resource key: {dotted_key}")
    current = config
    for part in parts[:-1]:
        child = current.get(part)
        if child is None:
            child = {}
            current[part] = child
        if not isinstance(child, dict):
            raise ValueError(f"resource key conflicts with non-mapping value: {dotted_key}")
        current = child
    current[parts[-1]] = value


def apply_resource_map(
    config: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    expected_id: str,
    approved_root: str,
) -> Dict[str, Any]:
    """Apply one immutable CCE resource set by logical config key."""

    if manifest.get("schema_version") != 1:
        raise ValueError("resource map schema_version must be 1")
    if manifest.get("resource_set_id") != expected_id:
        raise ValueError("resource map id does not match the fixed runtime contract")
    paths = manifest.get("resource_paths")
    if not isinstance(paths, Mapping) or not paths:
        raise ValueError("resource map must contain resource_paths")
    approved = PurePosixPath(approved_root)
    result = copy.deepcopy(dict(config))
    for key, raw_value in sorted(paths.items()):
        if not isinstance(key, str) or not isinstance(raw_value, str):
            raise ValueError("resource map keys and values must be strings")
        value = PurePosixPath(raw_value)
        if not value.is_absolute() or ".." in value.parts or approved not in value.parents:
            raise ValueError(f"resource path is outside the approved root: {key}")
        _set_dotted_path(result, key, str(value))
    database = result.setdefault("database", {})
    if "keywordFile" in database:
        database["HPO_CHPO_gene"] = database["keywordFile"]
    return result


def _normalized_analysis_schema(batch_config: Mapping[str, Any]) -> Dict[str, Any]:
    """Translate the established 3.9.3 resource keys for the shared Rules."""

    result = copy.deepcopy(dict(batch_config))
    if "reference" in result or "genome" not in result:
        return result
    genome = _merge({}, result.get("genome", {}))
    bed = _merge({}, result.get("bed", {}))
    database = _merge({}, result.get("database", {}))
    biosoft = _merge({}, result.get("biosoft", {}))
    result["reference"] = {
        "MTreference": genome["MTreference"],
        "hg38": {
            "genome": genome["fasta"],
            "known_Mills_indels": genome["known_Mills_indels"],
            "known_1000G_snps": genome["known_1000G_snps"],
            "known_1000G_indels": genome["known_1000G_indels"],
            "dbsnp": genome["dbsnp"],
            "hg38ToHg19Chain": genome["hg38ToHg19Chain"],
            "MTbed": bed["MT_bed"],
            "QC_bed": bed["QC_bed"],
            "geneBed": bed["geneBed"],
            "virtualWESBed": bed["virtualWESBed"],
            "BIN2POS": database["BIN2POS"],
            "ExpansionHunterDatabase": database["expansion"],
            "Pathogenic_UPDBed": database["pathogenicUPD"],
            "REjson": database["expansionCatalog"],
            "SLC25A13_region": database["SLC25A13_region"],
            "bkwgenelist": database["bkwgenelist"],
            "blacklist": database["blacklist"],
            "commonSNP": database["commonSNP"],
            "cytoband": database["cytobandTxt"],
            "disease": database["disease"],
            "exonIntron": database["exonIntron"],
            "geneDisease": database["geneDisease"],
            "gene_MIMnumber": database["gene_MIMnumber"],
            "imprint_gene_bed": database["imprint_gene_bed"],
            "localMaf": database["localMAF"],
            "meiRef": database["meiRef"],
            "polymorphism": database["CNVPolymorphism"],
            "wgEncodeCrgMapability": database["mappability36mer"],
            "wgEncodeCrgMapability100mer": database["mappability100mer"],
            "whitelistV1": database["whitelistV1"],
            "whitelistV1_BKW": database["whitelistV1_BKW"],
            "whitelistV4": database["whitelistV4"],
        },
    }
    aliases = {
        "PARbed": "parBed",
        "transcriptFile": "maneFile",
        "ps1pm5File": "clinvarPS1PM5",
        "psiFile": "TTNPSI",
        "gnomad_exomes": "gnomadWES",
        "gnomad_genomes": "gnomadWGS",
        "spliceai_Indel": "spliceaiINDEL",
        "spliceai_SNV": "spliceaiSNV",
        "hp2geneFile": "hp2gene",
        "hpoPhenotype2GeneFile": "hpoPhenotype2Genes",
        "localMEI_AFfile": "localMeiMafFile",
        "morbidmap": "morbidmapFile",
        "genmap_100mer": "mappability",
        "HPO_CHPO_gene": "keyWords2GeneFile",
        "keywordFile": "phen2gene",
        "vepcache": None,
        "vepcache104": None,
        "vepPlugin": None,
    }
    for target, source in aliases.items():
        if target in database:
            continue
        if source is not None:
            database[target] = database[source]
        elif target == "vepcache":
            database[target] = biosoft["vepCache"]
        elif target == "vepcache104":
            database[target] = biosoft["vepCache104"]
        else:
            database[target] = biosoft["vepPlugin"]
    result["database"] = database
    return result


def load_runtime_overlay(
    batch_config: Mapping[str, Any],
    pipeline_root: Path | str | None = None,
    *,
    resource_manifest: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return an effective config without persisting runtime paths per batch."""

    if not isinstance(batch_config, Mapping):
        raise ValueError("batch config must be a mapping")
    for key in sorted(PROTECTED_RUNTIME_KEYS):
        if key in batch_config:
            raise ValueError(f"batch config contains protected runtime key: {key}")
    normalized_batch = _normalized_analysis_schema(batch_config)
    execution = normalized_batch.get("execution", {})
    if not isinstance(execution, Mapping):
        raise ValueError("execution must be a mapping")
    executor = normalize_executor(execution.get("executor", execution.get("mode")))
    root = Path(pipeline_root or Path(__file__).resolve().parents[1])
    runtime_file = root / "cfg" / "profiles" / executor / "runtime.yaml"
    runtime = _load_yaml(runtime_file)
    if runtime.get("executor") != executor:
        raise ValueError(f"runtime profile executor mismatch: {runtime_file}")
    # images and Secret names belong to the committed profile compiler input.
    # Snakemake only receives the already-resolved Rule container mapping and
    # runtime-neutral tool/path settings.
    runtime_overlay = {
        key: value
        for key, value in runtime.items()
        if key not in {"images", "sentieon_license_secret", "schema_version", "executor"}
    }
    effective = _merge(normalized_batch, runtime_overlay)
    effective.setdefault("execution", {})["executor"] = executor
    if executor == "cce":
        workflow = effective.get("workflow")
        run = effective.get("run")
        runtime_contract = effective.get("runtime")
        if not isinstance(workflow, Mapping) or not isinstance(run, Mapping):
            raise ValueError("CCE batch config requires workflow and run mappings")
        release = str(workflow.get("pipeline_release", "")).strip()
        if not release or "/" in release or release in {".", ".."}:
            raise ValueError("workflow.pipeline_release must be a safe release name")
        owner = str(run.get("owner", "")).strip()
        if not owner or "/" in owner or owner in {".", ".."}:
            raise ValueError("run.owner must be a safe workspace owner")
        resource_set = runtime.get("resource_set")
        if not isinstance(resource_set, Mapping):
            raise ValueError("CCE runtime requires a fixed resource_set contract")
        if resource_manifest is None:
            resource_map_path = Path(str(resource_set.get("map", "")))
            resource_manifest = _load_yaml(resource_map_path)
        effective = apply_resource_map(
            effective,
            resource_manifest,
            expected_id=str(resource_set.get("id", "")),
            approved_root=str(resource_set.get("approved_root", "")),
        )
        effective.setdefault("execution", {})["executor"] = executor
        runtime_contract = effective.get("runtime")
        pipeline_root = PurePosixPath(str(runtime_contract.get("pipeline_root", "")))
        pipeline_dir = pipeline_root / release
        effective["execution"].update(
            pipeline_dir=str(pipeline_dir),
            script_dir=str(pipeline_dir / "script"),
        )
        cloud = effective.setdefault("cloud", {})
        cloud["pipeline_release"] = release
        cloud["code_root"] = str(pipeline_dir)
        cloud["resources_root"] = str(resource_set["approved_root"])
        cloud["approved_resource_roots"] = [str(resource_set["approved_root"])]
        cloud["resource_set_id"] = str(resource_set["id"])
        cloud["resource_map"] = str(resource_set["map"])
        cloud["resources_ready_marker"] = str(resource_set["ready_marker"])
        cloud["sfs_identity"] = {
            "mode": "cce_direct",
            "csi_volume_handle": runtime_contract["sfs_volume_handle"],
        }
    else:
        effective["execution"].update(
            pipeline_dir=str(root),
            script_dir=str(root / "script"),
        )
    return effective


class RuntimeContract:
    """Resolve the fixed container selected for a production Rule."""

    def __init__(self, config: Mapping[str, Any]):
        containers = config.get("containers")
        if not isinstance(containers, Mapping):
            raise ValueError("fixed runtime profile did not provide containers")
        self._containers = containers

    def container(self, rule_name: str) -> str:
        value = self._containers.get(rule_name)
        if not isinstance(value, str) or not value:
            raise ValueError(f"Rule {rule_name} is missing from the fixed runtime profile")
        return value


def runtime_shell_executable(config: Mapping[str, Any]) -> str:
    shell = config.get("shell")
    value = shell.get("executable") if isinstance(shell, Mapping) else None
    if not isinstance(value, str) or not value.startswith("/"):
        raise ValueError("fixed runtime profile requires an absolute shell.executable")
    return value
