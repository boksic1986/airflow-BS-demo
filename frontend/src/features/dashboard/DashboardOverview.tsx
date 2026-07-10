import {Link} from "react-router-dom";

import type {DashboardOverview, DashboardPipeline} from "../../api";

import {StatusBadge} from "../../components/StatusBadge";

export const dashboardPipelines: Array<{value: DashboardPipeline; label: string; description: string}> = [
  {value: "all", label: "All pipelines", description: "PGT-A + NIPT Docker"},
  {value: "pgta", label: "PGT-A", description: "Embryo CNV workflow"},
  {value: "nipt_docker", label: "NIPT Docker", description: "Scanned FASTQ chip batches"},
];

export function PipelineRail({pipeline, onChange}: {
  pipeline: DashboardPipeline;
  onChange: (pipeline: DashboardPipeline) => void;
}) {
  return (
    <aside className="pipeline-rail" aria-label="Pipeline selector">
      {dashboardPipelines.map((item) => (
        <button
          aria-label={item.label}
          className={pipeline === item.value ? "active" : ""}
          key={item.value}
          type="button"
          onClick={() => onChange(item.value)}
        >
          <strong>{item.label}</strong>
          <span>{item.description}</span>
        </button>
      ))}
    </aside>
  );
}

export function CommandSummary({overview, pipeline, loading, error}: {
  overview: DashboardOverview | null;
  pipeline: DashboardPipeline;
  loading: boolean;
  error: string | null;
}) {
  const totals = overview?.totals || {runs: 0, running: 0, failed: 0, success: 0, created: 0};
  const samples = overview?.sample_summary || {total: 0, running: 0, workflow_failed: 0, qc_failed: 0, completed: 0};
  const pipelineQuery = pipeline === "all" ? "" : `pipeline=${pipeline}&`;
  const items = [
    {label: "Runs", value: totals.runs, hint: `${totals.running} running`, to: `/runs?${pipelineQuery}sort=created_desc`},
    {label: "Samples", value: samples.total, hint: `${samples.running} in workflow`, to: `/samples?${pipelineQuery}page=1`},
    {label: "QC alerts", value: samples.qc_failed, hint: "sample-level fails", to: `/failures?${pipelineQuery}kind=qc&page=1`},
    {label: "Workflow fails", value: totals.failed, hint: `${samples.workflow_failed} samples affected`, to: `/failures?${pipelineQuery}kind=workflow&page=1`},
  ];
  return (
    <>
      {error ? <div className="inline-error" role="alert">Overview unavailable: {error}</div> : null}
      {loading && !overview ? <p className="muted panel-loading">Loading overview...</p> : null}
      <section className="command-summary-strip" aria-label="Command center summary" aria-busy={loading}>
        {items.map((item) => (
          <Link className="command-summary-link" key={item.label} to={item.to}>
            <article>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.hint}</small>
            </article>
          </Link>
        ))}
      </section>
    </>
  );
}

export function OperationsOverview({overview, period, loading, onPeriodChange}: {
  overview: DashboardOverview | null;
  period: "24h" | "7d" | "30d";
  loading: boolean;
  onPeriodChange: (period: "24h" | "7d" | "30d") => void;
}) {
  return (
    <section className="panel" aria-busy={loading} title="Aggregated backend metrics for the selected pipeline and period">
      <div className="section-heading split">
        <h2>Operations overview</h2>
        <StatusBadge status={(overview?.totals.failed || 0) > 0 ? "warning" : "success"} />
      </div>
      <div className="dashboard-insight-grid">
        <StatusDistribution overview={overview} />
        <RunTrend overview={overview} period={period} />
        <SampleThroughput overview={overview} period={period} onPeriodChange={onPeriodChange} />
      </div>
    </section>
  );
}

function StatusDistribution({overview}: {overview: DashboardOverview | null}) {
  const distribution = overview?.status_distribution || {};
  const segments = [
    {key: "running", label: "Running", tone: "info"},
    {key: "created", label: "Created", tone: "neutral"},
    {key: "success", label: "Success", tone: "success"},
    {key: "failed", label: "Failed", tone: "danger"},
  ];
  const total = Math.max(1, segments.reduce((sum, item) => sum + (distribution[item.key] || 0), 0));
  return (
    <article className="insight-card">
      <div>
        <h3>Status distribution</h3>
        <p>{overview?.totals.runs ?? 0} runs in current context</p>
      </div>
      <div className="status-distribution" aria-label="Status distribution">
        {segments.map((segment) => (
          <span
            className={`segment ${segment.tone}`}
            key={segment.key}
            style={{width: `${Math.max(0, ((distribution[segment.key] || 0) / total) * 100)}%`}}
            title={`${segment.label}: ${distribution[segment.key] || 0}`}
          />
        ))}
      </div>
      <div className="distribution-legend">
        {segments.map((segment) => (
          <span key={segment.key}><i className={segment.tone} />{segment.label}: {distribution[segment.key] || 0}</span>
        ))}
      </div>
    </article>
  );
}

