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
    description: "Server-path FASTQ scan with metadata, dry-run, failure-smoke, and staged baseline QC targets.",
    dagId: "bio_pgta",
    version: "level-4 staged",
    owner: "PGT-A platform",
    execution: "Snakemake direct in Airflow worker",
    reference: "PGT-A selected baseline samples",
    requiredInputs: ["allowlisted rawdata_root", "selected R1/R2 pairs", "target"],
    outputs: ["run_metadata.tsv", "baseline_qc_summary.tsv", "baseline_qc_report.md"],
    latestRun: "PGTA_20260706_162150_00C4FD",
    successRate: "workflow success; QC fail demo",
    implementationStatus: "staged",
    steps: [
      {name: "validate_request", status: "success", description: "Validate target and selected manifest"},
      {name: "prepare_pgta_config", status: "success", description: "Write PGT-A config under run workdir"},
      {name: "run_pgta_target", status: "success", description: "Run metadata/dryrun/baseline_qc target"},
      {name: "collect_pgta_artifact", status: "success", description: "Expose baseline QC artifacts"},
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
    name: "NIPT docker",
    description: "Docker images are preloaded on fengxian; runner is not implemented yet.",
    dagId: "bio_nipt_docker",
    version: "image-ready",
    owner: "NIPT team",
    execution: "Docker runner planned",
    reference: "niptpro:1.0.11",
    requiredInputs: ["sample sheet", "FASTQ path", "container image tag"],
    outputs: ["NIPT report", "fetal fraction", "z-score summary"],
    latestRun: "not available",
    successRate: "demo/mock",
    implementationStatus: "demo/mock",
    steps: [
      {name: "validate_images", status: "success", description: "Images loaded; no container smoke yet"},
      {name: "run_container", status: "planned", description: "Runner task pending"},
    ],
  },
  {
    id: "wgs",
    name: "WGS",
    description: "Roadmap surface for WGS analysis tracking, QC, and report artifacts.",
    dagId: "bio_wgs",
    version: "roadmap",
    owner: "WGS team",
    execution: "planned",
    reference: "GRCh37/GRCh38 selectable",
    requiredInputs: ["sample sheet", "FASTQ or BAM path", "reference"],
    outputs: ["coverage QC", "variant summary", "annotation report"],
    latestRun: "not available",
    successRate: "demo/mock",
    implementationStatus: "demo/mock",
    steps: [
      {name: "sample_qc", status: "planned", description: "Coverage and contamination checks"},
      {name: "variant_calling", status: "planned", description: "SNV/indel/SV calls"},
      {name: "report", status: "planned", description: "Report artifact registry"},
    ],
  },
];

export const deployedWorkflowTemplates = workflowTemplates.filter((pipeline) => pipeline.id === "pgta");

export const resourceOverview = [
  {title: "CPU allocation", value: "64", unit: "cores", status: "running", description: "Mock display from PGTA_SNAKEMAKE_CORES"},
  {title: "Memory pressure", value: "42", unit: "%", status: "success", description: "Mock resource telemetry"},
  {title: "Queue jobs", value: "0", unit: "jobs", status: "success", description: "Real qsub is not enabled on fengxian"},
  {title: "QC alerts", value: "14", unit: "metrics", status: "failed", description: "PGT-A baseline QC fail metrics"},
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
