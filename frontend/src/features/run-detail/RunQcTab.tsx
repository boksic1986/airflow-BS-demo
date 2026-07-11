import {useState} from "react";

import type {QcMetric, RunQc} from "../../api";

import {MetricCard} from "../../components/MetricCard";
import {StatusBadge} from "../../components/StatusBadge";
import {normalizeStatus} from "../../lib/status";

const pageSize = 20;
const metricPriority = ["qc_decision", "mapped_fragments", "zero_bin_fraction", "bin_cv", "pearson_r", "median_abs_z", "gc_signal_slope", "nipt_mount_smoke", "read_count", "Q30", "unique_mapping_rate", "pcr_duplication_rate", "chrY_percent", "gender", "fetal_fraction"];

type QcMatrixRow = {sampleId: string; status: string; metrics: Record<string, QcMetric>};

export function RunQcTab({qc}: {qc: RunQc | null}) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(0);
  const metrics = qc?.items || [];
  const matrix = buildQcMatrix(metrics);
  const filteredRows = matrix.rows.filter((row) => (!query.trim() || row.sampleId.toLowerCase().includes(query.trim().toLowerCase())) && (statusFilter === "all" || qcFilterBucket(row.status) === statusFilter));
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const visibleRows = filteredRows.slice(safePage * pageSize, safePage * pageSize + pageSize);
  const failureRows = qcFailureRows(metrics);
  const sampleSummary = qc?.sample_summary || qc?.summary;

  return (
    <div className="qc-tab-stack">
      <div className="metric-grid compact qc-summary-grid">{(["pass", "warn", "fail", "unknown"] as const).map((status) => <MetricCard key={status} title={status} value={sampleSummary?.[status] ?? 0} status={status} />)}</div>
      <section className="qc-failure-summary">
        <div className="section-heading"><h2>QC failures</h2><p>Failed and warning sample metrics</p></div>
        {failureRows.length ? <div className="table-wrap"><table className="data-table compact"><thead><tr><th>sample</th><th>metric</th><th>value</th><th>threshold</th><th>reason</th></tr></thead><tbody>{failureRows.slice(0, 12).map((row) => <tr key={`${row.sampleId}-${row.metric}-${row.value}`}><td>{row.sampleId}</td><td>{row.metric}</td><td>{row.value}</td><td>{row.threshold}</td><td>{row.reason}</td></tr>)}</tbody></table></div> : <p className="empty-state">No failed or warning QC metrics returned.</p>}
      </section>
      {metrics.length ? <>
        <div className="qc-toolbar">
          <label><span>Sample search</span><input type="search" value={query} onChange={(event) => {setQuery(event.target.value); setPage(0);}} placeholder="sample_id" /></label>
          <div className="segmented-control" aria-label="QC status filter">{["all", "fail", "warn", "pass", "unknown"].map((status) => <button key={status} className={statusFilter === status ? "active" : ""} type="button" onClick={() => {setStatusFilter(status); setPage(0);}}>{status}</button>)}</div>
        </div>
        <div className="table-wrap qc-matrix-wrap">
          <table className="data-table compact qc-matrix-table">
            <thead><tr><th>sample_id</th><th>qc_status</th>{matrix.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
            <tbody>{visibleRows.map((row) => <tr key={row.sampleId}><td className="qc-sample-cell">{row.sampleId}</td><td><StatusBadge status={row.status} size="sm" /></td>{matrix.columns.map((column) => {const metric = row.metrics[column]; return <td key={`${row.sampleId}-${column}`} className={metric ? `qc-status-${normalizeStatus(metric.status)}` : ""}>{metric ? metricValue(metric) : "-"}</td>;})}</tr>)}{visibleRows.length === 0 ? <tr><td className="empty-cell" colSpan={matrix.columns.length + 2}>No QC samples match the current filter.</td></tr> : null}</tbody>
          </table>
        </div>
        <div className="pagination-row"><span>{filteredRows.length} sample rows · page {safePage + 1} / {pageCount}</span><div><button className="button ghost" type="button" disabled={safePage === 0} onClick={() => setPage((current) => Math.max(0, current - 1))}>Previous</button><button className="button ghost" type="button" disabled={safePage >= pageCount - 1} onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))}>Next</button></div></div>
      </> : <p className="empty-state">No QC metrics returned.</p>}
    </div>
  );
}

