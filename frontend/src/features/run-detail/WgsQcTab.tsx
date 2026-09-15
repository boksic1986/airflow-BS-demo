import type {QcJudgment, Sample} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";
import {QcMetric} from "./QcMetric";

const keyMetrics = [
  ["clean_q30_percent", "Clean Q30"],
  ["mapped_reads_percent", "Mapped reads"],
  ["average_depth", "Average depth"],
  ["coverage_20x_percent", "Coverage ≥20X"],
  ["contamination", "Contamination"],
] as const;

const metricLabels: Record<string, string> = {
  mapped_reads_percent: "Mapped reads",
  raw_gc_percent: "Raw GC",
  clean_gc_percent: "Clean GC",
  snv_count: "SNV count",
  cnv_count: "CNV count",
  clean_q30_percent: "Clean Q30",
  average_depth: "Average depth",
  fold80: "Fold 80 base penalty",
  duplication_percent: "Duplicated reads",
  coverage_20x_percent: "Coverage ≥20X",
  coverage_1x_percent: "Coverage ≥1X",
  raw_bases: "Raw bases",
  effective_bases: "Effective bases",
  contamination: "Contamination",
  multi_dedup_bases: "MultiQC deduplicated bases",
  multi_average_depth: "MultiQC mean depth",
  multi_q30_percent: "MultiQC clean Q30",
  multi_coverage_30x_percent: "MultiQC coverage ≥30X",
  multi_coverage_10x_percent: "MultiQC coverage ≥10X",
  multi_duplication_percent: "MultiQC duplicated reads",
  sex_match: "Sex consistency",
  peddy: "Relatedness check",
};

const reasonLabels: Record<string, string> = {
  "Release policy provenance unavailable": "当前流程版本暂无已审核 QC 判定策略",
  "Within release criterion": "符合当前版本阈值",
  "Outside release criterion": "超出当前版本阈值",
  "Value unavailable": "未提供该指标值",
  "Project item unavailable": "项目类型条件不可用",
  "Sample type unavailable": "样本类型条件不可用",
  "Frozen BKW selection unavailable": "BKW 配置条件不可用",
  "Family relation unavailable": "家系关系条件不可用",
  "No applicable criterion in this release": "当前版本不适用此判定",
  "Value or release provenance unavailable": "指标值或版本策略来源不可用",
  "Source-produced contamination status": "来源 QC 给出的污染判定",
  "Individual safe evidence unavailable; retained source aggregate includes this check": "个体级安全证据不可用；来源汇总 QC 仍包含此项检查",
  "Source-produced sex consistency judgment": "来源 QC 给出的性别一致性判定",
};

export function WgsQcTab({samples}: {samples: Sample[]}) {
  return <div className="table-wrap">
    <table className="data-table" aria-label="WGS QC summary">
      <thead><tr>
        <th>Sample</th>
        <th>Source QC status</th>
        {keyMetrics.map(([, label]) => <th key={label}>{label}</th>)}
        <th>All release criteria</th>
      </tr></thead>
      <tbody>
        {samples.map((sample) => <tr key={sample.sample_id}>
          <td>{sample.sample_id}</td>
          <td><StatusBadge status={sample.qc_status || "unknown"} size="sm" /></td>
          {keyMetrics.map(([key]) => <td key={key}><QcMetric value={sample.qc_metrics?.[key]} judgment={sample.qc_judgments?.[key]} /></td>)}
          <td><SampleQcDetails sample={sample} /></td>
        </tr>)}
        {samples.length === 0 ? <tr><td className="empty-cell" colSpan={keyMetrics.length + 3}>QC is pending or unavailable because the batch QCstat has not been projected yet.</td></tr> : null}
      </tbody>
    </table>
  </div>;
}

