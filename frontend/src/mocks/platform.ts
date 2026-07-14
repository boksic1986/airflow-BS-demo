export type PipelineTemplate = {
  id: "wes_qsub" | "pgta" | "nipt_qsub" | "nipt_docker" | "wgs";
  name: string;
  description: string;
  dagId: string;
  version: string;
  owner: string;
  execution: string;
  reference: string;
  requiredInputs: string[];
  outputs: string[];
  latestRun: string;
  successRate: string;
  implementationStatus: "live" | "staged" | "demo/mock" | "planned";
  steps: Array<{name: string; status: string; description: string}>;
};

export const workflowTemplates: PipelineTemplate[] = [
  {
    id: "wes_qsub",
    name: "WES qsub",
    description: "Mock WES Snakemake profile with qsub event logging and resume/rerun controls.",
    dagId: "bio_wes_qsub",
    version: "demo-0.1",
    owner: "Bioinformatics",
    execution: "Snakemake 9.23.1 + mock qsub",
    reference: "mock hg19 panel",
    requiredInputs: ["mock S001/S002 sample set", "final_summary target"],
    outputs: ["final_summary.tsv", "qc_summary.tsv", "snakemake_events.jsonl", "qsub stdout/stderr"],
    latestRun: "WES_20260705_164813_C5561C",
    successRate: "100% demo",
    implementationStatus: "live",
    steps: [
      {name: "prepare_wes_config", status: "success", description: "Write run-local WES mock config"},
      {name: "run_wes_qsub", status: "success", description: "Run Snakemake through qsub profile"},
      {name: "collect_wes_artifacts", status: "success", description: "Expose command, events, QC, and reports"},
    ],
  },
  {
    id: "pgta",
    name: "PGT-A",
    description: "Server-path PGT-A prediction with fixed hg19 and approved XX, XY, and gender references.",
    dagId: "bio_pgta",
    version: "pgta-s9-v1.4",
    owner: "PGT-A platform",
    execution: "Snakemake 9.23.1 with rule event logger",
    reference: "hg19 / fixed XX, XY, and gender references",
    requiredInputs: ["allowlisted rawdata_root", "selected R1/R2 pairs", "predict profile"],
    outputs: ["mapping QC", "CNV QC", "WisecondorX prediction", "rule logs"],
    latestRun: "PGTA_20260706_162150_00C4FD",
    successRate: "validation in progress",
    implementationStatus: "live",
    steps: [
      {name: "validate_request", status: "success", description: "Validate selected manifest and approved profile"},
      {name: "prepare_pgta_config", status: "success", description: "Resolve immutable S9 run config"},
      {name: "pgta_predict.run_pgta_mapping", status: "success", description: "Clean reads, align, and collect mapping QC"},
      {name: "pgta_predict.run_pgta_metadata", status: "success", description: "Collect runtime provenance"},
      {name: "pgta_predict.run_pgta_cnv_qc", status: "success", description: "Convert bins, infer sex, and evaluate CNV QC"},
      {name: "pgta_predict.run_pgta_cnv_predict", status: "success", description: "Run WisecondorX prediction for QC-pass samples"},
      {name: "collect_pgta_artifact", status: "success", description: "Import QC, logs, and prediction status"},
    ],
  },
  {
    id: "nipt_qsub",
    name: "NIPT qsub",
    description: "Expected qsub-backed NIPT workflow surface. Runner work is still pending.",
    dagId: "bio_nipt_qsub",
    version: "planned",
    owner: "NIPT team",
    execution: "Snakemake/qsub planned",
    reference: "NIPT reference bins",
    requiredInputs: ["sample sheet", "FASTQ path", "sex", "project"],
    outputs: ["fetal_fraction", "chr13/18/21 z-scores", "CNV plots"],
    latestRun: "not available",
    successRate: "demo/mock",
    implementationStatus: "demo/mock",
    steps: [
      {name: "prepare_input", status: "planned", description: "Normalize NIPT sample manifest"},
      {name: "map_reads", status: "planned", description: "Map reads with qsub resources"},
      {name: "zscore", status: "planned", description: "Compute trisomy z-scores"},
    ],
  },
  {
    id: "nipt_docker",
    name: "NIPT Docker",
    description: "Server-path scanned NIPT Docker flow using clean FASTQ chip batches and Airflow handoff.",
    dagId: "bio_nipt_docker",
    version: "scan-v1",
    owner: "NIPT team",
    execution: "Airflow worker + host Docker socket",
    reference: "niptpro:1.0.11 / pytorch:biosan",
    requiredInputs: ["allowlisted NIPT fastq root", "*.clean.fastq.gz R1/R2 pairs", "32-core approved full analysis"],
    outputs: ["run-local NIPT samplesheet", "mount smoke QC TSV", "Docker compose artifact", "stdout/stderr", "NIPT QC summary after full run"],
    latestRun: "not available",
    successRate: "scanned-batch smoke pending",
    implementationStatus: "staged",
    steps: [
      {name: "validate_request", status: "success", description: "Validate scanned batch, mode, cores, and workdir"},
      {name: "prepare_nipt_docker_run", status: "success", description: "Generate run-local NIPT samplesheet, config, and compose file"},
      {name: "run_nipt_docker", status: "running", description: "Run mount smoke or guarded full Docker batch"},
      {name: "collect_nipt_artifacts", status: "planned", description: "Expose QC, logs, config, and compose artifacts"},
    ],
  },
  {
    id: "wgs",
    name: "WGS",
    description: "BS10610 host-native WGS workflow orchestrated by Airflow and Snakemake 9.",
    dagId: "bio_wgs",
    version: "wgs-s9-host-v1",
    owner: "WGS team",
    execution: "Airflow SSHOperator + BS10610 host Snakemake 9.23.1",
    reference: "GRCh38 / approved WGS V3.8 configuration",
    requiredInputs: ["pre-calling config", "downstream config", "controlled target list"],
    outputs: ["CRAM/gVCF", "SNV/SV/CNV results", "QC", "rule events", "resource telemetry"],
    latestRun: "not available",
    successRate: "validation pending",
    implementationStatus: "staged",
    steps: [
      {name: "prepare_wgs_run", status: "success", description: "Validate the controlled host request"},
      {name: "pre_calling", status: "planned", description: "FASTQ to CRAM and gVCF"},
      {name: "variant_analysis", status: "planned", description: "Run approved downstream targets"},
      {name: "collect_qc", status: "planned", description: "Collect QC and resource telemetry"},
    ],
  },
];