function qcFailureRows(metrics: QcMetric[]) {
  return metrics.filter((metric) => ["failed", "fail", "error", "warning", "warn", "qc_warning"].includes(normalizeStatus(metric.status))).map((metric) => ({sampleId: metric.sample_id || "project", metric: metric.metric_name, value: metricValue(metric), threshold: metric.threshold || "not set", reason: metric.metric_name === "qc_decision" ? `QC decision is ${metric.metric_value || metric.status}` : metric.threshold ? `Outside threshold ${metric.threshold}` : `Metric status is ${metric.status}`}));
}

function buildQcMatrix(metrics: QcMetric[]): {columns: string[]; rows: QcMatrixRow[]} {
  const columns = Array.from(new Set(metrics.map((metric) => metric.metric_name))).sort((left, right) => {const leftPriority = metricPriority.indexOf(left); const rightPriority = metricPriority.indexOf(right); return leftPriority >= 0 || rightPriority >= 0 ? (leftPriority >= 0 ? leftPriority : 999) - (rightPriority >= 0 ? rightPriority : 999) : left.localeCompare(right);});
  const rowsBySample = new Map<string, QcMatrixRow>();
  for (const metric of metrics) {const sampleId = metric.sample_id || "project"; const row = rowsBySample.get(sampleId) || {sampleId, status: "unknown", metrics: {}}; row.metrics[metric.metric_name] = metric; rowsBySample.set(sampleId, row);}
  for (const row of rowsBySample.values()) {
    const decisionMetrics = Object.values(row.metrics).filter((metric) => metric.decision_metric ?? isDecisionThreshold(metric.threshold));
    row.status = aggregateDecisionStatus(decisionMetrics.map((metric) => metric.status));
  }
  return {columns, rows: Array.from(rowsBySample.values()).sort((left, right) => qcStatusRank(left.status) - qcStatusRank(right.status) || left.sampleId.localeCompare(right.sampleId))};
}

function aggregateDecisionStatus(statuses: string[]): string {if (!statuses.length) return "unknown"; const normalized = statuses.map(normalizeStatus); if (normalized.some((status) => ["failed", "fail", "error"].includes(status))) return "fail"; if (normalized.some((status) => ["warning", "warn", "qc_warning"].includes(status))) return "warn"; if (normalized.some((status) => status === "unknown")) return "unknown"; return "pass";}
function isDecisionThreshold(threshold?: string | null): boolean {const normalized = String(threshold || "").trim().toLowerCase(); return Boolean(normalized && !["reported", "informational", "n/a", "na"].includes(normalized));}

function qcStatusRank(status: string): number {const value = normalizeStatus(status); if (["failed", "fail", "error"].includes(value)) return 0; if (["warning", "warn", "qc_warning"].includes(value)) return 1; if (value === "unknown") return 2; if (["success", "pass"].includes(value)) return 3; return 4;}
function metricValue(metric: QcMetric): string {if (metric.metric_value !== null && metric.metric_value !== undefined && metric.metric_value !== "") return String(metric.metric_value); if (metric.metric_numeric !== null && metric.metric_numeric !== undefined) return String(metric.metric_numeric); return "-";}
function qcFilterBucket(status: string): string {const value = normalizeStatus(status); if (["failed", "fail", "error"].includes(value)) return "fail"; if (["warning", "warn", "qc_warning"].includes(value)) return "warn"; if (["success", "pass"].includes(value)) return "pass"; return "unknown";}
