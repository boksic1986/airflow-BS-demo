import type {Sample} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";
import {QcMetric} from "./QcMetric";

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
  "Contamination measurements exceed release criterion": "污染指标超出当前版本阈值",
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
  const received = new Set(samples.flatMap(orderedMetricKeys));
  const keys = [...Object.keys(metricLabels).filter((key) => received.delete(key)), ...Array.from(received).sort()];
  return <div className="table-wrap wgs-qc-table-wrap" tabIndex={0} aria-label="QC table horizontal scroll">
    <table className="data-table" aria-label="WGS QC summary">
      <thead><tr>
        <th>Sample</th>
        <th>Source QC status</th>
        {keys.map((key) => <th key={key}>{metricLabel(key)}</th>)}
        <th>Reason</th>
      </tr></thead>
      <tbody>
        {samples.map((sample) => <tr key={sample.sample_id}>
          <td>{sample.sample_id}</td>
          <td><StatusBadge status={sample.qc_status || "unknown"} size="sm" /></td>
          {keys.map((key) => <td key={key}>{hasAvailableValue(sample, key)
            ? <QcMetric value={sample.qc_metrics?.[key]} judgment={sample.qc_judgments?.[key]} /> : "-"}</td>)}
          <td className="qc-reason-cell">{sampleReason(sample)}</td>
        </tr>)}
        {samples.length === 0 ? <tr><td className="empty-cell" colSpan={keys.length + 3}>QC is pending or unavailable because the batch QCstat has not been projected yet.</td></tr> : null}
      </tbody>
    </table>
  </div>;
}

function sampleReason(sample: Sample): string {
  const keys = orderedMetricKeys(sample);
  const reasons = keys.filter((key) => ["fail", "warn"].includes(sample.qc_judgments?.[key]?.status || ""))
    .map((key) => `${metricLabel(key)}：${friendlyReason(sample.qc_judgments![key].reason)}`);
  if (reasons.length) return reasons.join("；");
  if (["fail", "failed", "warn", "warning"].includes(sample.qc_status || "")) return "来源汇总 QC 未通过；缺少可展示的原因证据";
  return keys.length ? "-" : "暂无可展示的质控判定指标";
}

function orderedMetricKeys(sample: Sample): string[] {
  // Values remain useful when this release has no audited judgment policy.
  // Only known metric fields may fall back to the raw API projection.
  const received = new Set([
    ...Object.keys(sample.qc_judgments || {}),
    ...Object.keys(sample.qc_metrics || {}).filter((key) => key in metricLabels),
  ]);
  const ordered = Object.keys(metricLabels).filter((key) => received.delete(key));
  return [...ordered, ...Array.from(received).sort()];
}

function hasAvailableValue(sample: Sample, key: string): boolean {
  const judgment = sample.qc_judgments?.[key];
  const value = judgment?.value ?? sample.qc_metrics?.[key];
  return typeof value === "number" ? Number.isFinite(value) : typeof value === "string" && value.trim().length > 0;
}

function metricLabel(key: string): string {
  return metricLabels[key] || key.replaceAll("_", " ").replace(/^./, (character) => character.toUpperCase());
}

function friendlyReason(reason?: string): string {
  if (!reason) return "判定原因不可用";
  return reasonLabels[reason] || reason;
}