export const deployedWorkflowTemplates = workflowTemplates.filter((pipeline) => pipeline.id === "pgta" || pipeline.id === "nipt_docker" || pipeline.id === "wgs");

export const resourceOverview = [
  {title: "CPU allocation", value: "64 / 32", unit: "cores", status: "running", description: "PGT-A default / NIPT Docker approved default"},
  {title: "Memory pressure", value: "42", unit: "%", status: "success", description: "Mock resource telemetry"},
  {title: "Queue jobs", value: "0", unit: "jobs", status: "success", description: "qsub is not enabled; NIPT uses Docker"},
  {title: "QC alerts", value: "14", unit: "metrics", status: "failed", description: "PGT-A baseline QC fail metrics; NIPT smoke QC is non-biological"},
];

export const mockSamples = [
  {
    sample_id: "NIPT-DEMO-001",
    family_id: null,
    pipeline: "NIPT qsub",
    status: "planned",
    fastq_path: "/data/mock/nipt/NIPT-DEMO-001_R1.fastq.gz",
    qc_status: "unknown",
    report_status: "not generated",
    error_summary: "demo/mock only",
  },
  {
    sample_id: "WGS-DEMO-001",
    family_id: "FAM-WGS-001",
    pipeline: "WGS",
    status: "planned",
    fastq_path: "/data/mock/wgs/WGS-DEMO-001_R1.fastq.gz",
    qc_status: "unknown",
    report_status: "not generated",
    error_summary: "demo/mock only",
  },
];
