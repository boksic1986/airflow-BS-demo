from __future__ import annotations

from collections import Counter
from typing import Any


NIPT_RULE_PHASES = {
    "mapper_v2_manager_ready": "Input QC",
    "fastq_count": "Input QC",
    "map": "Mapping",
    "convert": "CNV",
    "predict": "CNV",
    "bgzip_bin": "CNV",
    "bgzip_seg": "CNV",
    "plot_cnv": "CNV",
    "gccorrect": "Aneuploidy",
    "gccorrect_bgzip": "Aneuploidy",
    "mv_gccorrect_png": "Aneuploidy",
    "aneuploidy_calling_batch": "Aneuploidy",
    "aneuploidy_calling_dynamicref": "Aneuploidy",
    "aneuscreen_direct_ready": "T21 classifier",
    "aneuscreen_loading": "T21 classifier",
    "aneuscreen_predict": "T21 classifier",
    "aneuscreen_loading_correct_matcnv": "T21 classifier",
    "aneuscreen_predict_correct_matcnv": "T21 classifier",
    "cal_fetal_ratio": "Fetal fraction",
    "mapping_qc": "Final QC",
    "pngquant": "Final QC",
    "bgzip_blk": "Final QC",
    "all": "Final QC",
    "nipt_full_run": "NIPT workflow",
    "nipt_mount_smoke": "Validation",
}

GENERIC_RULE_PHASES = {
    "fastp_bwa": "Mapping",
    "mapping": "Mapping",
    "collect_mapping_qc": "Mapping",
    "metadata": "Metadata",
    "collect_run_metadata": "Metadata",
    "cnv_qc": "CNV QC",
    "baseline_qc": "CNV QC",
    "wisecondorx_convert_for_cnv": "CNV QC",
    "wisecondorx_qc_for_predict": "CNV QC",
    "aggregate_pgta_qc": "CNV QC",
    "cnv_predict": "CNV prediction",
    "wisecondorx_gender_for_predict": "CNV prediction",
    "wisecondorx_predict_cnv": "CNV prediction",
    "aggregate_pgta_prediction_status": "CNV prediction",
    "Preall": "Pre-calling",
    "cleanFastq": "Pre-calling",
    "Dedup": "Pre-calling",
    "Sam2Cram": "Pre-calling",
    "QualCal": "Pre-calling",
    "QCStatic": "Pre-calling",
    "mtQC": "Pre-calling",
    "Haplotyper": "Pre-calling",
    "bam2blockUniq": "Pre-calling",
    "Smooverun": "Pre-calling",
    "mityCall": "Pre-calling",
    "MEICall": "Pre-calling",
    "fq2cram": "Pre-calling",
    "cram2gvcf": "Pre-calling",
    "SNV_Annotation": "Variant analysis",
    "INDEL_Annotation": "Variant analysis",
    "CNV_Annotation": "Variant analysis",
    "SV_Annotation": "Variant analysis",
    "GVCFtyper": "Variant analysis",
    "QCall": "QC",
    "PeddyC": "QC",
    "sceVCF": "QC",
    "gender": "QC",
    "SingleQC_merge": "QC",
    "mergeQC": "QC",
    "plotQC": "QC",
    "WGS_QC": "QC",
}

WGS_PRE_CALLING_RULES = frozenset(
    {
        "Preall",
        "cleanFastq",
        "mapping",
        "Dedup",
        "Sam2Cram",
        "QualCal",
        "QCStatic",
        "mtQC",
        "Haplotyper",
        "bam2blockUniq",
        "Smooverun",
        "mityCall",
        "MEICall",
    }
)
WGS_QC_RULES = frozenset(
    {
        "QCall",
        "PeddyC",
        "sceVCF",
        "gender",
        "SingleQC_merge",
        "mergeQC",
        "plotQC",
        "mergeMTQC",
    }
)
WGS_VARIANT_ANALYSIS_RULES = frozenset(
    {
        "CNVall",
        "fastqCount",
        "GCcorrect",
        "CNVcalling",
        "formatCNV",
        "CNV_VAF_plot",
        "mergeCNV",
        "CNVannotation",
        "insertplot",
        "MEIall",
        "MEI",
        "MEI_vep",
        "MEI_annotation",
        "ROHall",
        "ROHcalling",
        "vafplot",
        "format",
        "imprintRegionR",
        "MIE",
        "MIE_ROH_plot",
        "SMAall",
        "SMA",
        "CYP2D6",
        "CSall",
        "createCSfile",
        "fam_split_lenient_CS",
        "fam_split_lenient_CS_correct",
        "fam_split_strict_CS",
        "fam_split_strict_CS_correct",
        "makecsvcf",
        "makecsvcf_flt",
        "fam_slivar_lenient_CS",
        "fam_slivar_strict_CS",
        "fam_SNVannotation_strict_CS",
        "fam_SNVannotation_lenient_CS",
        "markCS_flt",
        "markCS",
        "MTall",
        "mityCallflt",
        "NorVcf",
        "mityreport",
        "mtAnnot",
        "mtFlt",
        "mtCombine",
        "REall",
        "expansionhunter",
        "SNVall",
        "GVCFtyper",
        "NormalizeVcf",
        "qualityFlt",
        "virtualWES",
        "vep",
        "intergenicFlt",
        "vepLenient",
        "blacklistCsqFlt",
        "vepFlt",
        "createPed",
        "solo_split_lenient",
        "solo_split_strict",
        "trio_split",
        "fam_split_lenient",
        "fam_split_lenient_correct",
        "fam_split_strict",
        "fam_split_strict_correct",
        "fam_slivar_lenient",
        "fam_slivar_strict",
        "fam_SNVannotation_strict",
        "fam_SNVannotation_lenient",
        "solo_SNVannotation_strict",
        "solo_SNVannotation_lenient",
        "batchVcf2Vaf",
        "splitVcf",
        "bedGraphVaf",
        "SVall",
        "splitCNV",
        "svVep",
        "SVtsv",
        "SVsort",
    }
)
WGS_RULE_PHASES = {
    **{rule: "Pre-calling" for rule in WGS_PRE_CALLING_RULES},
    **{rule: "Variant analysis" for rule in WGS_VARIANT_ANALYSIS_RULES},
    **{rule: "QC" for rule in WGS_QC_RULES},
}
WGS_RULE_PREFIX_PHASES = (
    ("pre_process_", "Pre-calling"),
    ("QC_", "QC"),
    ("cloud_", "Cloud delivery"),
    ("SNV_", "Variant analysis"),
    ("SV_", "Variant analysis"),
    ("MT_", "Variant analysis"),
    ("RE_", "Variant analysis"),
    ("ROH_", "Variant analysis"),
    ("CNV_", "Variant analysis"),
    ("MEI_", "Variant analysis"),
    ("SMA_", "Variant analysis"),
    ("CS_", "Variant analysis"),
)
WGS_UNKNOWN_RULE_PHASE = "Variant analysis"
WGS_PHASE_ORDER = {
    "Pre-calling": 10,
    "Variant analysis": 20,
    "QC": 30,
    "Cloud delivery": 40,
}

