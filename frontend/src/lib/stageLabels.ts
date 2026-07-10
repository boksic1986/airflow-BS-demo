const stageLabels: Record<string, string> = {
  validate_request: "Validate run request",
  prepare_pgta_config: "Prepare PGT-A config",
  choose_pgta_path: "Choose PGT-A execution path",
  run_pgta_target: "Run PGT-A workflow",
  "pgta_pipeline.run_pgta_mapping": "Mapping reads",
  "pgta_pipeline.run_pgta_metadata": "Collect metadata",
  "pgta_pipeline.run_pgta_baseline_qc": "Baseline QC",
  collect_pgta_artifact: "Collect PGT-A artifacts",
  prepare_nipt_docker_run: "Prepare NIPT Docker run",
  run_nipt_docker: "Run NIPT Docker workflow",
  collect_nipt_artifacts: "Collect NIPT artifacts",
  baseline_bam_uniformity_qc: "Baseline BAM uniformity QC",
  baseline_qc: "Baseline QC",
  metadata: "Metadata collection",
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
