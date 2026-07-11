import type {RuleEvent} from "../api";

const phaseOrder = ["Input QC", "Mapping", "CNV", "T21 classifier", "Aneuploidy", "Fetal fraction", "Final QC", "NIPT workflow", "Pipeline"];

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

export type RulePhaseSummary = {
  phase: string;
  total: number;
  running: number;
  success: number;
  failed: number;
  status: string;
};

export function niptPhaseForRule(rule: string): string {
  return rulePhases[rule] || "Pipeline";
}

export function summarizeRulePhases(rules: RuleEvent[]): RulePhaseSummary[] {
  const phases = new Map<string, RuleEvent[]>();
  for (const rule of rules) {
    const phase = rule.phase || niptPhaseForRule(rule.rule);
    phases.set(phase, [...(phases.get(phase) || []), rule]);
  }
  return [...phases.entries()]
    .map(([phase, items]) => {
      const running = items.filter((item) => ["running", "started", "submitted", "planned"].includes(item.status.toLowerCase())).length;
      const failed = items.filter((item) => ["failed", "fail", "error"].includes(item.status.toLowerCase())).length;
      const success = items.filter((item) => item.status.toLowerCase() === "success").length;
      return {
        phase,
        total: items.length,
        running,
        success,
        failed,
        status: failed ? "failed" : running ? "running" : success === items.length ? "success" : "queued",
      };
    })
    .sort((left, right) => phaseIndex(left.phase) - phaseIndex(right.phase));
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

function phaseIndex(phase: string): number {
  const index = phaseOrder.indexOf(phase);
  return index < 0 ? phaseOrder.length : index;
}
