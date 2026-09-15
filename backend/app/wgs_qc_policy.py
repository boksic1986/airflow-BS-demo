"""Audited QC display policy and exact source-equivalent releases.

Source aggregate remains authoritative; missing inputs are never imputed.
Clinical free-text notes and identity are not returned by this projection.
"""
import hashlib
import json
import math
from pathlib import Path

POLICY_FILE = Path(__file__).with_name("policies") / "wgs_qc_cc9bde3.json"
SPECIAL = {"Q0079", "Q0080", "Q0081", "Q0082", "Q0088"}
RELEASES = {"wgs-4.2.1-cc9bde3"}


def number(value):
    try:
        result = float(str(value).strip().replace(",", "").removesuffix("%"))
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def evaluate_metrics(source, *, release_id, context, multiqc=None):
    raw_policy = POLICY_FILE.read_bytes()
    policy = json.loads(raw_policy)
    equivalent_commit = policy.get("verified_equivalent_releases", {}).get(release_id)
    available = release_id in RELEASES or equivalent_commit is not None
    provenance = {**policy["provenance"], "policy_sha256": hashlib.sha256(raw_policy).hexdigest(), "release_id": release_id} if available else {"release_id": release_id, "reason": "Release policy provenance unavailable"}
    if equivalent_commit is not None:
        # All four packaged QC source blobs were compared at both exact commits.
        provenance.update(policy_source_commit=policy["provenance"]["source_commit"], source_commit=equivalent_commit)
    if context.get("manifest_sha256"):
        provenance["condition_manifest_sha256"] = context["manifest_sha256"]
    result = {}

    def check(key, column, unit, bounds=None, *, data=None, missing=None):
        value = number((source if data is None else data).get(column))
        status = "unknown"
        reason = "Value unavailable"
        threshold = None
        if not available:
            reason = "Release policy provenance unavailable"
        elif missing:
            reason = missing
        elif bounds is None:
            reason = "No applicable criterion in this release"
        else:
            lower, upper, lower_inclusive, upper_inclusive = bounds
            threshold = {"min": lower, "max": upper, "min_inclusive": lower_inclusive, "max_inclusive": upper_inclusive}
            if value is not None:
                passed = (lower is None or (value >= lower if lower_inclusive else value > lower)) and (upper is None or (value <= upper if upper_inclusive else value < upper))
                status = "pass" if passed else "fail"
                reason = "Within release criterion" if passed else "Outside release criterion"
        result[key] = {"value": value, "unit": unit, "threshold": threshold, "status": status, "reason": reason, "provenance": provenance, "source_field": column, "source_artifact": "multi.QC.tsv" if data is not None else "QCstat.tsv"}
        if data is not None and data.get("_artifact_sha256"):
            result[key]["source_sha256"] = data["_artifact_sha256"]

    thresholds = policy["QC_threshold"]
    item = context.get("item_id")
    relation = context.get("relation")
    special = item in SPECIAL
    item_missing = "Project item unavailable" if not item else None
    sample_type = context.get("sample_type")
    translated = policy["sampletype_trans"].get(sample_type, "其他")
    check("mapped_reads_percent", "Mapped_Reads%", "%", (float(thresholds["mapped"]), None, True, True))
    for key, column, policy_key in [("raw_gc_percent", "Raw_GC%", "Raw_GC"), ("clean_gc_percent", "Clean_GC%", "Clean_GC"), ("snv_count", "SNV_count", "SNV_count_bkw" if context.get("bkw") else "SNV_count"), ("cnv_count", "CNV_count", "CNV_count")]:
        limits = thresholds[policy_key][translated]
        missing = "Sample type unavailable" if not sample_type else "Frozen BKW selection unavailable" if key == "snv_count" and "bkw" not in context else None
        check(key, column, "%" if "gc" in key else "count", (float(limits["min"]), float(limits["max"]), True, True), missing=missing)
    check("clean_q30_percent", "Clean_Q30%", "%", (85, None, not special, True), missing=item_missing)
    check("average_depth", "Average_Depth", "×", (30 if special or relation == "先证者" else 20, None, True, True), missing=item_missing or ("Family relation unavailable" if not special and not relation else None))
    check("fold80", "FOLD_80_BASE_PENALTY", "ratio", (None, 2, True, True))
    check("duplication_percent", "Duplicated_reads%", "%", (None, 10, True, False) if special else None, missing=item_missing)
    check("coverage_20x_percent", ">=20X", "%", (90, None, False, True) if special else None, missing=item_missing)
    check("coverage_1x_percent", ">=1X", "%", (95, None, True, True) if not special else None, missing=item_missing)
    check("raw_bases", "Raw_bases", "bases", (115000000000, None, True, True) if not special else None, missing=item_missing)
    raw_reads, dup_reads = number(source.get("Raw_reads")), number(source.get("Duplicated_reads"))
    effective = (raw_reads - dup_reads) * 150 if raw_reads is not None and dup_reads is not None else None
    check("effective_bases", "effective_bases", "bases", (90000000000, None, False, True) if special else None, data={"effective_bases": effective}, missing=item_missing)
    result["effective_bases"].update(source_artifact="QCstat.tsv", source_field="(Raw_reads - Duplicated_reads) * 150")
    # g1 joins the two contamination measurements, not independent cutoffs.
    charr, inconsistent = number(source.get("CHARR")), number(source.get("INCONSISTENT_AB_HET_RATE"))
    level = str(source.get("contamination") or "").upper()
    computed = None if charr is None or inconsistent is None else "fail" if charr > .03 and inconsistent > .15 else "warn" if charr > .02 and inconsistent > .1 else "pass"
    contamination_reason = "Release policy provenance unavailable" if not available else "Value unavailable" if computed is None else "Within release criterion" if computed == "pass" else "Contamination measurements exceed release criterion"
    result["contamination"] = {
        "value": f"CHARR {charr:g} / AB {inconsistent:g}" if computed is not None else None,
        "unit": "status",
        "threshold": "FAIL: CHARR > 0.03 AND AB > 0.15; WARNING: CHARR > 0.02 AND AB > 0.1" if available else None,
        "status": (computed or "unknown") if available else "unknown",
        "reason": contamination_reason, "provenance": provenance,
        "computed_status": computed if available else None, "source_status": level or None,
        "measurements": {"CHARR": charr, "INCONSISTENT_AB_HET_RATE": inconsistent},
        "source_artifact": "QCstat.tsv", "source_field": "CHARR,INCONSISTENT_AB_HET_RATE",
    }
    if context.get("rare_disease"):
        for key, column, unit, bounds in [
            ("multi_dedup_bases", "Dedup_bases", "bases", (120000000000, None, True, True)),
            ("multi_average_depth", "Mean_Depth", "×", (40, None, True, True)),
            ("multi_q30_percent", "Clean_Q30%", "%", (85, None, False, True)),
            ("multi_coverage_30x_percent", ">=30X", "%", (90, None, True, True)),
            ("multi_coverage_10x_percent", ">=10X", "%", (98, None, True, True)),
            ("multi_duplication_percent", "Duplicated_reads%", "%", (None, 10, True, True)),
        ]:
            check(key, column, unit, bounds, data=multiqc or {})
    for key in ("sex_match", "peddy"):
        result[key] = {"value": None, "unit": "status", "threshold": None, "status": "unknown", "reason": "Individual safe evidence unavailable; retained source aggregate includes this check", "provenance": provenance}
    sex = source.get("性别是否符合")
    if available and sex in {"Yes", "No"}:
        result["sex_match"].update(value=sex, status="pass" if sex == "Yes" else "fail", reason="Source-produced sex consistency judgment")
    return result
