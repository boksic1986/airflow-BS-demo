import pytest


@pytest.mark.parametrize("item,relation,q30,depth,q30_status,depth_status", [
    ("Q0079", "父亲", "85%", "29.9", "fail", "fail"),
    ("Q0088", "先证者", "85.01%", "30", "pass", "pass"),
    ("OTHER", "父亲", "85%", "20", "pass", "pass"),
    ("OTHER", "先证者", "85%", "29.9", "pass", "fail"),
    (None, "先证者", "99%", "40", "unknown", "unknown"),
    ("OTHER", None, "99%", "40", "pass", "unknown"),
])
def test_qc_conditional_boundary(item, relation, q30, depth, q30_status, depth_status):
    from app.wgs_qc_policy import evaluate_metrics
    values = evaluate_metrics({"Clean_Q30%": q30, "Average_Depth": depth}, release_id="wgs-4.2.1-cc9bde3", context={"item_id": item, "relation": relation, "sample_type": "全血"})
    assert values["clean_q30_percent"]["status"] == q30_status
    assert values["average_depth"]["status"] == depth_status


def test_qc_version_missing_type_contamination_and_multiqc():
    from app.wgs_qc_policy import evaluate_metrics
    source = {"Raw_GC%": "39.36%", "CHARR": ".03", "INCONSISTENT_AB_HET_RATE": ".15", "contamination": "WARNING", "Mapped_Reads%": "99.9%"}
    current = evaluate_metrics(source, release_id="wgs-4.2.1-cc9bde3", context={"sample_type": "全血", "rare_disease": True}, multiqc={"Mean_Depth": "40", "Clean_Q30%": "85", "Duplicated_reads%": "10"})
    assert current["raw_gc_percent"]["status"] == "pass"
    assert current["contamination"]["status"] == "warn"
    assert current["multi_average_depth"]["status"] == "pass"
    assert current["multi_q30_percent"]["status"] == "fail"
    assert current["multi_duplication_percent"]["status"] == "pass"
    assert current["multi_dedup_bases"]["status"] == "unknown"
    assert current["mapped_reads_percent"]["provenance"]["source_commit"].startswith("cc9bde3")
    assert evaluate_metrics(source, release_id="wgs-4.2.0-31de5fb", context={})["mapped_reads_percent"]["status"] == "unknown"
    assert evaluate_metrics(source, release_id="wgs-4.2.1-cc9bde3", context={})["raw_gc_percent"]["status"] == "unknown"


def test_unknown_rule_is_not_claimed_as_variant_analysis():
    from app.workflow_phases import wgs_phase_for_rule
    assert wgs_phase_for_rule("unregistered_future_rule") == "Unknown"


@pytest.mark.parametrize("key,column,value,item,expected", [
    ("duplication_percent", "Duplicated_reads%", "10", "Q0080", "fail"),
    ("coverage_20x_percent", ">=20X", "90", "Q0081", "fail"),
    ("coverage_20x_percent", ">=20X", "90.01", "Q0082", "pass"),
    ("coverage_20x_percent", ">=20X", "85", "OTHER", "unknown"),
    ("raw_bases", "Raw_bases", "115000000000", "OTHER", "pass"),
    ("coverage_1x_percent", ">=1X", "94.99", "OTHER", "fail"),
    ("fold80", "FOLD_80_BASE_PENALTY", "2", "OTHER", "pass"),
    ("mapped_reads_percent", "Mapped_Reads%", "nan", "OTHER", "unknown"),
])
def test_other_release_boundaries(key, column, value, item, expected):
    from app.wgs_qc_policy import evaluate_metrics
    assert evaluate_metrics({column: value}, release_id="wgs-4.2.1-cc9bde3", context={"item_id": item})[key]["status"] == expected


def test_effective_bases_bkw_and_type_boundaries():
    from app.wgs_qc_policy import evaluate_metrics
    source = {"Raw_reads": "610000000", "Duplicated_reads": "10000000", "Raw_GC%": "39.5", "SNV_count": "8000"}
    blood = evaluate_metrics(source, release_id="wgs-4.2.1-cc9bde3", context={"item_id": "Q0079", "sample_type": "全血", "bkw": True})
    assert blood["effective_bases"]["value"] == 90000000000
    assert blood["effective_bases"]["status"] == "fail"
    assert blood["raw_gc_percent"]["status"] == "pass"
    assert blood["snv_count"]["status"] == "pass"
    dna = evaluate_metrics(source, release_id="wgs-4.2.1-cc9bde3", context={"sample_type": "DNA", "bkw": False})
    assert dna["raw_gc_percent"]["status"] == "fail"
    assert dna["snv_count"]["status"] == "fail"


def test_qc_projection_keeps_aggregate_and_private_conditions(tmp_path):
    from app.wgs_sample_projection import _read_qc
    batch = tmp_path / "SYNTHETIC"
    (batch / "07_QC").mkdir(parents=True)
    (batch / "sampleinfo.tsv").write_text("数据编号\t项目编号\t家系关系\t样本类型\t姓名\nS-F57J\tQ0079\t先证者\t全血\tPRIVATE_SYNTHETIC\n", encoding="utf-8")
    (batch / "07_QC" / "SYNTHETIC.QCstat.tsv").write_text("Sample_ID\t是否通过质控\tClean_Q30%\nS-F57J\tYes\t85%\n", encoding="utf-8")
    (batch / "07_QC" / "S-F57J.multi.QC.tsv").write_text("Sample\tMean_Depth\nS-F57J\t40\n", encoding="utf-8")
    result = _read_qc(batch, release_id="wgs-4.2.1-cc9bde3")["S-F57J"]
    assert result["status"] == "pass"
    assert result["metrics"]["clean_q30_percent"] == "85%"
    assert result["judgments"]["clean_q30_percent"]["status"] == "fail"
    assert result["judgments"]["multi_average_depth"]["status"] == "pass"
    assert "PRIVATE_SYNTHETIC" not in str(result)