function SampleQcDetails({sample}: {sample: Sample}) {
  const keys = orderedMetricKeys(sample);
  return <details>
    <summary>Review all metrics</summary>
    <div className="table-wrap">
      <table className="data-table compact" aria-label={`QC metric details for ${sample.sample_id}`}>
        <thead><tr><th>Metric</th><th>Value</th><th>Judgment</th><th>Reason</th><th>Threshold</th><th>Provenance</th></tr></thead>
        <tbody>{keys.map((key) => {
          const judgment = sample.qc_judgments?.[key];
          return <tr key={key}>
            <td>{metricLabel(key)}</td>
            <td>{formatValue(sample.qc_metrics?.[key], judgment)}</td>
            <td><StatusBadge status={judgment?.status || "unknown"} size="sm" /></td>
            <td>{friendlyReason(judgment?.reason)}</td>
            <td>{formatThreshold(judgment)}</td>
            <td>{formatProvenance(judgment)}</td>
          </tr>;
        })}</tbody>
      </table>
    </div>
    <details>
      <summary>Raw diagnostic fields</summary>
      <pre>{JSON.stringify({qc_metrics: sample.qc_metrics || {}, qc_judgments: sample.qc_judgments || {}}, null, 2)}</pre>
    </details>
  </details>;
}

function orderedMetricKeys(sample: Sample): string[] {
  const received = new Set([...Object.keys(sample.qc_metrics || {}), ...Object.keys(sample.qc_judgments || {})]);
  const ordered = Object.keys(metricLabels).filter((key) => received.delete(key));
  return [...ordered, ...Array.from(received).sort()];
}

function metricLabel(key: string): string {
  return metricLabels[key] || key.replaceAll("_", " ").replace(/^./, (character) => character.toUpperCase());
}

function formatValue(fallback: string | number | null | undefined, judgment?: QcJudgment): string {
  const value = judgment?.value ?? fallback;
  if (value == null || value === "") return "-";
  return `${value}${judgment?.unit && judgment.unit !== "status" ? ` ${judgment.unit}` : ""}`;
}

function friendlyReason(reason?: string): string {
  if (!reason) return "判定原因不可用";
  return reasonLabels[reason] || reason;
}

function formatThreshold(judgment?: QcJudgment): string {
  const threshold = judgment?.threshold;
  if (threshold == null) return "不适用或不可用";
  if (typeof threshold === "string") return threshold;
  if (typeof threshold !== "object" || Array.isArray(threshold)) return "详见诊断信息";
  const bounds = threshold as Record<string, unknown>;
  const unit = judgment?.unit && judgment.unit !== "status" ? ` ${judgment.unit}` : "";
  const minimum = finiteBound(bounds.min);
  const maximum = finiteBound(bounds.max);
  if (minimum != null && maximum != null) {
    const lower = bounds.min_inclusive === false ? ">" : "≥";
    const upper = bounds.max_inclusive === false ? "<" : "≤";
    return `${lower} ${minimum}${unit} and ${upper} ${maximum}${unit}`;
  }
  if (minimum != null) return `${bounds.min_inclusive === false ? ">" : "≥"} ${minimum}${unit}`;
  if (maximum != null) return `${bounds.max_inclusive === false ? "<" : "≤"} ${maximum}${unit}`;
  return "详见诊断信息";
}

function finiteBound(value: unknown): string | null {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : typeof value === "string" && value.trim() ? value : null;
}

function formatProvenance(judgment?: QcJudgment): string {
  const provenance = judgment?.provenance || {};
  const extended = (judgment || {}) as QcJudgment & {source_artifact?: string; source_sha256?: string};
  const values = [
    typeof provenance.release_id === "string" ? provenance.release_id : null,
    extended.source_artifact || null,
    typeof provenance.source_commit === "string" ? `commit ${provenance.source_commit.slice(0, 8)}` : null,
    typeof provenance.policy_sha256 === "string" ? `policy ${provenance.policy_sha256.slice(0, 12)}` : null,
    extended.source_sha256 ? `artifact ${extended.source_sha256.slice(0, 12)}` : null,
  ].filter(Boolean);
  return values.join(" · ") || "不可用";
}
