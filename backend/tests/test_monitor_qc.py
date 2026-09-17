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


@pytest.mark.parametrize("release_id", ["wgs-4.2.1-cc9bde3", "wgs-4.2.1-34bfcbf", "wgs-4.2.1-ebf1f4b"])
def test_qc_projection_keeps_aggregate_and_private_conditions(tmp_path, release_id):
    from app.wgs_sample_projection import _read_qc
    batch = tmp_path / "SYNTHETIC"
    (batch / "07_QC").mkdir(parents=True)
    (batch / "sampleinfo.tsv").write_text("数据编号\t项目编号\t家系关系\t样本类型\t姓名\nS-F57J\tQ0079\t先证者\t全血\tPRIVATE_SYNTHETIC\n", encoding="utf-8")
    (batch / "07_QC" / "SYNTHETIC.QCstat.tsv").write_text("Sample_ID\t是否通过质控\tClean_Q30%\nS-F57J\tYes\t85%\n", encoding="utf-8")
    (batch / "07_QC" / "S-F57J.multi.QC.tsv").write_text("Sample\tMean_Depth\nS-F57J\t40\n", encoding="utf-8")
    result = _read_qc(batch, release_id=release_id)["S-F57J"]
    assert result["status"] == "pass"
    assert result["metrics"]["clean_q30_percent"] == "85%"
    assert result["judgments"]["clean_q30_percent"]["status"] == "fail"
    assert result["judgments"]["multi_average_depth"]["status"] == "pass"
    assert "PRIVATE_SYNTHETIC" not in str(result)


def test_verified_qc_release_uses_identical_policy_with_exact_provenance():
    from app.wgs_qc_policy import evaluate_metrics
    source = {"Clean_Q30%": "85", "Mapped_Reads%": "99.9", "Average_Depth": "29.9",
              "Raw_GC%": "39.36", "SNV_count": "8000", "contamination": "WARNING",
              "性别是否符合": "Yes", "CHARR": ".03", "INCONSISTENT_AB_HET_RATE": ".15"}
    context = {"item_id": "Q0079", "relation": "先证者", "sample_type": "全血", "bkw": True, "rare_disease": True}
    multi = {"Mean_Depth": "40", "Clean_Q30%": "85", "Duplicated_reads%": "10"}
    previous = evaluate_metrics(source, release_id="wgs-4.2.1-cc9bde3", context=context, multiqc=multi)
    current = evaluate_metrics(source, release_id="wgs-4.2.1-34bfcbf", context=context, multiqc=multi)
    assert current["mapped_reads_percent"]["status"] == "pass"
    assert current["clean_q30_percent"]["status"] == "fail"
    assert current["average_depth"]["status"] == "fail"
    assert current["contamination"]["status"] == "warn"
    assert current["sex_match"]["status"] == "pass"
    assert current["peddy"]["status"] == "unknown"
    assert current["clean_gc_percent"]["reason"] == "Value unavailable"
    assert current["coverage_1x_percent"]["reason"] == "No applicable criterion in this release"
    for key in previous:
        assert {k: v for k, v in current[key].items() if k != "provenance"} == {k: v for k, v in previous[key].items() if k != "provenance"}
    provenance = current["mapped_reads_percent"]["provenance"]
    assert provenance["release_id"] == "wgs-4.2.1-34bfcbf"
    assert provenance["source_commit"] == "34bfcbf82238af684d005314360c9c9739377351"
    assert provenance["policy_source_commit"] == "cc9bde3c8ee6ad1cd2f85cf5d2ef49c5611ac081"
    assert provenance["source_git_blobs"] == previous["mapped_reads_percent"]["provenance"]["source_git_blobs"]
    missing = evaluate_metrics(source, release_id="wgs-4.2.1-34bfcbf", context={})
    assert missing["clean_q30_percent"]["reason"] == "Project item unavailable"
    assert missing["raw_gc_percent"]["reason"] == "Sample type unavailable"
    unknown = evaluate_metrics(source, release_id="wgs-4.2.1-34bfcbf-unreviewed", context=context)
    assert unknown["mapped_reads_percent"]["status"] == "unknown"
    assert unknown["mapped_reads_percent"]["reason"] == "Release policy provenance unavailable"


@pytest.mark.parametrize("charr,ab,want", [(None,".1","unknown"),("nan",".2","unknown"),(".03",".15","warn"),(".031",".151","fail"),(".04",".05","pass"),("0","0","pass")])
def test_contamination_requires_measurements_and_uses_joint_native_cutoffs(charr,ab,want):
    from app.wgs_qc_policy import evaluate_metrics
    result=evaluate_metrics({"CHARR":charr,"INCONSISTENT_AB_HET_RATE":ab,"contamination":"PASS"},release_id="wgs-4.2.1-34bfcbf",context={})["contamination"]
    assert result["status"] == want
    assert result["source_status"] == "PASS"
    if want == "unknown":
        assert result["value"] is None
    else:
        assert result["measurements"] == {"CHARR":float(charr),"INCONSISTENT_AB_HET_RATE":float(ab)}
        assert result["value"].startswith("CHARR ")


