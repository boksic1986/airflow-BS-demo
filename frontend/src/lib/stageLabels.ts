const stageLabels: Record<string, string> = {
  "Workflow complete": "Completed",
  validate_request: "Validate run request",
  prepare_pgta_config: "Prepare PGT-A config",
  choose_pgta_path: "Choose PGT-A execution path",
  run_pgta_target: "Run PGT-A workflow",
  "pgta_pipeline.run_pgta_mapping": "Mapping reads",
  "pgta_pipeline.run_pgta_metadata": "Collect metadata",
  "pgta_pipeline.run_pgta_baseline_qc": "Baseline QC",
  "pgta_predict.run_pgta_mapping": "Mapping reads",
  "pgta_predict.run_pgta_metadata": "Collect run metadata",
  "pgta_predict.run_pgta_cnv_qc": "CNV quality control",
  "pgta_predict.run_pgta_cnv_predict": "WisecondorX prediction",
  collect_pgta_artifact: "Collect PGT-A artifacts",
  prepare_nipt_docker_run: "Prepare NIPT Docker run",
  run_nipt_docker: "Run NIPT Docker workflow",
  collect_nipt_artifacts: "Collect NIPT artifacts",
  prepare_wgs_run: "Prepare WGS host run",
  choose_wgs_path: "Choose WGS validation path",
  "wgs_pipeline.pre_calling": "Pre-calling",
  "wgs_pipeline.variant_analysis": "Variant analysis",
  "wgs_pipeline.collect_qc": "WGS quality control",
  collect_wgs_artifacts: "Collect WGS artifacts",
  baseline_bam_uniformity_qc: "Baseline BAM uniformity QC",
  baseline_qc: "Baseline QC",
  metadata: "Metadata collection",
  fastp_bwa: "Read cleaning and mapping",
  collect_mapping_qc: "Mapping quality metrics",
  wisecondorx_convert_for_cnv: "Prepare CNV bins",
  wisecondorx_gender_for_predict: "Infer reference sex",
  wisecondorx_qc_for_predict: "CNV quality control",
  wisecondorx_predict_cnv: "WisecondorX CNV prediction",
  aggregate_pgta_qc: "Aggregate PGT-A QC",
  aggregate_pgta_prediction_status: "Finalize prediction status",
  nipt_mount_smoke: "NIPT mount smoke",
  __airflow_demo_invalid_target__: "Demo invalid target",
};

export function humanStageLabel(value?: string | null): string {
  if (!value) return "No step captured";
  return stageLabels[value] || prettifyIdentifier(value);
}

export function stageDebugLabel(value?: string | null): string | null {
  if (!value) return null;
  const label = humanStageLabel(value);
  return label === value ? null : value;
}

function prettifyIdentifier(value: string): string {
  return value
    .split(".")
    .pop()!
    .replace(/^run_/, "Run ")
    .replace(/^collect_/, "Collect ")
    .replace(/^prepare_/, "Prepare ")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