function RunTrend({overview, period}: {overview: DashboardOverview | null; period: "24h" | "7d" | "30d"}) {
  const trend = overview?.trend || [];
  const maxRuns = Math.max(1, ...trend.map((item) => item.runs));
  const points = trend.map((item, index) => {
    const x = trend.length <= 1 ? 50 : (index / (trend.length - 1)) * 100;
    const y = 44 - (item.runs / maxRuns) * 34;
    return `${x},${y}`;
  }).join(" ");
  return (
    <article className="insight-card">
      <div>
        <h3>{period} run activity</h3>
        <p>Created runs and failures</p>
      </div>
      <svg aria-label={`${period} run activity`} className="sparkline" preserveAspectRatio="none" viewBox="0 0 100 50">
        <polyline fill="none" points={points || "0,44 100,44"} stroke="#176b87" strokeWidth="3" />
        {trend.map((item, index) => {
          const x = trend.length <= 1 ? 50 : (index / (trend.length - 1)) * 100;
          const y = 44 - (item.runs / maxRuns) * 34;
          return <circle cx={x} cy={y} fill={item.failed ? "#b42318" : "#176b87"} key={item.date} r="2.6" />;
        })}
      </svg>
      <div className="mini-bars">
        {trend.map((item) => (
          <span key={item.date} style={{height: `${Math.max(8, (item.runs / maxRuns) * 42)}px`}} title={`${item.date}: ${item.runs}`} />
        ))}
      </div>
    </article>
  );
}

function SampleThroughput({overview, period, onPeriodChange}: {
  overview: DashboardOverview | null;
  period: "24h" | "7d" | "30d";
  onPeriodChange: (period: "24h" | "7d" | "30d") => void;
}) {
  const summary = overview?.sample_summary || {total: 0, running: 0, workflow_failed: 0, qc_failed: 0, completed: 0};
  const trend = overview?.sample_trend || [];
  const maxSamples = Math.max(1, ...trend.map((item) => item.total));
  return (
    <article className="insight-card sample-throughput-card">
      <div>
        <div className="section-heading-inline">
          <h3>Sample throughput</h3>
          <div className="period-selector" aria-label="Sample throughput period">
            {(["24h", "7d", "30d"] as const).map((item) => (
              <button className={period === item ? "active" : ""} key={item} type="button" onClick={() => onPeriodChange(item)}>{item}</button>
            ))}
          </div>
        </div>
      </div>
      <div className="sample-throughput-grid">
        <span>Sample total <strong>{summary.total}</strong></span>
        <span>Running samples <strong>{summary.running}</strong></span>
        <span>Workflow failed samples <strong>{summary.workflow_failed}</strong></span>
        <span>QC failed samples <strong>{summary.qc_failed}</strong></span>
        <span>Completed samples <strong>{summary.completed}</strong></span>
      </div>
      <div className="sample-stacked-bar" aria-label="Sample throughput distribution">
        <span className="success" style={{width: `${percent(summary.completed, summary.total)}%`}} title={`Completed: ${summary.completed}`} />
        <span className="info" style={{width: `${percent(summary.running, summary.total)}%`}} title={`Running: ${summary.running}`} />
        <span className="danger" style={{width: `${percent(summary.workflow_failed, summary.total)}%`}} title={`Workflow failed: ${summary.workflow_failed}`} />
        <span className="warning" style={{width: `${percent(summary.qc_failed, summary.total)}%`}} title={`QC failed: ${summary.qc_failed}`} />
      </div>
      <div className="mini-bars sample-bars">
        {trend.map((item) => (
          <span key={item.date} style={{height: `${Math.max(8, (item.total / maxSamples) * 42)}px`}} title={`${item.date}: ${item.total} samples`} />
        ))}
      </div>
    </article>
  );
}

function percent(value: number, total: number): number {
  if (!total) return 0;
  return Math.max(0, Math.min(100, (value / total) * 100));
}