FAILED_STATUSES = {"failed", "fail", "error"}
RUNNING_STATUSES = {"planned", "submitted", "running", "started"}
TERMINAL_STATUSES = {"success", "failed", "fail", "error", "skipped", "canceled", "cancelled", "terminated"}


def phase_for_rule(
    rule: str | None,
    *,
    pipeline_name: str | None = None,
    pipeline_stage: str | None = None,
) -> str:
    name = str(rule or "").strip()
    if str(pipeline_name or "").strip().lower() == "wgs":
        if name == "all":
            return "Pre-calling" if str(pipeline_stage or "").strip().lower() == "precalling" else "QC"
        for prefix, phase in WGS_RULE_PREFIX_PHASES:
            if name.startswith(prefix):
                return phase
        # Unknown WGS rules remain on the WGS stage rail rather than becoming generic Pipeline events.
        return WGS_RULE_PHASES.get(name, WGS_UNKNOWN_RULE_PHASE)
    return NIPT_RULE_PHASES.get(name) or GENERIC_RULE_PHASES.get(name) or "Pipeline"


def phase_order(phase: str | None, *, pipeline_name: str | None = None) -> int:
    """Return a stable UI sort order without deriving execution dependencies."""
    if str(pipeline_name or "").strip().lower() == "wgs":
        return WGS_PHASE_ORDER.get(str(phase or ""), 999)
    return 999


def wgs_phase_definitions() -> list[dict[str, object]]:
    return [
        {
            "key": phase.lower().replace("-", "_").replace(" ", "_"),
            "label": phase,
            "order": order,
        }
        for phase, order in sorted(WGS_PHASE_ORDER.items(), key=lambda item: item[1])
    ]


def rule_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    statuses = [str(item.get("status") or "unknown").lower() for item in events]
    return {
        "total": len(events),
        "running": sum(value in RUNNING_STATUSES for value in statuses),
        "success": statuses.count("success"),
        "failed": sum(value in FAILED_STATUSES for value in statuses),
        "terminal": sum(value in TERMINAL_STATUSES for value in statuses),
    }


def summarize_rule_events(
    events: list[dict[str, Any]],
    *,
    pipeline_name: str | None = None,
    pipeline_stage: str | None = None,
) -> dict[str, Any]:
    by_status = Counter(str(item.get("status") or "unknown").lower() for item in events)
    phase_rows: dict[str, list[dict[str, Any]]] = {}
    for item in events:
        phase_rows.setdefault(
            phase_for_rule(item.get("rule"), pipeline_name=pipeline_name, pipeline_stage=pipeline_stage),
            [],
        ).append(item)
    phases = [
        {"phase": phase, **rule_counts(items)}
        for phase, items in phase_rows.items()
    ]
    return {
        "total": len(events),
        "by_status": dict(sorted(by_status.items())),
        "phases": phases,
    }


def current_rule_event(events: list[dict[str, Any]], *, prefer_failed: bool = False) -> dict[str, Any] | None:
    candidates = events
    if prefer_failed:
        failed = [item for item in events if str(item.get("status") or "").lower() in FAILED_STATUSES]
        if failed:
            candidates = failed
    active = [item for item in candidates if str(item.get("status") or "").lower() in RUNNING_STATUSES]
    if active:
        candidates = active
    if not candidates:
        return None

    def sort_key(item: dict[str, Any]) -> tuple[int, str, str]:
        return (
            1 if item.get("sample_id") or item.get("snakemake_jobid") else 0,
            str(item.get("start_time") or item.get("end_time") or ""),
            str(item.get("rule") or ""),
        )

    return max(candidates, key=sort_key)