@pytest.mark.parametrize("value,expected", [("89.99", "fail"), ("90", "fail"), ("90.01", "pass"), (None, "unknown"), ("nan", "unknown")])
def test_ebf1f4b_checks_20x_for_other_projects_without_changing_history(value, expected):
    from app.wgs_qc_policy import evaluate_metrics
    source = {">=20X": value, "Mapped_Reads%": "99.9", "Clean_Q30%": "85", "Average_Depth": "20"}
    context = {"item_id": "OTHER", "relation": "父亲", "sample_type": "全血"}
    current = evaluate_metrics(source, release_id="wgs-4.2.1-ebf1f4b", context=context)
    assert current["coverage_20x_percent"]["status"] == expected
    assert current["coverage_20x_percent"]["threshold"] == {"min": 90, "max": None, "min_inclusive": False, "max_inclusive": True}
    for key in ("mapped_reads_percent", "clean_q30_percent", "average_depth"):
        assert current[key]["status"] == "pass"
    provenance = current["coverage_20x_percent"]["provenance"]
    assert provenance["source_commit"] == "ebf1f4bf2512feecdc3762e463145130192ca8bb"
    assert provenance["source_git_blobs"]["script/g1.Collect_QC.py"] == "6f873080049af713f57e7dc993ef391108bcc3e7"
    for release in ("wgs-4.2.1-cc9bde3", "wgs-4.2.1-34bfcbf"):
        previous = evaluate_metrics(source, release_id=release, context=context)
        assert previous["coverage_20x_percent"]["reason"] == "No applicable criterion in this release"
    unknown = evaluate_metrics(source, release_id="wgs-4.2.1-ebf1f4b-unreviewed", context=context)
    assert unknown["coverage_20x_percent"]["reason"] == "Release policy provenance unavailable"


def test_qc_counts_use_native_input_tables_and_keep_source_warning(tmp_path):
    from app.wgs_sample_projection import _read_qc
    batch = tmp_path / "SYNTHETIC"
    for directory in ("07_QC", "01_SNV", "03_CNV/Annot"):
        (batch / directory).mkdir(parents=True, exist_ok=True)
    (batch / "sampleinfo.tsv").write_text("数据编号\t项目编号\t家系关系\t样本类型\nS1\tOTHER\t先证者\t全血\n", encoding="utf-8")
    (batch / "config.yaml").write_text("BKWsampleList: []\n", encoding="utf-8")
    (batch / "07_QC/SYNTHETIC.QCstat.tsv").write_text("Sample_ID\t是否通过质控\nS1\tSNV数量(1)偏低\n", encoding="utf-8")
    snv = batch / "01_SNV/S1.flt.tsv"
    snv.write_text('Variant\tNote\n1\t"quoted\nrecord"\n\n', encoding="utf-8")
    (batch / "03_CNV/Annot/S1.CNV.tsv").write_text("Region\n" + "synthetic\n" * 4000, encoding="utf-8")
    result = _read_qc(batch, release_id="wgs-4.2.1-ebf1f4b")["S1"]
    assert result["status"] == "warn"
    assert result["metrics"]["snv_count"] == 1
    assert result["metrics"]["cnv_count"] == 4000
    assert result["judgments"]["snv_count"]["status"] == "fail"
    assert result["judgments"]["cnv_count"]["status"] == "pass"
    assert result["judgments"]["snv_count"]["source_artifact"] == "01_SNV/S1.flt.tsv"
    assert len(result["judgments"]["cnv_count"]["source_sha256"]) == 64
    snv.write_text("Variant\n", encoding="utf-8")
    assert _read_qc(batch, release_id="wgs-4.2.1-ebf1f4b")["S1"]["metrics"]["snv_count"] == 0
    # A new QC artifact containing explicit counts takes precedence over fallback.
    (batch / "07_QC/SYNTHETIC.QCstat.tsv").write_text("Sample_ID\t是否通过质控\tSNV_count\nS1\tYes\t900\n", encoding="utf-8")
    assert _read_qc(batch, release_id="wgs-4.2.1-ebf1f4b")["S1"]["judgments"]["snv_count"]["value"] == 900


def test_qc_count_missing_or_outside_project_never_becomes_zero(tmp_path):
    from app.wgs_sample_projection import _variant_count
    batch = tmp_path / "SYNTHETIC"
    batch.mkdir()
    assert _variant_count(batch, "S1", "SNV_count") is None
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "S1.flt.tsv").write_text("Variant\nprivate\n", encoding="utf-8")
    (batch / "01_SNV").symlink_to(outside, target_is_directory=True)
    assert _variant_count(batch, "S1", "SNV_count") is None
    assert _variant_count(batch, "../S1", "SNV_count") is None
