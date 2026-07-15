import type {RuleEvent} from "../api";

const niptPhaseOrder = ["Input QC", "Mapping", "CNV", "T21 classifier", "Aneuploidy", "Fetal fraction", "Final QC", "NIPT workflow", "Validation", "Pipeline"];
const wgsPhaseOrder = ["Pre-calling", "Variant analysis", "QC", "Pipeline"];

const rulePhases: Record<string, string> = {
  mapper_v2_manager_ready: "Input QC",
  fastq_count: "Input QC",
  map: "Mapping",
  convert: "CNV",
  predict: "CNV",
  bgzip_bin: "CNV",
  bgzip_seg: "CNV",
  plot_cnv: "CNV",
  gccorrect: "Aneuploidy",
  gccorrect_bgzip: "Aneuploidy",
  mv_gccorrect_png: "Aneuploidy",
  aneuploidy_calling_batch: "Aneuploidy",
  aneuploidy_calling_dynamicref: "Aneuploidy",
  aneuscreen_direct_ready: "T21 classifier",
  aneuscreen_loading: "T21 classifier",
  aneuscreen_predict: "T21 classifier",
  aneuscreen_loading_correct_matcnv: "T21 classifier",
  aneuscreen_predict_correct_matcnv: "T21 classifier",
  cal_fetal_ratio: "Fetal fraction",
  mapping_qc: "Final QC",
  pngquant: "Final QC",
  bgzip_blk: "Final QC",
  all: "Final QC",
  nipt_full_run: "NIPT workflow",
  nipt_mount_smoke: "Validation",
};

const wgsRulePhases: Record<string, string> = {
  Preall: "Pre-calling",
  cleanFastq: "Pre-calling",
  mapping: "Pre-calling",
  Dedup: "Pre-calling",
  Sam2Cram: "Pre-calling",
  QualCal: "Pre-calling",
  QCStatic: "Pre-calling",
  mtQC: "Pre-calling",
  Haplotyper: "Pre-calling",
  bam2blockUniq: "Pre-calling",
  Smooverun: "Pre-calling",
  mityCall: "Pre-calling",
  MEICall: "Pre-calling",
  fq2cram: "Pre-calling",
  cram2gvcf: "Pre-calling",
  SNV_Annotation: "Variant analysis",
  INDEL_Annotation: "Variant analysis",
  CNV_Annotation: "Variant analysis",
  SV_Annotation: "Variant analysis",
  GVCFtyper: "Variant analysis",
  QCall: "QC",
  PeddyC: "QC",
  sceVCF: "QC",
  gender: "QC",
  SingleQC_merge: "QC",
  mergeQC: "QC",
  plotQC: "QC",
  WGS_QC: "QC",
};

export type RulePhaseSummary = {
  phase: string;
  total: number;
  running: number;
  success: number;
  failed: number;
  canceled: number;
  status: string;
};

export function niptPhaseForRule(rule: string): string {
  return rulePhases[rule] || "Pipeline";
}

export function summarizeRulePhases(rules: RuleEvent[], pipeline = "nipt_docker"): RulePhaseSummary[] {
  const phases = new Map<string, RuleEvent[]>();
  for (const rule of rules) {
    const phase = rule.phase || (pipeline === "wgs" ? wgsRulePhases[rule.rule] || "Pipeline" : niptPhaseForRule(rule.rule));
    phases.set(phase, [...(phases.get(phase) || []), rule]);
  }
  return [...phases.entries()]
    .map(([phase, items]) => {
      const running = items.filter((item) => ["running", "started", "submitted", "planned"].includes(item.status.toLowerCase())).length;
      const failed = items.filter((item) => ["failed", "fail", "error"].includes(item.status.toLowerCase())).length;
      const success = items.filter((item) => item.status.toLowerCase() === "success").length;
      const canceled = items.filter((item) => ["canceled", "cancelled", "terminated"].includes(item.status.toLowerCase())).length;
      return {
        phase,
        total: items.length,
        running,
        success,
        failed,
        canceled,
        status: failed ? "failed" : running ? "running" : canceled ? "canceled" : success === items.length ? "success" : "queued",
      };
    })
    .sort((left, right) => phaseIndex(left.phase, pipeline) - phaseIndex(right.phase, pipeline));
}

export function sortRuleJobs(rules: RuleEvent[]): RuleEvent[] {
  const statusRank = (status: string) => {
    const normalized = status.toLowerCase();
    if (["running", "started", "submitted", "planned"].includes(normalized)) return 0;
    if (["failed", "fail", "error"].includes(normalized)) return 1;
    return 2;
  };
  return [...rules].sort((left, right) => {
    const statusDelta = statusRank(left.status) - statusRank(right.status);
    if (statusDelta) return statusDelta;
    return `${left.rule}:${left.sample_id || ""}:${left.snakemake_jobid || ""}`.localeCompare(`${right.rule}:${right.sample_id || ""}:${right.snakemake_jobid || ""}`);
  });
}

function phaseIndex(phase: string, pipeline: string): number {
  const order = pipeline === "wgs" ? wgsPhaseOrder : niptPhaseOrder;
  const index = order.indexOf(phase);
  return index < 0 ? order.length : index;
}
